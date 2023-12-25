import binascii
import core.coolPrint as log # for cool console logging

log.info("importing serial backend and cv2..")
from core.serBackend import vHID, keySerial # hid control
import core.cv2Frames as cvBackend # custom cv2 backend

log.info("importing flask..")
from flask import Flask, Response, request # flask webserver 
from flask_socketio import SocketIO, emit # flask sockets (for cv2 backend, amongst other things)

log.info("importing extras..")
import argparse # for arguments (doh)
import threading # for seperate running threads (doh)
import os # for obs studio opening, amongst other things
import logging
import json
import time
import sys
import psutil
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

hid = None
modifiers = []
backend = None

config = None
lastConfigWrite = datetime.now()
rebootRequired = False

emitting = False
splitFrames = None
updateFrames = False
frameSplit = 4

def frameCallback():
    if backend == "obs": return False
    else:
        frm = backend.grabFrame(encode=True)
        return frm

@app.route('/')
def index():
    return open('./core/static/index.html', 'r').read()

@app.route('/hid.js')
def hidjs():
    return Response(open('./core/static/js/hid.js', 'r').read(), mimetype="text/javascript")

@app.route('/socket.io.js')
def socketjs():
    return Response(open('./core/static/js/socket.io.js', 'r').read(), mimetype="text/javascript")

@app.route('/libjpegturbowasm.js')
def wasm1():
    return Response(open('./core/static/js/jpegwasm.js', 'r').read(), mimetype="text/javascript")
@app.route('/libjpegturbojs.js')
def wasm2():
    return Response(open('./core/static/js/jpegwasmjs.js', 'r').read(), mimetype="text/javascript")
@app.route("/libjpegturbowasm.wasm")
def wasm3():
    return Response(open('./core/static/js/jpeg.wasm', 'rb').read(), mimetype="application/wasm")

@app.route('/toastify.js')
def toastify():
    return Response(open('./core/static/js/toastify.js', 'r').read(), mimetype="text/javascript")

@app.route('/toastify.css')
def toastifycss():
    return Response(open('./core/static/css/toastify.min.css', 'r').read(), mimetype="text/css")

@app.route('/stream')
def stream():
    p = "./core/static/streams/"
    if backend == "obs":
        return open(p+'whip_stream.html', 'r').read()
    
    return open(p+'cv2_stream.html', 'r').read()

@app.route('/settings')
def settings():
    p = "./core/static/"
    
    return open(p+'settings.html', 'r').read()

@app.route('/api/dump_settings')
def dump_settings():
    global config
    return Response(json.dumps(config, indent=4), mimetype="application/json")

@app.route('/api/write_settings', methods=["POST"])
def write_settings():
    global config, lastConfigWrite, args, rebootRequired
    v = request.get_json(force=True)

    if (datetime.now() - lastConfigWrite).seconds > 5:
        lastConfigWrite = datetime.now()
        config = v
        with open(args.config, "w") as f:
            f.write(json.dumps(v, indent=4))
            f.flush()

        rebootRequired = True
        return Response(json.dumps({"success": True}, indent=4), mimetype="application/json")
    
    else:
        return Response(json.dumps({"success": False, "wait": (datetime.now() - lastConfigWrite).seconds}, indent=4), mimetype="application/json", status=429)

@app.route("/api/splitframeinfo")
def getSplitInfo():
    global backend, frameSplit

    frm = backend.grabFrame(encode=False)
    spFrame = backend.split_image(frm, split=frameSplit)[0]

    a = {
        "resolution": [spFrame.shape[1], spFrame.shape[0]],
        "splitby": frameSplit
    }

    return Response(json.dumps(a, indent=4), mimetype="application/json")


@socketio.on('frame')
def handle_frame():
    frm = frameCallback()
    if frm == False:
        return
    socketio.emit('video_frame', {"image": frm, "len": len(frm)})

@socketio.on('keystroke')
def handle_keystroke(key):
    global modifiers
    hid.press(key, modifiers=modifiers)

@socketio.on('mouse')
def handle_mouse(jsonXY):
    x, y = jsonXY.split("|")
    if config["mouse"]["invertMouse"]["value"]:
        x = int(x) * -1
        y = int(y) * -1
        
    hid.mouse(int(x), int(y))

@socketio.on('scroll')
def handle_scroll(jsonXY):
    x = jsonXY.replace("S:", "")
    hid.scroll(int(x) if not config["mouse"]["scrollInvert"]["value"] else int(x)*-1)

@socketio.on('click')
def handle_click(key):
    hid.click(key)

@socketio.on('modifiers')
def handle_mod(key):
    global modifiers
    modifiers = key.split(",")

    if modifiers[0] == '':
        modifiers = []

@socketio.on('framerate')
def handle_fps():
    emit("fps", {"framerate": backend.fps})

@socketio.on('updatetiles')
def handle_tiles():
    global updateFrames
    updateFrames = True
    
def autoReboot():
    global rebootRequired

    log.info("reboot daemon running in background")

    while True:
        if rebootRequired:
            log.warn("rebooting due to config change..")

            try:
                p = psutil.Process(os.getpid())
                for handler in p.open_files() + p.connections():
                    os.close(handler.fd)
            except Exception as e:
                logging.error(e)

            python = sys.executable
            os.execl(python, python, *sys.argv)

        time.sleep(0.5)

def autoFrameReport():
    global app
    ctx = app.test_request_context('/')
    log.info("started frame daemon")
    while True:
        frm = backend.grabFrame(encode=True)

        if frm is False:
            continue
    
        socketio.emit('video_frame', {"image": frm, "len": len(frm)}, namespace="/")
        time.sleep(0.001)

def autoChangeReport(split:bool, frameSplit=frameSplit):
    global app, backend, args, splitNewFrames
    global updateFrames, oldFrames, onNextCycle, framesReportedNew
    log.info('started tile change daemon')

    def scanFrames(frames:list, _id=0):
        global oldFrames, splitNewFrames, onNextCycle, framesReportedNew, frameSplit

        decay = round((1*frameSplit)/2) # amount of frames to send AFTER changes are detected
        # this is to prevent artifacts staying after updates

        changedFrames = {}

        log.info("started thread with id {} managing frames {} ({} frames)".format(_id, frames2Manage, len(frames2Manage)))

        while True:
            time.sleep(0.001)

            if oldFrames is None:
                continue

            if splitNewFrames is None:
                continue
            
            for _index in frames:
                try:
                    newFrame = splitNewFrames[_index]
                    oldFrame = oldFrames[_index]
                except IndexError:
                    ...

                if cvBackend._detect_changes(newFrame, oldFrame) or onNextCycle:
                    safeEmit('tileframechange', {
                        "frameIndex": _index,
                        "frame": backend.encode(newFrame),
                        "resolution": [newFrame.shape[1], newFrame.shape[0]],
                    })

                    if not onNextCycle:
                        changedFrames[_index] = decay
                    else:
                        framesReportedNew += 1

                    try:
                        oldFrames[_index] = newFrame
                    except:
                        ...

                    time.sleep(0.001)
                elif _index in list(changedFrames):
                    if changedFrames[_index] == 0:
                        continue

                    safeEmit('tileframechange', {
                        "frameIndex": _index,
                        "frame": backend.encode(newFrame),
                        "resolution": [newFrame.shape[1], newFrame.shape[0]],
                    })

                    if changedFrames[_index] == 0:
                        changedFrames.pop(_index)
                    else:
                        changedFrames[_index] -= 1

                    try:
                        oldFrames[_index] = newFrame
                    except:
                        ...

                    time.sleep(0.001)

        

    def safeEmit(channel, data):
        global emitting
        
        if not emitting:
            emitting = True
            socketio.emit(channel, data)
            emitting = False
        else:
            while emitting:
                pass

            emitting = True
            socketio.emit(channel, data)
            emitting = False

        time.sleep(0.005)

    oldFrames = None
    splitNewFrames = None
    framesReportedNew = 0

    hb = 0

    onNextCycle = False

    if split:
        tid = 0
        start = 0
        framesEachThread = 4
        amntOfFrames = frameSplit*frameSplit
        
        for x in range(0, amntOfFrames, framesEachThread):
            frames2Manage = []
            for x in range(start, start+framesEachThread):
                if amntOfFrames >= x:
                    frames2Manage.append(x)
                else:
                    break

            threading.Thread(target=scanFrames,
                              args=(frames2Manage,),
                              kwargs={'_id': tid}).start()
            tid += 1
            start += framesEachThread

    while True:
        time.sleep(0.0025)
        if oldFrames is None:
            frm = backend.grabFrame(encode=False)

            if frm is False:
                continue

            if split:
                oldFrames = backend.split_image(frm, split=frameSplit)
                backend.frame = None
            else:
                oldFrames = frm


            continue
        else:
            newFrames = backend.grabFrame(encode=False)

            if newFrames is False:
                continue

            if split:
                splitNewFrames = backend.split_image(newFrames, split=frameSplit)

                if onNextCycle: # if we're resending all tiles
                    if framesReportedNew >= len(splitNewFrames): # to make sure all threads sent their frame
                        onNextCycle = False # turn it off
                        framesReportedNew = 0 # reset
                    else:
                        ... # pass

                if updateFrames: # if we're supposed to resend all tiles
                    onNextCycle = True

                updateFrames = False
            else:
                if backend.detect_changes(newFrames, oldFrames):
                    print("change")
                    socketio.emit('video_frame', {"image": frameCallback()}, namespace="/")
                    oldFrames = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()


    parser.add_argument("--host",
                        help="ip to host server at",
                        default="127.0.0.1")
    
    parser.add_argument("--port",
                        help="port to host server at",
                        default=80, type=int)

    parser.add_argument("--config",
                        "-c", help="path to config",
                        default="./config.json")
    
    parser.add_argument("-d",
                        "--debug", help="debug mode",
                        action="store_true", default=False)
                       
    parser.add_argument("-nkb",
                        help="no keyboard mode",
                        action="store_true", default=False)
    
    args = parser.parse_args()

    # read config
    log.info('reading config')
    config = json.loads(open(args.config, "r").read())

    # setup vhid
    log.info('setting up keystroke serial..')
    ser = keySerial(config["serial"]["port"]["value"],
                     baud=115200, isFake=args.nkb)
    hid = vHID(ser)

    # setup streaming
    if config["video"]["streamBackend"]["value"] == "cv2":
        log.info('setting up cv2 capture.. (might take a while)')

        backend = cvBackend.cv2_backend(config=config["video"]["cv2"], debug=args.debug)
        
        backend.autoFrames()


    elif config["video"]["streamBackend"]["value"] == "whip":
        backend = "obs"
        log.info("opening obs studio w/ scene \"KVM\"")
        log.warn("anything put in command args aren't used - if you want to edit resolution, etc. do it in OBS studio")

        threading.Thread(target=os.system, 
                         args=("{}".format(config["video"]["whip"]["mtxPath"]["value"]),),
                         daemon=True).start()

        log.warn("waiting 0.5s..")
        time.sleep(0.5) # wait for mtx server to start
        
        if not config["video"]["whip"]["obsNoArgs"]["value"]:
            threading.Thread(target=os.system, 
                             args=("{} --startstreaming --scene \"KVM\" --minimize-to-tray".format(config["video"]["whip"]["obsPath"]["value"]),),
                             daemon=True).start()
        else:
            threading.Thread(target=os.system,
                            args=("{}".format(config["video"]["whip"]["obsPath"]["value"]),),
                            daemon=True).start()

    try:
        # setup http server
        log.info("setting up flask server..")

        fLog = logging.getLogger('werkzeug')
        #fLog.setLevel(logging.ERROR)

        threading.Thread(target=autoReboot, daemon=True).start()

        if config["video"]["cv2"]["frameMethod"]["value"] == "tiles":
            threading.Thread(target=autoChangeReport, args=(True,), kwargs={"frameSplit": frameSplit}, daemon=True).start()
        elif config["video"]["cv2"]["frameMethod"]["value"] == "daemon":
            threading.Thread(target=autoFrameReport, daemon=True).start()

        socketio.run(app, host=args.host, port=args.port, debug=False)
    except KeyboardInterrupt:
        os.system("taskkill /F /IM obs64.exe")
    
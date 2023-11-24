from core.serBackend import vHID, keySerial # hid control
import core.cv2Frames as cvBackend # custom cv2 backend

from flask import Flask, Response, request # flask webserver 
from flask_socketio import SocketIO, emit # flask sockets (for cv2 backend, amongst other things)

import argparse # for arguments (doh)
import threading # for seperate running threads (doh)
import os # for obs studio opening, amongst other things

import core.coolPrint as log # for cool console logging
import logging
import json
import time

from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

hid = None
modifiers = []
backend = None

config = None
lastConfigWrite = datetime.now()

def frameCallback():
    if backend == "obs": return False
    else:
        return backend.frame()
    
def getValuefromConfig(value):
    global config

@app.route('/')
def index():
    return open('./core/static/index.html', 'r').read()

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
    global config, lastConfigWrite, args
    v = request.get_json(force=True)

    print((datetime.now() - lastConfigWrite).seconds)

    if (datetime.now() - lastConfigWrite).seconds > 5:
        config = json.dumps(v, indent=4)
        with open(args.config, "w") as f:
            f.write(json.dumps(v, indent=4))
            f.flush()

        return Response(json.dumps({"success": True}, indent=4), mimetype="application/json")
    
    else:
        return Response(json.dumps({"success": False, "wait": (datetime.now() - lastConfigWrite).seconds}, indent=4), mimetype="application/json", status=429)

@socketio.on('connect')
def handle_connect():
    emit('video_frame', {'image': frameCallback()})

@socketio.on('frame')
def handle_frame():
    emit('video_frame', {'image': frameCallback()})

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

    print("[+] set modifiers to {}".format(modifiers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()


    parser.add_argument("--config",
                        "-c", help="path to config",
                        default="./config.json")
    
    args = parser.parse_args()

    # read config
    log.info('reading config')
    config = json.loads(open(args.config, "r").read())

    # setup vhid
    log.info('setting up keystroke serial..')
    ser = keySerial(config["serial"]["port"]["value"],
                     baud=9600)
    hid = vHID(ser)

    # setup streaming
    backendList = config["video"]["streamBackend"]["options"]
    if backendList[config["video"]["streamBackend"]["value"]] == "cv2":
        print('[+] setting up cv2 capture.. (might take a while)')

        backend = cvBackend.cv2_backend(backend=config["video"]["cv2"]["backend"]["value"],
                              resolution=config["video"]["cv2"]["resolution"]["value"],
                              quality=config["video"]["cv2"]["quality"]["value"],
                              camera=config["video"]["cv2"]["camera"]["value"])

    elif backendList[config["video"]["streamBackend"]["value"]] == "whip":
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
        fLog.setLevel(logging.ERROR)
        socketio.run(app, debug=False)
    except KeyboardInterrupt:
        os.system("taskkill /F /IM obs64.exe")
    
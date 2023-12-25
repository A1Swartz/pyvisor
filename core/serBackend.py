import serial
import json
import time
import threading

class keySerial:
    """
    a class that manages the serial HID bridge
    """

    def __init__(self, port, baud=115200, isFake=False) -> None:
        self.port = port
        if not isFake:
            self.serial = serial.Serial(port, baudrate=baud)
        else :
            self.serial = None
        pass

    def stringSend(self, string:str):
        """
        sends a string over the serial wire
        """
        
        if self.serial is not None:
            self.serial.write((string+"\r\n").encode('ascii'))
        return True
    
    def readline(self):
        """
        reads a line from serial wire
        """

        if self.serial == None: return None
        return self.serial.readline().decode('ascii')
    
class vHID:
    """
    virtual hid that uses keySerial object to communicate
    """
    def __init__(self, keyser:keySerial, pollingRate=-1) -> None:
        self.serial = keyser
        self.polling = pollingRate
        self.baseDataDict = {
            "key": None,
            "modifiers": [],
            "mouse": {
                "x": 0,
                "y": 0,
            },
            "scroll": 0,
            "mouseButtons": []
        }

        self.nextData = self.baseDataDict
        self.kill = False

        threading.Thread(target=self.sendData, daemon=True).start()

        pass

    def press(self, key:str, modifiers:list=[]):
        """
        press a key, with modifiers

        key: can be any key
        """

        self.nextData["key"] = key

        for x in list(modifiers): # to prevent random modifiers (ex: yyayyayay as a modifier)
            if x in ["Shift", "Alt", "Control", "Meta"]:
                pass
            else:
                modifiers.remove(x)

        self.nextData["modifiers"] = modifiers

    def click(self, key:str):
        """
        click the mouse

        key: left for leftclick, right for rightclick, middle for scrollwheel
        """

        self.nextData["mouseButtons"].append(key)

    def scroll(self, delta:int):
        """
        scroll the mouse up or down

        delta: amnt to scroll
        
        view (https://docs.circuitpython.org/projects/hid/en/latest/api.html#adafruit_hid.mouse.Mouse.move)
        """

        self.nextData["scroll"] = int(delta)

    def mouse(self, x:int, y:int): 
        """
        move the mouse in a RELATIVE x,y coordinate

        x: amount of pixels to move in the x direction (can be negative)
        y: amount of pixels to move in the y direction (can be negative)

        view (https://docs.circuitpython.org/projects/hid/en/latest/api.html#adafruit_hid.mouse.Mouse.move)
        """

        self.nextData["mouse"]["x"] = int(x)
        self.nextData["mouse"]["y"] = int(y)

    def sendData(self):
        """
        function to update data every x amount of times in a second (determined by __init__'s polling rate)

        meant to be ran in a seperate thread
        
        !!! DO NOT RUN THIS !!! if you want to send data immediately, use manualSend !!!
        """

        if self.polling != -1:
            delay = (60 / self.polling) * 0.5
            while True:
                print('moved data')
                if self.kill: return

                print(json.dumps(self.nextData))

                self.serial.stringSend(json.dumps(self.nextData))
                self.nextData = {
                    "key": None,
                    "modifiers": [],
                    "mouse": {
                        "x": 0,
                        "y": 0,
                    },
                    "scroll": 0,
                    "mouseButtons": []
                }

                time.sleep(delay)
        elif self.polling == 0:
            return
        else:
            old = json.dumps(self.nextData)
            while True:
                if self.kill: return

                if json.dumps(self.nextData) == old:
                    pass
                else:
                    self.serial.stringSend(json.dumps(self.nextData))
                    self.nextData = {
                        "key": None,
                        "modifiers": [],
                        "mouse": {
                            "x": 0,
                            "y": 0,
                        },
                        "scroll": 0,
                        "mouseButtons": []
                    }
                    
                old = json.dumps(self.nextData)

                time.sleep(0.01)


    def manualSend(self):
        """
        force send the nextData object to run HID commands immediately
        """

        self.serial.stringSend(json.dumps(self.nextData))
        self.nextData = {
            "key": None,
            "modifiers": [],
            "mouse": {
                "x": 0,
                "y": 0,
            },
            "scroll": 0,
            "mouseButtons": []
        }
        self.serial.stringSend(json.dumps(self.nextData))
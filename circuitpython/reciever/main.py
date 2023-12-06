import time
import board
import busio
import digitalio
import usb_hid
import json
from adafruit_hid.mouse import Mouse
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

# Define the UART pins
rx_pin = board.GP8  # Receive pin
tx_pin = board.GP9  # Transmit pin

# Initialize the UART (Serial) communication
uart = busio.UART(rx_pin, tx_pin, baudrate=57600)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

try:
    kbd = Keyboard(usb_hid.devices)
    layout = KeyboardLayoutUS(kbd)
    mouse = Mouse(usb_hid.devices)
except:
    raise

def uartCallback(data):
    if data and data != b'\x00':
        return True
    else:
        return False
    
def executeKeystroke(k:str, modifiers:list=[]):
    if not k:
        return False


    for x in modifiers:
        print(x)
        if x == "Control":
            kbd.press(Keycode.LEFT_CONTROL)
        elif x == "Alt":
            kbd.press(Keycode.LEFT_ALT)
        elif x == "Meta":
            kbd.press(Keycode.LEFT_GUI)
        elif x == "Shift":
            kbd.press(Keycode.LEFT_SHIFT)

    if len(k) == 1:
        layout.write(k[0])
    elif k == 'Enter':
        kbd.press(Keycode.ENTER)
    elif k == 'Escape':
        kbd.press(Keycode.ESCAPE)
    elif k == 'Backspace':
        kbd.press(Keycode.BACKSPACE)
    elif k == 'Tab':
        kbd.press(Keycode.TAB)
    elif k == ' ' or k == "space":
        kbd.press(Keycode.SPACEBAR)
    elif k == '-':
        kbd.press(Keycode.MINUS)
    elif k == '=':
        kbd.press(Keycode.EQUALS)
    elif k == '{':
        kbd.press(Keycode.LEFT_BRACKET)
    elif k == '}':
        kbd.press(Keycode.RIGHT_BRACKET)
    elif k == '\\':
        kbd.press(Keycode.BACKSLASH)
    elif k == '#':
        kbd.press(Keycode.POUND)
    elif k == ';':
        kbd.press(Keycode.SEMICOLON)
    elif k == '"':
        kbd.press(Keycode.QUOTE)
    elif k == '~':
        kbd.press(Keycode.GRAVE_ACCENT)
    elif k == ',':
        kbd.press(Keycode.COMMA)
    elif k == '.':
        kbd.press(Keycode.PERIOD)
    elif k == '/':
        kbd.press(Keycode.FORWARD_SLASH)
    elif k == "CapsLock":
        kbd.press(Keycode.CAPS_LOCK)
    elif k == 'PrtScn' or k == 'PRINT_SCREEN' or k == 'PRINTSCREEN':
        kbd.press(Keycode.PRINT_SCREEN)
    elif k == 'SCROLL' or k == 'SCROLL_LOCK' or k == 'ScrollLock':
        kbd.press(Keycode.SCROLL_LOCK)
    elif k == 'Pause' or k == 'BREAK':
        kbd.press(Keycode.PAUSE)
    elif k == 'Insert':
        kbd.press(Keycode.INSERT)
    elif k == 'Home':
        kbd.press(Keycode.HOME)
    elif k == 'PgUp' or k == 'PAGEUP':
        kbd.press(Keycode.PAGE_UP)
    elif k == 'Delete':
        kbd.press(Keycode.DELETE)
    elif k == 'End':
        kbd.press(Keycode.END)
    elif k == 'PgDown' or k == 'PAGEDOWN':
        kbd.press(Keycode.PAGE_DOWN)
    elif k == 'ArrowRight':
        kbd.press(Keycode.RIGHT_ARROW)
    elif k == 'ArrowLeft':
        kbd.press(Keycode.LEFT_ARROW)
    elif k == 'ArrowDown':
        kbd.press(Keycode.DOWN_ARROW)
    elif k == 'ArrowUp':
        kbd.press(Keycode.UP_ARROW)
    elif k == 'NUM' or k == 'NUM_LOCK' or k == 'NUMLOCK':
        kbd.press(Keycode.NUM_LOCK)
    elif k == 'APPLICATION' or k == 'MENU':
        kbd.press(Keycode.APPLICATION)
    elif k == 'Control':
        kbd.press(Keycode.LEFT_CONTROL)
    elif k == 'Shift':
        kbd.press(Keycode.LEFT_SHIFT)
    elif k == 'Meta':
        kbd.press(Keycode.LEFT_GUI)
    elif k == 'F1':
        kbd.press(Keycode.F1)
    elif k == 'F2':
        kbd.press(Keycode.F2)
    elif k == 'F3':
        kbd.press(Keycode.F3)
    elif k == 'F4':
        kbd.press(Keycode.F4)
    elif k == 'F5':
        kbd.press(Keycode.F5)
    elif k == 'F6':
        kbd.press(Keycode.F6)
    elif k == 'F7':
        kbd.press(Keycode.F7)
    elif k == 'F8':
        kbd.press(Keycode.F8)
    elif k == 'F9':
        kbd.press(Keycode.F9)
    elif k == 'F10':
        kbd.press(Keycode.F10)
    elif k == 'F11':
        kbd.press(Keycode.F11)
    elif k == 'F12':
        kbd.press(Keycode.F12)
    elif k == 'F13':
        kbd.press(Keycode.F13)
    elif k == 'F14':
        kbd.press(Keycode.F14)
    elif k == 'F15':
        kbd.press(Keycode.F15)
    elif k == 'F16':
        kbd.press(Keycode.F16)
    elif k == 'F17':
        kbd.press(Keycode.F17)
    elif k == 'F18':
        kbd.press(Keycode.F18)
    elif k == 'F19':
        kbd.press(Keycode.F19)

    kbd.release_all()

if __name__ == "__main__":
    # Echo the received data back over UART

    uart.write(b"\x03")

    while True:

        data = uart.readline()

        if uartCallback(data):
            try:
                jData = json.loads(data.decode('ascii').strip())
            except:
                continue

            print(data)
            
            try:
                # parse mouse
                mouse.move(int(jData["mouse"]["x"]), int(jData["mouse"]["y"]), int(jData["scroll"]))

                # parse mouse clicks
                for x in jData["mouseButtons"]:
                    if x == "left":
                        mouse.click(mouse.LEFT_BUTTON)
                    elif x == "right":
                        mouse.click(mouse.RIGHT_BUTTON)
                    elif x == "middle":
                        mouse.click(mouse.MIDDLE_BUTTON)
                
                # parse keystrokes
                executeKeystroke(jData["key"], modifiers=jData["modifiers"])
            except:
                pass

        time.sleep(0.01)  # Small delay to avoid excessive looping

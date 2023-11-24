import time
import board
import busio
import usb_cdc
import digitalio

# Define the UART pins
BAUD_RATE = 57600

rx_pin = board.GP8  # Receive pin
tx_pin = board.GP9  # Transmit pin


# Initialize the UART (Serial) communication
uart = busio.UART(rx_pin, tx_pin, baudrate=57600)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
serial = usb_cdc.data


def uartCallback(data):
    if data and data != b'\x00':
        return True
    else:
        return False
    
def readTill(serial, end=["\r", "\n"]):
    chars = []

    while True:
        a = serial.read(1).decode('ascii')
        if a in end:
            return ''.join(chars)
        
        chars.append(a)

while True:
    # Check if there is data available on USB serial
    if serial.in_waiting > 0:
        #data = serial.read(1)  # Read up to 64 bytes from USB serial
        data = serial.readline()

        # Print the received data
        print("Received from USB serial:", data)

        uart.write(data)

    # Check if there is data available on UART
    if uart.in_waiting > 0:
        data = uart.read(1)  # Read one byte from UART

        # Print the received data
        print("Received from UART:", data)

        if uartCallback(data):
            # Forward the received data to USB serial
            serial.write(data)

    time.sleep(0.01)  # Small delay to avoid excessive looping
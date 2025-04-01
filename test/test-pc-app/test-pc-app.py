# Test app. Work with modbus. Read array, write array and read again to validate
# uses 2nd com port in thse system (suppose 1st is used by arduino serial monitor)

import serial.tools.list_ports
from pymodbus.client import ModbusSerialClient

# Automatically find the first available serial port
def find_first_serial_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return None
    return ports[1].device  # Example: 'COM3', 'COM5', etc. - use second [1] port in the system

# Main code
serial_port = find_first_serial_port()
if serial_port is None:
    exit()

print(f"Using serial port: {serial_port}")

client = ModbusSerialClient(
    port=serial_port,
    baudrate=9600,
    stopbits=1,
    bytesize=8,
    parity='N',
    timeout=1,
)

# !! NOTE on each connect my arduino resets. most likely because
# Most USB-to-Serial adapters (and Arduino, especially the Mega 2560)
# automatically reboot when the COM port is opened. This behavior is caused by the DTR
# (Data Terminal Ready) line, which "pulls" the RESET pin on the Arduino
# through the capacitor every time the connection is opened.
# TODO use another port - non USB.
if not client.connect():
    print(f"Failed to connect to {serial_port}")
    exit()

UNIT_ID = 1
START_ADDRESS = 10
NUM_REGISTERS = 6

print(f"connected")

# --- Read array from Arduino ---
response = client.read_holding_registers(address=START_ADDRESS, count=NUM_REGISTERS, slave=UNIT_ID)
if not response.isError():
    values = response.registers
    print("Read from Arduino:", values)
else:
    print("Read error:", response)

# --- Write new array to Arduino ---
# the 0 element will be used to set in servo. use 500..2500 value.
new_values = [1500, 1500, 1500, 1500, 1500, 1500]
#write_response = client.write_registers(address=START_ADDRESS, values=new_values, slave=UNIT_ID)
write_response = client.write_registers(address=START_ADDRESS, values=new_values, slave=UNIT_ID)
if write_response.isError():
    print("Write error:", write_response)
else:
    print("New array written to Arduino:", new_values)

# --- Verify written data ---
verify = client.read_holding_registers(address=START_ADDRESS, count=NUM_REGISTERS, slave=UNIT_ID)
if not verify.isError():
    print("Verification read:", verify.registers)
else:
    print("Verification error:", verify)

client.close()
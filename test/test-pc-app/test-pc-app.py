import serial.tools.list_ports
import time
from pymodbus.client import ModbusSerialClient

# Automatically find the first available serial port
def find_first_serial_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return None
    return ports[0].device  # Example: 'COM3', 'COM5', etc.

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
    timeout=1
)

if not client.connect():
    print(f"Failed to connect to {serial_port}")
    exit()

UNIT_ID = 1
READY_FLAG_ADDRESS = 0
START_ADDRESS = 10
NUM_REGISTERS = 6

# --- Wait for Arduino to be ready ---
print("Waiting for device to be ready...")
ready = False
for _ in range(10):
    response = client.read_holding_registers(address=READY_FLAG_ADDRESS, count=1, slave=UNIT_ID)
    if not response.isError() and response.registers[0] == 1:
        ready = True
        break
    time.sleep(0.5)

if not ready:
    print("Device not ready. Exiting.")
    client.close()
    exit()

print("Device is ready.")

# --- Read array from Arduino ---
response = client.read_holding_registers(address=START_ADDRESS, count=NUM_REGISTERS, slave=UNIT_ID)
if not response.isError():
    values = response.registers
    print("Read from Arduino:", values)
else:
    print("Read error:", response)

# --- Write new array to Arduino ---
new_values = [100, 200, 300, 400, 500, 600]
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
import tkinter as tk
from tkinter import ttk
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
import serial.tools.list_ports

# Constants
LOGICAL_MIN = 500
LOGICAL_MAX = 2500
MODBUS_UNIT_ID = 1

VALUES_ACTUAL_ADDR = 10
VALUES_MIN_ADDR = 20
VALUES_MAX_ADDR = 30

SERVO_NAMES = ["yaw", "horizontal", "vertical", "pitch", "twist", "grab"]

class ServoControlGroup:
    def __init__(self, parent, name, index, write_callback):
        self.index = index
        self.write_callback = write_callback

        self.frame = ttk.LabelFrame(parent, text=name)
        self.frame.pack(fill='x', padx=5, pady=2)

        # Initial value
        initial_value = (LOGICAL_MIN + LOGICAL_MAX) // 2
        self.value_var = tk.IntVar(value=initial_value)

        # Slider
        self.scale = ttk.Scale(
            self.frame, from_=LOGICAL_MIN, to=LOGICAL_MAX,
            orient='horizontal', command=self.on_slider_change
        )
        self.scale.set(initial_value)
        self.scale.pack(fill='x', padx=5, side='left', expand=True)

        # Entry field
        self.entry = ttk.Entry(self.frame, width=5, textvariable=self.value_var)
        self.entry.pack(side='left', padx=5)
        self.entry.bind("<Return>", self.on_entry_change)

        # Set Min/Max buttons
        self.btn_set_min = ttk.Button(self.frame, text="Set Min", command=self.set_min)
        self.btn_set_min.pack(side='left', padx=2)

        self.btn_set_max = ttk.Button(self.frame, text="Set Max", command=self.set_max)
        self.btn_set_max.pack(side='left', padx=2)

    def on_slider_change(self, value):
        val = int(float(value))
        self.value_var.set(val)
        self.write_callback("values_actual", VALUES_ACTUAL_ADDR + self.index, val)

    def on_entry_change(self, event):
        try:
            val = int(self.entry.get())
            if LOGICAL_MIN <= val <= LOGICAL_MAX:
                self.scale.set(val)
                self.write_callback("values_actual", VALUES_ACTUAL_ADDR + self.index, val)
            else:
                raise ValueError()
        except ValueError:
            print(f"Invalid input for servo {self.index}")

    def set_min(self):
        val = self.value_var.get()
        self.write_callback("values_min", VALUES_MIN_ADDR + self.index, val)

    def set_max(self):
        val = self.value_var.get()
        self.write_callback("values_max", VALUES_MAX_ADDR + self.index, val)

    def update_value(self, val):
        self.value_var.set(val)
        self.scale.set(val)

class ModbusServoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus Servo Control")
        self.client = None

        self.setup_ui()

    def setup_ui(self):
        # Top frame for COM port selection
        top_frame = ttk.Frame(self.root)
        top_frame.pack(pady=5, padx=5, fill='x')

        ttk.Label(top_frame, text="COM port:").pack(side='left')

        self.combobox = ttk.Combobox(top_frame, state='readonly')
        self.combobox['values'] = self.get_serial_ports()
        self.combobox.bind("<<ComboboxSelected>>", self.on_port_selected)
        self.combobox.pack(side='left', padx=5)

        self.status_label = tk.Label(top_frame, text="not available", bg='red', fg='white', width=15)
        self.status_label.pack(side='left', padx=10)

        # Tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill='both', expand=True)

        # Manual tab
        self.manual_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.manual_tab, text="Manual")

        self.servo_controls = []
        for i, name in enumerate(SERVO_NAMES):
            group = ServoControlGroup(self.manual_tab, name, i, self.write_register)
            self.servo_controls.append(group)

        # Script tab placeholder
        self.script_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.script_tab, text="Script")

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def on_port_selected(self, event):
        port = self.combobox.get()
        if not port:
            self.set_status(False)
            return

        self.client = ModbusClient(method='rtu', port=port, baudrate=9600, timeout=1,
                                   stopbits=1, bytesize=8, parity='N')
        if not self.client.connect():
            self.set_status(False)
            return

        try:
            result = self.client.read_holding_registers(address=VALUES_ACTUAL_ADDR, count=6, unit=MODBUS_UNIT_ID)
            if result.isError():
                self.set_status(False)
                print("error read values_actual")
            else:
                values = result.registers
                print(f"got values_actual [0..5] {', '.join(map(str, values))}")
                for i, val in enumerate(values):
                    self.servo_controls[i].update_value(val)
                self.set_status(True)
        except Exception as e:
            self.set_status(False)
            print("error read values_actual:", e)
        finally:
            self.client.close()

    def set_status(self, is_ready):
        if is_ready:
            self.status_label.config(text="ready", bg='green')
        else:
            self.status_label.config(text="not available", bg='red')

    def write_register(self, reg_type, address, value):
        print(f"send {reg_type} [{address % 10}] {value}")
        try:
            self.client = ModbusClient(method='rtu', port=self.combobox.get(), baudrate=9600, timeout=1,
                                       stopbits=1, bytesize=8, parity='N')
            if self.client.connect():
                result = self.client.write_register(address=address, value=value, unit=MODBUS_UNIT_ID)
                if result.isError():
                    print(f"error send {reg_type} [{address % 10}] {value}")
                self.client.close()
        except Exception as e:
            print(f"error send {reg_type} [{address % 10}] {value} -> {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusServoApp(root)
    root.mainloop()

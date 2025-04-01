import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
import serial.tools.list_ports
import json
import threading
import time

# Constants
LOGICAL_MIN = 0
LOGICAL_MAX = 999
ACTUAL_MIN = 500
ACTUAL_MAX = 2500

MODBUS_UNIT_ID = 1

VALUES_LOGICAL_ADDR = 100
VALUES_ACTUAL_ADDR = 10
VALUES_MIN_ADDR = 20
VALUES_MAX_ADDR = 30

SERVO_NAMES = ["yaw", "horizontal", "vertical", "pitch", "twist", "grab"]


class ServoControlGroup:
    debounce_timers = {}

    def __init__(self, parent, name, index, write_callback):
        self.index = index
        self.write_callback = write_callback

        self.frame = ttk.LabelFrame(parent, text=name)
        self.frame.pack(fill='x', padx=5, pady=2)

        initial_value = (ACTUAL_MIN + ACTUAL_MAX) // 2
        self.value_var = tk.IntVar(value=initial_value)

        self.scale = ttk.Scale(
            self.frame, from_=ACTUAL_MIN, to=ACTUAL_MAX,
            orient='horizontal', command=self.on_slider_change
        )
        self.scale.set(initial_value)
        self.scale.pack(fill='x', padx=5, side='left', expand=True)

        self.entry = ttk.Entry(self.frame, width=5, textvariable=self.value_var)
        self.entry.pack(side='left', padx=5)
        self.entry.bind("<Return>", self.on_entry_change)

        self.btn_set_min = ttk.Button(self.frame, text="Set Min", command=self.set_min)
        self.btn_set_min.pack(side='left', padx=2)

        self.btn_set_max = ttk.Button(self.frame, text="Set Max", command=self.set_max)
        self.btn_set_max.pack(side='left', padx=2)

    def on_slider_change(self, value):
        val = int(float(value))
        if self.value_var.get() == val:
            return
        self.value_var.set(val)

        key = f"servo_{self.index}"
        if key in ServoControlGroup.debounce_timers:
            ServoControlGroup.debounce_timers[key].cancel()

        def delayed_send():
            self.write_callback("values_actual", VALUES_ACTUAL_ADDR + self.index, val)

        timer = threading.Timer(0.1, delayed_send)
        ServoControlGroup.debounce_timers[key] = timer
        timer.start()

    def on_entry_change(self, event):
        try:
            val = int(self.entry.get())
            if ACTUAL_MIN <= val <= ACTUAL_MAX:
                self.scale.set(val)
                self.write_callback("values_actual", VALUES_ACTUAL_ADDR + self.index, val)
        except ValueError:
            pass

    def set_min(self):
        val = self.value_var.get()
        self.write_callback("values_min", VALUES_MIN_ADDR + self.index, val)

    def set_max(self):
        val = self.value_var.get()
        self.write_callback("values_max", VALUES_MAX_ADDR + self.index, val)

    def update_value(self, val):
        self.value_var.set(val)
        self.scale.set(val)


class ScriptTab:
    def __init__(self, parent, write_logical_callback, write_logical_array_callback):
        self.parent = parent
        self.write_logical_callback = write_logical_callback
        self.write_logical_array_callback = write_logical_array_callback
        self.script_data = []
        self.running = False
        self.slider_debounce_timers = {}
        self.setup_ui()

    def setup_ui(self):
        top_frame = ttk.Frame(self.parent)
        top_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(top_frame, text="Load", command=self.load_script).pack(side="left", padx=2)
        ttk.Button(top_frame, text="Save", command=self.save_script).pack(side="left", padx=2)

        table_frame = ttk.Frame(self.parent)
        table_frame.pack(fill="both", expand=True, padx=5)
        self.table = ttk.Treeview(table_frame, columns=("data",), show="headings")
        self.table.heading("data", text="Script Row")
        self.table.pack(side="left", fill="both", expand=True)

        self.table_scroll = ttk.Scrollbar(table_frame, command=self.table.yview)
        self.table_scroll.pack(side="right", fill="y")
        self.table.config(yscrollcommand=self.table_scroll.set)

        self.table.bind("<<TreeviewSelect>>", self.on_tree_select)

        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill="x", pady=5, padx=5)

        self.btn_step = ttk.Button(control_frame, text="Step", command=self.step)
        self.btn_step.pack(side="left", padx=2)
        self.btn_go = ttk.Button(control_frame, text="Go", command=self.go)
        self.btn_go.pack(side="left", padx=2)
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=self.stop)
        self.btn_stop.pack(side="left", padx=2)
        self.btn_add = ttk.Button(control_frame, text="Add-after", command=self.add_after)
        self.btn_update = ttk.Button(control_frame, text="Update", command=self.update_selected)
        self.btn_update.pack(side="left", padx=2)
        self.btn_delete = ttk.Button(control_frame, text="Delete", command=self.delete_selected)
        self.btn_delete.pack(side="left", padx=2)
        self.btn_add.pack(side="left", padx=10)

        self.servo_controls = {}
        servo_frame = ttk.Frame(self.parent)
        servo_frame.pack(fill="x", pady=5)
        for name in SERVO_NAMES:
            group = ttk.LabelFrame(servo_frame, text=name)
            group.pack(side="left", padx=5, pady=5)
            var = tk.IntVar(value=499)
            entry = ttk.Entry(group, width=5, textvariable=var)
            entry.pack()
            scale = ttk.Scale(group, from_=LOGICAL_MIN, to=LOGICAL_MAX, orient="vertical")
            scale.set(499)
            scale.pack()
            self.servo_controls[name] = {"var": var, "scale": scale, "entry": entry, "updating": False}
            scale.config(command=lambda val, n=name: self.on_slider_change(n, val))
            entry.bind("<Return>", lambda e, n=name: self.on_entry_change(n))
            scale.config(command=lambda val, n=name: self.on_slider_change(n, val))
            entry.bind("<Return>", lambda e, n=name: self.on_entry_change(n))

        delay_frame = ttk.Frame(self.parent)
        delay_frame.pack(pady=5)
        ttk.Label(delay_frame, text="delay (ms):").pack(side="left")
        self.delay_var = tk.IntVar(value=2000)
        self.delay_entry = ttk.Entry(delay_frame, width=8, textvariable=self.delay_var)
        self.delay_entry.pack(side="left")

        default_entry = {"servos": {name: 499 for name in SERVO_NAMES}, "delay": 2000}
        self.script_data.append(default_entry)
        self.refresh_table()
        self.update_step_button()

    def refresh_table(self):
        self.table.delete(*self.table.get_children())
        for i, row in enumerate(self.script_data, start=1):
            self.table.insert("", "end", iid=str(i), values=(json.dumps(row),))
        self.update_step_button()

    def load_script(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.txt *.json")])
        if not path:
            return
        try:
            with open(path, "r") as f:
                self.script_data = json.load(f)
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load script: {e}")

    def save_script(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, "w") as f:
                json.dump(self.script_data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save script: {e}")

    def on_slider_change(self, name, value):
        if self.servo_controls[name].get("updating"):
            return

        val = int(float(value))
        previous_val = self.servo_controls[name]["var"].get()
        if val == previous_val:
            return

        self.servo_controls[name]["var"].set(val)

        # Cancel previous timer if exists
        if name in self.slider_debounce_timers:
            self.slider_debounce_timers[name].cancel()

        # Start new debounce timer
        def delayed_send():
            self.write_logical_callback(name, val)

        timer = threading.Timer(0.1, delayed_send)
        self.slider_debounce_timers[name] = timer
        timer.start()

        self.write_logical_callback(name, val)

    def on_entry_change(self, name):
        if self.servo_controls[name].get("updating"):
            return
        try:
            val = int(self.servo_controls[name]["entry"].get())
            val = max(LOGICAL_MIN, min(LOGICAL_MAX, val))
            self.servo_controls[name]["var"].set(val)
            self.servo_controls[name]["scale"].set(val)
            self.write_logical_callback(name, val)
        except ValueError:
            pass


        except ValueError:
            pass
            self.write_logical_callback(name, val)
        except ValueError:
            pass
        except ValueError:
            pass

    def add_after(self):
        selected = self.table.selection()
        if not selected:
            index = len(self.script_data)
        else:
            all_iids = self.table.get_children()
            index = all_iids.index(selected[0]) + 1

        new_row = {
            "servos": {name: self.servo_controls[name]["var"].get() for name in SERVO_NAMES},
            "delay": self.delay_var.get()
        }
        self.script_data.insert(index, new_row)
        self.refresh_table()
        if self.table.get_children():
            self.table.selection_set(self.table.get_children()[index if index < len(self.script_data) else -1])

    def update_step_button(self):
        if not self.table.selection():
            self.btn_step.config(state="normal")

    def step(self):
        all_iids = self.table.get_children()
        selected = self.table.selection()
        if not all_iids:
            return
        if not selected:
            next_index = 0
        else:
            current_index = all_iids.index(selected[0])
            if current_index + 1 >= len(all_iids):
                self.running = False  # End of script
                return
            next_index = current_index + 1

        next_iid = all_iids[next_index]
        self.table.selection_set(next_iid)
        # Treeview selection change will trigger on_tree_select automatically
        # Removed redundant focus to avoid duplicate event triggers

    def go(self):
        if self.running:
            return
        self.running = True

        def run_loop():
            while self.running:
                self.step()
                if not self.running:
                    break
                time.sleep(self.delay_var.get() / 1000.0)
            self.running = False

        threading.Thread(target=run_loop, daemon=True).start()

    def send_current_row(self):
        selected = self.table.selection()
        if not selected:
            return
        item = self.table.item(selected[0])
        try:
            row = json.loads(item['values'][0])
            values = [row['servos'].get(name, 499) for name in SERVO_NAMES]
            self.write_logical_array_callback(values)
        except Exception as e:
            print("error sending current row ->", e)

    def on_tree_select(self, event):
        selected = self.table.selection()
        if not selected:
            return
        item = self.table.item(selected[0])
        try:
            row = json.loads(item['values'][0])
            for name in SERVO_NAMES:
                value = row['servos'].get(name, 499)
                self.servo_controls[name]["updating"] = True
                self.servo_controls[name]['var'].set(value)
                self.servo_controls[name]['scale'].set(value)
                self.servo_controls[name]['entry'].delete(0, tk.END)
                self.servo_controls[name]['entry'].insert(0, str(value))
                self.servo_controls[name]["updating"] = False
            self.delay_var.set(row.get('delay', 2000))
            self.send_current_row()
            # self.send_current_row()
        except Exception as e:
            print("error parsing selected row ->", e)

    def delete_selected(self):
        selected = self.table.selection()
        if not selected:
            return
        index = self.table.index(selected[0])
        if len(self.script_data) <= 1:
            print("Cannot delete last remaining row")
            return
        self.script_data.pop(index)
        self.refresh_table()
        remaining = self.table.get_children()
        if remaining:
            new_index = max(0, index - 1)
            self.table.selection_set(remaining[new_index])

    def update_selected(self):
        selected = self.table.selection()
        if not selected:
            return
        try:
            index = self.table.index(selected[0])
            values = {name: self.servo_controls[name]['var'].get() for name in SERVO_NAMES}
            delay_val = self.delay_var.get()
            full = {"servos": values, "delay": delay_val}
            self.script_data[index] = full
            self.refresh_table()
            self.table.selection_set(self.table.get_children()[index])
        except Exception as e:
            print("error updating row ->", e)

    def stop(self):
        self.running = False


class ModbusServoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus Servo Control")
        self.client = None
        self.setup_ui()

    def setup_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(pady=5, padx=5, fill='x')

        ttk.Label(top_frame, text="COM port:").pack(side='left')
        self.combobox = ttk.Combobox(top_frame, state='readonly')
        self.combobox['values'] = self.get_serial_ports()
        self.combobox.bind("<<ComboboxSelected>>", self.on_port_selected)
        self.combobox.pack(side='left', padx=5)

        self.status_label = tk.Label(top_frame, text="not available", bg='red', fg='white', width=15)
        self.status_label.pack(side='left', padx=10)

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill='both', expand=True)

        self.manual_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.manual_tab, text="Manual")
        self.script_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.script_tab, text="Script")

        self.servo_controls = []
        for i, name in enumerate(SERVO_NAMES):
            group = ServoControlGroup(self.manual_tab, name, i, self.write_register)
            self.servo_controls.append(group)

        self.script = ScriptTab(self.script_tab, self.write_logical_named, self.write_logical_array)

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def on_port_selected(self, event):
        port = self.combobox.get()
        if not port:
            self.set_status(False)
            return
        self.client = ModbusClient(port=port, baudrate=9600, timeout=1,
                                   stopbits=1, bytesize=8, parity='N')
        if not self.client.connect():
            self.set_status(False)
            print("error read values_actual -> connect failed")
            return
        try:

            result = self.client.read_holding_registers(address=VALUES_ACTUAL_ADDR, count=6)
            if hasattr(result, "registers"):
                values = result.registers
                print("got values_actual [0..5]", ", ".join(map(str, values)))
                for i, val in enumerate(values):
                    self.servo_controls[i].update_value(val)
                self.set_status(True)
            else:
                print("error read values_actual ->", result)
                self.set_status(False)
        except Exception as e:
            print("error read values_actual ->", e)
            self.set_status(False)
        finally:
            self.client.close()

    def set_status(self, is_ready):
        if is_ready:
            self.status_label.config(text="ready", bg='green')
        else:
            self.status_label.config(text="not available", bg='red')

    def write_register(self, reg_type, address, value):
        port = self.combobox.get()
        if not port:
            print(f"error send {reg_type} [{address % 10}] {value} -> port not selected")
            return
        print(f"send {reg_type} [{address % 10}] {value}")
        try:
            self.client = ModbusClient(
                port=port, baudrate=9600, timeout=1,
                stopbits=1, bytesize=8, parity='N')
            if self.client.connect():
                self.client.write_register(address=address, value=value)
                self.client.close()
            else:
                print(f"error send {reg_type} [{address % 10}] {value} -> connect failed")
        except Exception as e:
            print(f"error send {reg_type} [{address % 10}] {value} -> {e}")

    def write_logical_named(self, name, value):
        if name in SERVO_NAMES:
            index = SERVO_NAMES.index(name)
            self.write_register("values_logical", VALUES_LOGICAL_ADDR + index, value)

    def write_logical_array(self, values):
        port = self.combobox.get()
        if not port:
            print("send values_logical [0..5]", ", ".join(map(str, values)), " -> port not selected")
            return
        print("send values_logical [0..5]", ", ".join(map(str, values)))
        try:
            self.client = ModbusClient(port=port, baudrate=9600, timeout=1,
                                       stopbits=1, bytesize=8, parity='N')
            if self.client.connect():

                self.client.write_registers(address=VALUES_LOGICAL_ADDR, values=values)
                self.client.close()
            else:
                print("error send values_logical [0..5] -> connect failed")
        except Exception as e:
            print("error send values_logical [0..5] ->", e)


if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusServoApp(root)
    root.mainloop()

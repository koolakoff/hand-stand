import tkinter as tk
from tkinter import ttk
import json
import serial
import serial.tools.list_ports
import threading
import time

# Список параметров
params = ["yaw", "horizontal", "vertical", "twist", "grab", "extra"]

MIN_VAL = 0
MAX_VAL = 99

class ServoControlUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Servo Arm Controller")
        self.geometry("600x550")
        self.resizable(False, False)

        self.variables = {}
        self.serial_thread = None
        self.serial_running = False
        self.serial_instance = None

        for idx, param in enumerate(params):
            self._create_control_row(idx, param)

        self._create_command_section(len(params))

    def _create_control_row(self, row, param_name):
        var = tk.IntVar(value=50)
        self.variables[param_name] = var

        label = ttk.Label(self, text=param_name.capitalize(), width=12)
        label.grid(row=row, column=0, padx=5, pady=5, sticky="w")

        slider = ttk.Scale(
            self,
            from_=MIN_VAL,
            to=MAX_VAL,
            orient="horizontal",
            variable=var,
            command=lambda val, v=var, e=None: self._update_entry(v, entry)
        )
        slider.grid(row=row, column=1, padx=5, pady=5, sticky="ew")

        entry = ttk.Entry(self, width=5)
        entry.insert(0, str(var.get()))
        entry.grid(row=row, column=2, padx=5, pady=5)

        entry.bind("<Return>", lambda event, v=var, e=entry: self._update_var_from_entry(v, e))

    def _create_command_section(self, row):
        # Выбор COM порта
        ttk.Label(self, text="Select COM port:").grid(row=row, column=0, padx=5, sticky="w")
        self.combobox = ttk.Combobox(self, values=self._get_serial_ports(), state="readonly", width=20)
        self.combobox.grid(row=row, column=1, columnspan=2, pady=5, sticky="w")
        if self.combobox["values"]:
            self.combobox.current(0)

        # Кнопка отправки команды
        button = ttk.Button(self, text="Generate command", command=self._generate_command)
        button.grid(row=row+1, column=0, columnspan=3, pady=10)

        # Поле вывода команды
        self.output_field = tk.Text(self, height=4, width=60, state="disabled")
        self.output_field.grid(row=row+2, column=0, columnspan=3, padx=10, pady=5)

        # Поле логов входящих сообщений
        ttk.Label(self, text="Serial Log:").grid(row=row+3, column=0, columnspan=3, padx=10, sticky="w")

        log_frame = tk.Frame(self)
        log_frame.grid(row=row+4, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        self.log_field = tk.Text(log_frame, height=3, width=60, state="disabled", wrap="none")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_field.yview)
        self.log_field.configure(yscrollcommand=scrollbar.set)

        self.log_field.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Запуск фонового потока
        self.after(100, self._start_serial_reader)

    def _get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def _generate_command(self):
        command = {name: self.variables[name].get() for name in self.variables}
        json_str = json.dumps(command)
        print("Generated:", json_str)
        self._display_output(json_str)
        self._send_serial(json_str)

    def _display_output(self, text):
        self.output_field.config(state="normal")
        self.output_field.delete(1.0, tk.END)
        self.output_field.insert(tk.END, text)
        self.output_field.config(state="disabled")

    def _log_input(self, line):
        self.log_field.config(state="normal")
        self.log_field.insert(tk.END, line + "\n")
        self.log_field.see(tk.END)
        self.log_field.config(state="disabled")

    def _send_serial(self, text):
        port = self.combobox.get()
        if not port:
            print("No COM port selected.")
            return
        try:
            with serial.Serial(port, 9600, timeout=1) as ser:
                ser.write((text + '\n').encode('utf-8'))
                print(f"Sent to {port}")
        except serial.SerialException as e:
            print(f"Failed to send to {port}: {e}")

    def _start_serial_reader(self):
        if self.serial_thread is None:
            self.serial_running = True
            self.serial_thread = threading.Thread(target=self._serial_read_loop, daemon=True)
            self.serial_thread.start()

    def _serial_read_loop(self):
        while self.serial_running:
            port = self.combobox.get()
            if not port:
                time.sleep(1)
                continue
            try:
                if self.serial_instance is None or not self.serial_instance.is_open:
                    self.serial_instance = serial.Serial(port, 9600, timeout=1)

                if self.serial_instance.in_waiting > 0:
                    line = self.serial_instance.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        print("received:", line)
                        self.after(0, self._log_input, line)
            except serial.SerialException:
                self.serial_instance = None
            time.sleep(0.1)

    def _update_entry(self, var, entry):
        entry.delete(0, tk.END)
        entry.insert(0, str(int(var.get())))

    def _update_var_from_entry(self, var, entry):
        try:
            value = int(entry.get())
            if MIN_VAL <= value <= MAX_VAL:
                var.set(value)
            else:
                raise ValueError
        except ValueError:
            entry.delete(0, tk.END)
            entry.insert(0, str(var.get()))

    def on_close(self):
        self.serial_running = False
        if self.serial_instance and self.serial_instance.is_open:
            self.serial_instance.close()
        self.destroy()

if __name__ == "__main__":
    app = ServoControlUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

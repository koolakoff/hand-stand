import tkinter as tk
from tkinter import ttk
import json

# Список параметров
params = ["yaw", "horizontal", "vertical", "twist", "grab", "extra"]

# Диапазон значений
MIN_VAL = 0
MAX_VAL = 99


class ServoControlUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Servo Arm Controller")
        self.geometry("500x400")
        self.resizable(False, False)

        self.variables = {}  # Для хранения значений параметров

        for idx, param in enumerate(params):
            self._create_control_row(idx, param)

        # Кнопка и поле вывода JSON команды
        self._create_command_section(len(params))

    def _create_control_row(self, row, param_name):
        # Переменная tkinter IntVar
        var = tk.IntVar(value=50)
        self.variables[param_name] = var

        # Метка
        label = ttk.Label(self, text=param_name.capitalize(), width=12)
        label.grid(row=row, column=0, padx=5, pady=5, sticky="w")

        # Слайдер
        slider = ttk.Scale(
            self,
            from_=MIN_VAL,
            to=MAX_VAL,
            orient="horizontal",
            variable=var,
            command=lambda val, v=var, e=None: self._update_entry(v, entry)
        )
        slider.grid(row=row, column=1, padx=5, pady=5, sticky="ew")

        # Текстовое поле
        entry = ttk.Entry(self, width=5)
        entry.insert(0, str(var.get()))
        entry.grid(row=row, column=2, padx=5, pady=5)

        # Обработчик изменения вручную
        entry.bind("<Return>", lambda event, v=var, e=entry: self._update_var_from_entry(v, e))

    def _create_command_section(self, row):
        # Кнопка генерации команды
        button = ttk.Button(self, text="Generate command", command=self._generate_command)
        button.grid(row=row, column=0, columnspan=3, pady=10)

        # Поле вывода JSON строки
        self.output_field = tk.Text(self, height=4, width=60, state="disabled")
        self.output_field.grid(row=row + 1, column=0, columnspan=3, padx=10, pady=5)

    def _generate_command(self):
        # Получение текущих значений
        command = {name: var.get() for name, var in self.variables.items()}
        json_str = json.dumps(command)

        # Вывод в консоль
        print(json_str)

        # Отображение в текстовом поле
        self.output_field.config(state="normal")
        self.output_field.delete(1.0, tk.END)
        self.output_field.insert(tk.END, json_str)
        self.output_field.config(state="disabled")

    def _update_entry(self, var, entry):
        """Обновление текста при движении слайдера"""
        entry.delete(0, tk.END)
        entry.insert(0, str(int(var.get())))

    def _update_var_from_entry(self, var, entry):
        """Обновление значения переменной при вводе в поле"""
        try:
            value = int(entry.get())
            if MIN_VAL <= value <= MAX_VAL:
                var.set(value)
            else:
                raise ValueError
        except ValueError:
            entry.delete(0, tk.END)
            entry.insert(0, str(var.get()))  # откат к текущему значению


if __name__ == "__main__":
    app = ServoControlUI()
    app.mainloop()

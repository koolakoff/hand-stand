# hand-stand
This is demo project that represents a system of control over a robotic arm. 
The project contains of:
- the [6-DOF robotic arm from Aliexpress](https://s.click.aliexpress.com/e/_onTxvrz) driven by PWM-controlled servos (DS3115 digital servo/MG996R analog servo)
- a Windows UI app (python + tkinter lib)
- [Arduino mega 2560 r3](https://s.click.aliexpress.com/e/_ooQZD0n) based controller
- for connection between controller and Windows app it is used
[Modbus RTU protocol](https://en.wikipedia.org/wiki/Modbus#Modbus_RTU) (over RS232). 
Used Arduino library [ModbusRTU by Alexander Emelianov](https://github.com/Emelianov/modbus-esp8266) and Python library `pymodbus`
<img src="https://github.com/user-attachments/assets/6529b6bf-a7a1-4956-8d6c-602a50b0b4b3" alt="schema" width="800"/>

Note, this project is slightly less than completely generated with help of ChatGPT:
- [Python UI app](https://chatgpt.com/share/67df3f7c-22ac-8003-bc4e-ac7ea6982ebe)
- [Arduino app, example of Python app modbus lib usage](https://chatgpt.com/share/67df3fd8-3cd4-8003-992e-2c174c5f28f8)

Libraries installation instructions
1. For install python lib use command `pip install pymodbus pyserial`
2. For install Arduino lib in Arduino studio run 
`Sketch`->`Include library`->`Manage Libraries...` search and install `ModbusRTU Alexander Emelianov`
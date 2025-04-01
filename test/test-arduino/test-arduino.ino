// Test app.
// test modbus and servo
// config servo on pin 2
// serial print on Serial (default serial port)
// modbus on Serial1 (tx: d18, rx: d19)

#include <ModbusRTU.h>
#include <Servo.h>

ModbusRTU mb;
Servo servo;

// === Constants ===
const uint8_t DEVICE_ID = 1;
const uint16_t REG_DATA_START = 10;
const uint8_t REG_DATA_COUNT = 6;

uint16_t data[REG_DATA_COUNT] = {500, 20, 30, 40, 50, 60};


// --- Write callback: update array from register write ---
uint16_t onHregSet(TRegister* reg, uint16_t val) {
  char buffer[64]; // print buffer
  uint16_t addr = reg->address.address;  // Safely cast TAddress to uint16_t
  uint16_t index = addr - REG_DATA_START;
  snprintf(buffer, sizeof(buffer), "set %d [%d]: %d", addr, index, val);
  Serial.println(buffer);
  if (index < REG_DATA_COUNT) {
    if (index == 0) {
      servo.writeMicroseconds(constrain(val, 500, 2500));
    }
    data[index] = val;
  }
  return val;  // Commit this value to the register
}

void setup() {
  // config debug print
  Serial.begin(9600);

  // config modbus
  Serial1.begin(9600);
  mb.begin(&Serial1);
  mb.setBaudrate(9600);
  mb.slave(DEVICE_ID);

  // Register holding registers from REG_DATA_START and initialize values
  for (uint8_t i = 0; i < REG_DATA_COUNT; i++) {
    uint16_t addr = REG_DATA_START + i;
    mb.addHreg(addr, data[i]);  // make each register writable and set initial value
  }
  mb.onSetHreg(REG_DATA_START, onHregSet, REG_DATA_COUNT);  // register write callback

  servo.attach(2);
  servo.writeMicroseconds(500);

  Serial.println("setup complete");
}

void loop() {
  mb.task();                    // Handle Modbus requests
  yield();
}

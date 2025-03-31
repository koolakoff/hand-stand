#include <ModbusRTU.h>

ModbusRTU mb;

// === Constants ===
const uint8_t DEVICE_ID = 1;
const uint16_t REG_READY = 0;
const uint16_t REG_DATA_START = 10;
const uint8_t REG_DATA_COUNT = 6;

uint16_t data[REG_DATA_COUNT] = {10, 20, 30, 40, 50, 60};

// --- Write callback: update array from register write ---
uint16_t onHregSet(TRegister* reg, uint16_t val) {
  uint16_t addr = *(uint16_t*)&reg->address;  // Safely cast TAddress to uint16_t
  uint16_t index = addr - REG_DATA_START;
  if (index < REG_DATA_COUNT) {
    data[index] = val;
  }
  return val;  // Commit this value to the register
}

void setup() {
  Serial.begin(9600);
  mb.begin(&Serial);
  mb.setBaudrate(9600);
  mb.slave(DEVICE_ID);

  mb.addHreg(REG_READY);         // readiness flag
  mb.Hreg(REG_READY, 0);         // not ready

  // Register holding registers from REG_DATA_START and initialize values
  for (uint8_t i = 0; i < REG_DATA_COUNT; i++) {
    uint16_t addr = REG_DATA_START + i;
    mb.addHreg(addr, data[i]);  // make each register writable and set initial value
    mb.onSetHreg(addr, onHregSet);  // register write callback
  }

  mb.Hreg(REG_READY, 1);         // ready
}

void loop() {
  mb.task();                    // Handle Modbus requests
  yield();
}

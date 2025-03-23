#include <ModbusRTU.h>
#include <EEPROM.h>
#include <Servo.h>

#define NUM_SERVOS 6
#define LOGICAL_MIN 0
#define LOGICAL_MAX 999

// Control arrays
uint16_t values_logical[NUM_SERVOS];   // Logical values (0..999)
uint16_t values_min[NUM_SERVOS];       // Min pulse width in microseconds
uint16_t values_max[NUM_SERVOS];       // Max pulse width in microseconds
uint16_t values_actual[NUM_SERVOS];    // Actual pulse width in microseconds

// Modbus addresses
const uint16_t ADDR_ACTUAL = 10;
const uint16_t ADDR_MIN = 20;
const uint16_t ADDR_MAX = 30;
const uint16_t ADDR_LOGICAL = 100;

// Servo setup
Servo servos[NUM_SERVOS];
const uint8_t servoPins[NUM_SERVOS] = {2, 3, 4, 5, 6, 7}; // D2 to D7

// Modbus setup
ModbusRTU mb;

bool cb(Modbus::FunctionCode fc, uint16_t addr, uint16_t length) {
  for (int i = 0; i < length; i++) {
    uint16_t val = mb.Hreg(addr + i);

    // Update actual values
    if (addr >= ADDR_ACTUAL && addr < ADDR_ACTUAL + NUM_SERVOS) {
      int idx = addr - ADDR_ACTUAL + i;
      values_actual[idx] = constrain(val, values_min[idx], values_max[idx]);
      values_logical[idx] = map(values_actual[idx], values_min[idx], values_max[idx], LOGICAL_MIN, LOGICAL_MAX);
      servos[idx].writeMicroseconds(values_actual[idx]);
    }

    // Update logical values
    else if (addr >= ADDR_LOGICAL && addr < ADDR_LOGICAL + NUM_SERVOS) {
      int idx = addr - ADDR_LOGICAL + i;
      values_logical[idx] = constrain(val, LOGICAL_MIN, LOGICAL_MAX);
      values_actual[idx] = map(values_logical[idx], LOGICAL_MIN, LOGICAL_MAX, values_min[idx], values_max[idx]);
      servos[idx].writeMicroseconds(values_actual[idx]);
    }

    // Update min values and save to EEPROM
    else if (addr >= ADDR_MIN && addr < ADDR_MIN + NUM_SERVOS) {
      int idx = addr - ADDR_MIN + i;
      values_min[idx] = val;
      EEPROM.put(idx * 2, values_min[idx]);
    }

    // Update max values and save to EEPROM
    else if (addr >= ADDR_MAX && addr < ADDR_MAX + NUM_SERVOS) {
      int idx = addr - ADDR_MAX + i;
      values_max[idx] = val;
      EEPROM.put(100 + idx * 2, values_max[idx]);
    }
  }
  return true;
}

void setup() {
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);

    // Load min and max values from EEPROM
    EEPROM.get(i * 2, values_min[i]);
    EEPROM.get(100 + i * 2, values_max[i]);

    // Default values if EEPROM is empty or invalid
    if (values_min[i] < 500 || values_min[i] > 2500) values_min[i] = 1000;
    if (values_max[i] < 500 || values_max[i] > 2500) values_max[i] = 2000;

    // Set initial values to midpoint
    values_actual[i] = (values_min[i] + values_max[i]) / 2;
    values_logical[i] = (LOGICAL_MIN + LOGICAL_MAX) / 2;
    servos[i].writeMicroseconds(values_actual[i]);
  }

  Serial.begin(9600);
  mb.begin(&Serial);
  mb.slave(1);

  mb.addHreg(ADDR_ACTUAL, values_actual, NUM_SERVOS);
  mb.addHreg(ADDR_MIN, values_min, NUM_SERVOS);
  mb.addHreg(ADDR_MAX, values_max, NUM_SERVOS);
  mb.addHreg(ADDR_LOGICAL, values_logical, NUM_SERVOS);

  mb.onSetHreg(cb);
}

void loop() {
  mb.task();
}

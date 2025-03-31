#include <ModbusRTU.h>
#include <EEPROM.h>
#include <Servo.h>

#define NUM_SERVOS 6
#define LOGICAL_MIN 0
#define LOGICAL_MAX 999
#define LOGICAL_DEFAULT 500
#define ACTUAL_MIN 500
#define ACTUAL_MAX 2500
#define ACTUAL_DEFAULT 1500

// Control arrays
uint16_t values_logical[NUM_SERVOS] = {};   // Logical values (0..999)
uint16_t values_min[NUM_SERVOS] = {};       // Min pulse width in microseconds
uint16_t values_max[NUM_SERVOS] = {};       // Max pulse width in microseconds
uint16_t values_actual[NUM_SERVOS] = {};    // Actual pulse width in microseconds

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

# TODO change to onHregSet() like in the example
bool cb(Modbus::FunctionCode fc, uint16_t addr, uint16_t length) {
  for (int i = 0; i < length; i++) {
    uint16_t val = mb.Hreg(addr + i);

    // Update actual values
    if (addr >= ADDR_ACTUAL && addr < ADDR_ACTUAL + NUM_SERVOS) {
      int idx = addr - ADDR_ACTUAL + i;
      values_actual[idx] = constrain(val, values_min[idx], values_max[idx]);
      values_logical[idx] = map(values_actual[idx], values_min[idx], values_max[idx], LOGICAL_MIN, LOGICAL_MAX);
      mb.Hreg(ADDR_ACTUAL, values_actual[i]);
      mb.Hreg(ADDR_LOGICAL, values_logical[i]);
      servos[idx].writeMicroseconds(values_actual[idx]);
    }

    // Update logical values
    else if (addr >= ADDR_LOGICAL && addr < ADDR_LOGICAL + NUM_SERVOS) {
      int idx = addr - ADDR_LOGICAL + i;
      values_logical[idx] = constrain(val, LOGICAL_MIN, LOGICAL_MAX);
      values_actual[idx] = map(values_logical[idx], LOGICAL_MIN, LOGICAL_MAX, values_min[idx], values_max[idx]);
      mb.Hreg(ADDR_ACTUAL, values_actual[i]);
      mb.Hreg(ADDR_LOGICAL, values_logical[i]);
      servos[idx].writeMicroseconds(values_actual[idx]);
    }

    // Update min values and save to EEPROM
    else if (addr >= ADDR_MIN && addr < ADDR_MIN + NUM_SERVOS) {
      int idx = addr - ADDR_MIN + i;
      values_min[idx] = val;
      mb.Hreg(ADDR_MIN, values_min[i]);
      EEPROM.put(idx * 2, values_min[idx]);
    }

    // Update max values and save to EEPROM
    else if (addr >= ADDR_MAX && addr < ADDR_MAX + NUM_SERVOS) {
      int idx = addr - ADDR_MAX + i;
      values_max[idx] = val;
      mb.Hreg(ADDR_MAX, values_max[i]);
      EEPROM.put(100 + idx * 2, values_max[idx]);
    }
  }
  return true;
}

void setup() {
  // setup modbus device
  Serial.begin(9600);
  mb.begin(&Serial);
  mb.slave(1);

  mb.addHreg(ADDR_ACTUAL, values_actual, NUM_SERVOS);
  mb.addHreg(ADDR_MIN, values_min, NUM_SERVOS);
  mb.addHreg(ADDR_MAX, values_max, NUM_SERVOS);
  mb.addHreg(ADDR_LOGICAL, values_logical, NUM_SERVOS);

  // setup initial values
  for (int i = 0; i < NUM_SERVOS; i++) {
    // Load min and max values from EEPROM
    EEPROM.get(i * 2, values_min[i]);
    EEPROM.get(100 + i * 2, values_max[i]);

    // Default values if EEPROM is empty or invalid
    if (values_min[i] < ACTUAL_MIN || values_min[i] > ACTUAL_MAX) values_min[i] = ACTUAL_MIN;
    if (values_max[i] < ACTUAL_MIN || values_max[i] > ACTUAL_MAX) values_max[i] = ACTUAL_MIN;

    // Set initial values to midpoint
    values_actual[i] = (values_min[i] + values_max[i]) / 2;
    values_logical[i] = (LOGICAL_MIN + LOGICAL_MAX) / 2;

    // Set corresponding registers
    // TODO better to set as an array but somewhy mb.Hreg(addr, array, len) does not work
    mb.Hreg(ADDR_ACTUAL, values_actual[i]);
    mb.Hreg(ADDR_MIN, values_min[i]);
    mb.Hreg(ADDR_MAX, values_max[i]);
    mb.Hreg(ADDR_LOGICAL, values_logical[i]);
  }
  mb.onSetHreg(cb);

  // setup servos
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].writeMicroseconds(values_actual[i]);
  }
}

void loop() {
  mb.task();
}

// servo_controller.ino
// Copyright (C) 2025 Petro Kulakov <https://github.com/koolakoff/hand-stand>
// This file is part of hand-stand project and is licensed under the GPLv3.
// See the LICENSE file in the root directory for full details.

// Servo arm controller for 6DOF robotic arm on PWM servos.
//
// Servo pins: {d2, d3, d4, d5, d6, d7}
//
// debug logging on Serial (tx: d1, rx: d0) Baudrate 9600
//
// Use ModbusRTU on Serial1 (tx: d18, rx: d19) Baudrate 9600
//   Registers:
//     - 10..15   - actual value of PWM control to be set on each servo in ms (500..2500)
//     - 20..25   - minimum allowed actual values in ms (500..2500)
//     - 30..35   - maximum allowed actual values in ms (500..2500)
//     - 100..105 - logical value of each servo (0..999).
//                  it is mapped to actual values in boundary of defined max/min:
//                  0   mapped to min allowed actual value
//                  999 mapped to max allowed actual value
//   Recommended workflow:
//     - set actual value for experimental find out end positions of each servo
//     - set min and max to define end position of each servo
//     - common flow control - use logical value (0..999) to control servo arm in limits defined on previous steps

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

// TODO change to onHregSet() like in the example
//bool cb(Modbus::FunctionCode fc, uint16_t addr, uint16_t length) {
uint16_t onHregSet(TRegister* reg, uint16_t val) {
  char buffer[64]; // print buffer
  uint16_t addr = reg->address.address;  // Safely cast TAddress to uint16_t
  //snprintf(buffer, sizeof(buffer), "set: [%d]: %d", addr, val);
  //Serial.println(buffer);
  //return val;

  // Update actual values
  if (addr >= ADDR_ACTUAL && addr < ADDR_ACTUAL + NUM_SERVOS) {
    int idx = addr - ADDR_ACTUAL;
    values_actual[idx] = constrain(val, ACTUAL_MIN, ACTUAL_MAX); // limit with default const MAX/MIN instead of var max/min because we may want config the max/min out of their current bonundary
    values_logical[idx] = constrain(map(values_actual[idx], values_min[idx], values_max[idx], LOGICAL_MIN, LOGICAL_MAX), LOGICAL_MIN, LOGICAL_MAX);
    servos[idx].writeMicroseconds(values_actual[idx]);
    snprintf(buffer, sizeof(buffer), "act [%d]: %d (%d)", idx, values_actual[idx], val);
  }

  // Update logical values
  else if (addr >= ADDR_LOGICAL && addr < ADDR_LOGICAL + NUM_SERVOS) {
    int idx = addr - ADDR_LOGICAL;
    values_logical[idx] = constrain(val, LOGICAL_MIN, LOGICAL_MAX);
    values_actual[idx] = constrain(map(values_logical[idx], LOGICAL_MIN, LOGICAL_MAX, values_min[idx], values_max[idx]), ACTUAL_MIN, ACTUAL_MAX);
    servos[idx].writeMicroseconds(values_actual[idx]);
    snprintf(buffer, sizeof(buffer), "log [%d]: %d (%d)", idx, values_logical[idx], val);
  }

  // Update min values and save to EEPROM
  else if (addr >= ADDR_MIN && addr < ADDR_MIN + NUM_SERVOS) {
    int idx = addr - ADDR_MIN;
    values_min[idx] = val;
    EEPROM.put(idx * 2, values_min[idx]);
    snprintf(buffer, sizeof(buffer), "min [%d]: %d", idx, val);
  }

  // Update max values and save to EEPROM
  else if (addr >= ADDR_MAX && addr < ADDR_MAX + NUM_SERVOS) {
    int idx = addr - ADDR_MAX;
    values_max[idx] = val;
    EEPROM.put(100 + idx * 2, values_max[idx]);
    snprintf(buffer, sizeof(buffer), "max [%d]: %d", idx, val);
  }

  else {
    snprintf(buffer, sizeof(buffer), "Error set: unknown addr [%d]: %d", addr, val);
  }

  Serial.println(buffer);
  return val;
}

void setup() {
  char buffer[64]; // print buffer

  // config debug print on default serial (tx: d1, rx: d0)
  Serial.begin(9600);

  // config modbus - Serial1 (tx: d18, rx: d19)
  Serial1.begin(9600);
  mb.begin(&Serial1);
  mb.slave(1);

  mb.addHreg(ADDR_ACTUAL, ACTUAL_DEFAULT, NUM_SERVOS);
  mb.addHreg(ADDR_MIN, ACTUAL_MIN, NUM_SERVOS);
  mb.addHreg(ADDR_MAX, ACTUAL_MAX, NUM_SERVOS);
  mb.addHreg(ADDR_LOGICAL, LOGICAL_DEFAULT, NUM_SERVOS);
  mb.onSetHreg(ADDR_ACTUAL,  onHregSet, NUM_SERVOS);  // register write callback
  mb.onSetHreg(ADDR_MIN,     onHregSet, NUM_SERVOS);  // register write callback
  mb.onSetHreg(ADDR_MAX,     onHregSet, NUM_SERVOS);  // register write callback
  mb.onSetHreg(ADDR_LOGICAL, onHregSet, NUM_SERVOS);  // register write callback

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
    values_logical[i] = constrain(map(values_actual[i], values_min[i], values_max[i], LOGICAL_MIN, LOGICAL_MAX), LOGICAL_MIN, LOGICAL_MAX);

    // Set corresponding registers
    // TODO better to set as an array but somewhy mb.Hreg(addr, array, len) does not work
    snprintf(buffer, sizeof(buffer), "config servo %d", i);
    Serial.println(buffer);
    mb.Hreg(ADDR_ACTUAL + i,  values_actual[i]);
    mb.Hreg(ADDR_MIN + i,     values_min[i]);
    mb.Hreg(ADDR_MAX + i,     values_max[i]);
    mb.Hreg(ADDR_LOGICAL + i, values_logical[i]);
  }


  // setup servos
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].writeMicroseconds(values_actual[i]);
  }

  Serial.println("setup complete");
}  // setup()

void loop() {
  mb.task();
}

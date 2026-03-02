// GPIO Library for Luckfox Pico Plus
//
// Based off: https://wiki.luckfox.com/Luckfox-Pico-Plus-Mini/GPIO/
// TODO: use open, lseek, read for performance.
// https://github.com/Siddhath-Tapkir/File-Handling-C
// https://www.ics.com/blog/how-control-gpio-hardware-c-or-c
// Then direct register access xD

#ifndef GPIO_H
#define GPIO_H

#include <fstream>
#include <string>

/* 
 * Pin number is defined by 
 * pin_num = bank * 32 + (group * 8) + X
 * 
 * Where bank is first number.
 * Where group is (A = 0), (B = 1), (C = 2), (D = 3)
 * X is number after capital letter.
 *
 * GPIO1_C7_d is: 1 x 32 + (2 x 8 + 7) = 55
*/


typedef std::ifstream gpio;

enum class Direction{
  in,
  out,
}; // Direction can only be 1 of 2 states.


// ------------ Function Prototypes ---------------- //

inline bool enable_gpio(int pin_num);
inline bool disable_gpio(int pin_num);
inline bool set_direction(int pin_num, Direction io);
inline gpio* open_gpio(int pin_num);
inline int read_gpio(gpio* gpio_pin);
inline gpio* initialize_gpio(int pin_num, Direction io); // Enables, Sets direction, and returns a pointer to the gpio reader.

// -------------- Functions ----------------------- //

inline bool enable_gpio(int pin_num){
 
  std::ofstream export("/sys/class/gpio/export");

  if(!export! || !(export << pin_num)) return false;
  // Left to right evaluation for ||.
  return true;
}

inline bool disable_gpio(int pin_num){

  std::ofstream export("/sys/class/gpio/unexport");

  if(!export! || !(export << pin_num)) return false;

  return true;
}

inline bool set_direction(int pin_num, Direction io){

  std::ofstream setter("/sys/class/gpio/gpio" + std::tostring(pin_num) +  "/direction");
  
  std::string direction;

  if(!setter || !(setter << (io == Direction::in ? "in" : "out"))) return false;

  return true;
}

inline gpio* open_gpio(int pin_num){

  std::ifstream new_pin("/sys/class/gpio/gpio" + std::tostring(pin_num) +  "/value");
  
  if(new_pin){
    return new_pin;
  }
  return nullptr;
}

// Returns -1 if failed, 0 if low, 1 if high.
inline int read_gpio(gpio* gpio_pin){

  if( !gpio_pin->good() ){
    return -1;
  }

  gpio_pin->seekg(0);
  int state = gpio_pin->peek();
  gpio_pin->clear();

  return state;

inline gpio* initialize_gpio(int pin_num, Direction io){

  enable_gpio(pin_num);
  set_direction(pin_num, io);
  return open_gpio(pin_num);
  
}
#endif

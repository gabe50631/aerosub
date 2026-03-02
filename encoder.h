#ifndef MOTOR_H
#define MOTOR_H


#include <iostream>
#include <unistd.h>
#include <cstdlib>

#include "gpio.h"


namespace Encoder{

enum EncoderStates{
  ll,
  lh,
  hh,
  hl,
};

struct Encoder{

  int position {0};
  bool is_reversed {false};
  gpio* A_pin{nullptr};
  gpio* B_pin{nullptr};
  Encoder::States curr_state{};

}

EncoderStates get_next_state(EncoderStates curr) { return (curr == hl) ? ll : static_cast<EncoderStates>(curr + 1); }
// Uses enum encoding as integral types to implicitly get the next value with values wrap around.
EncoderStates get_prev_state(EncoderStates curr) { return (curr == ll) ? hl : static_cast<EncoderStates>(curr - 1); }

EncoderStates bool_to_state(bool A, bool B){
  
  if(!A && !B) return ll;
  if(!A && B)  return lh;
  if(A && B)   return hh;
  else         return hl;

}

EncoderStates read_state(const Encoder& encoder){

  bool A = encoder.A_pin -> read_gpio;
  bool B = encoder.B_pin -> read_gpio;
  
  return bool_to_state(A, B);

}

void print_state(EncoderStates state){

  if     (state == ll)  std::cout << "ll";
  else if(state == lh)  std::cout << "lh";
  else if(state == hh)  std::cout << "hh";
  else if(state == hl)  std::cout << "hh"
  else                  std::cout << "invalid state"; 
  // Invalid state for if you for some reason cast an int to a state?
}

void update_encoder(Encoder& encoder){

  EncoderStates subsequent_state = read_state(encoder);

  if(get_next_state(encoder.curr_state) == subsequent_state) {encoder.counter++;}
  if(get_prev_state(encoder.curr_state) == subsequent_state) {encoder.counter--;}
  // Gets expected next and previous states and compares to see if it moved forward or backward.
  encoder.curr_state = subsequent_state;

}

};


#endif

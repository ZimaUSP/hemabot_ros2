/*
Autores  : Alicia Mei, Leonardo Dias do Carmo
Data    :   01/04/2025
Descrição: Código simples para teste de funcionamento do Driver TCRT500
*/


#include "firmware_minihema/motor_encoder.h"
#include <math.h>
const unsigned long intervaloDebounce = 0; // em milissegundos
volatile unsigned long ultimoPulso = 0;
// Initialize pulse counters
int left_wheel_pulse_count = 0;
int right_wheel_pulse_count = 0;

// Initialize wheel directions
// 1 - forward, 0 - backward
int left_wheel_direction = 1;
int right_wheel_direction = 1;

// Read wheel encoder values
void read_encoder_values(int *left_encoder_value, int *right_encoder_value) {
  *left_encoder_value = left_wheel_pulse_count;
  *right_encoder_value = right_wheel_pulse_count;
}


void add_left_wheel(){
  unsigned long agora = millis();
  if(left_wheel_direction == FORWARD && (agora - ultimoPulso > intervaloDebounce)){
    left_wheel_pulse_count++;
    ultimoPulso = agora;
  }
  else if (left_wheel_direction == BACKWARD && (agora - ultimoPulso > intervaloDebounce)){
    left_wheel_pulse_count--;
    ultimoPulso = agora;
  }
}

void add_right_wheel(){
  unsigned long agora = millis();
  if(right_wheel_direction == FORWARD && (agora - ultimoPulso > intervaloDebounce)){
    right_wheel_pulse_count++;
    ultimoPulso = agora;
  }
  else if (right_wheel_direction == BACKWARD && (agora - ultimoPulso > intervaloDebounce)){
    right_wheel_pulse_count--;
    ultimoPulso = agora;
  }
}

// Set each motor speed from the respective velocity command interface
void set_motor_speeds(double left_wheel_command, double right_wheel_command) {
  // Initialize DIR enum variables
  DIR left_motor_direction;
  DIR right_motor_direction;
  // Tune motor speeds by adjusting the command coefficients. These are
  // dependent on the number of encoder ticks. 3000 ticks and above work well
  // with coefficients of 1.0
  double left_motor_speed = ceil(left_wheel_command * 1.65);
  double right_motor_speed = ceil(right_wheel_command * 1.65);

  // Set motor directions
  if (left_motor_speed > 0)
    left_motor_direction = FORWARD;
  else
    left_motor_direction = BACKWARD;

  if (right_motor_speed > 0)
    right_motor_direction = FORWARD;
  else
    right_motor_direction = BACKWARD;
  
  left_wheel_direction = left_motor_direction;
  right_wheel_direction = right_motor_direction;
  
  // Run motors with specified direction and speeds
  Motor_Run(MOTORA, left_motor_direction, (int)abs(left_motor_speed));
  Motor_Run(MOTORB, right_motor_direction, (int)abs(right_motor_speed));
}

void handler(int signo) {
  Motor_Stop(MOTORA);
  Motor_Stop(MOTORB);

  exit(0);
}
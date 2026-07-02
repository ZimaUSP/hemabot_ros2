/*
Autores  : Alicia Mei, Leonardo Dias do Carmo
Data     : 01/04/2025
Descrição: Código simples para teste de funcionamento do Driver TCRT500 (Corrigido)
*/

#include "firmware_minihema/motor_encoder.h"
#include <math.h>

const unsigned long intervaloDebounce = 5; 

// Tempos de debounce independentes para cada roda
volatile unsigned long ultimoPulsoEsquerda = 0;
volatile unsigned long ultimoPulsoDireita = 0;

// Contadores de pulso precisam ser volatile pois mudam na ISR
volatile int left_wheel_pulse_count = 0;
volatile int right_wheel_pulse_count = 0;

// Direções das rodas (1 - forward, 0 - backward)
volatile int left_wheel_direction = 1;
volatile int right_wheel_direction = 1;

// Read wheel encoder values
void read_encoder_values(int *left_encoder_value, int *right_encoder_value) {
  *left_encoder_value = left_wheel_pulse_count;
  *right_encoder_value = right_wheel_pulse_count;
  
  DEBUG("Encoder esquerda: %d", *left_encoder_value);
  DEBUG("Encoder direita: %d", *right_encoder_value);
}

void add_left_wheel(){
  unsigned long agora = millis();
  if((agora - ultimoPulsoEsquerda) > intervaloDebounce){
    if(left_wheel_direction == FORWARD){
      left_wheel_pulse_count++;
    } else if (left_wheel_direction == BACKWARD){
      left_wheel_pulse_count--;
    }
    ultimoPulsoEsquerda = agora;
  }
}

void add_right_wheel(){
  unsigned long agora = millis();
  if((agora - ultimoPulsoDireita) > intervaloDebounce){
    if(right_wheel_direction == FORWARD){
      right_wheel_pulse_count++;
    } else if (right_wheel_direction == BACKWARD){
      right_wheel_pulse_count--;
    }
    ultimoPulsoDireita = agora;
  }
}

void set_motor_speeds(double left_wheel_command, double right_wheel_command) {
  DIR left_motor_direction;
  DIR right_motor_direction;

  // Aplica o ganho de conversão
  double left_motor_speed = ceil(left_wheel_command * 1.65);
  double right_motor_speed = ceil(right_wheel_command * 1.65);

  // Determina as direções
  if (left_motor_speed >= 0) 
    left_motor_direction = BACKWARD;
  else
    left_motor_direction = FORWARD;

  if (right_motor_speed >= 0)
    right_motor_direction = BACKWARD;
  else
    right_motor_direction = FORWARD;
  
  // Atualiza as variáveis de direção que as ISRs usam para saber se somam ou subtraem
  left_wheel_direction = left_motor_direction;
  right_wheel_direction = right_motor_direction;
  
  // Controla os motores físicos
  Motor_Run(MOTORA, left_motor_direction, (int)abs(left_motor_speed));
  Motor_Run(MOTORB, right_motor_direction, (int)abs(right_motor_speed));
}

void handler(int signo) {
  Motor_Stop(MOTORA);
  Motor_Stop(MOTORB);
  exit(0);
}
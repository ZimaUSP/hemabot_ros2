/*
Autores  : Alicia Mei, Leonardo Dias do Carmo
Data     : 01/04/2025
Descrição: Código simples para teste de funcionamento do Driver TCRT500 (Corrigido)
*/

#include "firmware_minihema/motor_encoder.h"
#include <math.h>
#include <pthread.h>

const unsigned int intervaloDebounce = 5000; // us

// Tempos de debounce independentes para cada roda
volatile unsigned int ultimoPulsoEsquerda = 0;
volatile unsigned int ultimoPulsoDireita = 0;

// Contadores de pulso precisam ser volatile pois mudam na ISR
volatile int left_wheel_pulse_count = 0;
volatile int right_wheel_pulse_count = 0;

// Direções das rodas (1 - forward, 0 - backward)
volatile int left_wheel_direction = 1;
volatile int right_wheel_direction = 1;

// Instante (micros) do último pulso aceito, usado para estimar a velocidade pelo intervalo entre pulsos
volatile unsigned int left_wheel_pulse_us = 0;
volatile unsigned int right_wheel_pulse_us = 0;

// As ISRs do wiringPi rodam em threads próprias: o mutex garante que contagem e instante sejam lidos juntos
static pthread_mutex_t encoder_mutex = PTHREAD_MUTEX_INITIALIZER;

// Read wheel encoder values
void read_encoder_values(int *left_encoder_value, int *right_encoder_value) {
  *left_encoder_value = left_wheel_pulse_count;
  *right_encoder_value = right_wheel_pulse_count;
  
  DEBUG("Encoder esquerda: %d", *left_encoder_value);
  DEBUG("Encoder direita: %d", *right_encoder_value);
}

// Read wheel encoder counts together with the time of the last pulse of each wheel
void read_encoder_snapshot(int *left_ticks, unsigned int *left_pulse_us,
                           int *right_ticks, unsigned int *right_pulse_us) {
  pthread_mutex_lock(&encoder_mutex);
  *left_ticks = left_wheel_pulse_count;
  *left_pulse_us = left_wheel_pulse_us;
  *right_ticks = right_wheel_pulse_count;
  *right_pulse_us = right_wheel_pulse_us;
  pthread_mutex_unlock(&encoder_mutex);
}

void add_left_wheel(){
  unsigned int agora = micros();
  if((agora - ultimoPulsoEsquerda) > intervaloDebounce){
    pthread_mutex_lock(&encoder_mutex);
    if(left_wheel_direction == FORWARD){
      left_wheel_pulse_count++;
    } else if (left_wheel_direction == BACKWARD){
      left_wheel_pulse_count--;
    }
    left_wheel_pulse_us = agora;
    pthread_mutex_unlock(&encoder_mutex);
    ultimoPulsoEsquerda = agora;
  }
}

void add_right_wheel(){
  unsigned int agora = micros();
  if((agora - ultimoPulsoDireita) > intervaloDebounce){
    pthread_mutex_lock(&encoder_mutex);
    if(right_wheel_direction == FORWARD){
      right_wheel_pulse_count++;
    } else if (right_wheel_direction == BACKWARD){
      right_wheel_pulse_count--;
    }
    right_wheel_pulse_us = agora;
    pthread_mutex_unlock(&encoder_mutex);
    ultimoPulsoDireita = agora;
  }
}

// Drive one motor with a signed duty cycle in [-1, 1]. The duty is applied with 1% resolution,
// which is what Motor_Run accepts.
static void drive_motor(UBYTE motor, double duty, volatile int *encoder_direction) {
  double magnitude = fabs(duty);
  if (!(magnitude <= 1.0)) magnitude = 1.0;  // also catches NaN

  int percent = (int)lround(magnitude * 100.0);
  if (percent == 0) {
    Motor_Stop(motor);
    return;
  }

  DIR direction = (duty > 0.0) ? FORWARD : BACKWARD;

  // The encoders are single-channel: the ISRs take the sign of each pulse from the driven
  // direction. It only changes while the motor is driven, because a coasting wheel keeps
  // turning the way it was going.
  *encoder_direction = direction;
  Motor_Run(motor, direction, (UWORD)percent);
}

void set_motor_duties(double left_duty, double right_duty) {
  drive_motor(MOTORA, left_duty, &left_wheel_direction);
  drive_motor(MOTORB, right_duty, &right_wheel_direction);
}

void handler(int signo) {
  Motor_Stop(MOTORA);
  Motor_Stop(MOTORB);
  exit(0);
}

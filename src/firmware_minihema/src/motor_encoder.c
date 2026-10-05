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

// Calibração dos motores
#define MIN_MOTOR_PWM 26.0          // Zona morta mínima para romper atrito estático imediatamente (sem atraso na partida)
#define RIGHT_WHEEL_RATIO 1.18      // Razão balanceada da roda direita para andar reto sem puxar para a esquerda/direita

void set_motor_speeds(double left_wheel_command, double right_wheel_command) {
  DIR left_motor_direction;
  DIR right_motor_direction;

  // Determina direções com base no comando
  left_motor_direction = (left_wheel_command >= 0.0) ? FORWARD : BACKWARD;
  right_motor_direction = (right_wheel_command >= 0.0) ? FORWARD : BACKWARD;

  // Converte comando em magnitude base [0..100] com a compensação balanceada na roda direita
  double left_mag = fabs(left_wheel_command) * 125.0;
  double right_mag = fabs(right_wheel_command) * (125.0 * RIGHT_WHEEL_RATIO);

  double left_motor_speed = 0.0;
  double right_motor_speed = 0.0;

  // Compensação de zona morta (deadband):
  // Se o comando for não-nulo, inicia na faixa de torque útil (MIN_MOTOR_PWM)
  // eliminando o atraso de partida (stiction lag)
  if (left_mag > 1e-3) {
    if (left_mag > 100.0) left_mag = 100.0;
    left_motor_speed = MIN_MOTOR_PWM + (left_mag * (100.0 - MIN_MOTOR_PWM) / 100.0);
  }
  if (right_mag > 1e-3) {
    if (right_mag > 100.0) right_mag = 100.0;
    right_motor_speed = MIN_MOTOR_PWM + (right_mag * (100.0 - MIN_MOTOR_PWM) / 100.0);
  }

  // Atualiza as variáveis de direção que as ISRs usam para saber se somam ou subtraem
  left_wheel_direction = left_motor_direction;
  right_wheel_direction = right_motor_direction;

  // Controla os motores físicos (se velocidade for zero, para imediatamente)
  if (left_motor_speed <= 0.0) {
    Motor_Stop(MOTORA);
  } else {
    Motor_Run(MOTORA, left_motor_direction, (int)round(left_motor_speed));
  }

  if (right_motor_speed <= 0.0) {
    Motor_Stop(MOTORB);
  } else {
    Motor_Run(MOTORB, right_motor_direction, (int)round(right_motor_speed));
  }
}

void handler(int signo) {
  Motor_Stop(MOTORA);
  Motor_Stop(MOTORB);
  exit(0);
}

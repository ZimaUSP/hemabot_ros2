/*
Autor  : Alicia Mei
Data    :   19/03/2025
Descrição: Código simples para teste de funcionamento do Driver TCRT500
*/


#ifndef __MOTOR_ENCODER_H__
#define __MOTOR_ENCODER_H__
#ifdef __cplusplus
extern "C"{
#endif
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <wiringPi.h>

#include "KeyesDriver.h"

#define LEFT_WHL_ENC_D0 9
#define RIGHT_WHL_ENC_D0 6

#define LEFT_WHL_ENC_DIR 24
#define RIGHT_WHL_ENC_DIR 25

#define LEFT_WHL_ENC_A0 4
#define RIGHT_WHL_ENC_A0 16

void handler(int signo);
void add_left_wheel();
void add_right_wheel();
void set_motor_speeds(double left_wheel_command, double right_wheel_command);
void read_encoder_values(int *left_encoder_value, int *right_encoder_value);

extern int left_wheel_pulse_count;
extern int right_wheel_pulse_count;
extern int left_wheel_direction;
extern int right_wheel_direction;
#ifdef __cplusplus
}
#endif
#endif 

  

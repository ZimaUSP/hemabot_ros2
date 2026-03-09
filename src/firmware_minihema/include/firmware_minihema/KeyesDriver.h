/*****************************************************************************
* | File        :   KeyesDriver.h
* | Author      :   Leonardo Dias do Carmo
* | Function    :   Drive Keyes L298N
*----------------
* |	This version:   V1.0
* | Date        :   2025-10-01
* | Info        :   Versão Básica
*
******************************************************************************/

#ifndef __KEYESDRIVER_
#define __KEYESDRIVER_

#ifdef __cplusplus
extern "C" {
#endif

#include "PinPlannerRasp.h"
#include "DEV_Config.h"
#include <wiringPi.h>

//  Configurações do GPIO

#define PINO_IN0   PIN_MOTOR_IN0
#define PINO_IN1   PIN_MOTOR_IN1
#define PINO_IN2   PIN_MOTOR_IN2
#define PINO_IN3   PIN_MOTOR_IN3

#define MOTORA       0
#define MOTORB       1

// Definições de tipos personalizados
typedef uint8_t  UBYTE;
typedef uint16_t UWORD;
typedef uint32_t UDOUBLE;

typedef enum {
    BACKWARD = 0,
    FORWARD,
} DIR;
//

void Motor_Init(void);
void Motor_Run(UBYTE motor, DIR dir, UWORD speed);
void Motor_Stop(UBYTE motor);
UBYTE Motor_Direction(UBYTE motor);
#ifdef __cplusplus
}
#endif
#endif

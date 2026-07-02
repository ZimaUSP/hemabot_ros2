/*****************************************************************************
* | File        :   KeyesDriver.cpp
* | Author      :   Leonardo Dias do Carmo
* | Function    :   Drive Keyes L298N
*----------------
* | This version:   V1.1 
* | Date        :   2026-06-14
*
******************************************************************************/

#include "firmware_minihema/KeyesDriver.h"
#include "firmware_minihema/DEV_Config.h"
#include "firmware_minihema/PinPlannerRasp.h"
#include <softPwm.h>



UWORD ain1_value = 0, ain2_value = 0; 
UWORD bin1_value = 0, bin2_value = 0;

void Motor_Init(void)
{
    pinMode(PINO_IN0, OUTPUT);  
    pinMode(PINO_IN1, OUTPUT);  
    pinMode(PINO_IN2, OUTPUT);  
    pinMode(PINO_IN3, OUTPUT);  
    pinMode(PINO_ENA, OUTPUT);
    pinMode(PINO_ENB, OUTPUT);
    
    softPwmCreate(PINO_ENA, 0, 255); 
    softPwmCreate(PINO_ENB, 0, 255);   
}

void Motor_Run(UBYTE motor, DIR dir, UWORD speed)
{   
    int pwmSpeed; // softPwmWrite espera um inteiro

    if(speed > 100)
        speed = 100;

    pwmSpeed = (int)(speed * (255.0 / 100.0)); 

    if(motor == MOTORA) {
        DEBUG("Velocidade do Motor A = %d\r\n", speed);
        if(dir == FORWARD) {
            DEBUG("Frente..\r\n");
            digitalWrite(PINO_IN1, 0);
            digitalWrite(PINO_IN0, 1);
            softPwmWrite(PINO_ENA, pwmSpeed);  
            ain1_value = 0;
            ain2_value = 1;
        } else {
            DEBUG("Ré...\r\n");
            digitalWrite(PINO_IN1, 1);
            digitalWrite(PINO_IN0, 0);
            softPwmWrite(PINO_ENA, pwmSpeed);
            ain1_value = 1;
            ain2_value = 0;
        }
    } else {
        DEBUG("Velocidade do Motor B = %d\r\n", speed);
        if(dir == FORWARD) {
            DEBUG("Frente...\r\n");   
            digitalWrite(PINO_IN3, 0);
            digitalWrite(PINO_IN2, 1);
            softPwmWrite(PINO_ENB, pwmSpeed);    
            bin1_value = 0;
            bin2_value = 1;
        } else {
            DEBUG("Ré...\r\n");
            digitalWrite(PINO_IN3, 1);    
            digitalWrite(PINO_IN2, 0);
            softPwmWrite(PINO_ENB, pwmSpeed); 
            bin1_value = 1;
            bin2_value = 0;
        }
    }
}

void Motor_Stop(UBYTE motor)
{
    if (motor == MOTORA){
        DEBUG("Parando MOTORA\r\n");
        digitalWrite(PINO_IN0, 0);
        digitalWrite(PINO_IN1, 0); 
        softPwmWrite(PINO_ENA, 0); 
    }
    else if (motor == MOTORB){
        DEBUG("Parando MOTORB\r\n");
        digitalWrite(PINO_IN2, 0);
        digitalWrite(PINO_IN3, 0);
        softPwmWrite(PINO_ENB, 0); 
    }
}

UBYTE Motor_Direction(UBYTE motor)
{
    if(motor == MOTORA) {
        if(ain1_value == 0 && ain2_value == 1) return 0;
        if(ain1_value == 1 && ain2_value == 0) return 1;
    }
    else if (motor == MOTORB) {
        if(bin1_value == 0 && bin2_value == 1) return 0;
        if(bin1_value == 1 && bin2_value == 0) return 1;
    }
    
    return 0; 
}
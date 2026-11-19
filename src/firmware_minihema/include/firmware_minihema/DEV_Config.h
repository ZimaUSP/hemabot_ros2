#ifndef __DEV_CONFIG_H__
#define __DEV_CONFIG_H__

// Ativação da biblioteca WiringPi (opcional)
#define USE_WIRINGPI_LIB 1

/***********************************************************************************************************************
 *                                         Hardware Interface
 ***********************************************************************************************************************/


#include <wiringPi.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/***********************************************************************************************************************
 *                                         Configuração de Debug
 ***********************************************************************************************************************/
// Keep disabled on the robot: DEBUG is called from the 20 Hz control loop, and printing every
// cycle can block that loop when the stdout pipe (read by ros2 launch) fills up.
#define USE_DEBUG 0

#if USE_DEBUG
    #define DEBUG(__info, ...) printf("[DEBUG] " __info, ##__VA_ARGS__)
#else
    #define DEBUG(__info, ...)
#endif

#endif // __DEV_CONFIG_H__

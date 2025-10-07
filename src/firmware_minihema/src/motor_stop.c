
#include "firmware_minihema/KeyesDriver.h"
#include "firmware_minihema/motor_encoder.h"
int main(int argc, char **argv)
{
    // Setup GPIO encoder interrupt and direction pins
    wiringPiSetupGpio();
    // Initialize motor driver
    handler(0);
}
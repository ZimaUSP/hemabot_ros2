extern "C" {
  #include "firmware_minihema/KeyesDriver.h"
  #include "firmware_minihema/motor_encoder.h"
}

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <wiringPi.h>

static volatile bool g_running = true;

void handleSigint(int) {
    g_running = false;
}

int main(int argc, char **argv) {
    signal(SIGINT, handleSigint);

    if (wiringPiSetupGpio() == -1) {
        fprintf(stderr, "[ERRO] Falha ao inicializar wiringPi.\n");
        return EXIT_FAILURE;
    }

    pinMode(LEFT_WHL_ENC_D0, INPUT);
    pinMode(RIGHT_WHL_ENC_D0, INPUT);

    pullUpDnControl(LEFT_WHL_ENC_D0, PUD_UP);
    pullUpDnControl(RIGHT_WHL_ENC_D0, PUD_UP);

    wiringPiISR(LEFT_WHL_ENC_D0, INT_EDGE_FALLING, add_left_wheel);
    wiringPiISR(RIGHT_WHL_ENC_D0, INT_EDGE_FALLING, add_right_wheel);

    printf("=== Teste de encoders iniciado (Ctrl+C para parar) ===\n");
    printf("Gire as rodas manualmente e observe a contagem dos pulsos.\n\n");

    int xPrev = 0, yPrev = 0;
    read_encoder_values(&xPrev, &yPrev);

    const int kSampleIntervalMs = 500; // intervalo entre amostras
    int elapsedTotal = 0;

    while (g_running) {
        delay(kSampleIntervalMs);
        elapsedTotal += kSampleIntervalMs;

        int xCur = 0, yCur = 0;
        read_encoder_values(&xCur, &yCur);

        int deltaLeft  = xCur - xPrev;
        int deltaRight = yCur - yPrev;

        double leftPulsesPerSec  = deltaLeft  / (kSampleIntervalMs / 1000.0);
        double rightPulsesPerSec = deltaRight / (kSampleIntervalMs / 1000.0);

        printf("[t=%5d ms] Esquerdo: total=%6d  delta=%4d  (%.1f p/s) | "
               "Direito: total=%6d  delta=%4d  (%.1f p/s)\n",
               elapsedTotal,
               xCur, deltaLeft, leftPulsesPerSec,
               yCur, deltaRight, rightPulsesPerSec);

        xPrev = xCur;
        yPrev = yCur;
    }

    int xFinal = 0, yFinal = 0;
    read_encoder_values(&xFinal, &yFinal);

    printf("\n=== Teste finalizado ===\n");
    printf("Contagem final -> Esquerdo: %d | Direito: %d\n", xFinal, yFinal);

    return EXIT_SUCCESS;
}
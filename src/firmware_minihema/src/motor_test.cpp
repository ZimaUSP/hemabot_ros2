extern "C" {
  #include "firmware_minihema/KeyesDriver.h"
  #include "firmware_minihema/motor_encoder.h"
}

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <wiringPi.h>

// Flag global para permitir parada segura com Ctrl+C
static volatile bool g_running = true;

void handleSigint(int) {
    g_running = false;
}

// Para os motores e imprime o estado final dos encoders antes de sair
void safeShutdown(int x, int y) {
    set_motor_speeds(0, 0);
    printf("\n[SHUTDOWN] Motores parados.\n");
    printf("[SHUTDOWN] Encoder esquerdo: %d | Encoder direito: %d\n", x, y);
}

// Executa um teste de movimento por uma duração, reportando velocidade
// estimada via encoder antes/depois (pulsos por segundo)
void runMotorTest(int leftSpeed, int rightSpeed, int durationMs, const char *label) {
    int xBefore = 0, yBefore = 0;
    int xAfter = 0, yAfter = 0;

    read_encoder_values(&xBefore, &yBefore);

    printf("\n[TEST] %s -> set_motor_speeds(%d, %d) por %d ms\n",
           label, leftSpeed, rightSpeed, durationMs);

    set_motor_speeds(leftSpeed, rightSpeed);

    // Delay interrompível em pedaços de 100ms, para reagir ao Ctrl+C rapidamente
    int elapsed = 0;
    while (elapsed < durationMs && g_running) {
        delay(100);
        elapsed += 100;
    }

    set_motor_speeds(0, 0);
    delay(200); // pequena pausa para o motor parar antes de ler o encoder

    read_encoder_values(&xAfter, &yAfter);

    int deltaLeft  = xAfter - xBefore;
    int deltaRight = yAfter - yBefore;
    double pulsesPerSecLeft  = deltaLeft  / (durationMs / 1000.0);
    double pulsesPerSecRight = deltaRight / (durationMs / 1000.0);

    printf("[RESULT] Encoder esquerdo: %d -> %d (delta %d, %.1f pulsos/s)\n",
           xBefore, xAfter, deltaLeft, pulsesPerSecLeft);
    printf("[RESULT] Encoder direito:  %d -> %d (delta %d, %.1f pulsos/s)\n",
           yBefore, yAfter, deltaRight, pulsesPerSecRight);
}

int main(int argc, char **argv) {
    signal(SIGINT, handleSigint);

    // Configura GPIO usando numeração BCM
    if (wiringPiSetupGpio() == -1) {
        fprintf(stderr, "[ERRO] Falha ao inicializar wiringPi.\n");
        return EXIT_FAILURE;
    }

    Motor_Init();

    pinMode(LEFT_WHL_ENC_D0, INPUT);
    pinMode(RIGHT_WHL_ENC_D0, INPUT);

    pullUpDnControl(LEFT_WHL_ENC_D0, PUD_UP);
    pullUpDnControl(RIGHT_WHL_ENC_D0, PUD_UP);

    wiringPiISR(LEFT_WHL_ENC_D0, INT_EDGE_FALLING, add_left_wheel);
    wiringPiISR(RIGHT_WHL_ENC_D0, INT_EDGE_FALLING, add_right_wheel);

    printf("=== Teste de motores e encoders iniciado (Ctrl+C para parar) ===\n");

    // Bateria de testes: frente, ré, giro no eixo, e parada
    const int kTestDurationMs = 3000;

    if (g_running) runMotorTest(40,  40,  kTestDurationMs, "Frente");
    if (g_running) runMotorTest(0,   0,   1000,            "Parada");
    if (g_running) runMotorTest(-100, -100, kTestDurationMs, "Ré");
    if (g_running) runMotorTest(0,   0,   1000,            "Parada");
    if (g_running) runMotorTest(100, -100,  kTestDurationMs, "Giro horário");
    if (g_running) runMotorTest(-100, 100,  kTestDurationMs, "Giro anti-horário");

    int xFinal = 0, yFinal = 0;
    read_encoder_values(&xFinal, &yFinal);
    safeShutdown(xFinal, yFinal);

    printf("=== Teste finalizado ===\n");
    return EXIT_SUCCESS;

}
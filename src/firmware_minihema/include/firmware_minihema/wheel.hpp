#ifndef _FIRMWARE_MINIHEMA__WHEEL_H_
#define _FIRMWARE_MINIHEMA__WHEEL_H_

#include <string>
#include <cmath>

class Wheel
{
  public:
    std::string name = "";
    int encoder_ticks = 0;
    double command = 0.0;
    double position = 0.0;
    double velocity = 0.0;
    double rads_per_tick = 0.0;

    // Estado do estimador de velocidade pelo intervalo entre pulsos
    unsigned int last_pulse_us = 0;
    bool has_pulse_reference = false;

    Wheel() = default;

    Wheel(const std::string &wheel_name, int ticks_per_rev);

    void setup(const std::string &wheel_name, int ticks_per_rev);

    double calculate_encoder_angle();

    // Sincroniza a posição com o encoder e zera a velocidade estimada
    void reset_encoder(int ticks);

    // Atualiza posição e velocidade a partir da contagem do encoder, do instante (micros)
    // do último pulso e do instante atual
    void update(int ticks, unsigned int pulse_us, unsigned int now_us, double timeout_s, double alpha);

};

#endif

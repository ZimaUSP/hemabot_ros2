#include "firmware_minihema/wheel.hpp"

#include <cstdlib>

Wheel::Wheel(const std::string &wheel_name, int ticks_per_rev)
{
    setup(wheel_name, ticks_per_rev);
}

void Wheel::setup(const std::string &wheel_name, int ticks_per_rev)
{
    name = wheel_name;
    rads_per_tick = (2*M_PI)/ticks_per_rev;
}

double Wheel::calculate_encoder_angle()
{
    return encoder_ticks * rads_per_tick;
}

void Wheel::reset_encoder(int ticks)
{
    encoder_ticks = ticks;
    position = calculate_encoder_angle();
    velocity = 0.0;
    has_pulse_reference = false;
}

void Wheel::update(int ticks, unsigned int pulse_us, unsigned int now_us, double timeout_s, double alpha)
{
    int delta_ticks = ticks - encoder_ticks;
    encoder_ticks = ticks;
    position = calculate_encoder_angle();

    if (delta_ticks != 0)
    {
        // Velocidade pelos pulsos que chegaram desde o último pulso de referência.
        // A subtração unsigned trata o estouro do micros() (~71 min).
        double interval_s = (pulse_us - last_pulse_us) * 1e-6;

        if (has_pulse_reference && interval_s > 0.0)
        {
            double raw_velocity = delta_ticks * rads_per_tick / interval_s;
            velocity = alpha * raw_velocity + (1.0 - alpha) * velocity;
        }
        else
        {
            // Primeiro pulso depois de a roda estar parada: o intervalo inclui o tempo parado
            velocity = 0.0;
        }

        last_pulse_us = pulse_us;
        has_pulse_reference = true;
        return;
    }

    // Sem pulsos neste ciclo: a roda não pode estar mais rápida que um tick no tempo desde o último pulso
    double since_last_pulse_s = (now_us - last_pulse_us) * 1e-6;
    if (!has_pulse_reference || since_last_pulse_s > timeout_s)
    {
        // Roda parada: descarta a referência para o próximo pulso não usar um intervalo antigo
        velocity = 0.0;
        has_pulse_reference = false;
    }
    else if (since_last_pulse_s > 0.0)
    {
        double max_speed = rads_per_tick / since_last_pulse_s;
        if (std::abs(velocity) > max_speed)
        {
            velocity = std::copysign(max_speed, velocity);
        }
    }
}

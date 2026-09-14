#ifndef FIRMWARE_MINIHEMA__PID_HPP_
#define FIRMWARE_MINIHEMA__PID_HPP_

#include <algorithm>
#include <cmath>

namespace firmware_minihema
{

/**
 * @brief Controlador PID baseado na implementação de referência pi_diff_drive/pid.cpp
 * Para controle puramente proporcional: defina ki = 0.0 e kd = 0.0.
 * A correção calculada será: correção = Kp * erro
 */
class PIDController
{
public:
    PIDController() = default;

    void setupPID(double kp, double ki, double kd, double time_step,
                  double max_input, double max_windup);

    double computeControl(double setpoint, double current_state);
    double computeControl(double setpoint, double current_state, double time_step);

    void reset();

    double kp_ = 0.0;
    double ki_ = 0.0;
    double kd_ = 0.0;
    double time_step_ = 0.0;
    double prev_state_ = 0.0;
    double prev_error_ = 0.0;
    double integral_error_ = 0.0;
    double max_windup_ = 0.0;
    double max_input_ = 0.0;
    double error = 0.0;
    double derivative_error = 0.0;
    double control_input = 0.0;
};

} // namespace firmware_minihema

#endif // FIRMWARE_MINIHEMA__PID_HPP_

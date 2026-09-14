#include "firmware_minihema/pid.hpp"

namespace firmware_minihema
{

void PIDController::setupPID(double kp, double ki, double kd, double time_step,
                             double max_input, double max_windup)
{
    kp_ = kp;
    ki_ = ki;
    kd_ = kd;
    time_step_ = time_step;
    max_input_ = max_input;
    max_windup_ = max_windup;
    prev_state_ = 0.0;
    prev_error_ = 0.0;
    integral_error_ = 0.0;
    error = 0.0;
    derivative_error = 0.0;
    control_input = 0.0;
}

void PIDController::reset()
{
    prev_state_ = 0.0;
    prev_error_ = 0.0;
    integral_error_ = 0.0;
    error = 0.0;
    derivative_error = 0.0;
    control_input = 0.0;
}

double PIDController::computeControl(double setpoint, double current_state)
{
    return computeControl(setpoint, current_state, time_step_);
}

double PIDController::computeControl(double setpoint, double current_state, double time_step)
{
    if (time_step > 1e-5)
    {
        time_step_ = time_step;
    }

    // Cálculo do erro: erro = setpoint - current_state
    error = setpoint - current_state;

    // Termo derivativo
    if (time_step_ > 1e-5)
    {
        derivative_error = (error - prev_error_) / time_step_;
    }
    else
    {
        derivative_error = 0.0;
    }

    // Termo integral com limite de windup
    integral_error_ += error * time_step_;
    if (max_windup_ > 0.0)
    {
        integral_error_ = std::clamp(integral_error_, -max_windup_, max_windup_);
    }

    // Cálculo do sinal de controle:
    // Para controle proporcional puro (ki = 0, kd = 0): correção = Kp * erro
    control_input = (error * kp_) + (integral_error_ * ki_) + (derivative_error * kd_);

    if (max_input_ > 0.0)
    {
        control_input = std::clamp(control_input, -max_input_, max_input_);
    }

    prev_error_ = error;
    prev_state_ = current_state;

    return control_input;
}

} // namespace firmware_minihema

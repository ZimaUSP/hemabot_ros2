#include "firmware_minihema/wheel_speed_controller.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace firmware_minihema
{

namespace
{

void require(bool condition, const std::string & message)
{
  if (!condition)
  {
    throw std::invalid_argument(message);
  }
}

bool is_non_negative(double value)
{
  return std::isfinite(value) && value >= 0.0;
}

}  // namespace

double MotorFeedforward::duty_for(double speed_magnitude) const
{
  if (speed_magnitude <= 0.0)
  {
    return 0.0;
  }
  return static_duty + duty_per_rad_s * speed_magnitude;
}

double MotorFeedforward::max_speed(double max_duty) const
{
  if (duty_per_rad_s <= 0.0)
  {
    return std::numeric_limits<double>::infinity();
  }
  return std::max(0.0, (max_duty - static_duty) / duty_per_rad_s);
}

WheelSpeeds limit_preserving_curvature(const WheelSpeeds & command, const WheelSpeeds & max_speed)
{
  double scale = 1.0;
  if (std::abs(command.left) > max_speed.left)
  {
    scale = std::min(scale, max_speed.left / std::abs(command.left));
  }
  if (std::abs(command.right) > max_speed.right)
  {
    scale = std::min(scale, max_speed.right / std::abs(command.right));
  }
  return WheelSpeeds{command.left * scale, command.right * scale};
}

WheelSpeedController::WheelSpeedController(
  const MotorFeedforward & feedforward, const WheelSpeedControllerConfig & config)
: feedforward_(feedforward), config_(config)
{
  require(std::isfinite(config.max_duty) && config.max_duty > 0.0 && config.max_duty <= 1.0,
    "max_duty must be in (0, 1]");
  // At static_duty == max_duty the motor could not go any faster than standing still
  require(is_non_negative(feedforward.static_duty) && feedforward.static_duty < config.max_duty,
    "static_duty must be in [0, max_duty)");
  require(is_non_negative(feedforward.duty_per_rad_s), "duty_per_rad_s must be >= 0");
  require(is_non_negative(config.kp), "kp must be >= 0");
  require(is_non_negative(config.ki), "ki must be >= 0");
  require(is_non_negative(config.integral_limit), "integral_limit must be >= 0");
  require(std::isfinite(config.rads_per_tick) && config.rads_per_tick > 0.0, "rads_per_tick must be > 0");
  require(is_non_negative(config.spin_up_time), "spin_up_time must be >= 0");
}

double WheelSpeedController::update(double target_speed, std::optional<double> measured_speed, double dt)
{
  if (!std::isfinite(target_speed) || std::abs(target_speed) < kStopThreshold)
  {
    reset();
    return 0.0;
  }

  const int direction = target_speed > 0.0 ? 1 : -1;
  if (direction != active_direction_)
  {
    // The integral was learned for the other direction (or for a previous run); it does not apply.
    reset();
    active_direction_ = direction;
  }

  const double step = std::isfinite(dt) ? std::clamp(dt, 0.0, kMaxIntegrationStep) : 0.0;

  // Work with magnitudes along the commanded direction, so both directions share one code path.
  const double speed_reference = std::abs(target_speed);
  const double feedforward = feedforward_.duty_for(speed_reference);

  const bool has_measurement = measured_speed.has_value() && std::isfinite(*measured_speed);
  if (has_measurement)
  {
    time_without_measurement_ = 0.0;
  }
  else
  {
    time_without_measurement_ += step;
    if (time_without_measurement_ < measurement_deadline(speed_reference))
    {
      // Speed unknown but not overdue: hold the integral and trust the model
      return direction * std::clamp(feedforward + integral_, 0.0, config_.max_duty);
    }
    // Overdue: the wheel is not turning (or turns slower than the encoder can measure)
  }

  const double speed_along_command = has_measurement ? direction * *measured_speed : 0.0;
  const double error = speed_reference - speed_along_command;

  const double proportional = config_.kp * error;
  const double candidate_integral = std::clamp(
    integral_ + config_.ki * error * step, -config_.integral_limit, config_.integral_limit);

  // Anti-windup (conditional integration): keep integrating only while the output can still
  // follow. Integrating against a saturated output would build up an integral that later has to
  // unwind, which shows up as overshoot.
  const double unsaturated = feedforward + proportional + candidate_integral;
  const bool saturated_high = unsaturated > config_.max_duty && error > 0.0;
  const bool saturated_low = unsaturated < 0.0 && error < 0.0;
  if (!saturated_high && !saturated_low)
  {
    integral_ = candidate_integral;
  }

  const double duty_magnitude = std::clamp(feedforward + proportional + integral_, 0.0, config_.max_duty);
  return direction * duty_magnitude;
}

void WheelSpeedController::reset()
{
  integral_ = 0.0;
  active_direction_ = 0;
  time_without_measurement_ = 0.0;
}

double WheelSpeedController::measurement_deadline(double speed_reference) const
{
  return config_.spin_up_time + 2.0 * config_.rads_per_tick / speed_reference;
}

}  // namespace firmware_minihema

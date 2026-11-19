#ifndef FIRMWARE_MINIHEMA__WHEEL_SPEED_CONTROLLER_HPP_
#define FIRMWARE_MINIHEMA__WHEEL_SPEED_CONTROLLER_HPP_

#include <optional>

namespace firmware_minihema
{

/**
 * @brief Open-loop model of the PWM duty cycle a wheel needs to spin at a given speed.
 *
 * duty = static_duty + duty_per_rad_s * |speed|
 *
 * static_duty is the dead zone of the motor/gearbox: the duty that just overcomes static
 * friction. duty_per_rad_s is the slope of the steady-state duty/speed curve. Each wheel has its
 * own model, which is where the mismatch between the two motors is compensated.
 */
struct MotorFeedforward
{
  double static_duty = 0.0;
  double duty_per_rad_s = 0.0;

  /// Unsigned duty in [0, inf) for the given speed magnitude; zero speed needs zero duty.
  double duty_for(double speed_magnitude) const;

  /// Highest speed (rad/s) the model predicts at `max_duty`; infinite when the slope is zero.
  double max_speed(double max_duty) const;
};

/// A pair of signed wheel speeds in rad/s.
struct WheelSpeeds
{
  double left = 0.0;
  double right = 0.0;
};

/**
 * @brief Scales both wheel commands by one common factor so that neither exceeds the speed its
 * motor can reach.
 *
 * Saturating only the wheel that is out of range would change the ratio between the wheels, so a
 * straight-line command would turn into a curve. A common factor keeps the ratio, and with it the
 * curvature of the path: the robot drives the same path, just slower.
 *
 * @param command   commanded speeds (signed)
 * @param max_speed reachable speed magnitude of each wheel (> 0, may be infinite)
 */
WheelSpeeds limit_preserving_curvature(const WheelSpeeds & command, const WheelSpeeds & max_speed);

/// Feedback gains, output limits and encoder timing of WheelSpeedController. Duties are in [0, 1].
struct WheelSpeedControllerConfig
{
  double kp = 0.0;              ///< Duty per rad/s of speed error.
  double ki = 0.0;              ///< Duty per rad of accumulated speed error (per rad/s per second).
  double integral_limit = 0.0;  ///< Bound on the magnitude of the integral term, in duty.
  double max_duty = 1.0;        ///< Bound on the magnitude of the output duty.

  /// Encoder resolution. With few pulses per revolution the first speed measurement after a
  /// start takes two pulses, and the controller has to know how long that is expected to take.
  double rads_per_tick = 0.0;
  /// Time the motor takes to get from rest to speed, before which pulses cannot be expected.
  double spin_up_time = 0.2;
};

/**
 * @brief Speed controller of one wheel: feedforward plus PI feedback on the measured speed.
 *
 * The feedforward produces almost all of the duty as soon as a command arrives, so the wheel
 * starts in the first control cycle. The PI term only corrects the model error, which is what
 * makes both wheels converge to their setpoints and the robot drive straight.
 *
 * Feedback needs a real speed measurement. Right after a start the encoder has not produced the
 * two pulses a measurement needs, and a reading of zero there is not true: acting on it would
 * over-drive a wheel that is already accelerating. Until a measurement arrives the output is the
 * feedforward (plus the integral learned so far). If none arrives within the time two pulses
 * take at the commanded speed, the wheel is stalled, and the PI acts on zero speed so the integral
 * builds up the extra duty needed to break static friction.
 *
 * The output never opposes the commanded direction: the encoders are single-channel, so the
 * direction of each pulse is inferred from the driven direction, and actively braking a wheel
 * would make the speed measurement wrong. A wheel that is too fast is slowed by reducing its duty,
 * down to zero (coasting).
 *
 * The output is independent of the control period: dt only scales integration and timing. A
 * late or early control cycle therefore never changes the torque applied to the motor.
 */
class WheelSpeedController
{
public:
  /// Commands below this magnitude (rad/s) stop the motor.
  static constexpr double kStopThreshold = 1e-3;

  /// Upper bound on the time step integrated in one cycle, so a stalled control loop does not
  /// make the integral jump when it resumes.
  static constexpr double kMaxIntegrationStep = 0.1;

  WheelSpeedController() = default;

  /// @throws std::invalid_argument if the feedforward or the configuration is out of range.
  WheelSpeedController(const MotorFeedforward & feedforward, const WheelSpeedControllerConfig & config);

  /**
   * @param target_speed   commanded wheel speed in rad/s (signed)
   * @param measured_speed measured wheel speed in rad/s (signed), or nullopt while the encoder
   *                       has no measurement (wheel stopped or just started)
   * @param dt             time since the previous update, in seconds
   * @return signed duty cycle in [-max_duty, max_duty]; positive drives the wheel forward
   */
  double update(double target_speed, std::optional<double> measured_speed, double dt);

  /// Forgets the integral and the current run; the next update starts from the feedforward alone.
  void reset();

  /// Current integral term, in duty (for diagnostics).
  double integral() const { return integral_; }

private:
  /// Time after which a wheel driven at `speed_reference` without any measurement is stalled.
  double measurement_deadline(double speed_reference) const;

  MotorFeedforward feedforward_;
  WheelSpeedControllerConfig config_;

  double integral_ = 0.0;
  int active_direction_ = 0;           ///< +1 / -1 while driving, 0 when stopped.
  double time_without_measurement_ = 0.0;
};

}  // namespace firmware_minihema

#endif  // FIRMWARE_MINIHEMA__WHEEL_SPEED_CONTROLLER_HPP_

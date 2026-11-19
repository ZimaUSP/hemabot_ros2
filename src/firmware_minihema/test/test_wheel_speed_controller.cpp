#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>

#include "firmware_minihema/wheel.hpp"
#include "firmware_minihema/wheel_speed_controller.hpp"

using firmware_minihema::limit_preserving_curvature;
using firmware_minihema::MotorFeedforward;
using firmware_minihema::WheelSpeedController;
using firmware_minihema::WheelSpeedControllerConfig;
using firmware_minihema::WheelSpeeds;

namespace
{

constexpr double kControlPeriod = 0.05;  // 20 Hz, as in controllers.yaml
constexpr int kTicksPerRev = 12;
const double kRadsPerTick = 2.0 * M_PI / kTicksPerRev;

const MotorFeedforward kFeedforward{0.26, 0.0883};
const WheelSpeedControllerConfig kConfig{0.06, 0.15, 0.25, 1.0, kRadsPerTick, 0.2};

const std::optional<double> kNoMeasurement = std::nullopt;

/**
 * Wheel driven by a first-order DC motor with a dead zone: for a duty d the speed tends to
 * (|d| - static_duty) / duty_per_rad_s in the direction of d, with time constant tau.
 * The physics runs at 1 ms; the encoder is the real one: kTicksPerRev pulses per revolution,
 * timestamped in microseconds and turned into a speed by the production Wheel estimator.
 */
class SimulatedWheel
{
public:
  SimulatedWheel(double static_duty, double duty_per_rad_s, double tau)
  : static_duty_(static_duty), duty_per_rad_s_(duty_per_rad_s), tau_(tau)
  {
    estimator_.setup("wheel", kTicksPerRev);
    estimator_.reset_encoder(0);
  }

  /// Runs one control period with the given duty, then samples the encoder like read() does.
  void run_period(double duty)
  {
    constexpr double kPhysicsStep = 0.001;
    for (int i = 0; i < static_cast<int>(kControlPeriod / kPhysicsStep); ++i)
    {
      const double effective = std::max(0.0, std::abs(duty) - static_duty_);
      const double steady_speed = std::copysign(effective / duty_per_rad_s_, duty);
      speed_ += (steady_speed - speed_) * (1.0 - std::exp(-kPhysicsStep / tau_));
      angle_ += speed_ * kPhysicsStep;
      time_us_ += 1000;

      const int ticks = static_cast<int>(std::floor(angle_ / kRadsPerTick));
      if (ticks != ticks_)
      {
        ticks_ = ticks;
        last_pulse_us_ = time_us_;
      }
    }
    estimator_.update(ticks_, last_pulse_us_, time_us_, 0.5, 0.5);
  }

  std::optional<double> measurement() const
  {
    return estimator_.velocity_measured ? std::optional<double>(estimator_.velocity) : std::nullopt;
  }

  double true_speed() const { return speed_; }

private:
  double static_duty_;
  double duty_per_rad_s_;
  double tau_;

  double speed_ = 0.0;
  double angle_ = 0.5 * kRadsPerTick;  // start between two slots
  int ticks_ = 0;
  unsigned int time_us_ = 1000000;
  unsigned int last_pulse_us_ = 0;
  Wheel estimator_;
};

struct Response
{
  double first_motion_s = -1.0;  ///< time until the wheel turns at all
  double peak_speed = 0.0;
  double final_speed = 0.0;
};

Response run_closed_loop(WheelSpeedController & controller, SimulatedWheel & wheel, double target, double duration)
{
  Response response;
  for (double t = 0.0; t < duration; t += kControlPeriod)
  {
    wheel.run_period(controller.update(target, wheel.measurement(), kControlPeriod));
    if (response.first_motion_s < 0.0 && std::abs(wheel.true_speed()) > 0.1)
    {
      response.first_motion_s = t + kControlPeriod;
    }
    response.peak_speed = std::max(response.peak_speed, std::abs(wheel.true_speed()));
  }
  response.final_speed = wheel.true_speed();
  return response;
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// MotorFeedforward
// ---------------------------------------------------------------------------------------------

TEST(MotorFeedforward, ZeroSpeedNeedsZeroDuty)
{
  EXPECT_DOUBLE_EQ(kFeedforward.duty_for(0.0), 0.0);
}

TEST(MotorFeedforward, AddsDeadZoneToLinearTerm)
{
  EXPECT_DOUBLE_EQ(kFeedforward.duty_for(5.0), 0.26 + 0.0883 * 5.0);
}

TEST(MotorFeedforward, MaxSpeedIsWhereModelReachesMaxDuty)
{
  EXPECT_NEAR(kFeedforward.duty_for(kFeedforward.max_speed(1.0)), 1.0, 1e-12);
  EXPECT_TRUE(std::isinf(MotorFeedforward{0.2, 0.0}.max_speed(1.0)));
}

// ---------------------------------------------------------------------------------------------
// limit_preserving_curvature
// ---------------------------------------------------------------------------------------------

TEST(LimitPreservingCurvature, ReachableCommandIsUnchanged)
{
  const WheelSpeeds limited = limit_preserving_curvature({3.0, -4.0}, {8.0, 7.0});
  EXPECT_DOUBLE_EQ(limited.left, 3.0);
  EXPECT_DOUBLE_EQ(limited.right, -4.0);
}

TEST(LimitPreservingCurvature, StraightCommandStaysStraight)
{
  // The weaker (right) motor cannot reach 10 rad/s: both wheels are slowed to its maximum
  const WheelSpeeds limited = limit_preserving_curvature({10.0, 10.0}, {8.4, 7.1});
  EXPECT_DOUBLE_EQ(limited.left, 7.1);
  EXPECT_DOUBLE_EQ(limited.right, 7.1);
}

TEST(LimitPreservingCurvature, KeepsRatioBetweenWheels)
{
  const WheelSpeeds limited = limit_preserving_curvature({12.0, -6.0}, {8.0, 8.0});
  EXPECT_DOUBLE_EQ(limited.left, 8.0);
  EXPECT_DOUBLE_EQ(limited.right, -4.0);
}

// ---------------------------------------------------------------------------------------------
// WheelSpeedController: unit behaviour
// ---------------------------------------------------------------------------------------------

TEST(WheelSpeedController, ZeroCommandStopsMotor)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  EXPECT_DOUBLE_EQ(controller.update(0.0, 3.0, kControlPeriod), 0.0);
  EXPECT_DOUBLE_EQ(controller.integral(), 0.0);
}

TEST(WheelSpeedController, NonFiniteCommandStopsMotor)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  EXPECT_DOUBLE_EQ(controller.update(std::numeric_limits<double>::quiet_NaN(), 0.0, kControlPeriod), 0.0);
  EXPECT_DOUBLE_EQ(controller.update(std::numeric_limits<double>::infinity(), 0.0, kControlPeriod), 0.0);
}

TEST(WheelSpeedController, DrivesAboveDeadZoneOnFirstCycle)
{
  // The wheel must start in the very first control cycle after the command arrives
  WheelSpeedController controller(kFeedforward, kConfig);
  const double target = 2.5;
  EXPECT_DOUBLE_EQ(controller.update(target, kNoMeasurement, kControlPeriod), kFeedforward.duty_for(target));
}

TEST(WheelSpeedController, OutputDoesNotDependOnControlPeriod)
{
  // The old implementation scaled the duty by the loop period, so a late or early cycle changed
  // the motor torque. Without integral action the output must be the same for any period.
  WheelSpeedControllerConfig proportional_only = kConfig;
  proportional_only.ki = 0.0;

  for (const double dt : {0.001, 0.05, 0.3})
  {
    WheelSpeedController controller(kFeedforward, proportional_only);
    EXPECT_DOUBLE_EQ(controller.update(4.0, 1.0, dt), kFeedforward.duty_for(4.0) + kConfig.kp * 3.0) << "dt=" << dt;
  }
}

TEST(WheelSpeedController, NegativeCommandGivesNegativeDuty)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  EXPECT_DOUBLE_EQ(controller.update(-3.0, kNoMeasurement, kControlPeriod), -kFeedforward.duty_for(3.0));
}

TEST(WheelSpeedController, NeverDrivesAgainstCommandedDirection)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  // Wheel measured far faster than commanded, in both directions
  for (int i = 0; i < 50; ++i)
  {
    EXPECT_GE(controller.update(1.0, 50.0, kControlPeriod), 0.0);
  }
  controller.reset();
  for (int i = 0; i < 50; ++i)
  {
    EXPECT_LE(controller.update(-1.0, -50.0, kControlPeriod), 0.0);
  }
}

TEST(WheelSpeedController, OutputIsLimitedToMaxDuty)
{
  WheelSpeedControllerConfig limited = kConfig;
  limited.max_duty = 0.8;
  WheelSpeedController controller(kFeedforward, limited);
  EXPECT_DOUBLE_EQ(controller.update(100.0, 0.0, kControlPeriod), 0.8);
  EXPECT_DOUBLE_EQ(controller.update(-100.0, 0.0, kControlPeriod), -0.8);
}

TEST(WheelSpeedController, WithoutMeasurementUsesFeedforwardUntilDeadline)
{
  // Right after a start the encoder has no measurement yet: no feedback on a fake zero speed
  WheelSpeedController controller(kFeedforward, kConfig);
  const double target = 3.0;
  const double deadline = kConfig.spin_up_time + 2.0 * kRadsPerTick / target;  // ~0.55 s

  for (double t = kControlPeriod; t < deadline - 1e-9; t += kControlPeriod)
  {
    EXPECT_DOUBLE_EQ(controller.update(target, kNoMeasurement, kControlPeriod), kFeedforward.duty_for(target)) << "t=" << t;
  }
  EXPECT_DOUBLE_EQ(controller.integral(), 0.0);
}

TEST(WheelSpeedController, StalledWheelBuildsUpIntegral)
{
  // No measurement long after the deadline: the wheel is stuck, so feedback must push harder
  WheelSpeedController controller(kFeedforward, kConfig);
  const double target = 3.0;
  double duty = 0.0;
  for (int i = 0; i < 40; ++i)  // 2 s
  {
    duty = controller.update(target, kNoMeasurement, kControlPeriod);
  }
  EXPECT_GT(controller.integral(), 0.0);
  EXPECT_GT(duty, kFeedforward.duty_for(target) + kConfig.kp * target);
}

TEST(WheelSpeedController, SlowerCommandsWaitLongerForMeasurement)
{
  // At 1 rad/s two pulses take ~1 s, so 0.8 s without measurement is still normal; at 4 rad/s
  // they take ~0.26 s, so the wheel is stalled
  WheelSpeedController slow(kFeedforward, kConfig);
  WheelSpeedController fast(kFeedforward, kConfig);
  for (int i = 0; i < 16; ++i)  // 0.8 s
  {
    slow.update(1.0, kNoMeasurement, kControlPeriod);
    fast.update(4.0, kNoMeasurement, kControlPeriod);
  }
  EXPECT_DOUBLE_EQ(slow.integral(), 0.0);
  EXPECT_GT(fast.integral(), 0.0);
}

TEST(WheelSpeedController, IntegralDoesNotWindUpWhileSaturated)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  // A blocked wheel under a command that already saturates the output
  for (int i = 0; i < 200; ++i)
  {
    controller.update(20.0, 0.0, kControlPeriod);
  }
  EXPECT_DOUBLE_EQ(controller.integral(), 0.0);
}

TEST(WheelSpeedController, IntegralIsBounded)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  for (int i = 0; i < 1000; ++i)
  {
    controller.update(1.5, 0.0, kControlPeriod);
  }
  EXPECT_DOUBLE_EQ(controller.integral(), kConfig.integral_limit);
}

TEST(WheelSpeedController, IntegrationStepIsBoundedAfterLoopStall)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  controller.update(1.0, 0.0, 5.0);  // control loop resumed after a 5 s stall
  EXPECT_NEAR(controller.integral(), kConfig.ki * 1.0 * WheelSpeedController::kMaxIntegrationStep, 1e-12);
}

TEST(WheelSpeedController, DirectionReversalClearsIntegral)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  for (int i = 0; i < 20; ++i)
  {
    controller.update(2.0, 1.0, kControlPeriod);
  }
  ASSERT_GT(controller.integral(), 0.0);

  controller.update(-2.0, -1.0, kControlPeriod);
  EXPECT_NEAR(controller.integral(), kConfig.ki * 1.0 * kControlPeriod, 1e-12);
}

TEST(WheelSpeedController, ResetClearsIntegral)
{
  WheelSpeedController controller(kFeedforward, kConfig);
  controller.update(2.0, 0.0, kControlPeriod);
  controller.reset();
  EXPECT_DOUBLE_EQ(controller.integral(), 0.0);
}

TEST(WheelSpeedController, RejectsInvalidConfiguration)
{
  WheelSpeedControllerConfig bad = kConfig;
  bad.max_duty = 1.5;
  EXPECT_THROW(WheelSpeedController(kFeedforward, bad), std::invalid_argument);

  bad = kConfig;
  bad.kp = -0.1;
  EXPECT_THROW(WheelSpeedController(kFeedforward, bad), std::invalid_argument);

  bad = kConfig;
  bad.rads_per_tick = 0.0;
  EXPECT_THROW(WheelSpeedController(kFeedforward, bad), std::invalid_argument);

  EXPECT_THROW(WheelSpeedController(MotorFeedforward{1.2, 0.1}, kConfig), std::invalid_argument);
  EXPECT_THROW(WheelSpeedController(MotorFeedforward{1.0, 0.1}, kConfig), std::invalid_argument);
  EXPECT_THROW(WheelSpeedController(MotorFeedforward{0.2, std::nan("")}, kConfig), std::invalid_argument);
}

// ---------------------------------------------------------------------------------------------
// Closed loop with the real speed estimator and a quantized encoder
// ---------------------------------------------------------------------------------------------

TEST(WheelSpeedControllerClosedLoop, WheelStartsWithinOneControlPeriod)
{
  SimulatedWheel wheel(0.26, 0.0883, 0.12);
  WheelSpeedController controller(kFeedforward, kConfig);
  const Response response = run_closed_loop(controller, wheel, 3.0, 1.0);
  EXPECT_GT(response.first_motion_s, 0.0);
  EXPECT_LE(response.first_motion_s, kControlPeriod);
}

TEST(WheelSpeedControllerClosedLoop, AccurateModelBarelyOvershoots)
{
  // The encoder reads zero until its second pulse; feedback acting on that reading used to
  // over-drive the wheel by 40-100% at every start
  for (const double target : {1.5, 3.0, 6.0})
  {
    SimulatedWheel wheel(0.26, 0.0883, 0.12);
    WheelSpeedController controller(kFeedforward, kConfig);
    const Response response = run_closed_loop(controller, wheel, target, 4.0);
    EXPECT_LT(response.peak_speed, 1.15 * target) << "target=" << target;
    EXPECT_NEAR(response.final_speed, target, 0.03 * target) << "target=" << target;
  }
}

TEST(WheelSpeedControllerClosedLoop, ReachesTargetDespiteModelError)
{
  // Real motor needs 30% more duty than the feedforward assumes, and has a larger dead zone
  SimulatedWheel wheel(0.32, 0.0883 * 1.3, 0.15);
  WheelSpeedController controller(kFeedforward, kConfig);
  const double target = 3.0;
  EXPECT_NEAR(run_closed_loop(controller, wheel, target, 4.0).final_speed, target, 0.03 * target);
}

TEST(WheelSpeedControllerClosedLoop, MismatchedWheelsConvergeToSameSpeed)
{
  // Same feedforward on both wheels, but the right motor is 18% weaker: without integral action
  // this is the mismatch that made the robot veer
  SimulatedWheel left_wheel(0.26, 0.0883, 0.12);
  SimulatedWheel right_wheel(0.26, 0.0883 * 1.18, 0.12);
  WheelSpeedController left_controller(kFeedforward, kConfig);
  WheelSpeedController right_controller(kFeedforward, kConfig);

  const double target = 4.0;
  const double left_speed = run_closed_loop(left_controller, left_wheel, target, 4.0).final_speed;
  const double right_speed = run_closed_loop(right_controller, right_wheel, target, 4.0).final_speed;
  EXPECT_NEAR(left_speed, right_speed, 0.03 * target);
}

TEST(WheelSpeedControllerClosedLoop, BreaksFreeWhenDeadZoneIsUnderestimated)
{
  // The real dead zone (40%) is above the feedforward at this speed: the wheel does not move
  // until the integral adds the missing duty
  SimulatedWheel wheel(0.40, 0.0883, 0.12);
  WheelSpeedController controller(kFeedforward, kConfig);
  const double target = 1.5;
  const Response response = run_closed_loop(controller, wheel, target, 4.0);
  EXPECT_GT(response.first_motion_s, 0.0);
  EXPECT_LT(response.first_motion_s, 1.5);
  EXPECT_NEAR(response.final_speed, target, 0.05 * target);
}

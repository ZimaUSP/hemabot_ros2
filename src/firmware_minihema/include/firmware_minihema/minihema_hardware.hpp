#ifndef _FIRMWARE_MINIHEMA__MINIHEMA_HARDWARE_HPP_
#define _FIRMWARE_MINIHEMA__MINIHEMA_HARDWARE_HPP_

#include <cmath>
#include <memory>
#include <cstring>
#include <thread>
#include <vector>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/node_interfaces/lifecycle_node_interface.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "motor_encoder.h"
#include "wheel.hpp"
#include "firmware_minihema/wheel_speed_controller.hpp"

using hardware_interface::return_type;
using hardware_interface::CallbackReturn;

namespace firmware_minihema
{

class MinihemaHardware : public hardware_interface::SystemInterface
{

  // Defaults reproduce the open-loop calibration the robot used before the speed controller
  // (26% dead zone, right motor needing 18% more duty than the left one).
  struct Config
  {
    std::string left_wheel_name = "left_wheel";
    std::string right_wheel_name = "right_wheel";
    int enc_ticks_per_rev = 12;

    double velocity_timeout = 0.5;      // s without pulses to consider the wheel stopped
    double velocity_filter_alpha = 0.5; // EMA on the measured speed (1.0 disables the filter)

    MotorFeedforward left_feedforward{0.26, 0.0883};
    MotorFeedforward right_feedforward{0.26, 0.1042};
    // kp, ki, integral_limit, max_duty, rads_per_tick (derived from enc_ticks_per_rev), spin_up_time
    WheelSpeedControllerConfig speed_controller{0.06, 0.15, 0.25, 1.0, 0.0, 0.2};

    double loop_stall_warn_period = 0.15; // s between control cycles above which a stall is reported
  };

  public:
    MinihemaHardware();

    CallbackReturn on_init(const hardware_interface::HardwareInfo & info) override;

    std::vector<hardware_interface::StateInterface> export_state_interfaces() override;

    std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

    CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;

    CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;

    CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;

    return_type read(const rclcpp::Time & time, const rclcpp::Duration & period) override;

    return_type write(const rclcpp::Time & time, const rclcpp::Duration & period) override;

  private:
    void load_config();

    // Reports control cycles that arrive much later than expected. While the loop is stalled the
    // motors keep their last duty and new velocity commands are not applied.
    void report_loop_stall(double period_s);

    void stop_motors();

    Config config_;

    Wheel left_wheel_;
    Wheel right_wheel_;

    WheelSpeedController left_speed_controller_;
    WheelSpeedController right_speed_controller_;

    // Speeds the motors can reach according to their feedforward models
    WheelSpeeds max_wheel_speeds_;

    bool driving_ = false;

    rclcpp::Logger logger_;
    rclcpp::Clock steady_clock_{RCL_STEADY_TIME}; // for log throttling only

};

} // namespace FIRMWARE_MINIHEMA

#endif

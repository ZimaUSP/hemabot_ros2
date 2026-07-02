#include "firmware_minihema/minihema_hardware.hpp"
#include "firmware_minihema/PinPlannerRasp.h"

namespace firmware_minihema
{

MinihemaHardware::MinihemaHardware()
    : logger_(rclcpp::get_logger("MinihemaHardware"))
{}

CallbackReturn MinihemaHardware::on_init(const hardware_interface::HardwareInfo & info)
{
    if (hardware_interface::SystemInterface::on_init(info) != CallbackReturn::SUCCESS)
    {
        return CallbackReturn::ERROR;
    }

    RCLCPP_INFO(logger_, "Initializing...");

    config_.left_wheel_name = info_.hardware_parameters["left_wheel_name"];
    config_.right_wheel_name = info_.hardware_parameters["right_wheel_name"];
    config_.enc_ticks_per_rev = std::stoi(info_.hardware_parameters["enc_ticks_per_rev"]);
    config_.loop_rate = std::stod(info_.hardware_parameters["loop_rate"]); // Mantido para referência, se necessário em outro lugar

    left_wheel_.setup(config_.left_wheel_name, config_.enc_ticks_per_rev);
    right_wheel_.setup(config_.right_wheel_name, config_.enc_ticks_per_rev);

    RCLCPP_INFO(logger_, "Finished initialization");

    return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> MinihemaHardware::export_state_interfaces()
{
    std::vector<hardware_interface::StateInterface> state_interfaces;

    state_interfaces.emplace_back(hardware_interface::StateInterface(left_wheel_.name, hardware_interface::HW_IF_VELOCITY, &left_wheel_.velocity));
    state_interfaces.emplace_back(hardware_interface::StateInterface(left_wheel_.name, hardware_interface::HW_IF_POSITION, &left_wheel_.position));
    state_interfaces.emplace_back(hardware_interface::StateInterface(right_wheel_.name, hardware_interface::HW_IF_VELOCITY, &right_wheel_.velocity));
    state_interfaces.emplace_back(hardware_interface::StateInterface(right_wheel_.name, hardware_interface::HW_IF_POSITION, &right_wheel_.position));

    return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> MinihemaHardware::export_command_interfaces()
{
    std::vector<hardware_interface::CommandInterface> command_interfaces;

    command_interfaces.emplace_back(hardware_interface::CommandInterface(left_wheel_.name, hardware_interface::HW_IF_VELOCITY, &left_wheel_.command));
    command_interfaces.emplace_back(hardware_interface::CommandInterface(right_wheel_.name, hardware_interface::HW_IF_VELOCITY, &right_wheel_.command));

    return command_interfaces;
}

CallbackReturn MinihemaHardware::on_configure(const rclcpp_lifecycle::State & /*previous_state*/)
{
    RCLCPP_INFO(logger_, "Configuring motors and encoders...");
    
    wiringPiSetupGpio();
    
    // Initialize motor driver
    Motor_Init();
    
    // Setup GPIO encoder interrupt and direction pins
    pinMode(LEFT_WHL_ENC_D0, INPUT);
    pinMode(RIGHT_WHL_ENC_D0, INPUT);

    // Setup pull up resistors on encoder interrupt pins
    pullUpDnControl(LEFT_WHL_ENC_D0, PUD_UP);
    pullUpDnControl(RIGHT_WHL_ENC_D0, PUD_UP);

    // Initialize encoder interrupts for falling signal states
    wiringPiISR(LEFT_WHL_ENC_D0, INT_EDGE_FALLING, add_left_wheel);
    wiringPiISR(RIGHT_WHL_ENC_D0, INT_EDGE_FALLING, add_right_wheel);

    RCLCPP_INFO(logger_, "Successfully configured motors and encoders!");

    return CallbackReturn::SUCCESS;
}

CallbackReturn MinihemaHardware::on_activate(const rclcpp_lifecycle::State & /*previous_state*/)
{
    RCLCPP_INFO(logger_, "Starting controller ...");

    // Zera os comandos e estados ao ativar para evitar saltos bruscos
    left_wheel_.command = 0.0;
    right_wheel_.command = 0.0;

    return CallbackReturn::SUCCESS;
}

CallbackReturn MinihemaHardware::on_deactivate(const rclcpp_lifecycle::State & /*previous_state*/)
{   
    RCLCPP_INFO(logger_, "Stopping Controller... Halting hardware!");

    // CRÍTICO: Parada física do robô
    set_motor_speeds(0.0, 0.0);
    Motor_Stop(MOTORA);
    Motor_Stop(MOTORB);

    return CallbackReturn::SUCCESS;
}

return_type MinihemaHardware::read(const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
{
    double delta_seconds = period.seconds();

    // Obtain encoder values
    read_encoder_values(&left_wheel_.encoder_ticks, &right_wheel_.encoder_ticks);

    // Prevenção de divisão por zero
    if (delta_seconds > 1e-5) 
    {
        double previous_position = left_wheel_.position;
        left_wheel_.position = left_wheel_.calculate_encoder_angle();
        left_wheel_.velocity = (left_wheel_.position - previous_position) / delta_seconds;

        previous_position = right_wheel_.position;
        right_wheel_.position = right_wheel_.calculate_encoder_angle();
        right_wheel_.velocity = (right_wheel_.position - previous_position) / delta_seconds;
    }

    return return_type::OK;
}

return_type MinihemaHardware::write(const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
{   
    double delta_seconds = period.seconds();

    // Cálculo utilizando o tempo real da iteração (delta_t) em vez da frequência teórica
    double left_motor_counts_per_loop = (left_wheel_.command * delta_seconds) / left_wheel_.rads_per_tick;
    double right_motor_counts_per_loop = (right_wheel_.command * delta_seconds) / right_wheel_.rads_per_tick;

    DEBUG("Enviando comandos para o driver do motor: left=%f, right=%f\n", left_motor_counts_per_loop, right_motor_counts_per_loop);
    // Send commands to motor driver
    set_motor_speeds(left_motor_counts_per_loop, right_motor_counts_per_loop);

    return return_type::OK;
}

} // namespace firmware_minihema

#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(
    firmware_minihema::MinihemaHardware, 
    hardware_interface::SystemInterface)
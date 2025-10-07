extern "C" {
  #include "firmware_minihema/KeyesDriver.h"
  #include "firmware_minihema/motor_encoder.h"
}
int main(int argc, char **argv)
{
    int x=0, y=0;
    // Setup GPIO encoder interrupt and direction pins
    wiringPiSetupGpio();
    // Initialize motor driver
    Motor_Init();

    // Initialize wiringPi using GPIO BCM pin numbers
    pinMode(LEFT_WHL_ENC_D0, INPUT);
    pinMode(RIGHT_WHL_ENC_D0, INPUT);

    // Setup pull up resistors on encoder pins
    pullUpDnControl(LEFT_WHL_ENC_D0, PUD_UP);
    pullUpDnControl(RIGHT_WHL_ENC_D0, PUD_UP);

    // Initialize encoder interrupts for falling signal states
    wiringPiISR(LEFT_WHL_ENC_D0, INT_EDGE_FALLING,  add_left_wheel);
    wiringPiISR(RIGHT_WHL_ENC_D0, INT_EDGE_FALLING, add_right_wheel);

    set_motor_speeds(1000, 1000); 
    
    read_encoder_values(&x, &y);
    
    DEBUG("Left encoder: %d \r\n", x);
    DEBUG("Right encoder: %d \r\n", y);
    /*
    // Initialize the rclcpp library
    rclcpp::init(argc, argv);

    // Create a shared pointer to a Node type and name it "motor_checks_server"
    std::shared_ptr<rclcpp::Node> node = rclcpp::Node::make_shared("motor_checks_server");

    // Create a "checks" service with a checkMotors callback
    rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr service = 
        node->create_service<std_srvs::srv::Trigger>("checks", &checkMotors);

    RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "Ready to check motors");
s
    // Spin the node until it's terminated
    rclcpp::spin(node);
    rclcpp::shutdown();
    */
}
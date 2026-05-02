#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "geometry_msgs/msg/twist.hpp"

class ObstacleAvoidance : public rclcpp::Node
{
public:
    ObstacleAvoidance() : Node("obstacle_avoidance")
    {
        subscription_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
            "/scan", 10,
            std::bind(&ObstacleAvoidance::scan_callback, this, std::placeholders::_1));

        publisher_ = this->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 22);
    }

private:
    void scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr msg)
    {
        int size = msg->ranges.size();

        // Região frontal
        int start = size / 3;
        int end = 2 * size / 3;

        float min_distance = std::numeric_limits<float>::infinity();

        for (int i = start; i < end; i++)
        {
            float r = msg->ranges[i];

            if (r > 0.0 && r < min_distance)
                min_distance = r;
        }

        RCLCPP_INFO(this->get_logger(), "Distancia minima: %.2f", min_distance);

        geometry_msgs::msg::Twist cmd;

        if (min_distance < 0.5)
        {
            cmd.linear.x = 0.0;
            cmd.angular.z = 0.5; // gira
        }
        else
        {
            cmd.linear.x = 0.2;
            cmd.angular.z = 0.0; // anda reto
        }

        publisher_->publish(cmd);
    }

    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr subscription_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ObstacleAvoidance>());
    rclcpp::shutdown();
    return 0;
}

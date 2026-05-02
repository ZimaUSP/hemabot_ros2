cmake_minimum_required(VERSION 3.8)
project(d_hospital_gazebo2)

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)

find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

install(
  DIRECTORY config launch worlds
  DESTINATION share/${PROJECT_NAME}
)

add_executable(obstacle_avoidance src/obstacle_avoidance.cpp)

ament_target_dependencies(obstacle_avoidance
  rclcpp
  sensor_msgs
  geometry_msgs
)

install(TARGETS
  obstacle_avoidance
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
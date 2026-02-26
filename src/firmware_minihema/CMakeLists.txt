cmake_minimum_required(VERSION 3.8)
project(firmware_minihema)

# Find required packages
find_package(ament_cmake REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(std_srvs REQUIRED)

# Include directories
include_directories(include)

# ------------------------------------------------------------------------------
# minihema_hardware library
# ------------------------------------------------------------------------------

add_library(minihema_hardware SHARED 
  src/minihema_hardware.cpp 
  src/wheel.cpp 
  src/KeyesDriver.c
  src/motor_encoder.c
)

target_include_directories(minihema_hardware PRIVATE include)

ament_target_dependencies(
  minihema_hardware
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
)

target_link_libraries(minihema_hardware wiringPi)

pluginlib_export_plugin_description_file(hardware_interface minihema_hardware.xml)

# Install library and headers
install(
  DIRECTORY include/
  DESTINATION include/minihema_hardware
)

install(
  TARGETS minihema_hardware
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)

# ------------------------------------------------------------------------------
# motor_test executable
# ------------------------------------------------------------------------------

add_executable(motor_test
  src/motor_test.cpp 
  src/motor_encoder.c
  src/KeyesDriver.c
)

ament_target_dependencies(motor_test
  rclcpp
  std_srvs
)

target_link_libraries(motor_test
  m
  wiringPi
  pthread
  crypt
  rt
)

target_compile_options(motor_test PRIVATE -w)  # Remove warnings (optional)

# ------------------------------------------------------------------------------
# Install executables
# ------------------------------------------------------------------------------

install(
  TARGETS 
    motor_test
  DESTINATION lib/${PROJECT_NAME}
)
# ------------------------------------------------------------------------------
# motor_stop executable
# ------------------------------------------------------------------------------

add_executable(motor_stop
  src/motor_stop.c
  src/motor_encoder.c
  src/KeyesDriver.c
)

ament_target_dependencies(motor_stop
  rclcpp
  std_srvs
)

target_link_libraries(motor_stop
  m
  wiringPi
  pthread
  crypt
  rt
)

target_compile_options(motor_stop PRIVATE -w)  # Remove warnings (optional)

# ------------------------------------------------------------------------------
# Install executables
# ------------------------------------------------------------------------------

install(
  TARGETS
    motor_stop
  DESTINATION lib/${PROJECT_NAME}
)


# ------------------------------------------------------------------------------
# Export the library
# ------------------------------------------------------------------------------

ament_export_libraries(minihema_hardware)

ament_package()


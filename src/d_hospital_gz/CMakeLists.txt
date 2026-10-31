cmake_minimum_required(VERSION 3.10)
project(d_hospital_gz)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch models urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()


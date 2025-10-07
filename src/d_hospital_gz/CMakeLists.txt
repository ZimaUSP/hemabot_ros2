cmake_minimum_required(VERSION 3.8)
project(d_hospital_gz)

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)

install(
  DIRECTORY config launch models urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()


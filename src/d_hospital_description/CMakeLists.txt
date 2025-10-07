cmake_minimum_required(VERSION 3.8)
project(d_hospital_description)

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)

install(
  DIRECTORY launch meshes urdf rviz config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

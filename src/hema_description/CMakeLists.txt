cmake_minimum_required(VERSION 3.8)
project(hema_description)

find_package(ament_cmake REQUIRED)

# Instala a descriÃ§Ã£o junto das malhas, controladores e mundos usados no launch.
install(DIRECTORY urdf meshes config launch worlds docs scripts
  DESTINATION share/${PROJECT_NAME}
)

install(FILES README.md DESTINATION share/${PROJECT_NAME})

ament_package()

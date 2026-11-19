# launch

## Subpastas

- [`__pycache__/`](__pycache__/README.md) — Bytecode gerado pelo Python para arquivos de launch.

## Arquivos

- `camera_launch.py` — Inicia o nó `v4l2_camera` para publicar as imagens da câmera.
- `minihema_launch.py` — Gera a descrição pelo Xacro e a compartilha com os nós de estado e controle, iniciando também a IMU, o LiDAR, a odometria filtrada e o joystick.
- `rplidar_launch.py` — Inicia o driver do RPLIDAR para publicar as varreduras do laser no ROS 2.

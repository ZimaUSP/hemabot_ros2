# launch

## Subpastas

- [`__pycache__/`](__pycache__/README.md) — Bytecode gerado pelo Python para arquivos de launch.

## Arquivos

- `camera_launch.py` — Inicia o nó `v4l2_camera` para publicar as imagens da câmera.
- `minihema_launch.py` — Sobe a descrição, os controladores, a IMU, o LiDAR, a odometria filtrada e o controle por joystick do robô físico.
- `rplidar_launch.py` — Inicia o driver do RPLIDAR para publicar as varreduras do laser no ROS 2.

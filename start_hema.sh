#!/bin/bash

echo "=========================="
echo "SETUP DO ROBO"
echo "=========================="

# carregar ambiente ROS2
source install/setup.bash

echo ""
echo "1️⃣Calibrando offsets da IMU..."
./calibrar_offsets

echo ""
echo " Calculando covariancias da IMU..."
./calibrar_covariancias.sh

echo ""
echo "3️⃣Recompilando workspace..."
colcon build

echo ""
echo "4️⃣Iniciando sistemma do robo..."

ros2 launch minihema_launch minihema_launch.py

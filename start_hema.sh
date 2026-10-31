#!/bin/bash
#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/hemabot/hemabot_ros2/install/setup.bash

# 2 executar programa
echo "Executando calculo de offsets..."
saida=$(ros2 run minihema_launch mpu6050_offsets)
echo "=========================="
echo "SETUP DO ROBO"
echo "=========================="

# carregar ambiente ROS2
source install/setup.bash

echo ""
echo "1️⃣Calibrando offsets da IMU..."
/home/hemabot/hemabot_ros2/calibrar_offsets

echo ""
echo " Calculando covariancias da IMU..."
/home/hemabot/hemabot_ros2/calibrar_covariancias.sh

echo ""
echo "3️⃣Recompilando workspace..."
colcon build

echo ""
echo "4️⃣Iniciando sistemma do robo..."

ros2 launch minihema_launch minihema_launch.py

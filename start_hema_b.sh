#!/bin/bash

echo "================================="
echo "SETUP AUTOMATICO DO ROBO"
echo "================================="

# criar pasta de logs
mkdir -p logs
logfile="logs/setup_$(date +%Y%m%d_%H%M%S).log"

echo "Logs salvos em $logfile"

# carregar ambiente ROS2
source install/setup.bash

echo ""
echo "1️⃣ Calibrando offsets da IMU..."
./calibrar_offsets | tee -a $logfile

echo ""
echo "2️⃣ Calculando covariancias da IMU..."
./calibrar_covariancias.sh | tee -a $logfile

echo ""
echo "3️⃣ Recompilando workspace..."
colcon build | tee -a $logfile

# recarregar ambiente
source install/setup.bash

echo ""
read -p "Pressione ENTER para iniciar o sistema do robo..."

echo ""
echo "4️⃣ Iniciando sistema ROS2..."

gnome-terminal -- bash -c "source install/setup.bash; ros2 launch minihema_launch minihema_launch.py; exec bash"

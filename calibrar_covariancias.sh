#!/bin/bash
#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/hemabot/hemabot_ros2/install/setup.bash

# 2 executar programa
echo "Executando calculo de offsets..."
saida=$(ros2 run minihema_launch mpu6050_offsets)
echo "Calculando covariancias da IMU..."

source install/setup.bash

saida=$(ros2 run minihema_launch mpu6050_covariances)

echo "$saida"

orient=$(echo "$saida" | grep "static_covariance_orientation")
angvel=$(echo "$saida" | grep "static_covariance_angular_velocity")
linacc=$(echo "$saida" | grep "static_covariance_linear_acceleration")

arquivo="/home/hemabot/hemabot_ros2/src/minihema_launch/config/controllers.yaml"

echo "Atualizando $arquivo"

sed -i "s|static_covariance_orientation:.*|$orient|" $arquivo
sed -i "s|static_covariance_angular_velocity:.*|$angvel|" $arquivo
sed -i "s|static_covariance_linear_acceleration:.*|$linacc|" $arquivo


arquivo="/home/hemabot/hemabot_ros2/src/d_hospital_description/config/controllers.yaml"


sed -i "s|static_covariance_orientation:.*|$orient|" $arquivo
sed -i "s|static_covariance_angular_velocity:.*|$angvel|" $arquivo
sed -i "s|static_covariance_linear_acceleration:.*|$linacc|" $arquivo
echo "Covariancias atualizadas!"

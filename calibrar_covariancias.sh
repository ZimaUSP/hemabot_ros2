#!/bin/bash

echo "Calculando covariancias da IMU..."

source install/setup.bash

saida=$(ros2 run minihema_launch mpu6050_covariances)

echo "$saida"

orient=$(echo "$saida" | grep "static_covariance_orientation")
angvel=$(echo "$saida" | grep "static_covariance_angular_velocity")
linacc=$(echo "$saida" | grep "static_covariance_linear_acceleration")

arquivo="src/minihema_launch/config/controllers.yaml"

echo "Atualizando $arquivo"

sed -i "s|static_covariance_orientation:.*|$orient|" $arquivo
sed -i "s|static_covariance_angular_velocity:.*|$angvel|" $arquivo
sed -i "s|static_covariance_linear_acceleration:.*|$linacc|" $arquivo

echo "Covariancias atualizadas!"

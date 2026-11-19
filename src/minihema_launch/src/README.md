# src

## Arquivos

- `mpu6050_covariances.cpp` — Coleta amostras da IMU para estimar a covariância das medições.
- `mpu6050_hardware_interface.cpp` — Lê o MPU6050 e passa as medições para o ros2_control.
- `mpu6050_lib.cpp` — Implementa a comunicação com o MPU6050 e a leitura de suas medições.
- `mpu6050_offsets.cpp` — Coleta amostras da IMU para calcular seus offsets de calibração.

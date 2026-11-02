# Relatório de Execução — Amostra 11

**Experimento:** experimento
**Data/hora de início:** 2026-09-14T00:25:41-03:00
**Classificação final:** `concluida`

## Ambiente

| Parâmetro | Valor |
|---|---|
| Distribuição ROS 2 | humble |
| Versão do Gazebo | desconhecida |
| Motor de física | ode |
| Presença de EKF | ausente |

## Parâmetros da simulação (mundo)

```json
{
  "world_file": "./src/d_hospital_gazebo2/worlds/pea.world",
  "physics_engine": "ode",
  "max_step_size": "0.001",
  "real_time_update_rate": "1000",
  "real_time_factor_configurado": "1.0"
}
```

## Parâmetros do robô

```json
{
  "urdf_file": "./src/d_hospital_description/urdf/robot.urdf",
  "controllers_yaml": "./src/d_hospital_description/config/controllers.yaml",
  "aviso_ambiguidade_controllers_yaml": "ATENÇÃO: 2 arquivos controllers.yaml encontrados no workspace com possíveis valores DIFERENTES (./src/d_hospital_description/config/controllers.yaml;./src/minihema_launch/config/controllers.yaml;). Usado: ./src/d_hospital_description/config/controllers.yaml. Confirme manualmente qual é o efetivamente carregado pelo seu launch antes de citar wheel_radius/wheel_separation em relatório científico.",
  "wheel_radius_m": "0.0325",
  "wheel_separation_m": "0.165",
  "massa_total_kg_aprox": "1.4700"
}
```

## Pose e velocidade iniciais

```json
{
  "posicao_inicial": {"x": "-10.000416508974933", "y": "0.000781300969858107", "z": "0.0025972953954445654"},
  "orientacao_inicial_quaternion": {"x": "0.00019803936116792896", "y": "-0.023608409768311373", "z": "0.009072933232305954", "w": "0.999680022433274"},
  "orientacao_inicial_yaw_rad": "0.018152",
  "velocidade_linear_inicial_x": "-4.331121679105065e-05",
  "velocidade_angular_inicial_z": "5.13277321619411e-06"
}
```

## Comando do experimento

| Parâmetro | Valor |
|---|---|
| Velocidade linear comandada (m/s) | -0.25 |
| Velocidade angular comandada (rad/s) | 0.0 |
| Sentido do deslocamento | ré |
| Distância planejada (m) | 5.0 |
| Duração máxima configurada (s) | 20.0000 |
| Tempo efetivamente gasto (s) | 20.466841306 |

## Frequências medidas (Hz)

| Tópico | Frequência |
|---|---|
| /odom | N/A |
| /imu | N/A |
| /scan | 2.923 |
| /joint_states | 9.989 |
| /cmd_vel | 30.023 |
| Controlador (configurado, controllers.yaml) | 30 |

## Estatísticas pós-execução

```json
{
  "mensagens_odom_recebidas": 2861,
  "distancia_percorrida_m_estimada": "6.9386",
  "velocidade_media_m_s_estimada": "0.3390"
}
```

## Arquivos desta amostra

- Rosbag: `rosbag/`
- CSVs: `csv/`
- Logs: `logs_rosbag.log`
- Resultado: `resultado.txt`

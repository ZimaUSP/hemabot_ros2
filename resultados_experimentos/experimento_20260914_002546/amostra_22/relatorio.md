# Relatório de Execução — Amostra 22

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
  "posicao_inicial": {"x": "-9.998410971585951", "y": "0.00020682675766832916", "z": "0.0025955519463258594"},
  "orientacao_inicial_quaternion": {"x": "3.8608506828419e-05", "y": "-0.023595365464978414", "z": "0.002624146643365527", "w": "0.9997163863633973"},
  "orientacao_inicial_yaw_rad": "0.005251",
  "velocidade_linear_inicial_x": "-0.0008146558545421637",
  "velocidade_angular_inicial_z": "4.9198234200664584e-05"
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
| Tempo efetivamente gasto (s) | 20.247921100 |

## Frequências medidas (Hz)

| Tópico | Frequência |
|---|---|
| /odom | 96.426 |
| /imu | N/A |
| /scan | 4.859 |
| /joint_states | 10.001 |
| /cmd_vel | 29.998 |
| Controlador (configurado, controllers.yaml) | 30 |

## Estatísticas pós-execução

```json
{
  "mensagens_odom_recebidas": 4771,
  "distancia_percorrida_m_estimada": "4.3570",
  "velocidade_media_m_s_estimada": "0.2152"
}
```

## Arquivos desta amostra

- Rosbag: `rosbag/`
- CSVs: `csv/`
- Logs: `logs_rosbag.log`
- Resultado: `resultado.txt`

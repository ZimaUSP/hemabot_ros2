# Relatório de Execução — Amostra 8

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
  "posicao_inicial": {"x": "-9.998809569524958", "y": "0.00036160143670380704", "z": "0.0025954100334074984"},
  "orientacao_inicial_quaternion": {"x": "8.522018189835701e-05", "y": "-0.02360842594366658", "z": "0.00517216960740754", "w": "0.9997034218012605"},
  "orientacao_inicial_yaw_rad": "0.010349",
  "velocidade_linear_inicial_x": "0.000597739819848343",
  "velocidade_angular_inicial_z": "0.0009585421585709537"
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
| Tempo efetivamente gasto (s) | 20.458051540 |

## Frequências medidas (Hz)

| Tópico | Frequência |
|---|---|
| /odom | 59.322 |
| /imu | N/A |
| /scan | 3.037 |
| /joint_states | 9.977 |
| /cmd_vel | 29.710 |
| Controlador (configurado, controllers.yaml) | 30 |

## Estatísticas pós-execução

```json
{
  "mensagens_odom_recebidas": 2833,
  "distancia_percorrida_m_estimada": "6.9311",
  "velocidade_media_m_s_estimada": "0.3388"
}
```

## Arquivos desta amostra

- Rosbag: `rosbag/`
- CSVs: `csv/`
- Logs: `logs_rosbag.log`
- Resultado: `resultado.txt`

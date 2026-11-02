# Relatório de Execução — Amostra 30

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
  "posicao_inicial": {"x": "-9.998448983553166", "y": "0.00021786437097445814", "z": "0.0025954672922606364"},
  "orientacao_inicial_quaternion": {"x": "4.111877089255431e-05", "y": "-0.023608510832279956", "z": "0.0026892606178442404", "w": "0.9997162564092028"},
  "orientacao_inicial_yaw_rad": "0.005381",
  "velocidade_linear_inicial_x": "0.0005932900964126243",
  "velocidade_angular_inicial_z": "0.00010681049106916687"
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
| Tempo efetivamente gasto (s) | 20.270041176 |

## Frequências medidas (Hz)

| Tópico | Frequência |
|---|---|
| /odom | 95.087 |
| /imu | N/A |
| /scan | 4.813 |
| /joint_states | 10.002 |
| /cmd_vel | 30.000 |
| Controlador (configurado, controllers.yaml) | 30 |

## Estatísticas pós-execução

```json
{
  "mensagens_odom_recebidas": 4774,
  "distancia_percorrida_m_estimada": "4.7686",
  "velocidade_media_m_s_estimada": "0.2353"
}
```

## Arquivos desta amostra

- Rosbag: `rosbag/`
- CSVs: `csv/`
- Logs: `logs_rosbag.log`
- Resultado: `resultado.txt`

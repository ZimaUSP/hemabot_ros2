# firmware_minihema

Interface de hardware `ros2_control` dos motores e encoders do MiniHema (Raspberry Pi 4 +
driver L298N + encoders ópticos de 12 pulsos por volta).

## Controle de velocidade das rodas

```
/cmd_vel_joy ─┐
              ├─ twist_mux ─ diff_drive_controller ─ comando de cada roda (rad/s)
/cmd_vel ─────┘                                              │
                                     ┌───────────────────────┘
                                     ▼
               limit_preserving_curvature   (reduz as duas rodas juntas se uma não alcança o comando)
                                     │
                                     ▼
          WheelSpeedController (por roda): duty = feedforward + PI(velocidade medida)
                                     │
                                     ▼
                     set_motor_duties ─ softPwm ─ L298N ─ motor
```

- **Feedforward** (`static_duty + duty_per_rad_s·|ω|`): gera quase todo o duty no primeiro
  ciclo, então a roda parte em até 50 ms. Cada motor tem o seu modelo, e é nele que fica a
  diferença entre os motores (o antigo `RIGHT_WHEEL_RATIO 1.18`).
- **PI**: corrige o erro do modelo. O termo integral faz cada roda chegar exatamente na sua
  velocidade, e é isso que faz o robô andar reto. Tem anti-windup e é zerado ao parar ou inverter
  o sentido.
- **Sem medição, sem realimentação**: o encoder só mede a velocidade a partir do 2º pulso depois da
  partida. Até lá, a leitura "0 rad/s" é falsa, e o controlador usa só o feedforward. Se o pulso não
  vier no tempo esperado para a velocidade comandada, a roda está travada, e o PI passa a
  aumentar o duty até vencer o atrito estático.
- **Saturação sem curvar**: se a roda mais fraca não alcança o comando, as duas rodas são reduzidas
  na mesma proporção, e o robô segue o mesmo caminho, só que mais devagar. Com a calibração atual a
  roda direita satura em ~7,1 rad/s (~0,28 m/s).
- O duty **não depende do período do loop**. Antes era `comando × período`, então qualquer atraso
  ou adiantamento do loop mudava o torque do motor.
- O duty nunca é aplicado contra o sentido comandado: o encoder tem um canal só, e o sentido de
  cada pulso vem do sentido acionado.

A lógica do controle não depende de ROS nem de wiringPi e tem testes unitários (com simulação de
motor e encoder quantizado):

```bash
colcon build --packages-select firmware_minihema
colcon test --packages-select firmware_minihema --event-handlers console_direct+
```

## Parâmetros (`d_hospital_description/urdf/ros2_control.xacro`)

| Parâmetro | Padrão | Significado |
|---|---|---|
| `left_static_duty`, `right_static_duty` | 0.26 | Zona morta: duty que vence o atrito estático (0..1) |
| `left_duty_per_rad_s`, `right_duty_per_rad_s` | 0.0883 / 0.1042 | Duty extra por rad/s |
| `speed_kp` | 0.06 | Duty por rad/s de erro |
| `speed_ki` | 0.15 | Duty por rad de erro acumulado |
| `speed_integral_limit` | 0.25 | Limite do termo integral (duty) |
| `max_duty` | 1.0 | Duty máximo |
| `spin_up_time` | 0.2 | Tempo (s) até o motor ganhar velocidade, antes de esperar pulsos |
| `velocity_timeout` | 0.5 | Sem pulsos por esse tempo (s) = roda parada |
| `velocity_filter_alpha` | 0.5 | Filtro EMA na velocidade medida (1 = sem filtro) |
| `loop_stall_warn_period` | 0.15 | Avisa quando dois ciclos do loop ficam mais distantes que isso (s) |

Velocidade mínima mensurável: um pulso por `velocity_timeout`, ou seja, 2π/12/0,5 ≈ 1 rad/s
(≈ 4 cm/s). Abaixo disso a realimentação não tem medição.

## Calibração do feedforward

Quanto melhor o feedforward, menor o trabalho do PI e mais limpa a partida. Com o robô no chão:

1. `ros2 launch minihema_launch minihema_launch.py hardware_log_level:=debug`
2. Ande reto em 3 ou 4 velocidades (por exemplo 0,1 / 0,2 / 0,3 m/s) por alguns segundos cada.
   O log mostra uma vez por segundo `Target`, `Vel`, `Duty` e `Integral` de cada roda.
3. Em regime, anote para cada roda o par (|Vel|, |Duty|) e ajuste uma reta
   `duty = static_duty + duty_per_rad_s·|ω|`. Se o `Integral` de uma roda fica sempre longe de 0,
   o modelo daquela roda está errado.
4. Coloque os valores no xacro, rode `colcon build` e repita: com o modelo certo o `Integral`
   fica perto de 0.

Para o `static_duty`: aumente o duty aos poucos com o robô parado no chão até a roda começar a
girar (o `motor_test` ajuda) e use um valor um pouco abaixo disso.

## Diagnóstico de atraso

Com o robô **suspenso**:

```bash
ros2 run firmware_minihema measure_drive_latency.py            # entrada /cmd_vel_joy (web/joystick)
ros2 run firmware_minihema measure_drive_latency.py --topic /cmd_vel
```

O script manda degraus de velocidade e mede quanto tempo cada etapa leva:
`publish -> mux` (DDS + twist_mux) e `mux -> wheel` (loop do ros2_control + motor + 1 pulso do
encoder). Ele diz em qual lado está o atraso.

O `ros2_control_node` também avisa `Control loop stalled` quando o loop trava. Enquanto o loop está
travado nenhum comando novo chega aos motores.

### `ros2 topic pub` no terminal

`ros2 topic pub` não serve para medir atraso:

- o processo leva de 1 a 3 s para iniciar na Raspberry (Python + descoberta DDS), e esse tempo
  varia;
- sem `-r` ele publica a **1 Hz**, mas o twist_mux e o diff_drive_controller descartam comandos
  com mais de 0,5 s. O robô anda meio segundo e para meio segundo.

Use sempre uma taxa de pelo menos 10 Hz:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
```

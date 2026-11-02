# Tutorial completo: locomoção, mapeamento e navegação autônoma

Este tutorial descreve o processo completo para simular o robô HemaBot no Gazebo, construir um mapa com SLAM, salvar esse mapa e realizar navegação autônoma usando AMCL e Nav2.

O processo possui duas fases:

1. Dirigir o robô manualmente enquanto o SLAM constrói o mapa.
2. Salvar o mapa, reiniciar a simulação, localizar o robô com AMCL e navegar autonomamente com Nav2.

> [!IMPORTANT]
> Não execute SLAM e AMCL simultaneamente. Os dois sistemas publicam a transformação `map → odom` e entrarão em conflito.

## 1. Preparar o ambiente

Entre no workspace e carregue o ROS 2 Humble:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
```

Se algum pacote necessário não estiver instalado, instale as dependências:

```bash
sudo apt install \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-robot-localization \
  ros-humble-twist-mux \
  ros-humble-teleop-twist-keyboard
```

Compile os pacotes utilizados neste tutorial:

```bash
colcon build --symlink-install \
  --packages-select \
  d_hospital_description \
  d_hospital_teleop \
  d_hospital_gazebo2 \
  d_hospital_slam \
  d_hospital_navigation2

source install/setup.bash
```

### Configuração de cada terminal

Todos os novos terminais usados nas próximas etapas devem carregar o workspace:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash
```

## Fase 1: locomoção e mapeamento

## 2. Iniciar o robô no Gazebo

No **Terminal 1**, execute:

```bash
ros2 launch d_hospital_gazebo2 hospital.py \
  use_sim_time:=true \
  use_ros2_control:=false \
  use_robot_localization:=false
```

Os dois parâmetros com valor `false` são importantes na configuração atual do projeto. O URDF utiliza o plugin diferencial nativo do Gazebo, definido em `src/d_hospital_description/urdf/gazebo_control.xacro`, em vez do `ros2_control`.

Espere o mundo e o robô aparecerem no Gazebo. Verifique se a simulação está publicando o relógio, o laser e a odometria:

```bash
ros2 topic echo /clock --once
ros2 topic echo /scan --once
ros2 topic echo /odom --once
```

Os três comandos devem retornar uma mensagem.

## 3. Iniciar o SLAM

No **Terminal 2**, execute:

```bash
ros2 launch d_hospital_slam online_async_launch.py \
  use_sim_time:=true
```

A configuração do SLAM utiliza:

- `/scan` para as leituras do LiDAR;
- `odom` como referencial odométrico;
- `base_footprint` como base do robô;
- `map` como referencial global.

Esses parâmetros estão em `src/d_hospital_slam/config/mapper_params_online_async.yaml`.

## 4. Acompanhar o mapa no RViz

No **Terminal 3**, execute:

```bash
rviz2 -d src/d_hospital_slam/rviz/lidarbot_slam.rviz
```

No RViz, confirme as seguintes configurações:

- `Fixed Frame`: `map`;
- visualização `Map`: tópico `/map`;
- visualização `LaserScan`: tópico `/scan`;
- `RobotModel` habilitado.

O mapa começará a surgir conforme o robô se movimentar.

## 5. Dirigir o robô com o teclado

No **Terminal 4**, execute:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel
```

Os controles principais são:

```text
u  i  o
j  k  l
m  ,  .
```

- `i`: mover para frente;
- `,`: mover para trás;
- `j`: girar para a esquerda;
- `l`: girar para a direita;
- `k`: parar;
- `q`: aumentar as velocidades;
- `z`: diminuir as velocidades.

Durante o mapeamento:

- conduza devagar;
- passe por todos os corredores e áreas livres;
- faça curvas suaves;
- retorne a regiões já percorridas para ajudar o SLAM a fechar ciclos;
- evite rotações muito rápidas;
- verifique se os pontos do laser coincidem com as paredes do mapa.

## 6. Salvar o mapa

Quando o mapa estiver completo, execute em outro terminal configurado:

```bash
ros2 run nav2_map_server map_saver_cli \
  -f /home/lukaf04/hemabot_ros2/src/d_hospital_navigation2/maps/meu_mapa
```

O comando criará os arquivos:

```text
meu_mapa.pgm
meu_mapa.yaml
```

Confirme que eles foram salvos:

```bash
ls -lh src/d_hospital_navigation2/maps/meu_mapa.*
```

### Salvar o grafo do SLAM

Opcionalmente, salve também o grafo editável do SLAM:

```bash
ros2 service call \
  /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/lukaf04/hemabot_ros2/src/d_hospital_navigation2/maps/meu_mapa'}"
```

Isso permite continuar ou editar o mapeamento posteriormente.

## 7. Encerrar o mapeamento

Pressione `Ctrl+C` nos terminais do:

1. controle por teclado;
2. RViz;
3. SLAM;
4. Gazebo.

Aguarde o Gazebo encerrar completamente antes de iniciar a fase de navegação.

## Fase 2: localização e navegação autônoma

## 8. Reiniciar o Gazebo

No **Terminal 1**, configure o ambiente e reinicie a simulação:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch d_hospital_gazebo2 hospital.py \
  use_sim_time:=true \
  use_ros2_control:=false \
  use_robot_localization:=false
```

## 9. Carregar o mapa e iniciar o AMCL

No **Terminal 2**, execute:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch d_hospital_navigation2 localization_launch.py \
  use_sim_time:=true \
  map:=/home/lukaf04/hemabot_ros2/src/d_hospital_navigation2/maps/meu_mapa.yaml
```

Verifique o estado do servidor de mapa e do AMCL:

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
```

Ambos devem retornar:

```text
active
```

## 10. Iniciar o Nav2

No **Terminal 3**, execute:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch d_hospital_navigation2 navigation_launch.py \
  use_sim_time:=true
```

Esse launch inicia os principais componentes do Nav2:

- planejador global;
- controlador local;
- suavizador de trajetória;
- árvore de comportamento;
- comportamentos de recuperação;
- seguidor de pontos;
- suavizador de velocidade;
- gerenciador de ciclo de vida.

## 11. Abrir o RViz de navegação

No **Terminal 4**, execute:

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

rviz2 -d src/d_hospital_navigation2/rviz/lidarbot_nav.rviz
```

## 12. Informar a posição inicial

O AMCL precisa saber aproximadamente onde o robô está no mapa.

No RViz:

1. Selecione **2D Pose Estimate**.
2. Clique na posição atual do robô.
3. Arraste a seta na direção em que o robô está apontando.
4. Verifique se os pontos do laser coincidem com as paredes do mapa.

Como o robô nasce em `(0, 0)` no Gazebo e o mapeamento também começou nesse ponto, a pose inicial normalmente será próxima de:

```text
x = 0
y = 0
yaw = 0
```

Também é possível publicar essa pose pelo terminal:

```bash
ros2 topic pub --once /initialpose \
  geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: map}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
```

## 13. Enviar um objetivo autônomo

No RViz:

1. Selecione **Nav2 Goal** ou **2D Goal Pose**.
2. Clique em uma área livre do mapa.
3. Arraste a seta para escolher a orientação final.

O fluxo de navegação será:

```text
objetivo → planejador global → controlador local → /cmd_vel → Gazebo
```

O robô deverá calcular a rota, evitar obstáculos e parar no destino.

## 14. Verificar a navegação

Confira se as ações de navegação foram criadas:

```bash
ros2 action list | grep navigate
```

O resultado deve incluir:

```text
/navigate_to_pose
/navigate_through_poses
```

Confira os comandos de velocidade:

```bash
ros2 topic echo /cmd_vel
```

Confira a cadeia de transformações:

```bash
ros2 run tf2_ros tf2_echo map base_footprint
```

Confira os nós ativos:

```bash
ros2 node list
```

Entre outros, devem aparecer:

```text
/amcl
/map_server
/controller_server
/planner_server
/bt_navigator
/behavior_server
/velocity_smoother
```

## Utilizar um mapa existente

Para testar somente a navegação, sem repetir o mapeamento, o projeto já possui o mapa `map_obs2.yaml`.

Use-o na etapa de localização:

```bash
ros2 launch d_hospital_navigation2 localization_launch.py \
  use_sim_time:=true \
  map:=/home/lukaf04/hemabot_ros2/src/d_hospital_navigation2/maps/map_obs2.yaml
```

Depois, continue a partir da etapa de inicialização do Nav2.

## Solução de problemas

### O caminho aparece, mas o robô não se move

Confirme que o Gazebo foi iniciado com:

```text
use_ros2_control:=false
use_robot_localization:=false
```

Verifique os publicadores e assinantes de velocidade:

```bash
ros2 topic info /cmd_vel -v
```

### O mapa aparece, mas o laser está deslocado

Refaça a localização usando **2D Pose Estimate** no RViz. A seta deve representar corretamente tanto a posição quanto a orientação do robô.

### Erro de transformação entre `map` e `odom`

Confirme que SLAM e AMCL não estão sendo executados simultaneamente:

```bash
ros2 node list | grep -E 'slam_toolbox|amcl'
```

Durante o mapeamento deve existir somente `slam_toolbox`. Durante a navegação deve existir somente `amcl`.

### O Nav2 fica esperando a localização

Publique a pose inicial usando **2D Pose Estimate** no RViz ou pelo tópico `/initialpose`.

### O mapa fica vazio ou deformado

- movimente o robô mais devagar;
- evite rotações bruscas;
- verifique se `/scan` e `/odom` estão sendo publicados;
- retorne a locais já visitados para permitir o fechamento de ciclos.

### Os nós não recebem o relógio da simulação

Todos os launches do Gazebo, SLAM, AMCL e Nav2 devem utilizar:

```text
use_sim_time:=true
```

Verifique o relógio com:

```bash
ros2 topic hz /clock
```

## Resumo dos terminais

### Durante o mapeamento

| Terminal | Processo |
|---|---|
| 1 | Gazebo e robô |
| 2 | SLAM Toolbox |
| 3 | RViz de mapeamento |
| 4 | Controle pelo teclado |

### Durante a navegação

| Terminal | Processo |
|---|---|
| 1 | Gazebo e robô |
| 2 | Servidor de mapa e AMCL |
| 3 | Nav2 |
| 4 | RViz de navegação |

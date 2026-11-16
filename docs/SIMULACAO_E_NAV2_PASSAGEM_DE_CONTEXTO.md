# Simulação Hema e Nav2 — passagem de contexto

Atualizado em 04/11/2026. Evidência: código local do commit `2812c34`, saídas do terminal remoto fornecidas pelo usuário e imagem da simulação. O agente não tem uma sessão SSH própria. Não foram instalados pacotes nem editados arquivos no robô pelo procedimento de simulação.

## Resultado confirmado

A adaptação do launch SOMENTE EM MEMÓRIA abriu o Gazebo, carregou o mundo com cones e inseriu o robô `d_hospital`. O usuário confirmou a presença do robô e a imagem mostra a entidade na árvore do Gazebo. Isso valida a inicialização visual, não comprova sensores, movimento, controladores, TF ou Nav2. A imagem mostra real-time factor de aproximadamente 8,74% naquela captura; não é benchmark permanente, mas indica simulação lenta nessa execução.

O pacote funcional é `d_hospital_gz`, para Ignition Gazebo 6 / Fortress. `d_hospital_gazebo2` é o caminho Gazebo Classic, não o caminho validado nesta sessão. Não confundir nomes dos pacotes com versões do Gazebo.

## Repositórios: causa da confusão

| Local | Estado observado | Uso |
| --- | --- | --- |
| Windows: `C:\Users\rober\OneDrive\Desktop\Zima\hemabot\hemabot_ros2` | `navigation-mapeamento`, commit `2812c34`, pull sem novidades | Repositório examinado diretamente pelo agente |
| Robô: `/home/hemabot/hemabot_ros2` | raiz Git própria, `navigation-mapeamento`, commit `2812c34`, tracking de origin | Clone correto para continuar |
| Robô: `/home/hemabot/d_hospital` | Git reportou `main`, commit `7415627`, mensagem Backup; status incluía arquivos de diretórios acima | Workspace de backup; raiz Git acima de d_hospital é hipótese ainda sem rev-parse confirmado |

O clone correto tem uma alteração local preservada em `src/d_hospital_description/urdf/ros2_control.xacro`: `velocity_filter_alpha` de `0.5` para `1`, no hardware real. Não restaurar, sobrescrever nem fazer stash automaticamente.

O caminho correto é `~/hemabot_ros2`, NÃO `~/hemabot/hemabot_ros2`. O segundo foi um erro de digitação do agente; a falha desse source não prova setup interno quebrado.

Source muda o workspace ROS da sessão; `cd` sozinho não muda. `git switch` muda código, não garante que todos os artefatos de install mudem. Neste caso, `readlink -f` confirmou que o launch de `~/hemabot_ros2/install` aponta para `~/hemabot_ros2/src/d_hospital_gz/launch/gz_launch.py`. Não generalizar esse link para todos os arquivos.

## Ambiente remoto observado

- Ubuntu 22.04 informado pelo usuário; ROS_DISTRO=humble; `/opt/ros/humble`.
- `command -v gazebo gz ign` retornou somente `/usr/bin/ign`.
- `libignition-gazebo6` versão `6.16.0-2~jammy`; integração `ros-humble-ros-gz-sim` versão `0.244.22...`.
- Pacotes ROS visíveis: `ros_gz_sim`, `ros_gz_bridge`, `ros_gz_image`, `ros_gz_interfaces`. Não estavam visíveis `gazebo_ros` nem `ros_ign_gazebo`.
- Launch disponível em ros_gz_sim: `gz_sim.launch.py`. `--show-args` confirmou `gz_args`, `gz_version` (default 6), `ign_args`, `ign_version`, `debugger`, `debug_env`, `on_exit_shutdown`.
- `DISPLAY=localhost:10.0`, janela gráfica remota funcionando.
- `ROS_DOMAIN_ID=77` usado nos terminais da simulação. Não foi auditado o domínio dos processos de hardware real. O domínio deve ser o mesmo entre os terminais da simulação e distinto do domínio de qualquer hardware que não se queira comandar.

## Bloqueio e solução validada

Nos dois workspaces, `gz_launch.py` procura `ros_ign_gazebo/ign_gazebo.launch.py`, embora as demais ações já usem ros_gz. Falhava com PackageNotFoundError. O erro secundário InvalidFrontendLaunchFileError não era prova de sintaxe inválida.

As duas substituições em memória foram:

```text
ros_ign_gazebo -> ros_gz_sim
ign_gazebo.launch.py -> gz_sim.launch.py
```

O adaptador reutilizável ao lado deste documento implementa a mesma abordagem, acrescentando o caminho dos modelos no próprio processo e preservando argumentos. O bloco inline original foi executado no robô com sucesso visual; o arquivo foi validado estaticamente no Windows, mas não executado em ROS pelo agente.

### Repetir no robô sem alterar launch nem compilar

Fechar a execução anterior com Ctrl+C antes de iniciar outra.

```bash
cd ~/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=77
SIM_SHARE="$(ros2 pkg prefix --share d_hospital_gz)"
export IGN_GAZEBO_RESOURCE_PATH="$SIM_SHARE/models${IGN_GAZEBO_RESOURCE_PATH:+:$IGN_GAZEBO_RESOURCE_PATH}"
export GZ_SIM_RESOURCE_PATH="$SIM_SHARE/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
python3 - <<'PY'
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchService
path = Path(get_package_share_directory('d_hospital_gz')) / 'launch/gz_launch.py'
code = path.read_text().replace('ros_ign_gazebo', 'ros_gz_sim')
code = code.replace('ign_gazebo.launch.py', 'gz_sim.launch.py')
scope = {'__file__': str(path), '__name__': 'temporary_simulation_launch'}
exec(compile(code, str(path), 'exec'), scope)
service = LaunchService(argv=['use_sim_time:=true'])
service.include_launch_description(scope['generate_launch_description']())
raise SystemExit(service.run())
PY
```

Ou, se este documento e o adaptador estiverem copiados para o computador Linux:

```bash
# Após carregar ROS/workspace e definir ROS_DOMAIN_ID:
python3 /caminho/para/simular_fortress_sem_editar.py use_sim_time:=true
```

Somente mundo, sem robô/controle/ponte: `ign gazebo -r "$SIM_SHARE/worlds/obstacles.world"`, após as variáveis de modelos acima. `ign gazebo` sozinho abre a janela. Os modelos de cones e barris estão no repositório; não precisaram de download para esse teste. Um ground_plane também aparece na captura; a disponibilidade de recursos básicos/cache em outra máquina deve ser verificada.

## Coletar antes de desconectar

Em outro terminal SSH, carregar ROS e o workspace correto, definir domínio 77 e consultar:

```bash
uname -m
ros2 node list
ros2 topic list -t
timeout 10 ros2 control list_controllers
timeout 5 ros2 run tf2_ros tf2_echo odom base_footprint
timeout 5 ros2 topic echo /clock --once
timeout 5 ros2 topic echo /scan --once --qos-reliability best_effort
timeout 5 ros2 topic echo /odom --once
```

Timeout ao consultar não é diagnóstico final; guardar saída e logs. Não publicar cmd_vel no robô físico para coletar informações. Se quiser registrar arquivos temporários de diagnóstico no robô, isso é uma escrita adicional a decidir com o usuário; o procedimento até aqui usa saída do terminal.

Registrar também pacotes realmente instalados, versão/arquitetura, e `ros2 param get /ekf_filter_node use_sim_time` (ajustar nome conforme node list), além de `ros2 param get /controller_manager use_sim_time`. Não considerar tópico listado como prova de mensagens chegando.

## Executar em casa sem conexão com o robô

O cenário, modelos de cones/barris, URDF, meshes, controllers e configuração de navegação estão no repositório. A simulação usa `ign_ros2_control/IgnitionSystem`, não o firmware físico. Portanto, em princípio pode executar inteiramente no computador de casa. Isso ainda NÃO foi testado lá.

Reproduzir primeiro Ubuntu 22.04 + ROS 2 Humble + Ignition Gazebo 6 / Fortress. No Windows, usar Ubuntu 22.04 no WSL2 com suporte gráfico WSLg ou Linux local; o PowerShell não oferece o mesmo ambiente. Não presumir que instalações do robô existam no computador. A escolha de WSL não foi validada neste diagnóstico.

Não copiar `build/`, `install/` ou binários do robô para outra arquitetura; compilar no computador de destino. Não copiar toda a home, caches ou configurações pessoais do robô. Registrar a lista de dependências pode ser útil, mas instalar TODOS os pacotes do robô não é necessário para simulação.

### Preparação na máquina de casa (somente nela)

1. Instalar/carregar ROS Humble no Ubuntu 22.04 conforme documentação oficial. Conferir que `ign gazebo` abre.
2. Clonar o repositório no Linux, sem reutilizar build Windows:

```bash
git clone --branch navigation-mapeamento https://github.com/ZimaUSP/hemabot_ros2.git ~/hemabot_sim_ws
cd ~/hemabot_sim_ws
git log -1 --oneline
source /opt/ros/humble/setup.bash
```

O estado examinado foi `2812c34`. A branch remota pode avançar; para reprodução exata, usar checkout desse commit no clone novo e limpo. A alteração de filtro do robô real não é necessária ao URDF próprio da simulação.

3. Conferir/instalar dependências de simulação nessa máquina. A lista mínima deve incluir ROS Humble, colcon, xacro, ros_gz_sim, ros_gz_bridge, ros_gz_image, ign_ros2_control, ros2_control/ros2_controllers, robot_localization, twist_mux, joy e teleop_twist_joy; para navegação, navigation2/nav2_bringup, slam_toolbox, RViz e teleop_twist_keyboard. Verificar nomes de pacotes Debian disponíveis antes de instalar. Não é uma instrução para instalar nada no robô.
4. Usar rosdep nas pastas de simulação, em vez de arrastar dependências do firmware ou do Gazebo Classic:

```bash
rosdep update
rosdep install --from-paths src/d_hospital_description src/d_hospital_teleop \
  src/d_hospital_gz src/d_hospital_navigation2 src/d_hospital_slam \
  --ignore-src --rosdistro humble -r -y
```

rosdep precisa estar instalado/inicializado antes; alguns manifests são incompletos. Inspecionar erros, não presumir cobertura total. O rosdep pode tentar resolver dependências transitivas maiores (ex.: rplidar); conferir o plano na máquina nova.

5. Compilar apenas o conjunto de simulação:

```bash
colcon build --symlink-install --packages-select \
  d_hospital_description d_hospital_teleop d_hospital_gz \
  d_hospital_navigation2 d_hospital_slam
source install/setup.bash
export ROS_DOMAIN_ID=77
```

6. Executar o adaptador deste documento (copiado junto) e verificar sensores, TF e controle. Essa receita de instalação/build em casa ainda não foi executada; resolver dependências reais reportadas sem alterar o robô remoto.

Referências oficiais: [ROS Humble no Ubuntu](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html), [ros2_control Humble](https://control.ros.org/humble/doc/getting_started/getting_started.html), [ign_ros2_control / Fortress](https://index.ros.org/r/ign_ros2_control/).

## Caminho do comando e da localização (inspeção do código)

```text
Nav2 -> /cmd_vel -> twist_mux -> /diff_controller/cmd_vel_unstamped
     -> diff_controller -> juntas no Ignition

diff_controller/odom + imu_broadcaster/imu -> EKF -> /odom e TF odom->base_footprint
/scan -> AMCL ou SLAM -> TF map->odom
robot_state_publisher -> frames dos links/sensores
```

O launch inicia joint_broadcaster e diff_controller. O IMU da simulação é entregue pela ponte; não é prova de que imu_broadcaster ros2_control precise estar ativo. O joystick tem prioridade maior no twist_mux e pode sobrepor comandos de navegação.

## Pontos críticos antes do Nav2

- Conferir `/clock`, `/scan`, `/odom` e cadeia TF `map -> odom -> base_footprint -> base_link` com mensagens atuais, não apenas nomes de tópicos.
- EKF local tem `use_sim_time: false`, e o launch não lhe passa override. O diff_controller tem `enable_odom_tf: false`; portanto o EKF é importante para odom->base. Isso é possível bloqueio posterior, ainda não validado por saída de execução.
- O plugin Ignition carrega `controllers.yaml`; esse arquivo não fixa use_sim_time. Consultar clock do controller_manager e controladores.
- `controllers.yaml` usa rodas left/right invertidas nominalmente; não alterar só pelo nome. Se testar movimento na máquina de casa, verificar sentido real na simulação.
- URDF do Gazebo limita interfaces das rodas a +/-1, enquanto Nav2 permite 0,26 m/s. Efeito real do limite precisa ser medido; não concluir que o movimento foi validado.
- `velocity_smoother` publica cmd_vel, e o controller_server publica cmd_vel_nav. O behavior_server local usa cmd_vel sem a mesma remap; observar comandos de recuperação se houver problemas.

### Opção A — mapa existente + AMCL

Com simulação e TF odom funcionando, em terminais separados, todos com ROS/workspace carregados e domínio 77:

```bash
ros2 launch d_hospital_navigation2 localization_launch.py \
  use_sim_time:=true \
  map:="$(ros2 pkg prefix --share d_hospital_navigation2)/maps/sim_map.yaml"

ros2 launch d_hospital_navigation2 navigation_launch.py use_sim_time:=true

ros2 launch nav2_bringup rviz_launch.py use_sim_time:=true
```

Esses comandos são roteiro para testar, NÃO foram validados nesta sessão. A correspondência de sim_map.yaml com obstacles.world não foi confirmada. Se não corresponder, criar um mapa novo. No RViz usar Fixed Frame map, 2D Pose Estimate e depois Nav2 Goal. Não enviar destino antes de confirmar localização e sensores. Se o mapa não estiver alinhado, conferir pose, scan e TF, não ajustar o objetivo para compensar.

### Opção B — criar mapa novo

ATENÇÃO: `src/d_hospital_slam/config/mapper_params_online_async.yaml` está em `mode: localization`, com `map_file_name: $HOME/mapa_nav`. O nome do launch não garante modo mapping. Não afirmar que `online_async_launch.py` sozinho cria mapa novo. A expansão de $HOME dentro desse YAML também não foi validada; preferir caminho absoluto em uma configuração de casa.

Na máquina de casa, criar uma cópia da configuração fora do arquivo original: definir `mode: mapping` e remover os parâmetros de mapa prévio/start pose para um mapa novo. Usar seu caminho absoluto:

```bash
ros2 launch d_hospital_slam online_async_launch.py \
  use_sim_time:=true slam_params_file:=/caminho/absoluto/mapper_sim.yaml
```

Não iniciar AMCL junto: ambos podem tentar fornecer map->odom. Explorar o mundo por teleop na simulação e salvar, por exemplo:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 run nav2_map_server map_saver_cli -f ~/mapa_sim --ros-args -p use_sim_time:=true
```

Depois encerrar SLAM e usar o YAML salvo com AMCL (opção A). O arquivo de ocupação YAML/PGM para AMCL não equivale ao posegraph serializado usado na localização do slam_toolbox.

## Encerramento

Antes de desconectar, Ctrl+C nos terminais de launch que você iniciou para esta simulação e aguardar encerramento. Não usar killall/pkill indiscriminadamente no robô: podem existir serviços reais de outros usuários. Não desligar serviços de hardware fora do escopo. Os exports desaparecem ao encerrar o terminal e não foram escritos no bashrc.

## Coleta recebida após a inicialização visual

Arquitetura confirmada: `aarch64`. O computador doméstico pode ser x86_64: recompilar nele, não transportar binários ARM.

O terminal de coleta estava em `~`; `git branch` ali retornou main. Isso NÃO contradiz navigation-mapeamento em `~/hemabot_ros2`: são raízes Git distintas. O source correto foi executado antes da coleta. Não trocar a branch da home para tentar corrigir a simulação.

Resultados importantes:

```text
ros2 node list: saída vazia
diff_controller   diff_drive_controller/DiffDriveController     inactive
joint_broadcaster joint_state_broadcaster/JointStateBroadcaster inactive
tf2_echo odom base_footprint: frame odom não existe durante os 5 s observados
```

O serviço list_controllers respondeu após uma espera inicial. Portanto havia comunicação com um controller_manager naquele momento. A lista de nodes vazia, contrastando com serviço/tópicos, pode envolver descoberta assíncrona/cache/daemon ou mudança temporal dos processos; causa NÃO confirmada. Não concluir que todos os nós morreram só por essa lista. Futuramente comparar com `ros2 node list --no-daemon` e logs da execução.

Tópicos listados (presença não comprova fluxo de mensagens): camera/camera_info, camera/image_raw e variantes compressed/compressedDepth/theora; /clock; /cmd_vel; /cmd_vel_joy; /diagnostics; /diff_controller/cmd_vel_unstamped; /diff_controller/odom; /diff_controller/transition_event; /dynamic_joint_states; /imu_broadcaster/imu; /joint_broadcaster/transition_event; /joint_states; /joy; /joy/set_feedback; /odom; /parameter_events; /robot_description; /rosout; /scan; /set_pose; /tf; /tf_static.

Interpretação: a integração é suficiente para inserir o robô, mas a coleta NÃO validou movimento. Os controladores estavam carregados, porém inativos. Ausência de TF odom->base e controladores inativos impedem considerar o sistema pronto para Nav2. Não iniciar navegação automática nesse estado.

Próxima investigação, preferencialmente em casa: ler logs dos spawners e controller_manager para causa de falha na ativação; verificar /clock e use_sim_time; conferir interfaces de hardware disponíveis; só depois decidir ativação de controladores no simulador isolado. Não ativar controladores indiscriminadamente no hardware real. Confirmar TF após resolver estado/clock do EKF; ausência de TF pode ter mais de uma causa.

Dependências confirmadas por dpkg (versões não incluídas nessa coleta):

```text
ros-humble-ign-ros2-control
ros-humble-joy
ros-humble-joy-tester
ros-humble-navigation2
ros-humble-robot-localization
ros-humble-ros-gz-bridge
ros-humble-ros-gz-image
ros-humble-ros-gz-interfaces
ros-humble-ros-gz-sim
ros-humble-ros2-control
ros-humble-ros2-control-test-assets
ros-humble-ros2-controllers
ros-humble-slam-toolbox
ros-humble-teleop-twist-joy
ros-humble-teleop-twist-keyboard
ros-humble-twist-mux
ros-humble-twist-mux-msgs
ros-humble-xacro
```

Também confirmados os componentes nav2: amcl, behavior-tree, behaviors, bringup, bt-navigator, collision-monitor, common, constrained-smoother, controller, core, costmap-2d, dwb-controller, lifecycle-manager, map-server, mppi-controller, msgs, navfn-planner, planner, regulated-pure-pursuit-controller, rotation-shim-controller, route, rviz-plugins, simple-commander, smac-planner, smoother, theta-star-planner, util, velocity-smoother, voxel-grid e waypoint-follower. Esta lista é inventário, não uma exigência de instalar cada componente separadamente em casa; metapacotes resolvem vários deles.

## Log de inicialização recebido ao final

Diretório da execução: `/home/hemabot/.ros/log/2026-11-04-16-09-34-726169-hemabot-2170`. Preservar como referência se ainda existir no robô; não foi copiado integralmente ao computador local.

Confirmações adicionais do log:

- robot_state_publisher carregou base_footprint, base_link e links de rodas/sensores.
- create retornou `OK creation of entity` e saiu com sucesso; Gazebo criou entidade 66, nome d_hospital.
- As pontes clock, IMU, scan e camera_info foram criadas. Gazebo anunciou câmera, lidar e IMU; isso ainda não substitui uma amostra recebida em ROS.
- O hardware simulado IgnitionSystem inicializou, configurou e ativou com sucesso, expondo position/velocity e comandos velocity nas duas juntas de rodas. Distinguir ativação do HARDWARE da ativação dos CONTROLADORES.
- O plugin antigo ign_ros2_control funcionou por compatibilidade, mas avisou que foi renomeado para gz_ros2_control, sugerindo `gz_ros2_control/GazeboSimSystem` e `gz_ros2_control-system`. Esse aviso NÃO impediu a inicialização do hardware; não é necessário renomear o plugin às cegas para explicar a falha atual.
- controller_manager carregou/configurou diff_controller e joint_broadcaster. Ambos falharam na ativação com `Switch controller timed out after 5.000000 seconds!`; os dois spawners encerraram com código 1. Isso explica diretamente o estado inactive observado depois.

Ordem temporal importante (segundos de relógio do log): hardware ativado ~9382, diff_controller carregado ~9383, primeiro timeout ~9388, segundo ~9393; anúncios de câmera/lidar e confirmação do tópico IMU aparecem durante/depois dessa janela. A captura mostrou simulação lenta. Isso torna atraso de inicialização/renderização ou falta de avanço do loop de simulação hipóteses para o timeout; NÃO prova a causa. A simulação foi iniciada com -r e a captura mostra botão de pausa, então não afirmar que estava pausada.

Próxima tentativa na máquina doméstica, após conferir que a simulação avança: consultar a ajuda do spawner (`ros2 run controller_manager spawner --help`) e avaliar ativação posterior/sequencial ou aumento do switch timeout disponível naquela versão. Usar apenas em simulação isolada e não presumir que aumentar timeout resolve um loop travado. Não foi realizada essa tentativa nem modificado o adaptador para fazê-la automaticamente.

Avisos do EKF confirmados em execução:

```text
Filter history interval of 1 specified, but smooth_lagged_data is set to false.
Some linear velocity entries in parameter imu0_config are listed true,
but a sensor_msgs/Imu contains no information about linear velocities.
```

O segundo corresponde ao vx marcado true em imu0_config no YAML local. Revisar a máscara em configuração específica de simulação: IMU fornece orientação, velocidade angular e aceleração linear, não velocidade linear. Não inferir que o warning sozinho causou TF ausente. O uso de relógio real no EKF, já encontrado por inspeção, permanece outra hipótese a verificar.

O aviso de período de controle 0,05 s vs passo de física 0,001 s registra taxas diferentes; não comprova por si só falha. Avisos QML, anti-aliasing e serialização apareceram, mas o mundo e robô abriram. Priorizar timeouts e relógios antes de atribuir o bloqueio a avisos gráficos.

## Pendências de evidência

- Saída de nodes, tópicos, controladores, TF e log de inicialização já foram incorporados. Os timeouts explicam a inatividade; a causa dos timeouts e amostras de mensagens ainda faltam.
- Movimento do robô, sensores e navegação NÃO estão confirmados só pela captura.
- Não foi feita instalação local no computador de casa, nem build/teste ROS pelo agente no Windows.
- O primeiro documento DIAGNOSTICO_SIMULACAO_HEMABOT.md é histórico anterior. Onde conflitar sobre sucesso da simulação, branch ou modo SLAM, este documento atualizado prevalece.

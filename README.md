# HemaBot ROS 2

Workspace ROS 2 do HemaBot (MiniHema), um robô móvel de tração diferencial desenvolvido para apoiar o transporte de materiais em ambiente hospitalar.

O objetivo do projeto é oferecer uma base para controle do robô físico, teleoperação, aquisição de sensores, localização, mapeamento e navegação autônoma. A chamada do robô por aplicativo faz parte da visão do projeto, mas **não está implementada neste repositório**.

## Estado atual

| Área | Situação na `main` |
| --- | --- |
| Robô físico | Bringup disponível para ROS 2 Humble, Raspberry Pi, motores, encoders, MPU6050 e RPLIDAR A1 |
| Teleoperação | Joystick iniciado pelo launch principal; teclado pode publicar em `/cmd_vel` |
| Localização | Fusão de odometria e IMU com `robot_localization` |
| SLAM e Nav2 | Pacotes e arquivos de configuração presentes; ainda exigem validação no ambiente e no mapa de destino |
| Câmera | Launch existente, mas desativado no bringup principal |
| Simulação | Implementações legadas para Gazebo Classic e Gazebo Fortress; veja [Simulação](#simulação) |

> A versão atualmente utilizada pelo robô físico é **ROS 2 Humble**. O código da `main` ainda não foi portado nem validado para ROS 2 Lyrical/Gazebo Jetty.

## Arquitetura

O bringup principal integra:

- `ros2_control` e `diff_drive_controller` para a base diferencial;
- encoders das rodas e driver dos motores via `wiringPi`;
- IMU MPU6050 via I²C;
- RPLIDAR A1;
- `robot_localization` para estimativa de odometria;
- `joy` e `teleop_twist_joy` para controle por joystick;
- `twist_mux` para priorizar comandos de navegação e joystick.

Os comandos recebidos em `/cmd_vel` (prioridade 10) e `/cmd_vel_joy` (prioridade 100) são encaminhados pelo `twist_mux` para `/diff_controller/cmd_vel_unstamped`.

## Plataforma de referência

- Ubuntu 22.04 (Jammy);
- ROS 2 Humble;
- Raspberry Pi 4 no robô físico;
- RPLIDAR A1;
- IMU MPU6050;
- motores de corrente contínua com encoders e driver compatível com o firmware existente;
- joystick compatível com o pacote `joy` (necessário para usar a teleoperação configurada).

Para instalar o ROS 2, siga a [documentação oficial do ROS 2 Humble](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html). Há também um [guia de preparação do Raspberry Pi](docs/os_installation_raspberry.md), que ainda deve ser revisado em conjunto com a documentação oficial.

## Instalação do workspace

```bash
git clone https://github.com/ZimaUSP/hemabot_ros2.git
cd hemabot_ros2

source /opt/ros/humble/setup.bash

# Execute `sudo rosdep init` apenas na primeira configuração da máquina.
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y

colcon build --symlink-install
source install/setup.bash
```

O hardware físico também depende das bibliotecas nativas `wiringPi` e I²C (`libi2c`). Essas dependências não estão completamente declaradas nos manifests ROS e podem precisar de instalação manual, de acordo com o sistema usado no Raspberry Pi.

Não existe `requirements.txt` na `main`; o projeto não é uma aplicação Python independente e suas dependências principais são gerenciadas por ROS/rosdep e CMake.

## Conexão com o robô

O SSH é usado para acessar o computador de bordo; ele não é o protocolo de controle dos motores. Use o usuário, hostname ou IP configurados no seu Raspberry Pi:

```bash
ssh <usuario>@<hostname>.local
# ou
ssh <usuario>@<endereco-ip>
```

O computador e o Raspberry Pi precisam ter conectividade de rede entre si, mas o projeto não depende de uma rede Wi-Fi com nome específico. Use `ssh -X` somente se precisar encaminhar uma interface gráfica e se o servidor SSH estiver configurado para X11 forwarding.

## Executando o robô físico

Em um terminal no Raspberry Pi, a partir da raiz do workspace:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch minihema_launch minihema_launch.py
```

Esse launch inicia a descrição do robô, o controller manager, os broadcasters de juntas e IMU, o controlador diferencial, o filtro de localização, o joystick, o LiDAR e o `twist_mux`. A câmera permanece desativada no arquivo de launch atual.

> **Segurança:** no primeiro teste após qualquer alteração de hardware, controle ou parâmetros, mantenha as rodas suspensas e tenha um meio de cortar a alimentação dos motores.

### Controle por joystick

O joystick é iniciado automaticamente pelo bringup. O arquivo `src/d_hospital_teleop/config/joystick.yaml` exige que o botão de habilitação configurado seja mantido pressionado.

### Controle por teclado

O pacote `teleop_twist_keyboard` é opcional e não faz parte deste repositório. Depois de instalá-lo para o ROS 2 Humble, execute:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=/cmd_vel
```

Também é possível publicar um comando de teste diretamente. O exemplo abaixo envia `0,10 m/s` em linha reta durante a execução do comando:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.10, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Interrompa com `Ctrl+C`. Se necessário, publique uma mensagem com todas as velocidades iguais a zero antes de desligar a base.

## Mapeamento e navegação

Com o bringup do robô já em execução, o SLAM assíncrono pode ser iniciado para o hardware físico com:

```bash
source install/setup.bash
ros2 launch d_hospital_slam online_async_launch.py use_sim_time:=false
```

O pacote `d_hospital_navigation2` contém configurações do Nav2, localização AMCL, servidor de mapas e arquivos de RViz. Antes do uso autônomo, valide o mapa, os frames TF, os limites de velocidade, o footprint e os parâmetros dos costmaps no ambiente real.

## Simulação

Há duas implementações de simulação na árvore atual:

- `d_hospital_gazebo2`: Gazebo Classic com `gazebo_ros_pkgs`;
- `d_hospital_gz`: Gazebo Fortress, mas ainda contém nomes antigos como `ros_ign_gazebo` e `ign_ros2_control`.

Esses pacotes são **legados e não representam uma simulação validada no estado atual da `main`**. Não instale uma versão mais recente do Gazebo esperando compatibilidade direta com eles.

Para manter ROS 2 Humble, a combinação oficialmente recomendada é Gazebo Fortress. Uma migração moderna deve substituir as referências `ros_ign_*`/`ign_*` por `ros_gz_*`/`gz_*`, revisar plugins, bridges e arquivos SDF/URDF e adicionar testes de inicialização.

Para uma atualização mais ampla, a combinação recomendada para novos projetos é Ubuntu 24.04, ROS 2 Jazzy e Gazebo Harmonic. Essa opção exige portar e validar também o firmware, `ros2_control`, Nav2 e os launch files; ela não é apenas uma troca de pacote. Consulte a [matriz oficial de compatibilidade ROS/Gazebo](https://gazebosim.org/docs/jetty/ros_installation/).

## Estrutura do repositório

```text
hemabot_ros2/
├── docs/                         # Documentação complementar
├── src/
│   ├── d_hospital_description/   # URDF/Xacro, meshes e RViz
│   ├── d_hospital_gazebo2/       # Simulação legada no Gazebo Classic
│   ├── d_hospital_gz/            # Simulação legada no Gazebo Fortress
│   ├── d_hospital_navigation2/   # Nav2, AMCL, mapas e localização
│   ├── d_hospital_slam/          # Configuração do slam_toolbox
│   ├── d_hospital_teleop/        # Joystick e twist_mux
│   ├── firmware_minihema/        # Interface ros2_control dos motores/encoders
│   └── minihema_launch/           # Bringup do hardware e interface da IMU
├── calibrar_offsets              # Auxiliar de calibração da IMU
├── calibrar_covariancias.sh      # Auxiliar de covariâncias da IMU
├── start_hema.sh                 # Script local do robô; contém caminhos específicos
└── README.md
```

Os diretórios `build/`, `install/` e `log/` são artefatos locais do `colcon` e não devem ser versionados.

## Problemas comuns

| Sintoma | Verificação |
| --- | --- |
| `Package ... not found` | Execute `source /opt/ros/humble/setup.bash`, compile e depois execute `source install/setup.bash` no terminal atual |
| Falha ao encontrar `wiringPi` ou `i2c` | Instale as bibliotecas de desenvolvimento compatíveis com o sistema do Raspberry Pi |
| LiDAR não abre a porta serial | Verifique o dispositivo configurado, cabo, alimentação e permissão do usuário sobre a porta |
| Joystick não movimenta o robô | Confirme o dispositivo em `device_id`, os eixos/botões e mantenha pressionado o botão de habilitação |
| Erro com `gazebo_ros_pkgs`, `ros_ign_*` ou `ign_ros2_control` | Os pacotes de simulação são legados; use o ambiente histórico compatível ou conclua a migração descrita acima |
| Tópicos existem, mas o robô não se move | Confirme que `diff_controller` está ativo e que `/cmd_vel_out` chega a `/diff_controller/cmd_vel_unstamped` |

## Desligamento seguro

1. Pare os comandos de movimento e envie velocidade zero, se necessário.
2. Finalize os processos ROS com `Ctrl+C`.
3. Corte a alimentação dos motores.
4. Desligue o Raspberry Pi corretamente antes de remover sua alimentação.
5. Desconecte o LiDAR e os demais periféricos conforme o procedimento do hardware.

## Contribuindo

1. Abra uma issue descrevendo o problema ou a proposta.
2. Faça um fork e crie uma branch específica.
3. Mantenha alterações pequenas e documente como foram testadas.
4. Não envie `build/`, `install/`, `log/`, dumps, mapas temporários, credenciais ou endereços particulares.
5. Abra um pull request para revisão.

## Licenciamento

Os manifests dos pacotes declaram licenças diferentes e o repositório ainda não possui uma licença única na raiz. Antes de considerar a distribuição open source consolidada, é necessário confirmar a autoria dos arquivos, escolher uma política de licenciamento compatível e adicionar os textos de licença correspondentes. Até essa regularização, não presuma que todo o conteúdo está coberto por uma única licença.

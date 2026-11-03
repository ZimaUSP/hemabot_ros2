# Hema V4: modelo CAD para ROS 2 e Gazebo

Descrição pronta para compilar, com as malhas incluídas no Git. Não é necessário baixar o ZIP CAD original para usar o robô. São 227 peças CAD agrupadas em 15 elos físicos, mais o elo do LiDAR e o referencial virtual `tool0`. A massa CAD estimada é 22,765 kg; o LiDAR assumido acrescenta 0,20 kg à simulação.

Este pacote representa o Hema V4 e é independente dos pacotes `d_hospital_*`/MiniHema do repositório. Ele oferece simulação, controle direto das rodas e um LiDAR 2D de 180°. Não substitui os drivers do robô físico nem inclui navegação ou odometria.

## Instalar e abrir

Use Ubuntu 22.04 com ROS 2 Humble/Gazebo Classic ou Ubuntu 24.04 com ROS 2 Jazzy/Gazebo Harmonic. No Windows, execute dentro da distribuição Ubuntu correspondente no WSL; a interface gráfica precisa de WSLg ou servidor X.

```bash
git clone https://github.com/ZimaUSP/hemabot_ros2.git
cd hemabot_ros2
source /opt/ros/humble/setup.bash
rosdep install --from-paths src/hema_description --ignore-src --rosdistro humble -r -y
colcon build --packages-select hema_description
source install/local_setup.bash
ros2 launch hema_description simulation.launch.py backend:=classic gui:=true
```

Se já clonou o repositório, atualize sua branch `main` antes do build. A instalação de dependências fica restrita a este pacote, evitando exigir os drivers dos demais robôs para abrir o modelo CAD.

Para Jazzy/Harmonic, troque `humble` por `jazzy` no `source` e no `rosdep`, e execute:

```bash
ros2 launch hema_description simulation.launch.py backend:=harmonic gui:=true
```

`gui:=false` inicia apenas o servidor. O launch insere o modelo e ativa os controladores automaticamente. Classic é uma opção legada, testada em execução; Harmonic foi validado estruturalmente. Este pacote não declara suporte a Lyrical/Jetty.

## Mover e parar

Em outro terminal, dentro do mesmo workspace:

```bash
source /opt/ros/humble/setup.bash
source install/local_setup.bash
ros2 topic pub --once /wheel_controller/commands std_msgs/msg/Float64MultiArray "{data: [2.0, 2.0]}"
```

O comando é `[roda_esquerda, roda_direita]`, em rad/s. O último comando permanece ativo. Para parar:

```bash
ros2 topic pub --once /wheel_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.0, 0.0]}"
```

| Movimento | Valores |
| --- | --- |
| Frente | `[2, 2]` |
| Ré | `[-2, -2]` |
| Girar à esquerda | `[-2, 2]` |
| Girar à direita | `[2, -2]` |
| Parar | `[0, 0]` |

O modelo usa `/wheel_controller/commands`, não `/cmd_vel`. O launch também aceita `command_interface:=position` ou `effort`, selecionando o YAML correspondente; nesses modos as unidades são rad e N·m.

## LiDAR interno de 180 graus

O LiDAR fica no centro do acabamento semicircular traseiro existente no CAD, em `(-0.1508, 0, 0.106) m` no `base_link`, orientado para trás. A varredura cobre de −90° a +90° no referencial `lidar_link`, com 361 amostras, 10 Hz e alcance de 0,15 a 12 m.

```bash
ros2 topic echo /scan --once
```

O tópico usa `sensor_msgs/msg/LaserScan`. No Classic, `gazebo_ros_ray_sensor` publica `/scan`; no Harmonic, o launch cria a ponte equivalente. A posição, a massa de 0,20 kg e o corpo cilíndrico de raio 35 mm são hipóteses de integração porque o arquivo nativo `HEM_RPlidar.SLDASM` não apareceu como malha funcional na exportação STL.

## Arquivos e parâmetros

| Arquivo | Responsabilidade |
| --- | --- |
| `urdf/robot.urdf.xacro` | Entrada e parâmetros |
| `urdf/inertials.xacro` | Macros de caixa, cilindro, esfera e tensor completo |
| `urdf/materials.xacro` | Cores reutilizáveis |
| `urdf/robot_core.xacro` | Elos, juntas, origens e colisões |
| `urdf/lidar.xacro` | LiDAR interno, campo de visão e plugins dos simuladores |
| `urdf/gazebo_config.xacro` | Contatos, plugins e ros2_control |
| `urdf/cad_visuals.xacro` | Instâncias visuais geradas |
| `config/cad_parameters.yaml` | Dimensões, massas, CoMs e tensores |
| `meshes/` | Malhas visuais, em metros |

O launch expõe `backend`, `command_interface`, `articulate_slides`, `caster_z_adjust`, `spawn_z` e `gui`. O Xacro também permite ajustar pose, massa, dimensões, alcance, frequência, amostragem, ruído e visualização do LiDAR. As corrediças ficam fixas por padrão; `articulate_slides:=true` as torna passivas. O curso de 0,25 m por estágio é uma hipótese, não um limite confirmado de fabricação. Não há garra: `tool0` é um referencial virtual no trilho esquerdo.

Para gerar URDF sem plugins:

```bash
share="$(ros2 pkg prefix hema_description)/share/hema_description"
xacro "$share/urdf/robot.urdf.xacro" backend:=none > /tmp/hema.urdf
```

O Xacro também aceita `mass_scale`, fatores de massa por grupo, `inertia_mode:=mesh|primitive`, limites de rodas, atrito e amortecimento. Consulte os argumentos no arquivo principal. Fatores de massa devem ser positivos. O ajuste padrão `caster_z_adjust=-0.005623657` alinha os contatos das seis rodas; zero restaura a pose CAD.

## Validação e rastreabilidade

- [Tabela completa de elos, materiais e hipóteses](docs/ENGINEERING.md)
- [Tabela de elos em CSV](docs/link_summary.csv)
- [Massa por peça](docs/cad_parts.csv)
- [Resultados históricos da validação no Classic](docs/VALIDATION.md)

Para conferir as 36 variantes de descrição, com Python, NumPy, PyYAML e Xacro disponíveis:

```bash
python3 src/hema_description/scripts/validate_description.py
```

Os resultados ficam em `src/hema_description/generated/`, ignorado pelo Git. O CI repete essa verificação. Para testar uma simulação já aberta em modo velocidade:

```bash
python3 src/hema_description/scripts/runtime_smoke.py --output /tmp/hema_runtime.json
```

O teste envia movimento e parada, verifica os estados das juntas e confere o `/scan`, seu quadro, 361 amostras e campo de visão de 180°. Ele não mede estabilidade prolongada ou fidelidade dinâmica ao robô real. Para refazer a análise CAD, instale `config/analysis-requirements.txt` em um ambiente Python separado e execute `scripts/analyze_cad.py` com o ZIP original. A simulação não depende dessas bibliotecas de análise.

Materiais, densidades, atuação e propriedades do LiDAR foram estimados. Bateria, carga útil e demais eletrônicos ausentes do STL não foram inventados. As colisões são simplificadas e a autocolisão está desativada. Os arquivos nativos SolidWorks e cortes redundantes de impressão não foram incluídos no pacote.

O código adota Apache-2.0 conforme `package.xml`; as malhas mantêm os direitos do titular do CAD de origem. Publicar o pacote não atribui uma nova licença às malhas.

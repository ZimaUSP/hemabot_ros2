# 🏥 Tutorial Mini Hema

## 📖 Contexto do Projeto

Foi a partir do **Dr. Oscar Fujita**, Diretor do **Núcleo de Inovação e Tecnologia (INTEC)**, que surgiu a demanda pelo **robô hospitalar**.  
Com o agravamento da pandemia, para evitar o contágio dos colaboradores com materiais potencialmente contaminados por **COVID-19**, foi sugerido o desenvolvimento de um robô capaz de **realizar o transporte autônomo de amostras laboratoriais**.

Através de diversos **sensores de distância**, **mapeamento digital** e **algoritmos de navegação**, o robô pode se locomover de forma **segura e autônoma** dentro do ambiente hospitalar.  
Além disso, para ser chamado, basta um simples **clique no aplicativo do Robô Hospitalar**, que inicia o deslocamento até o local solicitado.

---

## Branch mapeamento

Esta branch se destina ao mapeamento do ambiente com o HemaBot. Outras funções do projeto podem estar desatualizadas nesta branch.

Para conhecer a função de cada pacote, pasta e arquivo, siga o [índice do src](src/README.md).

## O papel de cada ferramenta

O **Gazebo** é o simulador onde podemos testar o robô em um ambiente virtual antes de levar o teste para a vida real. Ele simula o movimento, o contato com o chão e as leituras dos sensores. Na passagem para o robô físico, o comportamento pode mudar por causa de falhas nos motores, diferenças de atrito, rodas patinando e imprecisão dos sensores. O resultado depende de quanto esses efeitos estão representados na simulação.

O **SLAM** é o processo de construir um mapa enquanto o robô estima onde está dentro dele. Dá para pensar no mapa como uma memória do ambiente, construída a partir dos sensores. Conforme o robô anda, o SLAM compara novas leituras com o que já observou, deduz sua posição e ajusta o mapa. Neste projeto, usamos o **SLAM Toolbox**, que combina as varreduras do LiDAR com as informações de movimento do robô.

O **RViz2** transforma os dados publicados pelo ROS 2 em uma visualização que conseguimos interpretar. Nele, podemos acompanhar o mapa, os pontos do LiDAR, a posição estimada do robô e outros dados para entender o que o sistema está percebendo.

O **Nav2** é um conjunto de ferramentas de navegação do ROS 2 que oferece diferentes algoritmos para planejar uma rota e controlar o movimento entre um ponto e outro. Depois de criar o mapa, podemos usá-lo para localizar o robô e orientar a navegação, levando em conta os obstáculos percebidos pelos sensores. As escolhas de planejador e controlador ficam nas configurações do Nav2.

Também podemos interagir com o Nav2 pelo RViz2, usando o painel **Navigation 2** e a ferramenta **Nav2 Goal** para indicar no mapa a posição e a orientação de destino. Os nós de navegação e localização precisam estar rodando para o robô atender ao comando. A configuração `src/d_hospital_navigation2/rviz/lidarbot_nav.rviz` já inclui esse painel e essa ferramenta.

No fluxo de simulação, o Gazebo fornece o ambiente e os sensores simulados, o SLAM constrói o mapa e o RViz2 permite acompanhar o resultado. Com o mapa pronto, o Nav2 pode guiar o robô até um destino. No robô físico, os sensores e motores reais entram nesse mesmo fluxo.

## Como ler os comandos ROS 2

A estrutura mais comum para abrir um launch é

```bash
ros2 launch <pacote> <arquivo_de_launch> [argumentos]
```

Por exemplo, o arquivo `src/d_hospital_slam/launch/online_async_launch.py` é chamado assim

```bash
ros2 launch d_hospital_slam online_async_launch.py use_sim_time:=false
```

- `ros2` abre a ferramenta de linha de comando do ROS 2.
- `launch` escolhe a ação de iniciar um conjunto de nós e suas configurações.
- `d_hospital_slam` é o nome do pacote, declarado no `package.xml` e geralmente igual ao nome da pasta diretamente dentro de `src`.
- `online_async_launch.py` é o arquivo de launch instalado pelo pacote.
- `use_sim_time:=false` é um argumento aceito por esse launch e escolhe o relógio real.

Para executar um programa instalado por um pacote, a estrutura é

```bash
ros2 run <pacote> <executavel> [argumentos]
```

Por exemplo, `ros2 run nav2_map_server map_saver_cli` executa o programa que salva mapas. O nome do executável é definido pela instalação do pacote e pode ser diferente do nome do arquivo de código. Os pacotes ficam disponíveis depois de compilar o workspace e carregar o ambiente com `source`.

Os complementos dependem da ação. Launches aceitam argumentos como `use_sim_time:=true`, enquanto nós podem receber parâmetros como `--ros-args -p use_sim_time:=true`. Para ver os argumentos de um launch, use

```bash
ros2 launch d_hospital_slam online_async_launch.py --show-args
```

## Como fazer o mapeamento

### Preparar o workspace

Os comandos abaixo são para Linux, com Bash e ROS 2 Humble. Abra o terminal na raiz do workspace, a pasta que contém `src`.

Na primeira compilação ou depois de alterar o projeto, rode

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Em cada terminal novo, entre na raiz do workspace e carregue o ambiente

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

## Terminal 1 — Iniciar o robô

Escolha um dos caminhos e mantenha esse terminal aberto.

```text
                     Ambiente usado
                      ↙          ↘
             Robô físico        Simulação
                                 ↙      ↘
                        Gazebo Classic  Gazebo Sim / Ignition
```

**Robô físico**

```bash
ros2 launch minihema_launch minihema_launch.py
```

**Simulação com Gazebo Classic**

```bash
ros2 launch d_hospital_gazebo2 hospital.py
```

**Simulação com Gazebo Sim / Ignition**

```bash
ros2 launch d_hospital_gz gz_launch.py
```

Esses launches incluem a inicialização do controle por joystick. A simulação depende dos pacotes e plugins da versão de Gazebo escolhida.

## Terminal 2 — Iniciar o mapeamento

Escolha o relógio correspondente ao ambiente do terminal 1 e mantenha esse terminal aberto.

```text
                     Ambiente usado
                      ↙          ↘
             Robô físico        Simulação
           relógio real       relógio do Gazebo
```

**Robô físico**

```bash
ros2 launch d_hospital_slam online_async_launch.py use_sim_time:=false
```

**Simulação**

```bash
ros2 launch d_hospital_slam online_async_launch.py use_sim_time:=true
```

O SLAM Toolbox recebe as varreduras do LiDAR em `/scan` e monta o mapa conforme o robô explora o ambiente.

## Terminal 3 — Acompanhar o mapa no RViz

Escolha a opção correspondente ao ambiente do terminal 1.

```text
                     Ambiente usado
                      ↙          ↘
             Robô físico        Simulação
```

**Robô físico**

```bash
rviz2 -d "$(ros2 pkg prefix --share d_hospital_slam)/rviz/lidarbot_slam.rviz"
```

**Simulação**

```bash
rviz2 -d "$(ros2 pkg prefix --share d_hospital_slam)/rviz/lidarbot_slam.rviz" --ros-args -p use_sim_time:=true
```

Movimente o robô devagar pelo joystick e acompanhe no RViz as áreas que entram no mapa.

## Terminal 4 — Salvar o mapa

Depois de explorar o ambiente, mantenha o SLAM rodando e prepare a pasta de saída

```bash
mkdir -p ~/mapas
```

Escolha a opção correspondente ao ambiente do terminal 1.

```text
                     Ambiente usado
                      ↙          ↘
             Robô físico        Simulação
```

**Robô físico**

```bash
ros2 run nav2_map_server map_saver_cli -f ~/mapas/hospital
```

**Simulação**

```bash
ros2 run nav2_map_server map_saver_cli -f ~/mapas/hospital --ros-args -p use_sim_time:=true
```

O comando salva a imagem do mapa e o YAML com seus metadados. Troque `hospital` pelo nome desejado para guardar outro mapa. Esses arquivos servem para carregar a grade de ocupação depois. Para continuar uma sessão de SLAM com seu histórico, também é preciso salvar o grafo de poses pelo SLAM Toolbox. [Referência do Map Saver no Nav2](https://docs.nav2.org/rolling/tutorials/general_tutorials/navigation2_with_slam/navigation2_with_slam/)

## Terminal 4 — Conferir os dados se algo falhar

Use esse terminal para executar os comandos de diagnóstico, um por vez. Comandos que ficam acompanhando dados podem ser encerrados com `Ctrl+C`.

| Comando | O que conferir |
|---|---|
| `ros2 node list` | Quais nós estão rodando |
| `ros2 topic list` | Quais tópicos estão disponíveis |
| `ros2 topic hz /scan` | Se o LiDAR publica continuamente |
| `ros2 topic echo /odom --once` | Se a odometria chega |
| `ros2 topic info /map` | Quem publica e recebe o mapa |
| `ros2 run tf2_ros tf2_echo odom base_footprint` | A transformação da odometria para a base do robô |
| `ros2 run tf2_ros tf2_echo map odom` | A transformação produzida pelo SLAM |
| `ros2 param get /slam_toolbox use_sim_time` | Se o SLAM usa o relógio escolhido |

Os nomes dos launches e os tópicos foram conferidos nos arquivos desta branch. O roteiro ainda precisa de validação executando o ROS 2 no robô ou na simulação.

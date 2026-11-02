# d_hospital_control — lateral_pid_controller

Nó ROS2 (Python, `ament_python`) que fecha a malha de controle para eliminar
o desvio lateral sistemático (`e_y`) observado na odometria em malha aberta.

Lê `/odom`, calcula o erro lateral `e_y` e o erro de rumo `e_yaw` em relação
à reta capturada no início do movimento, e publica em `/cmd_vel` uma
velocidade linear constante mais uma correção angular PID + amortecimento
de rumo.

## Instalação

Copie a pasta `d_hospital_control/` para dentro do `src/` do workspace
(junto de `d_hospital_gazebo2`, `d_hospital_description`, etc.), depois:

```bash
cd ~/seu_workspace
colcon build --packages-select d_hospital_control
source install/setup.bash
```

## Uso

1. Suba a simulação normalmente:
   ```bash
   ros2 launch d_hospital_gazebo2 hospital.py use_sim_time:=true
   ```

2. Em outro terminal, suba o controlador:
   ```bash
   ros2 launch d_hospital_control lateral_pid_launch.py
   ```
   O robô vai andar reto em `linear_velocity` (padrão 0.25 m/s) e parar
   sozinho ao atingir `goal_distance` (padrão 5.0 m, igual ao seu
   experimento). Ajuste os ganhos editando
   `config/pid_params.yaml` ou passando overrides:
   ```bash
   ros2 launch d_hospital_control lateral_pid_launch.py \
     params_file:=/caminho/para/outros_ganhos.yaml
   ```
   ou diretamente por CLI:
   ```bash
   ros2 run d_hospital_control lateral_pid_controller \
     --ros-args -p kp:=1.0 -p kd:=0.2 -p goal_distance:=5.0
   ```

3. Para repetir o experimento (reset + gravação), o serviço
   `/lateral_pid_controller/reset` zera o estado interno (integral,
   referência) sem precisar reiniciar o nó — chame-o logo após
   `/reset_simulation`:
   ```bash
   ros2 service call /reset_simulation std_srvs/srv/Empty
   ros2 service call /lateral_pid_controller/reset std_srvs/srv/Empty
   ```

## Antes de rodar: verifique o publisher de /odom

O launch `hospital.py` pode ter **dois publicadores concorrendo em
`/odom`**: o plugin nativo do Gazebo (`libgazebo_ros_diff_drive`, que já
publica odometria) e o `ekf_node` do `robot_localization` (que remapeia
sua saída `/odometry/filtered` para `/odom`). Isso pode injetar saltos na
odometria e prejudicar o termo derivativo do PID. Confirme com:

```bash
ros2 topic info /odom -v
```

Se aparecer mais de um publisher, desative um dos dois (por exemplo,
`ros2 launch d_hospital_gazebo2 hospital.py use_robot_localization:=false`
para usar só a odometria nativa do Gazebo, mais direta para esse teste).

## Rodando as 50 amostras (mesmo protocolo do experimento.sh)

O script `experimento_pid.sh` (na raiz deste zip, fora da pasta do pacote)
repete exatamente o protocolo do `experimento.sh` original — reset,
gravação de bag com `/odom` e `/cmd_vel`, 50 amostras, mesma distância de
5.0 m — trocando apenas o `ros2 topic pub` em malha aberta pelo
`lateral_pid_controller` em malha fechada. Copie-o para a raiz do seu
workspace (onde já está o `experimento.sh`) e rode:

```bash
chmod +x experimento_pid.sh
./experimento_pid.sh
```

Isso gera `amostras_pid_-0_25ms.zip`, no mesmo formato de
`amostras_-0_25ms.zip`, então dá pra jogar os dois direto no
`analise_odometria.py`. Basta adicionar uma segunda entrada no dicionário
`EXPERIMENTOS` no topo do script (e ajustar `N_AMOSTRAS` para 50, que é o
valor real usado no seu experimento):

```python
N_AMOSTRAS = 50

EXPERIMENTOS = {
    "-0.25 m/s (malha aberta)": "amostras_-0_25ms.zip",
    "-0.25 m/s (PID)":          "amostras_pid_-0_25ms.zip",
}
```

Assim os dois relatórios saem lado a lado, com a mesma métrica (`e_y`
final, CTE médio, IAE etc.) — o comparativo direto que mostra se o viés
sumiu.

## Nota sobre andar de ré (linear_velocity negativo)

O controlador já leva em conta o sentido do movimento: os termos de erro
lateral (P, I, D) são multiplicados pelo sinal de `linear_velocity`,
porque corrigir um desvio para a esquerda/direita exige esterçar para o
lado oposto quando o robô anda de ré (a mesma lógica de contra-esterçar
ao dar ré num carro). Se você notar o robô curvando cada vez mais para
um lado em vez de convergir para a reta, confira se está usando uma
versão do nó anterior a essa correção.

## Tuning dos ganhos

O erro observado é pequeno (poucos mm por metro), então comece com ganhos
conservadores e vá subindo aos poucos:

1. Zere `ki` e `kd`, suba `kp` até o robô visivelmente corrigir o desvio
   sem oscilar.
2. Se sobrar oscilação (o robô "serpenteia"), aumente `kd` aos poucos.
3. Se sobrar um erro residual constante (não zera), ligue `ki` com um
   valor pequeno (ex.: 0.05) — o `integral_limit` evita windup.
4. `kh` (amortecimento por yaw) ajuda a estabilizar mais rápido; se o
   robô ficar "nervoso" ao corrigir, reduza `kh` antes de reduzir `kp`.

Depois de tunado, rode o mesmo protocolo de 50 amostras do
`experimento.sh` trocando o `ros2 topic pub` por este nó e comparando os
mesmos gráficos (`analise_odometria.py`) — o `e_y` final e o CTE médio
devem cair bem próximos de zero e sem viés de sinal constante.

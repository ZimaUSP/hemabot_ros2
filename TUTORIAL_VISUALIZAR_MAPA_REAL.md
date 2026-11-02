# Tutorial: visualizar o mapa real do HemaBot

Este tutorial mostra como visualizar o mapa real existente no workspace do HemaBot, tanto como uma imagem comum quanto no RViz.

## Arquivos do mapa

O mapa real é composto por dois arquivos:

```text
src/d_hospital_navigation2/maps/real_map3.pgm
src/d_hospital_navigation2/maps/real_map3.yaml
```

- `real_map3.pgm`: imagem do mapa de ocupação;
- `real_map3.yaml`: resolução, origem, limiares e caminho da imagem.

Na imagem:

- preto representa obstáculos ou paredes;
- branco representa espaço livre;
- cinza representa área desconhecida ou ainda não mapeada.

## 1. Abrir a imagem diretamente

Entre no workspace:

```bash
cd /home/lukaf04/hemabot_ros2
```

Abra o arquivo PGM com o visualizador padrão:

```bash
xdg-open src/d_hospital_navigation2/maps/real_map3.pgm
```

Em ambientes com o visualizador Eye of GNOME, também é possível usar:

```bash
eog src/d_hospital_navigation2/maps/real_map3.pgm
```

> Os comandos acima precisam ser executados em uma sessão gráfica. Em uma conexão SSH sem encaminhamento gráfico, converta ou copie a imagem para o computador local.

## 2. Converter o mapa para PNG

Se o visualizador não aceitar o formato PGM, use `pnmtopng`:

```bash
pnmtopng \
  src/d_hospital_navigation2/maps/real_map3.pgm \
  > /tmp/real_map3.png
```

Abra a imagem convertida:

```bash
xdg-open /tmp/real_map3.png
```

Se o comando `pnmtopng` não estiver disponível, instale o pacote correspondente:

```bash
sudo apt install netpbm
```

## 3. Dimensões físicas do mapa

O arquivo `real_map3.pgm` possui 227 por 242 pixels. A resolução declarada no YAML é:

```yaml
resolution: 0.05
```

Isso corresponde a 5 centímetros por pixel. Portanto, a área total representada pela imagem é aproximadamente:

```text
largura: 227 × 0,05 = 11,35 m
altura:  242 × 0,05 = 12,10 m
```

## 4. Visualizar o mapa no RViz

O RViz é a melhor opção para analisar o mapa com coordenadas, escala, pose do robô, laser e elementos do Nav2.

### Terminal 1: carregar o mapa

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch d_hospital_navigation2 localization_launch.py \
  use_sim_time:=false \
  map:=/home/lukaf04/hemabot_ros2/src/d_hospital_navigation2/maps/real_map3.yaml
```

### Terminal 2: abrir o RViz

```bash
cd /home/lukaf04/hemabot_ros2
source /opt/ros/humble/setup.bash
source install/setup.bash

rviz2 -d src/d_hospital_navigation2/rviz/lidarbot_nav.rviz
```

No RViz, confira:

- `Fixed Frame`: `map`;
- visualização `Map`: tópico `/map`;
- visualização `LaserScan`: tópico `/scan`, caso o robô esteja ligado;
- `RobotModel` habilitado, caso o `robot_state_publisher` esteja executando.

Se o mapa não aparecer, adicione manualmente uma visualização do tipo **Map** e selecione o tópico `/map`.

## 5. Verificações

Confirme que o servidor de mapa está ativo:

```bash
ros2 lifecycle get /map_server
```

O resultado esperado é:

```text
active
```

Confirme que o mapa está sendo publicado:

```bash
ros2 topic echo /map --once
```

Veja as informações do tópico:

```bash
ros2 topic info /map -v
```

## Observação sobre a qualidade do mapa

O `real_map3` apresenta regiões não exploradas e alguns rastros de leituras do laser fora das paredes principais. Antes de utilizá-lo para navegação autônoma, é recomendável conferir:

- se a odometria está calibrada;
- se a transformação entre `base_footprint` e `lidar_link` está correta;
- se o LiDAR está rigidamente fixado;
- se os pontos do laser coincidem com as paredes no RViz;
- se o ambiente foi percorrido devagar e com fechamento de ciclos.


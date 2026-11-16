# src

O `src` reúne os pacotes ROS 2 do HemaBot. Para entender a parte de mapeamento, comece pelo `d_hospital_slam`, que monta o mapa com o LiDAR. O `d_hospital_navigation2` cuida de usar mapas prontos para se localizar e navegar.

## Pastas e pacotes

- [`.vscode/`](.vscode/README.md) — Ajustes do editor para o código C, C++ e Python do workspace.
- [`d_hospital_description/`](d_hospital_description/README.md) — Modelo do robô, incluindo peças, juntas e sensores.
- [`d_hospital_gazebo2/`](d_hospital_gazebo2/README.md) — Simulação do robô com Gazebo Classic, incluindo o cenário do hospital.
- [`d_hospital_gz/`](d_hospital_gz/README.md) — Simulação com Gazebo Sim (Ignition) e ponte de sensores para o ROS 2.
- [`d_hospital_navigation2/`](d_hospital_navigation2/README.md) — Localização em mapas prontos, planejamento de rotas e acompanhamento da trajetória com Nav2.
- [`d_hospital_slam/`](d_hospital_slam/README.md) — Criação de mapas a partir das leituras do LiDAR com SLAM Toolbox.
- [`d_hospital_teleop/`](d_hospital_teleop/README.md) — Controle do robô com joystick e seleção da fonte de comandos de velocidade.
- [`firmware_minihema/`](firmware_minihema/README.md) — Interface do ROS 2 com os motores e encoders do robô físico.
- [`minihema_launch/`](minihema_launch/README.md) — Inicialização do robô físico e integração com o LiDAR, a câmera e a IMU.

# minihema_launch

## Subpastas

- [`config/`](config/README.md) — Arquivos YAML com parâmetros dos nós e componentes ROS 2 do pacote.
- [`include/`](include/README.md) — Cabeçalhos C e C++ usados pelo código do pacote.
- [`launch/`](launch/README.md) — Arquivos Python que organizam quais nós do pacote sobem e com quais parâmetros.
- [`scripts/`](scripts/README.md) — Nós e ferramentas Python do pacote.
- [`src/`](src/README.md) — Código C e C++ de drivers, interfaces de hardware e utilitários.

## Arquivos

- `CMakeLists.txt` — Compila o plugin da IMU e os utilitários de calibração e instala os launches.
- `mpu6050_hardware.xml` — Registra o plugin da IMU no pluginlib para o ros2_control encontrá-lo.
- `package.xml` — Declara os metadados e as dependências do pacote ROS 2.

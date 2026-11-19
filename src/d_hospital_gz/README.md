# d_hospital_gz

## Subpastas

- [`config/`](config/README.md) — Arquivos YAML com parâmetros dos nós e componentes ROS 2 do pacote.
- [`launch/`](launch/README.md) — Arquivos Python que organizam quais nós do pacote sobem e com quais parâmetros.
- [`models/`](models/README.md) — Modelos de objetos usados nos cenários do Gazebo Sim.
- [`urdf/`](urdf/README.md) — Arquivos Xacro que montam o modelo e definem juntas, sensores e controle.
- [`worlds/`](worlds/README.md) — Cenários carregados pelo Gazebo para simular o ambiente do robô.

## Arquivos

- `CMakeLists.txt` — Instala os launches e recursos da simulação no Gazebo Sim.
- `package.xml` — Declara os metadados e as dependências do pacote ROS 2.

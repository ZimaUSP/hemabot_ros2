# 🏥 Robô de Entregas Hospitalar

## 📖 Contexto do Projeto

Foi a partir do **Dr. Oscar Fujita**, Diretor do **Núcleo de Inovação e Tecnologia (INTEC)**, que surgiu a demanda pelo **robô hospitalar**.  
Com o agravamento da pandemia, para evitar o contágio dos colaboradores com materiais potencialmente contaminados por **COVID-19**, foi sugerido o desenvolvimento de um robô capaz de **realizar o transporte autônomo de amostras laboratoriais**.

Através de diversos **sensores de distância**, **mapeamento digital** e **algoritmos de navegação**, o robô pode se locomover de forma **segura e autônoma** dentro do ambiente hospitalar.  
Além disso, está em desenvolvimento o **aplicativo do Robô Hospitalar**, que permitirá chamar o robô e iniciar seu deslocamento até o local solicitado.

---

## 🤖 Descrição Geral

<!-- PADRONIZAÇÃO: O robô é chamado de “MiniHema” ao longo deste README. “hemabot_ros2” foi mantido exclusivamente como nome do repositório, e nomes de pacotes e comandos não foram alterados. -->

Este projeto é uma versão de controle manual do robô hospitalar, permitindo operá-lo remotamente a partir do **teclado do computador**.  
O sistema lê os comandos de teclado e envia instruções para o robô, que se movimenta em tempo real.

A comunicação pode ocorrer de duas formas:

- **Serial (USB)** – conexão direta com o microcontrolador.
- **Wi-Fi (Socket TCP/UDP)** – controle remoto via rede.

Ambas as formas de comunicação, incluindo os comandos “F”, “B”, “L”, “R” e “S”, fazem parte do projeto.

O código foi estruturado de forma modular, permitindo adaptação para plataformas como **Raspberry Pi** e **Jetson Nano**.

---

## ⚙️ Requisitos

### 💻 No computador:

- **Sistema operacional:** Windows ou Linux.
- **ROS 2:** Humble.

<!-- TODO: confirmar as dependências adicionais necessárias no computador. -->

### 🤖 No robô:

- Plataforma compatível (ex.: ESP32, Arduino Mega ou Raspberry Pi).
- Firmware que interprete os comandos enviados (ex.: “F”, “B”, “L”, “R”, “S”).

---

## 🧩 Instalação

1. Clone o repositório:

   ```bash
   git clone git@github.com:ZimaUSP/hemabot_ros2.git
   cd hemabot_ros2
   ```

2. Instale as dependências:

   <!-- ATENÇÃO: O arquivo requirements.txt não existe no repositório atual. O projeto está estruturado como um workspace ROS 2 compilado com colcon. Confirmar se esse arquivo deve ser criado ou se o comando abaixo deve ser substituído por instruções de rosdep. -->

   ```bash
   pip install -r requirements.txt
   ```

3. Conecte o robô ao computador via **USB** ou conecte ambos à **mesma rede Wi-Fi**. Para acesso remoto pela rede Wi-Fi, use SSH:

   <!-- ATENÇÃO: O comando SSH aplica-se à conexão pela rede Wi-Fi, não à conexão USB. -->
   <!-- SEGURANÇA: Confirme se o usuário e o IP ainda são válidos. Não publique senhas, chaves privadas ou outras credenciais no repositório. -->

   ```bash
   ssh -X hemabot@192.168.1.155
   ```

4. Digite a senha solicitada.

**Observação:** o PC deve estar conectado à rede Zima 5G.

<!-- TODO: confirmar se “Zima 5G”, o usuário hemabot e o IP 192.168.1.155 são requisitos atuais do ambiente. -->

## ▶️ Como Executar

Para controlar o robô, acesse o diretório do repositório `hemabot_ros2` e digite os seguintes comandos no terminal.

Caso tenha alterado o código, execute o comando `colcon build` na raiz do workspace:

```bash
colcon build
```

```bash
source install/setup.bash
```

Por fim, insira o seguinte comando:

```bash
ros2 launch minihema_launch minihema_launch.py
```

A partir daqui, todos os dados recebidos via sensores passam a ser compartilhados.

A câmera não está em uso no fluxo atual.

## ⌨️ Comandos via Teclado

Em geral, existem duas maneiras de movimentar o MiniHema por meio do teclado.

### Mensagem diretamente no tópico

Para enviar uma mensagem diretamente por um tópico do sistema, aplique o seguinte comando:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: v}, angular: {z: w}}"
```

Inserindo valores numéricos em `v` e `w`, a movimentação será realizada.

<!-- NOTA: No fluxo ROS 2, /cmd_vel é uma entrada do twist_mux, que encaminha comandos ao diff_controller. Os comandos “F”, “B”, “L”, “R” e “S” pertencem às formas de comunicação Serial/USB e Wi-Fi/Socket. -->

### Usando o pacote teleop_twist_keyboard

O pacote `teleop_twist_keyboard` permite o envio de comandos de direção por meio do teclado. Para executar, digite:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

No terminal, serão mostradas todas as teclas de movimentação:

<img width="328" height="289" alt="image" src="https://github.com/user-attachments/assets/0c0c217f-d6a1-4c0f-b5a9-ef426f77b278" />

## 🛑 Desligando com Segurança

1. Finalize os terminais abertos.
2. Desligue a alimentação do MiniHema e desconecte o LiDAR.

---

## 🧱 Estrutura do Projeto

O repositório está organizado como um workspace ROS 2. A estrutura abaixo apresenta seus principais arquivos, pacotes e diretórios:

```text
hemabot_ros2/
├── calibrar_covariancias.sh
├── calibrar_offsets
├── start_hema.sh
├── start_hema_b.sh
├── mapa*                 # Mapas gerados (.pgm, .png, .yaml, .data e .posegraph)
├── *.log                 # Logs de execução
├── frames_*.gv / *.pdf  # Arquivos de diagnóstico
├── README.md
└── src/
    ├── d_hospital_description/
    │   ├── config/
    │   ├── launch/
    │   ├── meshes/
    │   ├── rviz/
    │   ├── urdf/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── d_hospital_gazebo2/
    │   ├── config/
    │   ├── launch/
    │   ├── worlds/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── d_hospital_gz/
    │   ├── config/
    │   ├── launch/
    │   ├── models/
    │   ├── urdf/
    │   ├── worlds/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── d_hospital_navigation2/
    │   ├── config/
    │   ├── d_hospital_navigation2/
    │   ├── launch/
    │   ├── maps/
    │   ├── rviz/
    │   ├── scripts/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── d_hospital_slam/
    │   ├── config/
    │   ├── launch/
    │   ├── rviz/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── d_hospital_teleop/
    │   ├── config/
    │   ├── launch/
    │   ├── CMakeLists.txt
    │   └── package.xml
    ├── firmware_minihema/
    │   ├── include/
    │   ├── src/
    │   ├── CMakeLists.txt
    │   └── package.xml
    └── minihema_launch/
        ├── config/
        ├── include/
        ├── launch/
        ├── scripts/
        ├── src/
        ├── CMakeLists.txt
        └── package.xml
```

---

## ⚠️ Possíveis Erros e Soluções

<!-- ATENÇÃO: A solução abaixo parece relacionada a SSH ou Socket TCP/UDP. No fluxo ROS 2 local com ros2_control, “Connection refused” pode ter outras causas. Confirmar a qual conexão e a qual aplicação esta linha se refere. -->

| Erro | Causa | Solução |
| --- | --- | --- |
| `Connection refused` | IP incorreto ou robô desconectado | Verifique o endereço IP no código do robô |

---

## 🤝 Contribuindo

1. Faça um fork do projeto.
2. Crie uma nova branch:

   ```bash
   git checkout -b minha-feature
   ```

3. Realize suas modificações e envie um **pull request**.

---

## 🎥 Exemplo em Ação

<!-- Espaço reservado para adicionar futuramente a demonstração do robô. -->

[A PREENCHER]

## 📝 Pendências de Revisão

- Confirmar as dependências adicionais necessárias no computador.
- Validar o usuário `hemabot`, o IP `192.168.1.155` e a exigência da rede Zima 5G.

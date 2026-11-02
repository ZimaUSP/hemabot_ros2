<div align="center">

<h1 id="topo">🏥 Robô de Entregas Hospitalar</h1>

<p><strong>Robótica hospitalar com ROS 2, sensores, mapeamento e navegação.</strong></p>

<p>
  <a href="https://docs.ros.org/en/humble/">
    <img src="https://img.shields.io/badge/ROS%202-Humble-22314E?style=flat-square&logo=ros&logoColor=white" alt="ROS 2 Humble">
  </a>
  <img src="https://img.shields.io/badge/Sistema-Windows%20%7C%20Linux-0078D4?style=flat-square" alt="Windows ou Linux">
  <img src="https://img.shields.io/badge/Aplicativo-em%20desenvolvimento-F2A900?style=flat-square" alt="Aplicativo em desenvolvimento">
  <a href="https://github.com/ZimaUSP/hemabot_ros2/stargazers">
    <img src="https://img.shields.io/github/stars/ZimaUSP/hemabot_ros2?style=flat-square" alt="GitHub Stars">
  </a>
  <a href="https://github.com/ZimaUSP/hemabot_ros2/issues">
    <img src="https://img.shields.io/github/issues/ZimaUSP/hemabot_ros2?style=flat-square" alt="GitHub Issues">
  </a>
</p>

<p>
  <a href="#-contexto-do-projeto">Contexto</a> •
  <a href="#-requisitos">Requisitos</a> •
  <a href="#-instalação">Instalação</a> •
  <a href="#-como-executar">Execução</a> •
  <a href="#-estrutura-do-projeto">Estrutura</a> •
  <a href="#-contribuindo">Contribuição</a>
</p>

</div>

---

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

| Canal | Conexão | Finalidade |
| --- | --- | --- |
| **Serial** | USB | Conexão direta com o microcontrolador |
| **Wi-Fi** | Socket TCP/UDP | Controle remoto via rede |

Ambas as formas de comunicação, incluindo os comandos “F”, “B”, “L”, “R” e “S”, fazem parte do projeto.

O código foi estruturado de forma modular, permitindo adaptação para plataformas como **Raspberry Pi** e **Jetson Nano**.

<!-- Substitua os espaços abaixo pelas imagens correspondentes quando estiverem disponíveis. -->

<table>
  <tr>
    <td align="center" width="33%">
      <strong>🖼️ Design geral</strong><br><br>
      <sub>Espaço reservado para uma imagem de apresentação do MiniHema.</sub>
    </td>
    <td align="center" width="33%">
      <strong>📐 Vista lateral</strong><br><br>
      <sub>Espaço reservado para uma imagem lateral ou desenho técnico do robô.</sub>
    </td>
    <td align="center" width="33%">
      <strong>⚙️ Componentes internos</strong><br><br>
      <sub>Espaço reservado para uma imagem dos sensores e componentes internos.</sub>
    </td>
  </tr>
</table>

---

## ⚙️ Requisitos

### 💻 No computador:

| Item | Requisito |
| --- | --- |
| Sistema operacional | Windows ou Linux |
| ROS 2 | Humble |

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

   > [!IMPORTANT]
   > O comando SSH aplica-se somente à conexão pela rede Wi-Fi, não à conexão USB.

   ```bash
   ssh -X hemabot@192.168.1.155
   ```

4. Digite a senha solicitada.

**Segurança:** não publique senhas, chaves privadas ou outras credenciais no repositório.

> [!NOTE]
> O PC deve estar conectado à rede Zima 5G.

<!-- TODO: confirmar se “Zima 5G”, o usuário hemabot e o IP 192.168.1.155 são requisitos atuais do ambiente. -->

---

## ▶️ Como Executar

Para controlar o robô, acesse o diretório do repositório `hemabot_ros2` e digite os seguintes comandos no terminal.

Caso tenha alterado o código, execute o comando `colcon build` na raiz do workspace:

```bash
colcon build
source install/setup.bash
```

Por fim, insira o seguinte comando:

```bash
ros2 launch minihema_launch minihema_launch.py
```

> [!NOTE]
> Após o launch, os dados dos sensores ativos passam a ser compartilhados pelos nós ROS 2. A câmera não está em uso no fluxo atual.

---

## ⌨️ Comandos via Teclado

Em geral, existem duas maneiras de movimentar o MiniHema por meio do teclado.

### Mensagem diretamente no tópico

Para enviar uma mensagem diretamente por um tópico do sistema, aplique o seguinte comando:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: v}, angular: {z: w}}"
```

Inserindo valores numéricos em `v` e `w`, a movimentação será realizada.

> [!NOTE]
> No fluxo ROS 2, `/cmd_vel` é uma entrada do `twist_mux`, que encaminha comandos ao `diff_controller`. Os comandos “F”, “B”, “L”, “R” e “S” pertencem às formas de comunicação Serial/USB e Wi-Fi/Socket.

### Usando o pacote teleop_twist_keyboard

O pacote `teleop_twist_keyboard` permite o envio de comandos de direção por meio do teclado. Para executar, digite:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

No terminal, serão mostradas todas as teclas de movimentação:

<p align="center">
  <img width="328" height="289" alt="Teclas de movimentação do teleop_twist_keyboard" src="https://github.com/user-attachments/assets/0c0c217f-d6a1-4c0f-b5a9-ef426f77b278" />
</p>

---

## 🛑 Desligando com Segurança

1. Finalize os terminais abertos.
2. Desligue a alimentação do MiniHema e desconecte o LiDAR.

---

## 🧱 Estrutura do Projeto

O repositório está organizado como um workspace ROS 2. A estrutura abaixo apresenta seus principais arquivos, pacotes e diretórios:

<details>
<summary><strong>📂 Visualizar a árvore do workspace</strong></summary>

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

</details>

---

## ⚠️ Possíveis Erros e Soluções

<!-- ATENÇÃO: A solução abaixo parece relacionada a SSH ou Socket TCP/UDP. No fluxo ROS 2 local com ros2_control, “Connection refused” pode ter outras causas. Confirmar a qual conexão e a qual aplicação esta linha se refere. -->

| Erro | Causa | Solução |
| --- | --- | --- |
| `Connection refused` | IP incorreto ou robô desconectado | Verifique o endereço IP no código do robô |

---

## 🤝 Contribuindo

Correções, melhorias na documentação e novas funcionalidades são bem-vindas.

1. Faça um fork do projeto.
2. Crie uma nova branch:

   ```bash
   git checkout -b minha-feature
   ```

3. Realize suas modificações e envie um **pull request**.

---

## 🎥 Exemplo em Ação

<div align="center">

<p><strong>🎬 Demonstração em preparação</strong></p>

<sub>Este espaço está reservado para adicionar futuramente uma demonstração do robô.</sub>

</div>

---

## 📝 Pendências de Revisão

- [ ] Confirmar as dependências adicionais necessárias no computador.
- [ ] Validar o usuário `hemabot`, o IP `192.168.1.155` e a exigência da rede Zima 5G.

<p align="right"><a href="#topo">⬆️ Voltar ao início</a></p>

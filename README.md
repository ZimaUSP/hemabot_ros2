# 🏥 Robô de Entregas Hospitalar

## 📖 Contexto do Projeto

Foi a partir do **Dr. Oscar Fujita**, Diretor do **Núcleo de Inovação e Tecnologia (INTEC)**, que surgiu a demanda pelo **robô hospitalar**.  
Com o agravamento da pandemia, para evitar o contágio dos colaboradores com materiais potencialmente contaminados por **COVID-19**, foi sugerido o desenvolvimento de um robô capaz de **realizar o transporte autônomo de amostras laboratoriais**.

Através de diversos **sensores de distância**, **mapeamento digital** e **algoritmos de navegação**, o robô pode se locomover de forma **segura e autônoma** dentro do ambiente hospitalar.  
Além disso, para ser chamado, basta um simples **clique no aplicativo do Robô Hospitalar**, que inicia o deslocamento até o local solicitado.

---

## 🤖 Descrição Geral

Este projeto é uma versão de controle manual do robô hospitalar, permitindo operá-lo remotamente a partir do **teclado do computador**.  
O sistema lê os comandos de teclado e envia instruções para o robô, que se movimenta em tempo real.

A comunicação pode ocorrer de duas formas:
- **Serial (USB)** – conexão direta com o microcontrolador.  
- **Wi-Fi (Socket TCP/UDP)** – controle remoto via rede.

O código foi estruturado de forma modular, permitindo adaptação para plataformas como **Raspberry PI** e **Jetson Nano**.

---

## ⚙️ Requisitos

### 💻 No computador:

### 🤖 No robô:
- Microcontrolador compatível (ex: ESP32, Arduino Mega, Raspberry Pi)
- Firmware que interprete os comandos enviados (ex: “F”, “B”, “L”, “R”, “S”)

---

## 🧩 Instalação

1. Clone o repositório:
   ```bash
   git clone git@github.com:ZimaUSP/hemabot_ros2.git
   cd robo-hospitalar
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Conecte o robô ao computador via **USB** ou conecte ambos na **mesma rede Wi-Fi** através da chave ssh.

 ```bash
   ssh -X hemabot@192.168.1.155
   ```
4. Digite a senha solicitada.

Obs.: O PC deve estar conectado a rede Zima 5G
## ▶️ Como Executar

Para controlar o robô, acesse o diretório do hemabot e digite os seguintes comandos no terminal:

Caso tiver alterado o código, use o comando colcon build em d_hospital_new:

```bash
   concon build
   ```

```bash
   source install/setup.bash
   ```

- E finalmente, insira o seguinte comando:

```bash
   ros2 launch minihema_launch minihema_launch.py 
   ```

A partir daqui, todos os dados recebidos via sensores passam a ser compartilhados.

## ⌨️ Comandos via Teclado

- Em geral, existem duas maneiras de movimentar o MiniHema por meio do teclado:

## Mensagem diretamente no tópico

- Para uma mensagem diretamente através de um tópico do sistema, basta aplicar o seguinte comando:
  ```bash
   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: v}, angular: {z: w}}"
   ```
Inserindo valores numéricos a v e w, a movimentação será realizada.

## Usando o pacote teleop_twist_keyboard 

- O pacote teleop_twist_keyboard permite que haja o envio de comandos de direção por meio do teclado. Para executar, digite:
  ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   ```
No terminal serão mostradas todas as teclas de movimentação:

<img width="328" height="289" alt="image" src="https://github.com/user-attachments/assets/0c0c217f-d6a1-4c0f-b5a9-ef426f77b278" />




## 🛑 Desligando com Segurança

1. Finalize os terminais abertos.  
2. Desligue a alimentação do Hema e desconecte o LiDAR:
---

## 🧱 Estrutura do Projeto

```
robo-hospitalar/
│
├── main.py              # Programa principal
├── robo/
│   ├── controller.py    # Controle do robô
│   ├── serial_conn.py   # Comunicação Serial
│   ├── wifi_conn.py     # Comunicação via Wi-Fi
│
├── config.json          # Configurações de conexão
├── requirements.txt     # Dependências Python
└── README.md            # Este arquivo :)
```

---

## ⚠️ Possíveis Erros e Soluções

| Erro | Causa | Solução |
|------|--------|----------|
| `Connection refused` | IP incorreto ou robô desconectado | Verifique o endereço IP no código do robô |

---

## 🤝 Contribuindo

1. Faça um fork do projeto  
2. Crie uma nova branch:  
   ```bash
   git checkout -b minha-feature
   ```
3. Realize suas modificações e envie um **pull request**.

---

## 🎥 Exemplo em Ação

![Demonstração do Robô](docs/demo.gif)

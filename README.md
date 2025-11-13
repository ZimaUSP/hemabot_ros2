# 🏥 Robô Hospitalar Controlado por Teclado

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
- **Python 3.8 ou superior**
- Bibliotecas:
  ```bash
  pip install pyserial pynput
  ```
  *(caso use controle via rede, adicione `pip install socket`)*

### 🤖 No robô:
- Microcontrolador compatível (ex: ESP32, Arduino Mega, Raspberry Pi)
- Firmware que interprete os comandos enviados (ex: “F”, “B”, “L”, “R”, “S”)

---

## 🧩 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seuusuario/robo-hospitalar.git
   cd robo-hospitalar
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Conecte o robô ao computador via **USB** ou conecte ambos na **mesma rede Wi-Fi**.

---

## ▶️ Como Executar

No terminal do linux, digite:

 ```bash
   cd d_hospital_new
   ```
- Digite ls

vai aparecer:
```bash
   src
   ```
Caso tiver alterado o código, use o comando colcon build em d_hospital_new:

```bash
   concon build
   ```

- Digite ls

Você verá:

```bash
   source install/setup.bash
   ```

- E finalmente, insira o seguinte comando:

```bash
   ros2 launch minihema_launch minihema_launch.py 
   ```

Você deverá ver algo como:


## ⌨️ Comandos do Teclado

| Tecla | Ação                     |
|:------|:--------------------------|
| **W** | Mover para frente         |
| **S** | Mover para trás           |
| **A** | Girar para esquerda       |
| **D** | Girar para direita        |
| **Espaço** | Parar                 |
| **Q** | Desligar conexão / sair   |

---

## 🔌 Conectando ao Robô

### 🔹 Via Serial
1. Conecte o cabo USB ao robô.  
2. Descubra a porta serial:
   - **Windows:** abra o *Gerenciador de Dispositivos* → “Portas (COM e LPT)”.
   - **Linux/macOS:** use `ls /dev/tty*` e procure algo como `/dev/ttyUSB0`.
3. Edite o arquivo `config.json`:
   ```json
   {
     "modo": "serial",
     "porta": "COM3",
     "baudrate": 9600
   }
   ```

### 🔹 Via Wi-Fi
1. Conecte o robô e o computador na mesma rede.  
2. Edite o arquivo `config.json`:
   ```json
   {
     "modo": "wifi",
     "ip": "192.168.0.50",
     "porta": 8080
   }
   ```

3. Execute o programa e aguarde a mensagem de sucesso na conexão.

---

## 🛑 Desligando com Segurança

1. Pressione **Q** para encerrar a conexão.  
2. Aguarde a mensagem:
   ```
   [INFO] Conexão encerrada com sucesso.
   ```
3. Só então desligue o robô ou desconecte o cabo USB.

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
| `Permission denied /dev/ttyUSB0` | Falta de permissão serial | Execute `sudo chmod 666 /dev/ttyUSB0` |
| `Connection refused` | IP incorreto ou robô desconectado | Verifique o endereço IP no código do robô |
| Robô não responde | Baudrate incorreto | Ajuste o valor no `config.json` |

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

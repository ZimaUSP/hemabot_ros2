# Instalação

## Requisitos 

Raspberry Pi 4

Notebook com entrada ou adaptador para microSD

Cartão microSD com pelo menos 10 Gb, (recomendável tamanho de 32 Gb) que terá sua memória apagada

## Etapas

Baixe o raspberry pi imager no computador no link https://www.raspberrypi.com/software/

<img width="742" height="372" alt="Captura de tela 2026-06-18 175844" src="https://github.com/user-attachments/assets/16fb2be8-7455-426b-bd96-9da15f367f31" />


Abra o Raspberry Pi Imager, conecte seu microSD no notebook e realize a sequência de seleções nele


<img width="747" height="532" alt="Captura de tela 2026-06-18 175930" src="https://github.com/user-attachments/assets/8e72019b-4731-47ab-93fe-adf39a757f35" />

<img width="742" height="530" alt="Captura de tela 2026-06-18 175954" src="https://github.com/user-attachments/assets/a7192ff1-9558-4e78-b3dc-213d0f0eee5e" />

<img width="840" height="595" alt="Captura de tela 2026-06-18 180845" src="https://github.com/user-attachments/assets/de11102f-ff67-4019-a960-bc96347ff3fc" />

<img width="742" height="550" alt="Captura de tela 2026-06-18 180029" src="https://github.com/user-attachments/assets/1b5f4286-62d5-452f-aef5-50e8d53b0fd0" />

Agora, selecione o seu microSD (na imagem aparece um SD de 7 Gb, mas é necessário um de pelo menos 10 Gb)

<img width="747" height="537" alt="Captura de tela 2026-06-18 182106" src="https://github.com/user-attachments/assets/cd4d207a-330e-4bc7-940a-577a33bc2d28" />

Escreva o seu hostname

<img width="747" height="547" alt="Captura de tela 2026-06-18 182245" src="https://github.com/user-attachments/assets/243c3f64-9edf-4f34-9753-965a05bf0caa" />

Configure com base em seus dados preferiveis

<img width="747" height="532" alt="Captura de tela 2026-06-18 182326" src="https://github.com/user-attachments/assets/d9bc3782-ca3c-4e93-a5de-5ba054bffead" />

Agora coloque o nome de usuário e sua senha

<img width="750" height="535" alt="Captura de tela 2026-06-18 182410" src="https://github.com/user-attachments/assets/e4ccfea8-5657-44ca-adf8-0b25e8f0aaf2" />

Configure a internet, colocando a rede e senha que o robô irá se conectar

<img width="747" height="532" alt="Captura de tela 2026-06-18 182436" src="https://github.com/user-attachments/assets/00c7a15f-9dd7-4bf9-8aa7-08f091d2c358" />

<img width="750" height="532" alt="Captura de tela 2026-06-18 182450" src="https://github.com/user-attachments/assets/f6d2e5c7-5616-4f43-b4c1-f1c211519b95" />

Depois disso, clique em WRITE e em seguida confirme o apagamento dos dados atuais do microSD

Após esperar o download, conecte o microSD em sua Raspberry Pi 4.



## Conectando via SSH

Abra seu terminal e faça a conexão SSH, para isso é necessário descobrir o IP do raspberry pi ou então tentar identificar pelo hostname, as duas opções de comando estão listadas abaixo:

``` sh
ssh your_username@your_hostname.local
ssh your_username@192.168.x.x
```

Após isso, insira a senha que colocou para seu usuário e sua conexão será realizada.

## Instalação do ROS2

Antes de instalar qualquer coisa, é fundamental garantir que todos os pacotes atuais do sistema estejam na versão mais recente por meio do comando:

```sh
sudo apt update
sudo apt upgrade -y
```

Instale as dependências

```
sudo apt install -y curl gnupg2 lsb-release software-properties-common
```

Crie a pasta das chaves

``
sudo mkdir -p /etc/apt/keyrings
``
Baixar a chave oficial do ROS
````
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | sudo gpg --dearmor -o /etc/apt/keyrings/ros-archive-keyring.gpg
````
E adicionar o repositório do ROS2

````
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
````
Atualize novamente com o ''sudo apt update''

E agora vamos instalar o ROS2

````
sudo apt install ros-humble-ros-base
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
ros2 --version
ros2 topic list
````

Por fim, instalaremos as ferramentas de build

````
sudo apt install python3-colcon-common-extensions python3-rosdep python3-vcstool build-essential
sudo rosdep init
rosdep update
````


## Configuração de conexão a um outro wi-fi

## Configuração de um ID fixo

## Baixar as pastas do repositório github


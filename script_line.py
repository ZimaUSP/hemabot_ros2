from rosbags.rosbag2 import Reader
from rosbags.serde import deserialize_cdr
import matplotlib.pyplot as plt
import numpy as np

# Caminho para o DIRETÓRIO do bag (onde está o metadata.yaml e o .db3)
bag_path = './exp_linha_reta'

# Listas para armazenar as coordenadas
gt_x, gt_y = [], []
odom_x, odom_y = [], []

# Lendo o arquivo bag
with Reader(bag_path) as reader:
    for connection, timestamp, rawdata in reader.messages():
        
        # Lendo o Ground Truth
        if connection.topic == '/ground_truth/state':
            # deserialize_cdr converte os dados binários no formato da mensagem original
            msg = deserialize_cdr(rawdata, connection.msgtype)
            gt_x.append(msg.pose.pose.position.x)
            gt_y.append(msg.pose.pose.position.y)
            
        # Lendo a Odometria
        elif connection.topic == '/odom':
            msg = deserialize_cdr(rawdata, connection.msgtype)
            odom_x.append(msg.pose.pose.position.x)
            odom_y.append(msg.pose.pose.position.y)

# Convertendo para arrays do numpy para facilitar os cálculos de erro
gt_y = np.array(gt_y)
odom_y = np.array(odom_y)

print(f"Dados extraídos: {len(gt_x)} pontos de Ground Truth e {len(odom_x)} pontos de Odometria.")

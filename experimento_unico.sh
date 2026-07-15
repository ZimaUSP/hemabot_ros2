#!/bin/bash
#
# experimento_unico.sh
#
# Versão "single-shot" do experimento.sh: executa APENAS UMA amostra,
# para uma única velocidade. Útil para testar o setup (ROS2, tópicos,
# simulação) antes de rodar o experimento completo com as 30 amostras
# por velocidade.
#
# Uso:
#   ./experimento_unico.sh [velocidade_m_s] [distancia_m]
#
# Exemplos:
#   ./experimento_unico.sh              # usa valores padrão (0.5 m/s, 5.0 m)
#   ./experimento_unico.sh 1.0          # usa 1.0 m/s, distância padrão
#   ./experimento_unico.sh 0.25 3.0     # usa 0.25 m/s e 3.0 m

set -e

# --- Parâmetros (com valores padrão) ---
VEL="${1:-0.5}"
DISTANCIA="${2:-5.0}"

# Nome seguro para usar em arquivos (troca ponto por underscore)
VEL_NOME=$(echo "$VEL" | tr '.' '_')
DIR_AMOSTRA="amostra_unica_${VEL_NOME}ms"

# Calcula o tempo necessário para percorrer a distância na velocidade atual
TEMPO=$(echo "scale=4; $DISTANCIA / $VEL" | bc)

echo "========================================"
echo "Experimento único"
echo "Velocidade: ${VEL} m/s"
echo "Distância alvo: ${DISTANCIA} m | Tempo de movimento: ${TEMPO} s"
echo "========================================"

mkdir -p "$DIR_AMOSTRA"

echo "Iniciando amostra única (vel=${VEL} m/s, t=${TEMPO}s)"

# Reset da simulação
ros2 service call /reset_simulation std_srvs/srv/Empty

sleep 2

# Inicia gravação do bag
ros2 bag record -o "${DIR_AMOSTRA}/amostra1" /odom /cmd_vel &

BAG_PID=$!

sleep 2

# Movimento do robô pelo tempo calculado para manter distância constante
timeout "$TEMPO" ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: -${VEL}, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# Para o robô
ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

sleep 1

# Finaliza o rosbag
kill $BAG_PID
wait $BAG_PID 2>/dev/null

# Grava metadados da amostra num ficheiro de texto
META="${DIR_AMOSTRA}/amostra1/metadata.txt"
echo "velocidade_ms=${VEL}"        > "$META"
echo "velocidade_nome=${VEL_NOME}" >> "$META"
echo "distancia_alvo_m=${DISTANCIA}" >> "$META"
echo "tempo_movimento_s=${TEMPO}"  >> "$META"
echo "amostra=1"                   >> "$META"
echo "timestamp=$(date -Iseconds)" >> "$META"

echo ""
echo "========================================"
echo "Amostra única finalizada!"
echo "Dados salvos em: ${DIR_AMOSTRA}/amostra1"
echo "========================================"

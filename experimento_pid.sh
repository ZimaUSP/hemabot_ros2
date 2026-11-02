#!/bin/bash
# Repete o protocolo do experimento.sh original, mas usando o
# lateral_pid_controller (malha fechada) em vez de "ros2 topic pub"
# em malha aberta. Gera os bags no mesmo formato (/odom + /cmd_vel),
# então dá pra reaproveitar analise_odometria.py sem alterações.
#
# Suporta rodar em blocos, para reiniciar o Gazebo entre eles e evitar
# a degradação de desempenho (RTF caindo) observada em execuções longas:
#   ./experimento_pid.sh            # roda todas as NUM_AMOSTRAS de uma vez
#   ./experimento_pid.sh 1 10       # roda só as amostras 1 a 10
#   ./experimento_pid.sh 11 20      # roda só as amostras 11 a 20 (Gazebo
#                                    # deve estar recém-reiniciado)

VELOCIDADES=(-0.25)
DISTANCIA=5.0          # metros — mesma distância do experimento original
NUM_AMOSTRAS=50

INICIO=${1:-1}
FIM=${2:-$NUM_AMOSTRAS}

# Ganhos do PID (edite aqui ou aponte para outro yaml com params_file)
KP=0.8
KI=0.0
KD=0.15
KH=0.6
MAX_ANGULAR_Z=0.5

# Liga (1) ou desliga (0) o EKF (robot_localization) durante o
# experimento. Default 0 = EKF DESLIGADO.
#
# Confirmado no repositório (hemabot_ros2/src/d_hospital_gazebo2/launch/
# hospital.py): o launch de simulação já tem o argumento
# "use_robot_localization" (default True) que liga/desliga o nó
# ekf_node condicionalmente. O EKF remapeia sua saída
# (/odometry/filtered) diretamente para /odom.
#
# ATENÇÃO: em nenhum lugar do pipeline (d_hospital_gazebo2, d_hospital_gz,
# d_hospital_description) a odometria crua do diff_controller é
# remapeada para /odom — só o ekf_node publica nesse tópico. Ou seja,
# com EKF_ATIVO=0 e o launch atual, /odom provavelmente fica SEM
# publisher, e o bag gravado sai vazio nesse tópico. Antes de rodar
# com EKF_ATIVO=0, ajuste o launch (remapeie a saída do diff_controller
# para /odom quando use_robot_localization=False) ou troque o tópico
# gravado/analisado para /diff_controller/odom nesse caso.
EKF_ATIVO=0
# Padrão usado para identificar o nó do EKF em "ros2 node list"
# (o nó real se chama "ekf_filter_node", conforme ekf.yaml)
EKF_NODE_PATTERN="ekf_filter_node"
# Comando de referência para subir a simulação já no estado certo
# (rode manualmente antes do experimento; o script só confere o estado):
#   ros2 launch d_hospital_gazebo2 hospital.py use_robot_localization:=True   # EKF_ATIVO=1
#   ros2 launch d_hospital_gazebo2 hospital.py use_robot_localization:=False  # EKF_ATIVO=0 (ver alerta acima)

for VEL in "${VELOCIDADES[@]}"
do
    VEL_NOME=$(echo "$VEL" | tr '.' '_')
    DIR_AMOSTRAS="amostras_pid_${VEL_NOME}ms"

    VEL_ABS=$(echo "$VEL" | tr -d '-')
    TEMPO=$(echo "scale=4; $DISTANCIA / $VEL_ABS" | bc)
    # margem de segurança para o timeout externo (o nó já para sozinho
    # ao atingir goal_distance; isto é só uma rede de proteção). Ampliada
    # porque um caminho corrigido (curvo) é mais longo que a distância
    # em linha reta, e porque o Gazebo pode ficar mais lento que o
    # tempo real (RTF < 1) ao longo de muitas repetições.
    TEMPO_MARGEM=$(echo "scale=4; ($TEMPO * 1.5) + 15.0" | bc)

    echo "========================================"
    echo "Iniciando experimentos (PID) para velocidade: ${VEL} m/s"
    echo "Amostras ${INICIO} a ${FIM} de ${NUM_AMOSTRAS} totais"
    echo "Distância alvo: ${DISTANCIA} m | Tempo estimado: ${TEMPO} s | Timeout de segurança: ${TEMPO_MARGEM} s"
    echo "Ganhos: Kp=${KP} Ki=${KI} Kd=${KD} Kh=${KH}"
    if [ "$EKF_ATIVO" -eq 1 ]; then
        echo "EKF: esperado LIGADO (script só confere, não inicia sozinho)"
    else
        echo "EKF: esperado DESLIGADO (odometria crua)"
        echo "AVISO: confirme que /odom tem publisher nesse modo — no launch"
        echo "atual (hospital.py), só o ekf_node publica em /odom; sem ele,"
        echo "o tópico pode ficar vazio no bag. Veja o comentário de"
        echo "EKF_ATIVO no início do script."
    fi
    echo "========================================"

    mkdir -p "$DIR_AMOSTRAS"

    for i in $(seq $INICIO $FIM)
    do
        echo "  Iniciando amostra $i / ${NUM_AMOSTRAS} (vel=${VEL} m/s, t~${TEMPO}s)"

        # Rede de segurança: mata qualquer resto de processo de uma
        # iteração anterior que não tenha sido encerrado corretamente
        # (evita acúmulo de processos que degrada o RTF do Gazebo com
        # o tempo)
        pkill -f "lateral_pid_controller" 2>/dev/null
        pkill -f "ros2 bag record" 2>/dev/null
        sleep 1

        # Confere se o estado atual do EKF bate com EKF_ATIVO. O script
        # não liga/desliga o EKF sozinho (ver comentário na definição de
        # EKF_ATIVO), então aborta se houver divergência, em vez de
        # rodar o experimento inteiro no estado errado.
        if ros2 node list 2>/dev/null | grep -qi "$EKF_NODE_PATTERN"; then
            EKF_DETECTADO=1
        else
            EKF_DETECTADO=0
        fi
        if [ "$EKF_DETECTADO" -ne "$EKF_ATIVO" ]; then
            echo "ERRO: EKF_ATIVO=${EKF_ATIVO} mas o nó do EKF está $( [ "$EKF_DETECTADO" -eq 1 ] && echo 'RODANDO' || echo 'AUSENTE' ) no sistema."
            echo "Ajuste EKF_ATIVO no script para bater com o ambiente real, ou ligue/desligue o EKF manualmente antes de continuar."
            exit 1
        fi

        # Reset da simulação
        ros2 service call /reset_simulation std_srvs/srv/Empty
        sleep 2

        # Inicia gravação do bag em seu próprio grupo de processos, para
        # conseguirmos derrubar ele e todos os filhos de uma vez
        setsid ros2 bag record -o "${DIR_AMOSTRAS}/amostra${i}" /odom /cmd_vel /ground_truth/state &
        BAG_PID=$!
        sleep 2

        # Roda o controlador PID até atingir goal_distance (ou até o
        # timeout de segurança, o que vier primeiro). --signal=INT manda
        # SIGINT em vez do SIGTERM padrão do timeout: o nó Python trata
        # isso como KeyboardInterrupt e ainda executa o "finally" que
        # zera o /cmd_vel antes de sair — com SIGTERM isso não acontecia.
        T_INICIO=$(date +%s.%N)
        timeout --signal=INT "$TEMPO_MARGEM" ros2 run d_hospital_control lateral_pid_controller \
            --ros-args \
            -p linear_velocity:="${VEL}" \
            -p goal_distance:="${DISTANCIA}" \
            -p kp:="${KP}" -p ki:="${KI}" -p kd:="${KD}" -p kh:="${KH}" \
            -p max_angular_z:="${MAX_ANGULAR_Z}" \
            -p use_sim_time:=true
        T_FIM=$(date +%s.%N)
        TEMPO_REAL=$(echo "scale=4; $T_FIM - $T_INICIO" | bc)

        # Garante que o robô parou, mesmo se o timeout tiver interrompido
        ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \
            "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

        sleep 1

        # Derruba o bag record e todo o seu grupo de processos (o "-"
        # antes do PID manda o sinal para o grupo inteiro, não só o
        # processo principal)
        kill -INT -"$BAG_PID" 2>/dev/null
        sleep 1
        kill -9 -"$BAG_PID" 2>/dev/null
        wait $BAG_PID 2>/dev/null

        META="${DIR_AMOSTRAS}/amostra${i}/metadata.txt"
        echo "velocidade_ms=${VEL}"          > "$META"
        echo "velocidade_nome=${VEL_NOME}"  >> "$META"
        echo "distancia_alvo_m=${DISTANCIA}" >> "$META"
        echo "tempo_estimado_s=${TEMPO}"    >> "$META"
        echo "tempo_real_execucao_s=${TEMPO_REAL}" >> "$META"
        echo "timeout_seguranca_s=${TEMPO_MARGEM}" >> "$META"
        echo "controlador=lateral_pid_controller" >> "$META"
        echo "kp=${KP}" >> "$META"
        echo "ki=${KI}" >> "$META"
        echo "kd=${KD}" >> "$META"
        echo "kh=${KH}" >> "$META"
        echo "ekf_ativo=${EKF_ATIVO}" >> "$META"
        echo "ekf_detectado=${EKF_DETECTADO}" >> "$META"
        echo "amostra=${i}"                 >> "$META"
        echo "timestamp=$(date -Iseconds)"  >> "$META"

        echo "  Amostra $i finalizada (tempo real de execução: ${TEMPO_REAL}s)"
        sleep 3
    done

    RESUMO="${DIR_AMOSTRAS}/resumo_experimento.txt"
    echo "velocidade_ms=${VEL}"            > "$RESUMO"
    echo "distancia_alvo_m=${DISTANCIA}"  >> "$RESUMO"
    echo "tempo_por_amostra_s=${TEMPO}"   >> "$RESUMO"
    echo "num_amostras=${NUM_AMOSTRAS}"   >> "$RESUMO"
    echo "controlador=lateral_pid_controller (Kp=${KP} Ki=${KI} Kd=${KD} Kh=${KH})" >> "$RESUMO"
    echo "ekf_ativo=${EKF_ATIVO}" >> "$RESUMO"
    echo "timestamp=$(date -Iseconds)"    >> "$RESUMO"

    if [ "$FIM" -ge "$NUM_AMOSTRAS" ]; then
        ZIP_NAME="amostras_pid_${VEL_NOME}ms.zip"
        echo "Compactando amostras em ${ZIP_NAME}..."
        zip -r "$ZIP_NAME" "$DIR_AMOSTRAS"
        echo "Velocidade ${VEL} m/s (PID) concluída -> ${ZIP_NAME}"
    else
        echo "Bloco ${INICIO}-${FIM} concluído. Reinicie o Gazebo e rode o"
        echo "próximo bloco antes de compactar (ex.: ./experimento_pid.sh $((FIM+1)) <proximo_fim>)."
    fi
    echo ""
done

echo "========================================"
echo "Experimento com PID completo!"
echo "Compare com amostras_-0_25ms/ usando analise_odometria.py:"
echo "  - malha aberta:   amostras_-0_25ms/"
echo "  - malha fechada:  amostras_pid_-0_25ms/"
echo "========================================"

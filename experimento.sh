VELOCIDADES=(-0.25)
DISTANCIA=5.0  # metros — mesma distância para todas as velocidades

for VEL in "${VELOCIDADES[@]}"
do
    # Nome seguro para usar em arquivos (troca ponto por underscore)
    VEL_NOME=$(echo "$VEL" | tr '.' '_')
    DIR_AMOSTRAS="amostras_${VEL_NOME}ms"

    # Calcula o tempo necessário para percorrer a distância na velocidade atual
    # tempo = distancia / |velocidade|  (usa módulo pois VEL pode ser negativo,
    # indicando sentido oposto — o timeout não aceita valores negativos)
    VEL_ABS=$(echo "$VEL" | tr -d '-')
    TEMPO=$(echo "scale=4; $DISTANCIA / $VEL_ABS" | bc)

    echo "========================================"
    echo "Iniciando experimentos para velocidade: ${VEL} m/s"
    echo "Distância alvo: ${DISTANCIA} m | Tempo de movimento: ${TEMPO} s"
    echo "========================================"

    mkdir -p "$DIR_AMOSTRAS"

    for i in $(seq 1 50)
    do
        echo "  Iniciando amostra $i / 30 (vel=${VEL} m/s, t=${TEMPO}s)"

        # Reset da simulação
        ros2 service call /reset_simulation std_srvs/srv/Empty

        sleep 2

        # Inicia gravação do bag dentro da pasta da velocidade
        # Grava também /cmd_vel para registar a velocidade em cada amostra
        ros2 bag record -o "${DIR_AMOSTRAS}/amostra${i}" /odom /cmd_vel &

        BAG_PID=$!

        sleep 2

        # Movimento do robô pelo tempo calculado para manter distância constante
        # angular.z explicitamente zero para garantir trajetória reta
        timeout "$TEMPO" ros2 topic pub -r 30 /cmd_vel geometry_msgs/msg/Twist \
            "{linear: {x: ${VEL}, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

        # Para o robô
        ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \
            "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

        sleep 1

        # Finaliza o rosbag
        kill $BAG_PID
        wait $BAG_PID 2>/dev/null

        # Grava metadados da amostra num ficheiro de texto
        META="${DIR_AMOSTRAS}/amostra${i}/metadata.txt"
        echo "velocidade_ms=${VEL}"       > "$META"
        echo "velocidade_nome=${VEL_NOME}" >> "$META"
        echo "distancia_alvo_m=${DISTANCIA}" >> "$META"
        echo "tempo_movimento_s=${TEMPO}"  >> "$META"
        echo "amostra=${i}"               >> "$META"
        echo "timestamp=$(date -Iseconds)" >> "$META"

        sleep 3

        echo "  Amostra $i finalizada"
    done

    # Grava resumo da velocidade
    RESUMO="${DIR_AMOSTRAS}/resumo_experimento.txt"
    echo "velocidade_ms=${VEL}"            > "$RESUMO"
    echo "distancia_alvo_m=${DISTANCIA}"  >> "$RESUMO"
    echo "tempo_por_amostra_s=${TEMPO}"   >> "$RESUMO"
    echo "num_amostras=30"                >> "$RESUMO"
    echo "timestamp=$(date -Iseconds)"    >> "$RESUMO"

    # Compacta todas as amostras da velocidade em um .zip
    ZIP_NAME="amostras_${VEL_NOME}ms.zip"
    echo "Compactando amostras em ${ZIP_NAME}..."
    zip -r "$ZIP_NAME" "$DIR_AMOSTRAS"

    echo "Velocidade ${VEL} m/s concluída → ${ZIP_NAME}"
    echo ""
done

echo "========================================"
echo "Experimento completo!"
echo "Arquivos gerados:"
for VEL in "${VELOCIDADES[@]}"
do
    VEL_NOME=$(echo "$VEL" | tr '.' '_')
    echo "  - amostras_${VEL_NOME}ms.zip"
done
echo "========================================"

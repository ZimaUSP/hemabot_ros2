#!/bin/bash
###############################################################################
# coleta_experimento.sh
#
# Automação da coleta de dados experimentais para testes de trajetória de um
# robô móvel diferencial hospitalar em simulação (ROS 2 Humble + Gazebo
# Fortress). Documenta cada execução de forma reprodutível e rastreável,
# gerando: relatório individual (.md), rosbag, CSVs, logs e classificação
# final da execução, além de um relatório consolidado com todas as amostras.
#
# Compatível com: Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress (gz sim)
#
# Uso básico:
#   ./coleta_experimento.sh --velocidade -0.25 --distancia 5.0 --repeticoes 20
#
# Ajuda completa:
#   ./coleta_experimento.sh --help
###############################################################################

# Não usamos "set -e": o script precisa continuar e classificar a execução
# mesmo quando um comando pontual falha (ex.: um tópico opcional que não
# existe). Falhas relevantes são tratadas explicitamente em cada função.
set -uo pipefail

###############################################################################
# 1. CONFIGURAÇÃO PADRÃO (sobrescrevível via argumentos de linha de comando)
###############################################################################

VELOCIDADE_LINEAR=-0.25        # m/s (negativo = ré, positivo = frente)
VELOCIDADE_ANGULAR=0.0         # rad/s
DISTANCIA_PLANEJADA=5.0        # m (usada apenas para estimar o tempo de movimento)
DURACAO_MAX=""                 # s — se vazio, é calculada a partir da distância
TAXA_PUBLICACAO_CMDVEL=30      # Hz, taxa do "ros2 topic pub -r"
NUM_REPETICOES=50
INTERVALO_ENTRE_EXEC=3         # s de espera entre uma amostra e outra
NOME_EXPERIMENTO="experimento"
DIR_SAIDA_BASE="./resultados_experimentos"
RESET_ENTRE_EXECUCOES=1        # 1 = reseta simulação/pose entre execuções
FORCAR_WORLD=""                # caminho para .world (senão, detecção automática)
FORCAR_URDF=""                 # caminho para urdf/xacro (senão, detecção automática)
TOPICO_ODOM="/odom"
TOPICO_IMU="/imu"                       # sobrescrito automaticamente se não existir (ver detectar_topico_imu)
TOPICO_SCAN="/scan"
TOPICO_JOINT_STATES="/joint_states"
TOPICO_CMD_VEL="/cmd_vel"
# As arrays TOPICOS_BAG / TOPICOS_CSV são montadas dentro de main(), depois do
# parsing de argumentos e da detecção automática do tópico de IMU — assim
# refletem eventuais overrides via CLI e o nome real detectado em runtime.
JANELA_MEDICAO_HZ=4             # s de amostragem para medir frequência dos tópicos
TIMEOUT_ESTABILIZACAO=15        # s máx. de espera por estabilização pós-reset

# Critérios (configuráveis) usados na classificação final da execução
ODOM_MSGS_MINIMAS=5             # amostras mínimas de /odom para considerar válida
HZ_MINIMA_ACEITAVEL=1.0         # Hz mínima aceitável para tópicos essenciais

###############################################################################
# 2. FUNÇÕES DE APOIO — LOG, CORES E VERIFICAÇÕES BÁSICAS
###############################################################################

COR_INFO='\033[0;36m'; COR_OK='\033[0;32m'; COR_AVISO='\033[0;33m'
COR_ERRO='\033[0;31m'; COR_RESET='\033[0m'

log_info()  { echo -e "${COR_INFO}[INFO]${COR_RESET}  $*"; }
log_ok()    { echo -e "${COR_OK}[ OK ]${COR_RESET}  $*"; }
log_aviso() { echo -e "${COR_AVISO}[AVISO]${COR_RESET} $*"; }
log_erro()  { echo -e "${COR_ERRO}[ERRO]${COR_RESET}  $*" >&2; }

# Verifica se um comando existe antes de usá-lo; aborta se for essencial.
verificar_comando() {
    local cmd="$1"
    local essencial="${2:-1}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        if [ "$essencial" -eq 1 ]; then
            log_erro "Comando obrigatório '$cmd' não encontrado no PATH. Abortando."
            exit 1
        else
            log_aviso "Comando opcional '$cmd' não encontrado; funcionalidades associadas serão puladas."
            return 1
        fi
    fi
    return 0
}

# Executa um comando com timeout, sem derrubar o script caso ele falhe/expire.
executar_seguro() {
    local descricao="$1"; shift
    if ! "$@" >/dev/null 2>&1; then
        log_aviso "Falha ou timeout em: ${descricao}"
        return 1
    fi
    return 0
}

###############################################################################
# 3. VERIFICAÇÃO DO AMBIENTE (ROS 2 + GAZEBO)
###############################################################################

verificar_ambiente_ros() {
    log_info "Verificando ambiente ROS 2..."
    verificar_comando ros2 1

    if [ -z "${ROS_DISTRO:-}" ]; then
        log_erro "Variável ROS_DISTRO não definida. Faça 'source /opt/ros/humble/setup.bash' antes de rodar este script."
        exit 1
    fi
    if [ "$ROS_DISTRO" != "humble" ]; then
        log_aviso "ROS_DISTRO='${ROS_DISTRO}' (script foi desenhado para 'humble'). Continuando mesmo assim."
    fi

    # ros2 topic list é uma forma barata de confirmar que o daemon/DDS responde
    if ! timeout 8 ros2 topic list >/dev/null 2>&1; then
        log_erro "Não foi possível listar tópicos ROS 2. O ambiente ROS 2 parece não estar ativo."
        exit 1
    fi
    log_ok "Ambiente ROS 2 (${ROS_DISTRO}) respondendo normalmente."
}

verificar_gazebo() {
    log_info "Verificando se o Gazebo (Fortress) está em execução..."

    local gz_rodando=0
    if pgrep -f "gz sim" >/dev/null 2>&1 || pgrep -f "ign gazebo" >/dev/null 2>&1; then
        gz_rodando=1
    fi
    # /clock costuma existir quando use_sim_time está ativo e o Gazebo publica o relógio
    if timeout 5 ros2 topic list 2>/dev/null | grep -q "^/clock$"; then
        gz_rodando=1
    fi

    if [ "$gz_rodando" -eq 0 ]; then
        log_erro "Gazebo não parece estar em execução (nenhum processo 'gz sim'/'ign gazebo' e sem /clock). Abortando."
        exit 1
    fi
    log_ok "Gazebo em execução."
}

detectar_versao_gazebo() {
    local versao="desconhecida"
    if command -v gz >/dev/null 2>&1; then
        versao=$(gz sim --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
    fi
    [ -z "$versao" ] && versao="desconhecida"
    echo "$versao"
}

verificar_topicos_necessarios() {
    log_info "Verificando disponibilidade dos tópicos/nós principais..."
    local topicos_ativos
    topicos_ativos=$(timeout 8 ros2 topic list 2>/dev/null)

    local essenciais=("$TOPICO_CMD_VEL" "$TOPICO_ODOM")
    local opcionais=("$TOPICO_IMU" "$TOPICO_SCAN" "$TOPICO_JOINT_STATES")
    local faltando_essencial=0

    for t in "${essenciais[@]}"; do
        if echo "$topicos_ativos" | grep -q "^${t}$"; then
            log_ok "Tópico essencial disponível: ${t}"
        else
            log_erro "Tópico essencial ausente: ${t}"
            faltando_essencial=1
        fi
    done
    for t in "${opcionais[@]}"; do
        if echo "$topicos_ativos" | grep -q "^${t}$"; then
            log_ok "Tópico disponível: ${t}"
        else
            log_aviso "Tópico opcional ausente: ${t} (será ignorado na gravação/CSV)"
        fi
    done

    if [ "$faltando_essencial" -eq 1 ]; then
        log_erro "Tópicos essenciais ausentes. Verifique se a simulação e os controladores foram lançados corretamente."
        exit 1
    fi
}

detectar_ekf() {
    local presente="ausente"
    local nos
    nos=$(timeout 8 ros2 node list 2>/dev/null)
    local topicos
    topicos=$(timeout 8 ros2 topic list 2>/dev/null)

    if echo "$nos" | grep -q "ekf_filter_node"; then
        presente="presente (nó ekf_filter_node)"
    elif echo "$topicos" | grep -q "/odometry/filtered"; then
        presente="presente (tópico /odometry/filtered)"
    fi
    echo "$presente"
}

# O nome do tópico de IMU varia entre setups (ex.: '/imu' vs
# '/imu_broadcaster/imu', comum quando o driver é o imu_sensor_broadcaster
# do ros2_control). Tenta o nome configurado e, se ausente, alguns
# alternativos conhecidos antes de desistir.
detectar_topico_imu() {
    local topicos_ativos
    topicos_ativos=$(timeout 8 ros2 topic list 2>/dev/null)

    local candidatos=("$TOPICO_IMU" "/imu_broadcaster/imu" "/imu/data" "/imu/data_raw")
    for c in "${candidatos[@]}"; do
        if echo "$topicos_ativos" | grep -q "^${c}$"; then
            echo "$c"
            return 0
        fi
    done
    echo "$TOPICO_IMU"   # mantém o padrão mesmo se não encontrado (será reportado como ausente)
}



localizar_world() {
    if [ -n "$FORCAR_WORLD" ]; then
        echo "$FORCAR_WORLD"
        return 0
    fi

    # 1) Tenta descobrir pelo argumento de linha de comando do processo do Gazebo
    local cmdline
    cmdline=$(pgrep -af "gz sim" 2>/dev/null | head -n1)
    local candidato
    candidato=$(echo "$cmdline" | grep -oE '[^ ]+\.sdf|[^ ]+\.world' | head -n1)
    if [ -n "$candidato" ] && [ -f "$candidato" ]; then
        echo "$candidato"
        return 0
    fi

    # 2) Fallback: procura arquivos .world no workspace atual (src/ e install/)
    candidato=$(find . -path "*/log/*" -prune -o -path "*/build/*" -prune -o \
        -iname "*.world" -print 2>/dev/null | head -n1)
    if [ -n "$candidato" ]; then
        echo "$candidato"
        return 0
    fi

    echo ""
}

extrair_parametros_world() {
    local world_file="$1"
    local out_json="$2"

    local engine="desconhecido" max_step="N/A" rtf_config="N/A" rtu_rate="N/A"

    if [ -n "$world_file" ] && [ -f "$world_file" ]; then
        # Aceita tanto aspas simples quanto duplas (worlds do repo usam as duas formas)
        engine=$(grep -oE '<physics[^>]*type=["'"'"'][a-zA-Z]+["'"'"']' "$world_file" \
            | head -n1 | sed -E 's/.*type=["'"'"']([a-zA-Z]+)["'"'"'].*/\1/')
        max_step=$(grep -oE '<max_step_size>[^<]+' "$world_file" | head -n1 | sed 's/<max_step_size>//')
        rtf_config=$(grep -oE '<real_time_factor>[^<]+' "$world_file" | head -n1 | sed 's/<real_time_factor>//')
        rtu_rate=$(grep -oE '<real_time_update_rate>[^<]+' "$world_file" | head -n1 | sed 's/<real_time_update_rate>//')

        # No Gazebo Fortress (gz-sim), o atributo type="ignored" é a convenção
        # normal: o motor de física real não vem dessa tag, e sim do plugin
        # gz-physics-*-plugin efetivamente carregado (ou do padrão do
        # gz-sim-physics-system, que é DART, quando nenhum plugin de engine
        # específico é indicado). Diferente de mundos legados do Gazebo
        # clássico, onde type="ode" de fato seleciona o motor.
        if [ -z "$engine" ] || [ "$engine" = "ignored" ]; then
            local plugin_engine
            plugin_engine=$(grep -oE 'gz-physics-[a-zA-Z]+-plugin|libgz-physics-[a-zA-Z]+' "$world_file" | head -n1)
            if [ -n "$plugin_engine" ]; then
                engine="${plugin_engine} (extraído do nome do plugin)"
            else
                engine="DART (padrão do gz-sim-physics-system; tag <physics type=\"ignored\"> não indica o motor real neste .world — nenhum plugin de engine explícito foi encontrado)"
            fi
        fi

        [ -z "$max_step" ] && max_step="N/A"
        [ -z "$rtf_config" ] && rtf_config="N/A"
        [ -z "$rtu_rate" ] && rtu_rate="N/A"
    else
        log_aviso "Arquivo .world não localizado automaticamente; parâmetros físicos ficarão como N/A."
    fi

    cat > "$out_json" <<EOF
{
  "world_file": "${world_file:-N/A}",
  "physics_engine": "${engine}",
  "max_step_size": "${max_step}",
  "real_time_update_rate": "${rtu_rate}",
  "real_time_factor_configurado": "${rtf_config}"
}
EOF
}

# Melhor esforço para capturar o real_time_factor MEDIDO (não o configurado),
# via tópico de estatísticas do mundo (Gazebo Fortress). Requer o comando 'gz'.
medir_real_time_factor() {
    local mundo_nome="$1"
    if ! command -v gz >/dev/null 2>&1; then
        echo "N/A"
        return
    fi
    local topico="/world/${mundo_nome}/stats"
    local saida
    saida=$(timeout 6 gz topic -e -t "$topico" -n 1 2>/dev/null)
    local rtf
    rtf=$(echo "$saida" | grep -oE 'real_time_factor: [0-9.]+' | head -n1 | awk '{print $2}')
    [ -z "$rtf" ] && rtf="N/A"
    echo "$rtf"
}

###############################################################################
# 5. LOCALIZAÇÃO E EXTRAÇÃO DE PARÂMETROS — URDF/XACRO DO ROBÔ
###############################################################################

localizar_urdf() {
    if [ -n "$FORCAR_URDF" ]; then
        echo "$FORCAR_URDF"
        return 0
    fi

    # Prioriza .urdf "puro" (já expandido, com valores literais de massa/
    # inércia) sobre .xacro: arquivos .xacro costumam definir massa via
    # parâmetros de macro (ex.: ${mass}) sem um valor literal no próprio
    # arquivo, o que faz a extração por grep falhar silenciosamente.
    local candidato
    candidato=$(find . -path "*/log/*" -prune -o -path "*/build/*" -prune -o \
        -iname "*.urdf" ! -iname "*.xacro" -print 2>/dev/null \
        | grep -viE "/install/" | head -n1)

    if [ -z "$candidato" ]; then
        candidato=$(find . -path "*/log/*" -prune -o -path "*/build/*" -prune -o \
            \( -iname "*.urdf.xacro" -o -iname "*.xacro" \) -print 2>/dev/null \
            | grep -viE "/install/" | head -n1)
    fi
    echo "$candidato"
}

# Extrai parâmetros cinemáticos/físicos do robô, priorizando o YAML do
# controlador (fonte de verdade em runtime) e usando o URDF como fallback.
extrair_parametros_robot() {
    local urdf_file="$1"
    local out_json="$2"

    local raio_roda="N/A" distancia_rodas="N/A" massa_total="N/A"

    # 1) Fonte preferencial: controllers.yaml (usado de fato pelo ros2_control)
    local controllers_yaml todos_controllers_yaml n_controllers_yaml aviso_controllers=""
    todos_controllers_yaml=$(find . -path "*/log/*" -prune -o -path "*/build/*" -prune -o \
        -iname "controllers.yaml" -print 2>/dev/null | grep -viE "/install/")
    n_controllers_yaml=$(echo "$todos_controllers_yaml" | grep -c . || true)
    controllers_yaml=$(echo "$todos_controllers_yaml" | head -n1)

    if [ "$n_controllers_yaml" -gt 1 ]; then
        aviso_controllers="ATENÇÃO: ${n_controllers_yaml} arquivos controllers.yaml encontrados no workspace com possíveis valores DIFERENTES ($(echo "$todos_controllers_yaml" | tr '\n' ';')). Usado: ${controllers_yaml}. Confirme manualmente qual é o efetivamente carregado pelo seu launch antes de citar wheel_radius/wheel_separation em relatório científico."
        log_aviso "$aviso_controllers"
    fi

    if [ -n "$controllers_yaml" ] && [ -f "$controllers_yaml" ]; then
        raio_roda=$(grep -oE 'wheel_radius:\s*[0-9.]+' "$controllers_yaml" | head -n1 | awk '{print $2}')
        distancia_rodas=$(grep -oE 'wheel_separation:\s*[0-9.]+' "$controllers_yaml" | head -n1 | awk '{print $2}')
    fi

    # 2) Fallback / complemento: URDF bruto (soma de todas as tags <mass value="...">)
    if [ -n "$urdf_file" ] && [ -f "$urdf_file" ]; then
        [ -z "$raio_roda" ] && raio_roda=$(grep -oE 'wheel_separation>[0-9.]+' "$urdf_file" | head -n1 | grep -oE '[0-9.]+')

        local arquivo_para_massa="$urdf_file"
        # Se o arquivo é um .xacro, ele pode usar macros (ex.: ${mass}) sem
        # valor literal — tenta expandi-lo com o comando 'xacro' antes de
        # desistir, para conseguir valores reais em vez de macros vazias.
        if echo "$urdf_file" | grep -qi '\.xacro$' && command -v xacro >/dev/null 2>&1; then
            local expandido
            expandido=$(mktemp --suffix=.urdf)
            if xacro "$urdf_file" > "$expandido" 2>/dev/null && [ -s "$expandido" ]; then
                arquivo_para_massa="$expandido"
            fi
        fi

        massa_total=$(grep -oE '<mass value="[0-9.]+"' "$arquivo_para_massa" \
            | grep -oE '[0-9.]+' \
            | awk '{s+=$1; n++} END {if (n>0) printf "%.4f", s; }')
        [ -n "${expandido:-}" ] && rm -f "$expandido"
    fi

    [ -z "$massa_total" ] && massa_total="N/A"

    [ -z "$raio_roda" ] && raio_roda="N/A"
    [ -z "$distancia_rodas" ] && distancia_rodas="N/A"

    cat > "$out_json" <<EOF
{
  "urdf_file": "${urdf_file:-N/A}",
  "controllers_yaml": "${controllers_yaml:-N/A}",
  "aviso_ambiguidade_controllers_yaml": "${aviso_controllers}",
  "wheel_radius_m": "${raio_roda}",
  "wheel_separation_m": "${distancia_rodas}",
  "massa_total_kg_aprox": "${massa_total}"
}
EOF
}

###############################################################################
# 6. MEDIÇÃO DE FREQUÊNCIAS E POSE
###############################################################################

# Mede a frequência média de publicação de um tópico durante JANELA_MEDICAO_HZ
# segundos, usando 'ros2 topic hz'. Retorna "N/A" se o tópico não publicar.
medir_frequencia_topico() {
    local topico="$1"
    local saida
    saida=$(timeout "$((JANELA_MEDICAO_HZ + 2))" ros2 topic hz "$topico" --window 50 2>/dev/null)
    local hz
    hz=$(echo "$saida" | grep -oE 'average rate: [0-9.]+' | tail -n1 | awk '{print $3}')
    [ -z "$hz" ] && hz="N/A"
    echo "$hz"
}

# Lê um campo de uma mensagem via 'ros2 topic echo --once --field', com timeout.
ler_campo_topico() {
    local topico="$1"
    local campo="$2"
    local timeout_s="${3:-5}"
    local valor
    # 'ros2 topic echo --once --field' ainda termina a mensagem com o
    # separador de documento YAML "---" numa linha própria; removê-lo é
    # necessário antes de colapsar quebras de linha, senão ele gruda no
    # valor numérico (ex.: "-9.99---") e corrompe o dado.
    valor=$(timeout "$timeout_s" ros2 topic echo "$topico" --once --field "$campo" 2>/dev/null \
        | grep -v '^---$' | head -n1 | xargs)
    [ -z "$valor" ] && valor="N/A"
    echo "$valor"
}

obter_pose_inicial() {
    local out_json="$1"

    local x y z qx qy qz qw yaw vx wz

    x=$(ler_campo_topico /odom pose.pose.position.x)
    y=$(ler_campo_topico /odom pose.pose.position.y)
    z=$(ler_campo_topico /odom pose.pose.position.z)
    qx=$(ler_campo_topico /odom pose.pose.orientation.x)
    qy=$(ler_campo_topico /odom pose.pose.orientation.y)
    qz=$(ler_campo_topico /odom pose.pose.orientation.z)
    qw=$(ler_campo_topico /odom pose.pose.orientation.w)
    vx=$(ler_campo_topico /odom twist.twist.linear.x)
    wz=$(ler_campo_topico /odom twist.twist.angular.z)

    yaw="N/A"
    if command -v python3 >/dev/null 2>&1 && [ "$qz" != "N/A" ] && [ "$qw" != "N/A" ]; then
        yaw=$(python3 -c "
import math
try:
    qx, qy, qz, qw = ${qx:-0}, ${qy:-0}, ${qz:-0}, ${qw:-1}
    siny_cosp = 2.0 * (qw*qz + qx*qy)
    cosy_cosp = 1.0 - 2.0 * (qy*qy + qz*qz)
    print(round(math.atan2(siny_cosp, cosy_cosp), 6))
except Exception:
    print('N/A')
" 2>/dev/null)
        [ -z "$yaw" ] && yaw="N/A"
    fi

    cat > "$out_json" <<EOF
{
  "posicao_inicial": {"x": "${x}", "y": "${y}", "z": "${z}"},
  "orientacao_inicial_quaternion": {"x": "${qx}", "y": "${qy}", "z": "${qz}", "w": "${qw}"},
  "orientacao_inicial_yaw_rad": "${yaw}",
  "velocidade_linear_inicial_x": "${vx}",
  "velocidade_angular_inicial_z": "${wz}"
}
EOF
}

###############################################################################
# 7. RESET DA SIMULAÇÃO ENTRE EXPERIMENTOS
###############################################################################

parar_robo() {
    timeout 3 ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist \
        "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" >/dev/null 2>&1
}

resetar_simulacao() {
    log_info "Resetando simulação para o próximo experimento..."

    parar_robo

    # Mata resíduos de execuções anteriores que porventura não tenham
    # encerrado corretamente (evita degradação progressiva do RTF)
    pkill -f "ros2 bag record" 2>/dev/null
    pkill -f "ros2 topic echo .* --csv" 2>/dev/null
    pkill -f "ros2 topic pub -r ${TAXA_PUBLICACAO_CMDVEL} /cmd_vel" 2>/dev/null
    sleep 1

    # Reset da física/pose do mundo (serviço padrão do ros_gz_bridge/ros_ign)
    if ! executar_seguro "reset_simulation" timeout 5 ros2 service call /reset_simulation std_srvs/srv/Empty; then
        executar_seguro "reset_world (fallback)" timeout 5 ros2 service call /reset_world std_srvs/srv/Empty
    fi
    sleep 2

    # Reinício dos controladores via controller_manager, se disponível
    # (ignorado silenciosamente se o serviço não existir neste setup)
    if timeout 5 ros2 service list 2>/dev/null | grep -q "controller_manager/list_controllers"; then
        for ctrl in diff_controller joint_broadcaster imu_broadcaster; do
            executar_seguro "reinicio de ${ctrl}" timeout 5 ros2 service call \
                /controller_manager/switch_controller controller_manager_msgs/srv/SwitchController \
                "{deactivate_controllers: [], activate_controllers: [${ctrl}], strictness: 1}"
        done
    fi

    espera_estabilizacao_topicos
}

# Aguarda até que /odom volte a publicar após o reset (com timeout de segurança)
espera_estabilizacao_topicos() {
    log_info "Aguardando estabilização dos tópicos pós-reset (timeout ${TIMEOUT_ESTABILIZACAO}s)..."
    local inicio
    inicio=$(date +%s)
    while true; do
        if timeout 3 ros2 topic echo /odom --once >/dev/null 2>&1; then
            log_ok "Tópicos estabilizados."
            return 0
        fi
        local agora
        agora=$(date +%s)
        if [ "$((agora - inicio))" -ge "$TIMEOUT_ESTABILIZACAO" ]; then
            log_aviso "Timeout de estabilização atingido; prosseguindo mesmo assim."
            return 1
        fi
        sleep 1
    done
}

###############################################################################
# 8. GRAVAÇÃO DE ROSBAG E EXPORTAÇÃO PARA CSV
###############################################################################

# Inicia a gravação do rosbag em segundo plano, em seu próprio grupo de
# processos (setsid), para que possamos derrubar bag + filhos de uma vez.
iniciar_gravacao_bag() {
    local dir_saida="$1"
    local topicos_existentes=()
    local topicos_ativos
    topicos_ativos=$(timeout 8 ros2 topic list 2>/dev/null)

    for t in "${TOPICOS_BAG[@]}"; do
        if echo "$topicos_ativos" | grep -q "^${t}$"; then
            topicos_existentes+=("$t")
        fi
    done

    if [ "${#topicos_existentes[@]}" -eq 0 ]; then
        log_aviso "Nenhum tópico disponível para gravar no rosbag."
        echo ""
        return
    fi

    setsid ros2 bag record -o "${dir_saida}/rosbag" "${topicos_existentes[@]}" \
        > "${dir_saida}/logs_rosbag.log" 2>&1 &
    echo "$!"
}

parar_gravacao_bag() {
    local pid="$1"
    [ -z "$pid" ] && return
    kill -INT -"$pid" 2>/dev/null
    sleep 1
    kill -9 -"$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
}

# Inicia exportação em CSV "ao vivo" via 'ros2 topic echo --csv' para cada
# tópico disponível, gravando os PIDs para encerramento posterior.
iniciar_exportacao_csv() {
    local dir_saida="$1"
    local -n pids_ref="$2"   # nameref: array de PIDs preenchido por esta função
    pids_ref=()

    local topicos_ativos
    topicos_ativos=$(timeout 8 ros2 topic list 2>/dev/null)

    mkdir -p "${dir_saida}/csv"
    for t in "${TOPICOS_CSV[@]}"; do
        if echo "$topicos_ativos" | grep -q "^${t}$"; then
            local nome_arquivo
            nome_arquivo=$(echo "$t" | tr -d '/' )
            setsid ros2 topic echo "$t" --csv \
                > "${dir_saida}/csv/${nome_arquivo}.csv" 2>/dev/null &
            pids_ref+=("$!")
        fi
    done

    # CSV dedicado, apenas com pose.pose.position (x,y,z), usado no cálculo de
    # distância/velocidade média. Evita a ambiguidade de extrair posição do
    # CSV completo de /odom (que traz timestamp do header e covariâncias
    # antes/depois da posição, tornando frágil qualquer heurística de coluna).
    if echo "$topicos_ativos" | grep -q "^/odom$"; then
        setsid ros2 topic echo /odom --csv --field pose.pose.position \
            > "${dir_saida}/csv/odom_posicao.csv" 2>/dev/null &
        pids_ref+=("$!")
    fi
}

parar_exportacao_csv() {
    local -n pids_ref="$1"
    for pid in "${pids_ref[@]:-}"; do
        [ -z "$pid" ] && continue
        kill -INT -"$pid" 2>/dev/null
        sleep 0.3
        kill -9 -"$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
    done
}

###############################################################################
# 9. COMANDO DE VELOCIDADE E ESTATÍSTICAS PÓS-EXECUÇÃO
###############################################################################

publicar_cmd_vel() {
    local vel_lin="$1" vel_ang="$2" duracao="$3"
    timeout "$duracao" ros2 topic pub -r "$TAXA_PUBLICACAO_CMDVEL" /cmd_vel geometry_msgs/msg/Twist \
        "{linear: {x: ${vel_lin}, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: ${vel_ang}}}" \
        >/dev/null 2>&1
    # timeout retorna 124 quando expira por tempo — isso é o comportamento
    # ESPERADO aqui (publicação contínua até o fim da duração planejada)
    local status=$?
    if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then
        log_aviso "'ros2 topic pub' encerrou com código inesperado: ${status}"
    fi
}

# Calcula distância percorrida (soma das distâncias euclidianas entre pontos
# consecutivos de /odom) e velocidade média a partir do CSV exportado.
calcular_estatisticas_odom() {
    local csv_odom="$1"
    local out_json="$2"
    local duracao_real="$3"

    local n_msgs=0 distancia="N/A" vel_media="N/A"

    if [ -f "$csv_odom" ] && [ -s "$csv_odom" ]; then
        n_msgs=$(wc -l < "$csv_odom" | tr -d ' ')

        if command -v python3 >/dev/null 2>&1 && [ "$n_msgs" -gt 1 ]; then
            read -r distancia vel_media <<EOF
$(python3 - "$csv_odom" "$duracao_real" <<'PYEOF'
import csv, sys, math

csv_path, duracao = sys.argv[1], float(sys.argv[2]) if sys.argv[2] not in ("", "N/A") else 0.0
pontos = []
try:
    # Este CSV é gerado com 'ros2 topic echo /odom --csv --field pose.pose.position',
    # portanto cada linha é exatamente "x,y,z" — sem timestamp, covariância ou
    # qualquer outro campo, eliminando ambiguidade de coluna.
    with open(csv_path, newline='') as f:
        leitor = csv.reader(f)
        for linha in leitor:
            if len(linha) >= 2:
                try:
                    pontos.append([float(linha[0]), float(linha[1])])
                except ValueError:
                    continue
except Exception:
    print("N/A N/A")
    sys.exit(0)

if len(pontos) < 2:
    print("N/A N/A")
    sys.exit(0)

dist_total = 0.0
for i in range(1, len(pontos)):
    x0, y0 = pontos[i-1][0], pontos[i-1][1]
    x1, y1 = pontos[i][0], pontos[i][1]
    dist_total += math.hypot(x1 - x0, y1 - y0)

vel_media = (dist_total / duracao) if duracao > 0 else 0.0
print(f"{dist_total:.4f} {vel_media:.4f}")
PYEOF
)
EOF
        fi
    fi

    cat > "$out_json" <<EOF
{
  "mensagens_odom_recebidas": ${n_msgs},
  "distancia_percorrida_m_estimada": "${distancia}",
  "velocidade_media_m_s_estimada": "${vel_media}"
}
EOF
}

###############################################################################
# 10. CLASSIFICAÇÃO DA EXECUÇÃO
###############################################################################

# Critérios (nas variáveis de configuração no topo do arquivo):
#  - ODOM_MSGS_MINIMAS: nº mínimo de mensagens de /odom para não ser "não_convergente"
#  - HZ_MINIMA_ACEITAVEL: frequência mínima aceitável dos tópicos essenciais
# Classificações possíveis: valida | concluida | instavel | nao_convergente
classificar_execucao() {
    local n_msgs_odom="$1"
    local hz_odom="$2"
    local execucao_incompleta="$3"   # "1" se a publicação de /cmd_vel parou bem antes do planejado
    local hz_cmd_vel="$4"

    if [ "$n_msgs_odom" -lt "$ODOM_MSGS_MINIMAS" ]; then
        echo "nao_convergente"
        return
    fi

    if [ "$hz_odom" != "N/A" ] && awk "BEGIN{exit !(${hz_odom} < ${HZ_MINIMA_ACEITAVEL})}"; then
        echo "instavel"
        return
    fi

    if [ "$execucao_incompleta" -eq 1 ]; then
        echo "instavel"
        return
    fi

    if [ "$hz_cmd_vel" != "N/A" ] && awk "BEGIN{exit !(${hz_cmd_vel} < 1.0)}"; then
        echo "instavel"
        return
    fi

    echo "concluida"
}

###############################################################################
# 11. RELATÓRIOS (INDIVIDUAL E CONSOLIDADO)
###############################################################################

gerar_relatorio_individual() {
    local dir="$1" idx="$2" classificacao="$3"
    local relatorio="${dir}/relatorio.md"

    cat > "$relatorio" <<EOF
# Relatório de Execução — Amostra ${idx}

**Experimento:** ${NOME_EXPERIMENTO}
**Data/hora de início:** ${DATA_HORA_INICIO}
**Classificação final:** \`${classificacao}\`

## Ambiente

| Parâmetro | Valor |
|---|---|
| Distribuição ROS 2 | ${ROS_DISTRO:-N/A} |
| Versão do Gazebo | ${VERSAO_GAZEBO} |
| Motor de física | $(python3 -c "import json;print(json.load(open('${dir}/../mundo.json'))['physics_engine'])" 2>/dev/null || echo N/A) |
| Presença de EKF | ${EKF_STATUS} |

## Parâmetros da simulação (mundo)

\`\`\`json
$(cat "${dir}/../mundo.json" 2>/dev/null || echo '{}')
\`\`\`

## Parâmetros do robô

\`\`\`json
$(cat "${dir}/../robo.json" 2>/dev/null || echo '{}')
\`\`\`

## Pose e velocidade iniciais

\`\`\`json
$(cat "${dir}/pose_inicial.json" 2>/dev/null || echo '{}')
\`\`\`

## Comando do experimento

| Parâmetro | Valor |
|---|---|
| Velocidade linear comandada (m/s) | ${VELOCIDADE_LINEAR} |
| Velocidade angular comandada (rad/s) | ${VELOCIDADE_ANGULAR} |
| Sentido do deslocamento | ${SENTIDO_DESLOCAMENTO} |
| Distância planejada (m) | ${DISTANCIA_PLANEJADA} |
| Duração máxima configurada (s) | ${DURACAO_MAX} |
| Tempo efetivamente gasto (s) | ${TEMPO_REAL_EXECUCAO} |

## Frequências medidas (Hz)

| Tópico | Frequência |
|---|---|
| ${TOPICO_ODOM} | ${HZ_ODOM} |
| ${TOPICO_IMU} | ${HZ_IMU} |
| ${TOPICO_SCAN} | ${HZ_SCAN} |
| ${TOPICO_JOINT_STATES} | ${HZ_JOINT_STATES} |
| ${TOPICO_CMD_VEL} | ${HZ_CMDVEL} |
| Controlador (configurado, controllers.yaml) | ${FREQ_CONTROLADOR_CONFIG} |

## Estatísticas pós-execução

\`\`\`json
$(cat "${dir}/estatisticas.json" 2>/dev/null || echo '{}')
\`\`\`

## Arquivos desta amostra

- Rosbag: \`rosbag/\`
- CSVs: \`csv/\`
- Logs: \`logs_rosbag.log\`
- Resultado: \`resultado.txt\`
EOF
}

inicializar_relatorio_consolidado() {
    CONSOLIDADO="${DIR_SAIDA}/relatorio_consolidado.md"
    cat > "$CONSOLIDADO" <<EOF
# Relatório Consolidado — ${NOME_EXPERIMENTO}

**Início:** ${DATA_HORA_INICIO}
**ROS 2:** ${ROS_DISTRO:-N/A} | **Gazebo:** ${VERSAO_GAZEBO} | **EKF:** ${EKF_STATUS}

## Parâmetros fixos do experimento

- Velocidade linear comandada: ${VELOCIDADE_LINEAR} m/s
- Velocidade angular comandada: ${VELOCIDADE_ANGULAR} rad/s
- Distância planejada: ${DISTANCIA_PLANEJADA} m
- Repetições planejadas: ${NUM_REPETICOES}

## Amostras

| # | Classificação | Tempo real (s) | Dist. estimada (m) | Vel. média (m/s) | Hz /odom | Hz /cmd_vel |
|---|---|---|---|---|---|---|
EOF
}

adicionar_linha_consolidado() {
    local idx="$1" classificacao="$2" tempo_real="$3" dist="$4" vel_media="$5" hz_odom="$6" hz_cmdvel="$7"
    echo "| ${idx} | ${classificacao} | ${tempo_real} | ${dist} | ${vel_media} | ${hz_odom} | ${hz_cmdvel} |" >> "$CONSOLIDADO"
}

###############################################################################
# 12. LIMPEZA / TRATAMENTO DE INTERRUPÇÃO
###############################################################################

limpar_processos_residuais() {
    log_aviso "Encerrando processos auxiliares residuais..."
    parar_robo
    pkill -f "ros2 bag record" 2>/dev/null
    pkill -f "ros2 topic echo .* --csv" 2>/dev/null
    pkill -f "ros2 topic pub -r ${TAXA_PUBLICACAO_CMDVEL} /cmd_vel" 2>/dev/null
}

tratar_interrupcao() {
    log_erro "Execução interrompida pelo usuário (Ctrl+C). Limpando e encerrando..."
    limpar_processos_residuais
    exit 130
}
trap tratar_interrupcao SIGINT SIGTERM

###############################################################################
# 13. AJUDA E PARSING DE ARGUMENTOS
###############################################################################

mostrar_ajuda() {
    cat <<EOF
Uso: $0 [opções]

Coleta automatizada de dados experimentais de trajetória do robô diferencial
hospitalar em simulação (ROS 2 Humble + Gazebo Fortress).

Opções:
  --velocidade VALOR        Velocidade linear comandada em m/s (padrão: ${VELOCIDADE_LINEAR})
  --angular VALOR            Velocidade angular comandada em rad/s (padrão: ${VELOCIDADE_ANGULAR})
  --distancia VALOR          Distância planejada em m, usada p/ estimar tempo (padrão: ${DISTANCIA_PLANEJADA})
  --duracao-max SEGUNDOS      Força a duração máxima (senão é calculada da distância)
  --repeticoes N              Número de execuções/amostras (padrão: ${NUM_REPETICOES})
  --intervalo SEGUNDOS        Espera entre execuções (padrão: ${INTERVALO_ENTRE_EXEC})
  --taxa-publicacao HZ        Taxa de publicação do /cmd_vel (padrão: ${TAXA_PUBLICACAO_CMDVEL})
  --nome NOME                 Nome/identificador do experimento (padrão: ${NOME_EXPERIMENTO})
  --saida DIR                 Diretório base de saída (padrão: ${DIR_SAIDA_BASE})
  --world CAMINHO              Força o caminho do arquivo .world (senão detecta automaticamente)
  --urdf CAMINHO                Força o caminho do URDF/Xacro (senão detecta automaticamente)
  --sem-reset                  Não reseta a simulação entre execuções
  -h, --help                   Mostra esta ajuda e sai

Exemplo:
  $0 --velocidade -0.25 --distancia 5.0 --repeticoes 20 --nome pid_kp08
EOF
}

parse_argumentos() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --velocidade) VELOCIDADE_LINEAR="$2"; shift 2 ;;
            --angular) VELOCIDADE_ANGULAR="$2"; shift 2 ;;
            --distancia) DISTANCIA_PLANEJADA="$2"; shift 2 ;;
            --duracao-max) DURACAO_MAX="$2"; shift 2 ;;
            --repeticoes) NUM_REPETICOES="$2"; shift 2 ;;
            --intervalo) INTERVALO_ENTRE_EXEC="$2"; shift 2 ;;
            --taxa-publicacao) TAXA_PUBLICACAO_CMDVEL="$2"; shift 2 ;;
            --nome) NOME_EXPERIMENTO="$2"; shift 2 ;;
            --saida) DIR_SAIDA_BASE="$2"; shift 2 ;;
            --world) FORCAR_WORLD="$2"; shift 2 ;;
            --urdf) FORCAR_URDF="$2"; shift 2 ;;
            --sem-reset) RESET_ENTRE_EXECUCOES=0; shift ;;
            -h|--help) mostrar_ajuda; exit 0 ;;
            *) log_erro "Argumento desconhecido: $1"; mostrar_ajuda; exit 1 ;;
        esac
    done
}

###############################################################################
# 14. EXECUÇÃO DE UMA ÚNICA AMOSTRA
###############################################################################

executar_amostra() {
    local idx="$1"
    local dir="${DIR_SAIDA}/amostra_${idx}"
    mkdir -p "$dir"

    log_info "----- Amostra ${idx}/${NUM_REPETICOES} -----"

    if [ "$RESET_ENTRE_EXECUCOES" -eq 1 ]; then
        resetar_simulacao
    fi

    obter_pose_inicial "${dir}/pose_inicial.json"

    local pid_bag pids_csv=()
    pid_bag=$(iniciar_gravacao_bag "$dir")
    iniciar_exportacao_csv "$dir" pids_csv
    sleep 2   # garante que gravadores já estão inscritos antes de mover o robô

    local t_inicio t_fim execucao_incompleta=0
    local hz_cmdvel_arquivo
    hz_cmdvel_arquivo=$(mktemp)
    # Mede a frequência de /cmd_vel em paralelo, enquanto ele ainda está
    # sendo publicado — medir depois de parar_robo (como antes) sempre
    # resultava em N/A, pois o tópico já não publicava mais nesse ponto.
    ( medir_frequencia_topico "$TOPICO_CMD_VEL" > "$hz_cmdvel_arquivo" ) &
    local pid_hz_cmdvel=$!

    t_inicio=$(date +%s.%N)
    publicar_cmd_vel "$VELOCIDADE_LINEAR" "$VELOCIDADE_ANGULAR" "$DURACAO_MAX"
    t_fim=$(date +%s.%N)
    TEMPO_REAL_EXECUCAO=$(echo "scale=4; $t_fim - $t_inicio" | bc 2>/dev/null || echo "N/A")

    wait "$pid_hz_cmdvel" 2>/dev/null
    HZ_CMDVEL=$(cat "$hz_cmdvel_arquivo" 2>/dev/null)
    rm -f "$hz_cmdvel_arquivo"
    [ -z "$HZ_CMDVEL" ] && HZ_CMDVEL="N/A"

    # Em malha aberta, terminar com tempo_real ≈ duracao_max é o resultado
    # ESPERADO (é o próprio 'timeout' que interrompe a publicação na hora
    # certa). Uma amostra é considerada incompleta/suspeita apenas se o
    # 'ros2 topic pub' foi interrompido bem ANTES do planejado — sinal de
    # falha externa (nó morto, comunicação perdida, etc.), não de sucesso.
    if awk "BEGIN{exit !(${TEMPO_REAL_EXECUCAO} < (${DURACAO_MAX} * 0.9))}" 2>/dev/null; then
        execucao_incompleta=1
    fi

    parar_robo
    sleep 1

    # Medições de frequência (janela curta, tópicos ainda ativos pós-movimento)
    HZ_ODOM=$(medir_frequencia_topico "$TOPICO_ODOM")
    HZ_IMU=$(medir_frequencia_topico "$TOPICO_IMU")
    HZ_SCAN=$(medir_frequencia_topico "$TOPICO_SCAN")
    HZ_JOINT_STATES=$(medir_frequencia_topico "$TOPICO_JOINT_STATES")

    parar_gravacao_bag "$pid_bag"
    parar_exportacao_csv pids_csv

    calcular_estatisticas_odom "${dir}/csv/odom_posicao.csv" "${dir}/estatisticas.json" "$TEMPO_REAL_EXECUCAO"

    local n_msgs_odom
    n_msgs_odom=$(python3 -c "import json;print(json.load(open('${dir}/estatisticas.json'))['mensagens_odom_recebidas'])" 2>/dev/null || echo 0)

    local classificacao
    classificacao=$(classificar_execucao "$n_msgs_odom" "$HZ_ODOM" "$execucao_incompleta" "$HZ_CMDVEL")

    SENTIDO_DESLOCAMENTO="frente"
    awk "BEGIN{exit !(${VELOCIDADE_LINEAR} < 0)}" && SENTIDO_DESLOCAMENTO="ré"

    {
        echo "amostra=${idx}"
        echo "classificacao=${classificacao}"
        echo "tempo_real_execucao_s=${TEMPO_REAL_EXECUCAO}"
        echo "execucao_incompleta=${execucao_incompleta}"
        echo "mensagens_odom=${n_msgs_odom}"
        echo "hz_odom=${HZ_ODOM}"
        echo "hz_imu=${HZ_IMU}"
        echo "hz_scan=${HZ_SCAN}"
        echo "hz_joint_states=${HZ_JOINT_STATES}"
        echo "timestamp=$(date -Iseconds)"
    } > "${dir}/resultado.txt"

    gerar_relatorio_individual "$dir" "$idx" "$classificacao"

    local dist vel_media
    dist=$(python3 -c "import json;print(json.load(open('${dir}/estatisticas.json'))['distancia_percorrida_m_estimada'])" 2>/dev/null || echo N/A)
    vel_media=$(python3 -c "import json;print(json.load(open('${dir}/estatisticas.json'))['velocidade_media_m_s_estimada'])" 2>/dev/null || echo N/A)
    adicionar_linha_consolidado "$idx" "$classificacao" "$TEMPO_REAL_EXECUCAO" "$dist" "$vel_media" "$HZ_ODOM" "$HZ_CMDVEL"

    log_ok "Amostra ${idx} finalizada — classificação: ${classificacao} (tempo real: ${TEMPO_REAL_EXECUCAO}s)"
}

###############################################################################
# 15. FUNÇÃO PRINCIPAL
###############################################################################

main() {
    parse_argumentos "$@"

    verificar_comando bc 1
    verificar_comando python3 1
    verificar_comando zip 0

    verificar_ambiente_ros
    verificar_gazebo

    TOPICO_IMU=$(detectar_topico_imu)
    TOPICOS_BAG=("$TOPICO_ODOM" "$TOPICO_IMU" "$TOPICO_SCAN" "$TOPICO_JOINT_STATES" "$TOPICO_CMD_VEL" /tf /tf_static)
    TOPICOS_CSV=("$TOPICO_ODOM" "$TOPICO_IMU" "$TOPICO_SCAN" "$TOPICO_CMD_VEL")

    verificar_topicos_necessarios

    DATA_HORA_INICIO=$(date -Iseconds)
    VERSAO_GAZEBO=$(detectar_versao_gazebo)
    EKF_STATUS=$(detectar_ekf)
    FREQ_CONTROLADOR_CONFIG=$(find . -path "*/log/*" -prune -o -iname "controllers.yaml" -print 2>/dev/null \
        | grep -viE "/install/" | head -n1 | xargs -r grep -oE 'update_rate:\s*[0-9.]+' | head -n1 | awk '{print $2}')
    [ -z "${FREQ_CONTROLADOR_CONFIG:-}" ] && FREQ_CONTROLADOR_CONFIG="N/A"

    # Calcula a duração do movimento a partir da distância, se não foi forçada.
    # IMPORTANTE: como este script publica /cmd_vel em malha aberta (sem um
    # nó de controle que detecte e pare sozinho ao atingir a meta), o
    # 'timeout' aplicado ao 'ros2 topic pub' É o próprio mecanismo de parada.
    # Portanto a duração deve ser exatamente distância/velocidade — SEM
    # margem de segurança extra, ao contrário do que se faria para limitar
    # externamente um controlador em malha fechada (ver experimento_pid.sh).
    if [ -z "$DURACAO_MAX" ]; then
        local vel_abs
        vel_abs=$(echo "$VELOCIDADE_LINEAR" | tr -d '-')
        if [ "$vel_abs" = "0" ] || [ "$vel_abs" = "0.0" ]; then
            log_erro "Velocidade linear é zero e --duracao-max não foi informada; não é possível estimar a duração."
            exit 1
        fi
        DURACAO_MAX=$(echo "scale=4; $DISTANCIA_PLANEJADA / $vel_abs" | bc)
    fi

    local ts_dir
    ts_dir=$(date +%Y%m%d_%H%M%S)
    DIR_SAIDA="${DIR_SAIDA_BASE}/${NOME_EXPERIMENTO}_${ts_dir}"
    mkdir -p "$DIR_SAIDA"

    log_info "Diretório de saída: ${DIR_SAIDA}"
    log_info "Velocidade: ${VELOCIDADE_LINEAR} m/s | Distância planejada: ${DISTANCIA_PLANEJADA} m | Duração máx.: ${DURACAO_MAX}s"
    log_info "Repetições: ${NUM_REPETICOES} | Reset entre execuções: $([ "$RESET_ENTRE_EXECUCOES" -eq 1 ] && echo sim || echo não)"

    # Coleta única (estática) dos parâmetros do mundo e do robô, reaproveitada
    # em todos os relatórios individuais desta rodada de experimentos
    local world_file urdf_file
    world_file=$(localizar_world)
    urdf_file=$(localizar_urdf)
    [ -n "$world_file" ] && log_ok "Arquivo .world detectado: ${world_file}" || log_aviso "Arquivo .world não detectado."
    [ -n "$urdf_file" ] && log_ok "URDF/Xacro detectado: ${urdf_file}" || log_aviso "URDF/Xacro não detectado."

    extrair_parametros_world "$world_file" "${DIR_SAIDA}/mundo.json"
    extrair_parametros_robot "$urdf_file" "${DIR_SAIDA}/robo.json"

    inicializar_relatorio_consolidado

    for i in $(seq 1 "$NUM_REPETICOES"); do
        executar_amostra "$i"
        if [ "$i" -lt "$NUM_REPETICOES" ]; then
            sleep "$INTERVALO_ENTRE_EXEC"
        fi
    done

    echo "" >> "$CONSOLIDADO"
    echo "**Fim:** $(date -Iseconds)" >> "$CONSOLIDADO"

    log_ok "========================================"
    log_ok "Experimento '${NOME_EXPERIMENTO}' concluído."
    log_ok "Relatório consolidado: ${CONSOLIDADO}"
    log_ok "========================================"

    if command -v zip >/dev/null 2>&1; then
        local zip_name="${DIR_SAIDA}.zip"
        log_info "Compactando resultados em ${zip_name}..."
        zip -rq "$zip_name" "$DIR_SAIDA"
        log_ok "Arquivo compactado: ${zip_name}"
    fi
}

main "$@"

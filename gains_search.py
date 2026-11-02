"""
Busca sistemática de ganhos (Kp, Ki, Kd, Kh) para o lateral_pid_controller
do hemabot_ros2.

USO BÁSICO (depois do preflight passar):
    cd ~/hemabot_ros2
    source /opt/ros/<sua_distro>/setup.bash
    source install/setup.bash
    pip install numpy pandas matplotlib --break-system-packages
    python3 gains_search.py

Isso roda um grid search em (Kd, Kh), reiniciando o Gazebo entre blocos de
amostras, extrai métricas dos bags via extrair_metricas_bag.py, salva
progresso incrementalmente, gera um heatmap, valida o melhor candidato com
amostras novas e grava o resultado final em melhor_candidato.json.

Arquivos irmãos necessários no mesmo diretório:
    - experimento_pid.sh        (parametrizado via env vars)
    - extrair_metricas_bag.py   (lê /odom e /gazebo/model_states dos bags)

Requisitos: numpy, pandas, matplotlib, e um ambiente ROS2 com rclpy,
rosbag2_py e rosidl_runtime_py já sourced no terminal ONDE VOCÊ RODA
`python3 gains_search.py` (os subprocessos herdam esse ambiente).
"""

import itertools
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from extrair_metricas_bag import processar_diretorio_amostras


# =============================================================================
# 0. CONFIGURAÇÃO — confirmada a partir do repositório hemabot_ros2
# =============================================================================

CAMINHO_EXPERIMENTO_SH = os.environ.get("CAMINHO_EXPERIMENTO_SH", "./experimento_pid.sh")
DIR_BASE_BUSCA = os.environ.get("DIR_BASE_BUSCA", "busca_ganhos_amostras")
DISTANCIA_ALVO = 5.0  # m — mesma distância usada no experimento_pid.sh

# Nome do modelo spawnado no Gazebo. Confirmado em
# d_hospital_gazebo2/launch/hospital.py -> spawn_entity.py -entity d_hospital
# Nome do modelo spawnado no Gazebo. ATENÇÃO: depende do launch file:
#   hospital.py -> "d_hospital"     |     display.py -> "d_hospitalbot"
# Como GAZEBO_LAUNCH_FILE abaixo está em "display.py", o default aqui
# precisa ser "d_hospitalbot" — senão extrair_metricas_bag.py não encontra
# o robô em /gazebo/model_states, e o reposicionamento em
# experimento_pid.sh (/gazebo/set_entity_state) também falha silenciosamente.
ROBOT_MODEL_NAME = os.environ.get("ROBOT_MODEL_NAME", "d_hospitalbot")

# Comando de launch real, confirmado em simulation_launch.sh:
#   ros2 launch d_hospital_gazebo2 hospital.py
GAZEBO_LAUNCH_PACKAGE = os.environ.get("GAZEBO_LAUNCH_PACKAGE", "d_hospital_gazebo2")
GAZEBO_LAUNCH_FILE = os.environ.get("GAZEBO_LAUNCH_FILE", "display.py")

# O default do hospital.py é obstacles.world, mas para esta busca usamos
# d_hospital_gazebo2/worlds/pea.world. Sobrescreva via env var se precisar
# trocar para outro mundo (ex.: pista_reta.world):
#   export GAZEBO_WORLD_FILE=pista_reta.world
GAZEBO_WORLD_FILE = os.environ.get("GAZEBO_WORLD_FILE", "")

# Liga/desliga o EKF (robot_localization -> remapeado para /odom). Equivale
# à distinção "EKF ligado" vs "sem EKF" do relatório original.
GAZEBO_USE_ROBOT_LOCALIZATION = os.environ.get("GAZEBO_USE_ROBOT_LOCALIZATION", "True")

GAZEBO_READY_TOPIC = os.environ.get("GAZEBO_READY_TOPIC", "/clock")
GAZEBO_READY_TIMEOUT_S = float(os.environ.get("GAZEBO_READY_TIMEOUT_S", "60"))
GAZEBO_LOG_DIR = Path(os.environ.get("GAZEBO_LOG_DIR", "gazebo_restart_logs"))
GAZEBO_LOG_DIR.mkdir(exist_ok=True)


# =============================================================================
# 1. PREFLIGHT — evita descobrir "package not found" no meio de uma busca de horas
# =============================================================================

def verificar_ambiente() -> None:
    """
    Confirma que o ambiente ROS2 + workspace estão sourced e que os
    arquivos irmãos existem, ANTES de começar a busca. Falha rápido e
    com mensagem clara em vez de deixar cada combinação da busca falhar
    silenciosamente (foi exatamente isso que causou o erro
    "Package 'd_hospital_control' not found" quando o script rodou sem o
    workspace sourced).
    """
    print("Verificando ambiente antes de iniciar a busca...")
    problemas = []

    if not os.path.isfile(CAMINHO_EXPERIMENTO_SH):
        problemas.append(f"'{CAMINHO_EXPERIMENTO_SH}' não encontrado. "
                          f"Rode este script a partir do mesmo diretório que "
                          f"contém experimento_pid.sh (raiz do hemabot_ros2).")
    elif not os.access(CAMINHO_EXPERIMENTO_SH, os.X_OK):
        problemas.append(f"'{CAMINHO_EXPERIMENTO_SH}' existe mas não é executável "
                          f"— rode: chmod +x {CAMINHO_EXPERIMENTO_SH}")

    try:
        resultado = subprocess.run(["ros2", "pkg", "list"], capture_output=True,
                                    text=True, timeout=15)
        pacotes = resultado.stdout.split()
        if "d_hospital_control" not in pacotes:
            problemas.append(
                "Pacote 'd_hospital_control' não encontrado por 'ros2 pkg list'. "
                "O workspace não está sourced neste terminal (ou não foi "
                "compilado ainda). Rode, no MESMO terminal onde você vai "
                "executar 'python3 gains_search.py':\n"
                "    source /opt/ros/<sua_distro>/setup.bash\n"
                "    source install/setup.bash\n"
                "    colcon build   # se ainda não tiver buildado"
            )
    except FileNotFoundError:
        problemas.append("Comando 'ros2' não encontrado no PATH — o ambiente "
                          "ROS2 não está sourced neste terminal.")
    except subprocess.TimeoutExpired:
        problemas.append("'ros2 pkg list' não respondeu em 15s — verifique se "
                          "há algum daemon ROS2 travado.")

    if not problemas and GAZEBO_WORLD_FILE:
        try:
            caminho = _resolver_caminho_mundo(GAZEBO_WORLD_FILE)
            print(f"Mundo confirmado: {caminho}")
        except Exception as e:
            problemas.append(str(e))

    if problemas:
        print("\n" + "=" * 60)
        print("PREFLIGHT FALHOU — corrija antes de rodar a busca:")
        print("=" * 60)
        for p in problemas:
            print(f"\n- {p}")
        print()
        sys.exit(1)

    print("Preflight OK: ambiente ROS2 e experimento_pid.sh prontos.\n")


# =============================================================================
# 2. RESTART AUTOMÁTICO DO GAZEBO ENTRE BLOCOS
# =============================================================================

# Guarda o processo do Gazebo lançado por esta sessão, para conseguirmos
# encerrar o GRUPO inteiro de processos filhos (robot_state_publisher,
# ekf_node, twist_mux, spawners) no próximo restart — cada um roda com sua
# própria linha de comando, então um simples "pkill -f hospital.py" não
# pega os filhos.
_processo_gazebo_atual = None


_caminho_mundo_cache = None


def _resolver_caminho_mundo(nome_arquivo: str) -> str:
    """
    O argumento 'world' do hospital.py espera o CAMINHO COMPLETO do .world
    (é repassado direto pro gazebo_ros), não só o nome do arquivo. Resolve
    isso a partir do prefixo de instalação do pacote:
        <prefix>/share/d_hospital_gazebo2/worlds/<nome_arquivo>
    Se já vier um caminho absoluto, usa como está.
    """
    global _caminho_mundo_cache
    if os.path.isabs(nome_arquivo):
        return nome_arquivo
    if _caminho_mundo_cache is not None:
        return _caminho_mundo_cache

    resultado = subprocess.run(
        ["ros2", "pkg", "prefix", GAZEBO_LAUNCH_PACKAGE],
        capture_output=True, text=True, timeout=10,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"Não foi possível resolver o caminho de '{nome_arquivo}': "
            f"'ros2 pkg prefix {GAZEBO_LAUNCH_PACKAGE}' falhou. "
            f"O workspace está sourced?"
        )
    prefixo = resultado.stdout.strip()
    caminho = os.path.join(prefixo, "share", GAZEBO_LAUNCH_PACKAGE, "worlds", nome_arquivo)
    if not os.path.isfile(caminho):
        raise FileNotFoundError(
            f"Mundo '{nome_arquivo}' não encontrado em {caminho}. "
            f"Confira o nome (ex.: pea.world) e se o pacote foi buildado/instalado."
        )
    _caminho_mundo_cache = caminho
    return caminho


def _montar_comando_launch() -> list:
    cmd = [
        "ros2", "launch", GAZEBO_LAUNCH_PACKAGE, GAZEBO_LAUNCH_FILE,
        "use_sim_time:=true",
        f"use_robot_localization:={GAZEBO_USE_ROBOT_LOCALIZATION}",
    ]
    if GAZEBO_WORLD_FILE:
        caminho_mundo = _resolver_caminho_mundo(GAZEBO_WORLD_FILE)
        cmd.append(f"world:={caminho_mundo}")
    return cmd


def reiniciar_gazebo(indice_reinicio: int = 0) -> None:
    """
    Mata a instância anterior do Gazebo (grupo de processos inteiro) e sobe
    uma nova, esperando até confirmar que está pronta antes de retornar.

    Isso endereça a degradação de RTF relatada em execuções longas sem
    reinício: cada bloco de amostras começa com um Gazebo "fresco".
    """
    global _processo_gazebo_atual

    print("  [Gazebo] Encerrando instância anterior (se houver)...")
    if _processo_gazebo_atual is not None and _processo_gazebo_atual.poll() is None:
        try:
            pgid = os.getpgid(_processo_gazebo_atual.pid)
            os.killpg(pgid, signal.SIGINT)
            time.sleep(2)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    # Rede de segurança para processos órfãos de sessões anteriores
    subprocess.run(["pkill", "-9", "-f", "gzserver"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", "gzclient"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", f"{GAZEBO_LAUNCH_PACKAGE} {GAZEBO_LAUNCH_FILE}"],
                    capture_output=True)
    time.sleep(3)

    # Confirma que não sobrou nenhum gzserver de pé antes de subir um novo —
    # se sobrar, a "instância nova" na verdade vai conviver com uma antiga
    # (ou nem conseguir bindar a porta), e o /clock detectado depois é da
    # instância velha, travada onde o robô parou da última vez.
    sobreviventes = subprocess.run(["pgrep", "-f", "gzserver"], capture_output=True, text=True)
    if sobreviventes.stdout.strip():
        raise RuntimeError(
            f"gzserver ainda rodando após tentativa de kill (PIDs: "
            f"{sobreviventes.stdout.split()}). Mate manualmente com "
            f"'kill -9 {' '.join(sobreviventes.stdout.split())}' e rode de novo."
        )

    cmd = _montar_comando_launch()
    print(f"  [Gazebo] Subindo nova instância: {' '.join(cmd)}")
    log_path = GAZEBO_LOG_DIR / f"restart_{indice_reinicio:04d}.log"
    with open(log_path, "w") as log_file:
        # NÃO envolver com o binário 'setsid' aqui: start_new_session=True já
        # faz isso via os.setsid(). Envolver com os DOIS ao mesmo tempo faz o
        # utilitário 'setsid' externo detectar que já é líder de sessão,
        # forkar e sair imediatamente — o Popen então aponta pro processo
        # ERRADO (já morto), perdendo o handle real do Gazebo e quebrando o
        # killpg da próxima reinicialização (era a causa raiz do restart
        # "fantasma" com /clock de 1.5s).
        _processo_gazebo_atual = subprocess.Popen(
            cmd,
            stdout=log_file, stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    _esperar_gazebo_pronto(timeout_s=GAZEBO_READY_TIMEOUT_S)

    # Garante que a física não subiu pausada (senão o robô recebe /cmd_vel
    # normalmente mas nunca se move — mesmo sintoma de "travado").
    subprocess.run(["ros2", "service", "call", "/unpause_physics", "std_srvs/srv/Empty"],
                    capture_output=True, timeout=10)


def _esperar_gazebo_pronto(timeout_s: float) -> None:
    """
    Faz polling em GAZEBO_READY_TOPIC até a simulação responder, E confirma
    que o clock está de fato AVANÇANDO (não só existindo) — um /clock que
    existe mas não avança é sinal de instância travada/pausada, não de
    Gazebo pronto.
    """
    inicio = time.time()
    while time.time() - inicio < timeout_s:
        resultado = subprocess.run(
            ["ros2", "topic", "list"], capture_output=True, text=True, timeout=10
        )
        if GAZEBO_READY_TOPIC in resultado.stdout.split():
            if _clock_esta_avancando():
                print(f"  [Gazebo] Pronto e avançando após {time.time() - inicio:.1f}s.")
                time.sleep(2)  # margem extra para nós/plugins terminarem de subir
                return
            print("  [Gazebo] /clock presente mas não avança ainda, aguardando...")
        time.sleep(2)

    raise TimeoutError(
        f"Gazebo não ficou pronto em {timeout_s}s (tópico {GAZEBO_READY_TOPIC} "
        f"não apareceu ou não avança). Verifique GAZEBO_LAUNCH_PACKAGE/"
        f"GAZEBO_LAUNCH_FILE e o log em {GAZEBO_LOG_DIR}."
    )


def _clock_esta_avancando() -> bool:
    """Lê /clock duas vezes com um intervalo e confirma que o tempo avançou."""
    def _ler_clock():
        r = subprocess.run(
            ["ros2", "topic", "echo", GAZEBO_READY_TOPIC, "--once"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout

    try:
        t1 = _ler_clock()
        time.sleep(1.5)
        t2 = _ler_clock()
        return bool(t1) and bool(t2) and t1 != t2
    except subprocess.TimeoutExpired:
        return False


def encerrar_gazebo() -> None:
    """Mata a instância do Gazebo desta sessão. Chame ao final da busca."""
    global _processo_gazebo_atual
    if _processo_gazebo_atual is not None and _processo_gazebo_atual.poll() is None:
        try:
            pgid = os.getpgid(_processo_gazebo_atual.pid)
            os.killpg(pgid, signal.SIGINT)
        except ProcessLookupError:
            pass
    subprocess.run(["pkill", "-f", "gzserver"], capture_output=True)
    subprocess.run(["pkill", "-f", "gzclient"], capture_output=True)


# =============================================================================
# 3. run_simulation() — chama experimento_pid.sh e extrai as métricas
# =============================================================================

def _nome_dir_combinacao(kp: float, ki: float, kd: float, kh: float) -> str:
    def fmt(v):
        return f"{v:.4f}".replace(".", "p").replace("-", "m")
    return f"kp{fmt(kp)}_ki{fmt(ki)}_kd{fmt(kd)}_kh{fmt(kh)}"


def _gerar_blocos(n_samples: int, tamanho_bloco: int):
    blocos = []
    inicio = 1
    while inicio <= n_samples:
        fim = min(inicio + tamanho_bloco - 1, n_samples)
        blocos.append((inicio, fim))
        inicio = fim + 1
    return blocos


def run_simulation(kd: float, kh: float, kp: float = 0.8, ki: float = 0.0,
                    n_samples: int = 20, reiniciar_por_bloco: bool = True,
                    tamanho_bloco: int = 10, manter_bags: bool = False) -> dict:
    """
    Roda N amostras do experimento_pid.sh com os ganhos (kp, ki, kd, kh) e
    retorna as métricas agregadas, lidas diretamente dos bags gerados.
    """
    dir_saida = os.path.join(DIR_BASE_BUSCA, _nome_dir_combinacao(kp, ki, kd, kh))
    # Limpa qualquer resquício de uma tentativa anterior desta MESMA combinação
    # (ros2 bag record falha se o diretório de saída já existir).
    if os.path.exists(dir_saida):
        shutil.rmtree(dir_saida)
    os.makedirs(dir_saida)

    env = os.environ.copy()
    env.update({
        "KP": str(kp), "KI": str(ki), "KD": str(kd), "KH": str(kh),
        "NUM_AMOSTRAS": str(n_samples),
        "DIR_AMOSTRAS_OVERRIDE": dir_saida,
        "ROBOT_MODEL_NAME": ROBOT_MODEL_NAME,
    })

    blocos = _gerar_blocos(n_samples, tamanho_bloco if reiniciar_por_bloco else n_samples)
    for idx_bloco, (inicio, fim) in enumerate(blocos):
        if reiniciar_por_bloco:
            reiniciar_gazebo(indice_reinicio=idx_bloco)

        resultado = subprocess.run(
            [CAMINHO_EXPERIMENTO_SH, str(inicio), str(fim)],
            env=env, capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            raise RuntimeError(
                f"experimento_pid.sh falhou (Kp={kp}, Ki={ki}, Kd={kd}, Kh={kh}, "
                f"amostras {inicio}-{fim}):\n"
                f"--- stdout (final) ---\n{resultado.stdout[-2000:]}\n"
                f"--- stderr (final) ---\n{resultado.stderr[-2000:]}"
            )
        # Checagem adicional: mesmo com returncode 0, o node pode ter
        # falhado silenciosamente (ex.: pacote não encontrado, mas o
        # 'timeout' engoliu o erro). Detecta esse caso específico cedo.
        if "not found" in resultado.stdout.lower() or "not found" in resultado.stderr.lower():
            raise RuntimeError(
                f"experimento_pid.sh reportou 'not found' (Kp={kp}, Ki={ki}, "
                f"Kd={kd}, Kh={kh}, amostras {inicio}-{fim}) — provável pacote "
                f"ROS2 não encontrado. Rode verificar_ambiente() e confira o "
                f"source do workspace.\n--- stdout ---\n{resultado.stdout[-1500:]}"
            )

    _, agregado = processar_diretorio_amostras(
        dir_saida, distancia_alvo=DISTANCIA_ALVO, robot_model_name=ROBOT_MODEL_NAME
    )

    if not manter_bags:
        shutil.rmtree(dir_saida, ignore_errors=True)

    return agregado


# =============================================================================
# 4. FUNÇÃO DE CUSTO
# =============================================================================

@dataclass
class PesosCusto:
    """Pesos da função de custo. Ajuste conforme a prioridade do projeto."""
    w_e_y: float = 1.0        # penaliza erro lateral médio (viés)
    w_e_x: float = 0.5        # penaliza erro longitudinal médio
    w_iae: float = 1.0        # penaliza erro acumulado ao longo da trajetória
    w_overshoot: float = 2.0  # penaliza picos (overshoot) fortemente
    w_std: float = 1.0        # penaliza inconsistência entre amostras


def calcular_custo(metricas: dict, pesos: PesosCusto = PesosCusto()) -> float:
    """Menor custo = melhor combinação de ganhos."""
    return (
        pesos.w_e_y * abs(metricas["e_y_final_medio"])
        + pesos.w_e_x * abs(metricas["e_x_final_medio"])
        + pesos.w_iae * metricas["iae_medio"]
        + pesos.w_overshoot * abs(metricas["overshoot_max"])
        + pesos.w_std * metricas["e_y_final_std"]
    )


# =============================================================================
# 5. GRID SEARCH
# =============================================================================

def grid_search(kd_valores, kh_valores, n_samples=20,
                 pesos: PesosCusto = PesosCusto(),
                 checkpoint_path: str = "grid_search_resultados.csv") -> pd.DataFrame:
    """
    Varre todas as combinações de kd_valores x kh_valores.
    Salva resultados incrementalmente em CSV (retomável se cair no meio).
    """
    resultados = []
    checkpoint = Path(checkpoint_path)

    ja_testados = set()
    if checkpoint.exists():
        df_existente = pd.read_csv(checkpoint)
        resultados = df_existente.to_dict("records")
        ja_testados = {(round(r["kd"], 6), round(r["kh"], 6)) for r in resultados}
        print(f"Retomando checkpoint com {len(resultados)} combinações já testadas.")

    combinacoes = list(itertools.product(kd_valores, kh_valores))
    total = len(combinacoes)

    for i, (kd, kh) in enumerate(combinacoes, 1):
        if (round(kd, 6), round(kh, 6)) in ja_testados:
            continue

        print(f"[{i}/{total}] Testando Kd={kd:.3f}, Kh={kh:.3f} ...")
        t0 = time.time()
        try:
            metricas = run_simulation(kd, kh, n_samples=n_samples, reiniciar_por_bloco=True)
            custo = calcular_custo(metricas, pesos)
            registro = {"kd": kd, "kh": kh, "custo": custo,
                        "tempo_s": time.time() - t0, **metricas}
        except Exception as e:
            print(f"  ERRO em Kd={kd}, Kh={kh}: {e}")
            registro = {"kd": kd, "kh": kh, "custo": np.nan,
                        "tempo_s": time.time() - t0, "erro": str(e)}

        resultados.append(registro)
        pd.DataFrame(resultados).to_csv(checkpoint_path, index=False)

    df = pd.DataFrame(resultados)
    return df.sort_values("custo")


def plotar_heatmap_custo(df: pd.DataFrame, out_path: str = "heatmap_custo.png"):
    """Gera um heatmap do custo em função de (Kd, Kh)."""
    df_validos = df.dropna(subset=["custo"])
    if df_validos.empty:
        print("Nenhum resultado válido para plotar (todas as combinações falharam).")
        return

    pivot = df_validos.pivot_table(index="kh", columns="kd", values="custo")

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(pivot.values, origin="lower", aspect="auto", cmap="viridis_r")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{v:.3f}" for v in pivot.columns], rotation=45)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{v:.3f}" for v in pivot.index])
    ax.set_xlabel("Kd")
    ax.set_ylabel("Kh")
    ax.set_title("Custo por combinação de ganhos (menor = melhor)")
    fig.colorbar(im, ax=ax, label="Custo")

    melhor = df_validos.loc[df_validos["custo"].idxmin()]
    ix = list(pivot.columns).index(melhor["kd"])
    iy = list(pivot.index).index(melhor["kh"])
    ax.scatter([ix], [iy], marker="*", s=300, color="red",
               label=f"Melhor: Kd={melhor['kd']:.3f}, Kh={melhor['kh']:.3f}")
    ax.legend()

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Heatmap salvo em {out_path}")


# =============================================================================
# 6. BUSCA COORDENADA (alternativa mais barata que o grid completo)
# =============================================================================

def busca_coordenada(kd_inicial: float, kh_inicial: float,
                      kd_range, kh_range, n_samples=20,
                      pesos: PesosCusto = PesosCusto(),
                      n_ciclos: int = 2) -> dict:
    """
    Otimiza um parâmetro por vez, fixando o outro.
    Bom ponto de partida: Kd=0.15, Kh=0.6 (melhor resultado do relatório
    original — note que o experimento_pid.sh atual do repo usa Kd=0.38).
    """
    kd, kh = kd_inicial, kh_inicial
    historico = []
    melhor_custo = np.inf

    for ciclo in range(1, n_ciclos + 1):
        print(f"\n=== Ciclo {ciclo}: otimizando Kd (Kh fixo = {kh:.3f}) ===")
        melhor_custo_kd = np.inf
        melhor_kd = kd
        for kd_teste in kd_range:
            m = run_simulation(kd_teste, kh, n_samples=n_samples)
            c = calcular_custo(m, pesos)
            historico.append({"ciclo": ciclo, "etapa": "kd", "kd": kd_teste,
                               "kh": kh, "custo": c, **m})
            print(f"  Kd={kd_teste:.3f} -> custo={c:.5f}")
            if c < melhor_custo_kd:
                melhor_custo_kd, melhor_kd = c, kd_teste
        kd, melhor_custo = melhor_kd, melhor_custo_kd

        print(f"\n=== Ciclo {ciclo}: otimizando Kh (Kd fixo = {kd:.3f}) ===")
        melhor_custo_kh = np.inf
        melhor_kh = kh
        for kh_teste in kh_range:
            m = run_simulation(kd, kh_teste, n_samples=n_samples)
            c = calcular_custo(m, pesos)
            historico.append({"ciclo": ciclo, "etapa": "kh", "kd": kd,
                               "kh": kh_teste, "custo": c, **m})
            print(f"  Kh={kh_teste:.3f} -> custo={c:.5f}")
            if c < melhor_custo_kh:
                melhor_custo_kh, melhor_kh = c, kh_teste
        kh, melhor_custo = melhor_kh, melhor_custo_kh

        print(f"\n--> Fim do ciclo {ciclo}: Kd={kd:.3f}, Kh={kh:.3f}, custo={melhor_custo:.5f}")

    pd.DataFrame(historico).to_csv("busca_coordenada_historico.csv", index=False)
    return {"kd": kd, "kh": kh, "custo": melhor_custo}


# =============================================================================
# 7. VALIDAÇÃO — reamostragem do melhor candidato
# =============================================================================

def validar_candidato(kd: float, kh: float, n_samples: int = 20,
                       n_repeticoes: int = 3) -> pd.DataFrame:
    """
    Roda o melhor candidato várias vezes com lotes NOVOS de amostras, para
    garantir que o resultado não foi sorte estatística de um lote específico
    usado durante a busca.
    """
    registros = []
    for i in range(n_repeticoes):
        print(f"Validação {i+1}/{n_repeticoes} — Kd={kd:.3f}, Kh={kh:.3f}")
        m = run_simulation(kd, kh, n_samples=n_samples)
        registros.append({"repeticao": i + 1, **m})
    df = pd.DataFrame(registros)
    print("\nResumo da validação:")
    print(df.describe())
    return df


# =============================================================================
# 8. EXECUÇÃO PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    verificar_ambiente()

    try:
        # --- Malha do grid search ---------------------------------------
        # Cobre a vizinhança dos valores já testados manualmente
        # (Kd: 0.15/0.25/0.35/0.38, Kh: 0.6/0.8/1.0), então dá pra ver se o
        # ótimo está dentro ou fora dessa faixa.
        kd_valores = np.round(np.arange(0.05, 0.41, 0.05), 3)   # 0.05 .. 0.40
        kh_valores = np.round(np.arange(0.30, 1.01, 0.10), 3)   # 0.30 .. 1.00

        # n_samples baixo por padrão para a primeira rodada completa ser
        # viável em tempo razoável; suba para 50 depois de validar o fluxo.
        N_AMOSTRAS_BUSCA = int(os.environ.get("N_AMOSTRAS_BUSCA", "10"))

        df_grid = grid_search(kd_valores, kh_valores, n_samples=N_AMOSTRAS_BUSCA)
        print("\nTop 5 combinações (menor custo):")
        print(df_grid.head(5))
        plotar_heatmap_custo(df_grid)

        df_validos = df_grid.dropna(subset=["custo"])
        if df_validos.empty:
            print("\nTodas as combinações falharam — veja a coluna 'erro' em "
                  "grid_search_resultados.csv antes de tentar de novo.")
            sys.exit(1)

        melhor = df_validos.iloc[0]
        print("\nMelhor combinação encontrada:")
        print(melhor)
        if "odom_drift_y_final_medio" in melhor:
            print(f"\nDrift médio da odometria (odom - real) nesta combinação: "
                  f"{melhor['odom_drift_y_final_medio']:.5f} m "
                  f"(RMSE: {melhor.get('odom_drift_y_rmse_medio', float('nan')):.5f} m)")

        # --- Validação final com amostras novas -----------------------------
        N_AMOSTRAS_VALIDACAO = int(os.environ.get("N_AMOSTRAS_VALIDACAO", "20"))
        df_validacao = validar_candidato(melhor["kd"], melhor["kh"],
                                          n_samples=N_AMOSTRAS_VALIDACAO, n_repeticoes=3)

        with open("melhor_candidato.json", "w") as f:
            json.dump({"kp": 0.8, "ki": 0.0,
                       "kd": float(melhor["kd"]), "kh": float(melhor["kh"]),
                       "custo": float(melhor["custo"])}, f, indent=2)
        print("\nMelhor candidato salvo em melhor_candidato.json")

    finally:
        encerrar_gazebo()

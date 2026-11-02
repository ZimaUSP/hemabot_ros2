"""
Extração de métricas de odometria (/odom) a partir de bags rosbag2, para
alimentar a busca sistemática de ganhos (gains_search.py).

Assume que cada amostra é uma pasta de bag gerada por:
    ros2 bag record -o <dir>/amostra<i> /odom /cmd_vel

Requer ambiente ROS2 (mesmo usado por experimento_pid.sh):
    - rclpy
    - rosbag2_py
    - nav_msgs

Convenções de sinal (compatíveis com o relatório em PDF):
    e_y_final : erro lateral final [m]  (y_final - y_inicial; ref. y = 0)
    e_x_final : erro longitudinal final [m]
                (+) passou além do alvo   (-) ficou aquém do alvo
    iae       : integral do erro lateral absoluto ao longo do tempo [m·s]
    overshoot : pico máximo de |e_y| observado durante a trajetória [m]
"""

import argparse
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
except ImportError as e:
    raise ImportError(
        "Este script precisa rodar num ambiente com ROS2 (rclpy, rosbag2_py, "
        "rosidl_runtime_py) — o mesmo ambiente que executa o "
        "experimento_pid.sh. Rode com 'source /opt/ros/<distro>/setup.bash' "
        "ativo (e o workspace do d_hospital_control, se aplicável)."
    ) from e


# =============================================================================
# 1. LEITURA DE UM BAG -> DataFrame de série temporal de /odom
# =============================================================================

def ler_odom_do_bag(bag_path: str, topico: str = "/odom") -> pd.DataFrame:
    """
    Lê um bag rosbag2 (pasta) e retorna um DataFrame com colunas:
        t   : tempo relativo ao início do bag [s]
        x   : posição x [m]
        y   : posição y [m]
        yaw : orientação [rad] (a partir do quaternion)
    """
    storage_options = rosbag2_py.StorageOptions(uri=bag_path, storage_id="sqlite3")
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr", output_serialization_format="cdr"
    )

    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    tipos = {t.name: t.type for t in reader.get_all_topics_and_types()}
    if topico not in tipos:
        raise ValueError(
            f"Tópico {topico} não encontrado em {bag_path}. "
            f"Tópicos disponíveis: {list(tipos.keys())}"
        )
    msg_type = get_message(tipos[topico])

    registros = []
    t0 = None
    while reader.has_next():
        nome_topico, dados, timestamp_ns = reader.read_next()
        if nome_topico != topico:
            continue

        msg = deserialize_message(dados, msg_type)
        if t0 is None:
            t0 = timestamp_ns

        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        yaw = _quaternion_para_yaw(ori.x, ori.y, ori.z, ori.w)

        registros.append({
            "t": (timestamp_ns - t0) / 1e9,
            "x": pos.x,
            "y": pos.y,
            "yaw": yaw,
        })

    if not registros:
        raise ValueError(f"Nenhuma mensagem em {topico} encontrada em {bag_path}")

    return pd.DataFrame(registros)


def _quaternion_para_yaw(x: float, y: float, z: float, w: float) -> float:
    """Extrai o ângulo yaw (rotação em torno de z) de um quaternion."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return float(np.arctan2(siny_cosp, cosy_cosp))


def ler_pose_real_do_bag(bag_path: str, model_name: str,
                          topico: str = "/gazebo/model_states") -> pd.DataFrame:
    """
    Lê a pose REAL (ground truth) de um modelo específico a partir do tópico
    /gazebo/model_states (Gazebo clássico, gazebo_msgs/msg/ModelStates).

    Cada mensagem desse tópico traz TODOS os modelos da simulação; filtramos
    pelo nome do robô (ROBOT_MODEL_NAME no experimento_pid.sh).

    Retorna um DataFrame no mesmo formato de ler_odom_do_bag: t, x, y, yaw.
    Se o tópico não existir no bag (bags antigos, gravados antes desta
    mudança), retorna None.
    """
    storage_options = rosbag2_py.StorageOptions(uri=bag_path, storage_id="sqlite3")
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr", output_serialization_format="cdr"
    )

    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    tipos = {t.name: t.type for t in reader.get_all_topics_and_types()}
    if topico not in tipos:
        return None
    msg_type = get_message(tipos[topico])

    registros = []
    t0 = None
    modelo_nao_encontrado_avisado = False
    while reader.has_next():
        nome_topico, dados, timestamp_ns = reader.read_next()
        if nome_topico != topico:
            continue

        msg = deserialize_message(dados, msg_type)
        if model_name not in msg.name:
            if not modelo_nao_encontrado_avisado:
                print(f"  [AVISO] Modelo '{model_name}' não encontrado em "
                      f"{topico} de {bag_path}. Nomes disponíveis: {list(msg.name)}")
                modelo_nao_encontrado_avisado = True
            continue

        idx = list(msg.name).index(model_name)
        pos = msg.pose[idx].position
        ori = msg.pose[idx].orientation

        if t0 is None:
            t0 = timestamp_ns

        registros.append({
            "t": (timestamp_ns - t0) / 1e9,
            "x": pos.x,
            "y": pos.y,
            "yaw": _quaternion_para_yaw(ori.x, ori.y, ori.z, ori.w),
        })

    if not registros:
        return None

    return pd.DataFrame(registros)


# =============================================================================
# 2. MÉTRICAS DE UMA ÚNICA AMOSTRA
# =============================================================================

def calcular_metricas_amostra(df: pd.DataFrame, distancia_alvo: float,
                               df_real: "pd.DataFrame | None" = None) -> dict:
    """
    Calcula as métricas de uma única amostra a partir da série temporal de
    odometria. Segue as mesmas definições usadas no relatório original.

    Se df_real (pose real vinda de /gazebo/model_states) for fornecido,
    também calcula:
        - as mesmas métricas (e_y_final, e_x_final) usando a pose REAL
        - o drift da odometria: odom - real, ponto a ponto e no final

    Premissa da comparação: o frame de odometria e o frame do mundo (Gazebo)
    coincidem no instante inicial (robô acabou de ser resetado/spawnado).
    Isso é razoável logo após /reset_simulation, mas pode não valer se a
    odometria já acumula erro de orientação (yaw) desde o início — nesse
    caso o drift lateral calculado aqui é uma aproximação.
    """
    x0, y0 = df["x"].iloc[0], df["y"].iloc[0]
    x_f, y_f = df["x"].iloc[-1], df["y"].iloc[-1]

    e_y_serie = (df["y"] - y0).to_numpy()
    t = df["t"].to_numpy()

    distancia_percorrida = abs(x_f - x0)
    e_x_final = distancia_percorrida - distancia_alvo   # + passou além, - ficou aquém
    e_y_final = y_f - y0

    # IAE: integral do erro lateral absoluto ao longo do tempo (regra do trapézio)
    iae = float(np.trapz(np.abs(e_y_serie), t))

    overshoot_max = float(np.max(np.abs(e_y_serie)))
    cte_medio = float(np.mean(np.abs(e_y_serie)))

    metricas = {
        "e_y_final": float(e_y_final),
        "e_x_final": float(e_x_final),
        "iae": iae,
        "overshoot_max": overshoot_max,
        "cte_medio": cte_medio,
        "duracao_s": float(t[-1] - t[0]),
        "n_pontos": int(len(df)),
    }

    if df_real is not None and len(df_real) > 1:
        xr0, yr0 = df_real["x"].iloc[0], df_real["y"].iloc[0]
        xr_f, yr_f = df_real["x"].iloc[-1], df_real["y"].iloc[-1]
        tr = df_real["t"].to_numpy()

        e_y_serie_real = (df_real["y"] - yr0).to_numpy()
        distancia_percorrida_real = abs(xr_f - xr0)
        e_x_final_real = distancia_percorrida_real - distancia_alvo
        e_y_final_real = yr_f - yr0

        # Interpola a trajetória real nos instantes de tempo da odometria
        # (mesma base temporal) para comparar ponto a ponto
        e_y_real_interp = np.interp(t, tr, e_y_serie_real)
        drift_y_serie = e_y_serie - e_y_real_interp

        metricas.update({
            "e_y_final_real": float(e_y_final_real),
            "e_x_final_real": float(e_x_final_real),
            "odom_drift_y_final": float(e_y_final - e_y_final_real),
            "odom_drift_x_final": float(e_x_final - e_x_final_real),
            "odom_drift_y_rmse": float(np.sqrt(np.mean(drift_y_serie ** 2))),
            "odom_drift_y_max": float(np.max(np.abs(drift_y_serie))),
        })

    return metricas


# =============================================================================
# 3. AGREGAÇÃO SOBRE TODAS AS AMOSTRAS DE UM DIRETÓRIO
# =============================================================================

def processar_diretorio_amostras(dir_amostras: str, distancia_alvo: float = 5.0,
                                  padrao: str = "amostra*",
                                  robot_model_name: str = None) -> tuple[pd.DataFrame, dict]:
    """
    Processa todas as pastas de bag amostraN/ dentro de dir_amostras.

    robot_model_name: nome do modelo no Gazebo (ex.: "hemabot"), usado para
        extrair a pose real de /gazebo/model_states, se presente no bag.
        Se None, usa a variável de ambiente ROBOT_MODEL_NAME, ou "hemabot"
        como último fallback. Se o tópico não existir nos bags (gravações
        antigas), as métricas de drift simplesmente não são calculadas.

    Retorna:
        df_por_amostra : DataFrame com uma linha por amostra
        agregado       : dict com médias/desvios, no formato esperado por
                          gains_search.calcular_custo()
    """
    if robot_model_name is None:
        robot_model_name = os.environ.get("ROBOT_MODEL_NAME", "hemabot")

    pastas = sorted(
        glob.glob(os.path.join(dir_amostras, padrao)),
        key=lambda p: _extrair_indice_amostra(p)
    )
    # filtra só diretórios que realmente são bags (têm metadata.yaml)
    pastas = [p for p in pastas if os.path.isfile(os.path.join(p, "metadata.yaml"))]

    if not pastas:
        raise ValueError(f"Nenhuma pasta de bag encontrada em {dir_amostras} "
                          f"com padrão '{padrao}'")

    registros = []
    n_com_pose_real = 0
    for pasta in pastas:
        try:
            df_odom = ler_odom_do_bag(pasta)
            df_real = ler_pose_real_do_bag(pasta, robot_model_name)
            if df_real is not None:
                n_com_pose_real += 1
            metricas = calcular_metricas_amostra(df_odom, distancia_alvo, df_real=df_real)
            metricas["amostra"] = os.path.basename(pasta)
            registros.append(metricas)
        except Exception as e:
            print(f"  [AVISO] Falha ao processar {pasta}: {e}")

    if not registros:
        raise ValueError(f"Nenhuma amostra pôde ser processada em {dir_amostras}")

    df_por_amostra = pd.DataFrame(registros)

    agregado = {
        "e_y_final_medio": float(df_por_amostra["e_y_final"].mean()),
        "e_y_final_std": float(df_por_amostra["e_y_final"].std(ddof=1)) if len(df_por_amostra) > 1 else 0.0,
        "e_x_final_medio": float(df_por_amostra["e_x_final"].mean()),
        "e_x_final_std": float(df_por_amostra["e_x_final"].std(ddof=1)) if len(df_por_amostra) > 1 else 0.0,
        "iae_medio": float(df_por_amostra["iae"].mean()),
        "overshoot_max": float(df_por_amostra["overshoot_max"].max()),
        "n_amostras": int(len(df_por_amostra)),
    }

    if n_com_pose_real > 0:
        agregado["n_amostras_com_pose_real"] = n_com_pose_real
        for col in ("odom_drift_y_final", "odom_drift_x_final",
                    "odom_drift_y_rmse", "odom_drift_y_max"):
            if col in df_por_amostra.columns:
                serie = df_por_amostra[col].dropna()
                if len(serie):
                    agregado[f"{col}_medio"] = float(serie.mean())
                    agregado[f"{col}_std"] = float(serie.std(ddof=1)) if len(serie) > 1 else 0.0

    return df_por_amostra, agregado


def _extrair_indice_amostra(caminho_pasta: str) -> int:
    """Extrai o número N de uma pasta 'amostraN' para permitir ordenação numérica."""
    nome = os.path.basename(caminho_pasta.rstrip("/"))
    digitos = "".join(ch for ch in nome if ch.isdigit())
    return int(digitos) if digitos else 0


# =============================================================================
# 4. USO VIA LINHA DE COMANDO
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir_amostras", help="Diretório contendo as pastas amostraN/")
    parser.add_argument("--distancia", type=float, default=5.0,
                         help="Distância alvo da trajetória [m] (default: 5.0)")
    parser.add_argument("--modelo", default=None,
                         help="Nome do modelo no Gazebo, para ler a pose real de "
                              "/gazebo/model_states (default: $ROBOT_MODEL_NAME ou 'hemabot')")
    parser.add_argument("--saida", default=None,
                         help="Caminho do CSV de saída com métricas por amostra")
    args = parser.parse_args()

    df_amostras, agregado = processar_diretorio_amostras(
        args.dir_amostras, distancia_alvo=args.distancia, robot_model_name=args.modelo
    )

    print("\nMétricas por amostra:")
    print(df_amostras.to_string(index=False))

    print("\nAgregado:")
    for k, v in agregado.items():
        print(f"  {k}: {v}")

    if args.saida:
        df_amostras.to_csv(args.saida, index=False)
        print(f"\nCSV salvo em {args.saida}")

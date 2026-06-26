"""
Análise de métricas de odometria — robô diferencial
Trajetória de referência: eixo X (sentido +x)
Entrada: 3 arquivos .zip gerados pelo experimento.sh
         (amostras_0_25ms.zip, amostras_0_5ms.zip, amostras_1_0ms.zip)
         Cada zip contém amostra1/ … amostra30/, metadata.txt por amostra
         e resumo_experimento.txt na raiz.
"""

from rosbags.rosbag2 import Reader
from rosbags.serde import deserialize_cdr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
import zipfile
import tempfile
import shutil
import os

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

N_AMOSTRAS = 30

# Nomes dos zips gerados pelo experimento.sh (chave = label, valor = ficheiro)
# O label e a distância de referência são lidos do resumo_experimento.txt
# caso existam; caso contrário usam-se estes valores por defeito.
EXPERIMENTOS = {
    "0.25 m/s": "amostras_0_25ms.zip",
    "0.50 m/s": "amostras_0_5ms.zip",
    "1.00 m/s": "amostras_1_0ms.zip",
}

X_REF_DEFAULT = 5.0   # usado se resumo_experimento.txt não existir


# ─────────────────────────────────────────────
# LEITURA DE METADADOS
# ─────────────────────────────────────────────

def ler_metadata(caminho_txt):
    """Lê um ficheiro key=value e devolve um dicionário."""
    meta = {}
    if not os.path.exists(caminho_txt):
        return meta
    with open(caminho_txt) as f:
        for linha in f:
            linha = linha.strip()
            if "=" in linha:
                k, v = linha.split("=", 1)
                meta[k.strip()] = v.strip()
    return meta


def ler_resumo_experimento(pasta_raiz):
    """
    Lê resumo_experimento.txt gerado pelo .sh.
    Devolve (velocidade_ms: float, distancia_alvo_m: float, tempo_s: float).
    """
    caminho = os.path.join(pasta_raiz, "resumo_experimento.txt")
    meta = ler_metadata(caminho)
    vel   = float(meta.get("velocidade_ms",       0.0))
    dist  = float(meta.get("distancia_alvo_m",    X_REF_DEFAULT))
    tempo = float(meta.get("tempo_por_amostra_s", 0.0))
    return vel, dist, tempo


def ler_pose_inicial(caminho_txt):
    """
    Faz parsing do output de `ros2 topic echo /gazebo/model_states --once`.
    Este é YAML simples (lista de name/pose/twist), mas para evitar
    dependência extra fazemos parsing manual e robusto dos campos de
    posição e orientação do robô (segundo elemento de 'name', tipicamente
    o índice 1, pois o índice 0 costuma ser 'ground_plane').

    Devolve um dicionário:
        {"x": float, "y": float, "z": float,
         "qx": float, "qy": float, "qz": float, "qw": float,
         "yaw_deg": float}
    ou {} se não for possível interpretar o ficheiro.
    """
    if not os.path.exists(caminho_txt):
        return {}

    with open(caminho_txt) as f:
        linhas = f.readlines()

    # Procura blocos de 'pose:' -> 'position:' / 'orientation:'
    # Assume-se que o robô é o ÚLTIMO modelo não-estático listado
    # (tipicamente ground_plane vem primeiro). Para maior robustez,
    # guardamos TODOS os blocos de posição encontrados e devolvemos
    # o último (heurística: o robô costuma ser adicionado depois do
    # plano no SDF/world).
    posicoes = []
    pose_atual = {}
    dentro_de_position = False
    dentro_de_orientation = False

    for linha in linhas:
        l = linha.strip()

        if l.startswith("position:"):
            dentro_de_position, dentro_de_orientation = True, False
            pose_atual = {}
            continue
        if l.startswith("orientation:"):
            dentro_de_position, dentro_de_orientation = False, True
            continue
        if l.startswith("twist:") or l.startswith("name:") or l.startswith("- pose:"):
            dentro_de_position, dentro_de_orientation = False, False

        if dentro_de_position and ":" in l:
            k, v = l.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in ("x", "y", "z"):
                try:
                    pose_atual[k] = float(v)
                except ValueError:
                    pass

        if dentro_de_orientation and ":" in l:
            k, v = l.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in ("x", "y", "z", "w"):
                try:
                    pose_atual["q" + k] = float(v)
                except ValueError:
                    pass
            if {"x", "y", "z", "qx", "qy", "qz", "qw"}.issubset(pose_atual.keys()) or \
               all(k in pose_atual for k in ("x", "y", "qx", "qy", "qz", "qw")):
                posicoes.append(dict(pose_atual))

    if not posicoes:
        return {}

    pose = posicoes[-1]  # heurística: último bloco = robô (após ground_plane)

    # Calcula yaw a partir do quaternião (rotação em torno de Z)
    qx = pose.get("qx", 0.0)
    qy = pose.get("qy", 0.0)
    qz = pose.get("qz", 0.0)
    qw = pose.get("qw", 1.0)
    yaw_rad = np.arctan2(2.0 * (qw * qz + qx * qy),
                         1.0 - 2.0 * (qy * qy + qz * qz))
    pose["yaw_deg"] = np.degrees(yaw_rad)

    return pose


def validar_poses_iniciais(pasta_raiz, n_amostras, tolerancia_pos=0.01, tolerancia_yaw=1.0):
    """
    Lê pose_inicial.txt de cada amostra e verifica se a posição (x, y)
    e orientação (yaw) são consistentes entre todas as amostras.

    tolerancia_pos: tolerância em metros para x/y
    tolerancia_yaw: tolerância em graus para yaw

    Devolve: lista de dicionários de pose (uma por amostra, pode conter {}
              se não foi possível interpretar), e imprime diagnóstico.
    """
    poses = []
    for i in range(1, n_amostras + 1):
        caminho = os.path.join(pasta_raiz, f"amostra{i}", "pose_inicial.txt")
        poses.append(ler_pose_inicial(caminho))

    poses_validas = [p for p in poses if p]
    n_invalidas = n_amostras - len(poses_validas)

    print(f"\n{'─'*52}")
    print("  Validação da pose inicial (ground truth pós-reset)")
    print(f"{'─'*52}")

    if n_invalidas > 0:
        print(f"  ⚠  {n_invalidas}/{n_amostras} pose_inicial.txt não "
              f"puderam ser interpretados (ficheiro ausente ou formato inesperado)")

    if len(poses_validas) < 2:
        print("  ⚠  Dados insuficientes para validar repetibilidade da pose inicial")
        return poses

    xs   = np.array([p["x"]   for p in poses_validas])
    ys   = np.array([p["y"]   for p in poses_validas])
    yaws = np.array([p["yaw_deg"] for p in poses_validas])

    print(f"  x inicial   → média={np.mean(xs):+.4f} m  | σ={np.std(xs, ddof=1):.5f} m  "
          f"| range=[{np.min(xs):+.4f}, {np.max(xs):+.4f}]")
    print(f"  y inicial   → média={np.mean(ys):+.4f} m  | σ={np.std(ys, ddof=1):.5f} m  "
          f"| range=[{np.min(ys):+.4f}, {np.max(ys):+.4f}]")
    print(f"  yaw inicial → média={np.mean(yaws):+.4f}°  | σ={np.std(yaws, ddof=1):.5f}°  "
          f"| range=[{np.min(yaws):+.4f}, {np.max(yaws):+.4f}]")

    pos_spread = max(np.max(xs) - np.min(xs), np.max(ys) - np.min(ys))
    yaw_spread = np.max(yaws) - np.min(yaws)

    if pos_spread > tolerancia_pos:
        print(f"  ⚠  Posição inicial NÃO é repetível entre amostras "
              f"(spread={pos_spread:.4f} m > tolerância {tolerancia_pos} m)")
    else:
        print(f"  ✓  Posição inicial repetível dentro da tolerância ({tolerancia_pos} m)")

    if yaw_spread > tolerancia_yaw:
        print(f"  ⚠  Orientação (yaw) inicial NÃO é repetível entre amostras "
              f"(spread={yaw_spread:.4f}° > tolerância {tolerancia_yaw}°)")
        print(f"     → Um yaw inicial não-nulo explica diretamente o viés lateral "
              f"sistemático observado!")
    else:
        print(f"  ✓  Orientação inicial repetível dentro da tolerância ({tolerancia_yaw}°)")

    return poses


# ─────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────

def resumo(nome, vetor):
    mu    = np.mean(vetor)
    sigma = np.std(vetor, ddof=1)
    rmse  = np.sqrt(np.mean(vetor**2))
    cv    = sigma / abs(mu) if abs(mu) > 1e-9 else float('inf')
    vmax  = np.max(np.abs(vetor))
    ci95  = stats.t.interval(0.95, df=len(vetor)-1,
                             loc=mu, scale=stats.sem(vetor))
    print(f"\n{'─'*52}")
    print(f"  {nome}")
    print(f"{'─'*52}")
    print(f"  Média (bias)      : {mu:+.4f} m")
    print(f"  Desvio padrão (σ) : {sigma:.4f} m")
    print(f"  RMSE              : {rmse:.4f} m")
    print(f"  Máximo absoluto   : {vmax:.4f} m")
    print(f"  Coef. variação    : {cv:.2f}")
    print(f"  IC 95%            : [{ci95[0]:+.4f}, {ci95[1]:+.4f}] m")
    return dict(mu=mu, sigma=sigma, rmse=rmse, cv=cv, vmax=vmax, ci95=ci95)


def carregar_amostras(pasta_raiz, n_amostras=N_AMOSTRAS):
    """
    Lê amostra1/ … amostraN/ dentro de pasta_raiz.
    Lê /odom e /cmd_vel de cada bag.
    Também lê metadata.txt de cada amostra para validação.
    Devolve:
        todas_odom_x, todas_odom_y  — listas de arrays de posição
        todas_vel_cmd               — lista de velocidades lidas do /cmd_vel
        todas_meta                  — lista de dicionários metadata por amostra
    """
    todas_odom_x  = []
    todas_odom_y  = []
    todas_vel_cmd = []
    todas_meta    = []

    for i in range(1, n_amostras + 1):
        amostra_dir = os.path.join(pasta_raiz, f"amostra{i}")
        bag_path = os.path.join(amostra_dir, "bag")
        odom_x, odom_y, vel_cmd = [], [], []

        with Reader(bag_path) as reader:
            for connection, timestamp, rawdata in reader.messages():
                if connection.topic == '/odom':
                    msg = deserialize_cdr(rawdata, connection.msgtype)
                    odom_x.append(msg.pose.pose.position.x)
                    odom_y.append(msg.pose.pose.position.y)
                elif connection.topic == '/cmd_vel':
                    msg = deserialize_cdr(rawdata, connection.msgtype)
                    vel_cmd.append(msg.linear.x)

        # Lê metadata.txt da amostra
        meta_path = os.path.join(bag_path, "metadata.txt")
        meta = ler_metadata(meta_path)
        todas_meta.append(meta)

        # Valida velocidade: metadata vs cmd_vel gravado
        if meta and vel_cmd:
            vel_meta = float(meta.get("velocidade_ms", 0.0))
            vel_real = float(np.median(vel_cmd))
            if abs(vel_meta - vel_real) > 0.01:
                print(f"  ⚠  Amostra {i}: velocidade metadata={vel_meta} "
                      f"vs cmd_vel mediana={vel_real:.3f} — verifique!")

        todas_odom_x.append(np.array(odom_x))
        todas_odom_y.append(np.array(odom_y))
        todas_vel_cmd.append(np.array(vel_cmd) if vel_cmd else np.array([0.0]))

    return todas_odom_x, todas_odom_y, todas_vel_cmd, todas_meta


def calcular_metricas(todas_odom_x, todas_odom_y, x_ref):
    erros_laterais      = []
    erros_longitudinais = []
    erros_posicao       = []
    cte_medio           = []
    cte_max_lista       = []
    iae_lista           = []

    for odom_x, odom_y in zip(todas_odom_x, todas_odom_y):
        x_inicio  = odom_x[0]
        e_y_final = odom_y[-1]
        e_x_final = (odom_x[-1] - x_inicio) - x_ref
        e_p_final = np.sqrt(e_x_final**2 + e_y_final**2)

        erros_laterais.append(e_y_final)
        erros_longitudinais.append(e_x_final)
        erros_posicao.append(e_p_final)

        cte = np.abs(odom_y)
        cte_medio.append(np.mean(cte))
        cte_max_lista.append(np.max(cte))

        dist_percorrida = np.cumsum(
            np.sqrt(np.diff(odom_x, prepend=odom_x[0])**2 +
                    np.diff(odom_y, prepend=odom_y[0])**2)
        )
        iae_lista.append(np.trapz(cte, dist_percorrida))

    return (np.array(erros_laterais),
            np.array(erros_longitudinais),
            np.array(erros_posicao),
            np.array(cte_medio),
            np.array(cte_max_lista),
            np.array(iae_lista))


# ─────────────────────────────────────────────
# RELATÓRIO GRÁFICO
# ─────────────────────────────────────────────

def gerar_relatorio(label, x_ref, vel_ms, tempo_s,
                    todas_odom_x, todas_odom_y,
                    erros_laterais, erros_longitudinais, erros_posicao,
                    cte_medio, cte_max_lista, iae_lista,
                    m_lateral, m_longit, m_posicao, m_cte, m_cte_max,
                    n_amostras=N_AMOSTRAS):

    CINZA    = "#888780"
    AZUL     = "#378ADD"
    LARANJA  = "#EF9F27"
    VERMELHO = "#E24B4A"
    VERDE    = "#639922"

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor":   "white",
        "axes.spines.top":  False,
        "axes.spines.right":False,
        "axes.grid":        True,
        "grid.alpha":       0.35,
        "grid.linewidth":   0.5,
        "font.size":        11,
    })

    fig = plt.figure(figsize=(16, 18))
    subtitulo = (f"Análise de Odometria — Robô Diferencial  |  v = {label}  "
                 f"({n_amostras} amostras)  |  dist = {x_ref} m  |  t = {tempo_s:.2f} s")
    fig.suptitle(subtitulo, fontsize=13, y=0.99)

    gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.50, wspace=0.38)
    amostras = np.arange(1, n_amostras + 1)

    # 1 — Trajetórias sobrepostas
    ax1 = fig.add_subplot(gs[0, :2])
    for ox, oy in zip(todas_odom_x, todas_odom_y):
        ax1.plot(ox, oy, color=AZUL, alpha=0.35, linewidth=0.8)
    ax1.axhline(0, color=VERMELHO, linewidth=1.5, linestyle="--", label="Referência (y = 0)")
    ax1.set_xlabel("x [m]"); ax1.set_ylabel("y [m]")
    ax1.set_title("Trajetórias sobrepostas (odometria)")
    ax1.legend(fontsize=9)

    # 2 — Erro lateral final por amostra
    ax2 = fig.add_subplot(gs[0, 2])
    cores_y = [VERMELHO if e > 0 else AZUL for e in erros_laterais]
    ax2.bar(amostras, erros_laterais, color=cores_y, alpha=0.8, width=0.7)
    ax2.axhline(m_lateral["mu"], color=LARANJA, linewidth=1.5, linestyle="--",
                label=f"Média = {m_lateral['mu']:+.3f} m")
    ax2.axhline(0, color=CINZA, linewidth=0.8)
    ax2.set_xlabel("Amostra"); ax2.set_ylabel("e_y final [m]")
    ax2.set_title("Erro lateral final por amostra")
    ax2.legend(fontsize=9)

    # 3 — Erro longitudinal final
    ax3 = fig.add_subplot(gs[1, :2])
    cores_x = [VERDE if e > 0 else VERMELHO for e in erros_longitudinais]
    ax3.bar(amostras, erros_longitudinais, color=cores_x, alpha=0.8, width=0.7)
    ax3.axhline(m_longit["mu"], color=LARANJA, linewidth=1.5, linestyle="--",
                label=f"Média = {m_longit['mu']:+.3f} m")
    ax3.axhline(0, color=CINZA, linewidth=0.8)
    ax3.axhspan(m_longit["mu"] - m_longit["sigma"],
                m_longit["mu"] + m_longit["sigma"],
                alpha=0.10, color=LARANJA, label=f"±1σ = {m_longit['sigma']:.3f} m")
    ax3.set_xlabel("Amostra")
    ax3.set_ylabel("e_x final [m]  (+ passou além, − ficou aquém)")
    ax3.set_title(f"Erro longitudinal final por amostra  (referência = {x_ref} m)")
    ax3.legend(fontsize=9)

    # 4 — Histograma longitudinal
    ax_hx = fig.add_subplot(gs[1, 2])
    ax_hx.hist(erros_longitudinais, bins=10, color=VERDE, alpha=0.75, edgecolor="white")
    ax_hx.axvline(m_longit["mu"], color=LARANJA, linewidth=1.5, linestyle="--",
                  label=f"μ = {m_longit['mu']:+.3f} m")
    ax_hx.axvline(0, color=CINZA, linewidth=0.8)
    ax_hx.set_xlabel("e_x final [m]"); ax_hx.set_ylabel("Frequência")
    ax_hx.set_title("Distribuição do erro longitudinal")
    ax_hx.legend(fontsize=9)

    # 5 — Histograma lateral
    ax_hy = fig.add_subplot(gs[2, 0])
    ax_hy.hist(erros_laterais, bins=10, color=AZUL, alpha=0.75, edgecolor="white")
    ax_hy.axvline(m_lateral["mu"], color=LARANJA, linewidth=1.5, linestyle="--",
                  label=f"μ = {m_lateral['mu']:+.3f} m")
    ax_hy.axvline(0, color=CINZA, linewidth=0.8)
    ax_hy.set_xlabel("e_y final [m]"); ax_hy.set_ylabel("Frequência")
    ax_hy.set_title("Distribuição do erro lateral")
    ax_hy.legend(fontsize=9)

    # 6 — CTE médio por amostra
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.bar(amostras, cte_medio, color=VERDE, alpha=0.8, width=0.7)
    ax4.axhline(np.mean(cte_medio), color=LARANJA, linewidth=1.5, linestyle="--",
                label=f"Média = {np.mean(cte_medio):.3f} m")
    ax4.set_xlabel("Amostra"); ax4.set_ylabel("Erro Lateral médio [m]")
    ax4.set_title("Erro Lateral médio por amostra")
    ax4.legend(fontsize=9)

    # 7 — Perfil de acúmulo do CTE
    ax5 = fig.add_subplot(gs[2, 2])
    x_comum = np.linspace(0, 1, 200)
    cte_interp = []
    for ox, oy in zip(todas_odom_x, todas_odom_y):
        x_range = ox[-1] - ox[0]
        x_norm = (ox - ox[0]) / (x_range if x_range > 1e-9 else 1.0)
        cte_interp.append(np.interp(x_comum, x_norm, np.abs(oy)))
    cte_matrix     = np.array(cte_interp)
    cte_mean_curve = np.mean(cte_matrix, axis=0)
    cte_std_curve  = np.std(cte_matrix, axis=0, ddof=1)
    ax5.fill_between(x_comum,
                     cte_mean_curve - cte_std_curve,
                     cte_mean_curve + cte_std_curve,
                     alpha=0.25, color=AZUL, label="±1σ")
    ax5.plot(x_comum, cte_mean_curve, color=AZUL, linewidth=1.8, label="CTE médio")
    ax5.set_xlabel("Progresso normalizado da trajetória")
    ax5.set_ylabel("|CTE| [m]")
    ax5.set_title("Perfil de acúmulo do CTE")
    ax5.legend(fontsize=9)

    # 8 — Box-plot
    ax6 = fig.add_subplot(gs[3, 0])
    dados_bp  = [np.abs(erros_laterais), np.abs(erros_longitudinais),
                 erros_posicao, cte_medio, cte_max_lista]
    labels_bp = ["e_y\nfinal", "e_x\nfinal", "e_p\nfinal", "CTE\nmédio", "CTE\nmáx"]
    bp = ax6.boxplot(dados_bp, labels=labels_bp, patch_artist=True, widths=0.5,
                     medianprops=dict(color=VERMELHO, linewidth=2))
    for patch, cor in zip(bp["boxes"], [AZUL, VERDE, "#9B59B6", LARANJA, VERMELHO]):
        patch.set_facecolor(cor); patch.set_alpha(0.6)
    ax6.set_ylabel("[m]"); ax6.set_title("Box-plot das métricas de erro")

    # 9 — IAE por amostra
    ax7 = fig.add_subplot(gs[3, 1])
    ax7.bar(amostras, iae_lista, color=LARANJA, alpha=0.8, width=0.7)
    ax7.axhline(np.mean(iae_lista), color=VERMELHO, linewidth=1.5, linestyle="--",
                label=f"Média = {np.mean(iae_lista):.3f} m²")
    ax7.set_xlabel("Amostra"); ax7.set_ylabel("IAE [m²]")
    ax7.set_title("IAE por amostra")
    ax7.legend(fontsize=9)

    # 10 — Tabela resumo (inclui velocidade e tempo do .sh)
    ax8 = fig.add_subplot(gs[3, 2])
    ax8.axis("off")
    linhas = [
        ["Métrica",           "Média",                              "σ",                                   "RMSE"],
        ["v cmd [m/s]",       f"{vel_ms:.2f}",                      "—",                                   "—"],
        ["t mov. [s]",        f"{tempo_s:.2f}",                     "—",                                   "—"],
        ["e_y final [m]",     f"{m_lateral['mu']:+.4f}",            f"{m_lateral['sigma']:.4f}",           f"{m_lateral['rmse']:.4f}"],
        ["e_x final [m]",     f"{m_longit['mu']:+.4f}",             f"{m_longit['sigma']:.4f}",            f"{m_longit['rmse']:.4f}"],
        ["e_p final [m]",     f"{m_posicao['mu']:.4f}",             f"{m_posicao['sigma']:.4f}",           f"{m_posicao['rmse']:.4f}"],
        ["CTE médio [m]",     f"{m_cte['mu']:.4f}",                 f"{m_cte['sigma']:.4f}",               f"{m_cte['rmse']:.4f}"],
        ["CTE máx [m]",       f"{m_cte_max['mu']:.4f}",             f"{m_cte_max['sigma']:.4f}",           f"{m_cte_max['rmse']:.4f}"],
        ["IAE [m²]",          f"{np.mean(iae_lista):.4f}",          f"{np.std(iae_lista, ddof=1):.4f}",    "—"],
    ]
    tabela = ax8.table(cellText=linhas[1:], colLabels=linhas[0],
                       cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
    tabela.auto_set_font_size(False); tabela.set_fontsize(9)
    for (r, c), cell in tabela.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor("#378ADD"); cell.set_text_props(color="white", fontweight="bold")
        elif r in (1, 2):
            cell.set_facecolor("#FFF8E1")   # destaque para linhas de parâmetros do .sh
        elif r == 4:
            cell.set_facecolor("#E8F5E9")
        else:
            cell.set_facecolor("white" if r % 2 == 0 else "#F1EFE8")
    ax8.set_title("Resumo estatístico", pad=10)

    # Salva
    nome_arquivo = f"analise_odometria_{label.replace(' ', '').replace('/', '')}.png"
    plt.savefig(nome_arquivo, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n✓  Relatório salvo em: {nome_arquivo}")
    return nome_arquivo


# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────

for label, zip_path in EXPERIMENTOS.items():

    if not os.path.exists(zip_path):
        print(f"\n⚠  Arquivo não encontrado, pulando: {zip_path}")
        continue

    print("\n" + "═"*52)
    print(f"  VELOCIDADE: {label}  →  {zip_path}")
    print("═"*52)

    label_seguro = label.replace(' ', '_').replace('/', 'ps').replace('.', '_')
    tmp_dir = tempfile.mkdtemp(prefix=f"odom_{label_seguro}_")

    try:
        print(f"  Descompactando em {tmp_dir} ...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)

        # Desce um nível se o zip criou subpasta única
        conteudo = os.listdir(tmp_dir)
        if len(conteudo) == 1 and os.path.isdir(os.path.join(tmp_dir, conteudo[0])):
            pasta_raiz = os.path.join(tmp_dir, conteudo[0])
        else:
            pasta_raiz = tmp_dir

        # Lê parâmetros do experimento gerados pelo .sh
        vel_ms, x_ref, tempo_s = ler_resumo_experimento(pasta_raiz)
        if vel_ms == 0.0:
            # Fallback: extrai velocidade do label
            vel_ms = float(label.split()[0])
            x_ref  = X_REF_DEFAULT
            tempo_s = x_ref / vel_ms if vel_ms > 0 else 0.0
            print(f"  ⚠  resumo_experimento.txt não encontrado — usando valores por defeito")

        print(f"  Parâmetros lidos do .sh:")
        print(f"    velocidade     = {vel_ms} m/s")
        print(f"    distância alvo = {x_ref} m")
        print(f"    tempo mov.     = {tempo_s} s")

        # Valida repetibilidade da pose inicial (ground truth pós-reset)
        validar_poses_iniciais(pasta_raiz, N_AMOSTRAS)

        # Carrega bags (odom + cmd_vel + metadata)
        todas_odom_x, todas_odom_y, todas_vel_cmd, todas_meta = \
            carregar_amostras(pasta_raiz, N_AMOSTRAS)

        # Calcula métricas com x_ref lido do .sh
        (erros_laterais, erros_longitudinais, erros_posicao,
         cte_medio, cte_max_lista, iae_lista) = \
            calcular_metricas(todas_odom_x, todas_odom_y, x_ref)

        # Resumo no terminal
        print(f"\n{'═'*52}")
        print(f"  RESUMO ESTATÍSTICO — {label}")
        print(f"{'═'*52}")
        m_lateral  = resumo("Erro lateral final  e_y  [m]", erros_laterais)
        m_longit   = resumo(f"Erro longitudinal final e_x [m]  (ref = {x_ref} m)", erros_longitudinais)
        m_posicao  = resumo("Erro de posição total e_p [m]", erros_posicao)
        m_cte      = resumo("EL médio por trajetória [m]", cte_medio)
        m_cte_max  = resumo("EL máximo por trajetória [m]", cte_max_lista)

        print(f"\n{'─'*52}")
        print("  IAE [m²]")
        print(f"{'─'*52}")
        print(f"  Média : {np.mean(iae_lista):.4f} m²   σ : {np.std(iae_lista, ddof=1):.4f} m²")

        # Diagnósticos
        n_dir = np.sum(erros_laterais > 0)
        n_esq = np.sum(erros_laterais < 0)
        print(f"\n  Viés direcional → +y: {n_dir}/{N_AMOSTRAS}  |  -y: {n_esq}/{N_AMOSTRAS}")
        if max(n_dir, n_esq) / N_AMOSTRAS > 0.6:
            print("  ⚠  Viés direcional detectado")
        else:
            print("  ✓  Sem viés direcional significativo")

        bias_pct = m_longit["mu"] / x_ref * 100
        print(f"  Bias longitudinal: {m_longit['mu']:+.4f} m  ({bias_pct:+.2f}%)")
        if abs(m_longit["mu"]) > 0.02:
            print("  ⚠  Bias longitudinal significativo")
        else:
            print("  ✓  Bias longitudinal dentro de ±2 cm")

        # Validação cruzada: velocidade cmd_vel vs metadata
        vel_mediana_cmd = float(np.median(np.concatenate(todas_vel_cmd)))
        print(f"\n  Velocidade cmd_vel (mediana global): {vel_mediana_cmd:.3f} m/s")
        if abs(vel_mediana_cmd - vel_ms) > 0.01:
            print(f"  ⚠  Divergência entre cmd_vel ({vel_mediana_cmd:.3f}) "
                  f"e resumo_experimento ({vel_ms}) — verifique o .sh")
        else:
            print(f"  ✓  Velocidade cmd_vel consistente com resumo_experimento.txt")

        # Gera relatório gráfico
        gerar_relatorio(label, x_ref, vel_ms, tempo_s,
                        todas_odom_x, todas_odom_y,
                        erros_laterais, erros_longitudinais, erros_posicao,
                        cte_medio, cte_max_lista, iae_lista,
                        m_lateral, m_longit, m_posicao, m_cte, m_cte_max,
                        N_AMOSTRAS)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

print("\n✓  Análise completa para todas as velocidades.")

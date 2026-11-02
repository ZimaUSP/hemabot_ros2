#!/usr/bin/env python3
"""Gera um DOCX autocontido com o plano de continuidade do HemaBot.

Usa somente a biblioteca-padrão para que o artefato possa ser reproduzido
mesmo quando python-docx/LibreOffice não estão instalados.
"""

from __future__ import annotations

import os
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape


OUT_DIR = "documentos"
OUT_FILE = os.path.join(OUT_DIR, "Proximos_passos_HemaBot_curvas_e_ambiente_hospitalar.docx")

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def x(text: object) -> str:
    return escape(str(text), {'"': '&quot;'})


def run(text: str, *, bold=False, italic=False, color=None, size=None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if size:
        props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    return f"<w:r>{rpr}<w:t{preserve}>{x(text)}</w:t></w:r>"


def paragraph(text="", style=None, *, bold=False, italic=False, align=None,
              before=None, after=None, keep=False, page_break_before=False,
              color=None, size=None) -> str:
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if before is not None or after is not None:
        attrs = []
        if before is not None:
            attrs.append(f'w:before="{before}"')
        if after is not None:
            attrs.append(f'w:after="{after}"')
        ppr.append(f"<w:spacing {' '.join(attrs)}/>")
    if keep:
        ppr.append("<w:keepNext/>")
    if page_break_before:
        ppr.append("<w:pageBreakBefore/>")
    ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr_xml}{run(text, bold=bold, italic=italic, color=color, size=size)}</w:p>"


def rich_paragraph(parts, style=None, *, align=None, after=None) -> str:
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if after is not None:
        ppr.append(f'<w:spacing w:after="{after}"/>')
    body = []
    for part in parts:
        if isinstance(part, str):
            body.append(run(part))
        else:
            text, opts = part
            body.append(run(text, **opts))
    return f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{''.join(body)}</w:p>"


def bullet(text: str, level=0) -> str:
    return (
        "<w:p><w:pPr><w:pStyle w:val=\"ListParagraph\"/>"
        f"<w:numPr><w:ilvl w:val=\"{level}\"/><w:numId w:val=\"1\"/></w:numPr>"
        "<w:spacing w:after=\"80\"/></w:pPr>" + run(text) + "</w:p>"
    )


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def cell(content, width, *, header=False, shade=None, align=None) -> str:
    if not isinstance(content, list):
        content = [paragraph(str(content), bold=header, align=align, after=40)]
    fill = shade or ("1F4E78" if header else None)
    tcpr = [f'<w:tcW w:w="{width}" w:type="dxa"/>', '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>']
    if fill:
        tcpr.append(f'<w:shd w:fill="{fill}"/>')
    if header:
        colored = []
        for item in content:
            # Cabeçalhos simples são reconstruídos para texto branco.
            if "<w:t" in item:
                start = item.find(">", item.find("<w:t")) + 1
                end = item.find("</w:t>", start)
                txt = item[start:end]
                colored.append(paragraph(txt, bold=True, color="FFFFFF", align=align, after=40))
            else:
                colored.append(item)
        content = colored
    return f"<w:tc><w:tcPr>{''.join(tcpr)}</w:tcPr>{''.join(content)}</w:tc>"


def table(headers, rows, widths) -> str:
    borders = (
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="B7C9D6"/>'
        '<w:left w:val="single" w:sz="4" w:color="B7C9D6"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="B7C9D6"/>'
        '<w:right w:val="single" w:sz="4" w:color="B7C9D6"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="D5E2EA"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="D5E2EA"/></w:tblBorders>'
    )
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblLayout w:type="fixed"/>{borders}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    out.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>' + ''.join(cell(h, w, header=True) for h, w in zip(headers, widths)) + '</w:tr>')
    for idx, row in enumerate(rows):
        shade = "F2F6F8" if idx % 2 else None
        out.append('<w:tr>' + ''.join(cell(v, w, shade=shade) for v, w in zip(row, widths)) + '</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out) + paragraph("", after=80)


def hyperlink(url: str, label: str, rid: str) -> str:
    return (
        f'<w:hyperlink r:id="{rid}" w:history="1"><w:r><w:rPr>'
        '<w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr>'
        f'<w:t>{x(label)}</w:t></w:r></w:hyperlink>'
    )


def reference(number, citation, relevance, url, rid):
    return (
        f'<w:p><w:pPr><w:spacing w:after="70" w:line="260" w:lineRule="auto"/></w:pPr>'
        + run(f"[{number}] ", bold=True, color="1F4E78")
        + run(citation)
        + run("  ") + hyperlink(url, "Acesso", rid) + "</w:p>"
        + paragraph("Uso no projeto: " + relevance, style="Annotation")
    )


def build_document():
    body = []

    # Capa
    body += [
        paragraph("POLI – USP", style="CoverKicker", align="center", after=900),
        paragraph("PRÓXIMOS PASSOS DO PROJETO HEMABOT", style="Title", align="center", after=260),
        paragraph("Do rastreamento retilíneo ao controle em curvas e à validação em ambiente hospitalar", style="Subtitle", align="center", after=900),
        paragraph("Plano técnico-científico e bibliografia comentada", style="CoverKicker", align="center", after=800),
        paragraph("Lucas Fernando Neres Miranda", bold=True, align="center", size=25, after=100),
        paragraph("Orientador: Prof. Dr. Leopoldo Rideki Yoshioka", align="center", after=120),
        paragraph("Grupo de extensão Zima · Hospital Universitário (HU)", align="center", after=100),
        paragraph("Outubro de 2026", align="center", color="58636B", after=80),
        page_break(),
    ]

    body += [
        paragraph("Resumo executivo", style="Heading1"),
        paragraph(
            "O trabalho atual demonstrou, em simulação e em uma trajetória retilínea de 5 m, que a fusão de odometria e IMU por EKF pode melhorar o rastreamento lateral, mas não apresentou a mesma vantagem no erro longitudinal. A continuação recomendada é transformar essa análise pontual em um estudo de robustez e aplicabilidade: trajetórias com curvatura, comparação controlada entre estimadores e seguidores de caminho, validação no robô físico e ensaios progressivamente próximos da rotina hospitalar."
        ),
        paragraph(
            "A pergunta científica central proposta é: em quais condições de curvatura, velocidade, carga e interação com pessoas a estimação por EKF melhora a precisão e a confiabilidade do rastreamento de um robô diferencial destinado ao transporte de amostras clínicas?"
        ),
        paragraph("Recomendação principal", style="Heading2"),
        paragraph(
            "Adotar um protocolo em etapas, mantendo o PID/PD atual como linha de base e incluindo ao menos um seguidor geométrico adequado a curvas — preferencialmente Regulated Pure Pursuit, por ter implementação de referência no ROS 2/Nav2 — e Stanley como comparador acadêmico. O EKF deve ser tratado como fator experimental independente, com a mesma lei de controle, critério de parada e trajetória em cada comparação."
        ),
        paragraph("Resultado esperado em 12 meses", style="Heading2"),
        bullet("Pipeline reproduzível de ensaios em curvas, com configuração, rosbag, ground truth e análise versionados."),
        bullet("Comparação PID/PD, Stanley e Regulated Pure Pursuit, com e sem EKF, em simulação e no protótipo."),
        bullet("Demonstração hospitalar em corredor controlado, com obstáculos estáticos e pessoas, carga instrumentada e procedimento de segurança."),
        bullet("Artigo com contribuição centrada na interação entre estimação, curvatura e confiabilidade operacional."),
        paragraph("Sumário", style="Heading2"),
        paragraph("1. Ponto de partida e lacunas · 2. Questões e hipóteses · 3. Arquitetura experimental · 4. Trajetórias e cenários · 5. Métricas e estatística · 6. Aproximação ao hospital · 7. Plano de execução · 8. Riscos · 9. Entregáveis · 10. Papers relacionados"),
    ]

    # 1
    body += [page_break(), paragraph("1. Ponto de partida e lacunas", style="Heading1")]
    body.append(paragraph("O estudo anterior oferece uma boa linha de base, mas as conclusões ainda são específicas para movimento retilíneo, baixa velocidade e simulação. Em curvas, o erro lateral deixa de ser simplesmente yref − y e deve ser definido em relação ao caminho, normalmente como erro transversal ao segmento mais próximo, acompanhado do erro de orientação e da progressão ao longo do caminho."))
    body.append(table(
        ["Lacuna", "Por que importa", "Ação proposta"],
        [
            ["Controlador dependente do eixo global", "Não generaliza para arcos, curvas em S ou caminhos rotacionados.", "Representar o caminho por poses/curvatura e calcular erros no referencial de Frenet ou do segmento local."],
            ["Efeito do EKF confundido com o controle", "Troca simultânea de fonte de pose, critério de parada ou ganhos impede atribuir causalidade.", "Experimento fatorial: estimador ligado/desligado mantendo controlador, caminho, limites e terminação iguais."],
            ["Apenas MAE/RMSE finais", "Médias escondem picos, oscilações, falhas e proximidade perigosa.", "Incluir erro máximo, percentil 95, orientação, suavidade, controle, taxa de sucesso e eventos de segurança."],
            ["Somente simulação", "Não captura folga, escorregamento, atraso, vibração e irregularidade do piso.", "Validação escalonada: simulação → laboratório → corredor hospitalar controlado."],
            ["Pouca conexão com o fluxo clínico", "Precisão geométrica não garante utilidade ou segurança hospitalar.", "Medir tempo de entrega, integridade da carga, rastreabilidade, higienização, disponibilidade e aceitação da equipe."],
        ], [1900, 3000, 3900]
    ))
    body.append(paragraph("Antes de novos ensaios, é essencial auditar a arquitetura ROS 2: usar tópicos separados para odometria bruta e filtrada; confirmar qual pose alimenta o controlador; impedir realimentação da saída do EKF; registrar TF, parâmetros efetivos, frequências e atrasos; e adotar o mesmo critério de término em todos os métodos."))

    # 2
    body += [paragraph("2. Questões de pesquisa e hipóteses", style="Heading1")]
    body.append(table(
        ["Questão", "Hipótese testável", "Evidência necessária"],
        [
            ["Q1. O EKF melhora o seguimento em curvas?", "H1: reduz erro transversal e angular sobretudo em curvas de maior curvatura ou com ruído/escorregamento, mas pode aumentar atraso e erro de progressão se mal ajustado.", "Comparar pose estimada com ground truth e rastreamento sob o mesmo controlador."],
            ["Q2. Qual controlador é mais adequado ao HemaBot?", "H2: seguidores geométricos superam o PD de reta em curvas; a regulação de velocidade melhora suavidade e segurança.", "PID/PD, Stanley e RPP sob trajetórias, velocidades e limites idênticos."],
            ["Q3. O ganho permanece no protótipo?", "H3: a ordenação dos métodos se mantém, mas erros crescem por dinâmica não modelada e piso.", "Ensaios pareados em simulação e no robô com referência externa."],
            ["Q4. O sistema é operacionalmente viável no hospital?", "H4: velocidades adaptadas à curvatura e à proximidade de pessoas elevam a confiabilidade sem tornar a entrega excessivamente lenta.", "Sucesso de missão, tempo, near misses, intervenções, integridade da carga e percepção de usuários."],
        ], [1900, 3900, 3000]
    ))
    body.append(paragraph("Contribuição científica sugerida", style="Heading2"))
    body.append(paragraph("Um estudo reproduzível sobre como a estimação de estado afeta precisão, estabilidade e confiabilidade de seguidores de caminho em um robô diferencial de logística hospitalar, incluindo curvas, falhas e transferência simulação–protótipo. A novidade não deve ser apresentada como a simples aplicação de algoritmos conhecidos, mas como a caracterização experimental de suas interações e limites em um caso hospitalar."))

    # 3
    body += [paragraph("3. Arquitetura experimental recomendada", style="Heading1")]
    body.append(paragraph("3.1 Controladores", style="Heading2"))
    body.append(table(
        ["Método", "Papel no estudo", "Cuidados de comparação"],
        [
            ["PD/PID atual", "Linha de base e continuidade com a iniciação científica.", "Generalizar o erro para o caminho; documentar que Ki=0 caracteriza PD; usar anti-windup se Ki>0."],
            ["Stanley", "Comparador baseado em erro transversal e erro de orientação.", "Adaptar conscientemente ao robô diferencial; regular baixa velocidade e limitar velocidade angular."],
            ["Pure Pursuit", "Referência geométrica simples, interpretável e adequada a arcos.", "Avaliar lookahead fixo/adaptativo e efeito da velocidade."],
            ["Regulated Pure Pursuit (RPP)", "Candidato principal para protótipo e integração Nav2.", "Congelar versão/parâmetros; separar regulação de velocidade do efeito da estimação."],
            ["MPC, etapa opcional", "Extensão para restrições, obstáculos e pesquisa futura.", "Só incluir após as linhas de base; medir tempo computacional e perdas de deadline na Raspberry Pi."],
        ], [2100, 3100, 3600]
    ))
    body.append(paragraph("A comparação mínima publicável pode ser PD versus Stanley versus RPP. O Pure Pursuit básico é útil na fase de desenvolvimento, mas pode ser omitido do experimento final se o número de condições ficar excessivo."))
    body.append(paragraph("3.2 Estimação e referência", style="Heading2"))
    body += [
        bullet("Fator E0: odometria bruta de encoders, sem EKF."),
        bullet("Fator E1: EKF com encoders + IMU, covariâncias calibradas e timestamps verificados."),
        bullet("Extensão E2: EKF com fonte absoluta ou correção de mapa, caso haja LiDAR/SLAM confiável; não misturar essa extensão com a comparação principal."),
        bullet("Referência independente: ground truth do Gazebo na simulação; no físico, mocap, câmera superior calibrada com marcadores ou estação total. A precisão da referência deve ser menor que a diferença que se pretende detectar."),
        bullet("Avaliar o estimador separadamente por ATE/RPE, erro de yaw, atraso efetivo, inovações e consistência; depois avaliar o efeito fechado no controlador."),
    ]
    body.append(paragraph("3.3 Fatores controlados", style="Heading2"))
    body.append(table(
        ["Fator", "Níveis iniciais", "Motivação"],
        [
            ["Velocidade", "0,15; 0,25; 0,40 m/s", "Captura o compromisso entre tempo, erro e segurança."],
            ["Carga", "vazio; carga nominal; carga nominal deslocada", "Revela inércia, assimetria e risco de instabilidade do compartimento."],
            ["Curvatura", "reta; R=2,0 m; R=1,0 m; R=0,6 m", "Identifica o limite geométrico e de saturação angular."],
            ["Piso", "regular; junta/irregularidade controlada", "Testa escorregamento, vibração e transferência ao ambiente real."],
            ["Dinâmica humana", "sem pessoa; cruzamento; ultrapassagem; corredor parcialmente bloqueado", "Representa interações frequentes em corredores hospitalares."],
        ], [1800, 3000, 4000]
    ))

    # 4
    body += [page_break(), paragraph("4. Banco de trajetórias e cenários", style="Heading1")]
    body.append(paragraph("Usar trajetórias parametrizadas e reproduzíveis, com comprimento, curvatura e perfil de velocidade conhecidos. Quinas de 90° não devem ser tratadas como curvas executáveis a velocidade constante: devem ser suavizadas ou definidas como parada, rotação e retomada."))
    body.append(table(
        ["ID", "Trajetória", "Objetivo", "Critério principal"],
        [
            ["T0", "Reta de 5 m em 0° e 30°", "Reproduzir e generalizar a linha de base.", "Erro transversal independente do eixo global."],
            ["T1", "Arco de 90° e 180°", "Isolar curvatura constante.", "RMSE transversal, erro angular e tempo em saturação."],
            ["T2", "Curva em S", "Avaliar troca do sinal da curvatura.", "Pico de erro, oscilação e jerk."],
            ["T3", "Figura oito", "Testar progressão, cruzamento e alta excitação angular.", "Sem troca indevida de ramo; taxa de conclusão."],
            ["T4", "Corredor com curva de 90° suavizada", "Aproximar geometria hospitalar.", "Folga à parede e tempo de entrega."],
            ["T5", "Porta estreita + curva + estação de entrega", "Validar aproximação e parada.", "Sucesso de docking, orientação final e intervenções."],
        ], [700, 2400, 3200, 2500]
    ))
    body.append(paragraph("Sequência de validação", style="Heading2"))
    body.append(table(
        ["Gate", "Ambiente", "Entrada para o gate", "Saída exigida"],
        [
            ["G0", "Testes unitários/offline", "Modelos, transformações e sinais definidos.", "Cálculos de erro, curvatura, saturação e parada verificados."],
            ["G1", "Gazebo sem obstáculos", "Reta reproduzida com sucesso.", "Arco, S e oito concluídos sem falhas de software."],
            ["G2", "Gazebo com perturbações", "Configurações congeladas.", "Robustez a ruído, atraso, dropout, atrito e carga simulada."],
            ["G3", "Laboratório demarcado", "Parada de emergência e referência externa validadas.", "Resultados físicos sem pessoas e com carga inerte."],
            ["G4", "Corredor simulado", "Análise de risco aprovada.", "Obstáculos e voluntários treinados; near misses e intervenções registrados."],
            ["G5", "Piloto no HU", "Autorizações, supervisão e SOPs.", "Missões controladas fora do fluxo crítico; sem amostras reais inicialmente."],
        ], [700, 1700, 3200, 3200]
    ))

    # 5
    body += [paragraph("5. Métricas e plano estatístico", style="Heading1")]
    body.append(table(
        ["Dimensão", "Métricas"],
        [
            ["Rastreamento", "MAE, RMSE e P95 do erro transversal; erro máximo; erro angular; erro de progressão; erro final de posição/orientação."],
            ["Estimação", "ATE e RPE; erro de yaw; bias; latência; taxa de mensagens; inovação normalizada; divergências e resets."],
            ["Controle", "Tempo em saturação; integral de |omega|; variação total do comando; aceleração/jerk; deadline perdido; CPU e memória."],
            ["Segurança", "Distância mínima; near misses sob limiar pré-definido; colisões; paradas de emergência; tempo de parada; violação do envelope."],
            ["Missão", "Taxa de conclusão; tempo porta a porta; replans; bloqueios; intervenções humanas; disponibilidade; motivo de falha."],
            ["Carga clínica", "Temperatura; vibração RMS e choque de pico; inclinação; abertura indevida; cadeia de custódia; integridade do recipiente."],
            ["Pessoas", "Conforto, previsibilidade, confiança e aceitabilidade em questionário curto; impacto no fluxo e distância/tempo poupados pela equipe."],
        ], [2100, 6700]
    ))
    body.append(paragraph("Desenho estatístico recomendado", style="Heading2"))
    body += [
        bullet("Fazer um piloto com 8–10 repetições por condição para estimar variabilidade; dimensionar a amostra final por efeito mínimo de interesse e poder estatístico, em vez de repetir 50 por convenção."),
        bullet("Usar execução, e não amostra temporal, como unidade experimental. Mensagens do mesmo rosbag não são repetições independentes."),
        bullet("Parear sementes/condições entre métodos, randomizar a ordem e separar trajetórias de sintonia das trajetórias de teste."),
        bullet("Modelar controlador, estimador, velocidade, carga e trajetória como fatores. Usar modelo linear misto ou alternativa robusta, com execução/dia como efeito aleatório quando aplicável."),
        bullet("Relatar diferenças, intervalos de confiança e tamanho de efeito. Para taxa de sucesso/falha, usar intervalos binomiais e análise separada dos motivos de falha."),
        bullet("Definir previamente critérios de exclusão apenas para falha de aquisição verificável. Falhas do robô ou controlador permanecem como resultado de confiabilidade."),
    ]

    # 6
    body += [paragraph("6. Aproximação ao setor hospitalar", style="Heading1")]
    body.append(paragraph("A validação hospitalar deve tratar o HemaBot como um sistema sociotécnico. A navegação é apenas uma parte: a missão envolve solicitação, identificação do material, carregamento, transporte, entrega, confirmação, limpeza e recuperação de falhas."))
    body.append(table(
        ["Frente", "Próximo passo concreto", "Indicador"],
        [
            ["Mapeamento do fluxo", "Acompanhar equipe do HU e mapear origem, destino, prioridade, janelas de coleta, elevadores, portas e pontos de espera.", "Tempo atual, distância percorrida, variabilidade e gargalos."],
            ["Carga e cadeia de custódia", "Compartimento travado, identificador da missão, registro de abertura, confirmação de coleta/entrega e trilha de auditoria.", "100% dos eventos associados a usuário, horário, origem e destino."],
            ["Integridade da amostra", "Começar com tubos simulados e data logger de temperatura/IMU; depois realizar estudo laboratorial específico com especialistas.", "Limites de tempo, temperatura, vibração e choque definidos pelo tipo de amostra."],
            ["Interação com pessoas", "Velocidade contextual, sinalização de intenção, distância social, regra stop–wait–warn e cenários com cadeiras de rodas/macas.", "Near misses, folga, tempo de espera, conforto e previsibilidade."],
            ["Higienização", "Definir superfícies, compatibilidade química, frequência, responsável e registro de limpeza; testar áreas de difícil acesso.", "Conformidade do procedimento e, em parceria clínica, carga microbiológica antes/depois."],
            ["Segurança funcional", "Análise de risco, e-stop, bumper, watchdog, perda de comunicação, falha de sensor, recuperação manual e zonas de velocidade.", "Nenhuma colisão; tempo de parada; cobertura dos casos de falha."],
            ["Aceitação e operação", "Co-projetar a interface com enfermagem, laboratório, hotelaria, CCIH, engenharia clínica, TI e segurança.", "Usabilidade, carga de trabalho, interrupções, tempo poupado e taxa de adoção."],
        ], [1800, 4800, 2200]
    ))
    body.append(paragraph("Escopo seguro do primeiro piloto", style="Heading2"))
    body.append(paragraph("Realizar missões em horário e trecho controlados, sob supervisão, inicialmente com carga inerte. O piloto deve ter rota de fuga, operador com parada de emergência, limite conservador de velocidade, critério de aborto, registro de incidentes e aprovação institucional. O documento ISO 3691-4:2023 pode apoiar a análise de risco de veículos autônomos, mas a classificação regulatória aplicável ao HemaBot deve ser confirmada com as áreas competentes; esta recomendação não constitui certificação."))

    # 7
    body += [page_break(), paragraph("7. Plano de execução em 12 meses", style="Heading1")]
    body.append(table(
        ["Período", "Pacote de trabalho", "Entregável / gate"],
        [
            ["M1–M2", "Auditoria de ROS 2/TF, reprodução da reta, definição dos requisitos com o HU.", "Baseline reproduzida; dicionário de tópicos/parâmetros; mapa do fluxo hospitalar."],
            ["M2–M4", "Implementação de erros de caminho, Pure Pursuit/RPP e Stanley; testes unitários.", "G0 e G1 aprovados; trajetórias T0–T3 executáveis."],
            ["M4–M6", "DOE em Gazebo com EKF on/off, ruído, atraso, velocidade, carga e atrito.", "Relatório de robustez; parâmetros congelados para o físico."],
            ["M6–M8", "Calibração cinemática e ensaios no protótipo com referência externa.", "G3 aprovado; comparação simulação–real."],
            ["M8–M10", "Corredor simulado, obstáculos/pessoas, carga instrumentada e testes de falha.", "G4 aprovado; análise de risco revisada."],
            ["M10–M11", "Piloto controlado no HU, se autorizado.", "Dados de missão, aceitação, intervenções e higienização."],
            ["M11–M12", "Análise final, disponibilização de artefatos e redação.", "Dataset versionado, artigo e demonstração técnica."],
        ], [1500, 4200, 3100]
    ))
    body.append(paragraph("Escopo mínimo viável, caso o acesso ao hospital atrase", style="Heading2"))
    body.append(paragraph("Concluir a comparação controlada em simulação e laboratório, reproduzir um corredor hospitalar com obstáculos e voluntários, instrumentar a carga e obter avaliação dos cenários por profissionais do HU. Apresentar isso como validação pré-clínica, sem alegar implantação hospitalar."))

    # 8
    body += [paragraph("8. Riscos e mitigações", style="Heading1")]
    body.append(table(
        ["Risco", "Sinal de alerta", "Mitigação"],
        [
            ["EKF degrada a resposta", "Atraso, oscilação, inovações grandes ou erro longitudinal elevado.", "Sincronizar timestamps; calibrar covariâncias; medir atraso; validar sensores isoladamente; usar watchdog."],
            ["Comparação injusta", "Um método usa velocidade, parada ou pose diferente.", "Matriz de configuração e testes pareados; congelar código antes da coleta final."],
            ["Explosão do número de ensaios", "Centenas de combinações sem hipótese clara.", "Triagem em simulação, DOE fatorial fracionado e confirmação apenas nas condições informativas."],
            ["Ground truth insuficiente", "Diferenças entre métodos menores que a incerteza da referência.", "Calibrar o sistema externo, relatar incerteza e ajustar o efeito mínimo de interesse."],
            ["Comportamento imprevisível perto de pessoas", "Oscilações, passagem apertada, alternância de lado.", "Política legível, velocidade contextual, stop–wait–warn, zonas e supervisor."],
            ["Amostra comprometida", "Choque, vibração, temperatura ou tempo fora do limite.", "Carga inerte primeiro, data logger, embalagem validada e estudo por tipo de amostra com o laboratório."],
            ["Dificuldade regulatória/operacional", "Ausência de responsável, SOP ou autorização.", "Engajar CCIH, engenharia clínica, TI, segurança e comitês desde M1."],
        ], [2100, 3300, 3400]
    ))

    # 9
    body += [paragraph("9. Entregáveis e critérios de sucesso", style="Heading1")]
    body += [
        bullet("E1 — Especificação: requisitos, casos de uso hospitalares, interfaces, riscos e protocolo experimental pré-registrado."),
        bullet("E2 — Software: seguidores de caminho, configurações de estimação, launch files, testes e logging determinístico."),
        bullet("E3 — Dados: rosbag, configurações efetivas, seeds, metadados, motivos de término e scripts que reproduzam tabelas/figuras."),
        bullet("E4 — Protótipo: parada de emergência, watchdog, carga instrumentada, compartimento seguro e sinalização de intenção."),
        bullet("E5 — Evidência: resultados em curvas, transferência simulação–real, cenários dinâmicos, falhas e intervalos de confiança."),
        bullet("E6 — Artigo: métodos e dados rastreáveis, conclusões proporcionais ao escopo e limitações explícitas."),
    ]
    body.append(paragraph("Critérios quantitativos finais devem ser definidos com base nos requisitos do HU e no piloto. Como regra de engenharia, o projeto deve declarar antes dos testes: tolerância de erro transversal e final, margem mínima para pessoas/obstáculos, tempo máximo de entrega, limite de vibração/temperatura, taxa mínima de missões concluídas e condições que exigem parada segura."))

    # 10 references
    body += [page_break(), paragraph("10. Papers e fontes relacionados", style="Heading1")]
    body.append(paragraph("Seleção comentada. As fontes foram escolhidas por ligação direta com controle em curvas, fusão sensorial, navegação humana ou logística hospitalar. Recomenda-se iniciar pelos itens [1]–[8] e usar os demais para desenhar o piloto hospitalar."))

    refs = [
        (1, "Moore, T.; Stouch, D. A Generalized Extended Kalman Filter Implementation for the Robot Operating System. IAS-13, 2014.", "Base do robot_localization; fundamenta a arquitetura de fusão, atualizações parciais e configuração do EKF.", "https://docs.ros.org/en/kinetic/api/robot_localization/html/_downloads/robot_localization_ias13_revised.pdf"),
        (2, "Hoffmann, G. M.; Tomlin, C. J.; Montemerlo, M.; Thrun, S. Autonomous Automobile Trajectory Tracking for Off-Road Driving: Controller Design, Experimental Validation and Racing. ACC, 2007, p. 2296–2301.", "Referência do controlador Stanley e da combinação entre erro transversal e de orientação.", "https://robotics.stanford.edu/~gabeh/papers/hoffmann_stanley_control07.pdf"),
        (3, "Coulter, R. C. Implementation of the Pure Pursuit Path Tracking Algorithm. CMU-RI-TR-92-01, Carnegie Mellon University, 1992.", "Derivação geométrica e discussão do lookahead; base para o primeiro controlador de curvas.", "https://www.ri.cmu.edu/publication_view.html?pub_id=278"),
        (4, "Macenski, S.; Singh, S.; Martín, F.; Ginés, J. Regulated Pure Pursuit for Robot Path Tracking. Autonomous Robots, 47, 685–694, 2023. DOI: 10.1007/s10514-023-10097-6.", "Candidato principal no Nav2: regula velocidade para curvatura, proximidade e segurança em espaços confinados.", "https://doi.org/10.1007/s10514-023-10097-6"),
        (5, "Kanayama, Y.; Kimura, Y.; Miyazaki, F.; Noguchi, T. A Stable Tracking Control Method for an Autonomous Mobile Robot. IEEE ICRA, 1990, p. 384–389.", "Alternativa clássica com análise de estabilidade para robô tipo uniciclo; útil para fundamentar erros no referencial do robô.", "https://doi.org/10.1109/ROBOT.1990.126006"),
        (6, "Ali, A. M.; Shen, C.; Hashim, H. A. A Linear MPC with Control Barrier Functions for Differential Drive Robots. IET Control Theory & Applications, 18(18), 2693–2704, 2024. DOI: 10.1049/cth2.12709.", "Extensão futura para restrições e segurança; destaca custo computacional e garantias de barreira.", "https://doi.org/10.1049/cth2.12709"),
        (7, "Banisetty, S. B.; Forer, S.; Yliniemi, L.; Nicolescu, M.; Feil-Seifer, D. Socially-Aware Navigation: A Non-linear Multi-Objective Optimization Approach. ACM TiiS, 11, 2021. DOI: 10.1145/3453445.", "Fornece objetivos e cenários para navegação social: corredor, fila, grupo e espaço pessoal.", "https://doi.org/10.1145/3453445"),
        (8, "Zheng, K.; Wu, F.; Chen, X. Laser-Based People Detection and Obstacle Avoidance for a Hospital Transport Robot. Sensors, 21(3), 961, 2021. DOI: 10.3390/s21030961.", "Caso diretamente alinhado: robô diferencial hospitalar, detecção de pessoas, trajetórias legíveis e regra stop–wait–warn.", "https://doi.org/10.3390/s21030961"),
        (9, "Fung, W. K. et al. Development of a Hospital Service Robot for Transporting Task. IEEE RISSP, 2003, p. 628–633. DOI: 10.1109/RISSP.2003.1285647.", "Exemplo histórico de transporte de medicamentos, amostras e dispositivos com validação em hospital.", "https://doi.org/10.1109/RISSP.2003.1285647"),
        (10, "Howanitz, P. J.; Sunseri, D. A.; Love, L. A.; Lohr, A. Adapting Mobile Robotic Technology to Intralaboratory Specimen Transport. Archives of Pathology & Laboratory Medicine, 120(10), 944–950, 1996. PMID: 12046606.", "Mostra métricas operacionais de longo prazo: rotas, quilometragem, falhas, aceitação e retorno; reportou 99,4% de conclusão ao fim do estudo.", "https://pubmed.ncbi.nlm.nih.gov/12046606/"),
        (11, "Fragapane, G.; Hvolby, H.-H.; Sgarbossa, F.; Strandhagen, J. O. Autonomous Mobile Robots in Sterile Instrument Logistics: An Evaluation of the Material Handling System for a Strategic Fit Framework. Production Planning & Control, 34(1), 53–67, 2023. DOI: 10.1080/09537287.2021.1884914.", "Ajuda a selecionar KPIs hospitalares e a alinhar AMRs às características do hospital, além da navegação." , "https://doi.org/10.1080/09537287.2021.1884914"),
        (12, "Fragapane, G.; de Koster, R.; Sgarbossa, F.; Strandhagen, J. O. Planning and Control of Autonomous Mobile Robots for Intralogistics: Literature Review and Research Agenda. European Journal of Operational Research, 294(2), 405–426, 2021. DOI: 10.1016/j.ejor.2021.01.019.", "Panorama de planejamento, controle e operação de AMRs; sustenta a passagem de um robô isolado para sistema logístico.", "https://doi.org/10.1016/j.ejor.2021.01.019"),
        (13, "Kardas, P. et al. Evaluation of Disinfection Methods for Autonomous Mobile Robots Used in Hospital Logistics in Emergency Departments. Journal of Hospital Infection, 162, 17–25, 2025. DOI: 10.1016/j.jhin.2025.05.006.", "Mostra que superfícies do AMR exigem protocolo explícito; limpeza manual e fumigação tiveram eficácia diferente em áreas de difícil acesso.", "https://doi.org/10.1016/j.jhin.2025.05.006"),
        (14, "Sorokoletova, O. E.; Iocchi, L. Enhancing Robot Reliability for Health-Care Facilities by Means of Human-Aware Navigation Planning. arXiv:2409.17131, 2024.", "Integra planejamento human-aware em robô diferencial ROS e usa cenários médicos e avaliação por especialistas.", "https://arxiv.org/abs/2409.17131"),
        (15, "Design and Performance Evaluation of a Modular Mobile Robot for Autonomous Hospital Logistics. IEEE Transactions on Automation Science and Engineering, 23, 7748–7763, 2026. DOI: 10.1109/TASE.2026.3674356.", "Referência recente de arquitetura modular, recipientes sensorizados, RFID e validação em três hospitais europeus.", "https://doi.org/10.1109/TASE.2026.3674356"),
    ]
    relationships = []
    for idx, (num, cit, rel, url) in enumerate(refs, start=10):
        rid = f"rId{idx}"
        body.append(reference(num, cit, rel, url, rid))
        relationships.append((rid, url))

    body += [
        paragraph("Norma de apoio", style="Heading2"),
        rich_paragraph([
            ("ISO 3691-4:2023 — Industrial trucks — Safety requirements and verification — Part 4: Driverless industrial trucks and their systems. ", {"bold": True}),
            "Aplicável como referência de análise de perigos e verificação para veículos autônomos; confirmar enquadramento com especialistas. ",
        ]),
        f'<w:p>{hyperlink("https://www.iso.org/standard/83545.html", "Página oficial da ISO", "rId25")}</w:p>',
        paragraph("Nota metodológica", style="Heading2"),
        paragraph("Este plano propõe uma agenda e não presume que todos os itens já estejam implementados. As tolerâncias clínicas, a classificação regulatória e os procedimentos de amostras devem ser definidos com o HU, a CCIH, o laboratório, a engenharia clínica e os comitês competentes antes de qualquer piloto assistencial."),
    ]
    relationships.append(("rId25", "https://www.iso.org/standard/83545.html"))

    sect = (
        '<w:sectPr><w:headerReference w:type="default" r:id="rId2"/>'
        '<w:footerReference w:type="default" r:id="rId3"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1190" w:right="1190" w:bottom="1190" w:left="1190" w:header="500" w:footer="500" w:gutter="0"/>'
        '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}" xmlns:r="{NS_R}"><w:body>'
        + ''.join(body) + sect + '</w:body></w:document>'
    )
    return document, relationships


def styles_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS_W}">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:eastAsia="Aptos" w:cs="Aptos"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="12344D"/><w:sz w:val="38"/><w:szCs w:val="38"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:color w:val="2F6B78"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="CoverKicker"><w:name w:val="Cover Kicker"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:color w:val="2F6B78"/><w:caps/><w:spacing w:val="16"/><w:sz w:val="18"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="320" w:after="140"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="12344D"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="220" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="2F6B78"/><w:sz w:val="25"/><w:szCs w:val="25"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="520" w:hanging="260"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Annotation"><w:name w:val="Annotation"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="420"/><w:spacing w:after="150"/></w:pPr><w:rPr><w:i/><w:color w:val="58636B"/><w:sz w:val="20"/></w:rPr></w:style>
</w:styles>'''


def numbering_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{NS_W}"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="520"/></w:tabs><w:ind w:left="520" w:hanging="260"/></w:pPr><w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol"/></w:rPr></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="–"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="1040" w:hanging="260"/></w:pPr></w:lvl>
</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''


def header_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="{NS_W}"><w:p><w:pPr><w:jc w:val="right"/><w:pBdr><w:bottom w:val="single" w:sz="6" w:color="86A7B5" w:space="4"/></w:pBdr></w:pPr><w:r><w:rPr><w:color w:val="58636B"/><w:sz w:val="17"/></w:rPr><w:t>HemaBot · Plano de continuidade</w:t></w:r></w:p></w:hdr>'''


def footer_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="{NS_W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:color w:val="58636B"/><w:sz w:val="18"/></w:rPr><w:t>Página </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:color w:val="58636B"/><w:sz w:val="18"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'''


def write_docx():
    os.makedirs(OUT_DIR, exist_ok=True)
    document, links = build_document()
    doc_rels = [
        ('rId1', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles', 'styles.xml', False),
        ('rId2', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header', 'header1.xml', False),
        ('rId3', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer', 'footer1.xml', False),
        ('rId4', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering', 'numbering.xml', False),
    ]
    for rid, url in links:
        doc_rels.append((rid, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', url, True))
    rel_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for rid, typ, target, external in doc_rels:
        mode = ' TargetMode="External"' if external else ''
        rel_xml.append(f'<Relationship Id="{rid}" Type="{typ}" Target="{x(target)}"{mode}/>')
    rel_xml.append('</Relationships>')

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Próximos passos do projeto HemaBot</dc:title><dc:subject>Controle em curvas e validação hospitalar</dc:subject><dc:creator>Lucas Fernando Neres Miranda</dc:creator><cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><AppVersion>16.0000</AppVersion></Properties>'''

    with zipfile.ZipFile(OUT_FILE, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles_xml())
        z.writestr("word/numbering.xml", numbering_xml())
        z.writestr("word/header1.xml", header_xml())
        z.writestr("word/footer1.xml", footer_xml())
        z.writestr("word/_rels/document.xml.rels", ''.join(rel_xml))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    print(OUT_FILE)


if __name__ == "__main__":
    write_docx()

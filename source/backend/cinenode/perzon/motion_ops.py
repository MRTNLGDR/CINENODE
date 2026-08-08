"""Movimento do PERZON — curvas de animação medidas e corrigidas, não simuladas.

Uma animação aqui é `(quadros, juntas, 3)` em metros, mais o `fps`. Tudo o que
este módulo faz sai de diferença finita sobre esses números: velocidade é a
primeira derivada, jitter é a terceira, deslize de pé é velocidade horizontal em
quadro de contato. Nenhuma métrica é estimada por rótulo ou por nome de arquivo.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import savgol_filter

# Acima disto, o pé que deveria estar plantado está patinando no chão. Vem da
# tolerância usada em captura: 2 cm/s é abaixo do erro do próprio sensor, e
# acima de 5 cm/s o deslize já é visível a olho nu num plano médio.
LIMITE_DESLIZE_M_S = 0.05


def _velocidade(arranjo: np.ndarray, fps: float) -> np.ndarray:
    """Velocidade por quadro, em `(quadros, juntas, 3)` — mesma forma da entrada.

    Diferença para trás: `v[i]` é o quanto a junta andou PARA CHEGAR em `i`. A
    convenção precisa ser única no módulo inteiro. Quando `detectar_contatos`
    usava para trás e `medir_deslize` usava para frente, o último quadro de apoio
    era medido com a velocidade do balanço seguinte, e uma caminhada perfeita —
    pé cravado durante todo o apoio — acusava 3,0 m/s de deslize.
    """
    velocidade = np.diff(arranjo, axis=0) * fps
    return np.vstack([velocidade[:1], velocidade])


class AnimacaoInvalida(ValueError):
    """Os quadros não formam uma animação sobre a qual dê para calcular."""


def conferir(quadros: np.ndarray, fps: float) -> np.ndarray:
    arranjo = np.asarray(quadros, dtype=np.float64)
    if arranjo.ndim != 3 or arranjo.shape[2] != 3:
        raise AnimacaoInvalida(
            f"esperado (quadros, juntas, 3), veio {arranjo.shape}")
    if arranjo.shape[0] < 2:
        raise AnimacaoInvalida("uma animação precisa de pelo menos 2 quadros")
    if fps <= 0:
        raise AnimacaoInvalida(f"fps inválido: {fps}")
    if not np.isfinite(arranjo).all():
        raise AnimacaoInvalida("há NaN ou infinito nas posições")
    return arranjo


# ---- medida -----------------------------------------------------------------

def analisar(quadros: np.ndarray, fps: float) -> dict[str, Any]:
    """Retrato da animação: duração, velocidade, jitter e faixa de movimento."""
    arranjo = conferir(quadros, fps)
    modulo = np.linalg.norm(_velocidade(arranjo, fps), axis=2)

    return {
        "quadros": int(arranjo.shape[0]),
        "juntas": int(arranjo.shape[1]),
        "fps": float(fps),
        "duracao_s": round(arranjo.shape[0] / fps, 4),
        "velocidade_media_m_s": round(float(modulo.mean()), 6),
        "velocidade_maxima_m_s": round(float(modulo.max()), 6),
        "jitter": medir_jitter(arranjo, fps),
        "amplitude_m": [round(float(x), 6) for x in
                        (arranjo.reshape(-1, 3).max(axis=0)
                         - arranjo.reshape(-1, 3).min(axis=0))],
    }


def medir_jitter(quadros: np.ndarray, fps: float) -> dict[str, Any]:
    """Jitter é a terceira derivada — o solavanco, não a velocidade.

    Uma caminhada rápida tem velocidade alta e jitter baixo. Uma captura suja tem
    velocidade normal e jitter alto. Medir aceleração no lugar confundiria as
    duas, e a correção acabaria alisando o movimento junto com o ruído.
    """
    arranjo = conferir(quadros, fps)
    if arranjo.shape[0] < 4:
        return {"medio": None, "maximo": None,
                "nota": "menos de 4 quadros: a terceira derivada não existe"}
    solavanco = np.diff(arranjo, n=3, axis=0) * (fps ** 3)
    modulo = np.linalg.norm(solavanco, axis=2)
    return {
        "medio": round(float(modulo.mean()), 4),
        "maximo": round(float(modulo.max()), 4),
        "junta_mais_ruidosa": int(np.argmax(modulo.mean(axis=0))),
    }


def detectar_contatos(quadros: np.ndarray, fps: float, juntas_pe: list[int],
                      altura_chao: float | None = None,
                      fracao: float = 0.20, margem: int = 2) -> dict[str, Any]:
    """Em que quadros cada pé está no chão — pela altura DELE, não pela velocidade.

    A primeira versão exigia altura baixa E velocidade baixa. Parece razoável e é
    autodestrutivo: um pé que escorrega tem velocidade alta, some da lista de
    contatos, e o detector fica cego exatamente para o defeito que existe para
    achar. Medido: numa caminhada com deslize injetado, a versão com filtro de
    velocidade reportava 0,0 m/s porque descartara todos os quadros ruins.

    O limiar sai da faixa de altura do próprio pé, não da cena. Um personagem que
    levanta o joelho 40 cm e outro que arrasta 5 cm têm o mesmo apoio; normalizar
    pela altura da cabeça faria o segundo nunca sair do chão.

    A altura sozinha, porém, também pega o desprender e o pousar do pé: nesses
    quadros ele está na altura do chão e já se move a 3 m/s. O que separa apoio de
    transição não é o quadro isolado — é a duração. Cada bloco perde `margem`
    quadros em cada ponta, e o que sobra é apoio de fato. Medido: sem essa erosão,
    uma caminhada com o pé cravado durante todo o apoio acusava 3,0 m/s.
    """
    arranjo = conferir(quadros, fps)
    if not juntas_pe:
        raise AnimacaoInvalida("nenhuma junta de pé informada")

    contatos: dict[str, list[int]] = {}
    for junta in juntas_pe:
        alturas = arranjo[:, junta, 1]
        base = altura_chao if altura_chao is not None else float(alturas.min())
        faixa = max(float(np.ptp(alturas)), 1e-6)
        baixo = np.flatnonzero(alturas <= base + fracao * faixa).astype(int).tolist()
        contatos[str(junta)] = _erodir(baixo, margem)

    return {"margem_quadros": int(margem),
            "altura_chao": round(float(altura_chao if altura_chao is not None
                                       else arranjo[:, juntas_pe, 1].min()), 6),
            "fracao_da_faixa": float(fracao),
            "contatos_por_junta": contatos,
            "quadros_com_contato": sorted({q for v in contatos.values() for q in v})}


def medir_deslize(quadros: np.ndarray, fps: float, juntas_pe: list[int],
                  contatos: dict[str, Any] | None = None) -> dict[str, Any]:
    """Quanto o pé escorrega enquanto deveria estar plantado.

    É o defeito mais visível de retarget malfeito: o personagem anda e os pés
    patinam. A medida é a velocidade horizontal nos quadros de contato — a
    vertical não conta, porque levantar o pé é o movimento correto.
    """
    arranjo = conferir(quadros, fps)
    # Aceitar contatos prontos permite medir antes e depois nos MESMOS quadros.
    # Redetectar depois de corrigir compararia dois conjuntos diferentes, e a
    # correção pareceria funcionar mesmo quando piora.
    contatos = contatos or detectar_contatos(arranjo, fps, juntas_pe)
    velocidade = _velocidade(arranjo, fps)

    por_junta: dict[str, Any] = {}
    pior = 0.0
    for junta in juntas_pe:
        # Fora o primeiro quadro de cada apoio: a velocidade que chega nele é a do
        # pé pousando, movimento correto. Contá-la como deslize faria toda
        # caminhada reprovar e a correção parecer inútil — foi o que aconteceu
        # aqui: 2,4 m/s antes e 2,4 m/s depois de travar, com 87 quadros presos.
        quadros_contato = [q for bloco in _blocos_consecutivos(
            contatos["contatos_por_junta"][str(junta)]) for q in bloco[1:]]
        if not quadros_contato:
            por_junta[str(junta)] = {"quadros_de_contato": 0, "deslize_medio_m_s": None}
            continue
        horizontal = np.linalg.norm(velocidade[quadros_contato][:, junta, [0, 2]], axis=1)
        media = float(horizontal.mean())
        maximo = float(horizontal.max())
        pior = max(pior, maximo)
        por_junta[str(junta)] = {
            "quadros_de_contato": len(quadros_contato),
            "deslize_medio_m_s": round(media, 6),
            "deslize_maximo_m_s": round(maximo, 6),
            "aceitavel": bool(maximo <= LIMITE_DESLIZE_M_S),
        }

    return {"por_junta": por_junta, "deslize_maximo_m_s": round(pior, 6),
            "limite_m_s": LIMITE_DESLIZE_M_S,
            "aprovado": bool(pior <= LIMITE_DESLIZE_M_S)}


# ---- correção ---------------------------------------------------------------

def remover_jitter(quadros: np.ndarray, fps: float, janela: int = 5,
                   ordem: int = 2) -> tuple[np.ndarray, dict[str, Any]]:
    """Savitzky-Golay: tira o solavanco preservando o pico do movimento.

    A média móvel achataria o extremo de cada gesto — um soco perde o impacto e
    vira um empurrão. O Savitzky-Golay ajusta um polinômio local, o que mantém
    máximos e mínimos onde estão.
    """
    arranjo = conferir(quadros, fps)
    if janela % 2 == 0:
        janela += 1
    if janela <= ordem:
        raise AnimacaoInvalida(f"janela {janela} precisa ser maior que a ordem {ordem}")
    if janela > arranjo.shape[0]:
        raise AnimacaoInvalida(
            f"janela {janela} maior que a animação de {arranjo.shape[0]} quadros")

    antes = medir_jitter(arranjo, fps)
    suavizado = savgol_filter(arranjo, window_length=janela, polyorder=ordem, axis=0)
    depois = medir_jitter(suavizado, fps)

    deslocamento = float(np.linalg.norm(suavizado - arranjo, axis=2).mean())
    reducao = None
    if antes["medio"] and depois["medio"] is not None:
        reducao = round(1 - depois["medio"] / antes["medio"], 4)

    return suavizado, {
        "janela": int(janela), "ordem": int(ordem),
        "jitter_antes": antes["medio"], "jitter_depois": depois["medio"],
        "reducao_relativa": reducao,
        # Quanto a pose se afastou do original. Reduzir jitter deslocando muito
        # significa que a animação virou outra — o número deixa isso visível.
        "deslocamento_medio_m": round(deslocamento, 6),
    }


def travar_pes(quadros: np.ndarray, fps: float, juntas_pe: list[int],
               rampa: int = 4) -> tuple[np.ndarray, dict[str, Any]]:
    """Prende o pé em contato na posição horizontal do início do apoio.

    Corrige só X e Z. Y fica intocado: a altura do pé no apoio é informação real
    do terreno, e achatá-la criaria o defeito inverso, com o pé afundando no chão.

    O deslocamento entra e sai por rampa. A primeira versão travava seco dentro do
    bloco, e o quadro seguinte ao apoio saltava da posição presa para a real — o
    deslize medido subiu de 0,64 para 0,94 m/s, pior do que antes de corrigir. A
    rampa distribui esse salto pelos quadros vizinhos, onde o pé já está no ar.
    """
    arranjo = conferir(quadros, fps).copy()
    contatos = detectar_contatos(arranjo, fps, juntas_pe)
    antes = medir_deslize(arranjo, fps, juntas_pe, contatos)

    total = arranjo.shape[0]
    corrigidos = 0
    for junta in juntas_pe:
        # Um deslocamento por quadro, acumulado: dois apoios do mesmo pé têm
        # âncoras diferentes, e somar os dois deslocamentos é o que mantém a
        # trajetória contínua entre eles.
        deslocamento = np.zeros((total, 2), dtype=np.float64)
        for bloco in _blocos_consecutivos(contatos["contatos_por_junta"][str(junta)]):
            ancora = arranjo[bloco[0], junta][[0, 2]].copy()
            for quadro in bloco:
                deslocamento[quadro] = ancora - arranjo[quadro, junta][[0, 2]]
            corrigidos += len(bloco) - 1

            # Sai do apoio devolvendo o deslocamento aos poucos, em vez de zerar.
            saida = deslocamento[bloco[-1]].copy()
            for passo in range(1, rampa + 1):
                quadro = bloco[-1] + passo
                if quadro >= total:
                    break
                deslocamento[quadro] = saida * (1 - passo / (rampa + 1))
            # E entra no apoio subindo do zero, pelo mesmo motivo.
            entrada = deslocamento[bloco[0]].copy()
            for passo in range(1, rampa + 1):
                quadro = bloco[0] - passo
                if quadro < 0:
                    break
                deslocamento[quadro] = entrada * (1 - passo / (rampa + 1))

        arranjo[:, junta, 0] += deslocamento[:, 0]
        arranjo[:, junta, 2] += deslocamento[:, 1]

    # Mede nos MESMOS quadros de contato de antes. Redetectar mudaria o conjunto e
    # compararia duas coisas diferentes — foi assim que a primeira versão passou.
    depois = medir_deslize(arranjo, fps, juntas_pe, contatos)
    return arranjo, {
        "quadros_corrigidos": corrigidos,
        "rampa_quadros": int(rampa),
        "deslize_antes_m_s": antes["deslize_maximo_m_s"],
        "deslize_depois_m_s": depois["deslize_maximo_m_s"],
        "melhorou": bool(depois["deslize_maximo_m_s"] < antes["deslize_maximo_m_s"]),
        "aprovado": depois["aprovado"],
    }


def _erodir(indices: list[int], margem: int) -> list[int]:
    """Tira `margem` quadros de cada ponta de cada bloco contínuo."""
    if margem <= 0:
        return indices
    mantidos: list[int] = []
    for bloco in _blocos_consecutivos(indices):
        if len(bloco) > 2 * margem:
            mantidos.extend(bloco[margem:-margem])
    return mantidos


def _blocos_consecutivos(indices: list[int]) -> list[list[int]]:
    """Agrupa quadros vizinhos. Cada bloco é um apoio; dois apoios do mesmo pé
    têm âncoras diferentes, e tratá-los como um só travaria o passo inteiro."""
    if not indices:
        return []
    blocos, atual = [], [indices[0]]
    for indice in indices[1:]:
        if indice == atual[-1] + 1:
            atual.append(indice)
        else:
            blocos.append(atual)
            atual = [indice]
    blocos.append(atual)
    return blocos


def remover_drift(quadros: np.ndarray, fps: float,
                  junta_raiz: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Tira o desvio da raiz em relação à reta de melhor ajuste da trajetória.

    O que este cálculo NÃO consegue fazer, e é importante dizer: velocidade
    lateral constante é indistinguível de andar na diagonal. Sem uma referência
    de para onde o personagem está virado, as duas produzem exatamente a mesma
    curva. A primeira versão usava média móvel e, medida numa caminhada de 0,9 m/s
    em X com 0,06 m/s de deriva em Z, removeu 2,22 m em X — ou seja, comeu a
    caminhada inteira e deixou a deriva quase intacta.

    O que sobra, e é bem definido: o desvio em relação à reta. Serpenteio, arrasto
    que aparece no meio e volta, oscilação lenta de captura. Deriva de rumo
    constante fica, e o relatório diz que ficou.
    """
    arranjo = conferir(quadros, fps).copy()
    total = arranjo.shape[0]
    raiz = arranjo[:, junta_raiz, :].copy()
    tempo = np.arange(total, dtype=np.float64)

    # Reta de melhor ajuste em X e Z; Y não entra, porque altura da raiz é
    # agachamento e salto, não trajetória no plano.
    desvio = np.zeros((total, 3), dtype=np.float64)
    for eixo in (0, 2):
        coef = np.polyfit(tempo, raiz[:, eixo], 1)
        desvio[:, eixo] = raiz[:, eixo] - np.polyval(coef, tempo)

    arranjo -= desvio[:, None, :]
    return arranjo, {
        "aplicado": True,
        "desvio_maximo_m": round(float(np.abs(desvio[:, [0, 2]]).max()), 6),
        "desvio_medio_m": round(float(np.linalg.norm(desvio[:, [0, 2]], axis=1).mean()), 6),
        "rumo_preservado": True,
        "limitacao": "rumo constante não é separável de caminhada diagonal sem "
                     "referência de direção do corpo; só o desvio da reta é removido",
    }


def fazer_loop(quadros: np.ndarray, fps: float,
               transicao: int = 8) -> tuple[np.ndarray, dict[str, Any]]:
    """Costura o fim no começo com mistura por cosseno.

    Mistura linear deixa uma quebra de velocidade visível na emenda: a derivada
    salta. A meia-onda de cosseno começa e termina com derivada zero, e a emenda
    some.
    """
    arranjo = conferir(quadros, fps).copy()
    total = arranjo.shape[0]
    if transicao < 1 or transicao * 2 >= total:
        raise AnimacaoInvalida(
            f"transição de {transicao} quadros não cabe numa animação de {total}")

    erro_antes = float(np.linalg.norm(arranjo[-1] - arranjo[0], axis=1).mean())
    peso = (1 - np.cos(np.linspace(0, np.pi, transicao))) / 2

    cauda = arranjo[-transicao:].copy()
    cabeca = arranjo[:transicao].copy()
    arranjo[-transicao:] = cauda * (1 - peso[:, None, None]) + cabeca * peso[:, None, None]

    erro_depois = float(np.linalg.norm(arranjo[-1] - arranjo[0], axis=1).mean())
    return arranjo, {
        "transicao_quadros": int(transicao),
        "descontinuidade_antes_m": round(erro_antes, 6),
        "descontinuidade_depois_m": round(erro_depois, 6),
        "melhorou": bool(erro_depois < erro_antes),
    }


def reamostrar(quadros: np.ndarray, fps: float,
               fps_alvo: float) -> tuple[np.ndarray, dict[str, Any]]:
    """Troca a taxa de quadros por interpolação linear no tempo.

    Linear e não spline de propósito: spline extrapola além dos extremos e pode
    inventar uma pose que o ator nunca fez. Numa reamostragem de captura, isso
    aparece como membro passando através do corpo.
    """
    arranjo = conferir(quadros, fps)
    if fps_alvo <= 0:
        raise AnimacaoInvalida(f"fps alvo inválido: {fps_alvo}")

    duracao = arranjo.shape[0] / fps
    total_novo = max(2, int(round(duracao * fps_alvo)))
    tempo_velho = np.arange(arranjo.shape[0]) / fps
    tempo_novo = np.linspace(0, tempo_velho[-1], total_novo)

    novo = np.empty((total_novo, arranjo.shape[1], 3), dtype=np.float64)
    for junta in range(arranjo.shape[1]):
        for eixo in range(3):
            novo[:, junta, eixo] = np.interp(tempo_novo, tempo_velho,
                                             arranjo[:, junta, eixo])

    return novo, {
        "fps_antes": float(fps), "fps_depois": float(fps_alvo),
        "quadros_antes": int(arranjo.shape[0]), "quadros_depois": int(total_novo),
        "duracao_s": round(duracao, 4),
        "metodo": "linear; spline poderia inventar pose fora do intervalo capturado",
    }

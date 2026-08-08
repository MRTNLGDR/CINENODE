"""Expressão facial do PERZON — blendshapes medidas do rosto, não presets.

O FaceLandmarker do MediaPipe devolve 52 blendshapes compatíveis com ARKit no
mesmo passe dos 478 pontos. Elas são o dado: cada valor é a ativação medida de
uma região do rosto entre 0 e 1.

A emoção é derivada dessas ativações por combinação declarada, não por um
classificador escondido. Isso importa: quem lê "alegria 0,82" precisa poder ver
que o número saiu de `mouthSmileLeft` e `mouthSmileRight` e conferir na cara da
pessoa. Um classificador que só cospe o rótulo não permite discordar dele.
"""
from __future__ import annotations

from typing import Any

import numpy as np

# Índices do FaceLandmarker (478 pontos). Cada um foi conferido contra a malha
# canônica do MediaPipe — errar um índice aqui produz medida plausível e errada,
# que é o pior tipo de defeito porque não parece defeito.
OLHO_E_SUPERIOR, OLHO_E_INFERIOR = 159, 145
OLHO_D_SUPERIOR, OLHO_D_INFERIOR = 386, 374
OLHO_E_INTERNO, OLHO_E_EXTERNO = 133, 33
OLHO_D_INTERNO, OLHO_D_EXTERNO = 362, 263
IRIS_E, IRIS_D = 468, 473
LABIO_SUPERIOR, LABIO_INFERIOR = 13, 14
BOCA_ESQUERDA, BOCA_DIREITA = 61, 291
NASIO, QUEIXO = 168, 152

# Emoção por combinação de blendshapes. As combinações seguem o mapeamento FACS
# clássico (Ekman): alegria é AU6+AU12, tristeza é AU1+AU4+AU15, e assim por
# diante. O peso diz quanto cada ativação contribui.
EMOCOES: dict[str, dict[str, float]] = {
    "alegria": {"mouthSmileLeft": 0.35, "mouthSmileRight": 0.35,
                "cheekSquintLeft": 0.15, "cheekSquintRight": 0.15},
    "tristeza": {"browInnerUp": 0.30, "mouthFrownLeft": 0.25,
                 "mouthFrownRight": 0.25, "browDownLeft": 0.10, "browDownRight": 0.10},
    "raiva": {"browDownLeft": 0.30, "browDownRight": 0.30,
              "noseSneerLeft": 0.10, "noseSneerRight": 0.10,
              "mouthPressLeft": 0.10, "mouthPressRight": 0.10},
    "surpresa": {"browInnerUp": 0.20, "browOuterUpLeft": 0.20,
                 "browOuterUpRight": 0.20, "eyeWideLeft": 0.15,
                 "eyeWideRight": 0.15, "jawOpen": 0.10},
    "medo": {"browInnerUp": 0.25, "eyeWideLeft": 0.25, "eyeWideRight": 0.25,
             "mouthStretchLeft": 0.125, "mouthStretchRight": 0.125},
    "nojo": {"noseSneerLeft": 0.30, "noseSneerRight": 0.30,
             "mouthUpperUpLeft": 0.20, "mouthUpperUpRight": 0.20},
}

# Visemas por blendshape dominante. É o mapeamento que a indústria usa para
# sincronia labial; não substitui análise de áudio, e o relatório diz isso.
VISEMAS: dict[str, dict[str, float]] = {
    "AA": {"jawOpen": 1.0},
    "EE": {"mouthSmileLeft": 0.5, "mouthSmileRight": 0.5},
    "OO": {"mouthPucker": 1.0},
    "FV": {"mouthLowerDownLeft": 0.5, "mouthLowerDownRight": 0.5},
    "MBP": {"mouthClose": 1.0},
}

# Abaixo disto, o olho está praticamente fechado. Vem da razão de aspecto do olho
# (EAR) usada em detecção de piscada: olho aberto fica entre 0,25 e 0,35, e a
# piscada cruza 0,20 no meio do movimento.
EAR_FECHADO = 0.20


class RostoInvalido(ValueError):
    """Não há rosto medível na entrada."""


def _valores(blendshapes: Any) -> dict[str, float]:
    """Normaliza a saída do MediaPipe para um dicionário nome → ativação."""
    if isinstance(blendshapes, dict):
        return {str(k): float(v) for k, v in blendshapes.items()}
    return {item.category_name: float(item.score) for item in blendshapes}


# ---- blendshapes -------------------------------------------------------------

def analisar_blendshapes(blendshapes: Any) -> dict[str, Any]:
    """As 52 ativações medidas, com as que importam separadas.

    Devolver as 52 cruas seria despejo; devolver só o resumo esconderia o dado.
    O retorno traz os dois, e a UI escolhe o que mostrar.
    """
    valores = _valores(blendshapes)
    if not valores:
        raise RostoInvalido("nenhuma blendshape foi medida")

    ativas = {nome: round(v, 4) for nome, v in valores.items() if v >= 0.05}
    ordenadas = sorted(valores.items(), key=lambda item: -item[1])
    return {
        "total": len(valores),
        "ativas": len(ativas),
        "dominantes": [{"nome": n, "valor": round(v, 4)} for n, v in ordenadas[:8]],
        "todas": {n: round(v, 4) for n, v in sorted(valores.items())},
        "energia": round(float(sum(valores.values())), 4),
        # Rosto em repouso tem energia baixa. É o que separa "neutro" de
        # "não conseguimos medir": os dois têm poucas ativações fortes, mas o
        # segundo não tem ativação nenhuma.
        "neutro": bool(max(valores.values()) < 0.15),
    }


def classificar_emocao(blendshapes: Any) -> dict[str, Any]:
    """Pontua cada emoção pela combinação FACS declarada em `EMOCOES`.

    A pontuação é a média ponderada das ativações que compõem a emoção. Nenhuma
    rede foi treinada aqui: o cálculo é aritmética sobre dado medido, e quem
    discordar do resultado consegue ver exatamente qual termo puxou o número.
    """
    valores = _valores(blendshapes)
    if not valores:
        raise RostoInvalido("nenhuma blendshape foi medida")

    pontos: dict[str, float] = {}
    detalhe: dict[str, dict[str, float]] = {}
    for emocao, combinacao in EMOCOES.items():
        contribuicoes = {nome: round(valores.get(nome, 0.0) * peso, 4)
                         for nome, peso in combinacao.items()}
        pontos[emocao] = round(float(sum(contribuicoes.values())), 4)
        detalhe[emocao] = contribuicoes

    dominante, valor = max(pontos.items(), key=lambda item: item[1])
    # Abaixo de 0,15 nenhuma combinação está de fato ativa: o rosto está neutro,
    # e apontar a emoção "menos fraca" seria inventar leitura.
    neutro = valor < 0.15
    return {
        "dominante": "neutra" if neutro else dominante,
        "confianca": round(valor, 4),
        "pontuacoes": pontos,
        "contribuicoes": detalhe,
        "metodo": "combinação FACS declarada sobre blendshapes medidas; "
                  "não é classificador treinado",
    }


def detectar_visema(blendshapes: Any) -> dict[str, Any]:
    """Visema mais provável a partir da forma da boca.

    Não substitui análise de áudio: dois fonemas diferentes podem ter a mesma
    forma de boca, e sem o som não há como separá-los. O relatório diz isso em
    vez de deixar quem usa achar que tem sincronia labial resolvida.
    """
    valores = _valores(blendshapes)
    pontos = {visema: round(float(sum(valores.get(n, 0.0) * p for n, p in combinacao.items())), 4)
              for visema, combinacao in VISEMAS.items()}
    dominante, valor = max(pontos.items(), key=lambda item: item[1])
    return {
        "visema": dominante if valor >= 0.15 else "silencio",
        "intensidade": round(valor, 4),
        "pontuacoes": pontos,
        "limitacao": "forma de boca sozinha não separa fonemas homógrafos "
                     "visualmente; sincronia real exige o áudio",
    }


# ---- geometria dos olhos e da boca ------------------------------------------

def _ear(pontos: np.ndarray, superior: int, inferior: int,
         interno: int, externo: int) -> float:
    """Razão de aspecto do olho: altura sobre largura.

    Normalizar pela largura é o que torna a medida independente da distância da
    câmera. Usar a altura crua faria um rosto longe parecer sempre com os olhos
    fechados.
    """
    altura = float(np.linalg.norm(pontos[superior] - pontos[inferior]))
    largura = float(np.linalg.norm(pontos[interno] - pontos[externo]))
    return altura / largura if largura > 1e-9 else 0.0


def medir_olhos(pontos: np.ndarray) -> dict[str, Any]:
    """Abertura de cada olho e para onde eles apontam."""
    pontos = np.asarray(pontos, dtype=np.float64)
    if len(pontos) < 478:
        raise RostoInvalido(
            f"a íris exige os 478 pontos do FaceLandmarker; vieram {len(pontos)}")

    ear_e = _ear(pontos, OLHO_E_SUPERIOR, OLHO_E_INFERIOR, OLHO_E_INTERNO, OLHO_E_EXTERNO)
    ear_d = _ear(pontos, OLHO_D_SUPERIOR, OLHO_D_INFERIOR, OLHO_D_INTERNO, OLHO_D_EXTERNO)

    # Direção do olhar pela posição da íris dentro da fenda: 0 é canto interno,
    # 1 é canto externo. É aproximação — o olhar real depende também da rotação
    # do globo, que a malha não representa.
    def desvio(iris: int, interno: int, externo: int) -> float:
        canto_i, canto_e = pontos[interno], pontos[externo]
        largura = canto_e - canto_i
        norma = float(np.dot(largura, largura))
        if norma < 1e-12:
            return 0.5
        return float(np.dot(pontos[iris] - canto_i, largura) / norma)

    return {
        "abertura_esquerdo": round(ear_e, 4),
        "abertura_direito": round(ear_d, 4),
        "fechado_esquerdo": bool(ear_e < EAR_FECHADO),
        "fechado_direito": bool(ear_d < EAR_FECHADO),
        "piscando": bool(ear_e < EAR_FECHADO and ear_d < EAR_FECHADO),
        # Diferença entre os dois olhos: alta significa piscada de um olho só,
        # ou pálpebra caída — as duas coisas mudam o rig que o rosto precisa.
        "assimetria_de_abertura": round(abs(ear_e - ear_d), 4),
        "olhar_esquerdo": round(desvio(IRIS_E, OLHO_E_INTERNO, OLHO_E_EXTERNO), 4),
        "olhar_direito": round(desvio(IRIS_D, OLHO_D_INTERNO, OLHO_D_EXTERNO), 4),
        "limitacao": "a íris dá a posição na fenda, não a rotação do globo ocular",
    }


def medir_boca(pontos: np.ndarray) -> dict[str, Any]:
    """Abertura, largura e contato dos lábios."""
    pontos = np.asarray(pontos, dtype=np.float64)
    abertura = float(np.linalg.norm(pontos[LABIO_SUPERIOR] - pontos[LABIO_INFERIOR]))
    largura = float(np.linalg.norm(pontos[BOCA_ESQUERDA] - pontos[BOCA_DIREITA]))
    referencia = float(np.linalg.norm(pontos[NASIO] - pontos[QUEIXO]))

    razao = abertura / largura if largura > 1e-9 else 0.0
    return {
        "abertura_relativa": round(abertura / referencia, 4) if referencia > 1e-9 else 0.0,
        "largura_relativa": round(largura / referencia, 4) if referencia > 1e-9 else 0.0,
        "razao_abertura_largura": round(razao, 4),
        # Lábios encostados é o que decide se um visema de fechamento (M, B, P)
        # é possível naquele quadro.
        "labios_em_contato": bool(razao < 0.05),
    }


def medir_assimetria(pontos: np.ndarray) -> dict[str, Any]:
    """Quanto o rosto difere de si mesmo espelhado no plano sagital.

    Todo rosto humano é assimétrico, e apagar isso é o erro clássico de
    reconstrução facial: o resultado fica correto e não se parece com a pessoa.
    A medida existe para decidir conscientemente o que preservar.
    """
    pontos = np.asarray(pontos, dtype=np.float64)
    eixo = float((pontos[NASIO][0] + pontos[QUEIXO][0]) / 2)

    pares = [(OLHO_E_EXTERNO, OLHO_D_EXTERNO), (OLHO_E_INTERNO, OLHO_D_INTERNO),
             (BOCA_ESQUERDA, BOCA_DIREITA), (OLHO_E_SUPERIOR, OLHO_D_SUPERIOR)]
    referencia = float(np.linalg.norm(pontos[NASIO] - pontos[QUEIXO]))
    if referencia < 1e-9:
        raise RostoInvalido("nasio e queixo coincidem: o rosto não tem escala")

    desvios = []
    detalhe = []
    for esquerda, direita in pares:
        distancia_e = abs(float(pontos[esquerda][0]) - eixo)
        distancia_d = abs(float(pontos[direita][0]) - eixo)
        altura = abs(float(pontos[esquerda][1]) - float(pontos[direita][1]))
        desvio = (abs(distancia_e - distancia_d) + altura) / referencia
        desvios.append(desvio)
        detalhe.append({"par": [int(esquerda), int(direita)], "desvio": round(desvio, 5)})

    media = float(np.mean(desvios))
    return {
        "eixo_sagital_x": round(eixo, 4),
        "assimetria_media": round(media, 5),
        "assimetria_maxima": round(float(np.max(desvios)), 5),
        "por_par": detalhe,
        # 2% da altura do rosto é onde a assimetria passa de natural a visível.
        "assimetria_visivel": bool(media > 0.02),
    }


def compor_expressao(base: Any, camada: Any, peso: float = 0.5) -> dict[str, Any]:
    """Mistura duas expressões blendshape a blendshape.

    Soma com limite em 1, não média: sorrir e levantar a sobrancelha ao mesmo
    tempo dá as duas coisas, e a média daria meio sorriso com meia sobrancelha —
    uma terceira expressão que ninguém pediu.
    """
    if not 0.0 <= peso <= 1.0:
        raise RostoInvalido(f"peso fora de 0..1: {peso}")
    a, b = _valores(base), _valores(camada)
    nomes = sorted(set(a) | set(b))
    resultado = {n: round(min(1.0, a.get(n, 0.0) + b.get(n, 0.0) * peso), 4) for n in nomes}
    saturadas = [n for n, v in resultado.items() if v >= 1.0]
    return {
        "blendshapes": resultado,
        "peso_da_camada": float(peso),
        "saturadas": saturadas,
        "metodo": "soma limitada em 1; a média produziria uma terceira expressão",
    }


def espelhar_expressao(blendshapes: Any) -> dict[str, Any]:
    """Troca esquerda por direita em cada blendshape lateral.

    O nome carrega o lado (`mouthSmileLeft`), então a troca é textual e exata.
    Blendshape central fica como está — espelhar `jawOpen` não significa nada.
    """
    valores = _valores(blendshapes)
    # Cada nome recebe o valor do seu par. Nome sem par recebe o próprio valor,
    # o que mantém a chave e evita perder blendshape central na troca.
    saida = {nome: round(valores.get(_par(nome), valor), 4)
             for nome, valor in valores.items()}
    pares = sum(1 for nome in valores if _par(nome) in valores and _par(nome) != nome)
    return {"blendshapes": saida, "pares_trocados": pares // 2}


def _par(nome: str) -> str:
    if nome.endswith("Left"):
        return nome[:-4] + "Right"
    if nome.endswith("Right"):
        return nome[:-5] + "Left"
    return nome


def validar_expressao(blendshapes: Any) -> list[dict[str, str]]:
    """Combinações que a anatomia não permite, e que quebram o rig facial."""
    valores = _valores(blendshapes)
    achados: list[dict[str, str]] = []

    fora = [n for n, v in valores.items() if v < 0.0 or v > 1.0]
    if fora:
        achados.append({
            "codigo": "ATIVACAO_FORA_DA_FAIXA",
            "detalhe": ", ".join(fora[:5]),
            "efeito": "blendshape fora de 0..1 extrapola o morph e deforma a malha",
        })

    if valores.get("jawOpen", 0) > 0.6 and valores.get("mouthClose", 0) > 0.6:
        achados.append({
            "codigo": "MANDIBULA_E_BOCA_EM_CONFLITO",
            "detalhe": f"jawOpen={valores['jawOpen']:.2f} com mouthClose={valores['mouthClose']:.2f}",
            "efeito": "a mandíbula abre e os lábios fecham: o queixo atravessa os dentes",
        })

    for lado in ("Left", "Right"):
        fecha = valores.get(f"eyeBlink{lado}", 0)
        arregala = valores.get(f"eyeWide{lado}", 0)
        if fecha > 0.5 and arregala > 0.5:
            achados.append({
                "codigo": "OLHO_FECHA_E_ARREGALA",
                "detalhe": f"{lado}: blink={fecha:.2f}, wide={arregala:.2f}",
                "efeito": "pálpebra recebe dois alvos opostos e trava no meio",
            })

    if valores.get("mouthSmileLeft", 0) > 0.5 and valores.get("mouthFrownLeft", 0) > 0.5:
        achados.append({
            "codigo": "SORRISO_E_TRISTEZA_NO_MESMO_LADO",
            "detalhe": "mouthSmile e mouthFrown ativos juntos",
            "efeito": "o canto da boca sobe e desce ao mesmo tempo; a malha rasga",
        })
    return achados

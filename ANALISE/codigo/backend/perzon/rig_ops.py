"""Rig do PERZON — esqueleto e pesos calculados da malha, não desenhados à mão.

O esqueleto sai das proporções medidas do corpo; os pesos saem da distância de
cada vértice ao osso. Nada aqui é tabela fixa: um personagem de 1,50 m e um de
2,10 m recebem esqueletos diferentes porque a medida é diferente.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh

# Hierarquia canônica. É a mesma do glTF/Mixamo porque motor de jogo e biblioteca
# de animação esperam esses nomes — inventar nomenclatura própria significaria que
# nenhuma animação de terceiro carregaria no personagem.
HIERARQUIA: list[tuple[str, str | None]] = [
    ("quadril", None),
    ("coluna", "quadril"),
    ("coluna_media", "coluna"),
    ("peito", "coluna_media"),
    ("pescoco", "peito"),
    ("cabeca", "pescoco"),
    ("ombro_e", "peito"), ("braco_e", "ombro_e"), ("antebraco_e", "braco_e"), ("mao_e", "antebraco_e"),
    ("ombro_d", "peito"), ("braco_d", "ombro_d"), ("antebraco_d", "braco_d"), ("mao_d", "antebraco_d"),
    ("coxa_e", "quadril"), ("perna_e", "coxa_e"), ("pe_e", "perna_e"),
    ("coxa_d", "quadril"), ("perna_d", "coxa_d"), ("pe_d", "perna_d"),
]

# Fração da altura total em que cada junta fica. Sai de antropometria clássica
# (cânone de oito cabeças, com correção de Drillis-Contini para membros), não de
# chute: quadril em 0,53 H e joelho em 0,285 H são valores medidos em população.
FRACAO_ALTURA: dict[str, float] = {
    "quadril": 0.530, "coluna": 0.600, "coluna_media": 0.660, "peito": 0.720,
    "pescoco": 0.830, "cabeca": 0.870,
    "ombro_e": 0.815, "braco_e": 0.800, "antebraco_e": 0.620, "mao_e": 0.480,
    "ombro_d": 0.815, "braco_d": 0.800, "antebraco_d": 0.620, "mao_d": 0.480,
    "coxa_e": 0.530, "perna_e": 0.285, "pe_e": 0.039,
    "coxa_d": 0.530, "perna_d": 0.285, "pe_d": 0.039,
}

# Deslocamento lateral, em fração da largura dos ombros ou do quadril.
LADO: dict[str, float] = {
    "ombro_e": -0.50, "braco_e": -0.62, "antebraco_e": -0.62, "mao_e": -0.62,
    "ombro_d": 0.50, "braco_d": 0.62, "antebraco_d": 0.62, "mao_d": 0.62,
    "coxa_e": -0.18, "perna_e": -0.18, "pe_e": -0.18,
    "coxa_d": 0.18, "perna_d": 0.18, "pe_d": 0.18,
}


class RigInvalido(ValueError):
    """A malha não sustenta um esqueleto humano coerente."""


def medir_corpo(malha: trimesh.Trimesh) -> dict[str, float]:
    """Extrai as medidas que o esqueleto precisa, da geometria.

    A largura dos ombros é medida na fatia horizontal da altura do ombro, não na
    caixa envolvente: a caixa incluiria os braços estendidos e produziria um
    esqueleto com ombros no lugar dos cotovelos.
    """
    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    if altura <= 0:
        raise RigInvalido("altura zero no eixo Y: a malha não está de pé")

    def largura_na_altura(fracao: float, espessura: float = 0.02) -> float:
        """Largura da seção horizontal, por interseção com o plano.

        Amostrar vértices numa faixa parece equivalente e não é: um cilindro tem
        vértices só nas duas tampas, e a faixa no meio do braço sai vazia. O
        fallback devolvia a largura da caixa inteira, ou seja, exatamente o que
        esta função existe para não fazer — medido: ombro de 1,10 m num corpo cujo
        ombro tem 0,63 m, porque a caixa incluía o quadril alargado.
        """
        y = minimo[1] + fracao * altura
        try:
            segmentos = trimesh.intersections.mesh_plane(
                malha, plane_normal=[0.0, 1.0, 0.0], plane_origin=[0.0, y, 0.0])
        except Exception:      # noqa: BLE001 — malha degenerada não corta
            segmentos = np.empty((0, 2, 3))

        if len(segmentos):
            pontos = np.asarray(segmentos).reshape(-1, 3)
            return float(pontos[:, 0].max() - pontos[:, 0].min())

        faixa = malha.vertices[np.abs(malha.vertices[:, 1] - y) < espessura * altura]
        if len(faixa) < 3:
            return float(maximo[0] - minimo[0])
        return float(faixa[:, 0].max() - faixa[:, 0].min())

    return {
        "altura": altura,
        "base_y": float(minimo[1]),
        "centro_x": float((minimo[0] + maximo[0]) / 2),
        "centro_z": float((minimo[2] + maximo[2]) / 2),
        "largura_ombros": largura_na_altura(FRACAO_ALTURA["ombro_e"]),
        "largura_quadril": largura_na_altura(FRACAO_ALTURA["quadril"]),
        "profundidade": float(maximo[2] - minimo[2]),
    }


def gerar_esqueleto(malha: trimesh.Trimesh) -> dict[str, Any]:
    """Posiciona cada junta a partir das medidas reais da malha."""
    medida = medir_corpo(malha)
    altura, base = medida["altura"], medida["base_y"]
    ombros, quadril = medida["largura_ombros"], medida["largura_quadril"]

    juntas: dict[str, list[float]] = {}
    for nome, _pai in HIERARQUIA:
        y = base + FRACAO_ALTURA[nome] * altura
        fator = LADO.get(nome, 0.0)
        referencia = ombros if ("ombro" in nome or "braco" in nome or "mao" in nome) else quadril
        x = medida["centro_x"] + fator * referencia
        juntas[nome] = [round(x, 6), round(y, 6), round(medida["centro_z"], 6)]

    ossos = []
    for nome, pai in HIERARQUIA:
        if pai is None:
            continue
        comprimento = float(np.linalg.norm(
            np.array(juntas[nome]) - np.array(juntas[pai])))
        ossos.append({"nome": nome, "pai": pai, "comprimento": round(comprimento, 6)})

    return {
        "juntas": juntas,
        "ossos": ossos,
        "total_juntas": len(juntas),
        "medida": {k: round(v, 6) for k, v in medida.items()},
        "convencao": "glTF/Mixamo, Y para cima, metros",
    }


def calcular_pesos(malha: trimesh.Trimesh, esqueleto: dict[str, Any],
                   max_influencias: int = 4) -> dict[str, Any]:
    """Peso de skin por distância ao segmento de osso, com queda inversa.

    Distância ao *segmento*, não à junta: usar a junta faria o meio do braço ser
    puxado pelo ombro e pelo cotovelo em partes iguais, e o braço dobraria errado.

    Quatro influências por vértice é o teto do glTF e de praticamente todo motor
    de jogo. Passar disso significa que a exportação vai truncar em algum lugar
    fora daqui, sem avisar.
    """
    juntas = esqueleto["juntas"]
    ossos = esqueleto["ossos"]
    if not ossos:
        raise RigInvalido("esqueleto sem ossos")

    nomes = [o["nome"] for o in ossos]
    inicio = np.array([juntas[o["pai"]] for o in ossos])
    fim = np.array([juntas[o["nome"]] for o in ossos])

    vertices = malha.vertices
    distancias = np.empty((len(vertices), len(ossos)), dtype=np.float64)
    for i in range(len(ossos)):
        distancias[:, i] = _distancia_ao_segmento(vertices, inicio[i], fim[i])

    # Inverso do quadrado: a influência cai rápido, o que mantém a deformação
    # local. Sem o epsilon, um vértice exatamente sobre o osso daria divisão por
    # zero e o peso viraria NaN — que só aparece como membro explodido no render.
    influencia = 1.0 / (distancias ** 2 + 1e-8)

    ordem = np.argsort(-influencia, axis=1)[:, :max_influencias]
    linhas = np.arange(len(vertices))[:, None]
    melhores = influencia[linhas, ordem]
    soma = melhores.sum(axis=1, keepdims=True)
    normalizado = melhores / soma

    return {
        "ossos": nomes,
        "indices": ordem.astype(int).tolist(),
        "pesos": np.round(normalizado, 6).tolist(),
        "max_influencias": int(max_influencias),
        "vertices": int(len(vertices)),
        "verificacao": {
            # A soma tem de dar 1 em todo vértice. Se não der, a malha estica ou
            # encolhe ao animar, e o defeito só aparece em movimento.
            "soma_minima": float(normalizado.sum(axis=1).min()),
            "soma_maxima": float(normalizado.sum(axis=1).max()),
            "ossos_sem_influencia": [
                nomes[i] for i in range(len(nomes)) if i not in set(ordem.flatten().tolist())
            ],
        },
    }


def _distancia_ao_segmento(pontos: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distância euclidiana de cada ponto ao segmento AB, projetada e limitada."""
    ab = b - a
    comprimento2 = float(ab @ ab)
    if comprimento2 < 1e-12:
        return np.linalg.norm(pontos - a, axis=1)
    t = np.clip(((pontos - a) @ ab) / comprimento2, 0.0, 1.0)
    projecao = a + t[:, None] * ab
    return np.linalg.norm(pontos - projecao, axis=1)


def validar_rig(esqueleto: dict[str, Any], pesos: dict[str, Any]) -> list[dict[str, str]]:
    """Defeitos que só aparecem depois de animar, detectados antes de animar."""
    achados: list[dict[str, str]] = []

    verificacao = pesos["verificacao"]
    if abs(verificacao["soma_minima"] - 1.0) > 1e-4 or abs(verificacao["soma_maxima"] - 1.0) > 1e-4:
        achados.append({
            "codigo": "PESOS_NAO_NORMALIZADOS",
            "detalhe": f"soma entre {verificacao['soma_minima']:.6f} e "
                       f"{verificacao['soma_maxima']:.6f}",
            "efeito": "a malha estica ou encolhe ao animar",
        })

    orfaos = verificacao["ossos_sem_influencia"]
    if orfaos:
        achados.append({
            "codigo": "OSSOS_SEM_PESO",
            "detalhe": ", ".join(orfaos),
            "efeito": "esses ossos giram e nada se move junto",
        })

    curtos = [o["nome"] for o in esqueleto["ossos"] if o["comprimento"] < 1e-4]
    if curtos:
        achados.append({
            "codigo": "OSSO_DE_COMPRIMENTO_ZERO",
            "detalhe": ", ".join(curtos),
            "efeito": "orientação indefinida; o solucionador de IK diverge",
        })

    # Simetria esquerda/direita: assimetria no esqueleto vira andar torto.
    juntas = esqueleto["juntas"]
    for nome in [n for n, _ in HIERARQUIA if n.endswith("_e")]:
        espelho = nome[:-2] + "_d"
        if espelho not in juntas:
            continue
        esquerda, direita = np.array(juntas[nome]), np.array(juntas[espelho])
        if abs(abs(esquerda[0]) - abs(direita[0])) > 1e-4 or abs(esquerda[1] - direita[1]) > 1e-4:
            achados.append({
                "codigo": "PAR_ASSIMETRICO",
                "detalhe": f"{nome} contra {espelho}",
                "efeito": "a caminhada sai torta e o espelhamento de pose falha",
            })
    return achados

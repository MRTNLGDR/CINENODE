"""Cabelo do PERZON — guias como curvas, com física e conversão para cards.

Um fio é uma polilinha de pontos com a raiz fixa. Tudo o que se faz com cabelo —
pentear, encaracolar, aplicar gravidade, agrupar em mechas — é mover esses pontos
respeitando o comprimento do fio. Fio que estica ao ser penteado não é cabelo.

A conversão para cards existe porque motor de jogo não renderiza curva: ele
renderiza quad texturizado. O número de cards é o que decide se o cabelo cabe no
orçamento de polígonos, e ele sai medido, não estimado.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh
from scipy.spatial import cKDTree

GRAVIDADE_Y = -9.81

# Fio que estica mais que isto ao ser deformado deixou de ser fio e virou elástico.
TOLERANCIA_DE_COMPRIMENTO = 0.02


class CabeloInvalido(ValueError):
    """As guias não formam cabelo sobre o qual dê para calcular."""


def _conferir(guias: np.ndarray) -> np.ndarray:
    arranjo = np.asarray(guias, dtype=np.float64)
    if arranjo.ndim != 3 or arranjo.shape[2] != 3:
        raise CabeloInvalido(f"esperado (fios, pontos, 3), veio {arranjo.shape}")
    if arranjo.shape[1] < 2:
        raise CabeloInvalido("um fio precisa de pelo menos 2 pontos")
    if not np.isfinite(arranjo).all():
        raise CabeloInvalido("há NaN ou infinito nas guias")
    return arranjo


# ---- geração -----------------------------------------------------------------

def semear_raizes(couro: trimesh.Trimesh, quantidade: int,
                  semente: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Distribui raízes pela superfície, com área como peso.

    Amostrar vértices em vez da superfície concentraria as raízes onde a malha é
    mais densa — que é onde o modelador precisou de detalhe, não onde há mais
    cabelo. A amostragem por área é uniforme na pele de verdade.
    """
    if quantidade < 1:
        raise CabeloInvalido(f"quantidade precisa ser positiva: {quantidade}")
    if not len(couro.faces):
        raise CabeloInvalido("o couro cabeludo não tem faces")

    pontos, indices = trimesh.sample.sample_surface(couro, quantidade, seed=semente)
    normais = couro.face_normals[indices]

    espacamento = None
    if quantidade > 1:
        arvore = cKDTree(pontos)
        distancias, _ = arvore.query(pontos, k=2)
        espacamento = float(np.mean(distancias[:, 1]))

    return np.asarray(pontos), {
        "raizes": int(len(pontos)),
        "area_do_couro_m2": round(float(couro.area), 6),
        "densidade_por_m2": round(len(pontos) / max(float(couro.area), 1e-9), 2),
        "espacamento_medio_m": round(espacamento, 6) if espacamento else None,
        "normais": normais.tolist(),
    }


def crescer_guias(raizes: np.ndarray, normais: np.ndarray, comprimento_m: float,
                  pontos_por_fio: int = 8,
                  variacao: float = 0.15, semente: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Cria cada fio saindo da raiz na direção da normal.

    A variação de comprimento não é enfeite: cabelo com todos os fios do mesmo
    tamanho lê como peruca de plástico, porque a ponta forma uma linha reta que
    não existe em cabelo real.
    """
    raizes = np.asarray(raizes, dtype=np.float64)
    normais = np.asarray(normais, dtype=np.float64)
    if len(raizes) != len(normais):
        raise CabeloInvalido(f"{len(raizes)} raízes contra {len(normais)} normais")
    if comprimento_m <= 0:
        raise CabeloInvalido(f"comprimento precisa ser positivo: {comprimento_m}")
    if pontos_por_fio < 2:
        raise CabeloInvalido(f"pontos por fio precisa ser >= 2: {pontos_por_fio}")

    rng = np.random.default_rng(semente)
    fatores = 1.0 + rng.uniform(-variacao, variacao, len(raizes))
    passo = np.linspace(0.0, 1.0, pontos_por_fio)

    guias = (raizes[:, None, :]
             + normais[:, None, :] * (passo[None, :, None]
                                      * comprimento_m * fatores[:, None, None]))
    comprimentos = np.linalg.norm(np.diff(guias, axis=1), axis=2).sum(axis=1)
    return guias, {
        "fios": int(len(guias)),
        "pontos_por_fio": int(pontos_por_fio),
        "comprimento_medio_m": round(float(comprimentos.mean()), 6),
        "comprimento_minimo_m": round(float(comprimentos.min()), 6),
        "comprimento_maximo_m": round(float(comprimentos.max()), 6),
        "variacao": float(variacao),
    }


# ---- medida ------------------------------------------------------------------

def medir_guias(guias: np.ndarray) -> dict[str, Any]:
    """Comprimento, curvatura e dispersão das pontas."""
    arranjo = _conferir(guias)
    segmentos = np.diff(arranjo, axis=1)
    comprimentos = np.linalg.norm(segmentos, axis=2).sum(axis=1)

    # Curvatura pelo ângulo entre segmentos consecutivos. Cabelo liso tem ângulo
    # perto de zero; cacheado passa de 30 graus por segmento.
    angulos = []
    if arranjo.shape[1] >= 3:
        a = segmentos[:, :-1]
        b = segmentos[:, 1:]
        cosseno = np.einsum("ijk,ijk->ij", a, b) / np.maximum(
            np.linalg.norm(a, axis=2) * np.linalg.norm(b, axis=2), 1e-9)
        angulos = np.degrees(np.arccos(np.clip(cosseno, -1.0, 1.0)))

    pontas = arranjo[:, -1, :]
    return {
        "fios": int(arranjo.shape[0]),
        "pontos_por_fio": int(arranjo.shape[1]),
        "comprimento_medio_m": round(float(comprimentos.mean()), 6),
        "desvio_de_comprimento": round(float(comprimentos.std()), 6),
        "curvatura_media_graus": round(float(np.mean(angulos)), 3) if len(angulos) else 0.0,
        "curvatura_maxima_graus": round(float(np.max(angulos)), 3) if len(angulos) else 0.0,
        # Dispersão das pontas: cabelo preso tem pontas juntas, solto tem espalhadas.
        "dispersao_das_pontas_m": round(float(pontas.std(axis=0).mean()), 6),
    }


def _preservar_comprimento(original: np.ndarray, novo: np.ndarray) -> np.ndarray:
    """Reprojeta cada ponto para manter o comprimento de segmento do original.

    É a restrição que separa cabelo de elástico: qualquer deformação pode mover a
    ponta, nenhuma pode esticar o fio. A raiz nunca se move.
    """
    resultado = novo.copy()
    alvos = np.linalg.norm(np.diff(original, axis=1), axis=2)
    resultado[:, 0, :] = original[:, 0, :]
    for i in range(1, original.shape[1]):
        direcao = resultado[:, i, :] - resultado[:, i - 1, :]
        norma = np.linalg.norm(direcao, axis=1, keepdims=True)
        norma = np.where(norma < 1e-9, 1e-9, norma)
        resultado[:, i, :] = resultado[:, i - 1, :] + direcao / norma * alvos[:, i - 1][:, None]
    return resultado


# ---- deformação --------------------------------------------------------------

def aplicar_gravidade(guias: np.ndarray, forca: float = 1.0,
                      rigidez: float = 0.5) -> tuple[np.ndarray, dict[str, Any]]:
    """Puxa cada fio para baixo, com a ponta cedendo mais que a raiz.

    O peso acumula ao longo do fio: o ponto perto da raiz sustenta todo o resto e
    quase não cede; a ponta não sustenta nada e cede tudo. Aplicar deslocamento
    igual em todos os pontos daria um fio rígido transladado, não um fio pendendo.
    """
    arranjo = _conferir(guias)
    if not 0.0 <= rigidez <= 1.0:
        raise CabeloInvalido(f"rigidez fora de 0..1: {rigidez}")

    total = arranjo.shape[1]
    # Quadrático ao longo do fio: é a forma de uma catenária pequena, e o que
    # produz a curva que o olho reconhece como cabelo caindo.
    perfil = (np.arange(total) / max(total - 1, 1)) ** 2
    deslocamento = perfil[None, :, None] * np.array([0.0, GRAVIDADE_Y, 0.0])
    deslocamento = deslocamento * forca * (1.0 - rigidez) * 0.01

    resultado = _preservar_comprimento(arranjo, arranjo + deslocamento)
    return resultado, {
        "forca": float(forca), "rigidez": float(rigidez),
        "queda_da_ponta_m": round(float(np.abs(resultado[:, -1, 1] - arranjo[:, -1, 1]).mean()), 6),
        "comprimento_preservado": _comprimento_preservado(arranjo, resultado),
    }


def _comprimento_preservado(antes: np.ndarray, depois: np.ndarray) -> dict[str, Any]:
    a = np.linalg.norm(np.diff(antes, axis=1), axis=2).sum(axis=1)
    b = np.linalg.norm(np.diff(depois, axis=1), axis=2).sum(axis=1)
    desvio = float(np.abs(b - a).max() / max(float(a.mean()), 1e-9))
    return {"desvio_relativo": round(desvio, 6),
            "dentro_da_tolerancia": bool(desvio <= TOLERANCIA_DE_COMPRIMENTO),
            "tolerancia": TOLERANCIA_DE_COMPRIMENTO}


def aplicar_vento(guias: np.ndarray, direcao: list[float], forca: float = 1.0,
                  turbulencia: float = 0.3, semente: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Empurra os fios na direção do vento, com ruído por fio.

    Sem turbulência, todos os fios se movem juntos e o cabelo lê como uma peça só.
    O ruído é por fio e constante ao longo dele, não por ponto: ruído por ponto
    daria um fio serrilhado, que é outro defeito.
    """
    arranjo = _conferir(guias)
    vetor = np.asarray(direcao, dtype=np.float64)
    norma = float(np.linalg.norm(vetor))
    if norma < 1e-9:
        raise CabeloInvalido("direção de vento com norma zero")
    vetor = vetor / norma

    rng = np.random.default_rng(semente)
    ruido = 1.0 + rng.normal(0.0, turbulencia, (arranjo.shape[0], 1, 1))
    perfil = (np.arange(arranjo.shape[1]) / max(arranjo.shape[1] - 1, 1)) ** 1.5

    empurrao = perfil[None, :, None] * vetor[None, None, :] * forca * 0.01 * ruido
    resultado = _preservar_comprimento(arranjo, arranjo + empurrao)
    return resultado, {
        "direcao": vetor.tolist(), "forca": float(forca),
        "turbulencia": float(turbulencia),
        "deslocamento_medio_m": round(
            float(np.linalg.norm(resultado[:, -1] - arranjo[:, -1], axis=1).mean()), 6),
        "comprimento_preservado": _comprimento_preservado(arranjo, resultado),
    }


def agrupar_mechas(guias: np.ndarray, forca: float = 0.5,
                   raio_m: float = 0.02) -> tuple[np.ndarray, dict[str, Any]]:
    """Puxa fios vizinhos uns para os outros, formando mechas.

    Cabelo real não é fio isolado: a gordura natural agrupa os fios, e um cabelo
    renderizado sem esse agrupamento parece pelo de escova. O agrupamento é pela
    raiz e cresce até a ponta, que é onde as mechas se separam de novo.
    """
    arranjo = _conferir(guias)
    if not 0.0 <= forca <= 1.0:
        raise CabeloInvalido(f"força fora de 0..1: {forca}")

    raizes = arranjo[:, 0, :]
    arvore = cKDTree(raizes)
    grupos = arvore.query_ball_point(raizes, raio_m)

    resultado = arranjo.copy()
    perfil = (np.arange(arranjo.shape[1]) / max(arranjo.shape[1] - 1, 1))
    tamanhos = []
    for i, vizinhos in enumerate(grupos):
        tamanhos.append(len(vizinhos))
        if len(vizinhos) < 2:
            continue
        centro = arranjo[vizinhos].mean(axis=0)
        resultado[i] = arranjo[i] + (centro - arranjo[i]) * (perfil[:, None] * forca)

    resultado = _preservar_comprimento(arranjo, resultado)
    return resultado, {
        "raio_m": float(raio_m), "forca": float(forca),
        "mecha_media": round(float(np.mean(tamanhos)), 2),
        "mecha_maxima": int(max(tamanhos)),
        "fios_isolados": int(sum(1 for t in tamanhos if t < 2)),
        "comprimento_preservado": _comprimento_preservado(arranjo, resultado),
    }


def aplicar_frizz(guias: np.ndarray, intensidade: float = 0.3,
                  semente: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    """Ruído alto ao longo de cada fio, crescendo para a ponta.

    Frizz é o oposto de mecha: separa. Aplicá-lo com a mesma amplitude na raiz
    faria o cabelo descolar do couro cabeludo.
    """
    arranjo = _conferir(guias)
    rng = np.random.default_rng(semente)
    perfil = (np.arange(arranjo.shape[1]) / max(arranjo.shape[1] - 1, 1)) ** 2
    ruido = rng.normal(0.0, 1.0, arranjo.shape) * perfil[None, :, None]

    resultado = _preservar_comprimento(arranjo, arranjo + ruido * intensidade * 0.005)
    return resultado, {
        "intensidade": float(intensidade),
        "desvio_da_ponta_m": round(
            float(np.linalg.norm(resultado[:, -1] - arranjo[:, -1], axis=1).mean()), 6),
        "curvatura_depois": medir_guias(resultado)["curvatura_media_graus"],
        "comprimento_preservado": _comprimento_preservado(arranjo, resultado),
    }


def encaracolar(guias: np.ndarray, voltas: float = 2.0,
                raio_m: float = 0.01) -> tuple[np.ndarray, dict[str, Any]]:
    """Enrola cada fio em hélice em torno do seu próprio eixo.

    O raio cresce da raiz para a ponta: cacho que começa no couro cabeludo levanta
    o cabelo da cabeça, e o resultado é um capacete, não um penteado.
    """
    arranjo = _conferir(guias)
    total = arranjo.shape[1]
    fase = np.linspace(0.0, voltas * 2 * np.pi, total)
    perfil = np.arange(total) / max(total - 1, 1)

    resultado = arranjo.copy()
    for i in range(arranjo.shape[0]):
        eixo = arranjo[i, -1] - arranjo[i, 0]
        norma = float(np.linalg.norm(eixo))
        if norma < 1e-9:
            continue
        eixo = eixo / norma
        # Base ortonormal em torno do eixo do fio.
        auxiliar = np.array([1.0, 0.0, 0.0]) if abs(eixo[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = np.cross(eixo, auxiliar)
        u = u / max(float(np.linalg.norm(u)), 1e-9)
        v = np.cross(eixo, u)
        offset = (np.cos(fase)[:, None] * u + np.sin(fase)[:, None] * v)
        resultado[i] = arranjo[i] + offset * raio_m * perfil[:, None]

    resultado = _preservar_comprimento(arranjo, resultado)
    return resultado, {
        "voltas": float(voltas), "raio_m": float(raio_m),
        "curvatura_depois_graus": medir_guias(resultado)["curvatura_media_graus"],
        "comprimento_preservado": _comprimento_preservado(arranjo, resultado),
    }


def cortar(guias: np.ndarray, altura_m: float) -> tuple[np.ndarray, dict[str, Any]]:
    """Corta os fios num plano horizontal, como tesoura.

    Pontos acima do plano são puxados para ele em vez de removidos: remover mudaria
    o número de pontos por fio e quebraria qualquer operação que assume forma
    retangular.
    """
    arranjo = _conferir(guias)
    resultado = arranjo.copy()
    acima = resultado[:, :, 1] > altura_m
    cortados = int(np.count_nonzero(acima))
    resultado[:, :, 1] = np.minimum(resultado[:, :, 1], altura_m)

    return resultado, {
        "altura_m": float(altura_m),
        "pontos_cortados": cortados,
        "fios_afetados": int(np.count_nonzero(acima.any(axis=1))),
        "comprimento_depois_m": round(
            float(np.linalg.norm(np.diff(resultado, axis=1), axis=2).sum(axis=1).mean()), 6),
    }


# ---- conversão ---------------------------------------------------------------

def converter_em_cards(guias: np.ndarray,
                       largura_m: float = 0.004) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Transforma cada fio numa fita de quads — o que motor de jogo renderiza.

    A largura é constante ao longo do card. Estreitar na ponta ficaria mais bonito
    e custaria vértices que o orçamento de polígonos raramente tem; quem quiser
    afinamento faz com a textura, que é de graça.
    """
    arranjo = _conferir(guias)
    if largura_m <= 0:
        raise CabeloInvalido(f"largura precisa ser positiva: {largura_m}")

    vertices: list[np.ndarray] = []
    faces: list[list[int]] = []
    uv: list[list[float]] = []

    for fio in arranjo:
        base = len(vertices)
        segmentos = np.diff(fio, axis=0)
        for i, ponto in enumerate(fio):
            direcao = segmentos[min(i, len(segmentos) - 1)]
            norma = float(np.linalg.norm(direcao))
            direcao = direcao / norma if norma > 1e-9 else np.array([0.0, 1.0, 0.0])
            lateral = np.cross(direcao, [0.0, 0.0, 1.0])
            norma_lateral = float(np.linalg.norm(lateral))
            if norma_lateral < 1e-9:
                lateral = np.array([1.0, 0.0, 0.0])
            else:
                lateral = lateral / norma_lateral

            vertices.append(ponto - lateral * largura_m / 2)
            vertices.append(ponto + lateral * largura_m / 2)
            v = i / max(len(fio) - 1, 1)
            uv.extend([[0.0, v], [1.0, v]])

        for i in range(len(fio) - 1):
            a = base + i * 2
            faces.append([a, a + 1, a + 2])
            faces.append([a + 1, a + 3, a + 2])

    malha = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces),
                            process=False)
    malha.visual = trimesh.visual.TextureVisuals(uv=np.array(uv))
    return malha, {
        "fios": int(arranjo.shape[0]),
        "cards": int(arranjo.shape[0]),
        "vertices": int(len(vertices)),
        "faces": int(len(faces)),
        "largura_m": float(largura_m),
        # É o número que decide se o cabelo cabe no orçamento da cena.
        "triangulos_por_fio": int(len(faces) / max(arranjo.shape[0], 1)),
    }


def gerar_lods(guias: np.ndarray, niveis: int = 3) -> dict[str, Any]:
    """Cadeia de níveis por descarte de fios, mantendo a distribuição.

    Descartar fios alternados preserva a cobertura do couro cabeludo. Descartar os
    últimos deixaria metade da cabeça careca, que é o defeito que aparece assim que
    a câmera gira.
    """
    arranjo = _conferir(guias)
    if not 1 <= niveis <= 6:
        raise CabeloInvalido(f"níveis fora de 1..6: {niveis}")

    cadeia = []
    for nivel in range(niveis + 1):
        passo = 2 ** nivel
        selecao = arranjo[::passo]
        cadeia.append({"nivel": nivel, "fios": int(len(selecao)),
                       "fracao": round(len(selecao) / len(arranjo), 4)})
    return {"niveis": cadeia, "fios_originais": int(len(arranjo)),
            "metodo": "descarte alternado preserva a cobertura; descartar os "
                      "últimos deixaria metade da cabeça careca"}


def validar_cabelo(guias: np.ndarray, couro: trimesh.Trimesh | None = None) -> list[dict[str, str]]:
    """Defeitos que aparecem no render e não no editor."""
    arranjo = _conferir(guias)
    achados: list[dict[str, str]] = []

    comprimentos = np.linalg.norm(np.diff(arranjo, axis=1), axis=2).sum(axis=1)
    if float(comprimentos.min()) < 1e-4:
        achados.append({
            "codigo": "FIO_DE_COMPRIMENTO_ZERO",
            "detalhe": f"{int(np.count_nonzero(comprimentos < 1e-4))} fios",
            "efeito": "card degenerado: triângulo sem área, artefato de sombreamento",
        })

    if couro is not None and len(couro.faces):
        distancia = trimesh.proximity.closest_point(couro, arranjo[:, 0, :])[1]
        soltas = int(np.count_nonzero(distancia > 0.01))
        if soltas:
            achados.append({
                "codigo": "RAIZ_SOLTA",
                "detalhe": f"{soltas} raízes a mais de 1 cm do couro",
                "efeito": "o cabelo flutua acima da cabeça quando o personagem move",
            })

    if arranjo.shape[1] >= 3:
        segmentos = np.diff(arranjo, axis=1)
        a, b = segmentos[:, :-1], segmentos[:, 1:]
        cosseno = np.einsum("ijk,ijk->ij", a, b) / np.maximum(
            np.linalg.norm(a, axis=2) * np.linalg.norm(b, axis=2), 1e-9)
        dobras = int(np.count_nonzero(cosseno < -0.5))
        if dobras:
            achados.append({
                "codigo": "FIO_DOBRADO",
                "detalhe": f"{dobras} segmentos dobrando mais de 120 graus",
                "efeito": "o card se atravessa e a normal inverte no meio do fio",
            })
    return achados

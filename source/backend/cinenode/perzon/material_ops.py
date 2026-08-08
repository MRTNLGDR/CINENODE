"""Material PBR do PERZON — mapas derivados do pixel, com validação física.

Nenhum mapa aqui é gerado por ruído ou por preset. Todos saem de uma medida sobre
a imagem de entrada, e a validação compara contra limites que vêm da física do
render, não de gosto: albedo fora de 30–240 sRGB não existe em material real, e
um normal cuja soma vetorial não dá 1 produz iluminação errada em qualquer motor.
"""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# Faixa de albedo fisicamente plausível, em 8 bits sRGB. Nada natural reflete
# menos que ~3% (carvão) nem mais que ~95% (neve fresca); fora disso, o material
# devolve mais luz do que recebe e o render acumula energia a cada quique.
ALBEDO_MINIMO = 30
ALBEDO_MAXIMO = 240

# Limiar de luz assada, calibrado por medição em rampas conhecidas sobre a mesma
# textura de ruído: plana 0,019 · rampa 0,7–1,0 → 0,145 · rampa 0,5–1,0 → 0,241 ·
# rampa 0,25–1,0 → 0,362. O corte em 0,20 deixa passar vinheta leve e acusa a
# partir de 2:1 de brilho de um lado ao outro, que já é a luz da foto original.
LIMIAR_LUZ_ASSADA = 0.20


class ImagemInvalida(ValueError):
    """A imagem não sustenta a operação pedida."""


def carregar(caminho: str) -> np.ndarray:
    imagem = cv2.imread(str(caminho), cv2.IMREAD_UNCHANGED)
    if imagem is None:
        raise ImagemInvalida(f"não foi possível ler {caminho} como imagem")
    if imagem.ndim == 2:
        imagem = cv2.cvtColor(imagem, cv2.COLOR_GRAY2BGR)
    if imagem.shape[2] == 4:
        imagem = cv2.cvtColor(imagem, cv2.COLOR_BGRA2BGR)
    if imagem.dtype != np.uint8:
        imagem = cv2.normalize(imagem, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return imagem


def _luminancia(imagem: np.ndarray) -> np.ndarray:
    """Luminância perceptual Rec.709, não a média dos canais.

    A média trata o azul como igual ao verde. O olho não faz isso, e um mapa de
    altura derivado da média inverte o relevo em qualquer superfície colorida.
    """
    bgr = imagem.astype(np.float32) / 255.0
    return (0.0722 * bgr[:, :, 0] + 0.7152 * bgr[:, :, 1] + 0.2126 * bgr[:, :, 2])


def _amplitude_baixa_frequencia(luminancia: np.ndarray) -> float:
    """Quanta variação lenta de brilho existe na textura — a marca da luz assada.

    Uma textura de material puro varia rápido (poro, fio, grão) e quase nada de um
    canto ao outro. Uma foto carrega a luz da cena original: um lado claro, outro
    escuro, e essa rampa soma com a luz do render, dando duas sombras ao objeto.

    Reduzir a imagem por área É o filtro passa-baixa, e sem o defeito do borrão
    gaussiano de raio grande: medido aqui, um sigma de 42 px puxava as pontas de
    uma rampa 0,059–0,769 para 0,148–0,474 e escondia a rampa que devia acusar.
    O corte em p2/p98 descarta respingo isolado sem descartar a rampa.
    """
    pequeno = cv2.resize(luminancia, (32, 32), interpolation=cv2.INTER_AREA)
    return float(np.percentile(pequeno, 98) - np.percentile(pequeno, 2))


# ---- análise ----------------------------------------------------------------

def analisar_albedo(imagem: np.ndarray) -> dict[str, Any]:
    """Diz se a textura serve como cor base, e por que não serve quando não serve."""
    canais = imagem.reshape(-1, 3)
    luminancia = _luminancia(imagem)

    escuro = float(np.count_nonzero(canais.min(axis=1) < ALBEDO_MINIMO) / len(canais))
    claro = float(np.count_nonzero(canais.max(axis=1) > ALBEDO_MAXIMO) / len(canais))

    amplitude_baixa = _amplitude_baixa_frequencia(luminancia)

    return {
        "resolucao": [int(imagem.shape[1]), int(imagem.shape[0])],
        "luminancia_media": round(float(luminancia.mean()), 6),
        "fracao_abaixo_do_minimo": round(escuro, 6),
        "fracao_acima_do_maximo": round(claro, 6),
        "amplitude_baixa_frequencia": round(amplitude_baixa, 6),
        "iluminacao_assada": bool(amplitude_baixa > LIMIAR_LUZ_ASSADA),
        "saturacao_media": round(float(cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)[:, :, 1].mean()), 3),
    }


def medir_continuidade(imagem: np.ndarray) -> dict[str, Any]:
    """Descontinuidade entre bordas opostas — o que produz grade visível no tile.

    Compara a última coluna com a primeira e a última linha com a primeira. Se o
    material se repete, essas bordas encostam uma na outra na superfície final.
    """
    img = imagem.astype(np.float32) / 255.0
    erro_h = float(np.abs(img[:, -1] - img[:, 0]).mean())
    erro_v = float(np.abs(img[-1, :] - img[0, :]).mean())

    # Referência: diferença média entre colunas vizinhas quaisquer. Uma textura
    # muito detalhada tem erro de borda alto sem estar quebrada, e comparar com o
    # contraste interno é o que separa um caso do outro.
    ruido_interno = float(np.abs(img[:, 1:] - img[:, :-1]).mean())
    razao = erro_h / ruido_interno if ruido_interno > 1e-9 else float("inf")

    return {
        "erro_horizontal": round(erro_h, 6),
        "erro_vertical": round(erro_v, 6),
        "contraste_interno": round(ruido_interno, 6),
        "razao_borda_interno": round(razao, 4) if razao != float("inf") else None,
        # Duas vezes o contraste interno é onde a costura passa a ser vista como
        # linha, e não como parte do desenho.
        "tileable": bool(razao < 2.0),
    }


# ---- geração de mapas -------------------------------------------------------

def gerar_normal(imagem: np.ndarray, forca: float = 2.0) -> tuple[np.ndarray, dict[str, Any]]:
    """Normal tangente do gradiente de luminância, por Sobel.

    Convenção OpenGL (Y para cima). DirectX espera Y invertido — quem exportar
    para Unreal precisa inverter o canal verde, e isso vai na métrica para que a
    escolha seja consciente em vez de virar bug de iluminação invertida.
    """
    altura = _luminancia(imagem)
    dx = cv2.Sobel(altura, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(altura, cv2.CV_32F, 0, 1, ksize=3)

    normal = np.dstack([-dx * forca, -dy * forca, np.ones_like(altura)])
    comprimento = np.linalg.norm(normal, axis=2, keepdims=True)
    normal = normal / np.maximum(comprimento, 1e-9)

    saida = ((normal * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    # Volta para BGR porque é assim que o cv2 grava.
    saida = saida[:, :, ::-1]

    inclinacao = np.degrees(np.arccos(np.clip(normal[:, :, 2], -1, 1)))
    return saida, {
        "convencao": "OpenGL (Y+). Para DirectX, inverter o canal verde.",
        "forca": float(forca),
        "inclinacao_media_graus": round(float(inclinacao.mean()), 4),
        "inclinacao_maxima_graus": round(float(inclinacao.max()), 4),
        # Um normal cuja soma vetorial não dá 1 produz iluminação errada. Como
        # normalizamos acima, isto tem de dar ~1 — é a conferência do cálculo.
        "norma_media": round(float(np.linalg.norm(normal, axis=2).mean()), 6),
    }


def gerar_rugosidade(imagem: np.ndarray, janela: int = 9) -> tuple[np.ndarray, dict[str, Any]]:
    """Rugosidade da variância local: micro-detalhe espalha luz, liso reflete.

    O desvio padrão numa janela mede exatamente isso. Uma área de poro de pele tem
    variância alta e deve ficar fosca; uma área de plástico polido tem variância
    baixa e deve refletir.
    """
    if janela % 2 == 0:
        janela += 1
    luz = _luminancia(imagem)
    media = cv2.blur(luz, (janela, janela))
    media_quadrado = cv2.blur(luz * luz, (janela, janela))
    variancia = np.maximum(media_quadrado - media * media, 0.0)
    desvio = np.sqrt(variancia)

    if desvio.max() > 1e-9:
        rugosidade = desvio / desvio.max()
    else:
        rugosidade = np.zeros_like(desvio)

    # Piso em 0,04: rugosidade zero é espelho perfeito, que não existe. Motores
    # de render costumam produzir realce especular infinito nesse valor.
    rugosidade = np.clip(rugosidade, 0.04, 1.0)
    saida = (rugosidade * 255).astype(np.uint8)

    return saida, {
        "janela": int(janela),
        "rugosidade_media": round(float(rugosidade.mean()), 6),
        "rugosidade_minima": round(float(rugosidade.min()), 6),
        "rugosidade_maxima": round(float(rugosidade.max()), 6),
        "piso_aplicado": 0.04,
    }


def gerar_oclusao(imagem: np.ndarray, raio: int = 21) -> tuple[np.ndarray, dict[str, Any]]:
    """Oclusão pela cavidade do mapa de altura.

    Não é ray tracing: é a diferença entre a altura do ponto e a altura média da
    vizinhança. Onde o ponto está mais fundo que os vizinhos, ele recebe menos luz
    ambiente. Aproximação barata que acerta o essencial em textura de superfície,
    e que erra em geometria com auto-oclusão real — vale dizer isso aqui.
    """
    if raio % 2 == 0:
        raio += 1
    altura = _luminancia(imagem)
    vizinhanca = cv2.GaussianBlur(altura, (raio, raio), 0)
    cavidade = altura - vizinhanca

    if cavidade.std() > 1e-9:
        oclusao = np.clip(0.5 + cavidade / (4 * cavidade.std()), 0.0, 1.0)
    else:
        oclusao = np.ones_like(cavidade)

    saida = (oclusao * 255).astype(np.uint8)
    return saida, {
        "raio": int(raio),
        "oclusao_media": round(float(oclusao.mean()), 6),
        "fracao_ocluida": round(float(np.count_nonzero(oclusao < 0.5) / oclusao.size), 6),
        "metodo": "cavidade do mapa de altura; não substitui oclusão por traçado de raio",
    }


# ---- validação --------------------------------------------------------------

def validar_pbr(imagem: np.ndarray) -> list[dict[str, str]]:
    """Defeitos que quebram render fisicamente correto, com o efeito de cada um."""
    achados: list[dict[str, str]] = []
    analise = analisar_albedo(imagem)

    if analise["fracao_abaixo_do_minimo"] > 0.05:
        achados.append({
            "codigo": "ALBEDO_ESCURO_DEMAIS",
            "detalhe": f"{analise['fracao_abaixo_do_minimo']:.1%} dos pixels abaixo de "
                       f"{ALBEDO_MINIMO}",
            "efeito": "a superfície absorve luz demais e fica preta na sombra",
        })
    if analise["fracao_acima_do_maximo"] > 0.05:
        achados.append({
            "codigo": "ALBEDO_CLARO_DEMAIS",
            "detalhe": f"{analise['fracao_acima_do_maximo']:.1%} dos pixels acima de "
                       f"{ALBEDO_MAXIMO}",
            "efeito": "devolve mais luz do que recebe; o render acumula energia a cada quique",
        })
    if analise["iluminacao_assada"]:
        achados.append({
            "codigo": "ILUMINACAO_ASSADA",
            "detalhe": f"amplitude de baixa frequência {analise['amplitude_baixa_frequencia']:.3f}",
            "efeito": "a luz da foto original soma com a luz da cena; o objeto ganha duas sombras",
        })
    return achados

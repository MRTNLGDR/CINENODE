"""Headshot do PERZON — a foto serve ou não serve, medido antes de reconstruir.

Reconstrução facial a partir de foto ruim produz um rosto ruim, e a culpa acaba
recaindo no algoritmo de reconstrução. Este módulo mede a foto antes: nitidez,
exposição, frontalidade, resolução do rosto no quadro. Cada portão devolve o
número e o motivo, para que rejeitar uma foto seja uma decisão explicável.
"""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# Variância do laplaciano abaixo disto é foto borrada. O valor é conhecido em
# visão computacional para imagens de 8 bits; medido aqui numa foto nítida
# reduzida a 1/4 da resolução, a variância cai de ~900 para ~90.
NITIDEZ_MINIMA = 100.0

# O rosto precisa ocupar altura suficiente para haver detalhe onde importa. Abaixo
# de 200 px de altura de rosto, olho e boca ficam com poucas dezenas de pixels e a
# reconstrução inventa a textura que não está lá.
ALTURA_MINIMA_DO_ROSTO = 200

# Acima disto o rosto está virado demais para servir como frontal. É o mesmo
# limite do motor de medida: passados 35 graus a proporção horizontal encurta por
# projeção e a medida deixa de ser antropometria.
GUINADA_MAXIMA_GRAUS = 15.0


class FotoInvalida(ValueError):
    """A foto não sustenta reconstrução."""


def medir_nitidez(imagem: np.ndarray) -> dict[str, Any]:
    """Variância do laplaciano — quanto detalhe de alta frequência existe.

    Uma foto desfocada perde exatamente essa banda. Medir contraste global não
    serviria: uma foto borrada de cena contrastada tem contraste alto e detalhe
    nenhum.
    """
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem
    variancia = float(cv2.Laplacian(cinza, cv2.CV_64F).var())
    return {
        "nitidez": round(variancia, 2),
        "minimo": NITIDEZ_MINIMA,
        "aprovado": bool(variancia >= NITIDEZ_MINIMA),
        "metodo": "variância do laplaciano; contraste global não distingue "
                  "cena contrastada de foto borrada",
    }


def medir_exposicao(imagem: np.ndarray) -> dict[str, Any]:
    """Estourado e apagado contam separado, porque a perda é diferente.

    Pixel estourado perdeu a informação para sempre — não há o que recuperar. Pixel
    apagado ainda tem sinal enterrado no ruído. Somar os dois num "erro de
    exposição" só esconderia qual dos dois problemas a foto tem.
    """
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem
    total = cinza.size
    estourado = float(np.count_nonzero(cinza >= 250) / total)
    apagado = float(np.count_nonzero(cinza <= 5) / total)
    media = float(cinza.mean())

    problemas: list[str] = []
    if estourado > 0.05:
        problemas.append(f"{estourado:.1%} de pixels estourados: a informação sumiu")
    if apagado > 0.10:
        problemas.append(f"{apagado:.1%} de pixels apagados: sem sinal na sombra")
    if not 60 <= media <= 200:
        problemas.append(f"luminância média {media:.0f} fora da faixa útil 60..200")

    return {
        "luminancia_media": round(media, 2),
        "fracao_estourada": round(estourado, 5),
        "fracao_apagada": round(apagado, 5),
        "contraste": round(float(cinza.std()), 2),
        "problemas": problemas,
        "aprovado": not problemas,
    }


def medir_enquadramento(imagem: np.ndarray, pontos: np.ndarray) -> dict[str, Any]:
    """Onde o rosto está no quadro e quanto do quadro ele ocupa.

    Rosto pequeno no canto é o caso que mais engana: a foto parece boa em
    miniatura e não tem pixel nenhum onde a reconstrução precisa.
    """
    pontos = np.asarray(pontos, dtype=np.float64)
    if len(pontos) < 3:
        raise FotoInvalida("landmarks insuficientes para medir enquadramento")

    altura_img, largura_img = imagem.shape[:2]
    minimo, maximo = pontos[:, :2].min(axis=0), pontos[:, :2].max(axis=0)
    largura_rosto = float(maximo[0] - minimo[0])
    altura_rosto = float(maximo[1] - minimo[1])
    centro = ((minimo + maximo) / 2)

    return {
        "resolucao": [int(largura_img), int(altura_img)],
        "rosto_px": [round(largura_rosto, 1), round(altura_rosto, 1)],
        "ocupacao": round(float(largura_rosto * altura_rosto) / (largura_img * altura_img), 4),
        # Deslocamento do centro do rosto em relação ao centro do quadro, em
        # fração da dimensão. Serve para o corte automático não decapitar.
        "desvio_do_centro": [round(float(centro[0] / largura_img - 0.5), 4),
                             round(float(centro[1] / altura_img - 0.5), 4)],
        "altura_minima": ALTURA_MINIMA_DO_ROSTO,
        "aprovado": bool(altura_rosto >= ALTURA_MINIMA_DO_ROSTO),
    }


def medir_frontalidade(matriz_transformacao: Any) -> dict[str, Any]:
    """Ângulos da cabeça a partir da matriz que o FaceLandmarker devolve.

    Uma foto "frontal" com 20 graus de guinada encurta o lado virado por projeção.
    Reconstruir a partir dela produz um rosto assimétrico que a pessoa não tem.
    """
    matriz = np.asarray(matriz_transformacao, dtype=np.float64).reshape(4, 4)
    rotacao = matriz[:3, :3]

    # Decomposição ZYX. O sinal de `sy` próximo de zero é o caso degenerado
    # (gimbal lock), tratado separadamente para não devolver NaN silencioso.
    sy = float(np.sqrt(rotacao[0, 0] ** 2 + rotacao[1, 0] ** 2))
    if sy > 1e-6:
        pitch = float(np.degrees(np.arctan2(rotacao[2, 1], rotacao[2, 2])))
        yaw = float(np.degrees(np.arctan2(-rotacao[2, 0], sy)))
        roll = float(np.degrees(np.arctan2(rotacao[1, 0], rotacao[0, 0])))
    else:
        pitch = float(np.degrees(np.arctan2(-rotacao[1, 2], rotacao[1, 1])))
        yaw = float(np.degrees(np.arctan2(-rotacao[2, 0], sy)))
        roll = 0.0

    frontal = abs(yaw) <= GUINADA_MAXIMA_GRAUS and abs(pitch) <= GUINADA_MAXIMA_GRAUS
    return {
        "guinada_graus": round(yaw, 3),
        "inclinacao_graus": round(pitch, 3),
        "rotacao_graus": round(roll, 3),
        "limite_graus": GUINADA_MAXIMA_GRAUS,
        "frontal": bool(frontal),
        # Classificação de tomada: é o que decide para qual slot a foto vai num
        # conjunto frontal + perfil esquerdo + perfil direito.
        "tomada": ("frontal" if frontal else
                   "perfil_esquerdo" if yaw < -GUINADA_MAXIMA_GRAUS else
                   "perfil_direito" if yaw > GUINADA_MAXIMA_GRAUS else
                   "inclinada"),
    }


def segmentar_regioes(imagem: np.ndarray, pontos: np.ndarray) -> dict[str, Any]:
    """Máscaras de pele, cabelo e fundo.

    Pele por faixa de matiz e saturação em HSV, que é robusta a variação de
    iluminação de um jeito que RGB não é. Cabelo por luminância baixa acima da
    linha dos olhos. Não é segmentação semântica treinada — é limiar sobre cor, e
    o relatório diz isso para ninguém confundir com um modelo de matting.
    """
    pontos = np.asarray(pontos, dtype=np.float64)
    altura, largura = imagem.shape[:2]
    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)

    # Faixa de pele em HSV. Cobre tons claros a escuros porque o matiz da pele
    # humana varia pouco; o que varia é o valor, e por isso o limite inferior de
    # V é baixo.
    pele = cv2.inRange(hsv, np.array([0, 30, 40]), np.array([25, 180, 255]))
    pele |= cv2.inRange(hsv, np.array([160, 30, 40]), np.array([180, 180, 255]))
    pele = cv2.morphologyEx(pele, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    # Convexo dos landmarks: a região que sabemos ser rosto. Serve de âncora para
    # separar pele do rosto de pele de mão ou de fundo cor de pele.
    casco = cv2.convexHull(pontos[:, :2].astype(np.int32))
    rosto = np.zeros((altura, largura), np.uint8)
    cv2.fillConvexPoly(rosto, casco, 255)

    topo_dos_olhos = int(pontos[:, 1].min())
    acima = np.zeros((altura, largura), np.uint8)
    acima[:max(topo_dos_olhos, 1), :] = 255
    escuro = cv2.inRange(hsv[:, :, 2], 0, 90)
    cabelo = cv2.bitwise_and(acima, escuro)

    fundo = cv2.bitwise_not(cv2.bitwise_or(cv2.bitwise_or(pele, rosto), cabelo))
    total = altura * largura
    return {
        "fracao_pele": round(float(np.count_nonzero(pele) / total), 4),
        "fracao_rosto": round(float(np.count_nonzero(rosto) / total), 4),
        "fracao_cabelo": round(float(np.count_nonzero(cabelo) / total), 4),
        "fracao_fundo": round(float(np.count_nonzero(fundo) / total), 4),
        "metodo": "limiar em HSV com âncora no convexo dos landmarks; "
                  "não é segmentação semântica treinada",
    }


def alinhar_pelos_olhos(imagem: np.ndarray, pontos: np.ndarray,
                        tamanho: int = 512) -> tuple[np.ndarray, dict[str, Any]]:
    """Recorta e roda a foto para os olhos ficarem na horizontal e no mesmo lugar.

    Alinhar pelos olhos, e não pela caixa do rosto, é o que torna duas fotos
    comparáveis: a caixa muda de tamanho com a expressão, a distância interpupilar
    não muda.
    """
    from .face_ops import OLHO_D_EXTERNO, OLHO_D_INTERNO, OLHO_E_EXTERNO, OLHO_E_INTERNO

    pontos = np.asarray(pontos, dtype=np.float64)
    olho_e = (pontos[OLHO_E_INTERNO][:2] + pontos[OLHO_E_EXTERNO][:2]) / 2
    olho_d = (pontos[OLHO_D_INTERNO][:2] + pontos[OLHO_D_EXTERNO][:2]) / 2

    delta = olho_d - olho_e
    angulo = float(np.degrees(np.arctan2(delta[1], delta[0])))
    distancia = float(np.linalg.norm(delta))
    if distancia < 1e-6:
        raise FotoInvalida("os dois olhos coincidem: não há como alinhar")

    # Os olhos ficam a 30% da largura de cada borda, e a 38% da altura. É a
    # convenção usada em bancos de rosto alinhados, e o que torna o recorte
    # reprodutível entre fotos diferentes.
    alvo = tamanho * 0.40
    escala = alvo / distancia
    centro = tuple(((olho_e + olho_d) / 2).tolist())

    matriz = cv2.getRotationMatrix2D(centro, angulo, escala)
    matriz[0, 2] += tamanho / 2 - centro[0]
    matriz[1, 2] += tamanho * 0.38 - centro[1]
    alinhada = cv2.warpAffine(imagem, matriz, (tamanho, tamanho),
                              flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return alinhada, {
        "angulo_corrigido_graus": round(angulo, 3),
        "escala_aplicada": round(escala, 5),
        "distancia_interpupilar_px": round(distancia, 2),
        "tamanho": int(tamanho),
    }


def comparar_fotos(medidas: list[dict[str, Any]]) -> dict[str, Any]:
    """Confronta as medidas de várias fotos da mesma pessoa.

    Divergência alta entre fotos significa que uma delas não é a mesma pessoa, ou
    que a perspectiva de uma está distorcendo. Reconstruir a média das duas
    produziria um rosto que não é nenhum dos dois.
    """
    if len(medidas) < 2:
        raise FotoInvalida(f"comparar exige pelo menos 2 fotos, vieram {len(medidas)}")

    chaves = set(medidas[0])
    for medida in medidas[1:]:
        chaves &= set(medida)
    numericas = [k for k in sorted(chaves)
                 if all(isinstance(m.get(k), (int, float)) and not isinstance(m[k], bool)
                        for m in medidas)]
    if not numericas:
        raise FotoInvalida("as fotos não têm nenhuma medida numérica em comum")

    divergencias = []
    for chave in numericas:
        valores = np.array([float(m[chave]) for m in medidas])
        media = float(valores.mean())
        if abs(media) < 1e-9:
            continue
        variacao = float(valores.std() / abs(media))
        divergencias.append({"medida": chave, "media": round(media, 5),
                             "variacao_relativa": round(variacao, 5)})

    piores = sorted(divergencias, key=lambda d: -d["variacao_relativa"])[:5]
    maior = piores[0]["variacao_relativa"] if piores else 0.0
    return {
        "fotos": len(medidas),
        "medidas_comparadas": len(divergencias),
        "maior_divergencia": round(maior, 5),
        "piores": piores,
        # 15% de variação numa proporção facial é mais do que expressão e
        # perspectiva explicam juntas.
        "coerentes": bool(maior < 0.15),
    }


def avaliar(imagem: np.ndarray, pontos: np.ndarray | None = None,
            matriz: Any = None) -> dict[str, Any]:
    """Portão único: a foto serve para reconstrução, e por quê.

    Reunir os portões numa resposta só é o que permite recusar a foto uma vez, com
    a lista inteira do que está errado, em vez de fazer o usuário corrigir um
    problema por vez e reenviar.
    """
    relatorio: dict[str, Any] = {"nitidez": medir_nitidez(imagem),
                                 "exposicao": medir_exposicao(imagem)}
    if pontos is not None:
        relatorio["enquadramento"] = medir_enquadramento(imagem, pontos)
        relatorio["regioes"] = segmentar_regioes(imagem, pontos)
    if matriz is not None:
        relatorio["frontalidade"] = medir_frontalidade(matriz)

    reprovas: list[dict[str, str]] = []
    if not relatorio["nitidez"]["aprovado"]:
        reprovas.append({
            "codigo": "FOTO_BORRADA",
            "detalhe": f"nitidez {relatorio['nitidez']['nitidez']:.0f} "
                       f"abaixo de {NITIDEZ_MINIMA:.0f}",
            "efeito": "a reconstrução inventa o detalhe que a foto não tem"})
    for problema in relatorio["exposicao"]["problemas"]:
        reprovas.append({"codigo": "EXPOSICAO_RUIM", "detalhe": problema,
                         "efeito": "a textura assada carrega o erro para o material"})
    if "enquadramento" in relatorio and not relatorio["enquadramento"]["aprovado"]:
        reprovas.append({
            "codigo": "ROSTO_PEQUENO",
            "detalhe": f"{relatorio['enquadramento']['rosto_px'][1]:.0f} px de altura, "
                       f"mínimo {ALTURA_MINIMA_DO_ROSTO}",
            "efeito": "olho e boca ficam com poucas dezenas de pixels"})
    if "frontalidade" in relatorio and not relatorio["frontalidade"]["frontal"]:
        reprovas.append({
            "codigo": "ROSTO_NAO_FRONTAL",
            "detalhe": f"guinada {relatorio['frontalidade']['guinada_graus']:.1f}°, "
                       f"limite {GUINADA_MAXIMA_GRAUS}°",
            "efeito": "a projeção encurta o lado virado e o rosto sai assimétrico"})

    relatorio["reprovas"] = reprovas
    relatorio["aprovada"] = not reprovas
    return relatorio

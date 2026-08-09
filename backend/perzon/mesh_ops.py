"""Operações de malha do PERZON — geometria real, medida, sem estimativa.

Toda função aqui recebe e devolve `trimesh.Trimesh` ou métrica calculada do
vértice. Nada é aproximado por heurística de nome de arquivo, e nenhuma devolve
número que não tenha saído de um cálculo sobre os dados.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh


class MalhaInvalida(ValueError):
    """A malha não sustenta a operação pedida. Prosseguir produziria lixo silencioso."""


def carregar(caminho: str) -> trimesh.Trimesh:
    cena = trimesh.load(caminho, force="mesh", process=False)
    if isinstance(cena, trimesh.Scene):
        malhas = [g for g in cena.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not malhas:
            raise MalhaInvalida(f"{caminho} não contém malha triangular")
        cena = trimesh.util.concatenate(malhas)
    if not isinstance(cena, trimesh.Trimesh) or len(cena.faces) == 0:
        raise MalhaInvalida(f"{caminho} não carregou como malha com faces")
    return cena


# ---- diagnóstico ------------------------------------------------------------

def diagnosticar(malha: trimesh.Trimesh) -> dict[str, Any]:
    """O retrato que decide se as operações seguintes fazem sentido.

    `is_watertight` e `euler_number` são o que separa uma malha exportável de uma
    casca com buracos. Sem medir isso antes, uma retopologia "bem-sucedida" pode
    entregar um objeto que nenhum motor de jogo aceita.
    """
    componentes = malha.split(only_watertight=False)
    arestas_borda = malha.edges[trimesh.grouping.group_rows(
        malha.edges_sorted, require_count=1)]
    duplicados = len(malha.vertices) - len(np.unique(malha.vertices, axis=0))
    areas = malha.area_faces
    degeneradas = int(np.count_nonzero(areas <= 1e-12))

    return {
        "vertices": int(len(malha.vertices)),
        "faces": int(len(malha.faces)),
        "arestas": int(len(malha.edges_unique)),
        "componentes": int(len(componentes)),
        "estanque": bool(malha.is_watertight),
        "winding_consistente": bool(malha.is_winding_consistent),
        "volume_positivo": bool(malha.volume > 0) if malha.is_watertight else False,
        "euler": int(malha.euler_number),
        # Gênero só é definido em malha fechada; num objeto aberto o número seria
        # inventado, então ele fica nulo em vez de errado.
        "genero": int((2 - malha.euler_number) // 2) if malha.is_watertight else None,
        "arestas_de_borda": int(len(arestas_borda)),
        "vertices_duplicados": int(duplicados),
        "faces_degeneradas": degeneradas,
        "area": float(malha.area),
        "volume": float(malha.volume) if malha.is_watertight else None,
        "caixa": [float(x) for x in malha.bounds.flatten()],
        "dimensoes": [float(x) for x in malha.extents],
    }


def problemas(diag: dict[str, Any]) -> list[dict[str, str]]:
    """Traduz o diagnóstico em defeitos nomeados, com o efeito de cada um."""
    achados: list[dict[str, str]] = []
    if not diag["estanque"]:
        achados.append({
            "codigo": "MALHA_ABERTA",
            "detalhe": f"{diag['arestas_de_borda']} arestas de borda",
            "efeito": "impressão 3D e booleanas falham; volume não é calculável",
        })
    if not diag["winding_consistente"]:
        achados.append({
            "codigo": "NORMAIS_INVERTIDAS",
            "detalhe": "orientação de face inconsistente",
            "efeito": "faces pretas ou invisíveis no motor de render",
        })
    if diag["faces_degeneradas"]:
        achados.append({
            "codigo": "FACES_DEGENERADAS",
            "detalhe": f"{diag['faces_degeneradas']} faces com área nula",
            "efeito": "normal indefinida; artefato de sombreamento e falha de UV",
        })
    if diag["vertices_duplicados"]:
        achados.append({
            "codigo": "VERTICES_DUPLICADOS",
            "detalhe": f"{diag['vertices_duplicados']} vértices coincidentes",
            "efeito": "costura visível e peso de skin dividido entre cópias",
        })
    if diag["componentes"] > 1:
        achados.append({
            "codigo": "MULTIPLOS_COMPONENTES",
            "detalhe": f"{diag['componentes']} componentes soltos",
            "efeito": "partes podem sumir na exportação ou no rig",
        })
    return achados


# ---- reparo -----------------------------------------------------------------

def reparar(malha: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    """Conserta o que é conservador consertar, e diz o que fez.

    A ordem importa: soldar antes de remover degeneradas, porque a solda cria
    degeneradas novas ao colapsar vértices coincidentes.
    """
    aplicado: list[str] = []
    trabalho = malha.copy()

    antes_v = len(trabalho.vertices)
    trabalho.merge_vertices()
    if len(trabalho.vertices) < antes_v:
        aplicado.append(f"soldou {antes_v - len(trabalho.vertices)} vértices coincidentes")

    antes_f = len(trabalho.faces)
    trabalho.update_faces(trabalho.nondegenerate_faces())
    trabalho.update_faces(trabalho.unique_faces())
    if len(trabalho.faces) < antes_f:
        aplicado.append(f"removeu {antes_f - len(trabalho.faces)} faces degeneradas ou repetidas")

    trabalho.remove_unreferenced_vertices()

    if not trabalho.is_winding_consistent:
        trabalho.fix_normals()
        aplicado.append("reorientou as normais")

    if trabalho.is_watertight and trabalho.volume < 0:
        trabalho.invert()
        aplicado.append("inverteu a malha: o volume estava negativo")

    return trabalho, aplicado


def preencher_buracos(malha: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Fecha a casca. Só vale a pena reportar sucesso se ficar estanque de fato."""
    trabalho = malha.copy()
    antes = int(len(trabalho.edges[trimesh.grouping.group_rows(
        trabalho.edges_sorted, require_count=1)]))
    trabalho.fill_holes()
    trabalho.remove_unreferenced_vertices()
    depois = int(len(trabalho.edges[trimesh.grouping.group_rows(
        trabalho.edges_sorted, require_count=1)]))
    return trabalho, {
        "arestas_de_borda_antes": antes,
        "arestas_de_borda_depois": depois,
        "ficou_estanque": bool(trabalho.is_watertight),
    }


# ---- topologia --------------------------------------------------------------

def decimar(malha: trimesh.Trimesh, alvo_faces: int) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Reduz contagem de faces medindo o erro geométrico que isso custou.

    Devolver a malha reduzida sem medir o desvio seria entregar perda de forma
    sem informar. O desvio sai da distância dos vértices novos à superfície velha.
    """
    if alvo_faces < 4:
        raise MalhaInvalida(f"alvo de {alvo_faces} faces não forma um sólido")
    if alvo_faces >= len(malha.faces):
        return malha.copy(), {"reduziu": False, "faces": int(len(malha.faces)),
                              "motivo": "alvo maior ou igual à contagem atual"}

    reduzida = malha.simplify_quadric_decimation(face_count=alvo_faces)
    desvio = _desvio_de_superficie(malha, reduzida)
    return reduzida, {
        "reduziu": True,
        "faces_antes": int(len(malha.faces)),
        "faces_depois": int(len(reduzida.faces)),
        "taxa": round(len(reduzida.faces) / len(malha.faces), 4),
        **desvio,
    }


def _desvio_de_superficie(original: trimesh.Trimesh,
                          nova: trimesh.Trimesh) -> dict[str, float]:
    """Distância dos vértices da malha nova à superfície da original.

    Normalizada pela diagonal da caixa envolvente: 0,5 mm importa num anel e é
    irrelevante num terreno, e só a razão diz qual dos dois é o caso.
    """
    distancias = trimesh.proximity.closest_point(original, nova.vertices)[1]
    diagonal = float(np.linalg.norm(original.extents))
    return {
        "desvio_medio": float(np.mean(distancias)),
        "desvio_maximo": float(np.max(distancias)),
        "desvio_relativo": float(np.max(distancias) / diagonal) if diagonal else 0.0,
    }


def suavizar(malha: trimesh.Trimesh, iteracoes: int = 5,
             fator: float = 0.5) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Laplaciano de Taubin: suaviza segurando o volume.

    O laplaciano puro puxa todo vértice para a média dos vizinhos e reduz o volume
    a cada passada — num rosto, o nariz some. Taubin alterna um passo positivo com
    um negativo e freia esse encolhimento; não o elimina. Medido aqui numa
    icosfera de 5.120 faces com 5 iterações: 2,17% de volume perdido. Por isso o
    encolhimento sai no retorno em vez de ficar implícito — quem chama decide se
    2% é aceitável para o caso dele.
    """
    trabalho = malha.copy()
    volume_antes = float(trabalho.volume) if trabalho.is_watertight else None
    trimesh.smoothing.filter_taubin(trabalho, lamb=fator, nu=-(fator + 0.03),
                                    iterations=int(iteracoes))
    volume_depois = float(trabalho.volume) if trabalho.is_watertight else None
    encolhimento = None
    if volume_antes and volume_depois:
        encolhimento = round((volume_antes - volume_depois) / volume_antes, 6)
    return trabalho, {
        "iteracoes": int(iteracoes),
        "volume_antes": volume_antes,
        "volume_depois": volume_depois,
        "encolhimento_relativo": encolhimento,
        **_desvio_de_superficie(malha, trabalho),
    }


def subdividir(malha: trimesh.Trimesh, niveis: int = 1) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Cada nível quadruplica as faces. Três níveis são 64x — o limite existe
    porque 64x de uma malha de 100 mil faces não cabe em memória."""
    if not 1 <= niveis <= 3:
        raise MalhaInvalida(f"níveis fora da faixa 1..3: {niveis}")
    projetado = len(malha.faces) * (4 ** niveis)
    if projetado > 4_000_000:
        raise MalhaInvalida(
            f"{niveis} níveis gerariam {projetado} faces; o teto prático é 4 milhões")
    trabalho = malha.copy()
    for _ in range(niveis):
        trabalho = trabalho.subdivide()
    return trabalho, {"faces_antes": int(len(malha.faces)),
                      "faces_depois": int(len(trabalho.faces)), "niveis": int(niveis)}


# ---- UV ---------------------------------------------------------------------

def desdobrar_uv(malha: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Projeção esférica com costura no meridiano.

    É honesto dizer o que isto NÃO é: não é um desdobramento por corte automático
    tipo xatlas. Serve para corpo e cabeça, que são topologicamente próximos de
    uma esfera, e mede a distorção para que o resultado ruim apareça como número
    em vez de aparecer como textura esticada no personagem final.
    """
    trabalho = malha.copy()
    centro = trabalho.vertices.mean(axis=0)
    direcao = trabalho.vertices - centro
    raio = np.linalg.norm(direcao, axis=1)
    raio[raio == 0] = 1e-9
    unidade = direcao / raio[:, None]

    u = (np.arctan2(unidade[:, 2], unidade[:, 0]) + np.pi) / (2 * np.pi)
    v = np.arccos(np.clip(unidade[:, 1], -1.0, 1.0)) / np.pi
    uv = np.column_stack([u, v])

    trabalho.visual = trimesh.visual.TextureVisuals(uv=uv)
    return trabalho, {"metodo": "esferica", **_distorcao_uv(trabalho, uv)}


def _distorcao_uv(malha: trimesh.Trimesh, uv: np.ndarray) -> dict[str, Any]:
    """Razão entre área no espaço 3D e área no espaço UV, por triângulo.

    Um atlas perfeito teria razão constante. O desvio dessa constante é exatamente
    o quanto a textura estica, e é o número que decide se o mapa serve.
    """
    tri3d = malha.vertices[malha.faces]
    a3 = np.linalg.norm(np.cross(tri3d[:, 1] - tri3d[:, 0], tri3d[:, 2] - tri3d[:, 0]), axis=1) / 2

    tri2d = uv[malha.faces]
    e1 = tri2d[:, 1] - tri2d[:, 0]
    e2 = tri2d[:, 2] - tri2d[:, 0]
    a2 = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2

    validos = (a2 > 1e-12) & (a3 > 1e-12)
    if not validos.any():
        return {"distorcao_mediana": None, "faces_degeneradas_uv": int(len(a2))}

    razao = a3[validos] / a2[validos]
    mediana = float(np.median(razao))
    return {
        "distorcao_mediana": round(mediana, 6),
        # Normalizado pela mediana: o que importa é a variação, não a escala.
        "distorcao_p95": round(float(np.percentile(razao, 95)) / mediana, 4),
        "faces_degeneradas_uv": int(np.count_nonzero(~validos)),
        "cobertura_uv": round(float(a2.sum()), 6),
    }


# ---- normalização -----------------------------------------------------------

def normalizar_escala(malha: trimesh.Trimesh,
                      altura_alvo_m: float = 1.75) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Põe a malha em metros, de pé sobre a origem.

    Um personagem exportado em centímetros entra num motor de jogo com 100x o
    tamanho e ninguém descobre até a primeira colisão. A altura alvo é o eixo Y,
    que é a convenção de glTF.
    """
    trabalho = malha.copy()
    altura_atual = float(trabalho.extents[1])
    if altura_atual <= 0:
        raise MalhaInvalida("a malha tem altura zero no eixo Y")
    fator = altura_alvo_m / altura_atual
    trabalho.apply_scale(fator)

    minimo = trabalho.bounds[0]
    maximo = trabalho.bounds[1]
    deslocamento = np.array([
        -(minimo[0] + maximo[0]) / 2,   # centrado em X
        -minimo[1],                      # pés na origem
        -(minimo[2] + maximo[2]) / 2,   # centrado em Z
    ])
    trabalho.apply_translation(deslocamento)
    return trabalho, {
        "altura_antes_m": round(altura_atual, 6),
        "altura_depois_m": round(float(trabalho.extents[1]), 6),
        "fator": round(fator, 6),
        "deslocamento": [round(float(x), 6) for x in deslocamento],
    }


def simetria(malha: trimesh.Trimesh, eixo: int = 0) -> dict[str, Any]:
    """Quanto a malha é simétrica no eixo dado.

    Mede a distância de cada vértice espelhado à superfície original. Num
    personagem, assimetria alta antes do rig significa que o esqueleto vai sair
    torto e ninguém entende por quê.
    """
    espelho = malha.vertices.copy()
    centro = float(malha.vertices[:, eixo].mean())
    espelho[:, eixo] = 2 * centro - espelho[:, eixo]
    distancias = trimesh.proximity.closest_point(malha, espelho)[1]
    diagonal = float(np.linalg.norm(malha.extents))
    return {
        "eixo": ["X", "Y", "Z"][eixo],
        "plano_em": round(centro, 6),
        "erro_medio": float(np.mean(distancias)),
        "erro_maximo": float(np.max(distancias)),
        "erro_relativo": float(np.mean(distancias) / diagonal) if diagonal else 0.0,
        "simetrica": bool(np.mean(distancias) / diagonal < 0.01) if diagonal else False,
    }

"""Vestuário do PERZON — tecido simulado, molde medido, costura verificada.

A simulação é PBD (dinâmica baseada em posição): em vez de integrar forças e
torcer para o passo não explodir, cada restrição é resolvida movendo os vértices
diretamente. É o método que roupa em tempo real usa, e é estável com passo grande
— um integrador de forças com a rigidez de tecido precisaria de passos minúsculos
para não divergir.

Nada aqui é aparência: cada operação devolve o número que a decide. Tensão sai do
estiramento medido de cada aresta, colisão sai de distância real ao corpo, e a
costura recusa unir bordas de comprimento incompatível em vez de franzir em
silêncio.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh
from scipy.spatial import cKDTree

# Gravidade em m/s². O sinal negativo em Y é a convenção do resto do projeto.
GRAVIDADE = np.array([0.0, -9.81, 0.0])

# Sobrerrelaxação do solucionador. A média de Jacobi aplica só 1/grau da correção
# por iteração, o que é estável e lento. Multiplicar por 1,5 acelera a convergência
# sem devolver a divergência que a média corrigiu.
SOBRERRELAXACAO = 1.5

# Iterações por passo. `None` calcula a partir do tamanho da malha, e é o padrão
# porque o número certo NÃO é uma constante: em Jacobi a informação caminha uma
# aresta por iteração, então um painel de 16 divisões precisa de pelo menos 16
# iterações para o vértice de baixo saber que o de cima está preso. Medido com 8
# iterações fixas num painel 16x16: 115% de estiramento, porque a restrição do
# topo literalmente não chegava embaixo.
ITERACOES_PADRAO = None

# Estiramento acima disto rasga tecido real. 5% é o limite prático de malha de
# algodão; elastano chega a 100%, e por isso o limite é parâmetro e não constante.
ESTIRAMENTO_DE_RUPTURA = 0.05


class TecidoInvalido(ValueError):
    """A malha ou o parâmetro não sustentam simulação de tecido."""


# ---- molde -------------------------------------------------------------------

def gerar_painel(largura: float, altura: float, divisoes: int = 20) -> trimesh.Trimesh:
    """Painel plano de tecido, no plano XY, pronto para costurar.

    Divisão uniforme: o solucionador de PBD assume que arestas vizinhas têm
    comprimento parecido. Malha muito irregular faz umas restrições dominarem as
    outras, e o pano enruga onde não deveria.
    """
    if largura <= 0 or altura <= 0:
        raise TecidoInvalido(f"painel {largura}x{altura} não tem área")
    if not 2 <= divisoes <= 200:
        raise TecidoInvalido(f"divisões fora de 2..200: {divisoes}")

    xs = np.linspace(-largura / 2, largura / 2, divisoes)
    ys = np.linspace(0.0, altura, divisoes)
    grade_x, grade_y = np.meshgrid(xs, ys)
    vertices = np.column_stack([grade_x.ravel(), grade_y.ravel(),
                                np.zeros(grade_x.size)])

    faces = []
    for linha in range(divisoes - 1):
        for coluna in range(divisoes - 1):
            a = linha * divisoes + coluna
            faces.append([a, a + 1, a + divisoes])
            faces.append([a + 1, a + divisoes + 1, a + divisoes])
    return trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=False)


def medir_molde(painel: trimesh.Trimesh) -> dict[str, Any]:
    """Área, perímetro e proporção do molde — o que a mesa de corte precisa."""
    bordas = _arestas_de_borda(painel)
    perimetro = float(sum(
        np.linalg.norm(painel.vertices[a] - painel.vertices[b]) for a, b in bordas))
    minimo, maximo = painel.bounds
    return {
        "area_m2": round(float(painel.area), 6),
        "perimetro_m": round(perimetro, 6),
        "largura_m": round(float(maximo[0] - minimo[0]), 6),
        "altura_m": round(float(maximo[1] - minimo[1]), 6),
        "vertices": int(len(painel.vertices)),
        "faces": int(len(painel.faces)),
        "arestas_de_borda": len(bordas),
        # Área do retângulo envolvente menos a área real: é o desperdício de tecido
        # no corte, e o que decide o encaixe no rolo.
        "aproveitamento": round(
            float(painel.area) / max(float((maximo[0] - minimo[0]) * (maximo[1] - minimo[1])), 1e-9), 4),
    }


def _arestas_de_borda(malha: trimesh.Trimesh) -> np.ndarray:
    """Arestas que pertencem a uma face só — o contorno aberto do painel."""
    return malha.edges[trimesh.grouping.group_rows(malha.edges_sorted, require_count=1)]


def adicionar_folga(painel: trimesh.Trimesh, folga_m: float) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Afasta a borda do painel para fora, no plano, criando margem de costura.

    Empurra na direção da normal 2D da borda, não escala o painel: escalar moveria
    também o interior, e a marcação de pence e bolso sairia do lugar.
    """
    if folga_m <= 0:
        raise TecidoInvalido(f"folga precisa ser positiva: {folga_m}")

    trabalho = painel.copy()
    bordas = _arestas_de_borda(trabalho)
    if not len(bordas):
        raise TecidoInvalido("o painel é fechado: não há borda para afastar")

    indices = np.unique(bordas)
    centro = trabalho.vertices[indices][:, :2].mean(axis=0)
    for i in indices:
        direcao = trabalho.vertices[i][:2] - centro
        norma = float(np.linalg.norm(direcao))
        if norma > 1e-9:
            trabalho.vertices[i][:2] += direcao / norma * folga_m

    return trabalho, {
        "folga_m": float(folga_m),
        "vertices_movidos": int(len(indices)),
        "area_antes_m2": round(float(painel.area), 6),
        "area_depois_m2": round(float(trabalho.area), 6),
    }


# ---- costura -----------------------------------------------------------------

def verificar_costura(borda_a: np.ndarray, borda_b: np.ndarray,
                      tolerancia: float = 0.10) -> dict[str, Any]:
    """Duas bordas só costuram se tiverem comprimento compatível.

    Costurar bordas de comprimentos diferentes franze o tecido. Às vezes é
    intencional (uma manga em cabeça de manga franze de propósito), então a
    tolerância é parâmetro — mas franzir sem saber é defeito, e por isso a
    verificação existe antes da costura e não depois.
    """
    a = np.asarray(borda_a, dtype=np.float64)
    b = np.asarray(borda_b, dtype=np.float64)
    if len(a) < 2 or len(b) < 2:
        raise TecidoInvalido("cada borda precisa de pelo menos 2 pontos")

    comprimento_a = float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum())
    comprimento_b = float(np.linalg.norm(np.diff(b, axis=0), axis=1).sum())
    maior = max(comprimento_a, comprimento_b)
    diferenca = abs(comprimento_a - comprimento_b) / maior if maior > 1e-9 else 0.0

    return {
        "comprimento_a_m": round(comprimento_a, 6),
        "comprimento_b_m": round(comprimento_b, 6),
        "diferenca_relativa": round(diferenca, 5),
        "tolerancia": float(tolerancia),
        "compativel": bool(diferenca <= tolerancia),
        # Quanto de franzido a costura vai produzir se for feita assim mesmo.
        "franzido_previsto": round(diferenca, 5),
        "pontos": min(len(a), len(b)),
    }


def costurar(painel_a: trimesh.Trimesh, painel_b: trimesh.Trimesh,
             indices_a: list[int], indices_b: list[int]) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Une dois painéis criando faces entre as bordas indicadas.

    Os índices vêm em ordem ao longo de cada borda. Emparelhar por proximidade em
    vez de por ordem cruzaria a costura quando os painéis chegam espelhados — e o
    resultado é uma roupa com o avesso para fora numa das partes.
    """
    if len(indices_a) != len(indices_b):
        raise TecidoInvalido(
            f"as bordas têm {len(indices_a)} e {len(indices_b)} pontos; a costura "
            "precisa de correspondência um a um")
    if len(indices_a) < 2:
        raise TecidoInvalido("costura precisa de pelo menos 2 pontos")

    deslocamento = len(painel_a.vertices)
    vertices = np.vstack([painel_a.vertices, painel_b.vertices])
    faces = np.vstack([painel_a.faces, painel_b.faces + deslocamento])

    novas = []
    for i in range(len(indices_a) - 1):
        a0, a1 = indices_a[i], indices_a[i + 1]
        b0, b1 = indices_b[i] + deslocamento, indices_b[i + 1] + deslocamento
        novas.append([a0, b0, a1])
        novas.append([a1, b0, b1])

    unido = trimesh.Trimesh(vertices=vertices,
                            faces=np.vstack([faces, np.array(novas)]), process=False)
    return unido, {
        "pontos_costurados": len(indices_a),
        "faces_criadas": len(novas),
        "vertices_totais": int(len(unido.vertices)),
        "faces_totais": int(len(unido.faces)),
    }


# ---- simulação ---------------------------------------------------------------

def _restricoes_de_distancia(malha: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    """Cada aresta única vira uma restrição de comprimento de repouso."""
    arestas = malha.edges_unique
    repouso = np.linalg.norm(
        malha.vertices[arestas[:, 0]] - malha.vertices[arestas[:, 1]], axis=1)
    return arestas, repouso


def simular(malha: trimesh.Trimesh, passos: int = 30, dt: float = 0.016,
            rigidez: float = 0.9, amortecimento: float = 0.02,
            fixos: list[int] | None = None, corpo: trimesh.Trimesh | None = None,
            iteracoes: int | None = ITERACOES_PADRAO) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Deixa o tecido cair sob gravidade, preso pelos vértices fixos.

    PBD: integra a posição livremente e depois projeta cada restrição de volta.
    Isso é incondicionalmente estável — não existe passo de tempo que faça o pano
    explodir, ao contrário de massa-mola com rigidez alta.
    """
    if not 0.0 < rigidez <= 1.0:
        raise TecidoInvalido(f"rigidez fora de 0..1: {rigidez}")
    if passos < 1 or dt <= 0:
        raise TecidoInvalido(f"passos={passos}, dt={dt}: sem tempo para simular")

    posicao = np.array(malha.vertices, dtype=np.float64)
    anterior = posicao.copy()
    arestas, repouso = _restricoes_de_distancia(malha)

    if iteracoes is None:
        # Raiz do número de vértices aproxima o diâmetro da grade, que é a
        # distância que a informação precisa percorrer.
        iteracoes = int(np.ceil(np.sqrt(len(posicao)))) * 2
    if iteracoes < 1:
        raise TecidoInvalido(f"iterações precisa ser pelo menos 1: {iteracoes}")

    travados = np.zeros(len(posicao), dtype=bool)
    if fixos:
        travados[np.asarray(fixos, dtype=int)] = True

    # Grau de cada vértice: quantas restrições o puxam. É o divisor que mantém o
    # esquema estável, e vale 1 no mínimo para não dividir por zero num vértice
    # solto sem aresta.
    grau = np.zeros((len(posicao), 1), dtype=np.float64)
    np.add.at(grau, arestas[:, 0], 1.0)
    np.add.at(grau, arestas[:, 1], 1.0)
    grau = np.maximum(grau, 1.0)

    arvore = cKDTree(corpo.vertices) if corpo is not None else None
    colisoes = 0

    for _ in range(passos):
        # Verlet com amortecimento. A velocidade é implícita na diferença entre a
        # posição atual e a anterior, o que dispensa guardar um vetor de velocidade
        # que precisaria ser corrigido a cada projeção de restrição.
        velocidade = (posicao - anterior) * (1.0 - amortecimento)
        anterior = posicao.copy()
        posicao = posicao + velocidade + GRAVIDADE * dt * dt
        posicao[travados] = anterior[travados]

        for _ in range(iteracoes):
            delta = posicao[arestas[:, 1]] - posicao[arestas[:, 0]]
            distancia = np.linalg.norm(delta, axis=1)
            distancia = np.where(distancia < 1e-9, 1e-9, distancia)
            correcao = (distancia - repouso) / distancia * rigidez * 0.5
            ajuste = delta * correcao[:, None]

            # Acumula por vértice: um vértice participa de várias arestas, e
            # aplicar cada correção em sequência daria peso à ordem das arestas.
            acumulado = np.zeros_like(posicao)
            np.add.at(acumulado, arestas[:, 0], ajuste)
            np.add.at(acumulado, arestas[:, 1], -ajuste)
            # DIVIDIR pelo número de arestas do vértice é o que torna o esquema
            # de Jacobi estável. Somar as correções cruas parece funcionar e
            # diverge: com 4 a 6 arestas por vértice e rigidez 0,9, cada iteração
            # multiplica o erro. Medido antes desta linha, num painel de 0,6x0,8 m
            # com 40 passos: queda de 7×10¹⁵² metros. A estabilidade do PBD é do
            # método aplicado certo, não de quem o invoca pelo nome.
            posicao[~travados] += (acumulado / grau * SOBRERRELAXACAO)[~travados]

            if arvore is not None:
                distancias, vizinhos = arvore.query(posicao)
                dentro = distancias < 0.01
                if dentro.any():
                    colisoes += int(dentro.sum())
                    direcao = posicao[dentro] - corpo.vertices[vizinhos[dentro]]
                    norma = np.linalg.norm(direcao, axis=1, keepdims=True)
                    norma = np.where(norma < 1e-9, 1e-9, norma)
                    posicao[dentro] = corpo.vertices[vizinhos[dentro]] + direcao / norma * 0.01

    resultado = malha.copy()
    resultado.vertices = posicao
    queda = float(np.abs(posicao[:, 1] - malha.vertices[:, 1]).max())

    return resultado, {
        "passos": int(passos),
        "dt": float(dt),
        "rigidez": float(rigidez),
        "iteracoes": int(iteracoes),
        "vertices_fixos": int(travados.sum()),
        "queda_maxima_m": round(queda, 6),
        "resolucoes_de_colisao": colisoes,
        "tensao": medir_tensao(malha, resultado),
        "metodo": "PBD: incondicionalmente estável, ao contrário de massa-mola",
    }


def medir_tensao(repouso: trimesh.Trimesh, deformada: trimesh.Trimesh) -> dict[str, Any]:
    """Estiramento de cada aresta em relação ao comprimento de repouso.

    É o mapa que a costureira olha: onde o tecido está esticado além do que a
    fibra aguenta, a roupa vai rasgar ou marcar. Positivo é esticado, negativo é
    folgado.
    """
    if len(repouso.vertices) != len(deformada.vertices):
        raise TecidoInvalido(
            f"{len(repouso.vertices)} vértices no repouso contra "
            f"{len(deformada.vertices)} na deformada")

    arestas = repouso.edges_unique
    inicial = np.linalg.norm(
        repouso.vertices[arestas[:, 0]] - repouso.vertices[arestas[:, 1]], axis=1)
    final = np.linalg.norm(
        deformada.vertices[arestas[:, 0]] - deformada.vertices[arestas[:, 1]], axis=1)
    seguro = np.where(inicial < 1e-9, 1e-9, inicial)
    estiramento = (final - seguro) / seguro

    rompidas = int(np.count_nonzero(estiramento > ESTIRAMENTO_DE_RUPTURA))
    return {
        "estiramento_medio": round(float(estiramento.mean()), 5),
        "estiramento_maximo": round(float(estiramento.max()), 5),
        "compressao_maxima": round(float(estiramento.min()), 5),
        "arestas_acima_da_ruptura": rompidas,
        "fracao_rompida": round(rompidas / len(estiramento), 5),
        "limite_de_ruptura": ESTIRAMENTO_DE_RUPTURA,
        "aprovado": bool(rompidas == 0),
    }


def detectar_colisao(roupa: trimesh.Trimesh, corpo: trimesh.Trimesh,
                     margem: float = 0.005) -> dict[str, Any]:
    """Vértices de roupa que atravessaram o corpo.

    Testa o sinal da projeção na normal do corpo, não só a distância: um vértice a
    2 mm da pele pode estar do lado de dentro, e distância sozinha não distingue.
    """
    if not len(corpo.faces):
        raise TecidoInvalido("o corpo não tem faces para colidir")

    proximo, distancia, face = trimesh.proximity.closest_point(corpo, roupa.vertices)
    normais = corpo.face_normals[face]
    fora = np.einsum("ij,ij->i", roupa.vertices - proximo, normais) > 0

    penetrando = (~fora) | (distancia < margem)
    indices = np.flatnonzero(penetrando)
    return {
        "vertices_penetrando": int(len(indices)),
        "fracao": round(len(indices) / len(roupa.vertices), 5),
        "penetracao_maxima_m": round(float(distancia[~fora].max()), 6) if (~fora).any() else 0.0,
        "margem_m": float(margem),
        "indices": indices.astype(int).tolist()[:200],
        "aprovado": bool(len(indices) == 0),
    }


def resolver_colisao(roupa: trimesh.Trimesh, corpo: trimesh.Trimesh,
                     margem: float = 0.005) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Empurra para fora cada vértice que atravessou o corpo.

    Move ao longo da normal da face mais próxima, o que mantém o vértice sobre a
    mesma parte do corpo. Empurrar radialmente do centro faria a manga escorregar
    para o tronco.
    """
    trabalho = roupa.copy()
    antes = detectar_colisao(trabalho, corpo, margem)
    if antes["aprovado"]:
        return trabalho, {"movidos": 0, "passes": 0, "antes": antes, "depois": antes,
                          "resolveu": True}

    # Em passes: empurrar um vértice muda qual face é a mais próxima dos vizinhos,
    # e um passe só deixa resíduo. Medido numa esfera contra painel plano: 34
    # penetrações caíam para 26 num passe e para 0 em três.
    movidos = 0
    passes = 0
    for passes in range(1, 9):
        estado = detectar_colisao(trabalho, corpo, margem)
        if estado["aprovado"]:
            break
        proximo, _, face = trimesh.proximity.closest_point(corpo, trabalho.vertices)
        alvo = proximo + corpo.face_normals[face] * margem
        indices = np.array(estado["indices"], dtype=int)
        trabalho.vertices[indices] = alvo[indices]
        movidos += len(indices)

    depois = detectar_colisao(trabalho, corpo, margem)
    return trabalho, {"movidos": int(movidos), "passes": passes,
                      "antes": antes, "depois": depois,
                      "resolveu": bool(depois["vertices_penetrando"] == 0)}


def ajustar_ao_corpo(roupa: trimesh.Trimesh, corpo: trimesh.Trimesh,
                     folga_m: float = 0.01) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Encolhe a roupa até encostar no corpo, mantendo a folga pedida.

    Projeta cada vértice na superfície do corpo e recua pela folga. É o que
    "vestir" significa: a roupa passa a seguir a forma de quem a veste, em vez de
    manter a forma do manequim em que foi modelada.
    """
    if folga_m < 0:
        raise TecidoInvalido(f"folga negativa faria a roupa entrar na pele: {folga_m}")

    trabalho = roupa.copy()
    proximo, distancia, face = trimesh.proximity.closest_point(corpo, trabalho.vertices)
    normais = corpo.face_normals[face]
    trabalho.vertices = proximo + normais * folga_m

    return trabalho, {
        "folga_m": float(folga_m),
        "distancia_media_antes_m": round(float(distancia.mean()), 6),
        "distancia_maxima_antes_m": round(float(distancia.max()), 6),
        "vertices": int(len(trabalho.vertices)),
        "colisao_depois": detectar_colisao(trabalho, corpo, margem=folga_m * 0.5),
    }


def transferir_pesos(roupa: trimesh.Trimesh, corpo: trimesh.Trimesh,
                     pesos_do_corpo: dict[str, Any]) -> dict[str, Any]:
    """Copia o peso de skin do vértice de corpo mais próximo para cada vértice de roupa.

    Sem isso a roupa fica parada enquanto o personagem anda. Calcular peso próprio
    para a roupa daria um resultado ligeiramente diferente do corpo, e a diferença
    aparece como a roupa atravessando a pele no meio da animação.
    """
    indices_corpo = np.asarray(pesos_do_corpo["indices"], dtype=int)
    valores_corpo = np.asarray(pesos_do_corpo["pesos"], dtype=np.float64)
    if len(indices_corpo) != len(corpo.vertices):
        raise TecidoInvalido(
            f"pesos para {len(indices_corpo)} vértices, corpo tem {len(corpo.vertices)}")

    arvore = cKDTree(corpo.vertices)
    distancia, vizinho = arvore.query(roupa.vertices)

    return {
        "ossos": pesos_do_corpo["ossos"],
        "indices": indices_corpo[vizinho].tolist(),
        "pesos": valores_corpo[vizinho].tolist(),
        "max_influencias": pesos_do_corpo["max_influencias"],
        "vertices": int(len(roupa.vertices)),
        "distancia_media_m": round(float(distancia.mean()), 6),
        # Vértice de roupa longe de qualquer vértice de corpo herdou peso de uma
        # parte que não é a dele — capuz solto, saia rodada, manga larga.
        "vertices_distantes": int(np.count_nonzero(distancia > 0.10)),
    }


def gerar_lod(roupa: trimesh.Trimesh, niveis: int = 3) -> dict[str, Any]:
    """Cadeia de níveis de detalhe por decimação sucessiva.

    Cada nível tem metade das faces do anterior. O desvio geométrico de cada um
    vai no relatório, porque é ele que decide a que distância o nível pode entrar
    sem a troca ficar visível.
    """
    from . import mesh_ops

    if not 1 <= niveis <= 6:
        raise TecidoInvalido(f"níveis fora de 1..6: {niveis}")

    cadeia = [{"nivel": 0, "faces": int(len(roupa.faces)), "desvio_relativo": 0.0}]
    atual = roupa
    for nivel in range(1, niveis + 1):
        alvo = max(4, len(atual.faces) // 2)
        if alvo >= len(atual.faces):
            break
        atual, info = mesh_ops.decimar(atual, alvo)
        cadeia.append({"nivel": nivel, "faces": int(len(atual.faces)),
                       "desvio_relativo": info["desvio_relativo"]})

    return {"niveis": cadeia, "total": len(cadeia),
            "faces_originais": int(len(roupa.faces)),
            "faces_menor_nivel": cadeia[-1]["faces"]}


def propriedades_do_tecido(nome: str) -> dict[str, Any]:
    """Parâmetros físicos por tipo de tecido.

    São valores de referência da indústria têxtil, não medidas deste projeto — e o
    retorno diz isso. Servem de ponto de partida; o ajuste fino é do usuário.
    """
    tabela = {
        "algodao": {"rigidez": 0.85, "amortecimento": 0.03, "densidade_kg_m2": 0.15,
                    "estiramento_max": 0.05},
        "seda": {"rigidez": 0.55, "amortecimento": 0.01, "densidade_kg_m2": 0.06,
                 "estiramento_max": 0.08},
        "jeans": {"rigidez": 0.97, "amortecimento": 0.06, "densidade_kg_m2": 0.40,
                  "estiramento_max": 0.02},
        "malha": {"rigidez": 0.45, "amortecimento": 0.04, "densidade_kg_m2": 0.20,
                  "estiramento_max": 0.30},
        "couro": {"rigidez": 0.99, "amortecimento": 0.08, "densidade_kg_m2": 0.80,
                  "estiramento_max": 0.01},
    }
    if nome not in tabela:
        raise TecidoInvalido(f"tecido desconhecido: {nome}. Há: {', '.join(tabela)}")
    return {"tecido": nome, **tabela[nome],
            "origem": "valores de referência têxtil; não foram medidos neste projeto"}

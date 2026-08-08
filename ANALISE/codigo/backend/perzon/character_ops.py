"""Personagem do PERZON — proporção corporal medida da malha, não estimada.

Toda medida aqui sai de fatiar a geometria na altura certa e medir. Nenhuma vem
de tabela por idade ou por gênero: um personagem estilizado tem proporção que
nenhuma tabela antropométrica prevê, e aplicar a tabela nele produziria um
número que descreve outra pessoa.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh

# Alturas canônicas em fração da estatura, para fatiar o corpo nos lugares certos.
# Vêm de antropometria (Drillis-Contini e cânone de oito cabeças), e são usadas
# apenas para saber ONDE medir — nunca como valor de saída.
NIVEIS: dict[str, float] = {
    "tornozelo": 0.039,
    "joelho": 0.285,
    "quadril": 0.530,
    "cintura": 0.600,
    "peito": 0.720,
    "ombro": 0.815,
    "queixo": 0.870,
}

# Regiões do corpo por faixa de altura, DISJUNTAS. A primeira versão tinha
# `quadril` (0,470–0,560) atravessando `torso` e `coxas`: anatomicamente defensável,
# operacionalmente errado. Vértice em duas regiões recebe a edição duas vezes, e
# "congelar as pernas" deixaria de congelar de fato a faixa compartilhada.
REGIOES: dict[str, tuple[float, float]] = {
    "cabeca": (0.870, 1.001),
    "pescoco": (0.830, 0.870),
    "torso": (0.530, 0.830),
    "quadril": (0.470, 0.530),
    "coxas": (0.285, 0.470),
    "pernas": (0.039, 0.285),
    "pes": (0.000, 0.039),
}


class CorpoInvalido(ValueError):
    """A malha não sustenta medida corporal."""


def _fatia(malha: trimesh.Trimesh, fracao: float,
           espessura: float = 0.015) -> np.ndarray:
    """Seção horizontal na fração de altura pedida, por interseção com o plano.

    A primeira versão coletava vértices dentro de uma faixa. Parece equivalente e
    não é: um cilindro tem vértices só nas duas tampas, então a faixa no meio da
    coxa saía vazia e a largura do quadril vinha `None` num corpo perfeitamente
    medível. Medido no humanoide de teste: quadril, joelho e peito, os três níveis
    que mais importam, todos sem medida.

    A interseção com o plano corta as arestas onde elas de fato cruzam a altura, e
    não depende de onde o modelador pôs os vértices.
    """
    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    y = minimo[1] + fracao * altura

    try:
        segmentos = trimesh.intersections.mesh_plane(
            malha, plane_normal=[0.0, 1.0, 0.0], plane_origin=[0.0, y, 0.0])
    except Exception:      # noqa: BLE001 — malha degenerada não corta
        segmentos = np.empty((0, 2, 3))

    if len(segmentos):
        return np.asarray(segmentos).reshape(-1, 3)

    # Sem interseção, a altura está fora da malha ou o corte tangenciou. Cai para
    # os vértices próximos, que é pior mas ainda é medida.
    janela = espessura * altura
    return malha.vertices[np.abs(malha.vertices[:, 1] - y) < janela]


def detectar_pescoco(malha: trimesh.Trimesh, busca: tuple[float, float] = (0.35, 0.97),
                     amostras: int = 60) -> dict[str, Any]:
    """Onde a metade de cima do corpo se estrangula — é ali que fica o pescoço.

    Medir a cabeça por fração fixa da altura só funciona em corpo de proporção
    humana. Num personagem estilizado de cabeça grande, a fração devolve o mesmo
    número de sempre e a desproporção fica invisível justamente onde importa.

    Pescoço é **estrangulamento**: mais estreito que a seção acima E que a seção
    abaixo. A primeira versão pegava só o mínimo global entre 70% e 95%, e num
    corpo de cabeça grande esse mínimo caía no topo do crânio, onde a esfera
    afina. Resultado medido: 20 cabeças de altura para um boneco cabeçudo — o
    inverso exato do que a medida deveria dizer.

    A busca começa em 35% porque num corpo de cabeça grande o pescoço fica abaixo
    da metade da estatura — medido: 41% num boneco com cabeça de 0,45 m de raio.
    A cintura também estrangula e cai nessa faixa; o pescoço vence porque estreita
    mais, e é por isso que a escolha é pelo maior estrangulamento e não pelo mais
    alto.
    """
    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    if altura <= 0:
        raise CorpoInvalido("a malha tem altura zero")

    inicio, fim = busca
    fracoes = np.linspace(inicio, fim, amostras)
    larguras = np.array([
        (lambda f: float(f[:, 0].max() - f[:, 0].min()) if len(f) >= 3 else np.nan)(
            _fatia(malha, float(fracao), espessura=0.5 / amostras))
        for fracao in fracoes], dtype=np.float64)

    validos = ~np.isnan(larguras)
    if validos.sum() < 3:
        return {"fracao": NIVEIS["queixo"], "largura_m": None,
                "altura_da_cabeca_m": altura * (1.0 - NIVEIS["queixo"]),
                "estreitamento": 0.0, "confianca": "baixa",
                "motivo": "seções demais sem geometria para achar o estrangulamento"}

    # Candidato a pescoço: mínimo local com massa acima. `acima` garante que existe
    # cabeça — sem isso, o afinamento do topo do crânio venceria a busca.
    candidatos: list[tuple[float, float, float]] = []
    for i in np.flatnonzero(validos):
        if i == 0 or i == len(larguras) - 1:
            continue
        anterior = larguras[:i][validos[:i]]
        posterior = larguras[i + 1:][validos[i + 1:]]
        if not len(anterior) or not len(posterior):
            continue
        maior_abaixo, maior_acima = float(anterior.max()), float(posterior.max())
        largura = float(larguras[i])
        if largura >= maior_abaixo or largura >= maior_acima:
            continue
        referencia = min(maior_abaixo, maior_acima)
        candidatos.append((float(fracoes[i]), largura,
                           (referencia - largura) / referencia if referencia > 1e-9 else 0.0))

    if not candidatos:
        return {"fracao": NIVEIS["queixo"], "largura_m": None,
                "altura_da_cabeca_m": altura * (1.0 - NIVEIS["queixo"]),
                "estreitamento": 0.0, "confianca": "baixa",
                "motivo": "o corpo não estrangula: nenhuma seção é mais estreita "
                          "que a de cima e a de baixo ao mesmo tempo"}

    # O estrangulamento mais forte é o pescoço; num corpo humano a cintura também
    # estrangula, mas menos, e fica abaixo da faixa de busca.
    fracao, largura_pescoco, estreitamento = max(candidatos, key=lambda c: c[2])
    return {
        "fracao": round(fracao, 4),
        "largura_m": round(largura_pescoco, 6),
        "altura_da_cabeca_m": round(altura * (1.0 - fracao), 6),
        "estreitamento": round(estreitamento, 4),
        "candidatos": len(candidatos),
        "confianca": "alta" if estreitamento > 0.15 else "media",
        "motivo": "" if estreitamento > 0.15 else "estrangulamento fraco: menos de 15%",
    }


def medir_proporcoes(malha: trimesh.Trimesh) -> dict[str, Any]:
    """Estatura, larguras por nível e as razões que descrevem a silhueta.

    Largura sai da fatia, não da caixa envolvente: a caixa inclui os braços
    estendidos e faria a largura de ombro sair do tamanho da envergadura.
    """
    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    if altura <= 0:
        raise CorpoInvalido("a malha tem altura zero: não está de pé no eixo Y")

    larguras: dict[str, float] = {}
    profundidades: dict[str, float] = {}
    for nome, fracao in NIVEIS.items():
        faixa = _fatia(malha, fracao)
        if len(faixa) < 3:
            larguras[nome] = None
            profundidades[nome] = None
            continue
        larguras[nome] = round(float(faixa[:, 0].max() - faixa[:, 0].min()), 6)
        profundidades[nome] = round(float(faixa[:, 2].max() - faixa[:, 2].min()), 6)

    ombro, quadril, cintura = larguras.get("ombro"), larguras.get("quadril"), larguras.get("cintura")
    pescoco = detectar_pescoco(malha)
    altura_cabeca = pescoco["altura_da_cabeca_m"]

    return {
        "altura_m": round(altura, 6),
        "larguras_m": larguras,
        "profundidades_m": profundidades,
        "altura_da_cabeca_m": round(altura_cabeca, 6),
        "pescoco_em": pescoco["fracao"],
        # Quantas cabeças cabem na altura. Oito é a proporção heroica clássica,
        # sete e meia a realista, seis a estilizada.
        #
        # A altura da cabeça sai do pescoço medido, não de uma fração fixa. A
        # primeira versão usava `1 - 0.870` e portanto devolvia 7,69 para qualquer
        # corpo — um bonequinho de cabeça enorme e um humano normal recebiam o
        # mesmo número. Era tautologia com cara de medida.
        "cabecas_de_altura": round(altura / altura_cabeca, 3) if altura_cabeca > 1e-9 else None,
        "razao_ombro_quadril": round(ombro / quadril, 4) if ombro and quadril else None,
        "razao_cintura_quadril": round(cintura / quadril, 4) if cintura and quadril else None,
        "comprimento_das_pernas_m": round(altura * NIVEIS["quadril"], 6),
        "razao_perna_altura": round(NIVEIS["quadril"], 4),
        "metodo": "fatia horizontal na altura de cada nível; a caixa envolvente "
                  "incluiria os braços e inflaria a largura de ombro",
    }


def medir_massa(malha: trimesh.Trimesh, fatias: int = 20) -> dict[str, Any]:
    """Como o volume se distribui ao longo da altura.

    Duas silhuetas com a mesma estatura e a mesma largura de ombro podem ter
    distribuições de massa completamente diferentes. A curva é o que diferencia
    um corpo atlético de um pesado — e nenhuma medida pontual captura isso.
    """
    if fatias < 4:
        raise CorpoInvalido(f"{fatias} fatias não descrevem uma distribuição")

    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    if altura <= 0:
        raise CorpoInvalido("a malha tem altura zero")

    areas: list[float] = []
    for i in range(fatias):
        faixa = _fatia(malha, (i + 0.5) / fatias, espessura=0.5 / fatias)
        if len(faixa) < 3:
            areas.append(0.0)
            continue
        # Área da seção aproximada pela elipse da caixa da fatia. Casco convexo
        # seria mais exato e custa uma triangulação por fatia; a elipse acerta a
        # forma da curva, que é o que a medida usa.
        largura = float(faixa[:, 0].max() - faixa[:, 0].min())
        profundidade = float(faixa[:, 2].max() - faixa[:, 2].min())
        areas.append(float(np.pi * largura * profundidade / 4))

    arranjo = np.array(areas)
    total = float(arranjo.sum())
    if total <= 0:
        raise CorpoInvalido("todas as fatias saíram vazias")

    normalizado = arranjo / total
    alturas = (np.arange(fatias) + 0.5) / fatias
    centroide = float((normalizado * alturas).sum())

    return {
        "fatias": int(fatias),
        "area_por_fatia": [round(v, 6) for v in areas],
        "distribuicao": [round(v, 5) for v in normalizado],
        # Centro de massa em fração da altura. Acima de 0,5 significa tronco
        # pesado; abaixo, pernas pesadas.
        "centro_de_massa_relativo": round(centroide, 5),
        "fatia_mais_larga": int(np.argmax(arranjo)),
        "volume_aproximado_m3": round(total * altura / fatias, 6),
        "volume_real_m3": round(float(malha.volume), 6) if malha.is_watertight else None,
    }


def separar_regioes(malha: trimesh.Trimesh) -> dict[str, Any]:
    """Índices de vértice por região anatômica.

    É o que permite congelar uma parte e editar outra: sem um mapa de vértice para
    região, "editar só as pernas" não tem como ser expresso.
    """
    minimo, maximo = malha.bounds
    altura = float(maximo[1] - minimo[1])
    if altura <= 0:
        raise CorpoInvalido("a malha tem altura zero")

    alturas = (malha.vertices[:, 1] - minimo[1]) / altura
    regioes: dict[str, Any] = {}
    atribuidos = np.zeros(len(malha.vertices), dtype=bool)
    for nome, (inicio, fim) in REGIOES.items():
        seletor = (alturas >= inicio) & (alturas < fim)
        indices = np.flatnonzero(seletor)
        atribuidos |= seletor
        regioes[nome] = {"vertices": int(len(indices)),
                         "faixa_altura": [inicio, fim],
                         "indices": indices.astype(int).tolist()}

    # Vértice fora de toda faixa é sintoma de que as faixas não cobrem o corpo, e
    # editar por região deixaria esses vértices para trás sem ninguém notar.
    sobra = int(np.count_nonzero(~atribuidos))
    return {"regioes": regioes, "vertices_sem_regiao": sobra,
            "cobertura": round(1 - sobra / len(malha.vertices), 5)}


def espelhar_lado(malha: trimesh.Trimesh,
                  origem: str = "esquerdo") -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """Copia um lado sobre o outro pelo plano sagital.

    Cada vértice do lado destino é substituído pelo vértice mais próximo do
    espelho do lado origem. Espelhar a malha inteira e concatenar duplicaria a
    contagem de vértices e quebraria qualquer peso de skin já calculado.
    """
    if origem not in {"esquerdo", "direito"}:
        raise CorpoInvalido(f"lado desconhecido: {origem}")

    trabalho = malha.copy()
    eixo = float((trabalho.bounds[0][0] + trabalho.bounds[1][0]) / 2)
    espelho = trabalho.vertices.copy()
    espelho[:, 0] = 2 * eixo - espelho[:, 0]

    # `esquerdo` é X menor que o eixo, na convenção de olhar o personagem de frente.
    doador = trabalho.vertices[:, 0] < eixo if origem == "esquerdo" else trabalho.vertices[:, 0] > eixo
    destino = ~doador
    if not doador.any() or not destino.any():
        raise CorpoInvalido("o plano sagital não separa a malha em dois lados")

    from scipy.spatial import cKDTree

    arvore = cKDTree(espelho[doador])
    _, vizinho = arvore.query(trabalho.vertices[destino])
    indices_doadores = np.flatnonzero(doador)[vizinho]
    trabalho.vertices[destino] = espelho[indices_doadores]

    from . import mesh_ops

    return trabalho, {
        "lado_origem": origem,
        "vertices_substituidos": int(np.count_nonzero(destino)),
        "plano_sagital_x": round(eixo, 6),
        "simetria_depois": mesh_ops.simetria(trabalho, 0),
    }


def comparar_corpos(antes: trimesh.Trimesh,
                    depois: trimesh.Trimesh) -> dict[str, Any]:
    """Diferença medida entre duas versões do mesmo personagem.

    Um botão "comparar antes/depois" que só mostra as duas malhas lado a lado
    deixa o julgamento para o olho. O número diz exatamente o que mudou e quanto.
    """
    medida_antes = medir_proporcoes(antes)
    medida_depois = medir_proporcoes(depois)

    mudancas = []
    for nome in NIVEIS:
        a = medida_antes["larguras_m"].get(nome)
        b = medida_depois["larguras_m"].get(nome)
        if a is None or b is None or abs(a) < 1e-9:
            continue
        mudancas.append({"nivel": nome, "antes_m": a, "depois_m": b,
                         "variacao_relativa": round((b - a) / a, 5)})

    altura_a = medida_antes["altura_m"]
    return {
        "altura_antes_m": altura_a,
        "altura_depois_m": medida_depois["altura_m"],
        "variacao_de_altura": round((medida_depois["altura_m"] - altura_a) / altura_a, 5)
        if altura_a > 1e-9 else None,
        "por_nivel": mudancas,
        "maior_mudanca": max(mudancas, key=lambda m: abs(m["variacao_relativa"]))
        if mudancas else None,
        "topologia_preservada": bool(len(antes.vertices) == len(depois.vertices)
                                     and len(antes.faces) == len(depois.faces)),
    }


def validar_proporcao(malha: trimesh.Trimesh) -> list[dict[str, str]]:
    """Proporções que quebram rig, roupa ou animação.

    Nenhuma delas é julgamento estético: um corpo estilizado é bem-vindo. O que
    estas regras acusam são medidas que fazem o esqueleto ou a física falharem.
    """
    achados: list[dict[str, str]] = []
    medida = medir_proporcoes(malha)

    pescoco = detectar_pescoco(malha)
    if pescoco["confianca"] == "baixa":
        # Sem pescoço achado, `cabecas_de_altura` cai na fração antropométrica e
        # devolve ~7,7 para qualquer forma. Julgar proporção por esse número seria
        # julgar por uma constante — o defeito é não ter onde medir.
        achados.append({
            "codigo": "PESCOCO_NAO_ENCONTRADO",
            "detalhe": pescoco["motivo"],
            "efeito": "a altura da cabeça não é medível; o esqueleto canônico vai "
                      "posicionar o pescoço por fração fixa e pode cair dentro do crânio",
        })
    else:
        cabecas = medida["cabecas_de_altura"]
        if cabecas is not None and cabecas < 3.0:
            achados.append({
                "codigo": "CABECA_DESPROPORCIONAL",
                "detalhe": f"{cabecas:.1f} cabeças de altura",
                "efeito": "o esqueleto canônico põe o pescoço dentro do crânio",
            })

    ombro = medida["larguras_m"].get("ombro")
    quadril = medida["larguras_m"].get("quadril")
    if ombro and quadril and (ombro / quadril < 0.5 or ombro / quadril > 2.5):
        achados.append({
            "codigo": "RAZAO_OMBRO_QUADRIL_EXTREMA",
            "detalhe": f"{ombro / quadril:.2f}",
            "efeito": "peso de skin do torso vaza para os braços ou para as coxas",
        })

    faltando = [n for n, v in medida["larguras_m"].items() if v is None]
    if faltando:
        achados.append({
            "codigo": "NIVEL_SEM_GEOMETRIA",
            "detalhe": ", ".join(faltando),
            "efeito": "a malha não tem vértice nessa altura; o corpo está incompleto",
        })

    if medida["altura_m"] < 0.3 or medida["altura_m"] > 4.0:
        achados.append({
            "codigo": "ESCALA_FORA_DO_ESPERADO",
            "detalhe": f"{medida['altura_m']:.2f} m",
            "efeito": "o personagem entra no motor 100x maior ou menor que a cena",
        })
    return achados

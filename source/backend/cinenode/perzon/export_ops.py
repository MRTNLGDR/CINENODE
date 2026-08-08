"""Exportação do PERZON — glTF com esqueleto e pesos escritos à mão.

O `trimesh` exporta geometria em GLB, mas não escreve `skin`, `joints_0` nem
`weights_0`: o personagem sai como estátua. Um exportador de personagem que
perde o rig não exportou o personagem — exportou a casca.

Este módulo monta o glTF 2.0 diretamente, com o buffer binário, os acessores e a
hierarquia de nós. Cada campo é conferido contra a especificação, e o que a
especificação exige e não temos vira erro em vez de campo faltando.
"""
from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

# Tipos de componente do glTF 2.0, tabela 5.1.
FLOAT = 5126
UNSIGNED_INT = 5125
UNSIGNED_SHORT = 5123

# O glTF fixa em 4 as influências por vértice de um conjunto JOINTS_0/WEIGHTS_0.
# Mais que isso exige conjuntos adicionais, que quase nenhum motor lê.
INFLUENCIAS_POR_CONJUNTO = 4


class ExportacaoInvalida(ValueError):
    """Falta dado obrigatório para o formato pedido."""


def _alinhar(dados: bytearray, multiplo: int = 4) -> None:
    """glTF exige que cada bufferView comece em múltiplo de 4.

    Sem o preenchimento, o visualizador lê o acessor com deslocamento errado e o
    personagem aparece com os vértices embaralhados — sem nenhum erro no console.
    """
    while len(dados) % multiplo:
        dados.append(0)


def exportar_gltf(malha: trimesh.Trimesh, destino: Path,
                  esqueleto: dict[str, Any] | None = None,
                  pesos: dict[str, Any] | None = None) -> dict[str, Any]:
    """Grava GLB com geometria e, quando houver, esqueleto e pesos de skin."""
    destino = Path(destino)
    vertices = np.asarray(malha.vertices, dtype=np.float32)
    indices = np.asarray(malha.faces, dtype=np.uint32).reshape(-1)
    normais = np.asarray(malha.vertex_normals, dtype=np.float32)

    binario = bytearray()
    views: list[dict[str, Any]] = []
    acessores: list[dict[str, Any]] = []

    def anexar(arranjo: np.ndarray, tipo: str, componente: int,
               alvo: int | None = None) -> int:
        _alinhar(binario)
        inicio = len(binario)
        bruto = arranjo.tobytes()
        binario.extend(bruto)
        view = {"buffer": 0, "byteOffset": inicio, "byteLength": len(bruto)}
        if alvo is not None:
            view["target"] = alvo
        views.append(view)
        acessor: dict[str, Any] = {
            "bufferView": len(views) - 1, "componentType": componente,
            "count": int(arranjo.shape[0]), "type": tipo,
        }
        # POSITION exige min/max na especificação: é o que permite ao motor
        # calcular a caixa envolvente sem ler o buffer inteiro.
        if tipo == "VEC3" and componente == FLOAT:
            acessor["min"] = [float(x) for x in arranjo.min(axis=0)]
            acessor["max"] = [float(x) for x in arranjo.max(axis=0)]
        acessores.append(acessor)
        return len(acessores) - 1

    acessor_posicao = anexar(vertices, "VEC3", FLOAT, 34962)
    acessor_normal = anexar(normais, "VEC3", FLOAT, 34962)
    acessor_indice = anexar(indices, "SCALAR", UNSIGNED_INT, 34963)

    atributos = {"POSITION": acessor_posicao, "NORMAL": acessor_normal}
    if getattr(malha.visual, "uv", None) is not None:
        uv = np.asarray(malha.visual.uv, dtype=np.float32)
        if len(uv) == len(vertices):
            atributos["TEXCOORD_0"] = anexar(uv, "VEC2", FLOAT, 34962)

    gltf: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "cinenode.perzon"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "personagem"}],
        "meshes": [{"primitives": [{"attributes": atributos,
                                    "indices": acessor_indice, "mode": 4}]}],
    }

    relatorio: dict[str, Any] = {
        "vertices": int(len(vertices)), "faces": int(len(malha.faces)),
        "tem_uv": "TEXCOORD_0" in atributos, "tem_rig": False,
    }

    if esqueleto and pesos:
        _anexar_rig(gltf, esqueleto, pesos, atributos, anexar, len(vertices))
        relatorio["tem_rig"] = True
        relatorio["juntas"] = len(esqueleto["juntas"])

    _alinhar(binario)
    gltf["buffers"] = [{"byteLength": len(binario)}]
    gltf["bufferViews"] = views
    gltf["accessors"] = acessores

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(_montar_glb(gltf, bytes(binario)))
    relatorio["bytes"] = destino.stat().st_size
    relatorio["arquivo"] = str(destino)
    return relatorio


def _anexar_rig(gltf: dict[str, Any], esqueleto: dict[str, Any],
                pesos: dict[str, Any], atributos: dict[str, int],
                anexar, total_vertices: int) -> None:
    """Escreve skin, joints, weights e as matrizes inversas de bind.

    A matriz inversa de bind é o que leva o vértice do espaço do modelo para o
    espaço do osso. Sem ela o glTF carrega, e o personagem aparece dobrado sobre
    si mesmo assim que a primeira pose é aplicada — o erro clássico de exportador
    que grava o skin e esquece as matrizes.
    """
    ossos = pesos["ossos"]
    indices_peso = np.asarray(pesos["indices"], dtype=np.uint16)
    valores_peso = np.asarray(pesos["pesos"], dtype=np.float32)

    if indices_peso.shape[0] != total_vertices:
        raise ExportacaoInvalida(
            f"pesos para {indices_peso.shape[0]} vértices, malha tem {total_vertices}")
    if indices_peso.shape[1] != INFLUENCIAS_POR_CONJUNTO:
        raise ExportacaoInvalida(
            f"glTF aceita {INFLUENCIAS_POR_CONJUNTO} influências por conjunto, "
            f"vieram {indices_peso.shape[1]}")

    somas = valores_peso.sum(axis=1)
    if not np.allclose(somas, 1.0, atol=1e-4):
        raise ExportacaoInvalida(
            f"pesos não normalizados: soma entre {somas.min():.6f} e {somas.max():.6f}")

    atributos["JOINTS_0"] = anexar(indices_peso, "VEC4", UNSIGNED_SHORT, 34962)
    atributos["WEIGHTS_0"] = anexar(valores_peso, "VEC4", FLOAT, 34962)

    juntas = esqueleto["juntas"]
    pai_de = {osso["nome"]: osso["pai"] for osso in esqueleto["ossos"]}

    # Um nó por JUNTA, não por osso. A raiz não é osso de ninguém — ela não tem
    # pai — e criar nós só para os ossos a deixava de fora: os três ossos filhos
    # do quadril viravam raízes soltas e o esqueleto saía partido em três árvores
    # desconectadas. O glTF carrega assim mesmo, e o personagem se desmonta na
    # primeira pose.
    todas = list(juntas)
    base = len(gltf["nodes"])
    posicao_no = {nome: base + i for i, nome in enumerate(todas)}

    for nome in todas:
        # Translação relativa ao pai: glTF compõe a hierarquia, e gravar posição
        # absoluta em cada nó somaria a do pai duas vezes.
        pai = pai_de.get(nome)
        origem = juntas[pai] if pai and pai in juntas else [0.0, 0.0, 0.0]
        gltf["nodes"].append({
            "name": nome,
            "translation": [juntas[nome][i] - origem[i] for i in range(3)],
        })

    for nome in todas:
        pai = pai_de.get(nome)
        if pai in posicao_no:
            gltf["nodes"][posicao_no[pai]].setdefault("children", []).append(
                posicao_no[nome])

    raizes = [posicao_no[n] for n in todas if pai_de.get(n) not in posicao_no]
    gltf["scenes"][0]["nodes"] = [0] + raizes

    # Inversa de bind: translação negativa da posição absoluta, em coluna-maior,
    # que é a ordem que o glTF exige.
    matrizes = np.zeros((len(ossos), 16), dtype=np.float32)
    for i, nome in enumerate(ossos):
        m = np.eye(4, dtype=np.float32)
        m[:3, 3] = -np.array(juntas[nome], dtype=np.float32)
        matrizes[i] = m.T.reshape(-1)

    # `joints` fica na ordem de `pesos["ossos"]`, porque JOINTS_0 indexa esta
    # lista — não a lista de nós. Nem toda junta precisa estar no skin; a raiz
    # existe na hierarquia sem receber peso, e isso é válido.
    gltf["skins"] = [{
        "joints": [posicao_no[n] for n in ossos],
        "inverseBindMatrices": anexar(matrizes, "MAT4", FLOAT),
        "skeleton": raizes[0] if raizes else posicao_no[ossos[0]],
    }]
    gltf["nodes"][0]["skin"] = 0


def _montar_glb(gltf: dict[str, Any], binario: bytes) -> bytes:
    """Container GLB: cabeçalho de 12 bytes, pedaço JSON, pedaço BIN.

    Cada pedaço precisa terminar em múltiplo de 4 — o JSON completa com espaço e
    o binário com zero. É o que a especificação manda, e visualizador que não
    tolera desalinhamento simplesmente recusa o arquivo.
    """
    texto = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    texto += b" " * ((4 - len(texto) % 4) % 4)
    corpo = binario + b"\x00" * ((4 - len(binario) % 4) % 4)

    total = 12 + 8 + len(texto) + 8 + len(corpo)
    saida = bytearray()
    saida += struct.pack("<III", 0x46546C67, 2, total)      # "glTF", versão 2
    saida += struct.pack("<II", len(texto), 0x4E4F534A)     # "JSON"
    saida += texto
    saida += struct.pack("<II", len(corpo), 0x004E4942)     # "BIN"
    saida += corpo
    return bytes(saida)


def exportar_obj(malha: trimesh.Trimesh, destino: Path) -> dict[str, Any]:
    """OBJ é texto e não carrega rig. Exportar personagem aqui perde o esqueleto,
    e isso é dito no relatório em vez de descoberto no motor de jogo."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(trimesh.exchange.obj.export_obj(malha), encoding="utf-8")
    return {
        "arquivo": str(destino), "bytes": destino.stat().st_size,
        "vertices": int(len(malha.vertices)), "faces": int(len(malha.faces)),
        "tem_rig": False,
        "aviso": "OBJ não carrega esqueleto nem pesos de skin; use glTF para personagem",
    }


def exportar_bvh(esqueleto: dict[str, Any], quadros: np.ndarray, fps: float,
                 destino: Path) -> dict[str, Any]:
    """BVH: hierarquia em texto e uma linha de canais por quadro.

    Grava só translação da raiz e translação por junta. Rotação exigiria resolver
    a orientação de cada osso a partir das posições, o que é ambíguo sem um eixo
    de referência — e inventar essa orientação produziria torção visível no
    cotovelo e no joelho. O relatório diz o que ficou de fora.
    """
    destino = Path(destino)
    nomes = list(esqueleto["juntas"])
    if quadros.shape[1] != len(nomes):
        raise ExportacaoInvalida(
            f"{quadros.shape[1]} juntas na animação contra {len(nomes)} no esqueleto")

    pai_de = {osso["nome"]: osso["pai"] for osso in esqueleto["ossos"]}
    filhos: dict[str, list[str]] = {}
    for nome, pai in pai_de.items():
        filhos.setdefault(pai, []).append(nome)
    raiz = next(n for n in nomes if n not in pai_de)

    linhas = ["HIERARCHY"]

    def escrever(nome: str, nivel: int, e_raiz: bool = False) -> None:
        tab = "  " * nivel
        linhas.append(f"{tab}{'ROOT' if e_raiz else 'JOINT'} {nome}")
        linhas.append(f"{tab}{{")
        pai = pai_de.get(nome)
        origem = esqueleto["juntas"][pai] if pai else [0.0, 0.0, 0.0]
        local = [esqueleto["juntas"][nome][i] - origem[i] for i in range(3)]
        linhas.append(f"{tab}  OFFSET {local[0]:.6f} {local[1]:.6f} {local[2]:.6f}")
        canais = "6 Xposition Yposition Zposition Zrotation Xrotation Yrotation" \
            if e_raiz else "3 Xposition Yposition Zposition"
        linhas.append(f"{tab}  CHANNELS {canais}")
        for filho in filhos.get(nome, []):
            escrever(filho, nivel + 1)
        if not filhos.get(nome):
            linhas.append(f"{tab}  End Site")
            linhas.append(f"{tab}  {{")
            linhas.append(f"{tab}    OFFSET 0.000000 0.000000 0.000000")
            linhas.append(f"{tab}  }}")
        linhas.append(f"{tab}}}")

    escrever(raiz, 0, e_raiz=True)
    linhas.append("MOTION")
    linhas.append(f"Frames: {quadros.shape[0]}")
    linhas.append(f"Frame Time: {1.0 / fps:.8f}")

    ordem = [nomes.index(raiz)] + [nomes.index(n) for n in nomes if n != raiz]
    for quadro in quadros:
        valores: list[str] = []
        for posicao, indice in enumerate(ordem):
            x, y, z = quadro[indice]
            valores.extend([f"{x:.6f}", f"{y:.6f}", f"{z:.6f}"])
            if posicao == 0:
                valores.extend(["0.000000", "0.000000", "0.000000"])
        linhas.append(" ".join(valores))

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return {
        "arquivo": str(destino), "bytes": destino.stat().st_size,
        "quadros": int(quadros.shape[0]), "juntas": len(nomes), "fps": float(fps),
        "limitacao": "só translação; rotação por junta é ambígua sem eixo de "
                     "referência e inventá-la torceria cotovelo e joelho",
    }


def validar_gltf(caminho: Path) -> dict[str, Any]:
    """Confere o GLB gravado contra o que a especificação exige.

    Reler o arquivo e conferir é o que separa "gravou" de "gravou certo". Um GLB
    com comprimento declarado errado abre em algumas ferramentas e falha noutras,
    e o defeito só aparece no computador de outra pessoa.
    """
    caminho = Path(caminho)
    dados = caminho.read_bytes()
    problemas: list[dict[str, str]] = []

    if len(dados) < 20:
        return {"valido": False, "problemas": [
            {"codigo": "ARQUIVO_CURTO", "detalhe": f"{len(dados)} bytes"}]}

    magico, versao, comprimento = struct.unpack_from("<III", dados, 0)
    if magico != 0x46546C67:
        problemas.append({"codigo": "MAGICO_INVALIDO", "detalhe": hex(magico)})
    if versao != 2:
        problemas.append({"codigo": "VERSAO_INESPERADA", "detalhe": str(versao)})
    if comprimento != len(dados):
        problemas.append({"codigo": "COMPRIMENTO_DIVERGENTE",
                          "detalhe": f"cabeçalho diz {comprimento}, arquivo tem {len(dados)}"})

    tamanho_json, tipo_json = struct.unpack_from("<II", dados, 12)
    if tipo_json != 0x4E4F534A:
        problemas.append({"codigo": "PEDACO_JSON_AUSENTE", "detalhe": hex(tipo_json)})
        return {"valido": False, "problemas": problemas}

    documento = json.loads(dados[20:20 + tamanho_json].decode("utf-8"))
    for campo in ("asset", "scenes", "nodes"):
        if campo not in documento:
            problemas.append({"codigo": "CAMPO_OBRIGATORIO_AUSENTE", "detalhe": campo})

    for i, acessor in enumerate(documento.get("accessors", [])):
        if acessor.get("type") == "VEC3" and acessor.get("componentType") == FLOAT:
            if "min" not in acessor or "max" not in acessor:
                problemas.append({
                    "codigo": "ACESSOR_SEM_LIMITES",
                    "detalhe": f"acessor {i}: POSITION exige min e max"})

    for i, view in enumerate(documento.get("bufferViews", [])):
        if view.get("byteOffset", 0) % 4:
            problemas.append({"codigo": "BUFFERVIEW_DESALINHADO",
                              "detalhe": f"view {i} em {view['byteOffset']}"})

    return {
        "valido": not problemas,
        "problemas": problemas,
        "versao": versao,
        "bytes": len(dados),
        "malhas": len(documento.get("meshes", [])),
        "nos": len(documento.get("nodes", [])),
        "tem_skin": bool(documento.get("skins")),
        "juntas": len(documento["skins"][0]["joints"]) if documento.get("skins") else 0,
    }

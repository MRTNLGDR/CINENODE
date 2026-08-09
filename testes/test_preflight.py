"""UX-001: recusar antes de gastar GPU o que só falharia depois de esperar na fila.

Cada teste aqui reproduz uma falha real medida neste projeto. Os códigos de erro
históricos e sua contagem: `PROMPT_INPUT_MISSING` 3x, `COMFYUI_WORKFLOW_MISSING` 3x,
`ASSET_ID_MISSING` 2x, `COMFYUI_UNAVAILABLE` 2x — 10 de 23 falhas, todas detectáveis
um segundo antes de a fila começar.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.schemas import WorkflowGraph
from cinenode.workflow import preflight_workflow


def grafo(nodes, edges=()) -> WorkflowGraph:
    return WorkflowGraph.model_validate({
        "version": 1, "nodes": nodes, "edges": list(edges), "metadata": {},
    })


def no(id_, tipo, **cfg):
    return {"id": id_, "type": tipo, "position": {"x": 0, "y": 0}, "config": cfg}


def codigos(resultado) -> set[str]:
    return {p["codigo"] for p in resultado["problemas"]}


# ---- o que precisa ser recusado ---------------------------------------------

def test_gerador_sem_prompt_conectado_e_recusado(config):
    """PROMPT_INPUT_MISSING: 3 ocorrências reais."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([no("img", "image.generate")])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert r["pronto"] is False
        assert "ENTRADA_NAO_CONECTADA" in codigos(r)
        assert r["problemas"][0]["node_id"] == "img"
        assert r["problemas"][0]["como_corrigir"], "recusa sem instrução não ensina"


def test_asset_inexistente_e_recusado(config):
    """ASSET_ID_MISSING: 2 ocorrências reais."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([no("a", "input.asset", asset_id="ast_que_nao_existe")])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert "ASSET_INEXISTENTE" in codigos(r)


def test_asset_com_arquivo_apagado_e_recusado(config, tmp_path):
    """O asset existe no banco e o arquivo sumiu do disco."""
    app = create_app(config)
    with TestClient(app):
        arquivo = tmp_path / "some.png"
        arquivo.write_bytes(b"x")
        asset = app.state.store.add_asset(arquivo, "image")
        arquivo.unlink()
        g = grafo([no("a", "input.asset", asset_id=asset["id"])])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert "ASSET_SEM_ARQUIVO" in codigos(r)


def test_workflow_comfy_inexistente_e_recusado(config):
    """COMFYUI_WORKFLOW_MISSING: 3 ocorrências reais."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([
            no("p", "input.text", text="x"),
            no("m", "model3d.generate", workflow_path="D:/caminho/que/nao/existe.json"),
        ], [{"id": "e", "source": "p", "target": "m"}])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert "WORKFLOW_INEXISTENTE" in codigos(r)


def test_sidecar_fora_do_ar_e_recusado(config):
    """COMFYUI_UNAVAILABLE: 2 ocorrências reais."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([
            no("p", "input.text", text="x"),
            no("m", "model3d.generate"),
        ], [{"id": "e", "source": "p", "target": "m"}])
        r = preflight_workflow(g, store=app.state.store, config=config,
                               sidecar_health={"comfyui": False})
        assert "SIDECAR_FORA" in codigos(r)
        assert "run-comfy" in r["problemas"][0]["como_corrigir"]


def test_tipo_desconhecido_e_recusado(config):
    app = create_app(config)
    with TestClient(app):
        g = grafo([no("x", "nao.existe")])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert "TIPO_DESCONHECIDO" in codigos(r)


def test_campo_obrigatorio_vazio_e_recusado(config):
    """`input.text` declara `text` como obrigatório."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([no("p", "input.text", text="")])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert "CAMPO_OBRIGATORIO_VAZIO" in codigos(r)


# ---- o que precisa continuar passando ---------------------------------------

def test_grafo_valido_passa_no_prevoo(config):
    """Pré-voo que recusa grafo bom é pior que pré-voo nenhum: o usuário o ignora."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([
            no("p", "input.text", text="cidade neon"),
            no("s", "output.preview"),
        ], [{"id": "e", "source": "p", "target": "s"}])
        r = preflight_workflow(g, store=app.state.store, config=config)
        assert r["pronto"] is True, r["problemas"]
        assert r["problemas"] == []


def test_sidecar_no_ar_nao_gera_problema(config):
    app = create_app(config)
    with TestClient(app):
        g = grafo([
            no("p", "input.text", text="x"),
            no("m", "model3d.generate"),
        ], [{"id": "e", "source": "p", "target": "m"}])
        r = preflight_workflow(g, store=app.state.store, config=config,
                               sidecar_health={"comfyui": True})
        assert "SIDECAR_FORA" not in codigos(r)


def test_no_sem_entrada_declarada_nao_exige_conexao(config):
    """`input.text` não tem entrada: exigir conexão nele seria falso positivo."""
    app = create_app(config)
    with TestClient(app):
        r = preflight_workflow(grafo([no("p", "input.text", text="x")]),
                               store=app.state.store, config=config)
        assert "ENTRADA_NAO_CONECTADA" not in codigos(r)


# ---- contrato da rota -------------------------------------------------------

def test_rota_de_prevoo_responde_com_a_mesma_forma(config):
    app = create_app(config)
    with TestClient(app) as client:
        corpo = grafo([no("img", "image.generate")]).model_dump(mode="json")
        resposta = client.post("/api/workflows/preflight", json=corpo)
        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["pronto"] is False
        assert dados["com_problema"] == 1
        assert dados["total_nos"] == 1


def test_prevoo_conta_nos_com_problema_sem_duplicar(config):
    """Um nó com dois problemas conta como um nó, não dois."""
    app = create_app(config)
    with TestClient(app):
        g = grafo([no("m", "model3d.generate", workflow_path="/nao/existe.json")])
        r = preflight_workflow(g, store=app.state.store, config=config,
                               sidecar_health={"comfyui": False})
        assert len(r["problemas"]) >= 2
        assert r["com_problema"] == 1

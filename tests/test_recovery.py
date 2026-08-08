from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.schemas import WorkflowGraph


def text_graph() -> WorkflowGraph:
    return WorkflowGraph.model_validate({
        "version": 1,
        "nodes": [
            {"id": "prompt", "type": "input.text", "position": {"x": 0, "y": 0}, "config": {"text": "retomar"}},
            {"id": "preview", "type": "output.preview", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [{"id": "e", "source": "prompt", "target": "preview"}],
        "metadata": {},
    })


def test_restart_marca_interrupted_e_retoma_a_fila(config):
    """Job morto por reinício vira INTERRUPTED, não FAILED.

    A distinção é o que permite retomar: FAILED é "o trabalho estava errado",
    INTERRUPTED é "o trabalho foi cortado". Medido neste projeto: 9 de 23 falhas
    eram do segundo tipo, marcadas como o primeiro, e por isso perdidas.
    """
    first_app = create_app(config)
    with TestClient(first_app):
        interrupted = first_app.state.store.create_job(None, text_graph())
        first_app.state.store.update_job(interrupted["id"], status="RUNNING",
                                         started_at="2026-08-06T00:00:00Z")
        queued = first_app.state.store.create_job(None, text_graph())

    second_app = create_app(config)
    with TestClient(second_app) as client:
        recovered = client.get(f"/api/jobs/{interrupted['id']}").json()
        assert recovered["status"] == "INTERRUPTED"
        assert recovered["error_code"] == "PROCESS_INTERRUPTED"
        assert "retomado" in recovered["error_message"].lower()

        deadline = time.monotonic() + 5
        resumed = None
        while time.monotonic() < deadline:
            resumed = client.get(f"/api/jobs/{queued['id']}").json()
            if resumed["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.05)
        assert resumed is not None
        assert resumed["status"] == "SUCCEEDED", resumed
        assert resumed["result"]["terminal_results"][0]["text"] == "retomar"


def test_job_interrompido_aparece_na_lista_de_retomaveis(config):
    app = create_app(config)
    with TestClient(app):
        job = app.state.store.create_job(None, text_graph())
        app.state.store.update_job(job["id"], status="RUNNING")

    app2 = create_app(config)
    with TestClient(app2):
        retomaveis = app2.state.store.list_resumable_jobs()
        assert [j["id"] for j in retomaveis] == [job["id"]]


def test_retomar_recoloca_na_fila_e_executa(config):
    app = create_app(config)
    with TestClient(app):
        job = app.state.store.create_job(None, text_graph())
        app.state.store.update_job(job["id"], status="RUNNING")

    app2 = create_app(config)
    with TestClient(app2) as client:
        resposta = client.post(f"/api/jobs/{job['id']}/resume")
        assert resposta.status_code == 200, resposta.text

        deadline = time.monotonic() + 5
        estado = None
        while time.monotonic() < deadline:
            estado = client.get(f"/api/jobs/{job['id']}").json()
            if estado["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.05)
        assert estado["status"] == "SUCCEEDED", estado


def test_retomar_job_que_nao_foi_interrompido_e_recusado(config):
    """Retomar um job que terminou bem criaria trabalho duplicado em silêncio."""
    app = create_app(config)
    with TestClient(app) as client:
        job = app.state.store.create_job(None, text_graph())
        app.state.store.update_job(job["id"], status="SUCCEEDED")
        resposta = client.post(f"/api/jobs/{job['id']}/resume")
        assert resposta.status_code == 409
        corpo = resposta.json()
        assert "JOB_NAO_RETOMAVEL" in str(corpo)


def test_cache_de_no_guarda_e_devolve_pelo_hash(config):
    """Mudar a configuração de um nó invalida o cache dele, e só dele."""
    app = create_app(config)
    with TestClient(app):
        store = app.state.store
        job = store.create_job(None, text_graph())
        store.save_node_result(job["id"], "prompt", "hash-a", {"kind": "text", "text": "a"})

        assert store.get_node_result(job["id"], "prompt", "hash-a")["text"] == "a"
        # Hash diferente é entrada diferente: não pode reaproveitar.
        assert store.get_node_result(job["id"], "prompt", "hash-b") is None
        # Nó diferente com o mesmo hash também não.
        assert store.get_node_result(job["id"], "preview", "hash-a") is None


def test_limpar_cache_de_no_remove_tudo_do_job(config):
    app = create_app(config)
    with TestClient(app):
        store = app.state.store
        job = store.create_job(None, text_graph())
        store.save_node_result(job["id"], "prompt", "h", {"kind": "text", "text": "x"})
        store.save_node_result(job["id"], "preview", "h", {"kind": "text", "text": "y"})
        assert store.clear_node_results(job["id"]) == 2
        assert store.get_node_result(job["id"], "prompt", "h") is None


def test_rota_literal_nao_e_engolida_pela_parametrizada(config):
    """`/api/jobs/resumable` precisa vir antes de `/api/jobs/{job_id}`.

    O FastAPI casa na ordem de registro: registrada depois, a rota literal seria
    tratada como um job de id "resumable" e devolveria 404.
    """
    app = create_app(config)
    with TestClient(app) as client:
        resposta = client.get("/api/jobs/resumable")
        assert resposta.status_code == 200, resposta.text
        assert "itens" in resposta.json()

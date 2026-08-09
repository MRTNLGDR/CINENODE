"""Integridade referencial e biometria.

Nota de método: a auditoria concluiu que `foreign_keys` estava desligado porque leu
`PRAGMA foreign_keys` de uma conexão aberta pelo próprio auditor — o padrão do SQLite
é OFF por conexão, e a do app liga explicitamente. Medir a própria conexão em vez da
do sistema é um erro fácil de cometer e caro de acreditar. Estes testes medem a do app.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.schemas import WorkflowGraph


def grafo() -> WorkflowGraph:
    return WorkflowGraph.model_validate({
        "version": 1,
        "nodes": [{"id": "p", "type": "input.text", "position": {"x": 0, "y": 0},
                   "config": {"text": "x"}}],
        "edges": [], "metadata": {},
    })


# ---- integridade referencial ------------------------------------------------

def test_conexao_do_app_tem_foreign_keys_ligado(config):
    app = create_app(config)
    with TestClient(app):
        with app.state.db.connection() as conexao:
            assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_base_nao_tem_violacao_de_chave_estrangeira(config):
    app = create_app(config)
    with TestClient(app):
        with app.state.db.connection() as conexao:
            assert list(conexao.execute("PRAGMA foreign_key_check")) == []


def test_job_com_projeto_inexistente_e_recusado(config):
    """FK decorativa deixaria um job órfão apontando para nada."""
    app = create_app(config)
    with TestClient(app):
        with pytest.raises(sqlite3.IntegrityError):
            app.state.db.execute(
                "INSERT INTO jobs(id,project_id,graph_json,status,progress,created_at) "
                "VALUES('job_orfao','prj_que_nao_existe','{}','QUEUED',0,'2026-01-01T00:00:00Z')"
            )


def test_apagar_projeto_nao_deixa_snapshot_orfao(config):
    """`project_snapshots` declara ON DELETE CASCADE — o teste prova que ela age."""
    app = create_app(config)
    with TestClient(app):
        store = app.state.store
        projeto = store.create_project(type("P", (), {
            "name": "temporário", "description": "", "graph": grafo()})())
        store.create_snapshot(projeto["id"], label="antes")
        assert store.count_snapshots(projeto["id"]) == 1

        store.delete_project(projeto["id"])
        sobrou = app.state.db.query(
            "SELECT id FROM project_snapshots WHERE project_id = ?", (projeto["id"],))
        assert sobrou == [], "snapshot ficou órfão após apagar o projeto"


def test_wal_esta_ligado(config):
    """WAL é o que permite leitura durante escrita; sem ele a UI trava na geração."""
    app = create_app(config)
    with TestClient(app):
        with app.state.db.connection() as conexao:
            assert conexao.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


# ---- PRIV-001: biometria --------------------------------------------------

def test_ficha_de_dna_e_classificada_como_biometrica(config, tmp_path):
    """478 pontos faciais são dado biométrico. Sem classificação, nenhuma política
    de retenção ou exclusão consegue tratá-lo diferente de um PNG qualquer."""
    from cinenode.engines.humandna import HumanDnaEngine

    app = create_app(config)
    with TestClient(app):
        motor = HumanDnaEngine(config.home)
        from tests.test_humandna import _leitura  # reusa a leitura sintética

        ficha = motor.consolidar([_leitura("a")])
        assert ficha["classificacao"] == "biometrico"
        assert ficha["procedencia"]["local"] is True


def test_apagar_asset_de_dna_apaga_a_medida(config, tmp_path):
    """Apagar o asset e deixar a medida no disco é retenção de biometria sem base."""
    app = create_app(config)
    with TestClient(app):
        arquivo = config.outputs_dir / "dna.json"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text('{"versao": 1, "classificacao": "biometrico"}', encoding="utf-8")
        asset = app.state.store.add_asset(
            arquivo, "data", metadata={"operation": "human.dna", "classificacao": "biometrico"})

        # Exclusão é em duas etapas por desenho: marcar e depois purgar. Nenhuma
        # remoção definitiva acontece num clique só, e isso é correto.
        app.state.store.soft_delete_asset(asset["id"])
        assert arquivo.exists(), "marcar como excluído não pode apagar o arquivo ainda"

        app.state.store.purge_asset(asset["id"])
        assert not arquivo.exists(), "a medida biométrica ficou no disco após o purge"


def test_purgar_sem_marcar_e_recusado(config):
    """Sem as duas etapas, um clique errado apaga biometria sem volta."""
    import pytest as _pytest
    from fastapi import HTTPException

    app = create_app(config)
    with TestClient(app):
        arquivo = config.outputs_dir / "dna2.json"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text("{}", encoding="utf-8")
        asset = app.state.store.add_asset(arquivo, "data")
        with _pytest.raises(HTTPException) as exc:
            app.state.store.purge_asset(asset["id"])
        assert exc.value.status_code == 409

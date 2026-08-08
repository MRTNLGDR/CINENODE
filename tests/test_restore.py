"""RESTORE-001: um backup só é válido depois de restaurado em ambiente limpo.

A Bible §18 e §21 dizem isso, e até esta implementação nada testava. `backup.py`
tinha teste de criação — criar um ZIP prova que o ZIP existe, não que ele volta.
"""
from __future__ import annotations

import zipfile

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.backup import create_backup, restore_backup
from cinenode.database import Database
from cinenode.schemas import WorkflowGraph


def _config_limpo(home):
    """Ambiente limpo de verdade: outro diretório, outro banco, nada compartilhado.

    Constrói o AppConfig do mesmo jeito que o conftest, com Path em todo campo:
    `dataclasses.replace` preservava campos que o construtor normaliza.
    """
    from pathlib import Path

    from cinenode.config import AppConfig

    base = Path(home)
    modelo = _CONFIG_MODELO[0]
    valor = AppConfig(
        home=base,
        database=base / "cinenode.sqlite3",
        assets_dir=base / "assets",
        projects_dir=base / "projects",
        outputs_dir=base / "outputs",
        uploads_dir=base / "uploads",
        backups_dir=base / "backups",
        logs_dir=base / "logs",
        models_dir=base / "models",
        engines_dir=base / "engines",
        temp_dir=base / "tmp",
        frontend_dir=Path(modelo.frontend_dir),
        host="127.0.0.1",
        port=8788,
        max_upload_bytes=modelo.max_upload_bytes,
        command_timeout_seconds=modelo.command_timeout_seconds,
        local_access_token="test-token",
        allow_shutdown_endpoint=False,
    )
    valor.ensure_directories()
    return valor


_CONFIG_MODELO: list = []


@pytest.fixture(autouse=True)
def _guardar_modelo(config):
    """O conftest já monta um AppConfig completo; reusar evita duplicar 17 campos."""
    _CONFIG_MODELO.clear()
    _CONFIG_MODELO.append(config)
    yield


def grafo(texto: str = "conteúdo para restaurar") -> WorkflowGraph:
    return WorkflowGraph.model_validate({
        "version": 1,
        "nodes": [
            {"id": "p", "type": "input.text", "position": {"x": 0, "y": 0}, "config": {"text": texto}},
            {"id": "s", "type": "output.preview", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [{"id": "e", "source": "p", "target": "s"}],
        "metadata": {},
    })


def _povoar(app) -> dict:
    """Cria estado real: projeto com grafo, asset em disco e job."""
    store = app.state.store
    projeto = store.create_project(type("P", (), {
        "name": "Projeto para restaurar", "description": "", "graph": grafo(),
    })())
    arquivo = app.state.config.outputs_dir / "asset-restore.png"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    asset = store.add_asset(arquivo, "image", projeto["id"], original_name="asset-restore.png")
    job = store.create_job(projeto["id"], grafo())
    return {"projeto": projeto, "asset": asset, "job": job}


def test_backup_restaura_em_ambiente_limpo(config, tmp_path):
    """O teste que a Bible exige: gerar, restaurar em base vazia, comparar contagens."""
    app = create_app(config)
    with TestClient(app):
        antes = _povoar(app)
        contagens_antes = {
            "projetos": len(app.state.store.list_projects()),
            "assets": len(app.state.store.list_assets(limit=1000)),
            "jobs": len(app.state.store.list_jobs(limit=1000)),
        }
        backup = create_backup(app.state.db, app.state.config)

    from pathlib import Path as _P
    caminho = _P(backup["path"] if isinstance(backup, dict) else backup)
    assert zipfile.is_zipfile(caminho), "o backup precisa ser um ZIP legível"

    # Ambiente limpo de verdade: outro diretório, outro banco, nada compartilhado.
    config_limpo = _config_limpo(tmp_path / "limpo")
    db_limpo = Database(config_limpo.database)
    db_limpo.initialize()

    restore_backup(db_limpo, config_limpo, caminho, replace_existing=True)

    app2 = create_app(config_limpo)
    with TestClient(app2):
        store = app2.state.store
        assert len(store.list_projects()) == contagens_antes["projetos"]
        assert len(store.list_assets(limit=1000)) == contagens_antes["assets"]
        assert len(store.list_jobs(limit=1000)) == contagens_antes["jobs"]

        # Contagem igual não basta: o conteúdo precisa voltar íntegro.
        restaurado = store.get_project(antes["projeto"]["id"])
        assert restaurado["name"] == "Projeto para restaurar"
        nos = {n["id"]: n for n in restaurado["graph"]["nodes"]}
        assert nos["p"]["config"]["text"] == "conteúdo para restaurar"


def test_arquivo_do_asset_volta_e_abre(config, tmp_path):
    """Restaurar o registro sem o arquivo produz uma biblioteca de ponteiros mortos."""
    app = create_app(config)
    with TestClient(app):
        antes = _povoar(app)
        conteudo_original = (app.state.config.outputs_dir / "asset-restore.png").read_bytes()
        backup = create_backup(app.state.db, app.state.config)

    from pathlib import Path as _P
    caminho = _P(backup["path"] if isinstance(backup, dict) else backup)
    config_limpo = _config_limpo(tmp_path / "limpo2")
    db_limpo = Database(config_limpo.database)
    db_limpo.initialize()
    restore_backup(db_limpo, config_limpo, caminho, replace_existing=True)

    app2 = create_app(config_limpo)
    with TestClient(app2):
        from pathlib import Path

        asset = app2.state.store.get_asset(antes["asset"]["id"])
        arquivo = Path(asset["path"])
        assert arquivo.is_file(), f"o arquivo do asset não voltou: {arquivo}"
        assert arquivo.read_bytes() == conteudo_original, "conteúdo do asset divergiu"


def test_backup_nao_carrega_a_chave_do_provedor(config):
    """`settings` guarda a chave do OpenRouter. Um backup que a leva vaza credencial."""
    app = create_app(config)
    with TestClient(app):
        app.state.gateway.save_settings({
            "openrouter_key": "sk-or-chave-de-teste-nao-deve-vazar",
            "openrouter_enabled": True,
        })
        backup = create_backup(app.state.db, app.state.config)

    from pathlib import Path as _P
    caminho = _P(backup["path"] if isinstance(backup, dict) else backup)
    with zipfile.ZipFile(caminho) as zf:
        bruto = b"".join(zf.read(nome) for nome in zf.namelist())
    assert b"sk-or-chave-de-teste-nao-deve-vazar" not in bruto, (
        "a chave do provedor está em texto plano dentro do backup"
    )


def test_restaurar_backup_corrompido_falha_sem_destruir_a_base(config, tmp_path):
    """Restauração que apaga antes de validar transforma erro de arquivo em perda total."""
    app = create_app(config)
    with TestClient(app):
        _povoar(app)
        antes = len(app.state.store.list_projects())

        ruim = tmp_path / "corrompido.zip"
        ruim.write_bytes(b"isto nao e um zip")

        with pytest.raises(Exception):
            restore_backup(app.state.db, app.state.config, ruim, replace_existing=True)

        # A base precisa continuar utilizável depois da tentativa falha.
        assert len(app.state.store.list_projects()) == antes

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PydanticField

from . import __version__
from .agent import StudioAgent
from .backup import BackupError, create_backup, export_project, restore_backup
from .config import AppConfig
from .database import Database
from .engines import EngineRegistry
from .events import EventBus
from .gateway import AIGateway, GatewayError
from .governance import (
    log_governance,
    read_governance_snapshot,
    registrar_alerta,
    registrar_auditoria,
    registrar_decisao,
    registrar_opensource,
    seed_governance,
    set_alert_status,
    update_task,
)
from .indexer import CATEGORIAS, AssetIndexer
from .modules import FASES, ModuleRegistry
from .perzon import OPERACOES as PERZON_OPERACOES
from .perzon import PerzonEngine, PerzonOperationError, operacoes_por_modulo
from .registry_models import ModelRegistry
from .policy import BASES_DE_DIREITOS, BASES_QUE_AUTORIZAM
from .jobs import JobManager
from .schemas import (
    AgentChatRequest,
    BackupRequest,
    GovernanceTaskPatch,
    JobCreate,
    ProjectCreate,
    ProjectUpdate,
    RestoreRequest,
    SettingsPatch,
    WorkflowGraph,
    SnapshotCreate,
    CollectionCreate,
    CollectionItem,
)
from .security import require_local_request, sanitize_filename
from .store import Store
from .util import sha256_file, utc_now
from .workflow import NODE_CATALOG, preflight_workflow, validate_workflow


# Modelos de payload das rotas novas. Precisam ficar no escopo do módulo: com
# `from __future__ import annotations` a anotação vira string, e o FastAPI só a
# resolve pelos globals — dentro de `create_app` ela viraria query param.
class GatewaySettingsPayload(BaseModel):
    openrouter_enabled: bool | None = None
    openrouter_key: str | None = None
    clear_openrouter_key: bool = False
    policy: str | None = None
    bindings: dict[str, Any] | None = None


class GatewayChatPayload(BaseModel):
    slot: str = "texto.raciocinio"
    mensagens: list[dict[str, Any]]
    json_mode: bool = False
    temperatura: float = 0.2


class IndexRunPayload(BaseModel):
    limite: int = PydanticField(default=200, ge=1, le=2000)
    forcar: bool = False


class DireitosPayload(BaseModel):
    base: str
    titular: str = ""


class AlertaPatch(BaseModel):
    status: str
    evidencia: Any | None = None
    resultado: str = ""


class AlertaPayload(BaseModel):
    id: str
    severity: str
    kind: str
    fact: str
    action: str
    module_id: str = ""
    origem: str = ""
    causa: str = ""
    impacto: str = ""
    task_id: str = ""
    arquivos: list[str] = []
    teste: str = ""


class DecisaoPayload(BaseModel):
    id: str
    titulo: str
    estado: str
    contexto: str
    decisao: str
    consequencias: str = ""
    modulos: list[str] = []
    documento: str = ""


class AuditoriaPayload(BaseModel):
    sessao: str
    resultado: str
    escopo: str = ""
    itens_auditados: int = 0
    falhas_encontradas: int = 0
    falhas_corrigidas: int = 0
    testes_total: int = 0
    testes_verdes: int = 0
    evidencia: Any | None = None


class PerzonExecutarPayload(BaseModel):
    """Aceita asset registrado ou caminho solto; o asset é o caminho normal.

    Deixar os dois é o que permite testar uma operação sobre um arquivo que ainda
    não foi para a biblioteca, sem obrigar a importar antes de saber se serve.
    """
    feature_id: str
    asset_id: str = ""
    caminho: str = ""
    parametros: dict[str, Any] = {}


class WebFetchPayload(BaseModel):
    url: str
    modo: str = "texto"      # texto | html | metadados


# ---- SEC-005: o navegador interno nao pode virar porta para a rede interna ----
# Resolver o nome ANTES de conectar e recusar faixas privadas fecha o SSRF. Sem isto,
# `http://169.254.169.254` ou `http://127.0.0.1:11434` seriam lidos pelo servidor e
# devolvidos ao cliente.
_FAIXAS_BLOQUEADAS = "privada, loopback, link-local, multicast ou reservada"
_MAX_BYTES_WEB = 10 * 1024 * 1024
_MAX_REDIRECIONAMENTOS = 3


def _endereco_permitido(host: str) -> tuple[bool, str]:
    """Resolve o host e recusa qualquer IP que não seja público."""
    import ipaddress
    import socket

    if not host:
        return False, "endereço sem host"
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        return False, f"não consegui resolver {host}: {exc.strerror or exc}"
    for info in infos:
        endereco = info[4][0]
        try:
            ip = ipaddress.ip_address(endereco.split("%")[0])
        except ValueError:
            return False, f"endereço inválido: {endereco}"
        # `is_global` NÃO cobre multicast: 224.0.0.1 devolve is_global=True.
        # Cada faixa é checada explicitamente, e o teste prova cada uma.
        if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False, f"{host} resolve para {ip}, que é {_FAIXAS_BLOQUEADAS}"
    return True, ""


def _resolver_destino_publico(url: str) -> tuple[bool, str]:
    from urllib.parse import urlsplit

    partes = urlsplit(url)
    if partes.scheme not in ("http", "https"):
        return False, f"esquema não suportado: {partes.scheme or '(vazio)'}"
    return _endereco_permitido(partes.hostname or "")


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig.from_env()
    config.ensure_directories()
    db = Database(config.database)
    db.initialize()
    store = Store(db, config)
    store.initialize_defaults()
    seed_governance(db)
    events = EventBus()
    registry = EngineRegistry(store, config)
    jobs = JobManager(store, registry, config, events)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log_governance(db, "INFO", "app.started", {"version": __version__, "home": str(config.home)})
        await jobs.start()
        app.state.ready = True
        # O indexador só trabalha no ocioso; ele checa job ativo antes de tocar na GPU.
        indexer.start_background()
        try:
            yield
        finally:
            app.state.ready = False
            await indexer.stop()
            await jobs.stop()
            log_governance(db, "INFO", "app.stopped", {})

    app = FastAPI(
        title="Avangard CineNode Local",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.db = db
    app.state.store = store
    app.state.events = events
    app.state.registry = registry
    app.state.jobs = jobs
    gateway = AIGateway(store)
    indexer = AssetIndexer(store, gateway, jobs)
    app.state.gateway = gateway
    app.state.indexer = indexer
    app.state.ready = False

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.url.path.startswith("/api/") or request.url.path.startswith("/media/"):
            try:
                require_local_request(request, config)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "Entrada inválida", "details": exc.errors()}})

    @app.exception_handler(BackupError)
    async def backup_error(_: Request, exc: BackupError):
        return JSONResponse(status_code=400, content={"error": {"code": "BACKUP_ERROR", "message": str(exc)}})

    @app.exception_handler(Exception)
    async def unhandled_error(_: Request, exc: Exception):
        log_governance(db, "ERROR", "api.unhandled_error", {"type": type(exc).__name__, "message": str(exc)})
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}})

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "ready": bool(app.state.ready),
            "version": __version__,
            "database": str(config.database),
            "active_job_id": jobs.active_job_id,
            "time": utc_now(),
        }

    @app.get("/api/bootstrap")
    async def bootstrap():
        settings = store.list_settings()
        return {
            "app": {"name": "Avangard CineNode Local", "version": __version__, "profile": settings.get("app.profile")},
            "preferences": settings.get("app.preferences"),
            "node_catalog": NODE_CATALOG,
            "model_profiles": settings.get("model_profiles", {}),
            "paths": {
                "home": str(config.home), "models": str(config.models_dir), "engines": str(config.engines_dir),
                "outputs": str(config.outputs_dir), "backups": str(config.backups_dir), "logs": str(config.logs_dir),
            },
        }

    @app.get("/api/projects")
    async def list_projects():
        return {"items": store.list_projects()}

    @app.post("/api/projects", status_code=201)
    async def create_project(payload: ProjectCreate):
        project = store.create_project(payload)
        await events.publish("projects.updated", {"project_id": project["id"], "action": "created"})
        return project

    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str):
        return store.get_project(project_id)

    @app.put("/api/projects/{project_id}")
    async def update_project(project_id: str, payload: ProjectUpdate):
        project = store.update_project(project_id, payload)
        await events.publish("projects.updated", {"project_id": project_id, "action": "updated"})
        return project

    @app.delete("/api/projects/{project_id}", status_code=204)
    async def delete_project(project_id: str):
        store.delete_project(project_id)
        await events.publish("projects.updated", {"project_id": project_id, "action": "deleted"})
        return None

    @app.post("/api/projects/{project_id}/export")
    async def export_project_route(project_id: str):
        return export_project(db, config, project_id)

    @app.post("/api/workflows/validate")
    async def validate_graph(graph: WorkflowGraph):
        return validate_workflow(graph, for_execution=False)

    @app.get("/api/nodes/catalog")
    async def node_catalog():
        return {"items": NODE_CATALOG}

    @app.get("/api/jobs")
    async def list_jobs(limit: int = 100):
        return {"items": store.list_jobs(limit)}

    @app.post("/api/jobs", status_code=202)
    async def create_job(payload: JobCreate):
        if payload.project_id:
            project = store.get_project(payload.project_id)
            graph = payload.graph or WorkflowGraph.model_validate(project["graph"])
        elif payload.graph:
            graph = payload.graph
        else:
            raise HTTPException(status_code=400, detail="Provide project_id or graph")
        validation = validate_workflow(graph, for_execution=True)
        if not validation["valid"]:
            raise HTTPException(status_code=422, detail={"code": "WORKFLOW_INVALID", "errors": validation["errors"]})
        job = store.create_job(payload.project_id, graph)
        await jobs.enqueue(job["id"])
        return job

    # Rota literal antes da parametrizada: o FastAPI casa na ordem de registro, e
    # `/api/jobs/{job_id}` trataria "resumable" como um ID de job.
    @app.get("/api/jobs/resumable")
    async def jobs_resumable(request: Request) -> Any:
        require_local_request(request, config)
        return {"itens": store.list_resumable_jobs()}

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str):
        return store.get_job(job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str):
        job = store.request_cancel(job_id)
        await events.publish("jobs.updated", {"job_id": job_id, "cancel_requested": True})
        return job

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry_job(job_id: str):
        job = store.retry_job(job_id)
        await jobs.enqueue(job["id"])
        return job

    @app.get("/api/assets")
    async def list_assets(
        limit: int = 200,
        project_id: str | None = None,
        kind: str | None = None,
        search: str | None = None,
        deleted: bool = False,
    ):
        return {"items": store.list_assets(
            limit, project_id, only_deleted=deleted, kind=kind, search=search,
        )}

    @app.post("/api/assets/upload", status_code=201)
    async def upload_asset(file: UploadFile = File(...), project_id: str | None = None):
        safe_name = sanitize_filename(file.filename or "upload.bin")
        temp_path = config.temp_dir / f"incoming-{os.getpid()}-{safe_name}.part"
        total = 0
        try:
            with temp_path.open("wb") as stream:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > config.max_upload_bytes:
                        raise HTTPException(status_code=413, detail=f"Upload exceeds {config.max_upload_bytes} bytes")
                    stream.write(chunk)
            destination = config.uploads_dir / f"{utc_now().replace(':','')}-{safe_name}"
            os.replace(temp_path, destination)
            mime = file.content_type or "application/octet-stream"
            kind = "image" if mime.startswith("image/") else "video" if mime.startswith("video/") else "audio" if mime.startswith("audio/") else "file"
            asset = store.add_asset(destination, kind, project_id=project_id, original_name=safe_name, mime_type=mime, metadata={"uploaded": True})
            await events.publish("gallery.updated", {"asset_id": asset["id"]})
            return asset
        finally:
            await file.close()
            temp_path.unlink(missing_ok=True)

    @app.get("/api/assets/{asset_id}")
    async def get_asset(asset_id: str):
        return store.get_asset(asset_id)

    @app.get("/media/{asset_id}")
    async def serve_asset(asset_id: str):
        asset = store.get_asset(asset_id)
        path = Path(asset["path"])
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Asset file missing")
        return FileResponse(path, media_type=asset["mime_type"], filename=asset["original_name"] or path.name)

    @app.get("/api/settings")
    async def get_settings():
        return store.list_settings()

    @app.patch("/api/settings")
    async def patch_settings(payload: SettingsPatch):
        forbidden = {"local_access_token"}
        for key, value in payload.values.items():
            if key in forbidden:
                raise HTTPException(status_code=400, detail=f"Setting cannot be changed through API: {key}")
            store.set_setting(key, value)
        store.audit("local-super-admin", "settings.updated", "settings", None, {"keys": list(payload.values)})
        log_governance(db, "INFO", "settings.updated", {"keys": list(payload.values)})
        await events.publish("settings.updated", {"keys": list(payload.values)})
        await events.publish("governance.updated", {"source": "settings"})
        return store.list_settings()

    @app.get("/api/engines/status")
    async def engine_status():
        statuses = await registry.status_all()
        now = utc_now()
        for item in statuses:
            db.execute(
                "INSERT INTO engine_checks(engine_id,available,version,detail,checked_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(engine_id) DO UPDATE SET available=excluded.available,version=excluded.version,detail=excluded.detail,checked_at=excluded.checked_at",
                (item["engine_id"], int(bool(item["available"])), item.get("version"), str(item.get("detail", "")), now),
            )
        await events.publish("engines.updated", {"checked_at": now})
        return {"items": statuses, "checked_at": now, "gpu": await registry.gpu_info()}

    @app.get("/api/model-profiles")
    async def model_profiles():
        profiles = registry.profiles()
        enriched = {}
        for profile_id, profile in profiles.items():
            missing = []
            for key in ("model", "diffusion_model", "high_noise_diffusion_model", "vae", "llm", "clip_l", "clip_g", "t5xxl", "clip_vision"):
                value = profile.get(key)
                if value and not Path(str(value)).expanduser().is_file():
                    missing.append({"field": key, "path": str(value)})
            enriched[profile_id] = {**profile, "ready": not missing, "missing_files": missing}
        return {"items": enriched}

    @app.get("/api/governance/snapshot")
    async def governance_snapshot():
        snapshot = read_governance_snapshot(db)
        response = JSONResponse(snapshot)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Type"] = "application/json"
        return response

    @app.patch("/api/governance/tasks/{task_id}")
    async def governance_task(task_id: str, payload: GovernanceTaskPatch):
        if not update_task(db, task_id, payload.status, payload.evidence):
            raise HTTPException(status_code=404, detail="Governance task not found")
        await events.publish("governance.updated", {"source": "task", "task_id": task_id})
        return read_governance_snapshot(db)

    @app.post("/api/agent/chat")
    async def agent_chat(payload: AgentChatRequest):
        agent = StudioAgent(store)
        result = await agent.converse(
            [{"role": item.role, "content": item.content} for item in payload.messages],
            payload.graph.model_dump() if payload.graph else None,
        )
        return {
            "reply": result.reply,
            "proposal": result.proposal,
            "summary": result.summary,
            "tools": result.tool_trace,
            # Ações que o front executa no painel: abrir navegador ou software.
            "painel_acoes": result.painel_acoes,
        }

    # ---- Versionamento de projeto -------------------------------------------

    @app.get("/api/projects/{project_id}/snapshots")
    async def list_snapshots(project_id: str):
        store.get_project(project_id)
        return {"items": store.list_snapshots(project_id)}

    @app.post("/api/projects/{project_id}/snapshots", status_code=201)
    async def create_snapshot(project_id: str, payload: SnapshotCreate):
        snapshot = store.create_snapshot(project_id, label=payload.label, note=payload.note)
        await events.publish("projects.updated", {"project_id": project_id, "snapshot_id": snapshot["id"]})
        return snapshot

    @app.get("/api/snapshots/{snapshot_id}")
    async def get_snapshot(snapshot_id: str):
        return store.get_snapshot(snapshot_id)

    @app.post("/api/snapshots/{snapshot_id}/restore")
    async def restore_snapshot(snapshot_id: str):
        project = store.restore_snapshot(snapshot_id)
        await events.publish("projects.updated", {"project_id": project["id"], "restored_from": snapshot_id})
        return project

    @app.delete("/api/snapshots/{snapshot_id}", status_code=204)
    async def delete_snapshot(snapshot_id: str):
        store.delete_snapshot(snapshot_id)
        return Response(status_code=204)

    # ---- Ciclo de vida do asset ---------------------------------------------

    @app.delete("/api/assets/{asset_id}")
    async def delete_asset(asset_id: str):
        asset = store.soft_delete_asset(asset_id)
        await events.publish("gallery.updated", {"asset_id": asset_id, "deleted": True})
        return asset

    @app.post("/api/assets/{asset_id}/restore")
    async def restore_asset(asset_id: str):
        asset = store.restore_asset(asset_id)
        await events.publish("gallery.updated", {"asset_id": asset_id, "restored": True})
        return asset

    @app.post("/api/assets/{asset_id}/purge")
    async def purge_asset(asset_id: str):
        result = store.purge_asset(asset_id)
        await events.publish("gallery.updated", {"asset_id": asset_id, "purged": True})
        return result

    @app.post("/api/assets/purge-deleted")
    async def purge_deleted_assets():
        result = store.purge_deleted_assets()
        await events.publish("gallery.updated", {"purged": result["count"]})
        return result

    # ---- Colecoes: bibliotecas, referencias e galerias -----------------------

    @app.get("/api/collections")
    async def list_collections():
        return {"items": store.list_collections()}

    @app.post("/api/collections", status_code=201)
    async def create_collection(payload: CollectionCreate):
        return store.create_collection(payload.name, payload.kind, payload.description)

    @app.get("/api/collections/{collection_id}")
    async def get_collection(collection_id: str):
        return store.get_collection(collection_id)

    @app.post("/api/collections/{collection_id}/items")
    async def add_collection_item(collection_id: str, payload: CollectionItem):
        return store.add_to_collection(collection_id, payload.asset_id)

    @app.delete("/api/collections/{collection_id}/items/{asset_id}")
    async def remove_collection_item(collection_id: str, asset_id: str):
        return store.remove_from_collection(collection_id, asset_id)

    @app.delete("/api/collections/{collection_id}", status_code=204)
    async def delete_collection(collection_id: str):
        store.delete_collection(collection_id)
        return Response(status_code=204)

    @app.get("/api/events")
    async def event_stream():
        return StreamingResponse(events.stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/backups")
    async def make_backup(payload: BackupRequest):
        result = create_backup(db, config, include_assets=payload.include_assets, include_outputs=payload.include_outputs)
        log_governance(db, "INFO", "backup.created", result)
        await events.publish("governance.updated", {"source": "backup"})
        return result

    @app.get("/api/backups")
    async def list_backups():
        items = []
        for path in sorted(config.backups_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True):
            items.append({"path": str(path), "name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
        return {"items": items}

    @app.post("/api/backups/restore")
    async def restore(payload: RestoreRequest):
        result = restore_backup(db, config, Path(payload.backup_path), replace_existing=payload.replace_existing)
        store.initialize_defaults()
        seed_governance(db)
        log_governance(db, "WARN", "backup.restored", {"path": payload.backup_path})
        await events.publish("governance.updated", {"source": "restore"})
        return result

    @app.post("/api/admin/shutdown", status_code=202)
    async def shutdown():
        if not config.allow_shutdown_endpoint:
            raise HTTPException(status_code=403, detail="Shutdown endpoint disabled")

        async def terminate() -> None:
            await asyncio.sleep(0.4)
            os.kill(os.getpid(), signal.SIGTERM)

        asyncio.create_task(terminate())
        return {"status": "shutting_down"}


    # ================= GATEWAY DE PROVEDORES =================
    # Um endereço, muitos fornecedores. O nó pede capacidade, nunca fornecedor.

    def _gateway_error(exc: GatewayError) -> JSONResponse:
        return JSONResponse(status_code=502, content=exc.as_dict())

    @app.get("/api/ai/catalog")
    async def ai_catalog(request: Request) -> Any:
        require_local_request(request, config)
        return await app.state.gateway.catalog()

    @app.get("/api/ai/settings")
    async def ai_settings_get(request: Request) -> Any:
        require_local_request(request, config)
        return app.state.gateway.settings()

    @app.put("/api/ai/settings")
    async def ai_settings_put(request: Request, payload: GatewaySettingsPayload) -> Any:
        require_local_request(request, config)
        return app.state.gateway.save_settings(payload.model_dump(exclude_none=True))

    @app.post("/api/ai/chat")
    async def ai_chat(request: Request, payload: GatewayChatPayload) -> Any:
        require_local_request(request, config)
        try:
            if payload.json_mode:
                return await app.state.gateway.chat_json(
                    payload.slot, payload.mensagens, temperature=payload.temperatura)
            return await app.state.gateway.chat(
                payload.slot, payload.mensagens, temperature=payload.temperatura)
        except GatewayError as exc:
            return _gateway_error(exc)

    @app.get("/api/ai/resolve/{slot}")
    async def ai_resolve(request: Request, slot: str) -> Any:
        require_local_request(request, config)
        try:
            resolution = await app.state.gateway.resolve(slot)
        except GatewayError as exc:
            return _gateway_error(exc)
        return {"slot": resolution.slot, "provedor": resolution.provider, "modelo": resolution.model,
                "motivo": resolution.reason, "local": resolution.local}

    # ================= BIBLIOTECA E INDEXADOR =================

    @app.get("/api/library/summary")
    async def library_summary(request: Request) -> Any:
        require_local_request(request, config)
        return app.state.indexer.summary()

    @app.get("/api/library/assets")
    async def library_assets(
        request: Request,
        origem: str | None = None,
        categoria: str | None = None,
        kind: str | None = None,
        busca: str | None = None,
        limite: int = 200,
    ) -> Any:
        """Biblioteca categorizada: saídas e uploads são coleções separadas."""
        require_local_request(request, config)
        indexer = app.state.indexer
        if busca:
            assets = indexer.search(busca, limit=limite)
        else:
            assets = app.state.store.list_assets(limit=limite, kind=kind)
        resultado = []
        for asset in assets:
            ficha = (asset.get("metadata") or {}).get("index") or {}
            asset_origem = "saida" if asset.get("job_id") else "upload"
            if origem and asset_origem != origem:
                continue
            if categoria and (ficha.get("categoria") or "nao classificado") != categoria:
                continue
            if kind and asset.get("kind") != kind:
                continue
            resultado.append({
                "id": asset["id"],
                "kind": asset["kind"],
                "origem": asset_origem,
                "nome_original": asset.get("original_name"),
                "mime_type": asset.get("mime_type"),
                "size_bytes": asset.get("size_bytes"),
                "created_at": asset.get("created_at"),
                "job_id": asset.get("job_id"),
                "indexado": bool(ficha),
                "titulo": ficha.get("titulo") or asset.get("original_name") or asset["id"],
                "categoria": ficha.get("categoria") or "nao classificado",
                "subcategoria": ficha.get("subcategoria"),
                "etiquetas": ficha.get("etiquetas") or [],
                "descricao": ficha.get("descricao") or "",
                "nome_sugerido": ficha.get("nome_sugerido"),
                "score": asset.get("score"),
                # A UI precisa saber o que já foi declarado para desenhar o estado certo.
                "direitos": (asset.get("metadata") or {}).get("direitos")
                            or {"base": "nao_declarado", "titular": ""},
            })
        return {"itens": resultado, "total": len(resultado), "categorias": CATEGORIAS}

    @app.get("/api/indexer/status")
    async def indexer_status(request: Request) -> Any:
        require_local_request(request, config)
        estado = app.state.indexer.status.as_dict()
        estado["pendentes"] = len(app.state.indexer.pending(limit=1000))
        return estado

    @app.post("/api/indexer/run")
    async def indexer_run(request: Request, payload: IndexRunPayload) -> Any:
        require_local_request(request, config)
        return await app.state.indexer.run_once(limit=payload.limite, force=payload.forcar)

    @app.post("/api/indexer/asset/{asset_id}")
    async def indexer_asset(request: Request, asset_id: str, forcar: bool = False) -> Any:
        require_local_request(request, config)
        try:
            return await app.state.indexer.index_asset(asset_id, force=forcar)
        except GatewayError as exc:
            return _gateway_error(exc)

    @app.post("/api/indexer/asset/{asset_id}/rename")
    async def indexer_rename(request: Request, asset_id: str) -> Any:
        require_local_request(request, config)
        try:
            return app.state.indexer.rename_to_suggestion(asset_id)
        except GatewayError as exc:
            return _gateway_error(exc)

    # ================= NAVEGADOR INTERNO =================
    # Muitos sites recusam iframe por X-Frame-Options. Este proxy busca o conteúdo
    # pelo servidor local e devolve o texto, para o nó consumir e para o painel exibir
    # quando o embed direto for bloqueado.

    @app.post("/api/web/fetch")
    async def web_fetch(request: Request, payload: WebFetchPayload) -> Any:
        require_local_request(request, config)
        url = payload.url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        permitido, motivo = _resolver_destino_publico(url)
        if not permitido:
            return JSONResponse(status_code=403, content={
                "erro": "DESTINO_BLOQUEADO",
                "mensagem": f"O navegador interno não acessa este endereço: {motivo}.",
                "como_corrigir": "O painel só abre endereços públicos. Serviços locais "
                                 "aparecem na aba Software, com estado medido."})

        import httpx as _httpx
        cabecalhos = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CineNode Local"}
        try:
            # `follow_redirects=False`: cada salto é revalidado, senão um redirecionamento
            # público para 127.0.0.1 contornaria a checagem inicial.
            async with _httpx.AsyncClient(timeout=25.0, follow_redirects=False) as client:
                response = await client.get(url, headers=cabecalhos)
                for _ in range(_MAX_REDIRECIONAMENTOS):
                    if response.status_code not in (301, 302, 303, 307, 308):
                        break
                    destino = str(response.headers.get("location") or "")
                    if not destino:
                        break
                    destino = str(response.url.join(destino))
                    permitido, motivo = _resolver_destino_publico(destino)
                    if not permitido:
                        return JSONResponse(status_code=403, content={
                            "erro": "REDIRECIONAMENTO_BLOQUEADO",
                            "mensagem": f"O site redirecionou para um endereço interno: {motivo}.",
                            "como_corrigir": "Redirecionamento para a rede local é recusado."})
                    response = await client.get(destino, headers=cabecalhos)
                else:
                    return JSONResponse(status_code=502, content={
                        "erro": "REDIRECIONAMENTO_DEMAIS",
                        "mensagem": f"Mais de {_MAX_REDIRECIONAMENTOS} redirecionamentos.",
                        "como_corrigir": "Abra o endereço final direto."})
        except Exception as exc:
            return JSONResponse(status_code=502, content={
                "erro": "REDE", "mensagem": f"Não consegui acessar {url}.",
                "como_corrigir": "Confira o endereço e a conexão. Detalhe: " + str(exc)[:160]})

        if len(response.content) > _MAX_BYTES_WEB:
            return JSONResponse(status_code=413, content={
                "erro": "RESPOSTA_GRANDE",
                "mensagem": f"A página tem mais de {_MAX_BYTES_WEB // (1024*1024)} MB.",
                "como_corrigir": "Baixe o arquivo fora do painel."})
        html = response.text
        titulo = ""
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if match:
            titulo = re.sub(r"\s+", " ", match.group(1)).strip()[:200]
        bloqueia_iframe = any(
            header.lower() in {"x-frame-options"} for header in response.headers
        ) or "frame-ancestors" in (response.headers.get("content-security-policy") or "").lower()
        corpo = None
        if payload.modo in ("texto", "metadados"):
            limpo = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
            limpo = re.sub(r"(?s)<[^>]+>", " ", limpo)
            corpo = re.sub(r"\s+", " ", limpo).strip()[:20000]
        return {
            "url": str(response.url),
            "status": response.status_code,
            "titulo": titulo,
            "content_type": response.headers.get("content-type", ""),
            "embed_bloqueado": bloqueia_iframe,
            "texto": corpo,
            "html": html[:400000] if payload.modo == "html" else None,
        }

    # ================= MCP / SOFTWARE CONTROLADO =================
    # Registro dos alvos que o painel lateral pode abrir e controlar. Um alvo só fica
    # "no ar" quando o probe de saúde responde; nada é declarado pronto sem prova.

    DEFAULT_TARGETS = [
        {"id": "comfyui", "nome": "ComfyUI", "icone": "processador", "url": "http://127.0.0.1:8188",
         "health": "http://127.0.0.1:8188/system_stats", "tipo": "sidecar",
         "instalar": "scripts\\install-comfy.ps1", "embed": True},
        {"id": "ollama", "nome": "Ollama", "icone": "agente", "url": "http://127.0.0.1:11434",
         "health": "http://127.0.0.1:11434/api/version", "tipo": "runtime",
         "instalar": "winget install Ollama.Ollama", "embed": False},
        {"id": "brainlink", "nome": "Brainlink", "icone": "conhecimento", "url": "http://127.0.0.1:8080",
         "health": "http://127.0.0.1:8080", "tipo": "vendor",
         "instalar": "yarn dev em 26-Aiia universal UI/AFFINE", "embed": True},
        {"id": "flowise", "nome": "Flowise", "icone": "fluxo", "url": "http://127.0.0.1:3000",
         "health": "http://127.0.0.1:3000/api/v1/ping", "tipo": "vendor",
         "instalar": "npx flowise start", "embed": True},
    ]

    @app.get("/api/mcp/targets")
    async def mcp_targets(request: Request) -> Any:
        require_local_request(request, config)
        salvos = app.state.store.get_setting("mcp_targets") or []
        alvos = {t["id"]: t for t in DEFAULT_TARGETS}
        for extra in salvos:
            alvos[extra["id"]] = {**alvos.get(extra["id"], {}), **extra}
        import httpx as _httpx
        async def probe(alvo: dict[str, Any]) -> dict[str, Any]:
            estado = "fora"
            detalhe = ""
            try:
                async with _httpx.AsyncClient(timeout=2.5) as client:
                    response = await client.get(alvo["health"])
                    estado = "no ar" if response.status_code < 500 else "instavel"
                    detalhe = f"HTTP {response.status_code}"
            except Exception as exc:
                detalhe = type(exc).__name__
            return {**alvo, "estado": estado, "detalhe": detalhe}
        return {"alvos": await asyncio.gather(*(probe(a) for a in alvos.values()))}

    @app.put("/api/mcp/targets")
    async def mcp_targets_put(request: Request) -> Any:
        require_local_request(request, config)
        body = await request.json()
        alvos = body.get("alvos") or []
        app.state.store.set_setting("mcp_targets", alvos)
        app.state.store.audit("system", "mcp.targets", "setting", "mcp_targets", {"total": len(alvos)})
        return {"alvos": alvos}


    # ================= MÓDULOS E ALERTA DE CONCLUSÃO =================
    # O estado sai dos gates com evidência no disco, nunca de um campo escrito à mão.

    def _raiz_do_projeto() -> Path:
        """Onde estão `scripts/` e `docs/evidence/`.

        Instalado como wheel, `__file__` aponta para site-packages — a evidência não
        mora lá. A raiz é a pasta que contém `scripts/`: procura a partir de `data/`
        e do diretório de trabalho, nesta ordem.
        """
        for candidato in (config.home.parent, Path.cwd(), Path(__file__).resolve().parents[3]):
            if (candidato / "scripts").is_dir() and (candidato / "source").is_dir():
                return candidato
        return Path.cwd()

    @app.get("/api/governance/modules")
    async def governance_modules(request: Request, executar: bool = False) -> Any:
        require_local_request(request, config)
        registro = ModuleRegistry(_raiz_do_projeto(), NODE_CATALOG)
        # `executar=true` roda os comandos: caro, então só sob pedido explícito.
        return registro.relatorio(executar=executar)

    @app.get("/api/governance/phases")
    async def governance_phases(request: Request) -> Any:
        require_local_request(request, config)
        registro = ModuleRegistry(_raiz_do_projeto(), NODE_CATALOG)
        relatorio = registro.relatorio()
        return {"fases": relatorio["fases"], "titulos": FASES,
                "progresso_geral": relatorio["progresso_geral"],
                "concluidos": relatorio["concluidos"], "total": relatorio["total"]}


    # ================= GOVERNANCA: MUTACOES =================
    # O snapshot já era a fonte única de leitura. O que faltava era o caminho de
    # volta: um alerta que ninguém consegue fechar pela UI vira ruído permanente, e
    # `set_alert_status` existia sem rota nenhuma — código morto desde sempre.

    @app.patch("/api/governance/alerts/{alert_id}")
    async def governance_alerta(request: Request, alert_id: str,
                                payload: AlertaPatch) -> Any:
        require_local_request(request, config)
        if payload.status not in {"OPEN", "RESOLVED"}:
            raise HTTPException(status_code=422, detail={
                "code": "STATUS_INVALIDO",
                "message": f"Status '{payload.status}' não existe.",
                "hint": "Use OPEN ou RESOLVED."})
        if not set_alert_status(db, alert_id, payload.status, payload.evidencia):
            raise HTTPException(status_code=404, detail={
                "code": "ALERTA_INEXISTENTE",
                "message": f"Alerta {alert_id} não existe.", "hint": ""})
        if payload.resultado:
            db.execute("UPDATE governance_alerts SET resultado=? WHERE id=?",
                       (payload.resultado, alert_id))
        log_governance(db, "INFO", "governance.alert.updated",
                       {"alert_id": alert_id, "status": payload.status})
        await events.publish("governance.updated",
                             {"source": "alert", "alert_id": alert_id})
        return read_governance_snapshot(db)

    @app.post("/api/governance/alerts")
    async def governance_novo_alerta(request: Request, payload: AlertaPayload) -> Any:
        require_local_request(request, config)
        try:
            resultado = registrar_alerta(
                db, payload.id, severity=payload.severity, kind=payload.kind,
                fact=payload.fact, action=payload.action, module_id=payload.module_id,
                origem=payload.origem, causa=payload.causa, impacto=payload.impacto,
                task_id=payload.task_id, arquivos=payload.arquivos, teste=payload.teste)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail={
                "code": "SEVERIDADE_INVALIDA", "message": str(erro),
                "hint": "Use LOW, MEDIUM, HIGH ou CRITICAL."}) from erro
        await events.publish("governance.updated", {"source": "alert.new"})
        return {**resultado, "snapshot": read_governance_snapshot(db)}

    @app.post("/api/governance/decisions")
    async def governance_decisao(request: Request, payload: DecisaoPayload) -> Any:
        require_local_request(request, config)
        try:
            resultado = registrar_decisao(
                db, payload.id, titulo=payload.titulo, estado=payload.estado,
                contexto=payload.contexto, decisao=payload.decisao,
                consequencias=payload.consequencias, modulos=payload.modulos,
                documento=payload.documento)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail={
                "code": "ESTADO_INVALIDO", "message": str(erro),
                "hint": "Use PROPOSTA, ACEITA, SUBSTITUIDA ou REJEITADA."}) from erro
        await events.publish("governance.updated", {"source": "decision"})
        return resultado

    @app.post("/api/governance/audits")
    async def governance_auditoria(request: Request, payload: AuditoriaPayload) -> Any:
        require_local_request(request, config)
        try:
            resultado = registrar_auditoria(
                db, sessao=payload.sessao, resultado=payload.resultado,
                escopo=payload.escopo, itens_auditados=payload.itens_auditados,
                falhas_encontradas=payload.falhas_encontradas,
                falhas_corrigidas=payload.falhas_corrigidas,
                testes_total=payload.testes_total, testes_verdes=payload.testes_verdes,
                evidencia=payload.evidencia)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail={
                "code": "RESULTADO_INVALIDO", "message": str(erro),
                "hint": "Use APROVADA, REPROVADA ou BLOQUEADA."}) from erro
        await events.publish("governance.updated", {"source": "audit"})
        return resultado

    @app.post("/api/governance/sincronizar")
    async def governance_sincronizar(request: Request) -> Any:
        """Reconstrói o registro de open source a partir do que o sistema carrega.

        A alternativa era manter duas listas à mão e torcer para não divergirem.
        Aqui a fonte é o registro de modelos, que já mede o disco.
        """
        require_local_request(request, config)
        registro = ModelRegistry(config.models_dir)
        gravados = 0
        for modelo in registro.listar():
            registrar_opensource(
                db, modelo["id"], nome=modelo["nome_front"], origem=modelo["origem"],
                versao=modelo.get("revisao", ""), licenca=modelo["licenca"],
                spdx=modelo.get("spdx", ""), uso_comercial=modelo["uso_comercial"],
                integracao=modelo.get("runtime", ""),
                # ComfyUI e FFmpeg são GPL e rodam como processo separado: instalados
                # na máquina, nunca dentro do pacote. Marcar como redistribuído seria
                # declarar um risco que o desenho justamente evita.
                redistribuido=False,
                conferido=modelo.get("conferido", False),
                observacao=modelo.get("observacao", ""))
            gravados += 1

        # Alerta automático para o que não pode ir a produção. Descobrir a lacuna e
        # não registrá-la é como não tê-la descoberto.
        pendentes = registro.pendencias()
        for pendente in pendentes:
            registrar_alerta(
                db, f"LICENSE-{pendente['id'].replace('/', '-')}",
                severity="HIGH", kind="LICENSE", fact=pendente["o_que_falta"],
                action=f"Ler a licença em {pendente['origem']} e declarar no registro.",
                module_id="OSS", origem="/api/governance/sincronizar",
                causa="peso de terceiro sem licença resolvida",
                impacto="produto MIT distribuindo uso de peso com termo desconhecido",
                task_id="MODEL-002", teste="tests/test_registry_models.py")

        log_governance(db, "INFO", "governance.sync",
                       {"componentes": gravados, "pendentes": len(pendentes)})
        await events.publish("governance.updated", {"source": "sync"})
        return {"componentes": gravados, "alertas_abertos": len(pendentes),
                "snapshot": read_governance_snapshot(db)}

    # ================= FASE E: PERZON EXECUTAVEL =================
    # O PERZON entrega 1697 contratos e 1697 stubs que devolvem
    # `specified_not_implemented`. Estas rotas expõem o que tem cálculo de verdade.

    @app.get("/api/perzon/operacoes")
    async def perzon_operacoes(request: Request) -> Any:
        require_local_request(request, config)
        por_modulo = operacoes_por_modulo()
        return {
            "total": len(PERZON_OPERACOES),
            "modulos": {nome: [op.as_dict() for op in ops]
                        for nome, ops in sorted(por_modulo.items())},
            "nota": "Só aparece aqui o que executa. O resto do catálogo do PERZON "
                    "segue especificado e sem algoritmo.",
        }

    @app.post("/api/perzon/executar")
    async def perzon_executar(request: Request, payload: PerzonExecutarPayload) -> Any:
        require_local_request(request, config)
        caminho = payload.caminho
        if payload.asset_id:
            # `store.get_asset` levanta 404 com detalhe em texto solto. Aqui a UI
            # lê `detail.code` para decidir o que mostrar, então o erro é
            # reescrito na forma estruturada em vez de vazar duas convenções.
            try:
                asset = store.get_asset(payload.asset_id)
            except HTTPException as erro:
                if erro.status_code != 404:
                    raise
                raise HTTPException(status_code=404, detail={
                    "code": "ASSET_INEXISTENTE",
                    "message": f"Asset {payload.asset_id} não existe.",
                    "hint": "Confira em /api/assets qual id está na biblioteca.",
                }) from erro
            caminho = asset["path"]

        motor = PerzonEngine(config.outputs_dir)
        try:
            resultado = motor.executar(payload.feature_id, caminho, payload.parametros)
        except PerzonOperationError as erro:
            # 422 e não 500: a entrada é que não serve, e o corpo diz qual e por quê.
            raise HTTPException(status_code=422, detail=erro.as_dict()) from erro

        # Artefato produzido vira asset registrado, senão o arquivo fica órfão no
        # disco e a biblioteca não o enxerga.
        for artefato in resultado.get("artefatos", []):
            registrado = store.add_asset(
                Path(artefato["caminho"]), artefato["tipo"],
                metadata={"operation": payload.feature_id, "origem": "perzon",
                          "modulo": resultado["modulo"]})
            artefato["asset_id"] = registrado["id"]
        return resultado

    # ================= PROVENIENCIA DE MODELOS (MODEL-002) =================
    # A auditoria mediu 33 modelos carregáveis contra 4 governados. Um produto MIT
    # que carrega peso de licença desconhecida distribui um risco que não declarou.
    # Esta rota não conserta a licença — ela mostra, com nome e origem, o que falta
    # declarar, para que "não sabíamos" deixe de ser uma resposta possível.

    @app.get("/api/models/registry")
    async def models_registry(request: Request) -> Any:
        require_local_request(request, config)
        em_uso = [m["id"] for m in await gateway.local_models()]
        em_uso += [p for p in registry.profiles()]
        relatorio = ModelRegistry(config.models_dir).relatorio(em_uso)
        resposta = JSONResponse(relatorio)
        resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.post("/api/models/registry/evidencia")
    async def models_registry_evidencia(request: Request) -> Any:
        """Grava a evidência que `GATE-LICENSE` lê. Escrever à mão seria o mesmo que
        não ter gate: o arquivo tem de sair da medição, não da intenção."""
        require_local_request(request, config)
        em_uso = [m["id"] for m in await gateway.local_models()]
        em_uso += [p for p in registry.profiles()]
        destino = _raiz_do_projeto() / "docs" / "evidence" / "licencas" / "modelos.json"
        caminho = ModelRegistry(config.models_dir).gravar_evidencia(destino, em_uso)
        return {"arquivo": str(caminho), "gravado_em": utc_now()}

    # ================= BASE DE DIREITOS DO ASSET =================
    # Declarar é do usuário; o executor só consulta. Sem isto, a única saída para o
    # portão de identidade seria desligar a regra — e regra que se desliga não protege.

    @app.get("/api/rights/bases")
    async def rights_bases(request: Request) -> Any:
        require_local_request(request, config)
        return {"bases": [{"id": k, "descricao": v, "autoriza": k in BASES_QUE_AUTORIZAM}
                          for k, v in BASES_DE_DIREITOS.items()]}

    @app.put("/api/assets/{asset_id}/direitos")
    async def asset_direitos(request: Request, asset_id: str, payload: DireitosPayload) -> Any:
        require_local_request(request, config)
        if payload.base not in BASES_DE_DIREITOS:
            raise HTTPException(status_code=422, detail={
                "code": "BASE_DESCONHECIDA",
                "message": f"Base de direitos inválida: {payload.base}",
                "hint": f"Use uma destas: {', '.join(BASES_DE_DIREITOS)}",
            })
        if payload.base == "titular_consentiu" and not payload.titular.strip():
            raise HTTPException(status_code=422, detail={
                "code": "TITULAR_AUSENTE",
                "message": "Declarar que o titular consentiu exige nomear o titular.",
                "hint": "Preencha o campo titular, ou escolha outra base.",
            })
        asset = store.get_asset(asset_id)
        metadata = dict(asset.get("metadata") or {})
        metadata["direitos"] = {"base": payload.base, "titular": payload.titular.strip(),
                                "declarado_em": utc_now()}
        db.execute("UPDATE assets SET metadata_json = ? WHERE id = ?",
                   (db.dump_json(metadata), asset_id))
        store.audit("user", "asset.direitos", "asset", asset_id,
                    {"base": payload.base, "titular": bool(payload.titular.strip())})
        return {"asset_id": asset_id, "direitos": metadata["direitos"]}


    # ================= JOB-001: RETOMADA =================

    @app.post("/api/jobs/{job_id}/resume")
    async def job_resume(request: Request, job_id: str) -> Any:
        require_local_request(request, config)
        job = store.resume_job(job_id)
        await jobs.enqueue(job_id)
        await events.publish("jobs.updated", {"job_id": job_id, "status": "QUEUED"})
        return job

    @app.post("/api/jobs/{job_id}/retry")
    async def job_retry(request: Request, job_id: str) -> Any:
        """Cria um job novo a partir do mesmo grafo. Diferente de retomar: refaz tudo."""
        require_local_request(request, config)
        novo = store.retry_job(job_id)
        await jobs.enqueue(novo["id"])
        await events.publish("jobs.updated", {"job_id": novo["id"], "status": "QUEUED"})
        return novo


    # ================= UX-001: PRÉ-VOO =================

    @app.post("/api/workflows/preflight")
    async def workflow_preflight(request: Request, graph: WorkflowGraph) -> Any:
        """Checa o que falharia na execução, antes de entrar na fila."""
        require_local_request(request, config)
        import httpx as _httpx

        async def vivo(url: str) -> bool:
            try:
                async with _httpx.AsyncClient(timeout=2.0) as client:
                    return (await client.get(url)).status_code < 500
            except Exception:
                return False

        # Só consulta o sidecar quando algum nó realmente depende dele.
        precisa_comfy = any(
            n.type.startswith("model3d.") or str((n.config or {}).get("engine", "")) == "comfyui"
            for n in graph.nodes
        )
        saude = {"comfyui": await vivo("http://127.0.0.1:8188/system_stats")} if precisa_comfy else {}
        return preflight_workflow(graph, store=store, config=config, sidecar_health=saude)

    bundled_docs = Path(__file__).resolve().parent / "docs"
    source_docs = Path(__file__).resolve().parents[3] / "docs"
    docs_dir = bundled_docs if bundled_docs.is_dir() else source_docs
    if docs_dir.is_dir():
        app.mount("/docs-files", StaticFiles(directory=str(docs_dir), html=False), name="docs-files")
    if not config.frontend_dir.is_dir():
        raise RuntimeError(f"Frontend directory not found: {config.frontend_dir}")
    # O index.html sai por rota para carimbar a versão dos assets. Sem isso o navegador
    # serve app.js do cache e o usuário vê a interface antiga achando que nada mudou.
    @app.get("/", include_in_schema=False)
    async def frontend_index() -> Any:
        index = config.frontend_dir / "index.html"
        html = index.read_text(encoding="utf-8")
        marca = 0
        for nome in ("app.js", "styles.css"):
            arquivo = config.frontend_dir / nome
            if arquivo.exists():
                marca = max(marca, int(arquivo.stat().st_mtime))
        html = html.replace('src="/app.js"', f'src="/app.js?v={marca}"')
        html = html.replace('href="/styles.css"', f'href="/styles.css?v={marca}"')
        return Response(content=html, media_type="text/html",
                        headers={"Cache-Control": "no-cache, must-revalidate"})

    app.mount("/", StaticFiles(directory=str(config.frontend_dir), html=True), name="frontend")
    return app


app = create_app()

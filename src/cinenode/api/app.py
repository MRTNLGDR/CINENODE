from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator
import asyncio
import json
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cinenode import __version__
from cinenode.backup import BackupService
from cinenode.config import Settings
from cinenode.database import Database
from cinenode.doctor import report as doctor_report
from cinenode.engines.registry import EngineRegistry, builtin_engines
from cinenode.events import EventBus
from cinenode.jobs import JobService
from cinenode.nodes import NodeRegistry, builtin_registry
from cinenode.security import SecurityMiddleware
from cinenode.store import Store
from cinenode.workflow import compile_workflow


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)


class WorkflowCreate(BaseModel):
    project_id: str | None = None
    name: str = Field(default="Untitled workflow", max_length=160)
    definition: dict[str, Any]


class WorkflowUpdate(BaseModel):
    definition: dict[str, Any]


class JobCreate(BaseModel):
    workflow_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class AppServices:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(settings.database_path)
        self.store = Store(self.database, settings.home)
        self.nodes: NodeRegistry = builtin_registry()
        self.engines: EngineRegistry = builtin_engines(test_mode=settings.test_mode, allow_private=settings.allow_private_engine_urls)
        self.events = EventBus()
        self.jobs = JobService(self.store, self.nodes, self.engines, self.events)
        self.backups = BackupService(settings, self.database)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.prepare()
    services = AppServices(settings)
    services.database.initialize()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await services.jobs.start()
        try:
            yield
        finally:
            await services.jobs.stop()

    app = FastAPI(
        title="CineNode",
        version=__version__,
        description="Local-first modular node canvas and inference orchestration engine",
        lifespan=lifespan,
    )
    app.state.services = services
    app.add_middleware(SecurityMiddleware, settings=settings)

    def missing(exc: KeyError) -> HTTPException:
        return HTTPException(404, f"resource not found: {exc.args[0]}")

    @app.get("/api/health")
    @app.get("/health")
    async def health() -> dict[str, Any]:
        integrity = services.database.integrity_report()
        return {"ok": bool(integrity["ok"]), "product": "CineNode", "version": __version__, "mode": settings.mode, "database": integrity}

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        return settings.public_dict()

    @app.get("/api/settings")
    async def public_settings() -> dict[str, Any]:
        return services.store.public_settings()

    @app.get("/api/nodes")
    async def node_catalog() -> list[dict[str, Any]]:
        return services.nodes.catalog()

    @app.get("/api/engines")
    async def engines() -> list[dict[str, Any]]:
        return services.engines.list()

    @app.post("/api/engines/{engine_id}/probe")
    async def probe_engine(engine_id: str) -> dict[str, Any]:
        try:
            return await services.engines.get(engine_id).probe()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/projects")
    async def list_projects() -> list[dict[str, Any]]:
        return services.store.list_projects()

    @app.post("/api/projects", status_code=201)
    async def create_project(payload: ProjectCreate) -> dict[str, Any]:
        try:
            return services.store.create_project(payload.name, payload.description)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/workflows")
    async def list_workflows(project_id: str | None = None) -> list[dict[str, Any]]:
        return services.store.list_workflows(project_id)

    @app.post("/api/workflows", status_code=201)
    async def create_workflow(payload: WorkflowCreate) -> dict[str, Any]:
        try:
            compile_workflow(payload.definition, services.nodes)
            return services.store.create_workflow(payload.project_id, payload.name, payload.definition)
        except (ValueError, KeyError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return services.store.get_workflow(workflow_id)
        except KeyError as exc:
            raise missing(exc) from exc

    @app.put("/api/workflows/{workflow_id}")
    async def update_workflow(workflow_id: str, payload: WorkflowUpdate) -> dict[str, Any]:
        try:
            compile_workflow(payload.definition, services.nodes)
            return services.store.update_workflow(workflow_id, payload.definition)
        except KeyError as exc:
            raise missing(exc) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/workflows/validate")
    async def validate_workflow(definition: dict[str, Any]) -> dict[str, Any]:
        try:
            compiled = compile_workflow(definition, services.nodes)
            return {"ok": True, "order": list(compiled.order)}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    @app.get("/api/jobs")
    async def list_jobs(limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
        return services.store.list_jobs(limit)

    @app.post("/api/jobs", status_code=202)
    async def create_job(payload: JobCreate) -> dict[str, Any]:
        try:
            return await services.jobs.submit(payload.workflow_id, payload.input)
        except KeyError as exc:
            raise missing(exc) from exc

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str) -> dict[str, Any]:
        try:
            return services.store.get_job(job_id)
        except KeyError as exc:
            raise missing(exc) from exc

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        try:
            return services.jobs.cancel(job_id)
        except KeyError as exc:
            raise missing(exc) from exc

    @app.post("/api/jobs/{job_id}/resume")
    async def resume_job(job_id: str) -> dict[str, Any]:
        try:
            return await services.jobs.resume(job_id)
        except KeyError as exc:
            raise missing(exc) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str) -> StreamingResponse:
        try:
            services.store.get_job(job_id)
        except KeyError as exc:
            raise missing(exc) from exc

        async def stream() -> AsyncIterator[str]:
            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"
            async for event in services.events.subscribe(f"job:{job_id}"):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/assets/upload", status_code=201)
    async def upload_asset(
        upload: UploadFile = File(...),
        project_id: str | None = None,
        kind: str = "upload",
    ) -> dict[str, Any]:
        safe_name = Path(upload.filename or "upload.bin").name
        destination = settings.assets_dir / "uploads" / f"{uuid.uuid4().hex}-{safe_name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with destination.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, "upload exceeds configured size limit")
                    output.write(chunk)
            return services.store.register_asset(
                destination,
                project_id=project_id,
                job_id=None,
                kind=kind,
                original_name=safe_name,
                media_type=upload.content_type,
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @app.get("/api/assets/{asset_id}")
    async def download_asset(asset_id: str) -> FileResponse:
        try:
            item, path = services.store.get_asset(asset_id)
        except KeyError as exc:
            raise missing(exc) from exc
        if not path.is_file():
            raise HTTPException(410, "asset file is missing")
        return FileResponse(path, media_type=item.get("media_type"), filename=item["original_name"])

    @app.post("/api/backups", status_code=201)
    async def create_backup() -> dict[str, Any]:
        path = await asyncio.to_thread(services.backups.create)
        return {"ok": True, "name": path.name, "bytes": path.stat().st_size}

    @app.post("/api/backups/restore")
    async def restore_backup(name: str) -> dict[str, Any]:
        safe_name = Path(name).name
        source = settings.backups_dir / safe_name
        if not source.is_file():
            raise HTTPException(404, "backup not found")
        restore_home = settings.home / "restore-preview" / uuid.uuid4().hex
        return await asyncio.to_thread(BackupService.restore, source, restore_home)

    @app.get("/api/doctor")
    async def doctor() -> dict[str, Any]:
        return doctor_report(settings, services.database, services.engines)

    web = Path(__file__).resolve().parents[1] / "web"
    app.mount("/web", StaticFiles(directory=web), name="web")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(web / "index.html", media_type="text/html")

    @app.get("/favicon.svg")
    async def favicon() -> FileResponse:
        return FileResponse(web / "favicon.svg", media_type="image/svg+xml")

    return app

from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .catalog import catalog_payload
from .config import Settings
from .db import Database
from .engines import engine_status
from .jobs import JobManager
from .schemas import ProjectCreate, RunRequest, WorkflowCreate, WorkflowGraph, WorkflowUpdate
from .security import is_loopback_host, safe_child
from .workflow import validate_graph


TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}


def error(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _safe_filename(value: str) -> str:
    name = Path(value or "upload.bin").name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name[:180] or "upload.bin"


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.load()
    cfg.ensure()
    db = Database(cfg.db_path)
    db.initialize()
    jobs = JobManager(cfg, db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        jobs.start()
        yield
        jobs.shutdown()

    app = FastAPI(
        title="CineNode",
        version=__version__,
        description="Canvas nodal local-first para cinema, mídia, automação e IA local.",
        lifespan=lifespan,
    )
    app.state.settings = cfg
    app.state.db = db
    app.state.jobs = jobs

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            payload = exc.detail
        else:
            payload = {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": payload})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Dados inválidos", "details": exc.errors()}},
        )

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        client_host = request.client.host if request.client else None
        raw_host = request.headers.get("host", "").strip()
        if raw_host.startswith("[") and "]" in raw_host:
            host_header = raw_host[1:raw_host.index("]")]
        elif raw_host.count(":") == 1:
            host_header = raw_host.rsplit(":", 1)[0]
        else:
            host_header = raw_host
        if not is_loopback_host(client_host) or (host_header and not is_loopback_host(host_header)):
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "LOCAL_ONLY", "message": "CineNode aceita apenas conexões locais."}},
            )
        return await call_next(request)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "name": "CineNode",
            "version": __version__,
            "home": str(cfg.home),
            "schema_version": 1,
            "perzon_bundled": False,
        }

    @app.get("/api/catalog")
    def catalog():
        return {"nodes": catalog_payload(), "count": len(catalog_payload())}

    @app.get("/api/engines")
    def engines():
        return {"engines": engine_status()}

    @app.get("/api/projects")
    def list_projects():
        return {"projects": db.list_projects()}

    @app.post("/api/projects", status_code=201)
    def create_project(payload: ProjectCreate):
        return db.create_project(payload.name.strip(), payload.description.strip())

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        project = db.get_project(project_id)
        if not project:
            raise error("PROJECT_NOT_FOUND", "Projeto não encontrado", 404)
        project["workflows"] = db.list_workflows(project_id)
        project["assets"] = db.list_assets(project_id=project_id)
        return project

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str):
        if not db.delete_project(project_id):
            raise error("PROJECT_NOT_FOUND", "Projeto não encontrado", 404)
        return None

    @app.get("/api/workflows")
    def list_workflows(project_id: str | None = None):
        return {"workflows": db.list_workflows(project_id)}

    @app.post("/api/workflows", status_code=201)
    def create_workflow(payload: WorkflowCreate):
        if not db.get_project(payload.project_id):
            raise error("PROJECT_NOT_FOUND", "Projeto não encontrado", 404)
        errors = validate_graph(payload.graph)
        if errors:
            raise error("INVALID_GRAPH", "; ".join(errors), 422)
        return db.create_workflow(payload.project_id, payload.name.strip(), payload.graph.model_dump(mode="json"))

    @app.post("/api/workflows/validate")
    def validate_workflow(graph: WorkflowGraph):
        errors = validate_graph(graph)
        return {"valid": not errors, "errors": errors}

    @app.get("/api/workflows/{workflow_id}")
    def get_workflow(workflow_id: str):
        workflow = db.get_workflow(workflow_id)
        if not workflow:
            raise error("WORKFLOW_NOT_FOUND", "Workflow não encontrado", 404)
        return workflow

    @app.put("/api/workflows/{workflow_id}")
    def update_workflow(workflow_id: str, payload: WorkflowUpdate):
        if payload.graph is not None:
            errors = validate_graph(payload.graph)
            if errors:
                raise error("INVALID_GRAPH", "; ".join(errors), 422)
        workflow = db.update_workflow(
            workflow_id,
            name=payload.name.strip() if payload.name is not None else None,
            graph=payload.graph.model_dump(mode="json") if payload.graph is not None else None,
        )
        if not workflow:
            raise error("WORKFLOW_NOT_FOUND", "Workflow não encontrado", 404)
        return workflow

    @app.delete("/api/workflows/{workflow_id}", status_code=204)
    def delete_workflow(workflow_id: str):
        if not db.delete_workflow(workflow_id):
            raise error("WORKFLOW_NOT_FOUND", "Workflow não encontrado", 404)
        return None

    @app.post("/api/workflows/{workflow_id}/run", status_code=202)
    def run_workflow(workflow_id: str, payload: RunRequest):
        if not db.get_workflow(workflow_id):
            raise error("WORKFLOW_NOT_FOUND", "Workflow não encontrado", 404)
        return jobs.create_and_enqueue(workflow_id, payload.inputs)

    @app.get("/api/jobs")
    def list_jobs(workflow_id: str | None = None, limit: int = Query(100, ge=1, le=500)):
        return {"jobs": db.list_jobs(workflow_id, limit)}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = db.get_job(job_id)
        if not job:
            raise error("JOB_NOT_FOUND", "Job não encontrado", 404)
        job["events"] = db.list_events(job_id, 0, 500)
        return job

    @app.post("/api/jobs/{job_id}/cancel", status_code=202)
    def cancel_job(job_id: str):
        job = db.get_job(job_id)
        if not job:
            raise error("JOB_NOT_FOUND", "Job não encontrado", 404)
        if job["status"] in TERMINAL_STATES:
            raise error("JOB_ALREADY_FINISHED", f"Job já terminou como {job['status']}", 409)
        db.request_cancel(job_id)
        db.add_event(job_id, "cancel_requested", {})
        return db.get_job(job_id)

    @app.post("/api/jobs/{job_id}/resume", status_code=202)
    def resume_job(job_id: str):
        job = db.get_job(job_id)
        if not job:
            raise error("JOB_NOT_FOUND", "Job não encontrado", 404)
        resumed = jobs.resume(job_id)
        if not resumed:
            raise error("JOB_NOT_RESUMABLE", f"Estado {job['status']} não permite retomada", 409)
        return resumed

    @app.get("/api/jobs/{job_id}/events")
    async def stream_events(job_id: str, after: int = Query(0, ge=0)):
        if not db.get_job(job_id):
            raise error("JOB_NOT_FOUND", "Job não encontrado", 404)

        async def generate() -> AsyncIterator[str]:
            cursor = after
            idle = 0
            while True:
                events = db.list_events(job_id, cursor, 500)
                if events:
                    idle = 0
                    for item in events:
                        cursor = item["id"]
                        yield "data: " + json.dumps(item, ensure_ascii=False) + "\n\n"
                else:
                    idle += 1
                    if idle % 15 == 0:
                        yield ": keepalive\n\n"
                job = db.get_job(job_id)
                if job and job["status"] in TERMINAL_STATES and not events:
                    break
                await asyncio.sleep(0.25)

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/api/assets/upload", status_code=201)
    async def upload_asset(file: UploadFile = File(...), project_id: str | None = None):
        if project_id and not db.get_project(project_id):
            raise error("PROJECT_NOT_FOUND", "Projeto não encontrado", 404)
        original_name = _safe_filename(file.filename or "upload.bin")
        destination_name = f"{uuid.uuid4().hex}-{original_name}"
        destination = cfg.uploads_dir / destination_name
        digest = hashlib.sha256()
        total = 0
        try:
            with destination.open("wb") as stream:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > cfg.max_upload_bytes:
                        raise error("UPLOAD_TOO_LARGE", f"Limite: {cfg.max_upload_bytes} bytes", 413)
                    digest.update(chunk)
                    stream.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        media_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        return db.create_asset(
            project_id=project_id,
            job_id=None,
            name=original_name,
            media_type=media_type,
            relative_path=str(destination.relative_to(cfg.home)),
            bytes_count=total,
            sha256=digest.hexdigest(),
        )

    @app.get("/api/assets")
    def list_assets(project_id: str | None = None, job_id: str | None = None):
        return {"assets": db.list_assets(project_id, job_id)}

    @app.get("/api/assets/{asset_id}")
    def download_asset(asset_id: str):
        asset = db.get_asset(asset_id)
        if not asset:
            raise error("ASSET_NOT_FOUND", "Asset não encontrado", 404)
        try:
            path = safe_child(cfg.home, asset["relative_path"])
        except ValueError as exc:
            raise error("ASSET_PATH_INVALID", str(exc), 500) from exc
        if not path.is_file():
            raise error("ASSET_FILE_MISSING", "Arquivo do asset não existe no disco", 410)
        return FileResponse(path, media_type=asset["media_type"], filename=asset["name"])

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(static_dir / "index.html")

    return app

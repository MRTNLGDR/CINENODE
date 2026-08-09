from __future__ import annotations

import json
import mimetypes
import shutil
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .config import AppConfig
from .database import Database
from .schemas import ProjectCreate, ProjectUpdate, WorkflowGraph
from .util import new_id, sha256_file, utc_now


MESH_MIME_TYPES = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".obj": "model/obj", ".ply": "model/ply"}


def _default_engine_settings(config: AppConfig) -> dict[str, Any]:
    exe = ".exe" if sys.platform == "win32" else ""
    return {
        "sd_cpp": {
            "label": "stable-diffusion.cpp",
            "enabled": True,
            "binary_path": str(config.engines_dir / "stable-diffusion.cpp" / "bin" / f"sd-cli{exe}"),
            "ffmpeg_path": "ffmpeg",
            "timeout_seconds": 14400,
        },
        "wangp": {
            "label": "WanGP / Wan2GP — integração externa opcional",
            "enabled": False,
            "root_path": "",
            "python_path": "",
            "config_path": "",
            "cli_args": ["--attention", "sdpa", "--profile", "4"],
            "timeout_seconds": 14400,
        },
        "comfyui": {
            "label": "ComfyUI",
            "enabled": True,
            "base_url": "http://127.0.0.1:8188",
            "timeout_seconds": 14400,
        },
        "realesrgan": {
            "label": "Real-ESRGAN NCNN Vulkan",
            "enabled": True,
            "binary_path": str(config.engines_dir / "realesrgan-ncnn-vulkan" / f"realesrgan-ncnn-vulkan{exe}"),
            "models_path": str(config.engines_dir / "realesrgan-ncnn-vulkan" / "models"),
            "timeout_seconds": 14400,
        },
        "rife": {
            "label": "RIFE NCNN Vulkan",
            "enabled": True,
            "binary_path": str(config.engines_dir / "rife-ncnn-vulkan" / f"rife-ncnn-vulkan{exe}"),
            "models_path": str(config.engines_dir / "rife-ncnn-vulkan" / "rife-v4.6"),
            "timeout_seconds": 14400,
        },
        "ffmpeg": {
            "label": "FFmpeg",
            "enabled": True,
            "binary_path": "ffmpeg",
            "probe_path": "ffprobe",
            "timeout_seconds": 14400,
        },
        "ollama": {
            "label": "Ollama local LLM",
            "enabled": True,
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen3:8b-q4_K_M",
            "timeout_seconds": 600,
        },
        "openrouter": {
            "label": "OpenRouter — provider remoto opcional",
            "enabled": False,
            "base_url": "https://openrouter.ai/api/v1",
            "model": "",
            "api_key": "",
            "temperature": 0.45,
            "timeout_seconds": 300,
        },
        "opencode": {
            "label": "OpenCode local agent",
            "enabled": True,
            "binary_path": "opencode",
            "model": "ollama/qwen3:8b-q4_K_M",
            "timeout_seconds": 900,
        },
    }


def _default_model_profiles(config: AppConfig) -> dict[str, Any]:
    return {
        "z-image-turbo-fast": {
            "label": "Z-Image Turbo — rápido",
            "kind": "image",
            "engine": "sd_cpp",
            "ready": False,
            "diffusion_model": str(config.models_dir / "z-image-turbo" / "z_image_turbo-Q3_K.gguf"),
            "vae": str(config.models_dir / "z-image-turbo" / "z_image_vae.safetensors"),
            "llm": str(config.models_dir / "z-image-turbo" / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"),
            "defaults": {"width": 1024, "height": 1024, "steps": 8, "cfg_scale": 1.0, "sampling_method": "euler"},
        },
        "flux-fast-quantized": {
            "label": "FLUX quantizado — qualidade",
            "kind": "image",
            "engine": "sd_cpp",
            "ready": False,
            "diffusion_model": str(config.models_dir / "flux" / "flux1-schnell-Q4_K_S.gguf"),
            "vae": str(config.models_dir / "flux" / "ae.safetensors"),
            "clip_l": str(config.models_dir / "flux" / "clip_l.safetensors"),
            "t5xxl": str(config.models_dir / "flux" / "t5xxl-Q5_K_M.gguf"),
            "defaults": {"width": 1024, "height": 1024, "steps": 4, "cfg_scale": 1.0, "sampling_method": "euler"},
        },
        "wan21-t2v-1.3b-fast": {
            "label": "Wan 2.1 T2V 1.3B — rápido",
            "kind": "video",
            "engine": "sd_cpp",
            "ready": False,
            "diffusion_model": str(config.models_dir / "wan21" / "wan2.1_t2v_1.3B_fp16.safetensors"),
            "vae": str(config.models_dir / "wan21" / "wan_2.1_vae.safetensors"),
            "t5xxl": str(config.models_dir / "wan21" / "umt5-xxl-encoder-Q5_K_M.gguf"),
            "defaults": {"width": 832, "height": 480, "steps": 20, "cfg_scale": 6.0, "frames": 33, "fps": 16, "flow_shift": 3.0},
        },
        "wan22-t2v-a14b-quality": {
            "label": "Wan 2.2 T2V A14B — qualidade",
            "kind": "video",
            "engine": "sd_cpp",
            "ready": False,
            "diffusion_model": str(config.models_dir / "wan22" / "Wan2.2-T2V-A14B-LowNoise-Q5_K_M.gguf"),
            "high_noise_diffusion_model": str(config.models_dir / "wan22" / "Wan2.2-T2V-A14B-HighNoise-Q5_K_M.gguf"),
            "vae": str(config.models_dir / "wan22" / "wan_2.1_vae.safetensors"),
            "t5xxl": str(config.models_dir / "wan22" / "umt5-xxl-encoder-Q5_K_M.gguf"),
            "defaults": {"width": 832, "height": 480, "steps": 10, "high_noise_steps": 8, "cfg_scale": 3.5, "frames": 33, "fps": 16, "flow_shift": 3.0},
        },
    }


class Store:
    def __init__(self, db: Database, config: AppConfig):
        self.db = db
        self.config = config

    def initialize_defaults(self) -> None:
        defaults = {
            "app.profile": {"display_name": "Administrador local", "role": "super_admin"},
            "app.preferences": {"theme": "dark", "governance_poll_ms": 15000, "open_browser": True},
            "engines": _default_engine_settings(self.config),
            "model_profiles": _default_model_profiles(self.config),
            "runtime": {"max_parallel_gpu_jobs": 1, "max_parallel_cpu_jobs": 2, "auto_resume_interrupted_jobs": False},
        }
        for key, value in defaults.items():
            if self.get_setting(key) is None:
                self.set_setting(key, value)

    def get_setting(self, key: str) -> Any | None:
        row = self.db.query_one("SELECT value_json FROM settings WHERE key = ?", (key,))
        return self.db.load_json(row["value_json"]) if row else None

    def list_settings(self) -> dict[str, Any]:
        rows = self.db.query("SELECT key, value_json FROM settings ORDER BY key")
        return {row["key"]: self.db.load_json(row["value_json"]) for row in rows}

    def set_setting(self, key: str, value: Any) -> None:
        now = utc_now()
        self.db.execute(
            "INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
            (key, self.db.dump_json(value), now),
        )

    def list_projects(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM projects ORDER BY updated_at DESC")
        return [self._project_row(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return self._project_row(row)

    def create_project(self, payload: ProjectCreate) -> dict[str, Any]:
        project_id = new_id("prj")
        now = utc_now()
        self.db.execute(
            "INSERT INTO projects(id,name,description,graph_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (project_id, payload.name, payload.description, self.db.dump_json(payload.graph.model_dump()), now, now),
        )
        self.audit("local-super-admin", "project.created", "project", project_id, {"name": payload.name})
        return self.get_project(project_id)

    def update_project(self, project_id: str, payload: ProjectUpdate) -> dict[str, Any]:
        current = self.get_project(project_id)
        name = payload.name if payload.name is not None else current["name"]
        description = payload.description if payload.description is not None else current["description"]
        graph = payload.graph.model_dump() if payload.graph is not None else current["graph"]
        now = utc_now()
        self.db.execute(
            "UPDATE projects SET name=?, description=?, graph_json=?, updated_at=? WHERE id=?",
            (name, description, self.db.dump_json(graph), now, project_id),
        )
        self.audit("local-super-admin", "project.updated", "project", project_id, {"name": name})
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        self.get_project(project_id)
        self.db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.audit("local-super-admin", "project.deleted", "project", project_id, {})

    # ---- Snapshots de projeto -------------------------------------------------

    def create_snapshot(self, project_id: str, label: str = "", note: str = "", origin: str = "manual") -> dict[str, Any]:
        """Congela o grafo atual do projeto. É o ponto de retorno do versionamento."""
        project = self.get_project(project_id)
        graph = project["graph"] or {"version": 1, "nodes": [], "edges": [], "metadata": {}}
        snapshot_id = new_id("snp")
        now = utc_now()
        self.db.execute(
            "INSERT INTO project_snapshots(id,project_id,label,note,graph_json,node_count,edge_count,origin,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                snapshot_id, project_id, (label or f"v{self.count_snapshots(project_id) + 1}").strip()[:120],
                note.strip()[:2000], self.db.dump_json(graph),
                len(graph.get("nodes") or []), len(graph.get("edges") or []), origin, now,
            ),
        )
        self.audit("local-super-admin", "project.snapshot.created", "project", project_id, {"snapshot_id": snapshot_id})
        return self.get_snapshot(snapshot_id)

    def count_snapshots(self, project_id: str) -> int:
        return int(self.db.scalar("SELECT COUNT(*) FROM project_snapshots WHERE project_id=?", (project_id,)) or 0)

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id,project_id,label,note,node_count,edge_count,origin,created_at "
            "FROM project_snapshots WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        )
        return [dict(row) for row in rows]

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM project_snapshots WHERE id=?", (snapshot_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        row = dict(row)
        row["graph"] = self.db.load_json(row.pop("graph_json"), {})
        return row

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Restaura o grafo — guardando antes um snapshot do estado atual, para que
        restaurar nunca seja uma operação destrutiva."""
        snapshot = self.get_snapshot(snapshot_id)
        project_id = snapshot["project_id"]
        self.create_snapshot(project_id, label="antes da restauração", origin="auto-restore")
        self.db.execute(
            "UPDATE projects SET graph_json=?, updated_at=? WHERE id=?",
            (self.db.dump_json(snapshot["graph"]), utc_now(), project_id),
        )
        self.audit("local-super-admin", "project.snapshot.restored", "project", project_id, {"snapshot_id": snapshot_id})
        return self.get_project(project_id)

    def delete_snapshot(self, snapshot_id: str) -> None:
        self.get_snapshot(snapshot_id)
        self.db.execute("DELETE FROM project_snapshots WHERE id=?", (snapshot_id,))
        self.audit("local-super-admin", "project.snapshot.deleted", "snapshot", snapshot_id, {})

    def _project_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row["graph"] = self.db.load_json(row.pop("graph_json"), {"version": 1, "nodes": [], "edges": [], "metadata": {}})
        return row

    def create_job(self, project_id: str | None, graph: WorkflowGraph) -> dict[str, Any]:
        job_id = new_id("job")
        now = utc_now()
        self.db.execute(
            "INSERT INTO jobs(id,project_id,status,progress,graph_json,created_at) VALUES(?,?,?,?,?,?)",
            (job_id, project_id, "QUEUED", 0.0, self.db.dump_json(graph.model_dump()), now),
        )
        self.audit("local-super-admin", "job.queued", "job", job_id, {"project_id": project_id})
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return self._job_row(row)

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),))
        return [self._job_row(row) for row in rows]

    def _job_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row["graph"] = self.db.load_json(row.pop("graph_json"), {})
        row["result"] = self.db.load_json(row.pop("result_json"), None)
        row["cancel_requested"] = bool(row["cancel_requested"])
        return row

    def update_job(self, job_id: str, **changes: Any) -> None:
        allowed = {
            "status", "progress", "current_node_id", "result_json", "error_code",
            "error_message", "cancel_requested", "started_at", "finished_at"
        }
        invalid = set(changes) - allowed
        if invalid:
            raise ValueError(f"Invalid job fields: {sorted(invalid)}")
        if not changes:
            return
        assignments = ",".join(f"{key}=?" for key in changes)
        values = [self.db.dump_json(value) if key == "result_json" and value is not None else value for key, value in changes.items()]
        self.db.execute(f"UPDATE jobs SET {assignments} WHERE id=?", (*values, job_id))

    def request_cancel(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return job
        self.update_job(job_id, cancel_requested=1)
        return self.get_job(job_id)

    def retry_job(self, job_id: str) -> dict[str, Any]:
        old = self.get_job(job_id)
        graph = WorkflowGraph.model_validate(old["graph"])
        return self.create_job(old["project_id"], graph)

    def recover_interrupted_jobs(self) -> int:
        """Job morto por reinício vira INTERRUPTED, não FAILED.

        A diferença importa: FAILED significa "o trabalho estava errado"; INTERRUPTED
        significa "o trabalho foi cortado". Só o segundo pode ser retomado, e 9 das 23
        falhas medidas neste projeto eram do segundo tipo marcadas como o primeiro.
        """
        return self.db.execute(
            "UPDATE jobs SET status='INTERRUPTED', error_code='PROCESS_INTERRUPTED', "
            "error_message='O processo anterior parou enquanto este job rodava. "
            "Ele pode ser retomado de onde parou.', "
            "finished_at=? WHERE status='RUNNING'",
            (utc_now(),),
        )

    def list_resumable_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Jobs que podem voltar de onde pararam."""
        rows = self.db.query(
            "SELECT * FROM jobs WHERE status='INTERRUPTED' ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        )
        return [self._job_row(row) for row in rows]

    def resume_job(self, job_id: str) -> dict[str, Any]:
        """Recoloca na fila preservando o grafo e o ponto onde parou."""
        job = self.get_job(job_id)
        if job["status"] != "INTERRUPTED":
            raise HTTPException(
                status_code=409,
                detail={"code": "JOB_NAO_RETOMAVEL",
                        "message": f"O job está {job['status']}, e só INTERRUPTED retoma.",
                        "hint": "Use reexecutar para criar um job novo a partir do mesmo grafo."},
            )
        self.update_job(job_id, status="QUEUED", error_code=None, error_message=None,
                        finished_at=None, cancel_requested=0)
        self.audit("user", "job.resumed", "job", job_id,
                   {"retomado_de": job.get("current_node_id")})
        return self.get_job(job_id)

    # ---- cache de resultado por nó -------------------------------------------

    def save_node_result(self, job_id: str, node_id: str, input_hash: str,
                         result: dict[str, Any]) -> None:
        """Guarda o resultado de um nó para que a retomada não o refaça.

        A chave é o hash das entradas: mudar a configuração invalida o cache sozinho.
        """
        self.db.execute(
            "INSERT OR REPLACE INTO node_results(job_id,node_id,input_hash,result_json,created_at) "
            "VALUES(?,?,?,?,?)",
            (job_id, node_id, input_hash, self.db.dump_json(result), utc_now()),
        )

    def get_node_result(self, job_id: str, node_id: str, input_hash: str) -> dict[str, Any] | None:
        row = self.db.query_one(
            "SELECT result_json FROM node_results WHERE job_id=? AND node_id=? AND input_hash=?",
            (job_id, node_id, input_hash),
        )
        return self.db.load_json(row["result_json"], None) if row else None

    def clear_node_results(self, job_id: str) -> int:
        return self.db.execute("DELETE FROM node_results WHERE job_id=?", (job_id,))

    def add_asset(
        self,
        path: Path,
        kind: str,
        project_id: str | None = None,
        job_id: str | None = None,
        original_name: str | None = None,
        mime_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = path.resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f"Asset does not exist: {path}")
        asset_id = new_id("ast")
        # mimetypes não conhece formatos de malha; sem isso o .glb viraria octet-stream.
        guessed = mimetypes.guess_type(path.name)[0] or MESH_MIME_TYPES.get(path.suffix.lower())
        now = utc_now()
        metadata = dict(metadata or {})
        metadata.setdefault("sha256", sha256_file(path))
        self.db.execute(
            "INSERT INTO assets(id,project_id,job_id,kind,path,original_name,mime_type,size_bytes,metadata_json,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                asset_id, project_id, job_id, kind, str(path), original_name,
                mime_type or guessed or "application/octet-stream", path.stat().st_size,
                self.db.dump_json(metadata), now,
            ),
        )
        self.audit("system", "asset.created", "asset", asset_id, {"path": str(path), "kind": kind})
        return self.get_asset(asset_id)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        row["metadata"] = self.db.load_json(row.pop("metadata_json"), {})
        return row

    def list_assets(
        self,
        limit: int = 200,
        project_id: str | None = None,
        *,
        include_deleted: bool = False,
        only_deleted: bool = False,
        kind: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista a galeria com os filtros que a biblioteca precisa.

        Assets excluidos ficam fora por padrao: a exclusao e logica para nao quebrar
        o historico de jobs que os referenciam.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if only_deleted:
            clauses.append("deleted_at IS NOT NULL")
        elif not include_deleted:
            clauses.append("deleted_at IS NULL")
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if search:
            clauses.append("(original_name LIKE ? OR id LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 1000)))
        rows = self.db.query(f"SELECT * FROM assets {where} ORDER BY created_at DESC LIMIT ?", tuple(params))
        result = []
        for row in rows:
            row["metadata"] = self.db.load_json(row.pop("metadata_json"), {})
            result.append(row)
        return result

    # ---- Exclusao em duas etapas ---------------------------------------------

    def soft_delete_asset(self, asset_id: str) -> dict[str, Any]:
        """Marca como excluido sem apagar o arquivo. Reversivel."""
        self.get_asset(asset_id)
        self.db.execute("UPDATE assets SET deleted_at=? WHERE id=?", (utc_now(), asset_id))
        self.audit("local-super-admin", "asset.deleted", "asset", asset_id, {"mode": "soft"})
        return self.get_asset(asset_id)

    def restore_asset(self, asset_id: str) -> dict[str, Any]:
        self.get_asset(asset_id)
        self.db.execute("UPDATE assets SET deleted_at=NULL WHERE id=?", (asset_id,))
        self.audit("local-super-admin", "asset.restored", "asset", asset_id, {})
        return self.get_asset(asset_id)

    def purge_asset(self, asset_id: str) -> dict[str, Any]:
        """Apaga o registro e o arquivo. So aceita asset ja marcado como excluido,
        para que nenhuma exclusao definitiva aconteca em um clique so."""
        asset = self.get_asset(asset_id)
        if not asset.get("deleted_at"):
            raise HTTPException(
                status_code=409,
                detail={"code": "ASSET_NOT_MARKED", "message": "Marque o asset como excluido antes de purgar."},
            )
        path = Path(asset["path"])
        removed = False
        try:
            inside_home = path.resolve().is_relative_to(self.config.home.resolve())
        except (OSError, ValueError):
            inside_home = False
        if inside_home and path.is_file():
            path.unlink()
            removed = True
        self.db.execute("DELETE FROM asset_collection_items WHERE asset_id=?", (asset_id,))
        self.db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        self.audit("local-super-admin", "asset.purged", "asset", asset_id, {"file_removed": removed, "path": str(path)})
        return {"id": asset_id, "file_removed": removed, "outside_home": not inside_home}

    def purge_deleted_assets(self) -> dict[str, Any]:
        """Esvazia a lixeira. Devolve o que saiu e quantos bytes voltaram."""
        pending = self.list_assets(limit=1000, only_deleted=True)
        freed = 0
        purged: list[str] = []
        for asset in pending:
            freed += int(asset.get("size_bytes") or 0)
            self.purge_asset(asset["id"])
            purged.append(asset["id"])
        return {"purged": purged, "count": len(purged), "freed_bytes": freed}

    # ---- Colecoes: bibliotecas e referencias ---------------------------------

    def create_collection(self, name: str, kind: str = "library", description: str = "") -> dict[str, Any]:
        collection_id = new_id("col")
        now = utc_now()
        self.db.execute(
            "INSERT INTO asset_collections(id,name,kind,description,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (collection_id, name.strip()[:160] or "Sem nome", kind, description.strip()[:2000], now, now),
        )
        self.audit("local-super-admin", "collection.created", "collection", collection_id, {"name": name})
        return self.get_collection(collection_id)

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        row = self.db.query_one("SELECT * FROM asset_collections WHERE id=?", (collection_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Collection not found")
        row = dict(row)
        items = self.db.query(
            "SELECT a.* FROM asset_collection_items i JOIN assets a ON a.id = i.asset_id "
            "WHERE i.collection_id=? AND a.deleted_at IS NULL ORDER BY i.position, i.added_at",
            (collection_id,),
        )
        for item in items:
            item["metadata"] = self.db.load_json(item.pop("metadata_json"), {})
        row["items"] = items
        row["item_count"] = len(items)
        return row

    def list_collections(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM asset_collections ORDER BY updated_at DESC")
        result = []
        for row in rows:
            row = dict(row)
            row["item_count"] = int(self.db.scalar(
                "SELECT COUNT(*) FROM asset_collection_items i JOIN assets a ON a.id=i.asset_id "
                "WHERE i.collection_id=? AND a.deleted_at IS NULL", (row["id"],)) or 0)
            result.append(row)
        return result

    def add_to_collection(self, collection_id: str, asset_id: str) -> dict[str, Any]:
        self.get_collection(collection_id)
        self.get_asset(asset_id)
        position = int(self.db.scalar(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM asset_collection_items WHERE collection_id=?",
            (collection_id,)) or 0)
        self.db.execute(
            "INSERT INTO asset_collection_items(collection_id,asset_id,position,added_at) VALUES(?,?,?,?) "
            "ON CONFLICT(collection_id,asset_id) DO NOTHING",
            (collection_id, asset_id, position, utc_now()),
        )
        self.db.execute("UPDATE asset_collections SET updated_at=? WHERE id=?", (utc_now(), collection_id))
        return self.get_collection(collection_id)

    def remove_from_collection(self, collection_id: str, asset_id: str) -> dict[str, Any]:
        self.db.execute(
            "DELETE FROM asset_collection_items WHERE collection_id=? AND asset_id=?", (collection_id, asset_id))
        self.db.execute("UPDATE asset_collections SET updated_at=? WHERE id=?", (utc_now(), collection_id))
        return self.get_collection(collection_id)

    def delete_collection(self, collection_id: str) -> None:
        self.get_collection(collection_id)
        self.db.execute("DELETE FROM asset_collections WHERE id=?", (collection_id,))
        self.audit("local-super-admin", "collection.deleted", "collection", collection_id, {})

    def audit(self, actor: str, action: str, target_type: str | None, target_id: str | None, detail: Any) -> None:
        self.db.execute(
            "INSERT INTO audit_events(created_at,actor,action,target_type,target_id,detail_json) VALUES(?,?,?,?,?,?)",
            (utc_now(), actor, action, target_type, target_id, self.db.dump_json(detail)),
        )

    def copy_upload(self, source: Path, safe_name: str) -> Path:
        destination = self.config.uploads_dir / f"{new_id('upload')}_{safe_name}"
        shutil.copy2(source, destination)
        return destination

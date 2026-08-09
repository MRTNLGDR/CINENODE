from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import uuid

from .database import Database
from .util import now_iso


class Store:
    def __init__(self, db: Database, home: Path):
        self.db = db
        self.home = Path(home).resolve()

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        project = {"id": self._id("prj"), "name": name.strip(), "description": description.strip(), "created_at": now_iso(), "updated_at": now_iso()}
        if not project["name"]:
            raise ValueError("project name is required")
        with self.db.transaction() as con:
            con.execute("INSERT INTO projects(id,name,description,created_at,updated_at) VALUES(:id,:name,:description,:created_at,:updated_at)", project)
        self.audit("project.created", project["id"], {"name": project["name"]})
        return project

    def list_projects(self) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM projects ORDER BY updated_at DESC")]

    def create_workflow(self, project_id: str | None, name: str, definition: dict[str, Any]) -> dict[str, Any]:
        item = {"id": self._id("wf"), "project_id": project_id, "name": name.strip() or "Untitled workflow", "definition_json": json.dumps(definition, ensure_ascii=False), "revision": 1, "created_at": now_iso(), "updated_at": now_iso()}
        with self.db.transaction() as con:
            con.execute("INSERT INTO workflows(id,project_id,name,definition_json,revision,created_at,updated_at) VALUES(:id,:project_id,:name,:definition_json,:revision,:created_at,:updated_at)", item)
        self.audit("workflow.created", item["id"], {"name": item["name"]})
        return self.get_workflow(item["id"])

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM workflows WHERE id=?", (workflow_id,)).fetchone()
        if row is None:
            raise KeyError(workflow_id)
        item = dict(row)
        item["definition"] = json.loads(item.pop("definition_json"))
        return item

    def list_workflows(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM workflows"
        args: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id=?"; args = (project_id,)
        query += " ORDER BY updated_at DESC"
        with self.db.connect() as con:
            rows = [dict(row) for row in con.execute(query, args)]
        for item in rows:
            item["definition"] = json.loads(item.pop("definition_json"))
        return rows

    def update_workflow(self, workflow_id: str, definition: dict[str, Any]) -> dict[str, Any]:
        with self.db.transaction() as con:
            changed = con.execute("UPDATE workflows SET definition_json=?,revision=revision+1,updated_at=? WHERE id=?", (json.dumps(definition, ensure_ascii=False), now_iso(), workflow_id)).rowcount
        if not changed:
            raise KeyError(workflow_id)
        self.audit("workflow.updated", workflow_id, {})
        return self.get_workflow(workflow_id)

    def create_job(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = now_iso(); job_id = self._id("job")
        with self.db.transaction() as con:
            con.execute("INSERT INTO jobs(id,workflow_id,status,input_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", (job_id, workflow_id, "QUEUED", json.dumps(payload, ensure_ascii=False), now, now))
        self.audit("job.queued", job_id, {"workflow_id": workflow_id})
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        item = dict(row)
        item["input"] = json.loads(item.pop("input_json") or "{}")
        item["output"] = json.loads(item.pop("output_json")) if item.get("output_json") else None
        return item

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            ids = [row[0] for row in con.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),))]
        return [self.get_job(job_id) for job_id in ids]

    def set_job(self, job_id: str, status: str, **values: Any) -> None:
        allowed = {"output_json", "error_code", "error_message", "current_node_id", "stop_reason", "started_at", "finished_at"}
        updates: dict[str, Any] = {"status": status, "updated_at": now_iso()}
        for key, value in values.items():
            if key in allowed:
                updates[key] = json.dumps(value, ensure_ascii=False) if key == "output_json" and value is not None else value
        sql = ",".join(f"{key}=?" for key in updates)
        with self.db.transaction() as con:
            changed = con.execute(f"UPDATE jobs SET {sql} WHERE id=?", (*updates.values(), job_id)).rowcount
        if not changed:
            raise KeyError(job_id)

    def set_node_run(self, job_id: str, node_id: str, status: str, input_value: Any = None, output_value: Any = None, error_message: str | None = None) -> None:
        now = now_iso()
        with self.db.transaction() as con:
            con.execute("""INSERT INTO node_runs(job_id,node_id,status,input_json,output_json,error_message,started_at,finished_at)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_id,node_id) DO UPDATE SET status=excluded.status,input_json=excluded.input_json,output_json=excluded.output_json,error_message=excluded.error_message,finished_at=excluded.finished_at""", (job_id,node_id,status,json.dumps(input_value,ensure_ascii=False),json.dumps(output_value,ensure_ascii=False) if output_value is not None else None,error_message,now,now if status in {"SUCCEEDED","FAILED","CANCELLED"} else None))

    def completed_node_outputs(self, job_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            rows = con.execute("SELECT node_id,output_json FROM node_runs WHERE job_id=? AND status='SUCCEEDED'", (job_id,)).fetchall()
        return {row[0]: json.loads(row[1]) for row in rows if row[1] is not None}

    def cache_get(self, key: str) -> Any | None:
        with self.db.connect() as con:
            row = con.execute("SELECT value_json FROM node_cache WHERE cache_key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key: str, value: Any) -> None:
        with self.db.transaction() as con:
            con.execute("INSERT INTO node_cache(cache_key,value_json,created_at) VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET value_json=excluded.value_json,created_at=excluded.created_at", (key,json.dumps(value,ensure_ascii=False),now_iso()))

    def register_asset(self, source: Path, *, project_id: str | None, job_id: str | None, kind: str, original_name: str, media_type: str | None = None) -> dict[str, Any]:
        source = source.resolve()
        try:
            relative = source.relative_to(self.home).as_posix()
        except ValueError as exc:
            raise ValueError("asset must be inside CineNode home") from exc
        data = source.read_bytes(); asset_id = self._id("ast")
        item = {"id":asset_id,"project_id":project_id,"job_id":job_id,"kind":kind,"relative_path":relative,"original_name":original_name,"media_type":media_type,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"created_at":now_iso()}
        with self.db.transaction() as con:
            con.execute("INSERT INTO assets(id,project_id,job_id,kind,relative_path,original_name,media_type,bytes,sha256,created_at) VALUES(:id,:project_id,:job_id,:kind,:relative_path,:original_name,:media_type,:bytes,:sha256,:created_at)",item)
        return item

    def get_asset(self, asset_id: str) -> tuple[dict[str, Any], Path]:
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        if row is None:
            raise KeyError(asset_id)
        item=dict(row); path=(self.home/item["relative_path"]).resolve()
        if self.home not in path.parents:
            raise ValueError("invalid asset path")
        return item,path

    def public_settings(self) -> dict[str, Any]:
        with self.db.connect() as con:
            rows=con.execute("SELECT key,value_json FROM settings WHERE secret=0 ORDER BY key").fetchall()
        return {row[0]:json.loads(row[1]) for row in rows}

    def audit(self, event_type: str, subject_id: str | None, payload: dict[str, Any]) -> None:
        with self.db.transaction() as con:
            con.execute("INSERT INTO audit_events(event_type,subject_id,payload_json,created_at) VALUES(?,?,?,?)", (event_type,subject_id,json.dumps(payload,ensure_ascii=False),now_iso()))

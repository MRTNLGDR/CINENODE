from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.RLock()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self._write_lock, self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_workflows_project ON workflows(project_id);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    current_node_id TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_workflow ON jobs(workflow_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id, id);
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
                    name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_assets_job ON assets(job_id, created_at DESC);
                """
            )
            conn.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            conn.commit()

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        now = utcnow()
        project_id = new_id("prj")
        with self._write_lock, self.connection() as conn:
            conn.execute(
                "INSERT INTO projects(id,name,description,created_at,updated_at) VALUES(?,?,?,?,?)",
                (project_id, name, description, now, now),
            )
            conn.commit()
        return self.get_project(project_id) or {}

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            return self._row(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())

    def delete_project(self, project_id: str) -> bool:
        with self._write_lock, self.connection() as conn:
            cur = conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
            conn.commit()
            return cur.rowcount > 0

    def create_workflow(self, project_id: str, name: str, graph: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        workflow_id = new_id("wf")
        with self._write_lock, self.connection() as conn:
            conn.execute(
                "INSERT INTO workflows(id,project_id,name,graph_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (workflow_id, project_id, name, json.dumps(graph, ensure_ascii=False), now, now),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
            conn.commit()
        return self.get_workflow(workflow_id) or {}

    def list_workflows(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM workflows"
        args: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id=?"
            args = (project_id,)
        query += " ORDER BY updated_at DESC"
        with self.connection() as conn:
            rows = [dict(row) for row in conn.execute(query, args)]
        for row in rows:
            row["graph"] = json.loads(row.pop("graph_json"))
        return rows

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = self._row(conn.execute("SELECT * FROM workflows WHERE id=?", (workflow_id,)).fetchone())
        if row:
            row["graph"] = json.loads(row.pop("graph_json"))
        return row

    def update_workflow(self, workflow_id: str, *, name: str | None = None, graph: dict[str, Any] | None = None) -> dict[str, Any] | None:
        current = self.get_workflow(workflow_id)
        if not current:
            return None
        now = utcnow()
        next_name = name if name is not None else current["name"]
        next_graph = graph if graph is not None else current["graph"]
        with self._write_lock, self.connection() as conn:
            conn.execute(
                "UPDATE workflows SET name=?, graph_json=?, updated_at=? WHERE id=?",
                (next_name, json.dumps(next_graph, ensure_ascii=False), now, workflow_id),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, current["project_id"]))
            conn.commit()
        return self.get_workflow(workflow_id)

    def delete_workflow(self, workflow_id: str) -> bool:
        with self._write_lock, self.connection() as conn:
            cur = conn.execute("DELETE FROM workflows WHERE id=?", (workflow_id,))
            conn.commit()
            return cur.rowcount > 0

    def create_job(self, workflow_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        job_id = new_id("job")
        with self._write_lock, self.connection() as conn:
            conn.execute(
                "INSERT INTO jobs(id,workflow_id,status,input_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (job_id, workflow_id, "QUEUED", json.dumps(inputs, ensure_ascii=False), now, now),
            )
            conn.commit()
        self.add_event(job_id, "queued", {"workflow_id": workflow_id})
        return self.get_job(job_id) or {}

    def _decode_job(self, row: dict[str, Any]) -> dict[str, Any]:
        row["inputs"] = json.loads(row.pop("input_json") or "{}")
        row["result"] = json.loads(row.pop("result_json")) if row.get("result_json") else None
        row["cancel_requested"] = bool(row["cancel_requested"])
        return row

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = self._row(conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
        return self._decode_job(row) if row else None

    def list_jobs(self, workflow_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM jobs"
        args: list[Any] = []
        if workflow_id:
            query += " WHERE workflow_id=?"
            args.append(workflow_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        args.append(max(1, min(limit, 500)))
        with self.connection() as conn:
            return [self._decode_job(dict(row)) for row in conn.execute(query, args)]

    def set_job_state(self, job_id: str, status: str, *, result: Any = None, error_code: str | None = None,
                      error_message: str | None = None, current_node_id: str | None = None) -> None:
        now = utcnow()
        started = now if status == "RUNNING" else None
        finished = now if status in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"} else None
        with self._write_lock, self.connection() as conn:
            fields = ["status=?", "updated_at=?", "current_node_id=?"]
            values: list[Any] = [status, now, current_node_id]
            if started:
                fields.append("started_at=COALESCE(started_at, ?)")
                values.append(started)
            if finished:
                fields.append("finished_at=?")
                values.append(finished)
            if result is not None:
                fields.append("result_json=?")
                values.append(json.dumps(result, ensure_ascii=False, default=str))
            if error_code is not None:
                fields.append("error_code=?")
                values.append(error_code)
            if error_message is not None:
                fields.append("error_message=?")
                values.append(error_message)
            values.append(job_id)
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id=?", values)
            conn.commit()

    def request_cancel(self, job_id: str) -> bool:
        with self._write_lock, self.connection() as conn:
            cur = conn.execute("UPDATE jobs SET cancel_requested=1, updated_at=? WHERE id=?", (utcnow(), job_id))
            conn.commit()
            return cur.rowcount > 0

    def cancel_requested(self, job_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
            return bool(row and row[0])

    def mark_abandoned_interrupted(self) -> int:
        now = utcnow()
        with self._write_lock, self.connection() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status='INTERRUPTED', error_code='PROCESS_INTERRUPTED', "
                "error_message='O processo CineNode foi encerrado durante a execução.', finished_at=?, updated_at=? "
                "WHERE status='RUNNING'",
                (now, now),
            )
            conn.commit()
            return cur.rowcount

    def reset_for_resume(self, job_id: str) -> bool:
        with self._write_lock, self.connection() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status='QUEUED', cancel_requested=0, result_json=NULL, error_code=NULL, "
                "error_message=NULL, finished_at=NULL, current_node_id=NULL, updated_at=? "
                "WHERE id=? AND status IN ('INTERRUPTED','FAILED','CANCELLED')",
                (utcnow(), job_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def add_event(self, job_id: str, kind: str, payload: dict[str, Any]) -> int:
        with self._write_lock, self.connection() as conn:
            cur = conn.execute(
                "INSERT INTO job_events(job_id,kind,payload_json,created_at) VALUES(?,?,?,?)",
                (job_id, kind, json.dumps(payload, ensure_ascii=False, default=str), utcnow()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_events(self, job_id: str, after_id: int = 0, limit: int = 500) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM job_events WHERE job_id=? AND id>? ORDER BY id LIMIT ?",
                (job_id, after_id, max(1, min(limit, 2000))),
            )]
        for row in rows:
            row["payload"] = json.loads(row.pop("payload_json"))
        return rows

    def create_asset(self, *, project_id: str | None, job_id: str | None, name: str, media_type: str,
                     relative_path: str, bytes_count: int, sha256: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        asset_id = new_id("asset")
        with self._write_lock, self.connection() as conn:
            conn.execute(
                "INSERT INTO assets(id,project_id,job_id,name,media_type,relative_path,bytes,sha256,metadata_json,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (asset_id, project_id, job_id, name, media_type, relative_path, bytes_count, sha256,
                 json.dumps(metadata or {}, ensure_ascii=False), utcnow()),
            )
            conn.commit()
        return self.get_asset(asset_id) or {}

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = self._row(conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone())
        if row:
            row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
        return row

    def list_assets(self, project_id: str | None = None, job_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if project_id:
            clauses.append("project_id=?")
            args.append(project_id)
        if job_id:
            clauses.append("job_id=?")
            args.append(job_id)
        query = "SELECT * FROM assets" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at DESC"
        with self.connection() as conn:
            rows = [dict(row) for row in conn.execute(query, args)]
        for row in rows:
            row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
        return rows

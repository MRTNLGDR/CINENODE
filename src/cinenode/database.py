from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

SCHEMA_VERSION = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workflows (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, definition_json TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, workflow_id TEXT REFERENCES workflows(id) ON DELETE SET NULL,
  status TEXT NOT NULL, input_json TEXT NOT NULL DEFAULT '{}', output_json TEXT,
  error_code TEXT, error_message TEXT, current_node_id TEXT, stop_reason TEXT,
  created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS node_runs (
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE, node_id TEXT NOT NULL,
  status TEXT NOT NULL, input_json TEXT, output_json TEXT, error_message TEXT,
  started_at TEXT, finished_at TEXT, PRIMARY KEY(job_id, node_id)
);
CREATE TABLE IF NOT EXISTS node_cache (
  cache_key TEXT PRIMARY KEY, value_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL, kind TEXT NOT NULL,
  relative_path TEXT NOT NULL, original_name TEXT NOT NULL, media_type TEXT,
  bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY, value_json TEXT NOT NULL, secret INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
  subject_id TEXT, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as con:
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    con.execute(statement)
            # Non-destructive upgrades: only add missing columns, never drop a referenced table.
            self._ensure_columns(con, "jobs", {
                "workflow_id": "TEXT",
                "status": "TEXT NOT NULL DEFAULT 'QUEUED'",
                "input_json": "TEXT NOT NULL DEFAULT '{}'",
                "output_json": "TEXT",
                "error_code": "TEXT",
                "error_message": "TEXT",
                "current_node_id": "TEXT",
                "stop_reason": "TEXT",
                "created_at": "TEXT",
                "started_at": "TEXT",
                "finished_at": "TEXT",
                "updated_at": "TEXT",
            })
            self._ensure_columns(con, "assets", {
                "project_id": "TEXT",
                "job_id": "TEXT",
                "kind": "TEXT NOT NULL DEFAULT 'asset'",
                "relative_path": "TEXT",
                "original_name": "TEXT NOT NULL DEFAULT 'asset'",
                "media_type": "TEXT",
                "bytes": "INTEGER NOT NULL DEFAULT 0",
                "sha256": "TEXT",
                "created_at": "TEXT",
            })
            con.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_assets_job ON assets(job_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id)")
            broken = con.execute("PRAGMA foreign_key_check").fetchall()
            if broken:
                raise RuntimeError(f"foreign key check failed: {broken}")

    @staticmethod
    def _ensure_columns(con: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        for name, declaration in columns.items():
            if name not in existing:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def integrity_report(self) -> dict[str, object]:
        with self.connect() as con:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            foreign = [dict(row) for row in con.execute("PRAGMA foreign_key_check")]
            version = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return {"ok": integrity == "ok" and not foreign, "integrity": integrity, "foreign_key_errors": foreign, "schema_version": int(version[0]) if version else 0}

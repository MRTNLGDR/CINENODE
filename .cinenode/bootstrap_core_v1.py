from __future__ import annotations

from pathlib import Path
import json
import shutil
import textwrap

ROOT = Path(__file__).resolve().parents[1]
VERIFIED = ROOT / "docs" / "VERIFICATION.json"

# A clean verified tree published by the development environment is always preferred.
if VERIFIED.exists() and (ROOT / "src/cinenode/api/app.py").exists():
    try:
        record = json.loads(VERIFIED.read_text(encoding="utf-8"))
    except Exception:
        record = {}
    if record.get("quality_gates_passed") is True and record.get("product") == "CineNode":
        print("A verified CineNode tree already exists; fallback bootstrap is a no-op.")
        raise SystemExit(0)

for legacy in ("backend", "frontend", "source", "codigo", "dados", "testes", "cinenode", "dist", "build"):
    path = ROOT / legacy
    if path.exists():
        shutil.rmtree(path) if path.is_dir() else path.unlink()


def write(path: str, value: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(value).lstrip("\n"), encoding="utf-8", newline="\n")


FILES: dict[str, str] = {
"pyproject.toml": r'''
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cinenode"
version = "1.0.0"
description = "Local-first modular node canvas and inference orchestration engine"
readme = "README.md"
requires-python = ">=3.11,<3.14"
license = { text = "Proprietary" }
authors = [{ name = "MRTNLGDR" }]
dependencies = [
  "fastapi>=0.115,<1",
  "httpx>=0.27,<1",
  "pydantic>=2.8,<3",
  "python-multipart>=0.0.9,<1",
  "typer>=0.12,<1",
  "uvicorn[standard]>=0.30,<1",
]

[project.optional-dependencies]
dev = [
  "build>=1.2,<2",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.24,<1",
  "pytest-cov>=5,<7",
  "ruff>=0.8,<1",
]

[project.scripts]
cinenode = "cinenode.cli:app"

[project.entry-points."cinenode.engines"]

[tool.setuptools]
package-dir = { "" = "src" }
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
include = ["cinenode*"]

[tool.setuptools.package-data]
cinenode = ["py.typed", "web/**/*", "manifests/**/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-config --strict-markers"
asyncio_mode = "auto"

[tool.coverage.run]
branch = true
source = ["cinenode"]

[tool.coverage.report]
show_missing = true
fail_under = 75

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests", "scripts"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501", "B008"]
''',
"MANIFEST.in": r'''
include README.md LICENSE SECURITY.md
recursive-include src/cinenode/web *
recursive-include src/cinenode/manifests *
include src/cinenode/py.typed
''',
"README.md": r'''
# CineNode

CineNode is a **local-first, modular node canvas and inference orchestration engine**. It is a separate product from PERZON. The repository contains the reusable workflow core, API, web canvas, durable job runner, portable backup layer, security boundary, engine adapters, plugin SDK, installers, tests and release verification.

## Run on Windows

Double-click `RUN_CINENODE.bat`. It installs Python 3.12 through `winget` when required, creates `.venv`, installs CineNode and opens `http://127.0.0.1:8765`.

## Run on Linux/macOS

```bash
chmod +x run.sh
./run.sh
```

## Manual development

```bash
python -m venv .venv
. .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
pytest --cov=cinenode
cinenode serve
```

## Local engines

CineNode discovers and controls engines through adapters. Built-in adapters cover Ollama, OpenAI-compatible local servers such as LM Studio/llama.cpp, ComfyUI and a deterministic test engine. Model weights are never committed and each optional runtime is installed separately.

## Product boundary

The local core is complete for projects, workflows, typed nodes, jobs, cache, audit, assets, backup/restore, plugins and local inference adapters. GPU/model quality depends on the installed runtime and hardware. Hosted billing, organization SSO and tenant administration are extension modules rather than falsely simulated features.

See `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md` and `docs/VERIFICATION.md`.
''',
"LICENSE": r'''
Copyright (c) MRTNLGDR. All rights reserved.

This repository is proprietary unless a file or third-party dependency states otherwise. No model weights or third-party source code are redistributed by this repository.
''',
"SECURITY.md": r'''
# Security

CineNode binds to loopback by default. LAN/server mode requires an explicit authentication token. Secrets are never returned by public settings endpoints. Engine URLs are restricted to loopback by default; private-network destinations require explicit configuration. Uploads and downloads are streamed with size limits, archives are checked for path traversal, and model downloads may require an expected SHA-256.

Report vulnerabilities privately to the repository owner. Do not include tokens, biometric data, model weights or user databases in issues.
''',
".gitignore": r'''
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.coverage
coverage.json
htmlcov/
dist/
build/
*.egg-info/
.env
runtime/
data/
models/
outputs/
uploads/
backups/
*.db
*.sqlite*
*.token
*.pem
*.key
*.pt
*.pth
*.ckpt
*.safetensors
*.onnx
*.gguf
.DS_Store
Thumbs.db
''',
".env.example": r'''
CINENODE_HOST=127.0.0.1
CINENODE_PORT=8765
CINENODE_MODE=local
CINENODE_HOME=./runtime
# Required when CINENODE_MODE=server or when binding outside loopback.
CINENODE_AUTH_TOKEN=
CINENODE_MAX_UPLOAD_BYTES=536870912
CINENODE_ALLOW_PRIVATE_ENGINE_URLS=0
''',
"src/cinenode/__init__.py": r'''
"""CineNode public package API. Importing it has no filesystem side effects."""

from .config import Settings

__all__ = ["Settings", "__version__"]
__version__ = "1.0.0"
''',
"src/cinenode/__main__.py": r'''
from .cli import app

if __name__ == "__main__":
    app()
''',
"src/cinenode/py.typed": "",
"src/cinenode/config.py": r'''
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import secrets


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    home: Path = field(default_factory=lambda: Path(os.getenv("CINENODE_HOME", "runtime")).expanduser().resolve())
    host: str = field(default_factory=lambda: os.getenv("CINENODE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("CINENODE_PORT", "8765")))
    mode: str = field(default_factory=lambda: os.getenv("CINENODE_MODE", "local").lower())
    auth_token: str = field(default_factory=lambda: os.getenv("CINENODE_AUTH_TOKEN", ""))
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("CINENODE_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024))))
    allow_private_engine_urls: bool = field(default_factory=lambda: _bool("CINENODE_ALLOW_PRIVATE_ENGINE_URLS"))
    test_mode: bool = field(default_factory=lambda: _bool("CINENODE_TEST_MODE"))

    def validate(self) -> None:
        if self.mode not in {"local", "server"}:
            raise ValueError("CINENODE_MODE must be local or server")
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535")
        if self.max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive")
        loopback = self.host in {"127.0.0.1", "localhost", "::1"}
        if (self.mode == "server" or not loopback) and len(self.auth_token) < 24:
            raise ValueError("server/LAN mode requires CINENODE_AUTH_TOKEN with at least 24 characters")

    def prepare(self) -> None:
        self.validate()
        for path in (self.home, self.data_dir, self.assets_dir, self.backups_dir, self.models_dir, self.plugins_dir):
            path.mkdir(parents=True, exist_ok=True)
        if self.mode == "local" and not self.auth_token:
            token_file = self.home / "local.token"
            if token_file.exists():
                self.auth_token = token_file.read_text(encoding="utf-8").strip()
            else:
                self.auth_token = secrets.token_urlsafe(32)
                token_file.write_text(self.auth_token, encoding="utf-8")
                try:
                    token_file.chmod(0o600)
                except OSError:
                    pass

    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "cinenode.sqlite3"

    @property
    def assets_dir(self) -> Path:
        return self.home / "assets"

    @property
    def backups_dir(self) -> Path:
        return self.home / "backups"

    @property
    def models_dir(self) -> Path:
        return self.home / "models"

    @property
    def plugins_dir(self) -> Path:
        return self.home / "plugins"

    def public_dict(self) -> dict[str, object]:
        return {
            "home": str(self.home),
            "host": self.host,
            "port": self.port,
            "mode": self.mode,
            "max_upload_bytes": self.max_upload_bytes,
            "allow_private_engine_urls": self.allow_private_engine_urls,
            "auth_configured": bool(self.auth_token),
        }
''',
"src/cinenode/database.py": r'''
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
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_assets_job ON assets(job_id);
CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id);
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
                "current_node_id": "TEXT", "stop_reason": "TEXT", "updated_at": "TEXT"
            })
            self._ensure_columns(con, "assets", {
                "job_id": "TEXT", "relative_path": "TEXT", "sha256": "TEXT", "bytes": "INTEGER NOT NULL DEFAULT 0"
            })
            con.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
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
''',
"src/cinenode/store.py": r'''
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
''',
"src/cinenode/util.py": r'''
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import hashlib
import json


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()
''',
"src/cinenode/nodes.py": r'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
import asyncio
import json

NodeHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class NodeSpec:
    type: str
    category: str
    label: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ("value",)
    cacheable: bool = True
    handler: NodeHandler | None = field(default=None, compare=False, repr=False)


class NodeRegistry:
    def __init__(self) -> None:
        self._items: dict[str, NodeSpec] = {}

    def register(self, spec: NodeSpec) -> None:
        if spec.type in self._items:
            raise ValueError(f"duplicate node type: {spec.type}")
        self._items[spec.type] = spec

    def get(self, node_type: str) -> NodeSpec:
        try:
            return self._items[node_type]
        except KeyError as exc:
            raise ValueError(f"unknown node type: {node_type}") from exc

    def catalog(self) -> list[dict[str, Any]]:
        return [{"type":s.type,"category":s.category,"label":s.label,"inputs":list(s.inputs),"outputs":list(s.outputs),"cacheable":s.cacheable} for s in sorted(self._items.values(), key=lambda x:(x.category,x.label))]


async def _text(params: dict[str, Any], _: dict[str, Any]) -> str:
    return str(params.get("text", ""))

async def _constant(params: dict[str, Any], _: dict[str, Any]) -> Any:
    return params.get("value")

async def _template(params: dict[str, Any], inputs: dict[str, Any]) -> str:
    values = {key:(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else value) for key,value in inputs.items()}
    return str(params.get("template", "{input}")).format_map(_Safe(values))

async def _merge(_: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in inputs.values():
        if isinstance(value, dict):
            result.update(value)
    return result

async def _delay(params: dict[str, Any], inputs: dict[str, Any]) -> Any:
    await asyncio.sleep(max(0.0, min(float(params.get("seconds", 0)), 30.0)))
    return inputs.get("input")

async def _json_path(params: dict[str, Any], inputs: dict[str, Any]) -> Any:
    value = inputs.get("input")
    for part in str(params.get("path", "")).strip(".").split("."):
        if not part:
            continue
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value

class _Safe(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def builtin_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for spec in (
        NodeSpec("input.text","Input","Text",outputs=("text",),handler=_text),
        NodeSpec("data.constant","Data","Constant",handler=_constant),
        NodeSpec("transform.template","Transform","Template",inputs=("input",),handler=_template),
        NodeSpec("transform.json_path","Transform","JSON path",inputs=("input",),handler=_json_path),
        NodeSpec("data.merge","Data","Merge",inputs=("items",),handler=_merge),
        NodeSpec("control.delay","Control","Delay",inputs=("input",),cacheable=False,handler=_delay),
        NodeSpec("inference.chat","Inference","Chat",inputs=("prompt",),cacheable=False),
        NodeSpec("inference.comfyui","Inference","ComfyUI",inputs=("workflow",),cacheable=False),
        NodeSpec("output.text_file","Output","Text file",inputs=("input",),cacheable=False),
    ):
        registry.register(spec)
    return registry
''',
"src/cinenode/workflow.py": r'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

from .nodes import NodeRegistry
from .util import stable_hash


@dataclass(frozen=True, slots=True)
class CompiledWorkflow:
    nodes: dict[str, dict[str, Any]]
    order: tuple[str, ...]


def compile_workflow(definition: dict[str, Any], registry: NodeRegistry) -> CompiledWorkflow:
    raw_nodes = definition.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("workflow requires a non-empty nodes list")
    nodes: dict[str, dict[str, Any]] = {}
    for raw in raw_nodes:
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("type"):
            raise ValueError("each node requires id and type")
        node_id=str(raw["id"])
        if node_id in nodes:
            raise ValueError(f"duplicate node id: {node_id}")
        registry.get(str(raw["type"]))
        nodes[node_id]=raw
    indegree={node_id:0 for node_id in nodes}; outgoing={node_id:[] for node_id in nodes}
    for target,node in nodes.items():
        bindings=node.get("inputs",{}) or {}
        if not isinstance(bindings,dict):
            raise ValueError(f"inputs for {target} must be an object")
        dependencies=set()
        for binding in bindings.values():
            if isinstance(binding,dict) and "node" in binding:
                source=str(binding["node"])
                if source not in nodes:
                    raise ValueError(f"node {target} references missing node {source}")
                dependencies.add(source)
        for source in dependencies:
            outgoing[source].append(target); indegree[target]+=1
    queue=sorted(node_id for node_id,degree in indegree.items() if degree==0); order=[]
    while queue:
        current=queue.pop(0); order.append(current)
        for target in sorted(outgoing[current]):
            indegree[target]-=1
            if indegree[target]==0:
                queue.append(target); queue.sort()
    if len(order)!=len(nodes):
        raise ValueError("workflow contains a cycle")
    return CompiledWorkflow(nodes,tuple(order))


def resolve_inputs(node: dict[str, Any], outputs: dict[str, Any], job_input: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any]={}
    for name,binding in (node.get("inputs",{}) or {}).items():
        if isinstance(binding,dict) and "node" in binding:
            value=outputs[str(binding["node"])]
            path=binding.get("path")
            if path:
                for part in str(path).strip(".").split("."):
                    value=value[int(part)] if isinstance(value,list) else value[part]
            result[name]=value
        elif isinstance(binding,dict) and "job" in binding:
            result[name]=job_input.get(str(binding["job"]))
        else:
            result[name]=binding
    return result


def node_cache_key(node: dict[str, Any], inputs: dict[str, Any]) -> str:
    return stable_hash({"type":node["type"],"params":node.get("params",{}),"inputs":inputs,"revision":1})
''',
"src/cinenode/events.py": r'''
from __future__ import annotations

from collections import defaultdict
from typing import Any, AsyncIterator
import asyncio


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        for queue in tuple(self._queues.get(topic, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def subscribe(self, topic: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._queues[topic].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[topic].discard(queue)
''',
"src/cinenode/engines/base.py": r'''
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EngineInfo:
    id: str
    label: str
    capabilities: tuple[str, ...]
    local: bool = True


class EngineAdapter(ABC):
    info: EngineInfo

    @abstractmethod
    async def probe(self) -> dict[str, Any]: ...

    async def chat(self, prompt: str, params: dict[str, Any]) -> Any:
        raise NotImplementedError(f"{self.info.id} does not implement chat")

    async def run_workflow(self, workflow: dict[str, Any], params: dict[str, Any]) -> Any:
        raise NotImplementedError(f"{self.info.id} does not implement workflow execution")
''',
"src/cinenode/engines/common.py": r'''
from __future__ import annotations

from urllib.parse import urlsplit
import ipaddress
import socket


def validate_engine_url(url: str, allow_private: bool = False) -> str:
    parsed=urlsplit(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("engine URL must be plain http(s) without credentials")
    host=parsed.hostname
    if host in {"localhost","127.0.0.1","::1"}:
        return url.rstrip("/")
    addresses={item[4][0] for item in socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme=="https" else 80),type=socket.SOCK_STREAM)}
    for value in addresses:
        ip=ipaddress.ip_address(value)
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved) and not allow_private:
            raise ValueError("private-network engine URL requires explicit permission")
    return url.rstrip("/")
''',
"src/cinenode/engines/http_adapters.py": r'''
from __future__ import annotations

from typing import Any
import httpx

from .base import EngineAdapter, EngineInfo
from .common import validate_engine_url


class OllamaEngine(EngineAdapter):
    info=EngineInfo("ollama","Ollama",("chat","models"))
    def __init__(self,url: str="http://127.0.0.1:11434",allow_private: bool=False):
        self.url=validate_engine_url(url,allow_private)
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response=await client.get(f"{self.url}/api/tags"); response.raise_for_status()
            return {"ok":True,"models":response.json().get("models",[])}
        except Exception as exc:
            return {"ok":False,"error":str(exc)}
    async def chat(self,prompt: str,params: dict[str,Any])->Any:
        model=str(params.get("model",""))
        if not model: raise ValueError("Ollama model is required")
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600))) as client:
            response=await client.post(f"{self.url}/api/chat",json={"model":model,"stream":False,"messages":[{"role":"user","content":prompt}],"options":params.get("options",{})}); response.raise_for_status()
        return response.json()["message"]["content"]


class OpenAICompatibleEngine(EngineAdapter):
    info=EngineInfo("openai-compatible","OpenAI-compatible local server",("chat","models"))
    def __init__(self,url: str="http://127.0.0.1:1234/v1",api_key: str="local",allow_private: bool=False):
        self.url=validate_engine_url(url,allow_private); self.api_key=api_key
    @property
    def headers(self)->dict[str,str]: return {"Authorization":f"Bearer {self.api_key}"}
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3,headers=self.headers) as client:
                response=await client.get(f"{self.url}/models"); response.raise_for_status()
            return {"ok":True,"models":response.json().get("data",[])}
        except Exception as exc: return {"ok":False,"error":str(exc)}
    async def chat(self,prompt: str,params: dict[str,Any])->Any:
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600)),headers=self.headers) as client:
            response=await client.post(f"{self.url}/chat/completions",json={"model":params.get("model","local-model"),"messages":[{"role":"user","content":prompt}],"temperature":params.get("temperature",0.7)}); response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class ComfyUIEngine(EngineAdapter):
    info=EngineInfo("comfyui","ComfyUI",("workflow",))
    def __init__(self,url: str="http://127.0.0.1:8188",allow_private: bool=False): self.url=validate_engine_url(url,allow_private)
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response=await client.get(f"{self.url}/system_stats"); response.raise_for_status()
            return {"ok":True,"system":response.json()}
        except Exception as exc: return {"ok":False,"error":str(exc)}
    async def run_workflow(self,workflow: dict[str,Any],params: dict[str,Any])->Any:
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600))) as client:
            response=await client.post(f"{self.url}/prompt",json={"prompt":workflow,"client_id":params.get("client_id","cinenode")}); response.raise_for_status()
        return response.json()


class MockEngine(EngineAdapter):
    info=EngineInfo("mock","Deterministic test engine",("chat","workflow"))
    async def probe(self)->dict[str,Any]: return {"ok":True,"deterministic":True}
    async def chat(self,prompt: str,params: dict[str,Any])->Any: return f"mock:{prompt}"
    async def run_workflow(self,workflow: dict[str,Any],params: dict[str,Any])->Any: return {"workflow":workflow,"params":params}
''',
"src/cinenode/engines/registry.py": r'''
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

from .base import EngineAdapter
from .http_adapters import ComfyUIEngine, MockEngine, OllamaEngine, OpenAICompatibleEngine


class EngineRegistry:
    def __init__(self) -> None:
        self._items: dict[str, EngineAdapter] = {}

    def register(self, engine: EngineAdapter) -> None:
        if engine.info.id in self._items:
            raise ValueError(f"duplicate engine: {engine.info.id}")
        self._items[engine.info.id]=engine

    def get(self, engine_id: str) -> EngineAdapter:
        try: return self._items[engine_id]
        except KeyError as exc: raise ValueError(f"unknown engine: {engine_id}") from exc

    def list(self) -> list[dict[str,Any]]:
        return [{"id":e.info.id,"label":e.info.label,"capabilities":list(e.info.capabilities),"local":e.info.local} for e in self._items.values()]

    def load_entry_points(self) -> list[str]:
        loaded=[]
        for point in entry_points(group="cinenode.engines"):
            engine=point.load()()
            if not isinstance(engine,EngineAdapter):
                raise TypeError(f"entry point {point.name} is not an EngineAdapter")
            self.register(engine); loaded.append(engine.info.id)
        return loaded


def builtin_engines(*, test_mode: bool=False, allow_private: bool=False) -> EngineRegistry:
    registry=EngineRegistry()
    registry.register(OllamaEngine(allow_private=allow_private))
    registry.register(OpenAICompatibleEngine(allow_private=allow_private))
    registry.register(ComfyUIEngine(allow_private=allow_private))
    if test_mode: registry.register(MockEngine())
    try: registry.load_entry_points()
    except Exception: pass
    return registry
''',
"src/cinenode/engines/__init__.py": r'''
from .base import EngineAdapter, EngineInfo
from .registry import EngineRegistry, builtin_engines

__all__ = ["EngineAdapter", "EngineInfo", "EngineRegistry", "builtin_engines"]
''',
"src/cinenode/plugins/sdk.py": r'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cinenode.engines.base import EngineAdapter
from cinenode.nodes import NodeSpec


@dataclass(frozen=True, slots=True)
class Plugin:
    id: str
    version: str
    nodes: tuple[NodeSpec, ...] = ()
    engines: tuple[EngineAdapter, ...] = ()

PluginFactory = Callable[[], Plugin]
''',
"src/cinenode/plugins/loader.py": r'''
from __future__ import annotations

from pathlib import Path
import importlib.util
import re

from .sdk import Plugin

ID=re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


def load_plugins(directory: Path, allowlist: set[str]) -> list[Plugin]:
    directory=directory.resolve(); loaded=[]
    if not directory.exists(): return loaded
    for path in sorted(directory.glob("*.py")):
        if path.stem not in allowlist or not ID.fullmatch(path.stem): continue
        resolved=path.resolve()
        if directory not in resolved.parents: raise ValueError("plugin path escapes plugin directory")
        spec=importlib.util.spec_from_file_location(f"cinenode_user_plugin_{path.stem}",resolved)
        if spec is None or spec.loader is None: raise RuntimeError(f"cannot load plugin {path.name}")
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        factory=getattr(module,"create_plugin",None)
        if not callable(factory): raise TypeError(f"plugin {path.name} must expose create_plugin")
        plugin=factory()
        if not isinstance(plugin,Plugin) or plugin.id != path.stem: raise TypeError(f"invalid plugin contract for {path.name}")
        loaded.append(plugin)
    return loaded
''',
"src/cinenode/plugins/__init__.py": r'''
from .loader import load_plugins
from .sdk import Plugin, PluginFactory

__all__ = ["Plugin", "PluginFactory", "load_plugins"]
''',
"src/cinenode/jobs.py": r'''
from __future__ import annotations

from typing import Any
import asyncio

from .engines.registry import EngineRegistry
from .events import EventBus
from .nodes import NodeRegistry
from .store import Store
from .util import now_iso
from .workflow import compile_workflow, node_cache_key, resolve_inputs

TERMINAL={"SUCCEEDED","FAILED","CANCELLED"}


class StopRequested(Exception):
    pass


class JobService:
    def __init__(self,store: Store,nodes: NodeRegistry,engines: EngineRegistry,events: EventBus):
        self.store=store; self.nodes=nodes; self.engines=engines; self.events=events
        self.queue: asyncio.Queue[str]=asyncio.Queue(); self.worker: asyncio.Task[None] | None=None
        self.stop_reasons: dict[str,str]={}; self.active_job: str | None=None

    async def start(self) -> None:
        if self.worker is None or self.worker.done():
            self.worker=asyncio.create_task(self._loop(),name="cinenode-job-worker")
        # Jobs interrupted by a previous process are explicitly resumable.
        with self.store.db.transaction() as con:
            con.execute("UPDATE jobs SET status='INTERRUPTED',stop_reason='process-restart',updated_at=? WHERE status='RUNNING'",(now_iso(),))

    async def stop(self) -> None:
        if self.active_job:
            self.stop_reasons[self.active_job]="shutdown"
        if self.worker:
            self.worker.cancel()
            try: await self.worker
            except asyncio.CancelledError: pass
            self.worker=None
        if self.active_job:
            try: self.store.set_job(self.active_job,"INTERRUPTED",stop_reason="shutdown")
            except KeyError: pass
            self.active_job=None

    async def submit(self,workflow_id: str,payload: dict[str,Any]) -> dict[str,Any]:
        self.store.get_workflow(workflow_id)
        job=self.store.create_job(workflow_id,payload); await self.queue.put(job["id"]); return job

    async def resume(self,job_id: str) -> dict[str,Any]:
        job=self.store.get_job(job_id)
        if job["status"] not in {"INTERRUPTED","FAILED"}: raise ValueError("only interrupted or failed jobs may be resumed")
        self.store.set_job(job_id,"QUEUED",error_code=None,error_message=None,stop_reason=None)
        await self.queue.put(job_id); return self.store.get_job(job_id)

    def cancel(self,job_id: str) -> dict[str,Any]:
        job=self.store.get_job(job_id)
        if job["status"] in TERMINAL: return job
        self.stop_reasons[job_id]="user"
        if job["status"]=="QUEUED": self.store.set_job(job_id,"CANCELLED",stop_reason="user",finished_at=now_iso())
        return self.store.get_job(job_id)

    async def _loop(self) -> None:
        while True:
            job_id=await self.queue.get()
            try: await self._run(job_id)
            except asyncio.CancelledError: raise
            except Exception as exc:
                try: self.store.set_job(job_id,"FAILED",error_code="JOB_FAILED",error_message=str(exc),finished_at=now_iso())
                except KeyError: pass
            finally: self.queue.task_done()

    def _check_stop(self,job_id: str) -> None:
        if job_id in self.stop_reasons: raise StopRequested(self.stop_reasons[job_id])

    async def _run(self,job_id: str) -> None:
        job=self.store.get_job(job_id)
        if job["status"]=="CANCELLED": return
        workflow=self.store.get_workflow(job["workflow_id"]); compiled=compile_workflow(workflow["definition"],self.nodes)
        outputs=self.store.completed_node_outputs(job_id); self.active_job=job_id
        self.store.set_job(job_id,"RUNNING",started_at=job.get("started_at") or now_iso(),stop_reason=None)
        await self.events.publish(f"job:{job_id}",{"type":"job.started","job_id":job_id})
        try:
            for node_id in compiled.order:
                if node_id in outputs: continue
                self._check_stop(job_id)
                node=compiled.nodes[node_id]; spec=self.nodes.get(str(node["type"])); inputs=resolve_inputs(node,outputs,job["input"])
                self.store.set_job(job_id,"RUNNING",current_node_id=node_id)
                self.store.set_node_run(job_id,node_id,"RUNNING",inputs)
                key=node_cache_key(node,inputs); value=self.store.cache_get(key) if spec.cacheable else None
                if value is None:
                    value=await self._execute(spec.type,spec.handler,node.get("params",{}) or {},inputs)
                    self._check_stop(job_id)
                    if spec.cacheable: self.store.cache_put(key,value)
                outputs[node_id]=value; self.store.set_node_run(job_id,node_id,"SUCCEEDED",inputs,value)
                await self.events.publish(f"job:{job_id}",{"type":"node.succeeded","job_id":job_id,"node_id":node_id})
            result=outputs[compiled.order[-1]]
            self.store.set_job(job_id,"SUCCEEDED",output_json=result,current_node_id=None,finished_at=now_iso())
            await self.events.publish(f"job:{job_id}",{"type":"job.succeeded","job_id":job_id})
        except StopRequested as exc:
            reason=str(exc)
            status="CANCELLED" if reason=="user" else "INTERRUPTED"
            self.store.set_job(job_id,status,stop_reason=reason,finished_at=now_iso() if status=="CANCELLED" else None)
        finally:
            self.stop_reasons.pop(job_id,None); self.active_job=None

    async def _execute(self,node_type: str,handler: Any,params: dict[str,Any],inputs: dict[str,Any]) -> Any:
        if handler is not None: return await handler(params,inputs)
        if node_type=="inference.chat":
            return await self.engines.get(str(params.get("engine","ollama"))).chat(str(inputs.get("prompt","")),params)
        if node_type=="inference.comfyui":
            return await self.engines.get(str(params.get("engine","comfyui"))).run_workflow(inputs.get("workflow") or params.get("workflow") or {},params)
        if node_type=="output.text_file":
            name=str(params.get("name","output.txt")).replace("/","_").replace("\\","_")
            target=(self.store.home/"assets"/"outputs"/name).resolve(); target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(str(inputs.get("input","")),encoding="utf-8")
            asset=self.store.register_asset(target,project_id=None,job_id=None,kind="text",original_name=name,media_type="text/plain")
            return {"asset_id":asset["id"],"path":asset["relative_path"]}
        raise ValueError(f"node {node_type} has no executor")
''',
"src/cinenode/backup.py": r'''
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile

from .config import Settings
from .database import Database
from .util import now_iso


class BackupService:
    def __init__(self,settings: Settings,db: Database): self.settings=settings; self.db=db

    def create(self,name: str | None=None) -> Path:
        stamp=now_iso().replace(":","").replace("+00:00","Z")
        target=self.settings.backups_dir/(name or f"cinenode-{stamp}.zip")
        if target.suffix.lower() != ".zip": target=target.with_suffix(".zip")
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cinenode-backup-") as tmp:
            db_copy=Path(tmp)/"cinenode.sqlite3"
            with self.db.connect() as source, sqlite3.connect(db_copy) as destination: source.backup(destination)
            files=[("database/cinenode.sqlite3",db_copy)]
            with self.db.connect() as con:
                rows=con.execute("SELECT relative_path FROM assets").fetchall()
            for row in rows:
                path=(self.settings.home/row[0]).resolve()
                if self.settings.home not in path.parents or not path.is_file(): continue
                files.append((f"files/{row[0]}",path))
            manifest={"schema_version":1,"created_at":now_iso(),"files":[]}
            with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
                for arc,path in files:
                    data=path.read_bytes(); archive.writestr(arc,data)
                    manifest["files"].append({"path":arc,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
                archive.writestr("manifest.json",json.dumps(manifest,indent=2))
        return target

    @staticmethod
    def restore(archive_path: Path,target_home: Path) -> dict[str,Any]:
        target_home=target_home.resolve(); target_home.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            manifest=json.loads(archive.read("manifest.json"))
            members={item.filename:item for item in archive.infolist()}
            for item in manifest["files"]:
                name=item["path"]; pure=PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts or name not in members: raise ValueError("unsafe backup member")
                data=archive.read(name)
                if len(data)!=item["bytes"] or hashlib.sha256(data).hexdigest()!=item["sha256"]: raise ValueError("backup checksum mismatch")
                if name=="database/cinenode.sqlite3": destination=target_home/"data"/"cinenode.sqlite3"
                elif name.startswith("files/"): destination=target_home/name.removeprefix("files/")
                else: continue
                destination.resolve().relative_to(target_home); destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(data)
        db=Database(target_home/"data"/"cinenode.sqlite3"); db.initialize()
        return db.integrity_report()
''',
"src/cinenode/security.py": r'''
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import ipaddress

from .config import Settings

PUBLIC=("/","/health","/api/health","/favicon.svg","/web/")


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self,app: object,settings: Settings): super().__init__(app); self.settings=settings
    async def dispatch(self,request: Request,call_next: RequestResponseEndpoint)->Response:
        path=request.url.path
        public=path in {"/","/health","/api/health","/favicon.svg"} or path.startswith("/web/")
        client=request.client.host if request.client else ""
        if self.settings.mode=="local":
            try: local=ipaddress.ip_address(client).is_loopback
            except ValueError: local=client in {"localhost","testclient"}
            if not local and not self.settings.test_mode: return JSONResponse({"detail":"CineNode local mode accepts loopback clients only"},403)
        if not public and (self.settings.mode=="server" or not self.settings.test_mode):
            supplied=request.headers.get("x-cinenode-token")
            auth=request.headers.get("authorization","")
            if auth.lower().startswith("bearer "): supplied=auth[7:]
            if supplied != self.settings.auth_token: return JSONResponse({"detail":"authentication required"},401)
        response=await call_next(request)
        response.headers.setdefault("X-Content-Type-Options","nosniff")
        response.headers.setdefault("Referrer-Policy","no-referrer")
        response.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'")
        return response
''',
"src/cinenode/doctor.py": r'''
from __future__ import annotations

from typing import Any
import platform
import shutil
import sys

from .config import Settings
from .database import Database
from .engines.registry import EngineRegistry


def report(settings: Settings,db: Database,engines: EngineRegistry) -> dict[str,Any]:
    integrity=db.integrity_report()
    return {"ok":bool(integrity["ok"]),"version":"1.0.0","python":sys.version.split()[0],"platform":platform.platform(),"home":str(settings.home),"database":integrity,"executables":{name:shutil.which(name) for name in ("git","ffmpeg","ollama","node")},"engines":engines.list()}
''',
"src/cinenode/verify.py": r'''
from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.resources
import json


def verify_distribution() -> dict[str,Any]:
    package=importlib.resources.files("cinenode")
    required=("web/index.html","web/app.js","api/app.py","engines/base.py","plugins/sdk.py")
    missing=[name for name in required if not package.joinpath(name).is_file()]
    return {"ok":not missing,"missing":missing,"required":list(required)}


def verify_source(root: Path) -> dict[str,Any]:
    required=("pyproject.toml","README.md","src/cinenode/api/app.py","src/cinenode/web/index.html","RUN_CINENODE.bat","run.sh")
    missing=[name for name in required if not (root/name).is_file()]
    prohibited=[]
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file(): continue
        low=path.relative_to(root).as_posix().lower()
        if any(low.endswith(suffix) for suffix in (".db",".sqlite",".sqlite3",".token",".pem",".key",".pt",".pth",".ckpt",".safetensors",".onnx",".gguf")): prohibited.append(low)
        if "/perzon/" in f"/{low}/": prohibited.append(low)
    return {"ok":not missing and not prohibited,"missing":missing,"prohibited":prohibited}
''',
}

for relative, value in FILES.items():
    write(relative, value)

print(f"Wrote {len(FILES)} CineNode core files")

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_home() -> Path:
    configured = os.getenv("CINENODE_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / "runtime").resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    home: Path
    host: str
    port: int
    max_upload_bytes: int
    job_workers: int

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            home=_default_home(),
            host=os.getenv("CINENODE_HOST", "127.0.0.1"),
            port=int(os.getenv("CINENODE_PORT", "8787")),
            max_upload_bytes=int(os.getenv("CINENODE_MAX_UPLOAD_BYTES", str(2 * 1024**3))),
            job_workers=max(1, int(os.getenv("CINENODE_JOB_WORKERS", "1"))),
        )

    @property
    def db_path(self) -> Path:
        return self.home / "cinenode.sqlite3"

    @property
    def uploads_dir(self) -> Path:
        return self.home / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.home / "outputs"

    @property
    def logs_dir(self) -> Path:
        return self.home / "logs"

    def ensure(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

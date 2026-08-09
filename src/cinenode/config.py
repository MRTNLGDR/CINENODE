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

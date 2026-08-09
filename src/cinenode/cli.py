from __future__ import annotations

from pathlib import Path
import json
import os
import secrets
import webbrowser

import typer
import uvicorn

from .api.app import create_app
from .config import Settings
from .database import Database
from .doctor import report as doctor_report
from .engines.registry import builtin_engines
from .verify import verify_distribution, verify_source

app = typer.Typer(no_args_is_help=True, help="CineNode local-first orchestration CLI")


@app.command()
def serve(
    host: str | None = typer.Option(None),
    port: int | None = typer.Option(None),
    mode: str | None = typer.Option(None),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
    reload: bool = False,
) -> None:
    settings = Settings()
    if host:
        settings.host = host
    if port:
        settings.port = port
    if mode:
        settings.mode = mode
    settings.prepare()
    if open_browser and settings.host in {"127.0.0.1", "localhost"}:
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{settings.host}:{settings.port}")).start()
    if reload:
        os.environ.update({"CINENODE_HOME": str(settings.home), "CINENODE_HOST": settings.host, "CINENODE_PORT": str(settings.port), "CINENODE_MODE": settings.mode})
        uvicorn.run("cinenode.api.app:create_app", factory=True, host=settings.host, port=settings.port, reload=True)
    else:
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="info")


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    settings = Settings(); settings.prepare(); db = Database(settings.database_path); db.initialize()
    result = doctor_report(settings, db, builtin_engines(test_mode=settings.test_mode, allow_private=settings.allow_private_engine_urls))
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False) if json_output else "\n".join(f"{key}: {value}" for key, value in result.items()))
    if not result["ok"]:
        raise typer.Exit(1)


@app.command()
def verify(source: Path | None = typer.Option(None)) -> None:
    result = verify_source(source.resolve()) if source else verify_distribution()
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise typer.Exit(1)


@app.command("generate-token")
def generate_token() -> None:
    typer.echo(secrets.token_urlsafe(48))

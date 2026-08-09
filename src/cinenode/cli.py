from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path


from . import __version__
from .config import Settings
from .db import Database
from .engines import engine_status


def doctor(settings: Settings) -> int:
    settings.ensure()
    db = Database(settings.db_path)
    db.initialize()
    report = {
        "name": "CineNode",
        "version": __version__,
        "home": str(settings.home),
        "database": str(settings.db_path),
        "database_exists": settings.db_path.is_file(),
        "engines": engine_status(),
        "perzon_bundled": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cinenode")
    parser.add_argument("command", nargs="?", choices=["run", "init", "doctor", "version"], default="run")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    settings = Settings.load()
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "init":
        settings.ensure()
        Database(settings.db_path).initialize()
        print(f"CineNode inicializado em {settings.home}")
        return 0
    if args.command == "doctor":
        return doctor(settings)
    host = args.host or settings.host
    port = args.port or settings.port
    if not args.no_browser:
        import threading
        import time
        def open_later():
            time.sleep(1.2)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_later, daemon=True).start()
    try:
        import uvicorn
    except ImportError as exc:
        print("uvicorn não está instalado. Execute INSTALL_CINENODE.bat ou ./install.sh.", file=sys.stderr)
        return 2
    uvicorn.run("cinenode.api:create_app", factory=True, host=host, port=port)
    return 0

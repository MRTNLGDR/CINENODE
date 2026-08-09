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

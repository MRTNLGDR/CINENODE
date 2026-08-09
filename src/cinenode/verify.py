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

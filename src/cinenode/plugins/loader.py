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

from pathlib import Path
import sys
import zipfile

wheel = Path(sys.argv[1])
required = {"cinenode/__init__.py", "cinenode/api/app.py", "cinenode/web/index.html", "cinenode/engines/base.py", "cinenode/plugins/sdk.py"}
with zipfile.ZipFile(wheel) as archive:
    names = set(archive.namelist())
missing = sorted(required - names)
if missing:
    raise SystemExit(f"wheel is incomplete: {missing}")
print(f"wheel OK: {wheel.name}; entries={len(names)}")

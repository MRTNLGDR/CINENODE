from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and verify a CineNode wheel outside its source tree")
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        raise FileNotFoundError(wheel)

    root = Path(tempfile.mkdtemp(prefix="cinenode-cleanroom-"))
    try:
        environment = root / "venv"
        runtime = root / "runtime"
        run([sys.executable, "-m", "venv", str(environment)])
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-U", "pip"])
        run([str(python), "-m", "pip", "install", str(wheel)])
        env = os.environ.copy()
        env.update({"CINENODE_HOME": str(runtime), "CINENODE_TEST_MODE": "1"})
        script = """
import json
import cinenode
from cinenode.api.app import create_app
from cinenode.verify import verify_distribution
app = create_app()
paths = {route.path for route in app.routes}
required = {'/api/health', '/api/capabilities', '/api/models', '/api/jobs', '/api/backups'}
assert app.title == 'CineNode'
assert required <= paths
assert verify_distribution()['ok'] is True
print(json.dumps({'version': cinenode.__version__, 'routes': len(paths), 'distribution': True}))
"""
        result = subprocess.run(
            [str(python), "-c", script],
            cwd=root,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        print(result.stdout.strip())
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p runtime
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(not ((3,11) <= sys.version_info[:2] < (3,14)))'; then PYTHON="$candidate"; break; fi
    fi
  done
fi
if [[ -z "$PYTHON" ]]; then
  echo "Python 3.11–3.13 não encontrado. Instale Python 3.12 e execute novamente." >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
.venv/bin/python -m pip install --disable-pip-version-check -e .
.venv/bin/python -m cinenode init
.venv/bin/python -m cinenode doctor
printf '\nCineNode instalado. Execute ./run.sh\n'

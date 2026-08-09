#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || { echo "Python 3.11 or 3.12 is required." >&2; exit 1; }
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -U pip setuptools wheel
.venv/bin/python -m pip install -e .
exec .venv/bin/python -m cinenode serve --open

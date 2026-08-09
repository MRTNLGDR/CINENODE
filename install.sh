#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -U pip setuptools wheel
.venv/bin/python -m pip install -e .
.venv/bin/python -m cinenode doctor --json

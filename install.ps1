$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
& .venv\Scripts\python.exe -m pip install --disable-pip-version-check -U pip setuptools wheel
& .venv\Scripts\python.exe -m pip install -e .
& .venv\Scripts\python.exe -m cinenode doctor --json

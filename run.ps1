$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Install Python 3.12 first." }
  winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
}
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
& .venv\Scripts\python.exe -m pip install --disable-pip-version-check -U pip setuptools wheel
& .venv\Scripts\python.exe -m pip install -e .
& .venv\Scripts\python.exe -m cinenode serve --open

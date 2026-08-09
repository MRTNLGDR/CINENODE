@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul || (
  echo Python was not found. Installing Python 3.12 with winget...
  where winget >nul 2>nul || (echo Install Python 3.12 from python.org and run this file again.& pause & exit /b 1)
  winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements || exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv || py -3 -m venv .venv || exit /b 1
call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -U pip setuptools wheel || exit /b 1
python -m pip install -e . || exit /b 1
python -m cinenode serve --open

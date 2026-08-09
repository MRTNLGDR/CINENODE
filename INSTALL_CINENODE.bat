@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul || (
  where winget >nul 2>nul || (echo Install Python 3.12 first.& pause & exit /b 1)
  winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements || exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv || py -3 -m venv .venv || exit /b 1
call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -U pip setuptools wheel || exit /b 1
python -m pip install -e . || exit /b 1
python -m cinenode doctor --json || exit /b 1
echo CineNode installation completed.
pause

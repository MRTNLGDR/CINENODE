@echo off
setlocal
cd /d "%~dp0"
title CineNode
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 (
  echo.
  echo CineNode terminou com erro. Consulte runtime\install.log.
  pause
)
endlocal

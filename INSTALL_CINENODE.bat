@echo off
setlocal
cd /d "%~dp0"
title Instalador CineNode
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 pause
endlocal

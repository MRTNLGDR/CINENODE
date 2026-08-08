@echo off
REM Sobe o sistema inteiro: CineNode, Ollama e ComfyUI, cada um so se estiver instalado.
REM Uso:  start.bat            sobe tudo que estiver disponivel
REM       start.bat --so-app   sobe apenas o CineNode
REM       start.bat --parar    derruba tudo
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start-all.ps1" %*
if errorlevel 1 pause

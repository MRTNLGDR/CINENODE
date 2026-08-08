@echo off
REM ============================================================================
REM  LIGAR  -  sobe o estudio inteiro com um clique, sem Docker.
REM
REM  Por que este arquivo existe se ja havia start.bat: digitar "start.bat" no
REM  cmd nao roda este arquivo. "start" e comando interno do cmd, e ele ganha da
REM  resolucao por extensao -- o cmd abre uma janela nova em vez de subir o app.
REM  "LIGAR" nao colide com nada.
REM
REM  Uso:  LIGAR.bat              sobe tudo e abre o navegador
REM        LIGAR.bat /so-app      sobe so o CineNode (sem Ollama, sem ComfyUI)
REM        LIGAR.bat /sem-browser sobe tudo sem abrir o navegador
REM        LIGAR.bat /desligar    derruba tudo
REM ============================================================================
setlocal
cd /d "%~dp0"
title Avangard CineNode - ligando

set "ARGS="
:parse
if "%~1"=="" goto pronto
if /i "%~1"=="/so-app"      set "ARGS=%ARGS% -SoApp"      & shift & goto parse
if /i "%~1"=="/sem-browser" set "ARGS=%ARGS% -SemNavegador" & shift & goto parse
if /i "%~1"=="/desligar"    set "ARGS=%ARGS% -Parar"      & shift & goto parse
echo [aviso] opcao desconhecida: %~1
shift
goto parse
:pronto

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start-all.ps1" %ARGS%
set "SAIDA=%ERRORLEVEL%"

if not "%SAIDA%"=="0" (
  echo.
  echo [ERRO] a subida falhou. A janela fica aberta para voce ler a causa acima.
  pause
)
endlocal & exit /b %SAIDA%

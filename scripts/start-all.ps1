param(
  [switch]$SoApp,
  [switch]$Parar,
  [switch]$SemNavegador
)
# Orquestra os três processos do estúdio em 127.0.0.1. Cada serviço é opcional:
# o que não estiver instalado é reportado com o comando que o instala, e o app
# sobe do mesmo jeito — ele degrada com erro acionável em vez de quebrar.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Runtime = Join-Path $Root ".runtime"

$Servicos = @(
  @{ Nome = "CineNode"; Porta = 8787; Saude = "http://127.0.0.1:8787/api/health" }
  @{ Nome = "Ollama";   Porta = 11434; Saude = "http://127.0.0.1:11434/api/version" }
  @{ Nome = "ComfyUI";  Porta = 8188; Saude = "http://127.0.0.1:8188/system_stats" }
)

function Test-Servico([string]$url, [int]$timeout = 3) {
  try { $null = Invoke-RestMethod $url -TimeoutSec $timeout; return $true } catch { return $false }
}

function Wait-Servico([string]$url, [int]$tentativas, [int]$intervalo = 2) {
  for ($i = 0; $i -lt $tentativas; $i++) {
    Start-Sleep -Seconds $intervalo
    if (Test-Servico $url) { return $true }
  }
  return $false
}

if ($Parar) {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*cinenode*run*' -or $_.CommandLine -like '*ComfyUI*main.py*' } |
    ForEach-Object { Write-Host "parando PID $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force }
  Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
  Write-Host "Tudo parado." -ForegroundColor Green
  return
}

# ---------- CineNode ----------
$VenvPython = Join-Path $Runtime "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  Write-Host "Instalando o nucleo local pela primeira vez..." -ForegroundColor Cyan
  & (Join-Path $PSScriptRoot "install.ps1") -SkipOpenSources
}
if (Test-Servico $Servicos[0].Saude) {
  Write-Host "CineNode ja estava no ar." -ForegroundColor DarkGray
} else {
  $env:CINENODE_HOME = Join-Path $Root "data"
  $env:CINENODE_HOST = "127.0.0.1"
  $env:CINENODE_PORT = "8787"
  Start-Process -FilePath $VenvPython -ArgumentList "-m", "cinenode", "run", "--no-browser" `
    -WorkingDirectory $Root -RedirectStandardOutput (Join-Path $Runtime "server.log") `
    -RedirectStandardError (Join-Path $Runtime "server.err.log") -WindowStyle Hidden
  if (-not (Wait-Servico $Servicos[0].Saude 20)) {
    throw "O CineNode nao respondeu. Veja $Runtime\server.err.log"
  }
}

if (-not $SoApp) {
  # ---------- Ollama: cerebro do worker ----------
  if (Test-Servico $Servicos[1].Saude) {
    Write-Host "Ollama ja estava no ar." -ForegroundColor DarkGray
  } elseif (Get-Command ollama -ErrorAction SilentlyContinue) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    if (-not (Wait-Servico $Servicos[1].Saude 15)) { Write-Warning "Ollama nao respondeu; o worker ficara indisponivel." }
  } else {
    Write-Warning "Ollama nao instalado. O chat do worker fica fora. Instale com: winget install Ollama.Ollama"
  }

  # ---------- ComfyUI: fazenda de engines (3D) ----------
  $ComfyPython = Join-Path $Runtime "comfy-venv\Scripts\python.exe"
  if (Test-Servico $Servicos[2].Saude) {
    Write-Host "ComfyUI ja estava no ar." -ForegroundColor DarkGray
  } elseif (Test-Path $ComfyPython) {
    & (Join-Path $PSScriptRoot "run-comfy.ps1") | Out-Null
    if (-not (Wait-Servico $Servicos[2].Saude 45)) { Write-Warning "ComfyUI nao respondeu; os nos 3D ficarao indisponiveis." }
  } else {
    Write-Warning "ComfyUI nao instalado. Os nos 3D ficam fora. Instale com: scripts\install-comfy.ps1"
  }
}

Write-Host ""
foreach ($servico in $Servicos) {
  $ok = Test-Servico $servico.Saude
  $cor = if ($ok) { "Green" } else { "DarkGray" }
  Write-Host ("  {0,-10} {1,-6} {2}" -f $servico.Nome, $servico.Porta, $(if ($ok) { "no ar" } else { "fora" })) -ForegroundColor $cor
}

# ---------- recursos ----------
# O gargalo medido nesta maquina nao e RAM nem CPU: e VRAM. O job mais pesado do
# projeto (video 832x480, 33 frames, RIFE + H.265) marcou 15.752 MiB de pico contra
# 16.376 MiB totais. Sobrando menos que isso, a geracao de video morre por falta de
# memoria no meio -- e o erro que aparece nao diz "faltou VRAM".
$PICO_VIDEO_MIB = 15752

Write-Host ""
try {
  $linha = (& nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits) -split "`n" | Select-Object -First 1
  $partes = $linha -split ',' | ForEach-Object { [int]$_.Trim() }
  $total = $partes[0]; $usada = $partes[1]; $livre = $total - $usada
  $cor = if ($livre -ge $PICO_VIDEO_MIB) { "Green" } else { "Yellow" }
  Write-Host ("  VRAM       {0} MiB livres de {1}" -f $livre, $total) -ForegroundColor $cor
  if ($livre -lt $PICO_VIDEO_MIB) {
    Write-Host ("  -> imagem e 3D cabem; video no maximo nao cabe (precisa de {0} MiB)." -f $PICO_VIDEO_MIB) -ForegroundColor Yellow
    Write-Host "  -> para liberar: feche o que desenha na GPU (navegador, Obsidian) ou use LIGAR.bat /so-app" -ForegroundColor DarkGray
  }
} catch { Write-Host "  VRAM       nvidia-smi indisponivel" -ForegroundColor DarkGray }

try {
  $os = Get-CimInstance Win32_OperatingSystem
  $livreGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
  $totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
  Write-Host ("  RAM        {0} GB livres de {1}" -f $livreGB, $totalGB) -ForegroundColor Green
} catch {}

# Docker nao e usado por este app e nao consome VRAM. Mede-se aqui so para nao
# atribuir a ele um peso que ele nao tem -- o custo real fica visivel no numero.
try {
  $dockerProcs = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -match '^(vmmemWSL|com\.docker|Docker Desktop|dockerd)' }
  if ($dockerProcs) {
    $dockerGB = [math]::Round((($dockerProcs | Measure-Object WS -Sum).Sum) / 1GB, 1)
    $containers = @(& docker ps -q 2>$null | Where-Object { $_ }).Count
    Write-Host ("  Docker     {0} GB de RAM, {1} containers, 0 MiB de VRAM" -f $dockerGB, $containers) -ForegroundColor DarkGray
    Write-Host "  -> nao concorre com a geracao; parar o Docker nao libera VRAM" -ForegroundColor DarkGray
  }
} catch {}

Write-Host "`n  Abra: http://127.0.0.1:8787" -ForegroundColor Cyan
if (-not $SemNavegador) { Start-Process "http://127.0.0.1:8787" }

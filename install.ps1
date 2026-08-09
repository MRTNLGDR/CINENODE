param(
  [switch]$WithEngines,
  [switch]$WithComfyUI,
  [switch]$WithOllama,
  [switch]$WithFFmpeg,
  [switch]$Repair
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
New-Item -ItemType Directory -Force -Path "$Root\runtime" | Out-Null
$Log = "$Root\runtime\install.log"
Start-Transcript -Path $Log -Append | Out-Null

function Find-Python {
  $candidates = @(
    @{Exe="py"; Args=@("-3.12")},
    @{Exe="python"; Args=@()},
    @{Exe="python3"; Args=@()}
  )
  foreach ($candidate in $candidates) {
    try {
      $version = & $candidate.Exe @($candidate.Args) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
      if ($LASTEXITCODE -eq 0 -and $version -in @("3.11","3.12","3.13")) { return $candidate }
    } catch {}
  }
  return $null
}

$Python = Find-Python
if (-not $Python) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "Python 3.11–3.13 não encontrado e winget indisponível. Instale Python 3.12 x64."
  }
  Write-Host "Instalando Python 3.12..." -ForegroundColor Cyan
  winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
  $Python = Find-Python
  if (-not $Python) { throw "Python foi instalado, mas não foi localizado. Reinicie o terminal e execute novamente." }
}

$VenvPython = "$Root\.venv\Scripts\python.exe"
if ($Repair -and (Test-Path "$Root\.venv")) { Remove-Item -Recurse -Force "$Root\.venv" }
if (-not (Test-Path $VenvPython)) {
  Write-Host "Criando ambiente virtual..." -ForegroundColor Cyan
  & $Python.Exe @($Python.Args) -m venv "$Root\.venv"
}
& $VenvPython -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
& $VenvPython -m pip install --disable-pip-version-check -e "$Root"

if ($WithEngines) { $WithFFmpeg = $true; $WithOllama = $true; $WithComfyUI = $true }
if ($WithFFmpeg -and -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Instalando FFmpeg..." -ForegroundColor Cyan
    winget install --id Gyan.FFmpeg --exact --source winget --accept-package-agreements --accept-source-agreements
  } else { Write-Warning "winget indisponível; FFmpeg não foi instalado." }
}
if ($WithOllama -and -not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Instalando Ollama..." -ForegroundColor Cyan
    winget install --id Ollama.Ollama --exact --source winget --accept-package-agreements --accept-source-agreements
  } else { Write-Warning "winget indisponível; Ollama não foi instalado." }
}
if ($WithComfyUI) {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      winget install --id Git.Git --exact --source winget --accept-package-agreements --accept-source-agreements
      $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    } else { Write-Warning "Git indisponível; ComfyUI não foi instalado." }
  }
  $Comfy = "$Root\runtime\engines\ComfyUI"
  if ((Get-Command git -ErrorAction SilentlyContinue) -and -not (Test-Path "$Comfy\.git")) {
    New-Item -ItemType Directory -Force -Path "$Root\runtime\engines" | Out-Null
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $Comfy
  }
  if (Test-Path "$Comfy\requirements.txt") {
    $ComfyPython = "$Comfy\.venv\Scripts\python.exe"
    if (-not (Test-Path $ComfyPython)) {
      & $Python.Exe @($Python.Args) -m venv "$Comfy\.venv"
    }
    & $ComfyPython -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
    & $ComfyPython -m pip install --disable-pip-version-check -r "$Comfy\requirements.txt"
  }
}
& $VenvPython -m cinenode init
& $VenvPython -m cinenode doctor
Write-Host "CineNode instalado. Execute RUN_CINENODE.bat" -ForegroundColor Green
Stop-Transcript | Out-Null

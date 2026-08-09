param(
  [switch]$Force,
  [string]$CudaChannel = ""
)
# Instala o ComfyUI como sidecar local: venv próprio, PyTorch com CUDA e um
# extra_model_paths.yaml que aponta para data/models/comfy. O ComfyUI é GPL-3.0
# e por isso NÃO é redistribuído no pacote: este script o instala na máquina do
# usuário a partir do commit pinado em Avangard One/opensources/manifest.json,
# e o CineNode conversa com ele apenas por HTTP em 127.0.0.1:8188.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Source = Join-Path $Root "Avangard One\opensources\upstream\ComfyUI"
$Runtime = Join-Path $Root ".runtime"
$Venv = Join-Path $Runtime "comfy-venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$ModelsRoot = Join-Path $Root "data\models\comfy"

if (-not (Test-Path (Join-Path $Source "main.py"))) {
  throw "ComfyUI não está no acervo. Rode scripts\bootstrap-opensources.ps1 antes: o clone precisa passar pelo gate de supply chain."
}

function Find-Python {
  foreach ($candidate in @("py -3.12", "py -3.11", "python")) {
    $parts = $candidate.Split(' '); $exe = $parts[0]; $extra = @()
    if ($parts.Length -gt 1) { $extra = $parts[1..($parts.Length - 1)] }
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
      & $exe @extra -c "import sys; assert (3,10) <= sys.version_info < (3,13)" 2>$null
      if ($LASTEXITCODE -eq 0) { return $candidate }
    }
  }
  return $null
}

if ($Force -and (Test-Path $Venv)) { Remove-Item -Recurse -Force $Venv }
if (-not (Test-Path $VenvPython)) {
  $Python = Find-Python
  if (-not $Python) { throw "O ComfyUI exige Python 3.10 a 3.12. Instale um deles e rode de novo." }
  $parts = $Python.Split(' '); $pyexe = $parts[0]; $pyargs = @()
  if ($parts.Length -gt 1) { $pyargs = $parts[1..($parts.Length - 1)] }
  & $pyexe @pyargs -m venv $Venv
}
& $VenvPython -m pip install --disable-pip-version-check --upgrade pip

# PyTorch com CUDA. Sem GPU compatível o ComfyUI cairia para CPU e o 3D ficaria inviável,
# então o canal é escolhido pelo driver e a checagem é feita de verdade no fim.
function Test-TorchCuda {
  # O probe escreve traceback no stderr quando o torch ainda não existe. Em PS 5.1,
  # stderr de processo nativo com ErrorActionPreference=Stop vira erro terminante,
  # então o preference é relaxado só aqui e a decisão sai do exit code.
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & $VenvPython -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
  } catch { return $false } finally { $ErrorActionPreference = $previous }
}

if (-not (Test-TorchCuda)) {
  $channels = if ($CudaChannel) { @($CudaChannel) } else { @("cu128", "cu126", "cu121") }
  $installed = $false
  foreach ($channel in $channels) {
    Write-Host "Instalando PyTorch ($channel)…" -ForegroundColor Cyan
    & $VenvPython -m pip install --disable-pip-version-check torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/$channel"
    if ($LASTEXITCODE -eq 0) {
      if (Test-TorchCuda) { $installed = $true; break }
      Write-Warning "$channel instalou mas não enxergou a GPU; tentando o próximo canal."
    }
  }
  if (-not $installed) { throw "Não foi possível instalar um PyTorch com CUDA funcional. Verifique o driver NVIDIA." }
}

& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $Source "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências do ComfyUI." }

# Os pesos ficam no acervo do CineNode, não dentro do clone: o upstream continua imutável.
foreach ($folder in @("checkpoints", "clip_vision", "vae", "loras", "diffusion_models", "text_encoders")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $ModelsRoot $folder) | Out-Null
}
$Yaml = @"
# Gerado por scripts/install-comfy.ps1. Mantém o clone upstream sem escrita.
cinenode:
  base_path: $ModelsRoot
  checkpoints: checkpoints
  clip_vision: clip_vision
  vae: vae
  loras: loras
  diffusion_models: diffusion_models
  text_encoders: text_encoders
"@
Set-Content -Path (Join-Path $Runtime "comfy-extra-model-paths.yaml") -Value $Yaml -Encoding UTF8

$Report = [ordered]@{
  comfy_source  = $Source
  comfy_python  = $VenvPython
  models_root   = $ModelsRoot
  torch         = (& $VenvPython -c "import torch; print(torch.__version__)")
  cuda_device   = (& $VenvPython -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')")
  launch        = "scripts\run-comfy.ps1"
}
$Report | ConvertTo-Json | Set-Content -Path (Join-Path $Runtime "comfy-install-report.json") -Encoding UTF8
$Report.GetEnumerator() | ForEach-Object { "{0,-14} {1}" -f $_.Key, $_.Value }
Write-Host "ComfyUI instalado. Suba com scripts\run-comfy.ps1" -ForegroundColor Green

param(
  [string]$ComfyHost = "127.0.0.1",
  [int]$Port = 8188,
  [switch]$Foreground
)
# Sobe o sidecar ComfyUI em 127.0.0.1. Sem --listen público: o runtime é local.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Source = Join-Path $Root "Avangard One\opensources\upstream\ComfyUI"
$Runtime = Join-Path $Root ".runtime"
$VenvPython = Join-Path $Runtime "comfy-venv\Scripts\python.exe"
$ExtraPaths = Join-Path $Runtime "comfy-extra-model-paths.yaml"

if (-not (Test-Path $VenvPython)) { throw "ComfyUI não instalado. Rode scripts\install-comfy.ps1 primeiro." }

try {
  $alive = Invoke-RestMethod "http://${ComfyHost}:$Port/system_stats" -TimeoutSec 3
  if ($alive) { Write-Host "ComfyUI já está no ar em http://${ComfyHost}:$Port" -ForegroundColor Green; return }
} catch {}

# Start-Process não cita sozinho: qualquer caminho com espaço (e a raiz tem "BASE TESTE")
# chegaria partido em dois argumentos.
function Quote([string]$value) { return '"' + $value + '"' }
$argumentList = @(
  (Quote (Join-Path $Source "main.py")),
  "--listen", $ComfyHost,
  "--port", "$Port",
  "--disable-auto-launch",
  "--output-directory", (Quote (Join-Path $Root "data\outputs\comfy"))
)
if (Test-Path $ExtraPaths) { $argumentList += @("--extra-model-paths-config", (Quote $ExtraPaths)) }
New-Item -ItemType Directory -Force -Path (Join-Path $Root "data\outputs\comfy") | Out-Null

if ($Foreground) {
  & $VenvPython @argumentList
  return
}
Start-Process -FilePath $VenvPython -ArgumentList $argumentList -WorkingDirectory $Source `
  -RedirectStandardOutput (Join-Path $Runtime "comfy.log") -RedirectStandardError (Join-Path $Runtime "comfy.err.log") -WindowStyle Hidden

for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 2
  try {
    $stats = Invoke-RestMethod "http://${ComfyHost}:$Port/system_stats" -TimeoutSec 3
    $device = $stats.devices[0]
    "ComfyUI no ar em http://${ComfyHost}:$Port"
    "device: {0} · VRAM total {1:N0} MiB" -f $device.name, ($device.vram_total / 1MB)
    return
  } catch {}
}
throw "ComfyUI não respondeu em 180s. Veja $Runtime\comfy.err.log"

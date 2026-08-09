param(
  [switch]$NoComfy,
  [switch]$Stop
)
# Sobe a pilha local — CineNode e, se os pesos 3D estiverem presentes, o sidecar ComfyUI.
#
# Os processos são criados por Win32_Process.Create (WMI) em vez de Start-Process.
# Start-Process cria um filho do console atual: quando o terminal que chamou o script
# encerra, o filho vai junto e um job de GPU longo morre no meio. O processo criado
# por WMI não tem esse vínculo e sobrevive ao fechamento do terminal.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Runtime = Join-Path $Root ".runtime"
$AppPython = Join-Path $Runtime "venv\Scripts\python.exe"
$ComfyPython = Join-Path $Runtime "comfy-venv\Scripts\python.exe"
$ComfySource = Join-Path $Root "Avangard One\opensources\upstream\ComfyUI"
$Checkpoints = Join-Path $Root "data\models\comfy\checkpoints"

function Get-StackProcesses {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -and ($_.CommandLine -like "*$Root*" -or $_.CommandLine -like "*ComfyUI*") }
}

if ($Stop) {
  $found = Get-StackProcesses
  foreach ($proc in $found) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }
  "encerrados: $($found.Count)"
  return
}

function Start-Detached([string]$exe, [string]$arguments, [string]$workDir) {
  $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = "`"$exe`" $arguments"
    CurrentDirectory = $workDir
  }
  if ($result.ReturnValue -ne 0) { throw "Win32_Process.Create falhou com código $($result.ReturnValue)" }
  return $result.ProcessId
}

function Wait-Endpoint([string]$url, [int]$seconds) {
  for ($i = 0; $i -lt $seconds; $i++) {
    try { return Invoke-RestMethod $url -TimeoutSec 3 } catch { Start-Sleep -Seconds 1 }
  }
  return $null
}

$report = [ordered]@{}

# --- CineNode -------------------------------------------------------------
if (-not (Wait-Endpoint "http://127.0.0.1:8787/api/health" 1)) {
  $env:CINENODE_HOME = Join-Path $Root "data"
  $pid1 = Start-Detached $AppPython "-m cinenode run --no-browser" $Root
  $health = Wait-Endpoint "http://127.0.0.1:8787/api/health" 90
  if (-not $health) { throw "CineNode não respondeu. Veja $Runtime\server.err.log" }
  $report["cinenode"] = "pid $pid1 · $($health.status)"
} else {
  $report["cinenode"] = "já estava no ar"
}

# --- ComfyUI (opcional) ---------------------------------------------------
$hasCheckpoint = (Test-Path $Checkpoints) -and (Get-ChildItem $Checkpoints -Filter *.safetensors -ErrorAction SilentlyContinue)
if ($NoComfy) {
  $report["comfyui"] = "pulado por -NoComfy"
} elseif (-not (Test-Path $ComfyPython)) {
  $report["comfyui"] = "não instalado (scripts\install-comfy.ps1)"
} elseif (-not $hasCheckpoint) {
  # Sem pesos o sidecar subiria só para falhar no primeiro job; melhor dizer isso agora.
  $report["comfyui"] = "sem checkpoint em data\models\comfy\checkpoints (scripts\download-models.ps1 -Bundle hunyuan3d-v2-image-to-mesh)"
} elseif (Wait-Endpoint "http://127.0.0.1:8188/system_stats" 1) {
  $report["comfyui"] = "já estava no ar"
} else {
  $comfyArgs = "`"$ComfySource\main.py`" --listen 127.0.0.1 --port 8188 --disable-auto-launch " +
               "--output-directory `"$Root\data\outputs\comfy`" " +
               "--extra-model-paths-config `"$Runtime\comfy-extra-model-paths.yaml`""
  $pid2 = Start-Detached $ComfyPython $comfyArgs $ComfySource
  $stats = Wait-Endpoint "http://127.0.0.1:8188/system_stats" 180
  $report["comfyui"] = if ($stats) { "pid $pid2 · $($stats.devices[0].name)" } else { "não respondeu; veja $Runtime\comfy.err.log" }
}

$report.GetEnumerator() | ForEach-Object { "{0,-10} {1}" -f $_.Key, $_.Value }
"interface   http://127.0.0.1:8787"

param(
  [switch]$WithEngines,
  [switch]$NoBrowser,
  [int]$Port = 8787
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$VenvPython = "$Root\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  & "$Root\install.ps1" -WithEngines:$WithEngines
}
& $VenvPython -c "import cinenode, fastapi, uvicorn"
if ($LASTEXITCODE -ne 0) {
  & "$Root\install.ps1" -WithEngines:$WithEngines -Repair
}

function Test-LocalPort([int]$PortNumber) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $task = $client.ConnectAsync("127.0.0.1", $PortNumber)
    if (-not $task.Wait(350)) { $client.Dispose(); return $false }
    $ok = $client.Connected
    $client.Dispose()
    return $ok
  } catch { return $false }
}

if ($WithEngines) {
  if ((Get-Command ollama -ErrorAction SilentlyContinue) -and -not (Test-LocalPort 11434)) {
    Start-Process -WindowStyle Minimized -FilePath "ollama" -ArgumentList "serve"
  }
  $Comfy = "$Root\runtime\engines\ComfyUI"
  $ComfyPython = "$Comfy\.venv\Scripts\python.exe"
  if ((Test-Path "$Comfy\main.py") -and (Test-Path $ComfyPython) -and -not (Test-LocalPort 8188)) {
    Start-Process -WorkingDirectory $Comfy -WindowStyle Minimized -FilePath $ComfyPython -ArgumentList @("main.py", "--listen", "127.0.0.1", "--port", "8188")
  }
}

$arguments = @("-m", "cinenode", "run", "--port", "$Port")
if ($NoBrowser) { $arguments += "--no-browser" }
& $VenvPython @arguments

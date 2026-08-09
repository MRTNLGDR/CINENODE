param(
  [switch]$SkipOpenSources,
  [switch]$InstallCoreEngines
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Runtime = Join-Path $Root ".runtime"
$Venv = Join-Path $Runtime "venv"
$Data = Join-Path $Root "data"
New-Item -ItemType Directory -Force -Path $Runtime,$Data | Out-Null

function Find-Python {
  foreach ($candidate in @("py -3.12", "py -3.11", "python", "python3")) {
    try {
      $parts=$candidate.Split(' '); $exe=$parts[0]; $args=@(); if ($parts.Length -gt 1) { $args=$parts[1..($parts.Length-1)] }
      if (Get-Command $exe -ErrorAction SilentlyContinue) {
        & $exe @args -c "import sys; assert sys.version_info >= (3,11)" 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
      }
    } catch {}
  }
  return $null
}
$Python = Find-Python
if (-not $Python) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Python 3.11+ is missing and winget is unavailable." }
  winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements
  $Python = Find-Python
  if (-not $Python) { throw "Python installation completed but executable was not found. Reopen the terminal and run install.ps1." }
}
$parts=$Python.Split(' '); $pyexe=$parts[0]; $pyargs=@(); if ($parts.Length -gt 1) {$pyargs=$parts[1..($parts.Length-1)]}

function Refresh-ProcessPath {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machine;$user"
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install --id Gyan.FFmpeg -e --scope user --accept-package-agreements --accept-source-agreements
    Refresh-ProcessPath
  } else {
    Write-Warning "FFmpeg/ffprobe are missing and winget is unavailable. The editor will open, but media post-processing will remain unavailable until FFmpeg is installed."
  }
}
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) { & $pyexe @pyargs -m venv $Venv }
$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
  & $VenvPython -m ensurepip --upgrade
  if ($LASTEXITCODE -ne 0) { throw "pip could not be initialized inside the local virtual environment." }
}

function Test-CineNodeRuntime {
  & $VenvPython -c "import fastapi,httpx,multipart,pydantic,uvicorn; print('Runtime dependencies validated')"
  return $LASTEXITCODE -eq 0
}

function Install-HostRuntimeFallback([System.IO.FileInfo]$WheelFile) {
  Write-Warning "Package index unavailable. Trying compatible packages already installed for $Python."
  $HostPathsJson = & $pyexe @pyargs -c "import json,os,sys; print(json.dumps([os.path.abspath(p) for p in sys.path if p and os.path.isdir(p) and ('site-packages' in p or 'dist-packages' in p)]))"
  if ($LASTEXITCODE -ne 0) { return $false }
  $HostPaths = @($HostPathsJson | ConvertFrom-Json)
  if ($HostPaths.Count -eq 0) { return $false }
  $VenvSite = & $VenvPython -c "import site; print(site.getsitepackages()[0])"
  if ($LASTEXITCODE -ne 0) { return $false }
  $PthPath = Join-Path $VenvSite "cinenode-host-runtime.pth"
  [System.IO.File]::WriteAllLines($PthPath, [string[]]$HostPaths, [System.Text.UTF8Encoding]::new($false))
  & $VenvPython -m pip install --disable-pip-version-check --no-deps --force-reinstall $WheelFile.FullName
  if ($LASTEXITCODE -ne 0) { return $false }
  return (Test-CineNodeRuntime)
}

$Wheel = Get-ChildItem (Join-Path $Root "installers\python\avangard_cinenode_local-*.whl") -File -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
# Numa arvore com fonte, o wheel fica velho no instante em que alguem edita um .py.
# O servidor entao serve codigo antigo e ninguem entende por que a correcao "nao pegou".
# Onde existe fonte, ela manda; o wheel so vale na maquina que so recebeu o pacote.
$FonteLocal = Join-Path $Root "source\backend\pyproject.toml"
if (Test-Path $FonteLocal) {
  Write-Host "Arvore com fonte detectada: instalando em modo editavel (fonte = runtime)."
  & $VenvPython -m pip install --disable-pip-version-check --no-build-isolation -e (Join-Path $Root "source\backend")
  if ($LASTEXITCODE -ne 0 -or -not (Test-CineNodeRuntime)) { throw "CineNode Python package installation failed." }
} elseif ($Wheel) {
  Write-Host "Installing bundled wheel: $($Wheel.Name)"
  & $VenvPython -m pip install --disable-pip-version-check --prefer-binary $Wheel.FullName
  if ($LASTEXITCODE -ne 0) {
    if (-not (Install-HostRuntimeFallback $Wheel)) {
      throw "CineNode dependencies could not be downloaded or reused from the host Python. Reconnect to a Python package index and rerun install.ps1; the installer is resumable."
    }
  } elseif (-not (Test-CineNodeRuntime)) {
    throw "CineNode installed, but a required Python runtime dependency failed to import."
  }
} else {
  Write-Host "Bundled wheel not found; installing from source."
  & $VenvPython -m pip install --disable-pip-version-check --no-build-isolation -e (Join-Path $Root "source\backend")
  if ($LASTEXITCODE -ne 0 -or -not (Test-CineNodeRuntime)) { throw "CineNode Python package installation failed." }
}
$env:CINENODE_HOME=$Data
& $VenvPython -m cinenode init
if (-not $SkipOpenSources) {
  try { & (Join-Path $Root "scripts\bootstrap-opensources.ps1") } catch { Write-Warning "Open-source synchronization failed: $($_.Exception.Message). The app remains installed; retry the bootstrap script when online." }
}
if ($InstallCoreEngines) { & (Join-Path $Root "scripts\install-engines.ps1") -Core }
$ShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) "Avangard CineNode Local.lnk"
try {
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($ShortcutPath)
  $shortcut.TargetPath = Join-Path $Root "run.bat"
  $shortcut.WorkingDirectory = $Root
  $shortcut.Description = "Avangard CineNode Local"
  $shortcut.Save()
} catch { Write-Warning "Desktop shortcut could not be created: $($_.Exception.Message)" }
Write-Host "Installation complete. Run: $Root\run.bat" -ForegroundColor Green

param(
  [switch]$SkipOpenSources,
  [switch]$InstallCoreEngines
)
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "scripts\install.ps1") -SkipOpenSources:$SkipOpenSources -InstallCoreEngines:$InstallCoreEngines

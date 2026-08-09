param(
  [string]$Mensagem = "",
  [ValidateSet("patch", "minor", "major", "none")][string]$Bump = "patch",
  [switch]$SemTestes,
  [switch]$Vigiar,
  [int]$IntervaloSegundos = 180
)
# Versionamento e commit automáticos com um portão: nada é commitado sem a suíte verde.
# Um commit automático que grava código quebrado é pior que nenhum commit automático.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function Get-Versao {
  $init = Join-Path $Root "source\backend\cinenode\__init__.py"
  $texto = Get-Content $init -Raw
  if ($texto -match '__version__\s*=\s*"([^"]+)"') { return $Matches[1] }
  throw "Não achei __version__ em $init"
}

function Set-Versao([string]$nova) {
  foreach ($alvo in @("source\backend\cinenode\__init__.py", "source\backend\pyproject.toml")) {
    $caminho = Join-Path $Root $alvo
    if (-not (Test-Path $caminho)) { continue }
    $texto = Get-Content $caminho -Raw
    $texto = $texto -replace '(__version__\s*=\s*")[^"]+(")', "`${1}$nova`${2}"
    $texto = $texto -replace '(?m)^(version\s*=\s*")[^"]+(")', "`${1}$nova`${2}"
    # -Encoding UTF8 no PS 5.1 grava BOM, e o tomllib rejeita BOM no pyproject.toml.
    # Escrever pelo .NET com UTF8Encoding($false) garante arquivo sem BOM.
    [System.IO.File]::WriteAllText($caminho, $texto, (New-Object System.Text.UTF8Encoding($false)))
  }
}

function Step-Versao([string]$atual, [string]$tipo) {
  if ($tipo -eq "none") { return $atual }
  $partes = $atual.Split('.')
  $maior = [int]$partes[0]; $menor = [int]$partes[1]; $correcao = [int]$partes[2]
  switch ($tipo) {
    "major" { $maior++; $menor = 0; $correcao = 0 }
    "minor" { $menor++; $correcao = 0 }
    "patch" { $correcao++ }
  }
  return "$maior.$menor.$correcao"
}

function Invoke-Commit {
  $sujo = git status --porcelain
  if (-not $sujo) { Write-Host "Nada mudou; nenhum commit." -ForegroundColor DarkGray; return $false }

  if (-not $SemTestes) {
    Write-Host "Rodando a suíte antes de commitar..." -ForegroundColor Cyan
    $py = Join-Path $Root ".runtime\venv\Scripts\python.exe"
    & $py -m pytest -q 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Testes falharam. Nada foi commitado — corrija antes."
      return $false
    }
    & $py (Join-Path $Root "scripts\validate_package.py") --root $Root 2>&1 | Select-Object -Last 2
    if ($LASTEXITCODE -ne 0) { Write-Warning "validate_package falhou. Nada foi commitado."; return $false }
  }

  $atual = Get-Versao
  $nova = Step-Versao $atual $Bump
  # Tag existente nunca e movida: mover marcador de historico apaga a referencia do
  # que ja foi entregue. Se a tag ja existe, sobe a versao ate achar uma livre.
  while (git tag --list "v$nova") {
    Write-Host "v$nova ja existe; subindo mais uma" -ForegroundColor DarkYellow
    $nova = Step-Versao $nova $(if ($Bump -eq 'none') { 'patch' } else { $Bump })
  }
  if ($nova -ne $atual) {
    Set-Versao $nova
    Write-Host "Versão $atual -> $nova" -ForegroundColor Green
  }

  # Mensagem derivada do que mudou: um log legível vale mais que "wip".
  if (-not $Mensagem) {
    $arquivos = (git status --porcelain | ForEach-Object { ($_ -split '\s+', 2)[1] })
    $areas = @{}
    foreach ($arquivo in $arquivos) {
      $area = switch -Wildcard ($arquivo) {
        "source/frontend/*" { "interface" }
        "source/backend/cinenode/engines/*" { "engines" }
        "source/backend/*"  { "backend" }
        "scripts/*"         { "scripts" }
        "tests/*"           { "testes" }
        "docs/*"            { "documentação" }
        "workflows/*"       { "workflows" }
        default             { "projeto" }
      }
      $areas[$area] = $true
    }
    $Mensagem = "Atualiza " + (($areas.Keys | Sort-Object) -join ", ")
  }

  git add -A
  git commit -m $Mensagem -m "Versão $nova. Suíte verde no momento do commit." | Out-Null
  if ($nova -ne $atual) {
    git tag "v$nova" | Out-Null
    Write-Host "Commit + tag v$nova" -ForegroundColor Green
  } else {
    Write-Host "Commit sem mudança de versão" -ForegroundColor Green
  }
  git log --oneline -1
  return $true
}

if ($Vigiar) {
  Write-Host "Vigiando mudanças a cada $IntervaloSegundos s. Ctrl+C para parar." -ForegroundColor Cyan
  while ($true) {
    try { Invoke-Commit | Out-Null } catch { Write-Warning $_.Exception.Message }
    Start-Sleep -Seconds $IntervaloSegundos
  }
} else {
  Invoke-Commit | Out-Null
}

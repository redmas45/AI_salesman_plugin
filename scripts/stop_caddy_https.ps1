$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot ".caddy.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
  Write-Host "No Caddy PID file found."
  exit 0
}

$rawPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
$parsedPid = 0
if ([int]::TryParse($rawPid, [ref]$parsedPid) -and $parsedPid -gt 0) {
  $proc = Get-Process -Id $parsedPid -ErrorAction SilentlyContinue
  if ($proc) {
    taskkill /PID $parsedPid /F /T | Out-Null
    Write-Host "Stopped Caddy PID $parsedPid"
  }
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

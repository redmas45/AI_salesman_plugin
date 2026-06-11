$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFiles = @(
  (Join-Path $projectRoot ".static_ip_backend.pid"),
  (Join-Path $projectRoot ".static_ip_storefront.pid")
)

foreach ($pidFile in $pidFiles) {
  if (-not (Test-Path -LiteralPath $pidFile)) {
    continue
  }

  $rawPid = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  $parsedPid = 0
  if ([int]::TryParse($rawPid, [ref]$parsedPid) -and $parsedPid -gt 0) {
    $proc = Get-Process -Id $parsedPid -ErrorAction SilentlyContinue
    if ($proc) {
      taskkill /PID $parsedPid /F /T | Out-Null
      Write-Host "Stopped PID $parsedPid"
    }
  }

  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

param(
    [string]$CrmUrl = $env:CRM_URL
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CrmUrl)) {
    $CrmUrl = "https://localhost:8484/crm"
}

Write-Host "[AI Hub] Starting Docker stack..."
docker compose up -d --build

Write-Host ""
Write-Host "============================================================"
Write-Host " AI Hub Docker is booting"
Write-Host " CRM:    $CrmUrl"
Write-Host " Widget: $($CrmUrl -replace '/crm$','')/shopbot.js?site=ai_kart_main"
Write-Host " API:    http://localhost:8585"
Write-Host "============================================================"
Write-Host ""

Write-Host "[AI Hub] Waiting for CRM at $CrmUrl"
$deadline = (Get-Date).AddMinutes(4)
$ready = $false

while ((Get-Date) -lt $deadline) {
    $result = & curl.exe -k -fsS $CrmUrl 2>$null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $ready) {
    throw "CRM did not become ready before timeout: $CrmUrl"
}

Write-Host "[AI Hub] Opening CRM: $CrmUrl"
Start-Process $CrmUrl

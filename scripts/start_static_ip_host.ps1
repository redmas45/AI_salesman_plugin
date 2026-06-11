param(
  [string]$PublicIp = "",
  [string]$SiteId = "ai_kart_main",
  [int]$StorefrontPort = 8000,
  [int]$BackendPort = 8011,
  [string]$PublicStorefrontOrigin = "",
  [string]$PublicBackendOrigin = "",
  [string]$StorefrontRoot = "C:\Users\admin\Desktop\Vercel_website",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-PublicIp {
  if ($PublicIp) {
    return $PublicIp
  }

  try {
    $result = Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 10
    return [string]$result.ip
  } catch {
    throw "Could not detect public IP. Pass -PublicIp manually."
  }
}

function Stop-PreviousProcess {
  param([string]$PidFile)

  if (-not (Test-Path -LiteralPath $PidFile)) {
    return
  }

  $rawPid = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  $parsedPid = 0
  if ([int]::TryParse($rawPid, [ref]$parsedPid) -and $parsedPid -gt 0) {
    $proc = Get-Process -Id $parsedPid -ErrorAction SilentlyContinue
    if ($proc) {
      taskkill /PID $parsedPid /F /T | Out-Null
    }
  }

  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Start-HostProcess {
  param(
    [string]$Name,
    [string]$WorkingDirectory,
    [string]$Command,
    [hashtable]$Environment,
    [string]$PidFile,
    [string]$LogFile
  )

  Stop-PreviousProcess -PidFile $PidFile

  $envLines = foreach ($entry in $Environment.GetEnumerator()) {
    "`$env:$($entry.Key) = '$($entry.Value -replace "'", "''")'"
  }

  $script = @"
Set-Location -LiteralPath '$WorkingDirectory'
$($envLines -join "`n")
$Command
"@

  if ($DryRun) {
    Write-Host "[dry-run] $Name"
    Write-Host "[dry-run] Working directory: $WorkingDirectory"
    Write-Host "[dry-run] Command: $Command"
    return
  }

  $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
  $errorLogFile = "$LogFile.err"
  $proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded `
    -WorkingDirectory $WorkingDirectory `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $errorLogFile `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -LiteralPath $PidFile -Value $proc.Id -Encoding UTF8
  Write-Host "Started $Name PID $($proc.Id). Logs: $LogFile, $errorLogFile"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$publicIpValue = Get-PublicIp

if (-not $PublicStorefrontOrigin) {
  $PublicStorefrontOrigin = "http://$publicIpValue`:$StorefrontPort"
}
if (-not $PublicBackendOrigin) {
  $PublicBackendOrigin = $PublicStorefrontOrigin
}

$localStorefrontOrigin = "http://127.0.0.1:$StorefrontPort"
$logsDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$backendPid = Join-Path $projectRoot ".static_ip_backend.pid"
$storefrontPid = Join-Path $projectRoot ".static_ip_storefront.pid"
$backendLog = Join-Path $logsDir "static_ip_backend.log"
$storefrontLog = Join-Path $logsDir "static_ip_storefront.log"

Start-HostProcess `
  -Name "AI-KART storefront" `
  -WorkingDirectory $StorefrontRoot `
  -Command "python -m uvicorn api.index:app --host 0.0.0.0 --port $StorefrontPort" `
  -Environment @{
    "LAB_INJECTION_HTML" = "<script src=`"/shopbot.js?site=$SiteId`"></script>"
    "LAB_ALLOWED_SCRIPT_ORIGINS" = $PublicStorefrontOrigin
    "SHOPBOT_BACKEND_ORIGIN" = "http://127.0.0.1:$BackendPort"
    "AI_DEFAULT_SITE_ID" = $SiteId
    "ADMIN_USERNAME" = "admin"
    "ADMIN_PASSWORD" = "admin"
  } `
  -PidFile $storefrontPid `
  -LogFile $storefrontLog

Start-Sleep -Seconds 2

Start-HostProcess `
  -Name "AI backend" `
  -WorkingDirectory $projectRoot `
  -Command "python -m uvicorn api.main:app --host 127.0.0.1 --port $BackendPort" `
  -Environment @{
    "PUBLIC_API_URL" = $PublicBackendOrigin
    "CURRENT_URL" = $localStorefrontOrigin
    "CURRENT_SITE_ID" = $SiteId
    "AI_DEFAULT_SITE_ID" = $SiteId
    "DEFAULT_SITE_ID" = $SiteId
    "CRAWL_ON_STARTUP" = "true"
  } `
  -PidFile $backendPid `
  -LogFile $backendLog

Write-Host ""
Write-Host "Storefront public URL: $PublicStorefrontOrigin"
Write-Host "Widget/API public URL: $PublicBackendOrigin"
Write-Host "Admin URL:             $PublicStorefrontOrigin/admin"
Write-Host ""
Write-Host "For real customer voice recording, use HTTPS through a domain/reverse proxy."

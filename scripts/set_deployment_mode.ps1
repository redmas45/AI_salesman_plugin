param(
  [ValidateSet("intranet", "public-ip", "domain", "custom")]
  [string]$Mode = "intranet",
  [string]$Origin = "",
  [string]$Domain = "",
  [string]$LanIp = "",
  [string]$SiteId = "",
  [int]$StorefrontPort = 8000
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

function Set-DotEnv {
  param(
    [string]$Key,
    [string]$Value
  )

  $escaped = $Value.Replace("'", "''")
  $line = "$Key='$escaped'"

  if (-not (Test-Path -LiteralPath $envFile)) {
    Set-Content -LiteralPath $envFile -Value $line -Encoding UTF8
    return
  }

  $lines = Get-Content -LiteralPath $envFile
  $updated = $false
  $newLines = foreach ($existing in $lines) {
    if ($existing -match "^\s*$([regex]::Escape($Key))=") {
      $updated = $true
      $line
    } else {
      $existing
    }
  }

  if (-not $updated) {
    $newLines += $line
  }

  Set-Content -LiteralPath $envFile -Value $newLines -Encoding UTF8
}

function Get-DotEnvValue {
  param(
    [string]$Key,
    [string]$Default = ""
  )

  if (-not (Test-Path -LiteralPath $envFile)) {
    return $Default
  }

  foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match "^\s*$([regex]::Escape($Key))=(.*)$") {
      return $Matches[1].Trim().Trim("'").Trim('"')
    }
  }

  return $Default
}

function Get-LanIp {
  if ($LanIp) {
    return $LanIp
  }

  $ip = Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Where-Object { $_ -and $_ -notlike "169.254.*" -and $_ -ne "127.0.0.1" } |
    Select-Object -First 1

  if (-not $ip) {
    throw "Could not detect LAN IP. Pass -LanIp manually."
  }

  return [string]$ip
}

function Normalize-Origin {
  param([string]$Value)

  $text = $Value.Trim().TrimEnd("/")
  if (-not $text) {
    throw "Origin cannot be empty."
  }
  if ($text -notmatch "^https?://") {
    $text = "https://$text"
  }
  return $text.TrimEnd("/")
}

function Get-PublicIp {
  try {
    $result = Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 10
    return [string]$result.ip
  } catch {
    throw "Could not detect public IP. Pass -Origin https://your-public-ip or use -Mode domain/custom."
  }
}

if (-not $SiteId) {
  $SiteId = Get-DotEnvValue -Key "CURRENT_SITE_ID" -Default "ai_kart_main"
}

switch ($Mode) {
  "intranet" {
    if (-not $Origin) {
      $Origin = "https://$(Get-LanIp)"
    }
  }
  "public-ip" {
    if (-not $Origin) {
      $Origin = "https://$(Get-PublicIp)"
    }
  }
  "domain" {
    if (-not $Origin) {
      if (-not $Domain) {
        throw "Use -Domain your-domain.com or -Origin https://your-domain.com for domain mode."
      }
      $Origin = "https://$Domain"
    }
  }
  "custom" {
    if (-not $Origin) {
      throw "Use -Origin https://your-tunnel-or-custom-host for custom mode."
    }
  }
}

$Origin = Normalize-Origin -Value $Origin

Set-DotEnv -Key "DEPLOYMENT_MODE" -Value $Mode
Set-DotEnv -Key "CURRENT_URL" -Value "http://127.0.0.1:$StorefrontPort"
Set-DotEnv -Key "PUBLIC_STOREFRONT_ORIGIN" -Value $Origin
Set-DotEnv -Key "PUBLIC_API_URL" -Value $Origin
Set-DotEnv -Key "PUBLIC_HTTPS_ORIGIN" -Value $Origin
Set-DotEnv -Key "FORCE_HTTPS" -Value "true"
Set-DotEnv -Key "MANUAL_WIDGET_SCRIPT" -Value "<script src=`"$Origin/shopbot.js?site=$SiteId`"></script>"
Set-DotEnv -Key "PUBLIC_WIDGET_SCRIPT_URL" -Value "$Origin/shopbot.js?site=$SiteId"

Write-Host "[ok] DEPLOYMENT_MODE=$Mode"
Write-Host "[ok] Browser origin: $Origin"
Write-Host "[ok] Start with: python run.py"
if ($Mode -eq "intranet") {
  Write-Host "[info] Open $Origin from devices on the same Wi-Fi/LAN."
  Write-Host "[info] Browsers may show a certificate warning because this is IP-based HTTPS."
}

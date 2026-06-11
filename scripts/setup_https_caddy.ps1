param(
  [string]$Domain = "",
  [string]$IpAddress = "",
  [string]$CaddyExe = "",
  [switch]$Start,
  [switch]$InstallWithWinget,
  [switch]$IpPoc
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
$deployDir = Join-Path $projectRoot "deploy"
$caddyFile = Join-Path $deployDir "Caddyfile"
$logsDir = Join-Path $projectRoot "logs"
$pidFile = Join-Path $projectRoot ".caddy.pid"

function Normalize-Domain {
  param([string]$Value)

  $text = $Value.Trim().ToLowerInvariant()
  $text = $text -replace "^https?://", ""
  $text = $text.TrimEnd("/")

  if ($text -match ":\d+$") {
    throw "Use a DNS name without a port, for example shop.example.com."
  }
  if ($text -match "^\d{1,3}(\.\d{1,3}){3}$") {
    throw "Trusted browser HTTPS needs a domain/subdomain, not a raw public IP."
  }
  if ($text -notmatch "^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$") {
    throw "Invalid domain name: $Value"
  }

  return $text
}

function Normalize-IpAddress {
  param([string]$Value)

  $text = $Value.Trim()
  $normalized = $text -replace "^\[|\]$", ""
  $parsed = [ipaddress]::None
  if ([ipaddress]::TryParse($normalized, [ref]$parsed)) {
    return $normalized
  }

  throw "Invalid IP address: $Value"
}

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

function Find-Caddy {
  if ($CaddyExe) {
    if (-not (Test-Path -LiteralPath $CaddyExe)) {
      throw "Caddy executable not found: $CaddyExe"
    }
    return (Resolve-Path -LiteralPath $CaddyExe).Path
  }

  $command = Get-Command caddy -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $localExe = Join-Path $projectRoot ".local\caddy\caddy.exe"
  if (Test-Path -LiteralPath $localExe) {
    return $localExe
  }

  $wingetPackageDir = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
  if (Test-Path -LiteralPath $wingetPackageDir) {
    $wingetExe = Get-ChildItem `
      -Path $wingetPackageDir `
      -Recurse `
      -Filter "caddy.exe" `
      -ErrorAction SilentlyContinue |
      Select-Object -First 1

    if ($wingetExe) {
      return $wingetExe.FullName
    }
  }

  return ""
}

function Stop-ExistingCaddy {
  if (-not (Test-Path -LiteralPath $pidFile)) {
    return
  }

  $rawPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  $parsedPid = 0
  if ([int]::TryParse($rawPid, [ref]$parsedPid) -and $parsedPid -gt 0) {
    $proc = Get-Process -Id $parsedPid -ErrorAction SilentlyContinue
    if ($proc) {
      taskkill /PID $parsedPid /F /T | Out-Null
    }
  }

  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if ($IpPoc) {
  if (-not $IpAddress) {
    $IpAddress = "103.97.243.133"
  }
  $siteAddress = Normalize-IpAddress -Value $IpAddress
  $origin = "https://$siteAddress"
} else {
  if (-not $Domain) {
    throw "Pass -Domain your-domain.com, or use -IpPoc -IpAddress 103.97.243.133 for IP-only POC HTTPS."
  }
  $siteAddress = Normalize-Domain -Value $Domain
  $origin = "https://$siteAddress"
}

$siteId = Get-DotEnvValue -Key "CURRENT_SITE_ID" -Default "ai_kart_main"

New-Item -ItemType Directory -Path $deployDir, $logsDir -Force | Out-Null

if ($IpPoc) {
  $certOutput = python (Join-Path $PSScriptRoot "generate_ip_cert.py") `
    --ip $siteAddress `
    --out-dir (Join-Path $deployDir "certs")
  $certPath = [string]($certOutput | Select-Object -First 1)
  $keyPath = [string]($certOutput | Select-Object -Skip 1 -First 1)
  $certPath = $certPath.Replace("\", "/")
  $keyPath = $keyPath.Replace("\", "/")

@"
{
	default_sni $siteAddress
}

http://:80 {
	redir https://{host}{uri} 308
}

https://:443 {
	encode gzip zstd
	tls $certPath $keyPath

	reverse_proxy 127.0.0.1:8000
}
"@ | Set-Content -LiteralPath $caddyFile -Encoding ASCII
} else {
@"
$siteAddress {
	encode gzip zstd

	reverse_proxy 127.0.0.1:8000
}
"@ | Set-Content -LiteralPath $caddyFile -Encoding ASCII
}

Set-DotEnv -Key "PUBLIC_STOREFRONT_ORIGIN" -Value $origin
Set-DotEnv -Key "PUBLIC_API_URL" -Value $origin
Set-DotEnv -Key "PUBLIC_HTTPS_ORIGIN" -Value $origin
Set-DotEnv -Key "FORCE_HTTPS" -Value "true"
Set-DotEnv -Key "MANUAL_WIDGET_SCRIPT" -Value "<script src=`"$origin/shopbot.js?site=$siteId`"></script>"
Set-DotEnv -Key "PUBLIC_WIDGET_SCRIPT_URL" -Value "$origin/shopbot.js?site=$siteId"

Write-Host "[ok] Wrote $caddyFile"
Write-Host "[ok] Updated .env public origin to $origin"
Write-Host ""
if ($IpPoc) {
  Write-Host "IP-only POC mode:"
  Write-Host "- URL: $origin"
  Write-Host "- Certificate: local self-signed cert with IP Subject Alternative Name."
  Write-Host "- Cert file: $certPath"
  Write-Host "- Router forward TCP 443 -> 192.168.68.71:443"
} else {
  Write-Host "Router/DNS requirements:"
  Write-Host "- DNS A record: $siteAddress -> 103.97.243.133"
  Write-Host "- Router forward TCP 80  -> 192.168.68.71:80"
  Write-Host "- Router forward TCP 443 -> 192.168.68.71:443"
}
Write-Host ""

if ($InstallWithWinget) {
  winget install --id CaddyServer.Caddy --accept-source-agreements --accept-package-agreements
}

$resolvedCaddy = Find-Caddy
if (-not $resolvedCaddy) {
  Write-Host "[!] Caddy executable not found."
  Write-Host "Install it with:"
  Write-Host "    winget install --id CaddyServer.Caddy --accept-source-agreements --accept-package-agreements"
  Write-Host "Or pass -CaddyExe C:\path\to\caddy.exe after manual download."
  exit 0
}

& $resolvedCaddy validate --config $caddyFile --adapter caddyfile
Write-Host "[ok] Caddyfile validated with $resolvedCaddy"

if ($Start) {
  Stop-ExistingCaddy
  $stdout = Join-Path $logsDir "caddy.log"
  $stderr = Join-Path $logsDir "caddy.err.log"
  $proc = Start-Process -FilePath $resolvedCaddy `
    -ArgumentList "run", "--config", $caddyFile, "--adapter", "caddyfile" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -LiteralPath $pidFile -Value $proc.Id -Encoding UTF8
  Write-Host "[ok] Started Caddy PID $($proc.Id)"
  Write-Host "     logs: $stdout, $stderr"
}

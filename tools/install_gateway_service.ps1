<#
.SYNOPSIS
Install the cross-PC protocol gateway as a Windows service via nssm.

.DESCRIPTION
Idempotent installer. Run from PowerShell as Administrator on the desktop
that hosts the canonical gateway (the machine reachable at 192.168.2.32:8788
from every other peer). After install, the gateway survives reboots, shell
closes, and operator log-offs -- which eliminates the recurring failure mode
documented in CHATBIBLE_FAILURE.MD ("human-must-restart-gateway", 2026-05-15
/ 2026-05-22 / 2026-05-24 -- same root cause every time).

.PARAMETER ServiceName
Windows service name. Default: cross-pc-gateway

.PARAMETER PythonExe
Full path to python.exe. Auto-detected from PATH if not specified.

.PARAMETER RepoRoot
Absolute path to the repo root. Default: the parent of this script's directory.

.PARAMETER HttpPort
HTTP port. Default: 8788

.PARAMETER WsPort
WebSocket port. Default: 8787

.PARAMETER Host
Bind address. Default: 0.0.0.0 (LAN-reachable). Do NOT use 127.0.0.1 -- other
peers cannot reach loopback from a different machine.

.PARAMETER NssmExe
Path to nssm.exe. Default: searches PATH and common install locations.
Download from https://nssm.cc if not installed.

.PARAMETER Reinstall
Remove existing service before installing. Use after editing the gateway
source if you want to force a clean restart.

.EXAMPLE
# First-time install on Windows desktop, run as Administrator:
PS> .\tools\install_gateway_service.ps1

.EXAMPLE
# Reinstall after pulling new gateway code:
PS> .\tools\install_gateway_service.ps1 -Reinstall

.NOTES
After install, manage the service with:
  nssm restart cross-pc-gateway     # apply config changes
  nssm stop    cross-pc-gateway
  nssm start   cross-pc-gateway
  nssm status  cross-pc-gateway
  Get-Service  cross-pc-gateway
  Get-EventLog -LogName Application -Source cross-pc-gateway -Newest 20

Logs are written to <RepoRoot>\logs\cross_pc_gateway\stdout.log and stderr.log.

The protocol bus is SINGLE-HOST by design -- only ONE machine should run this
service. Other peers (Linux/WSL, laptops, other workstations) should run
register_peer.py as their daemon, NOT a second gateway. See
CHATBIBLE_FAILURE.MD 2026-05-22T13:28Z correction for why a second gateway
fragments the bus.
#>

[CmdletBinding()]
param(
    [string]$ServiceName = "cross-pc-gateway",
    [string]$PythonExe = "",
    [string]$RepoRoot = "",
    [int]$HttpPort = 8788,
    [int]$WsPort = 8787,
    [string]$BindHost = "0.0.0.0",
    [string]$NssmExe = "",
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"

function Require-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run from an elevated PowerShell (Run as Administrator). nssm install requires admin rights to create a Windows service."
    }
}

function Find-Nssm {
    param([string]$Override)
    if ($Override) {
        if (Test-Path $Override) { return $Override }
        throw "nssm.exe not found at supplied path: $Override"
    }
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "C:\ProgramData\chocolatey\bin\nssm.exe",
        "C:\Program Files\nssm\nssm.exe",
        "C:\Program Files (x86)\nssm\nssm.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw "nssm.exe not found on PATH or in standard install locations. Install via 'choco install nssm' or download from https://nssm.cc/download and either add to PATH or pass -NssmExe '<full path>'."
}

function Find-Python {
    param([string]$Override)
    if ($Override) {
        if (Test-Path $Override) { return $Override }
        throw "python.exe not found at supplied path: $Override"
    }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python3.exe -ErrorAction SilentlyContinue }
    if (-not $cmd) { throw "python.exe not found on PATH. Install Python 3.11+ or pass -PythonExe '<full path>'." }
    return $cmd.Source
}

function Resolve-RepoRoot {
    param([string]$Override)
    if ($Override) {
        $resolved = (Resolve-Path $Override).Path
        if (-not (Test-Path (Join-Path $resolved "tools\protocol_gateway.py"))) {
            throw "RepoRoot $resolved does not contain tools\protocol_gateway.py"
        }
        return $resolved
    }
    $scriptDir = Split-Path -Parent $PSCommandPath
    $candidate = (Resolve-Path (Join-Path $scriptDir "..")).Path
    if (-not (Test-Path (Join-Path $candidate "tools\protocol_gateway.py"))) {
        throw "Auto-detected RepoRoot $candidate does not contain tools\protocol_gateway.py -- pass -RepoRoot '<path>'."
    }
    return $candidate
}

Require-Admin

$nssm = Find-Nssm $NssmExe
$python = Find-Python $PythonExe
$repo = Resolve-RepoRoot $RepoRoot
$gatewayScript = Join-Path $repo "tools\protocol_gateway.py"
$logDir = Join-Path $repo "logs\cross_pc_gateway"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdoutLog = Join-Path $logDir "stdout.log"
$stderrLog = Join-Path $logDir "stderr.log"

Write-Host "nssm:    $nssm"
Write-Host "python:  $python"
Write-Host "repo:    $repo"
Write-Host "script:  $gatewayScript"
Write-Host "logs:    $logDir"
Write-Host "service: $ServiceName"
Write-Host "bind:    ${BindHost}:${HttpPort} (http) / ${BindHost}:${WsPort} (ws)"
Write-Host ""

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    if (-not $Reinstall) {
        Write-Host "Service '$ServiceName' already exists. Use -Reinstall to recreate."
        Write-Host "Current status: $($existing.Status)"
        exit 0
    }
    Write-Host "Removing existing service (Reinstall requested)..."
    & $nssm stop $ServiceName confirm 2>$null | Out-Null
    & $nssm remove $ServiceName confirm | Out-Null
    Start-Sleep -Seconds 2
}

# Install
$arguments = "`"$gatewayScript`" --host $BindHost --http-port $HttpPort --ws-port $WsPort"
& $nssm install $ServiceName $python $arguments | Out-Null

# Configure service
& $nssm set $ServiceName AppDirectory $repo | Out-Null
& $nssm set $ServiceName AppStdout $stdoutLog | Out-Null
& $nssm set $ServiceName AppStderr $stderrLog | Out-Null
& $nssm set $ServiceName AppRotateFiles 1 | Out-Null
& $nssm set $ServiceName AppRotateBytes 10485760 | Out-Null  # rotate at 10 MB
& $nssm set $ServiceName Start SERVICE_AUTO_START | Out-Null
& $nssm set $ServiceName AppExit Default Restart | Out-Null
& $nssm set $ServiceName AppRestartDelay 5000 | Out-Null     # 5s between restarts
& $nssm set $ServiceName Description "Cross-PC protocol gateway (ws+http) -- single canonical bus for multi-agent fleet" | Out-Null

# Start
& $nssm start $ServiceName | Out-Null
Start-Sleep -Seconds 3

# Verify
$status = & $nssm status $ServiceName
Write-Host "Service status: $status"

try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$HttpPort/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "/health OK:"
    Write-Host $health.Content
} catch {
    Write-Warning "Service started but /health did not respond yet. Check $stderrLog. Error: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "OK. Service '$ServiceName' is running and will auto-start on boot."
Write-Host "Next: on every OTHER peer (Linux/WSL, laptops), run register_peer.py as a daemon:"
Write-Host "  python3 tools/register_peer.py --peer-id <unique-id> --http-base http://192.168.2.32:$HttpPort"

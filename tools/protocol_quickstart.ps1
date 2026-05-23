#!/usr/bin/env pwsh
# tools/protocol_quickstart.ps1
# Bootstrap a cross-pc/v1 sender on Windows (PowerShell or PowerShell Core)
# Usage: .\tools\registry_quickstart.ps1 [peer-id] [ws-url] [http-base]
#
# Examples:
#   .\tools\registry_quickstart.ps1                              # defaults: peer-main, ws://127.0.0.1:8787, http://127.0.0.1:8788
#   .\tools\registry_quickstart.ps1 cursor-1                     # custom peer ID
#   .\tools\registry_quickstart.ps1 cursor-1 ws://192.168.1.50:8787 http://192.168.1.50:8788  # custom endpoints

param(
    [string]$PeerId   = if ($env:AGENT_ID) { $env:AGENT_ID } else { Read-Host 'Enter peer ID (e.g. cursor-main)' },
    [string]$WsUrl    = if ($args[0]) { $args[0] } else { 'ws://127.0.0.1:8787' },
    [string]$HttpBase = if ($args[1]) { $args[1] } else { 'http://127.0.0.1:8788' }
)

$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host '=== Cross-PC Protocol v1 Quickstart (Windows/PowerShell) ===' -ForegroundColor Cyan
Write-Host 'Peer ID  :' $PeerId
Write-Host 'WS URL   :' $WsUrl
Write-Host 'HTTP Base:' $HttpBase
Write-Host ''

# --- Send a test dispatch ---
Write-Host '[1] Sending test dispatch...' -ForegroundColor Yellow
$Result = python $RepoRoot\tools\adapters\freebuff_adapter.py --peer-id $PeerId --ws-url $WsUrl --http-base $HttpBase dispatch `
    --command 'Hello from Cross-PC Protocol v1! Quickstart bootstrap successful. Sent via PowerShell.' `
    --workspace $RepoRoot --priority 1 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Dispatch OK:' $Result -ForegroundColor Green
} else {
    Write-Host 'Dispatch failed (exit code: '$LASTEXITCODE')' $Result -ForegroundColor Red
}

# --- Send a heartbeat ---
Write-Host ''
Write-Host '[2] Sending heartbeat...' -ForegroundColor Yellow
$HbResult = python $RepoRoot\tools\adapters\freebuff_adapter.py --peer-id $PeerId --ws-url $WsUrl --http-base $HttpBase heartbeat --status ready 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Heartbeat OK:' $HbResult -ForegroundColor Green
} else {
    Write-Host 'Heartbeat failed (exit code: '$LASTEXITCODE')' $HbResult -ForegroundColor Red
}

# --- Poll for queued messages ---
Write-Host ''
Write-Host '[3] Polling for queued messages...' -ForegroundColor Yellow
$PollResult = python $RepoRoot\tools\adapters\freebuff_adapter.py --peer-id $PeerId --ws-url $WsUrl --http-base $HttpBase poll --limit 5 2>&1
Write-Host $PollResult -ForegroundColor Cyan

Write-Host ''
Write-Host '=== Done ===' -ForegroundColor Cyan
Write-Host 'To send a custom message:'
Write-Host '  python tools\registry_adapter.py --peer-id <id> dispatch --command <msg> [--to <target-peer>]'
Write-Host ''
Write-Host 'Quickstart complete. Press any key to exit...'
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
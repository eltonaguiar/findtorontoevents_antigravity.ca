#!/usr/bin/env powershell
# Deploy Updates to findtorontoevents.ca

$ErrorActionPreference = "Stop"

# FTP Configuration from environment
$ftpServer = $env:FTP_SERVER
$ftpUser = $env:FTP_USER  
$ftpPass = $env:FTP_PASS
$ftpPath = "/findtorontoevents.ca/updates"

Write-Host "========================================"
Write-Host "DEPLOYING UPDATES"
Write-Host "========================================"

if (-not $ftpServer -or -not $ftpUser -or -not $ftpPass) {
    Write-Host "ERROR: FTP credentials not found"
    exit 1
}

Write-Host "Server: $ftpServer"
Write-Host "User: $ftpUser"
Write-Host ""

# Files to deploy
$files = @(
    "updates/index.html",
    "updates/database_infrastructure.html", 
    "updates/multi_timeframe_strategy.html",
    "updates/audit-response-enhancement.html",
    "updates/meme-strategy-v2.html",
    "updates/ENHANCEMENTS.html",
    "updates/backup-plan.html"
)

$success = 0
$failed = 0

foreach ($file in $files) {
    Write-Host "Deploying $file..."
    try {
        $localPath = Join-Path $PWD $file
        if (-not (Test-Path $localPath)) {
            Write-Host "  Not found!" -ForegroundColor Red
            $failed++
            continue
        }
        
        $uri = "ftp://$ftpServer$ftpPath/$([System.IO.Path]::GetFileName($file))"
        $request = [System.Net.FtpWebRequest]::Create($uri)
        $request.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
        $request.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
        $request.UseBinary = $true
        
        $content = [System.IO.File]::ReadAllBytes($localPath)
        $request.ContentLength = $content.Length
        
        $stream = $request.GetRequestStream()
        $stream.Write($content, 0, $content.Length)
        $stream.Close()
        
        $response = $request.GetResponse()
        $response.Close()
        
        Write-Host "  OK" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  FAILED: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "Results: $success success, $failed failed"
Write-Host "========================================"

if ($failed -eq 0) {
    Write-Host "Visit: https://findtorontoevents.ca/updates/"
}

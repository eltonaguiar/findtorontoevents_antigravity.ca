# Meme Coin Scanner Fix Deployment Script
# Deploys critical fixes to the findtorontoevents.ca server

param(
    [switch]$TestOnly,
    [switch]$BackupFirst
)

$ErrorActionPreference = "Stop"

# FTP Configuration from environment
$ftpServer = $env:FTP_SERVER
$ftpUser = $env:FTP_USER
$ftpPass = $env:FTP_PASS

if (-not $ftpServer -or -not $ftpUser -or -not $ftpPass) {
    Write-Error "FTP credentials not found in environment variables. Please set FTP_SERVER, FTP_USER, and FTP_PASS."
    exit 1
}

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "MEME COIN SCANNER FIX DEPLOYMENT" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Server: $ftpServer"
Write-Host "User: $ftpUser"
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')"
Write-Host ""

# Files to deploy
$files = @(
    @{
        Local = "findcryptopairs/api/meme_scanner_fixed.php"
        Remote = "/findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php"
        Description = "Fixed scanner API with inverted tier patch"
    },
    @{
        Local = "scripts/meme_sentiment_scraper_v2.py"
        Remote = "/findtorontoevents.ca/scripts/meme_sentiment_scraper_v2.py"
        Description = "Enhanced sentiment scraper v2"
    },
    @{
        Local = "scripts/meme_scanner_monitor.py"
        Remote = "/findtorontoevents.ca/scripts/meme_scanner_monitor.py"
        Description = "Scanner health monitor"
    }
)

# Test FTP connection
Write-Host "Testing FTP connection..." -ForegroundColor Yellow
try {
    $ftpUri = "ftp://$ftpServer/"
    $ftpRequest = [System.Net.FtpWebRequest]::Create($ftpUri)
    $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::ListDirectory
    $ftpRequest.UseBinary = $true
    $ftpRequest.UsePassive = $true
    
    $response = $ftpRequest.GetResponse()
    $response.Close()
    Write-Host "✅ FTP connection successful" -ForegroundColor Green
} catch {
    Write-Error "❌ FTP connection failed: $_"
    exit 1
}

# Deploy each file
$successCount = 0
$failCount = 0

foreach ($file in $files) {
    $localPath = Join-Path $PSScriptRoot $file.Local
    $remotePath = $file.Remote
    
    Write-Host ""
    Write-Host "Deploying: $($file.Local)" -ForegroundColor Yellow
    Write-Host "  Description: $($file.Description)"
    Write-Host "  Remote: $remotePath"
    
    if (-not (Test-Path $localPath)) {
        Write-Host "  ❌ Local file not found: $localPath" -ForegroundColor Red
        $failCount++
        continue
    }
    
    if ($TestOnly) {
        Write-Host "  🧪 TEST MODE - Would upload $(Get-FileHash $localPath -Algorithm SHA256 | Select-Object -ExpandProperty Hash)" -ForegroundColor Cyan
        $successCount++
        continue
    }
    
    try {
        # Ensure directory exists
        $remoteDir = [System.IO.Path]::GetDirectoryName($remotePath).Replace('\', '/')
        $ftpUri = "ftp://$ftpServer$remotePath"
        
        # Upload file
        $ftpRequest = [System.Net.FtpWebRequest]::Create($ftpUri)
        $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
        $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
        $ftpRequest.UseBinary = $true
        $ftpRequest.UsePassive = $true
        
        $fileContent = [System.IO.File]::ReadAllBytes($localPath)
        $ftpRequest.ContentLength = $fileContent.Length
        
        $requestStream = $ftpRequest.GetRequestStream()
        $requestStream.Write($fileContent, 0, $fileContent.Length)
        $requestStream.Close()
        
        $response = $ftpRequest.GetResponse()
        $response.Close()
        
        Write-Host "  ✅ Upload successful" -ForegroundColor Green
        $successCount++
    } catch {
        Write-Host "  ❌ Upload failed: $_" -ForegroundColor Red
        $failCount++
    }
}

# Summary
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT SUMMARY" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Success: $successCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })

if ($failCount -eq 0) {
    Write-Host ""
    Write-Host "✅ All files deployed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test the fixed API: https://findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php?action=stats"
    Write-Host "  2. Run the GitHub Actions workflow 'Meme Coin Scanner v2'"
    Write-Host "  3. Monitor the health check results"
    exit 0
} else {
    Write-Host ""
    Write-Host "🔴 Some files failed to deploy. Please check the errors above." -ForegroundColor Red
    exit 1
}

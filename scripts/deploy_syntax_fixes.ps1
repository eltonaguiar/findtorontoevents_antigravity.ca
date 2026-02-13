# Deploy syntax-fixed PHP files to remote FTP server with verification
# This script checks remote files before overwriting them

$ftpServer = $env:FTP_SERVER
$ftpUser = $env:FTP_USER
$ftpPass = $env:FTP_PASS

# Files to deploy
$filesToDeploy = @(
    @{
        Local       = "E:\findtorontoevents_antigravity.ca\live-monitor\api\scrapers\cron_scheduler.php"
        Remote      = "ftp://$ftpServer/findtorontoevents.ca/live-monitor/api/scrapers/cron_scheduler.php"
        Description = "Cron scheduler (fixed comment syntax)"
    },
    @{
        Local       = "E:\findtorontoevents_antigravity.ca\live-monitor\api\setup_sportsbet_tables.php"
        Remote      = "ftp://$ftpServer/findtorontoevents.ca/live-monitor/api/setup_sportsbet_tables.php"
        Description = "Sports bet table setup (fixed escaped quotes)"
    }
)

Write-Host ""
Write-Host "=== DEPLOYMENT VERIFICATION ===" -ForegroundColor Cyan
Write-Host "This script will deploy the following files:" -ForegroundColor Yellow

foreach ($file in $filesToDeploy) {
    Write-Host ""
    Write-Host "  * $($file.Description)" -ForegroundColor White
    Write-Host "    Local:  $($file.Local)" -ForegroundColor Gray
    Write-Host "    Remote: $($file.Remote)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== CHECKING REMOTE FILES ===" -ForegroundColor Cyan

foreach ($file in $filesToDeploy) {
    Write-Host ""
    Write-Host "Checking: $($file.Description)..." -ForegroundColor Yellow
    
    # Try to download current remote file
    try {
        $ftpRequest = [System.Net.FtpWebRequest]::Create($file.Remote)
        $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::DownloadFile
        $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
        $ftpRequest.UseBinary = $true
        $ftpRequest.UsePassive = $true
        
        $response = $ftpRequest.GetResponse()
        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $remoteContent = $reader.ReadToEnd()
        $reader.Close()
        $response.Close()
        
        # Show first 300 chars of remote file
        $previewLength = [Math]::Min(300, $remoteContent.Length)
        $preview = $remoteContent.Substring(0, $previewLength)
        Write-Host "  Remote file exists. Preview:" -ForegroundColor Green
        Write-Host "  $preview" -ForegroundColor DarkGray
        
        # Check for syntax errors in remote
        if ($remoteContent -match "syntax error|Parse error") {
            Write-Host "  WARNING: Remote file has syntax errors - SAFE TO REPLACE" -ForegroundColor Yellow
        }
        else {
            Write-Host "  INFO: Remote file appears valid" -ForegroundColor Cyan
        }
    }
    catch {
        Write-Host "  Remote file does not exist or cannot be accessed" -ForegroundColor Magenta
        Write-Host "  Error: $_" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== DEPLOYMENT CONFIRMATION ===" -ForegroundColor Cyan
$confirmation = Read-Host "Do you want to proceed with deployment? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host ""
    Write-Host "Deployment cancelled by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=== DEPLOYING FILES ===" -ForegroundColor Cyan

foreach ($file in $filesToDeploy) {
    Write-Host ""
    Write-Host "Deploying: $($file.Description)..." -ForegroundColor Yellow
    
    # Create FTP request
    $ftpRequest = [System.Net.FtpWebRequest]::Create($file.Remote)
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
    $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
    $ftpRequest.UseBinary = $true
    $ftpRequest.UsePassive = $true
    
    # Read file content
    $fileContent = [System.IO.File]::ReadAllBytes($file.Local)
    $ftpRequest.ContentLength = $fileContent.Length
    
    # Upload file
    try {
        $requestStream = $ftpRequest.GetRequestStream()
        $requestStream.Write($fileContent, 0, $fileContent.Length)
        $requestStream.Close()
        
        $response = $ftpRequest.GetResponse()
        Write-Host "  SUCCESS: $($response.StatusDescription)" -ForegroundColor Green
        $response.Close()
    }
    catch {
        Write-Host "  ERROR: Upload failed - $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host "All files deployed successfully!" -ForegroundColor Green
Write-Host ""

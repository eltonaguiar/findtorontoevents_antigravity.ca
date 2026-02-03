# Deploy MOVIESHOWS2 to findtorontoevents.ca via SFTP
# This script uploads the MOVIESHOWS2 directory to the web server

Write-Host "🚀 Deploying MOVIESHOWS2 to findtorontoevents.ca..." -ForegroundColor Cyan

# Configuration
$ftpHost = "ftps2.50webs.com"
$ftpPort = 22
$ftpUser = "ejaguiar1"
$remotePath = "/findtorontoevents.ca/MOVIESHOWS2"
$localPath = "E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2"

Write-Host "`n📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Host: $ftpHost" -ForegroundColor Gray
Write-Host "  Port: $ftpPort" -ForegroundColor Gray
Write-Host "  User: $ftpUser" -ForegroundColor Gray
Write-Host "  Remote: $remotePath" -ForegroundColor Gray
Write-Host "  Local: $localPath" -ForegroundColor Gray

# Check if WinSCP is available
$winscpPath = "C:\Program Files (x86)\WinSCP\WinSCP.com"
if (-not (Test-Path $winscpPath)) {
    Write-Host "`n❌ WinSCP not found at: $winscpPath" -ForegroundColor Red
    Write-Host "`n📝 Manual Deployment Instructions:" -ForegroundColor Yellow
    Write-Host "  1. Open your FTP client (FileZilla, WinSCP, etc.)" -ForegroundColor White
    Write-Host "  2. Connect to:" -ForegroundColor White
    Write-Host "     - Host: ftps2.50webs.com" -ForegroundColor Cyan
    Write-Host "     - Port: 22 (SFTP)" -ForegroundColor Cyan
    Write-Host "     - Username: ejaguiar1" -ForegroundColor Cyan
    Write-Host "     - Password: (from your .env file)" -ForegroundColor Cyan
    Write-Host "  3. Navigate to: /findtorontoevents.ca/" -ForegroundColor White
    Write-Host "  4. Upload the entire MOVIESHOWS2 folder" -ForegroundColor White
    Write-Host "  5. Verify at: https://findtorontoevents.ca/MOVIESHOWS2/" -ForegroundColor Green
    Write-Host "`n💡 Or install WinSCP from: https://winscp.net/eng/download.php" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✓ WinSCP found!" -ForegroundColor Green

# Prompt for password
$password = Read-Host "Enter FTP password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Create WinSCP script
$scriptContent = @"
option batch abort
option confirm off
open sftp://${ftpUser}:${plainPassword}@${ftpHost}:${ftpPort}/ -hostkey=*
cd /findtorontoevents.ca
mkdir MOVIESHOWS2
cd MOVIESHOWS2
lcd "$localPath"
put index.html
exit
"@

$scriptPath = "$env:TEMP\winscp_deploy_movieshows2.txt"
$scriptContent | Out-File -FilePath $scriptPath -Encoding ASCII

Write-Host "`n📤 Uploading files..." -ForegroundColor Cyan

# Execute WinSCP
try {
    & $winscpPath /script="$scriptPath" /log="$env:TEMP\winscp_deploy_movieshows2.log"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
        Write-Host "`n🌐 Your site is now live at:" -ForegroundColor Cyan
        Write-Host "   https://findtorontoevents.ca/MOVIESHOWS2/" -ForegroundColor Yellow
        Write-Host "`n📝 Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Visit the URL above to verify" -ForegroundColor White
        Write-Host "  2. Test the tooltip on the main page" -ForegroundColor White
        Write-Host "  3. Check that links to /MOVIESHOWS work" -ForegroundColor White
    } else {
        Write-Host "`n❌ Deployment failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Check log at: $env:TEMP\winscp_deploy_movieshows2.log" -ForegroundColor Yellow
    }
} catch {
    Write-Host "`n❌ Error during deployment: $_" -ForegroundColor Red
} finally {
    # Clean up
    if (Test-Path $scriptPath) {
        Remove-Item $scriptPath -Force
    }
}

Write-Host "`n✨ Done!" -ForegroundColor Green

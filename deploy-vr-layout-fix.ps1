# Deploy layout-fix.js to findtorontoevents.ca via SFTP
Write-Host "🚀 Deploying layout-fix.js to findtorontoevents.ca/vr/..." -ForegroundColor Cyan

# Configuration
$ftpHost = "ftps2.50webs.com"
$ftpPort = 22
$ftpUser = "ejaguiar1"
$remotePath = "/findtorontoevents.ca/vr/layout-fix.js"
$localFile = "E:\findtorontoevents_antigravity.ca\vr\layout-fix.js"

Write-Host "`n📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Host: $ftpHost" -ForegroundColor Gray
Write-Host "  Port: $ftpPort" -ForegroundColor Gray
Write-Host "  User: $ftpUser" -ForegroundColor Gray
Write-Host "  Remote: $remotePath" -ForegroundColor Gray
Write-Host "  Local: $localFile" -ForegroundColor Gray

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
    Write-Host "  3. Navigate to: /findtorontoevents.ca/vr/" -ForegroundColor White
    Write-Host "  4. Upload layout-fix.js" -ForegroundColor White
    Write-Host "  5. Verify at: https://findtorontoevents.ca/vr/movies.html" -ForegroundColor Green
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
cd /findtorontoevents.ca/vr
put "$localFile"
exit
"@

$scriptPath = "$env:TEMP\winscp_deploy_layout_fix.txt"
$scriptContent | Out-File -FilePath $scriptPath -Encoding ASCII

Write-Host "`n📤 Uploading layout-fix.js..." -ForegroundColor Cyan

# Execute WinSCP
try {
    & $winscpPath /script="$scriptPath" /log="$env:TEMP\winscp_deploy_layout_fix.log"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
        Write-Host "`n🌐 File deployed to:" -ForegroundColor Cyan
        Write-Host "   https://findtorontoevents.ca/vr/layout-fix.js" -ForegroundColor Yellow
        Write-Host "`n📝 Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Visit https://findtorontoevents.ca/vr/movies.html" -ForegroundColor White
        Write-Host "  2. Hard refresh (Ctrl+Shift+R)" -ForegroundColor White
        Write-Host "  3. Verify the overlapping is fixed" -ForegroundColor White
    }
    else {
        Write-Host "`n❌ Deployment failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Check log at: $env:TEMP\winscp_deploy_layout_fix.log" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "`n❌ Error during deployment: $_" -ForegroundColor Red
}
finally {
    # Clean up
    if (Test-Path $scriptPath) {
        Remove-Item $scriptPath -Force
    }
}

Write-Host "`n✨ Done!" -ForegroundColor Green

# PowerShell script to download and display .htaccess file contents
# This proves the file exists by actually downloading it

$FTP_HOST = "ftps2.50webs.com"
$FTP_USER = "ejaguiar1"
$FTP_PASS = '$a^FzN7BqKapSQMsZxD&^FeTJ'
$REMOTE_FILE = "next/_next/.htaccess"
$LOCAL_TEMP = "$env:TEMP\htaccess_verify.txt"

Write-Host "Downloading .htaccess file from FTP server..." -ForegroundColor Cyan
Write-Host "Remote path: $REMOTE_FILE" -ForegroundColor Cyan
Write-Host ""

try {
    # Create FTP request to download the file
    $ftpRequest = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/${REMOTE_FILE}")
    $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::DownloadFile
    $ftpRequest.EnableSsl = $true
    $ftpRequest.UsePassive = $true
    
    # Get response and download
    $response = $ftpRequest.GetResponse()
    $responseStream = $response.GetResponseStream()
    
    # Save to temp file
    $fileStream = [System.IO.File]::Create($LOCAL_TEMP)
    $responseStream.CopyTo($fileStream)
    $fileStream.Close()
    $responseStream.Close()
    $response.Close()
    
    # Read and display contents
    $fileSize = (Get-Item $LOCAL_TEMP).Length
    $content = Get-Content $LOCAL_TEMP -Raw
    
    Write-Host "✅ SUCCESS! File downloaded!" -ForegroundColor Green
    Write-Host ""
    Write-Host "File size: $fileSize bytes" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "=== FILE CONTENTS ===" -ForegroundColor Green
    Write-Host $content -ForegroundColor White
    Write-Host ""
    Write-Host "=== END OF FILE ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "File saved to: $LOCAL_TEMP" -ForegroundColor Yellow
    Write-Host "You can open it with: notepad `"$LOCAL_TEMP`"" -ForegroundColor Cyan
    
    # Open in notepad
    Write-Host ""
    $open = Read-Host "Open file in Notepad? (Y/N)"
    if ($open -eq 'Y' -or $open -eq 'y') {
        notepad $LOCAL_TEMP
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ ERROR: Could not download file" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.InnerException) {
        Write-Host $_.Exception.InnerException.Message -ForegroundColor Red
    }
    exit 1
}

Write-Host ""
Write-Host "=== PROOF COMPLETE ===" -ForegroundColor Green
Write-Host "The file exists because we just downloaded it!" -ForegroundColor Cyan

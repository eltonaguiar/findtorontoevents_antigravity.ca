# Simple script to verify .htaccess exists by trying to read it
# Run this anytime to prove the file is there

$FTP_HOST = "ftps2.50webs.com"
$FTP_USER = "ejaguiar1"
$FTP_PASS = '$a^FzN7BqKapSQMsZxD&^FeTJ'

Write-Host "Checking if .htaccess exists..." -ForegroundColor Cyan
Write-Host ""

# Method 1: Try to get file size (proves it exists)
try {
    $ftpRequest = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/next/_next/.htaccess")
    $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::GetFileSize
    $ftpRequest.EnableSsl = $true
    $ftpRequest.UsePassive = $true
    
    $response = $ftpRequest.GetResponse()
    $fileSize = $response.ContentLength
    $response.Close()
    
    Write-Host "✅ .htaccess EXISTS!" -ForegroundColor Green
    Write-Host "   Size: $fileSize bytes" -ForegroundColor Cyan
    Write-Host "   Location: next/_next/.htaccess" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The file is there, just hidden from directory listings." -ForegroundColor Yellow
    
} catch {
    Write-Host "❌ .htaccess NOT FOUND" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Method 2: Try to read first few bytes
Write-Host "Reading file contents..." -ForegroundColor Cyan
try {
    $ftpRequest2 = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/next/_next/.htaccess")
    $ftpRequest2.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $ftpRequest2.Method = [System.Net.WebRequestMethods+Ftp]::DownloadFile
    $ftpRequest2.EnableSsl = $true
    $ftpRequest2.UsePassive = $true
    
    $response2 = $ftpRequest2.GetResponse()
    $stream = $response2.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $firstLine = $reader.ReadLine()
    $reader.Close()
    $response2.Close()
    
    Write-Host "✅ File contents (first line):" -ForegroundColor Green
    Write-Host "   $firstLine" -ForegroundColor White
    Write-Host ""
    Write-Host "This proves the file exists and is readable!" -ForegroundColor Green
    
} catch {
    Write-Host "Could not read file contents: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green

# PowerShell script to verify .htaccess file exists on FTP server
# This will prove the file is really there even if FileZilla doesn't show it

$FTP_HOST = "ftps2.50webs.com"
$FTP_USER = "ejaguiar1"
$FTP_PASS = '$a^FzN7BqKapSQMsZxD&^FeTJ'
$REMOTE_DIR = "next/_next"

Write-Host "Connecting to FTP server: $FTP_HOST" -ForegroundColor Cyan
Write-Host "Checking directory: $REMOTE_DIR" -ForegroundColor Cyan
Write-Host ""

try {
    # Create FTP request
    $ftpRequest = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/${REMOTE_DIR}/")
    $ftpRequest.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::ListDirectoryDetails
    $ftpRequest.EnableSsl = $true
    $ftpRequest.UsePassive = $true
    
    # Get response
    $response = $ftpRequest.GetResponse()
    $responseStream = $response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($responseStream)
    
    Write-Host "=== ALL FILES IN $REMOTE_DIR (including hidden) ===" -ForegroundColor Green
    Write-Host ""
    
    $allFiles = @()
    $htaccessFound = $false
    
    while ($null -ne ($line = $reader.ReadLine())) {
        if ($line) {
            $allFiles += $line
            Write-Host $line
            
            # Check if .htaccess is in this line
            if ($line -match '\.htaccess') {
                $htaccessFound = $true
                Write-Host "  ^^^ FOUND .htaccess! ^^^" -ForegroundColor Yellow
            }
        }
    }
    
    $reader.Close()
    $response.Close()
    
    Write-Host ""
    Write-Host "=== SUMMARY ===" -ForegroundColor Green
    Write-Host "Total items found: $($allFiles.Count)" -ForegroundColor Cyan
    
    if ($htaccessFound) {
        Write-Host ""
        Write-Host "✅ .htaccess FILE EXISTS!" -ForegroundColor Green
        Write-Host "The file is there, but FileZilla hides it by default." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To see it in FileZilla:" -ForegroundColor Cyan
        Write-Host "  1. Press Ctrl+H (or Server → Force show hidden files)" -ForegroundColor White
        Write-Host "  2. Refresh the directory (F5)" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "❌ .htaccess NOT FOUND in listing" -ForegroundColor Red
        Write-Host "Let me try to check it directly..." -ForegroundColor Yellow
        
        # Try to get file size directly
        try {
            $ftpRequest2 = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/${REMOTE_DIR}/.htaccess")
            $ftpRequest2.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
            $ftpRequest2.Method = [System.Net.WebRequestMethods+Ftp]::GetFileSize
            $ftpRequest2.EnableSsl = $true
            $ftpRequest2.UsePassive = $true
            
            $response2 = $ftpRequest2.GetResponse()
            $fileSize = $response2.ContentLength
            $response2.Close()
            
            Write-Host ""
            Write-Host "✅ .htaccess EXISTS! (Size: $fileSize bytes)" -ForegroundColor Green
            Write-Host "The file is there, but wasn't in the directory listing." -ForegroundColor Yellow
        } catch {
            Write-Host ""
            Write-Host "❌ Could not access .htaccess file: $_" -ForegroundColor Red
        }
    }
    
    # Also check for README-TEST.txt
    Write-Host ""
    Write-Host "=== Checking for README-TEST.txt ===" -ForegroundColor Green
    try {
        $ftpRequest3 = [System.Net.FtpWebRequest]::Create("ftp://${FTP_HOST}/${REMOTE_DIR}/README-TEST.txt")
        $ftpRequest3.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
        $ftpRequest3.Method = [System.Net.WebRequestMethods+Ftp]::GetFileSize
        $ftpRequest3.EnableSsl = $true
        $ftpRequest3.UsePassive = $true
        
        $response3 = $ftpRequest3.GetResponse()
        $testFileSize = $response3.ContentLength
        $response3.Close()
        
        Write-Host "✅ README-TEST.txt EXISTS! (Size: $testFileSize bytes)" -ForegroundColor Green
        Write-Host "If you see this in FileZilla, you're in the right directory." -ForegroundColor Cyan
    } catch {
        Write-Host "❌ README-TEST.txt not found: $_" -ForegroundColor Red
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green

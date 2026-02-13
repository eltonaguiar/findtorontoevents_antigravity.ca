# Deploy penny-stocks.html to remote FTP server
$ftpServer = $env:FTP_SERVER
$ftpUser = $env:FTP_USER
$ftpPass = $env:FTP_PASS
$localFile = "E:\findtorontoevents_antigravity.ca\findstocks\portfolio2\penny-stocks.html"
$remoteFile = "ftp://$ftpServer/findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html"

Write-Host "Deploying penny-stocks.html to $ftpServer..." -ForegroundColor Cyan

# Create FTP request
$ftpRequest = [System.Net.FtpWebRequest]::Create($remoteFile)
$ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
$ftpRequest.Credentials = New-Object System.Net.NetworkCredential($ftpUser, $ftpPass)
$ftpRequest.UseBinary = $true
$ftpRequest.UsePassive = $true

# Read file content
$fileContent = [System.IO.File]::ReadAllBytes($localFile)
$ftpRequest.ContentLength = $fileContent.Length

# Upload file
try {
    $requestStream = $ftpRequest.GetRequestStream()
    $requestStream.Write($fileContent, 0, $fileContent.Length)
    $requestStream.Close()
    
    $response = $ftpRequest.GetResponse()
    Write-Host "SUCCESS: Upload complete - $($response.StatusDescription)" -ForegroundColor Green
    $response.Close()
}
catch {
    Write-Host "ERROR: Upload failed - $_" -ForegroundColor Red
    exit 1
}

$ftpServer = "ftp://ftp.50webs.com"
$ftpUsername = "ejaguiar1"
$ftpPassword = "Elton2024!"
$localFile = "vr/layout-fix.js"
$remoteFile = "/public_html/vr/layout-fix.js"

try {
    $webclient = New-Object System.Net.WebClient
    $webclient.Credentials = New-Object System.Net.NetworkCredential($ftpUsername, $ftpPassword)
    
    $uri = New-Object System.Uri($ftpServer + $remoteFile)
    $webclient.UploadFile($uri, $localFile)
    
    Write-Host "Successfully uploaded $localFile to $remoteFile" -ForegroundColor Green
} catch {
    Write-Host "Error uploading file: $_" -ForegroundColor Red
    exit 1
}

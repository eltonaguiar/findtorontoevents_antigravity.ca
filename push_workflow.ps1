$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$localFile = 'e:\findtorontoevents_antigravity.ca\.github\workflows\live-monitor-refresh.yml'
$content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($localFile))

$body = @{
    message = 'Add GitHub Actions workflow for live monitor auto-refresh (prices every 30min, track positions, scan signals, circuit breakers)'
    content = $content
    branch = 'main'
} | ConvertTo-Json

$uri = 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/contents/.github/workflows/live-monitor-refresh.yml'
$authHeader = 'token ' + $pat

try {
    $resp = Invoke-RestMethod -Uri $uri -Method Put -Body $body -ContentType 'application/json' -Headers @{ Authorization = $authHeader; Accept = 'application/vnd.github.v3+json' }
    Write-Host ('SUCCESS: Workflow created at ' + $resp.content.path)
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host ('HTTP ' + $statusCode)
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errBody = $reader.ReadToEnd()
        Write-Host $errBody
    }
}

$pat = [System.Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
if (-not $pat) { Write-Output "ERROR: GIT_HUB_PAT_GODMODE not set"; exit 1 }

$headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
$body = '{"ref":"main"}'
$base = 'https://api.github.com/repos/eltonaguiar/findtorontoevents.ca/actions/workflows'

$workflows = @(
    'live-monitor-refresh.yml',
    'refresh-stocks-portfolio.yml'
)

foreach ($wf in $workflows) {
    try {
        Invoke-RestMethod -Method Post -Uri "$base/$wf/dispatches" -Headers $headers -Body $body -ContentType 'application/json'
        Write-Output "OK: $wf triggered"
    } catch {
        Write-Output "FAIL: $wf - $($_.Exception.Message)"
    }
}

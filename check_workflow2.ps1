$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json' }
$r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/live-monitor-refresh.yml/runs?per_page=5' -Headers $h
Write-Host ("Total runs: " + $r.total_count)
foreach ($run in $r.workflow_runs) {
    Write-Host ($run.id.ToString() + ' | ' + $run.status + ' | ' + $run.conclusion + ' | ' + $run.created_at + ' | ' + $run.event)
}

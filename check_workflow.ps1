$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json' }
$r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/live-monitor-refresh.yml/runs?per_page=3' -Headers $h
foreach ($run in $r.workflow_runs) {
    Write-Host ($run.id.ToString() + ' | ' + $run.status + ' | ' + $run.conclusion + ' | ' + $run.created_at + ' | ' + $run.display_title)
}

# Get jobs for the most recent run
if ($r.workflow_runs.Count -gt 0) {
    $runId = $r.workflow_runs[0].id
    Write-Host "`n=== Jobs for run $runId ==="
    $jobs = Invoke-RestMethod -Uri "https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/$runId/jobs" -Headers $h
    foreach ($j in $jobs.jobs) {
        Write-Host ($j.name + ' | ' + $j.status + ' | ' + $j.conclusion)
        foreach ($s in $j.steps) {
            Write-Host ('  Step: ' + $s.name + ' | ' + $s.status + ' | ' + $s.conclusion)
        }
    }
}

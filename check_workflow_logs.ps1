$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json' }

# Get the most recent run
$r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/live-monitor-refresh.yml/runs?per_page=1' -Headers $h
$runId = $r.workflow_runs[0].id
Write-Host "Run ID: $runId"

# Get jobs
$jobs = Invoke-RestMethod -Uri "https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/$runId/jobs" -Headers $h

foreach ($j in $jobs.jobs) {
    Write-Host ("`n=== JOB: " + $j.name + " ===")
    # Get log for this job
    try {
        $logUrl = "https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/jobs/$($j.id)/logs"
        $log = Invoke-WebRequest -Uri $logUrl -Headers $h -UseBasicParsing
        $logText = [System.Text.Encoding]::UTF8.GetString($log.Content)
        # Show relevant lines (skip setup noise)
        $lines = $logText -split "`n"
        foreach ($line in $lines) {
            if ($line -match '(Crypto|Forex|Stock|Tracked|Auto-closed|Symbols|Signals|Portfolio|breaker|ACTIVE|Error|PnL|Learning|Applied|trades)') {
                Write-Host $line
            }
        }
    } catch {
        Write-Host "Could not fetch logs"
    }
}

$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json' }

Write-Host "=== Live Monitor Workflow Runs (last 10) ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/live-monitor-refresh.yml/runs?per_page=10' -Headers $h -TimeoutSec 15
    Write-Host ("Total runs: " + $r.total_count)
    foreach ($run in $r.workflow_runs) {
        Write-Host ('{0} | {1} | {2} | {3} | trigger={4}' -f $run.id, $run.status, $run.conclusion, $run.created_at, $run.event)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

Write-Host "`n=== Current Dashboard ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=dashboard' -TimeoutSec 15
    $s = $r.stats
    Write-Host ("Portfolio: $" + $r.portfolio_value + " | Trades: " + $s.total_trades + " | W:" + $s.wins + " L:" + $s.losses + " WR:" + $s.win_rate + "%")
    Write-Host ("Open: " + $r.open_positions.Count)
    foreach ($p in $r.open_positions) {
        Write-Host ('  ' + $p.symbol + ' ' + $p.direction + ' pnl=' + $p.unrealized_pnl_usd + ' (' + $p.unrealized_pct + '%)')
    }
} catch {
    Write-Host ("Dashboard error: " + $_.Exception.Message)
}

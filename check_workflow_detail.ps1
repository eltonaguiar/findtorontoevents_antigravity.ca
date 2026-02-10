$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json' }

# Check ALL workflow runs (not just live-monitor)
Write-Host "=== ALL RECENT WORKFLOW RUNS ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?per_page=10' -Headers $h -TimeoutSec 15
    Write-Host ("Total runs across all workflows: " + $r.total_count)
    foreach ($run in $r.workflow_runs) {
        Write-Host ($run.id.ToString().PadRight(15) + ' | ' + $run.name.PadRight(45) + ' | ' + $run.status.PadRight(10) + ' | ' + $run.conclusion + ' | ' + $run.created_at + ' | ' + $run.event)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

# Check if the specific workflow is enabled
Write-Host "`n=== WORKFLOW STATE ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows' -Headers $h -TimeoutSec 15
    foreach ($w in $r.workflows) {
        Write-Host ($w.name.PadRight(50) + ' | ' + $w.state + ' | ' + $w.path)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

# Test trade API with correct action names
Write-Host "`n=== TRADE API: positions ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=positions' -TimeoutSec 15
    Write-Host ("OK: " + $r.ok + " | count: " + $r.count)
    foreach ($p in $r.positions) {
        Write-Host ('{0,-12} | {1,-5} | entry={2} | pnl_usd={3}' -f $p.symbol, $p.direction, $p.entry_price, $p.unrealized_pnl_usd)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

Write-Host "`n=== TRADE API: history ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=history&limit=10' -TimeoutSec 15
    Write-Host ("OK: " + $r.ok + " | count: " + $r.count)
    foreach ($t in $r.trades) {
        Write-Host ('{0,-12} | {1,-5} | pnl={2}% | reason={3} | {4}' -f $t.symbol, $t.direction, $t.realized_pnl_pct, $t.close_reason, $t.closed_at)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

Write-Host "`n=== TRADE API: dashboard ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=dashboard' -TimeoutSec 15
    $s = $r.stats
    Write-Host ("Portfolio Value: $" + $r.portfolio_value)
    Write-Host ("Total Trades: " + $s.total_trades + " (W:" + $s.wins + " L:" + $s.losses + " WR:" + $s.win_rate + "%)")
    Write-Host ("Total PnL: $" + $s.total_pnl_usd)
    Write-Host ("Open positions: " + $r.open_positions.Count)
    foreach ($p in $r.open_positions) {
        Write-Host ('  ' + $p.symbol + ' ' + $p.direction + ' entry=' + $p.entry_price + ' unrealized=' + $p.unrealized_pnl_usd + ' (' + $p.unrealized_pct + '%)')
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

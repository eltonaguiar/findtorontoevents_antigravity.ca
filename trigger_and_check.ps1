# Trigger the live monitor workflow NOW
$pat = [Environment]::GetEnvironmentVariable('GIT_HUB_PAT_GODMODE','User')
$h = @{ Authorization = 'token ' + $pat; Accept = 'application/vnd.github.v3+json'; 'Content-Type' = 'application/json' }

Write-Host "=== Triggering live-monitor-refresh workflow ==="
try {
    $body = '{"ref":"main"}'
    Invoke-RestMethod -Method Post -Uri 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/live-monitor-refresh.yml/dispatches' -Headers $h -Body $body -TimeoutSec 15
    Write-Host "Triggered successfully!"
} catch {
    Write-Host ("Trigger error: " + $_.Exception.Message)
}

# Also run a manual scan right now to generate fresh signals
Write-Host "`n=== Running manual scan NOW ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_signals.php?action=scan&key=livetrader2026' -TimeoutSec 120
    Write-Host ("Signals generated: " + $r.count)
    Write-Host ("Symbols scanned: " + $r.symbols_scanned)
    foreach ($s in $r.signals) {
        Write-Host ('{0,-12} | {1,-25} | {2,-5} | str={3}' -f $s.symbol, $s.algorithm_name, $s.signal_type, $s.signal_strength)
    }
} catch {
    Write-Host ("Scan error: " + $_.Exception.Message)
}

# Track existing positions (auto-close if SL/TP hit)
Write-Host "`n=== Tracking positions ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=track&key=livetrader2026' -TimeoutSec 30
    Write-Host ("Tracked: " + $r.tracked + " | Auto-closed: " + $r.closed)
    if ($r.closed_details) {
        foreach ($c in $r.closed_details) {
            Write-Host ("  CLOSED: " + $c.symbol + " | reason=" + $c.exit_reason + " | PnL=$" + $c.realized_pnl_usd)
        }
    }
} catch {
    Write-Host ("Track error: " + $_.Exception.Message)
}

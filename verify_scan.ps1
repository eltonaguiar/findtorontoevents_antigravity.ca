# Verify disclaimers and run scan
Write-Host "=== Verify Disclaimers ==="
try {
    $r = Invoke-WebRequest -Uri 'https://findtorontoevents.ca/findstocks/portfolio2/dividends.html' -TimeoutSec 15 -UseBasicParsing
    if ($r.Content -match 'Data delays') { Write-Host 'DIVIDENDS: Disclaimer FOUND' } else { Write-Host 'DIVIDENDS: Disclaimer MISSING' }
} catch { Write-Host ("Dividends check error: " + $_.Exception.Message) }

try {
    $r = Invoke-WebRequest -Uri 'https://findtorontoevents.ca/findstocks/portfolio2/picks.html' -TimeoutSec 15 -UseBasicParsing
    if ($r.Content -match 'delayed 15-20 minutes') { Write-Host 'PICKS: Delay disclaimer FOUND' } else { Write-Host 'PICKS: Delay disclaimer MISSING' }
} catch { Write-Host ("Picks check error: " + $_.Exception.Message) }

# Run a fresh scan + track
Write-Host "`n=== Running fresh scan ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_signals.php?action=scan&key=livetrader2026' -TimeoutSec 120
    Write-Host ("Signals: " + $r.signals_generated + " | Scanned: " + $r.symbols_scanned)
    foreach ($s in $r.signals) {
        Write-Host ('  ' + $s.symbol + ' | ' + $s.algorithm_name + ' | ' + $s.signal_type + ' | str=' + $s.signal_strength)
    }
} catch { Write-Host ("Scan error: " + $_.Exception.Message) }

Write-Host "`n=== Tracking positions ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_trade.php?action=track&key=livetrader2026' -TimeoutSec 30
    Write-Host ("Tracked: " + $r.tracked + " | Closed: " + $r.closed)
    if ($r.closed_details) {
        foreach ($c in $r.closed_details) {
            Write-Host ("  CLOSED: " + $c.symbol + " reason=" + $c.exit_reason + " PnL=$" + $c.realized_pnl_usd)
        }
    }
} catch { Write-Host ("Track error: " + $_.Exception.Message) }

Write-Host "`n=== Active signals ==="
try {
    $r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_signals.php?action=list' -TimeoutSec 15
    Write-Host ("Active signals: " + $r.count)
    foreach ($s in $r.signals) {
        Write-Host ('  ' + $s.symbol + ' | ' + $s.algorithm_name + ' | ' + $s.signal_type + ' | expires=' + $s.expires_at)
    }
} catch { Write-Host ("List error: " + $_.Exception.Message) }

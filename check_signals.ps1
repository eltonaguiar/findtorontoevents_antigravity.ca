$r = Invoke-RestMethod -Uri 'https://findtorontoevents.ca/live-monitor/api/live_signals.php?action=list' -TimeoutSec 30
Write-Host ("Total active signals: " + $r.count)
foreach ($s in $r.signals) {
    $reason = ''
    if ($s.rationale -and $s.rationale.reason) {
        $reason = $s.rationale.reason
    }
    Write-Host ('{0,-10} | {1,-25} | {2,-5} | str={3,3} | TP={4}% SL={5}%' -f $s.symbol, $s.algorithm_name, $s.signal_type, $s.signal_strength, $s.target_tp_pct, $s.target_sl_pct)
    Write-Host ("  -> " + $reason.Substring(0, [Math]::Min(100, $reason.Length)))
}

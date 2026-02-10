# Live scan with debug
$cryptoKey = [Environment]::GetEnvironmentVariable('CRYPTO_SCAN_KEY','User')
if (-not $cryptoKey) { Write-Host "ERROR: Set CRYPTO_SCAN_KEY env var"; exit 1 }
Write-Host "=== LIVE SCAN v2 ==="
try {
    $r = Invoke-RestMethod -Uri "https://findtorontoevents.ca/findcryptopairs/api/crypto_winners.php?action=scan&key=$cryptoKey" -TimeoutSec 120
    if ($r.ok) {
        Write-Host ("USDT pairs: " + $r.total_pairs + " | Candidates: " + $r.candidates_filtered + " | Analyzed: " + $r.deep_analyzed + " | Winners: " + $r.winners_found + " | Time: " + $r.elapsed_sec + "s")
        Write-Host ""

        if ($r.winners_found -gt 0) {
            Write-Host "=== WINNERS ==="
            foreach ($w in $r.winners) {
                $pair = $w.pair -replace '_USDT', '/USDT'
                Write-Host ('{0,-14} Score={1,3} {2,-12} 24h={3:N1}%' -f $pair, $w.score, $w.verdict, $w.chg_24h)
            }
        }

        Write-Host ""
        Write-Host "=== TOP CANDIDATES (even below threshold) ==="
        foreach ($tc in $r.top_candidates) {
            $pair = $tc.pair -replace '_USDT', '/USDT'
            Write-Host ('{0,-14} Score={1,3} {2,-12} 24h={3:N2}% Vol=${4:N0} | {5}' -f $pair, $tc.score, $tc.verdict, $tc.chg_24h, $tc.vol_usd, $tc.factors_summary)
        }
    } else {
        Write-Host ("Error: " + $r.error)
    }
} catch {
    Write-Host ("Error: " + $_.Exception.Message)
}

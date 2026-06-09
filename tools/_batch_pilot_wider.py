#!/usr/bin/env python3
"""Batch-run forward_paper_pilot.py on the 6 wider-pool sub-T2 candidates at
60d and 90d lookback windows. Outputs a comparison table."""
import subprocess, json, sys
from pathlib import Path
REPO = Path('/home/eaguiar2015/findtorontoevents_antigravity.ca')
sys.path.insert(0, str(REPO))

# High WR/PF sub-T2 candidates from the wider clean-cohort pool
CANDIDATES = [
    'signal_validation', 'battleground_ml_relaxed_mut', 'claude_ml_moderate_mut',
    'battleground_vwap_1h_mut', 'MeanReversionBB', 'evolutionary_regime_engine',
    # Plus the only Tier-2 survivor, for reference at 60d/90d
    'luxalgo_confluence',
]

results = []
for strat in CANDIDATES:
    for window in (60, 90):
        cmd = ['python3', str(REPO / 'tools' / 'forward_paper_pilot.py'),
               '--strategy', strat, '--asset-class', 'CRYPTO',
               '--lookback-days', str(window), '--max-hold-bars', '168']
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(REPO))
            # parse last line "FORWARD VERDICT: X"
            verdict = '?'
            for line in r.stdout.splitlines():
                if 'FORWARD VERDICT' in line: verdict = line.split(':',1)[1].strip()
            # load latest report
            rp = sorted((REPO / 'reports').glob(f'forward_paper_pilot_{strat}_*.json'))
            if rp:
                d = json.loads(rp[-1].read_text())
                results.append((strat, window, d.get('replayed',0), d.get('true_wr_pct',0),
                                d.get('true_pf',0), d.get('tp_to_sl_reclass',0),
                                d.get('forward_verdict','?')))
            else:
                results.append((strat, window, 0, 0, 0, 0, 'no_report'))
        except subprocess.TimeoutExpired:
            results.append((strat, window, 0, 0, 0, 0, 'TIMEOUT'))
        except Exception as e:
            results.append((strat, window, 0, 0, 0, 0, f'ERR:{e}'))

print(f"\n{'strategy':32} {'days':>5} {'n':>5} {'WR%':>6} {'PF':>6} {'recl':>5} verdict")
print('-'*70)
for s, d, n, w, p, rcl, v in results:
    print(f"{s[:32]:32} {d:5d} {n:5d} {w:6} {str(p):>6} {rcl:5} {v}")

# summary
holds = [r for r in results if r[6] == 'HOLDS']
refuted = [r for r in results if r[6] == 'REFUTED']
insuff = [r for r in results if r[6] == 'INSUFFICIENT']
print()
print(f"HOLDS: {len(holds)}/{len(results)} ; REFUTED: {len(refuted)}/{len(results)} ; INSUFFICIENT: {len(insuff)}/{len(results)}")

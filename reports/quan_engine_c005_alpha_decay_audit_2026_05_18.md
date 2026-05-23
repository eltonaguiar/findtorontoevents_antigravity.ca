# C-005: quan_engine Alpha Decay Audit

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Task:** C-005 from MASTER_ACTION_PLAN_2026-05-18.md  
**Verdict:** ❌ BLOCK CONFIRMED — zero viable sub-strategies

---

## Reproduction Command

```bash
python -c "
import json; from pathlib import Path; from collections import defaultdict
reg = json.loads(Path('audit_dashboard/data/pf_registry.json').read_text())
ROOT = Path('.')
qe = []
for sf in reg['source_files']:
    fp = ROOT / sf['file']
    if not fp.exists(): continue
    data = json.loads(fp.read_text())
    picks = data if isinstance(data, list) else data.get('picks', data.get('closed', []))
    qe.extend([p for p in picks if isinstance(p, dict) and 'quan_engine' in str(p.get('source_system',''))])
print(f'quan_engine n={len(qe)}')"
```

---

## Strategy Breakdown

| Strategy | n | Win Rate | Profit Factor | Verdict |
|----------|---|----------|---------------|---------|
| quan_engine_scalp | 5,293 | 29.9% | 0.38 | ❌ BLOCKED |
| quan_engine_swing | 109 | 27.5% | 0.99 | ❌ SUB-T2 |
| quan_engine_position | 26 | 0.0% | 0.00 | ❌ ZERO-WR |
| untagged (strategy='?') | 468 | 37.6% | 0.76 | ❌ SUB-T2 |
| **TOTAL** | **5,896** | **~30%** | **~0.38** | **❌ BLOCKED** |

**Source:** `audit_dashboard/data/pf_registry.json` → 32 source files

---

## Block History

| Date | Action | Evidence |
|------|--------|----------|
| 2026-05-06 | `quan_engine` added to `BLOCKED_SOURCE_SYSTEMS` | PF < T2 floor, source-level block |
| 2026-05-18 | `("CRYPTO", "quan_engine_scalp")` added to `BLOCKED_ASSET_STRATEGY_PAIRS` (line 2396) | 7/7 swarm agents unanimous — see `reports/quan_engine_scalp_swarm_decision_2026_05_18.md` |

---

## Alpha Decay Analysis

No temporal decay data available because no `resolved_at` timestamps are populated on the 5,896 picks. However, structural evidence is sufficient:

1. **quan_engine_scalp** (n=5,293): WR=29.9%, PF=0.38 — well below T2 minimum (WR≥50%, PF≥1.5). All 5 walk-forward folds below 50% (mean=23.3%). 240-cell autopsy found zero profitable sub-segment.

2. **quan_engine_swing** (n=109): WR=27.5%, PF=0.99 — negative expectancy in PF terms.

3. **quan_engine_position** (n=26): WR=0.0% — total loss record.

4. **Root causes (from swarm decision):**
   - ONDOUSDT 60% concentration at peak (single-name autocorrelation)
   - Signal spam ~100/day from correlated EMA sub-signals
   - Avg win (+0.370%) < avg loss (0.417%) — unfavorable risk/reward
   - No temporal robustness across any walk-forward fold

---

## Conclusion

All `quan_engine` sub-strategies are negative expectancy. The source-level block in `BLOCKED_SOURCE_SYSTEMS` (2026-05-06) plus the strategy-level block `("CRYPTO", "quan_engine_scalp")` in `BLOCKED_ASSET_STRATEGY_PAIRS` (2026-05-18) are correct and should not be reversed.

**C-005 STATUS: COMPLETE — blocks confirmed, no alpha found.**  
**D-002 (unblock gate): NOT WARRANTED** — zero qualifying walk-forward fold exists.

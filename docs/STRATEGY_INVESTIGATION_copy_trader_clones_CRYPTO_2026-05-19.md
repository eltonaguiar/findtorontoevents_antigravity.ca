# Strategy Investigation: copy_trader_clones — CRYPTO class
**Date:** 2026-05-19  
**Status:** KILL RECOMMENDED  
**Analyst:** claude-sonnet-4-6 (Session CV) — no swarm dissent needed (clear negative Kelly)

---

## 1. Evidence Summary

| Metric | Value | T2 Threshold | Status |
|---|---|---|---|
| n (resolved) | 34 | ≥30 | ✓ Sufficient |
| Win Rate | 44.1% | ≥50% | ✗ FAIL (−5.9pp) |
| Profit Factor | 0.781 | ≥1.5 | ✗ FAIL |
| Gross Profit | 0.1662 | — | — |
| Gross Loss | 0.2127 | — | — |
| Total PnL | −0.0465 | >0% | LOSS |
| Kelly | −0.123 | >0 | NEGATIVE |
| Avg Win | 0.0111 | — | — |
| Avg Loss | 0.0112 | — | — |
| Risk/Reward | 0.990 (1:1) | — | — |

Source: `audit_dashboard/data/pf_registry.json::by_asset_class_strategy_policy_clean_net` (2026-05-19)

## 2. Autopsy

`copy_trader_clones` CRYPTO has symmetric R:R (avg_win ≈ avg_loss at ~1.1%) but WR=44% — below the 50% break-even point for a 1:1 R:R system. At exactly 1:1 R:R, break-even WR = 50%. At 44%, every trade loses 6pp of expected value.

### Kelly Calculation

- avg_win = 0.0111, avg_loss = 0.0112, RR = avg_win/avg_loss = 0.990
- Kelly = (WR × RR − (1−WR)) / RR = (0.441 × 0.990 − 0.559) / 0.990 = **−0.123**
- Negative Kelly = negative expectancy = capital destroyer

### Axis 1 — Calibration
- Not viable. WR=44% with RR≈1.0 has no path to positive expectancy without both improving WR by 6pp AND improving avg_win vs avg_loss. This is a clone (copy-trade) strategy — the underlying traders being copied are also underperforming.

### Axis 2 — Mutation (direction filter, symbol filter)
- At n=34 with only 15 wins, directional sub-slices would have n<20. No viable mutation.

### Axis 3 — Termination ← **RECOMMENDED**
- Negative Kelly at n≥30 is the block threshold.
- Compare: copy_trader_intel (same source family) blocked 2026-05-18 at WR=0%, PF=0.
- copy_trader_clones is less extreme but still negative expectancy.

## 3. Impact Estimate

Removing 34 picks (15W / 19L):
- CRYPTO policy_clean n: approx. 1610 → 1576
- Removes net −0.0465 PnL drag
- Small WR improvement from removing below-average picks

## 4. Proposed Block

In `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`:
```python
("CRYPTO", "copy_trader_clones"),  # n=34 WR=44% PF=0.78 Kelly=-0.12 — CV 2026-05-19
```

## 5. Verdict

- Negative Kelly (−0.123) at n≥30 meets the block threshold.
- RR=0.990 (symmetric losses): the copy-trade signals have no directional edge.
- Block applied autonomously per session mandate ("proceed to your discretion").

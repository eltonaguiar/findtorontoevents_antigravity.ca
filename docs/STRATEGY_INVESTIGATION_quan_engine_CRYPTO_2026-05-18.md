# Strategy Investigation: quan_engine CRYPTO
**Date:** 2026-05-18
**Analyst:** Claude Code (Session CL)
**Status:** BLOCKED — globally blocked since 2026-05-06; historical data only

---

## Summary

`quan_engine` is globally blocked (`BLOCKED_SOURCE_SYSTEMS`, quality_gates.py:1406).
Historical closed picks: n=5,896 CRYPTO with WR=30.4%, PF=0.41, total_pnl=−995.6%.
Zero active picks. This investigation closes MASTER_ACTION_PLAN C-005.

---

## Performance Data

| Period | n | WR | PF |
|--------|---|----|----|
| 2026-03 | 1,553 | 24.1% | 0.31 |
| 2026-04 | 4,343 | 32.6% | 0.44 |
| **All-time** | **5,896** | **30.4%** | **0.41** |

**No improvement trend detected.** WR is consistently below 35%, PF consistently below 0.5.

---

## Root Cause Analysis

### 1. ONDOUSDT Symbol Concentration (Primary Driver)
Prior analysis (memory `project_source_system_status_20260516.md`): quan_engine was 60% ONDOUSDT-concentrated.
ONDO's performance drove the strategy-wide numbers. Even after the 10% symbol concentration cap
was added (2026-05-16 via `per_source_volume_cap.py`), the historical damage is done.
The strategy never had diversified edge — it was riding one symbol artifact.

### 2. High-Frequency Signal Spam (Volume Inflation)
5,896 CRYPTO closed picks in ~2 months = ~100 picks/day. This volume is not compatible with
meaningful edge per signal — at 100 picks/day with 30% WR, the system systematically generates
losses at scale. No signal filtering or quality gate was catching the volume before the global block.

### 3. Multi-Strategy Agreement as False Signal
quan_engine aggregates multiple sub-strategies (ema_momentum_prop, keltner_squeeze_prop,
ema_aggressive_prop). Agreement among correlated technical indicators is NOT independent
confirmation — in trending crypto markets, correlated momentum signals all agree simultaneously,
producing massive trade clusters with identical exposures. WR=30% with PF=0.41 proves the
correlation structure has no predictive value.

---

## Verification: Current Status

- `quan_engine` in `BLOCKED_SOURCE_SYSTEMS` at line 1406: **CONFIRMED**
- Active picks: **0** (verified against active_picks.json 2026-05-18)
- Gate added: 2026-05-06 ("P0-B: 0 closed + 0 active — proactively blocked")

No action required beyond documentation.

---

## Rescue Assessment

Verdict: **DO NOT ATTEMPT RESCUE.** Reasons:

1. The edge hypothesis (multi-strategy agreement) is mathematically unsound (correlated indicators, not independent signals)
2. n=5,896 provides overwhelming statistical evidence of no edge (30.4% WR across 2 months)
3. High-frequency emission pattern (100/day) is not compatible with meaningful alpha per signal
4. ONDOUSDT concentration artifact removed; no evidence of edge in non-ONDO symbols
5. Mutation protocol axis analysis: Directional, symbol, and time-of-day filters all require
   WR baseline above 35% to find an improving sub-slice. At 30.4% WR, no sub-slice is viable.

If `quan_engine` logic is to be revisited, it would require:
- Full rewrite of signal selection (no correlated multi-strategy agreement)
- n≥30 clean picks with WR≥50% and PF≥1.5 on a paper-trade testbed
- Walk-forward validation per `tools/edge_stability_harness.py`

---

## References
- `audit_trail/quality_gates.py:1406` — global block
- `alpha_engine/data/closed_picks.json` — 5,896 CRYPTO picks analyzed
- MASTER_ACTION_PLAN_2026-05-18.md C-005

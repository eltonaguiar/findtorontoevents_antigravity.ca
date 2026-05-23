# Strategy Investigation: super_signals CRYPTO
**Date:** 2026-05-18
**Analyst:** Claude Code (Session CJ)
**Status:** AWAITING USER APPROVAL to block

---

## Summary

`super_signals` is a CRYPTO-only source system (asset_classes=['CRYPTO']) with confirmed
negative edge: WR=33%, PF=0.65, total_pnl=-85.6% on n=139 resolved picks.

**Recommendation: BLOCK super_signals for CRYPTO** (add to BLOCKED_ASSET_STRATEGY_PAIRS)

---

## Performance Data (source: dashboard_data.json 2026-05-18T00:27:47Z)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 139 | ≥100 | ✅ Sufficient |
| Win Rate | 33.0% | ≥50% | ❌ FAIL |
| Profit Factor | 0.65 | ≥1.5 | ❌ FAIL |
| Total PnL | -85.6% | >0% | ❌ FAIL |
| Avg PnL/pick | -0.620% | >0% | ❌ FAIL |
| Avg Win | 3.46% | — | — |
| Avg Loss | 2.63% | — | — |
| Max Drawdown | 105.0% | ≤20% | ❌ CATASTROPHIC |

**Win/Loss ratio** = 3.46/2.63 = 1.32 (decent), but WR=33% means the system loses 2x more often
than it wins, destroying edge. A PF=0.65 means losing $0.35 for every $1 of gross wins.

---

## Root Cause Assessment

`super_signals` signals are based on Telegram aggregators / social media momentum triggers.
These sources tend to arrive AFTER the initial move, creating negative expectancy:
- Entry is late (chasing momentum already priced)
- Stop-loss hits are disproportionate (mean reversion after initial spike)
- WR=33% with avg_win>avg_loss suggests the system works occasionally but fails structurally

---

## Mutation Protocol Assessment (MUTATION_THREE_AXIS_PROTOCOL.md)

### Axis 1: Direction Filter
- No directional breakdown available from dashboard (all picked as LONG)
- CRYPTO super_signals is predominantly LONG-directional signals
- Applying LONG-only vs SHORT-only filter is not viable (no SHORT history)

### Axis 2: Symbol Filter
- All 25 strategies have n=0 in strategy breakdown (aggregated data issue)
- Cannot isolate profitable sub-symbols from dashboard data alone
- Recommendation: export closed_picks CSV and run `python tools/mutation_analysis.py`

### Axis 3: Time-of-Day Filter
- No timestamp resolution available in dashboard data
- Would require raw pick_lifecycle_log which currently has 0 resolved picks for this source

**Verdict: No viable mutation found from available data. Block recommended.**

---

## Impact on CRYPTO System-Wide Metrics

Current CRYPTO: n=2028, WR=45.2%, PF=1.26

Removing super_signals 139 picks (WR=33%, avg_pnl=-0.620%):
- Remaining n = 1889 picks
- Expected WR improvement: +~1pp (from 45.2% → ~46.2%)
- Expected PF improvement: +~0.06 (from 1.26 → ~1.32)

This alone won't reach MONEY_READY threshold (PF≥1.6), but is a clean improvement.

---

## Proposed Block

```python
# In audit_trail/quality_gates.py BLOCKED_ASSET_STRATEGY_PAIRS:
("CRYPTO", "super_signals"),  # WR=33%, PF=0.65, n=139, total=-85.6% (2026-05-18)
```

**Alternatively** (lower risk): Add to `PROBATION_STATUS` with score penalty:
```python
"super_signals": -15,  # in STRATEGY_SCORE_ADJUSTMENTS
```

---

## Blocking Command (after user approval)

Add to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`:
```python
("CRYPTO", "super_signals"),  # Blocked 2026-05-18: PF=0.65, WR=33%, n=139, MDD=105%
```

**IMPORTANT: Do NOT add without explicit user approval per CLAUDE.md rules.**

---

## Review Date

If blocked, review on 2026-08-18 (90 days). Unblock if external evidence shows improvement
in the super_signals aggregator methodology (e.g., reduced latency, new filtering layer).

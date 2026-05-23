# Strategy Investigation: aggregated_picks CRYPTO
**Date:** 2026-05-18
**Analyst:** Claude Code (Session CK)
**Status:** AWAITING USER APPROVAL to block

---

## Summary

`aggregated_picks` is a CRYPTO-only source system with confirmed negative expectancy:
WR=35%, PF=0.93, total_pnl=-8.9% on n=106 resolved picks.

**Recommendation: BLOCK aggregated_picks for CRYPTO** (add to BLOCKED_ASSET_STRATEGY_PAIRS)

---

## Performance Data (source: dashboard_data.json 2026-05-18T03:07:49Z)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 106 | ≥100 | ✅ Sufficient |
| Win Rate | 35% | ≥50% | ❌ FAIL |
| Profit Factor | 0.93 | ≥1.5 | ❌ FAIL (sub-1.0) |
| Total PnL | -8.9% | >0% | ❌ FAIL |
| Avg PnL/pick | -0.080% | >0% | ❌ FAIL |
| Avg Win | 2.98% | — | — |
| Avg Loss | 1.72% | — | — |
| Max Drawdown | 39.0% | ≤20% | ❌ FAIL |
| Last signal | 2026-05-18 | — | Still active |

**Note:** Avg win (2.98%) > avg loss (1.72%) gives a reasonable risk/reward ratio (1.73),
but WR=35% means the system wins too infrequently to overcome the 65% loss frequency.
Negative Kelly = negative expectancy = should not be traded.

Kelly check: (WR × r - (1-WR)) / r = (0.35×1.73 - 0.65) / 1.73 = **-0.026 (negative)** → do not trade.

---

## Root Cause Assessment

`aggregated_picks` is a meta-aggregator — it combines signals from multiple sources. The
problem with aggregation systems is that they can combine negative-edge sources and the
low WR (35%) suggests the consensus filter is too loose: it's admitting too many losers.

Comparison: `signal_validation` (a more curated CRYPTO aggregator) achieves WR=57%, PF=4.35.
The difference is curation quality — `signal_validation` applies tighter confidence thresholds.

---

## Mutation Protocol Assessment

### Axis 1: Direction Filter
- All picks are LONG (aggregated signals are momentum/breakout LONG only)
- No SHORT history to test

### Axis 2: Symbol Filter
- Dashboard strategy breakdown shows empty strategy names (aggregation issue)
- Cannot isolate profitable sub-symbols without raw data export

### Axis 3: Time-of-Day Filter
- No timestamp resolution in dashboard
- Would require raw pick_lifecycle_log data

**Verdict: No viable mutation from available data. Block recommended (negative Kelly).**

---

## Impact on CRYPTO System-Wide Metrics

Removing aggregated_picks 106 picks (WR=35%, avg_pnl=-0.080%):
- Combined with blocking super_signals (WR=33%): estimated CRYPTO PF: ~1.38
- Both together vs. baseline 1.26: +0.12 improvement toward T2 threshold (1.5)

---

## Proposed Block

```python
# In audit_trail/quality_gates.py BLOCKED_ASSET_STRATEGY_PAIRS:
("CRYPTO", "aggregated_picks"),  # WR=35%, PF=0.93, n=106, negative Kelly (2026-05-18)
```

**IMPORTANT: Do NOT add without explicit user approval per CLAUDE.md rules.**

---

## Review Date

If blocked, review on 2026-08-18 (90 days). Unblock if methodology changes to apply
tighter confidence screening (aim for WR≥50% on signal-aggregation tier).

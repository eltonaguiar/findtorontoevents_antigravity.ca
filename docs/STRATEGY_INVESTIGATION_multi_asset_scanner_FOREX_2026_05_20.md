# Strategy Investigation: multi_asset_scanner / FOREX

**Status:** MUTATION_CANDIDATE — awaiting user approval to block  
**Filed:** 2026-05-20  
**Protocol:** docs/MUTATION_THREE_AXIS_PROTOCOL.md §7 (STRATEGY_INVESTIGATION_BEFORE_KILL)

---

## Evidence Summary

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| WR (FOREX) | 9.1% | ≥50% | FAIL |
| PF (FOREX) | 0.209 | ≥1.2 | FAIL |
| n (FOREX) | ~44 | ≥30 | PASS |
| DSR | not computed | ≥0.95 | — |

Source: `audit_dashboard/data/dashboard_data.json` per-source breakdown (2026-05-20).

## Impact of Blocking

- Current FOREX aggregate PF: **1.491** (just below T2 floor of 1.500)
- `multi_asset_scanner` FOREX: n≈44, WR=9.1%, PF=0.209 — negative expected value
- Excluding `multi_asset_scanner` FOREX → estimated aggregate PF **~1.85+**
- Secondary drag: `alpha_engine` FOREX (WR≈40%, PF≈0.841), also mutation candidate (separate investigation)

## Root Cause Investigation

`multi_asset_scanner` is a multi-class scanner that routes picks across EQUITY, CRYPTO, and FOREX.
The FOREX routing appears to lack the directional filters that make it work for other classes:

1. FOREX picks from this source have no session-time filter (M-078 applies to all sources but this source may not respect it)
2. No carry or trend regime condition — fires indiscriminately on cross-pairs
3. 9.1% WR suggests it is systematically wrong (contrarian signal, not noise)

## Three-Axis Mutation Options (per MUTATION_THREE_AXIS_PROTOCOL.md)

### Axis 1: Direction Flip
- `multi_asset_scanner` FOREX signals reversed (SHORT→LONG, LONG→SHORT)
- WR of reversed signal: estimated ~91% (complement of 9.1%)
- **Recommended if** reversal WR holds on OOS data — run 3-fold backtest

### Axis 2: Class-level Block
- Add `("FOREX", "multi_asset_scanner")` to `BLOCKED_ASSET_STRATEGY_PAIRS`
- Effect: preserves `multi_asset_scanner` for EQUITY/CRYPTO where it performs
- **Requires explicit user approval** per CLAUDE.md

### Axis 3: Sub-filter
- Restrict `multi_asset_scanner` FOREX to USD/JPY pairs only (JPY carry signal is strong per F-ANON-001)
- Block other cross-pairs from this source

## Recommendation

**Axis 2 (class-level block)** is the cleanest fix with the least risk of cross-class regression.
No code changes to the strategy logic itself. Single entry in BLOCKED_ASSET_STRATEGY_PAIRS.

Before implementing Axis 1 (direction flip), run the direction-flip backtest to confirm the
anti-signal hypothesis holds OOS (not just in-sample). Export CSV per protocol:

```bash
python tools/mutation_analysis.py --source multi_asset_scanner --class FOREX --export-csv
```

## Decision Gate

**BLOCKED BY CLAUDE.md:** Cannot add to BLOCKED_ASSET_STRATEGY_PAIRS without explicit user approval.

**To approve Axis 2 block, user should confirm:**
- [ ] Axis 2 block approved: `("FOREX", "multi_asset_scanner")` → BLOCKED_ASSET_STRATEGY_PAIRS

**To test Axis 1 flip first:**
- [ ] Run direction-flip backtest, review result, then decide

## Files to Modify (post-approval)

- `audit_trail/quality_gates.py` — add to `BLOCKED_ASSET_STRATEGY_PAIRS`
- Tests: `tests/test_quality_gates.py` — add assertion for the new block

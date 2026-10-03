# /audit active picks per asset class — per-class visibility floor

**Date:** 2026-10-03
**Scope:** `audit_trail/dashboard_generator.py` → `_apply_per_class_visibility_floor()`
**Status:** fixed, verified locally on a clean branch off `main`

## Symptom

After the crash fix (`2026-10-03-audit-dashboard-frozen-reverse-split-indexerror.md`)
the dashboard could regenerate again, but the published Active Picks book was
empty for most asset classes. Measured on current `main` data by running the
real publish path (`collect_all_picks` → `_is_pre_score_active_candidate` →
`_filter_active_picks_with_gate`):

```
before floor: 30  Counter({'EQUITY': 18, 'ETF': 7, 'BOND': 5})
```

CRYPTO, FOREX, COMMODITY and FUTURES published **0** picks. The frozen
2026-08-30 payload showed the same shape (`asset_class_summary` activeCount 0
for every class except FOREX 1).

## Root cause

Not a single bug — the accumulated admission gates in
`audit_trail/quality_gates.passes_active_gate()` zero out entire classes. Per-class
rejection reasons measured against the live candidate pool:

| Class | Candidates | Passed | Dominant blocking gates |
|---|---|---|---|
| CRYPTO | 76 | 0 | `M-036 crypto_direction_blocked` (LONG), `crypto_not_liquid_core` (top-25 ADV only), confidence-inversion (>0.90), `crypto_short_blocked_in_bull_regime` |
| FOREX | 10 | 0 | FOREX directional gate (LONG requires elite≥75 & conf≥0.75), `forex_session_gate`, FOREX symbol gate |
| COMMODITY | 11 | 0 | `BLOCKED_DIRECTION_TRIPLES`, `commodity_subclass_killed` (CL=F/GC=F/NG=F/ZC=F) |
| FUTURES | 2 | 0 | `matrix_symbol_gate` allow-list |
| EQUITY | 31 | 18 | — |
| ETF | 13 | 7 | — |
| BOND | 5 | 5 | — |

Each gate is deliberate and evidence-backed (they exist to block historically
losing pairs). The problem is *dashboard starvation*, which directly contradicts
the stated philosophy right above `ACTIVE_PICKS_MIN_SCORE`:

> `ACTIVE_PICKS_MIN_SCORE = 0  # REVERTED: let ALL picks through, sort by score. Hiding picks starves the dashboard.`

## Fix

Added `_apply_per_class_visibility_floor(published_active, pre_gate_candidates)`
and call it immediately after the final `_filter_active_picks_with_gate()` pass,
before `asset_class_summary` is built (so per-class counts stay consistent).

Behaviour:

- For each of `CRYPTO, EQUITY, ETF, FOREX, COMMODITY, FUTURES, BOND`, if fewer
  than `N` (default **2**) gate-passing picks are published, surface the
  top-scoring `N` candidates for that class from the pre-gate pool.
- **No gate is relaxed and no trading behaviour changes.** Floored picks are
  tagged `_gate_passed=False`, `_below_gate=True`, `_visibility_floor="per_class"`
  so the UI/stats can distinguish them from gate-passing picks.
- Kill-switch `PER_CLASS_ACTIVE_FLOOR=0`; count override `PER_CLASS_ACTIVE_FLOOR_N`.

Verified result:

```
after floor:  38  Counter({'EQUITY': 18, 'ETF': 7, 'BOND': 5,
                           'CRYPTO': 2, 'FOREX': 2, 'COMMODITY': 2, 'FUTURES': 2})
```

## Verification

- `tests/test_per_class_visibility_floor.py` (9 cases): coverage, no duplication,
  score-descending ranking, kill-switch, env count override, garbage inputs.
- `tests/test_reverse_split_annotate.py` (12 cases) still passes.
- Combined run: **21 passed**.
- `py_compile` clean.

## Limitations / follow-ups

- This is a *visibility* fix. The underlying question "should any CRYPTO/FOREX/
  COMMODITY/FUTURES picks be tradable right now?" is a separate risk decision —
  the gates still say **no**, and the floored picks are marked accordingly.
- If a class genuinely has no candidates at all, nothing is invented (no fake picks).
- The `_below_gate` tag is available for the UI to badge these rows.

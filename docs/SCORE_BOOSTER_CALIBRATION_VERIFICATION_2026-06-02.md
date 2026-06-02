# Score-Booster Calibration Verification — Spec

**Date:** 2026-06-02
**Source:** EAGLE_JUNE2_claude-opus-4-7.md §7.1 + §6.2
**Status:** Calibration is ALREADY WIRED (`alpha_engine/score_booster.py:672-720`); this spec is for VERIFICATION + tighter statistical tests.

## What already exists

`_calibrate_confidence(conf, asset_class)` at `alpha_engine/score_booster.py:672` returns a per-pick score adjustment (-15 to +5) that addresses the confidence inversion observed in the audit:

| Class | conf band | adjustment |
|---|---|---:|
| CRYPTO | ≥0.85 | -12 |
| CRYPTO | 0.80-0.85 | -6 |
| CRYPTO | 0.60-0.80 | 0 |
| CRYPTO | 0.50-0.60 | **+3** (best band) |
| CRYPTO | <0.50 | +2 |
| EQUITY | 0.85-0.90 | -15 (worst band) |
| EQUITY | >0.90 | +5 (recovers) |
| EQUITY | 0.70-0.90 | 0 |
| EQUITY | 0.55-0.70 | +3 |
| EQUITY | <0.55 | +1 |
| FOREX | ≥0.85 | -10 |
| FOREX | 0.75-0.85 | 0 |
| FOREX | 0.65-0.75 | +3 |
| COMMODITY | ≥0.85 | -5 |
| COMMODITY | 0.70-0.85 | 0 |
| COMMODITY | 0.60-0.70 | +2 |

This is called at `score_booster.py:1467-1481` for every pick in `active_picks` after the main score is computed.

## What this spec adds: verification + tighter test

### Issue 1 — The current calibration is rule-based, not data-fitted.

The buckets (0.5-0.6 = best, 0.85+ = worst) were derived from a single audit pass. If the underlying WR-by-confidence distribution shifts, the rules don't move with it.

**Fix:** Add a quarterly recalibration pass:

```python
# In tools/recalibrate_score_booster.py (new file, opt-in)
def recompute_calibration(asset_class: str, lookback_days: int = 60) -> dict[str, float]:
    """Read trading_picks closed in the last N days, group by confidence decile,
    compute WR per decile, return a per-decile adjustment that maximizes
    Spearman correlation between adjusted_score and WR."""
    ...
```

This produces a JSON file `alpha_engine/data/score_booster_calibration.json` that `_calibrate_confidence` reads at import. If the file is absent, fall back to the hard-coded rules.

### Issue 2 — The CRYPTO +3 boost at 0.50-0.60 may over-shoot.

If the WR distribution has 0.50-0.60 at 60.3% (best) but 0.60-0.70 at 50% (median), then the 0 vs +3 gap creates a score cliff at 0.60. Picks at 0.59 vs 0.60 may have WR 60% vs 50% but score 53 vs 50 — the boost is correct but the boundary is sharp.

**Fix:** Smooth the boundary:

```python
# Replaces the if/elif ladder
if asset_class == "CRYPTO":
    if conf >= 0.85:
        return -12
    if conf >= 0.80:
        return -6 - 6 * (conf - 0.80) / 0.05  # linear interpolation -6 → -12
    if conf >= 0.60:
        # Smooth transition: 0.60 → 0, 0.50 → +3
        return 3 * (0.60 - conf) / 0.10
    if conf >= 0.50:
        return 3
    return 2
```

This removes the score cliff and is more robust to minor distribution shifts.

### Issue 3 — No live verification of the calibration's effect.

**Fix:** Add a per-decile WR delta test to `audit_trail/quality_gates.py`:

```python
def verify_calibration_drift(asset_class: str, lookback_days: int = 14) -> dict:
    """Compare live WR-by-confidence-band vs the calibration's expected WR.

    Returns: {"drift_pp": float, "verdict": "OK"|"DRIFTED"|"INVERTED"}
    """
    bands = {"low": (0.0, 0.5), "mid": (0.5, 0.7), "high": (0.7, 1.01)}
    expected = {"CRYPTO": {"low": 22, "mid": 60, "high": 14}, ...}
    ...
```

If `mid_drift > 10pp` (mid band WR drops below 50% in live data), flag the calibration for review.

## Test plan

1. `python3 -m py_compile alpha_engine/score_booster.py` OK
2. Unit test: `_calibrate_confidence(0.55, "CRYPTO")` → `+3`; `_calibrate_confidence(0.90, "CRYPTO")` → `-12`; `_calibrate_confidence(0.65, "EQUITY")` → `0`
3. Unit test: after smoothing, `_calibrate_confidence(0.825, "CRYPTO")` → `-9` (linear interp, not `-6`)
4. Live: read 60-day `trading_picks` and confirm mid-band CRYPTO WR is still ≥50% (within drift tolerance)

## Why this is lower priority than the source-system cap

The calibration is already producing the right effect on average (the dashboard shows the inversion is being addressed). The biggest issue isn't the calibration — it's that picks with high conf still get emitted and the cap is per-pick score, not per-emit. The source-system cap (§SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md) is a higher-leverage change.

## Files

- `alpha_engine/score_booster.py` (existing — read-only verification)
- `tools/recalibrate_score_booster.py` (new, opt-in)
- `alpha_engine/data/score_booster_calibration.json` (new, opt-in)
- `audit_trail/quality_gates.py::verify_calibration_drift` (new)

## Status

**NOT YET MERGED.** The smoothing change is small (~15 lines) and could ship as a PR. The recalibration tool + drift check are larger (~100 lines) and need a 2nd-agent review pass per CLAUDE.md before merge.

# Session AR — Swarm Review Request
# Date: 2026-05-17
# Session: AR (following AQ — APPROVE)

## Context

Session AR: Investigated root cause of the elite_score=-8.2 sentinel reported in Session AQ
for cyclic_momentum_stack. Found and fixed a genuine bug (M-083). Code changes committed.

## Session AR Findings

### 1. Root Cause: elite_score Adjustment-from-Zero Bug (M-083)

**Finding:** Signals from strategies that don't pre-compute elite_score (e.g., cyclic_momentum_stack,
fractal_sr_bounce, stochrsi_oversold_bounce) arrive in the forward_validator main loop with
`elite_score=None`. The downstream adjustment gates use fallback defaults:

```python
# forward_validator.py L2740 (GRU, default=0):
signal['elite_score'] = signal.get('elite_score', 0) + _gru_adj

# forward_validator.py L2812 (Volume Confirmation, default=50):
signal["elite_score"] = signal.get("elite_score", 50) + 5
```

When a signal with `elite_score=None` hits one of these defaults, subsequent adjustments
compound on the default (0 or 50) rather than the real score. The sequence of:
- Volume WEAK: `50 - 3 = 47`
- MTF misaligned: `max(0, 47 - 10) = 37`
- Ensemble fails: `max(0, 37 - 10) = 27`
- GRU disagrees: `0 + (-5) = -5` (if GRU fires first with default=0)
- BOCPD changepoint: `existing - 8 = -8.x`

...produces scores like -8.2 for cyclic_momentum_stack (which fires consistently in a
TRENDING_DOWN regime with BOCPD detecting changepoints).

**Verified discrepancy:**
- Shadow tracker records: elite_score=-8.2 (adjustment-from-zero result)
- `compute_elite_score()` actual: 27-28 for cyclic_momentum_stack
- `compute_elite_score()` actual: 33 for fractal_sr_bounce (would PASS Gate 9 at ≥30)
- `compute_elite_score()` actual: 32 for stochrsi_oversold_bounce (would PASS Gate 9)

### 2. M-083 Fix: Batch Pre-Enrichment Before Main Loop

**Location:** `alpha_engine/forward_validator.py`, before `for signal in ranked:` (line 2146)

```python
# M-083: Pre-compute elite_score for signals missing it before the adjustment pipeline.
_m083_unscored = [s for s in ranked if s.get("elite_score") is None]
if _m083_unscored:
    try:
        enrich_picks_with_elite_score(_m083_unscored, DATA_DIR)
        print(f"  [M-083] Pre-scored {len(_m083_unscored)} unscored signal(s) with elite_scorer")
    except Exception as _m083_err:
        print(f"  [M-083] Pre-score failed (non-fatal): {_m083_err}")
```

**Safety properties:**
- Only fires for signals with `elite_score=None` (pre-scored signals untouched)
- Fails silently (non-fatal) — signal passes through if compute fails
- Uses existing `enrich_picks_with_elite_score` (already imported, battle-tested)
- Batch operation (one call, not per-signal overhead)

**Expected impact:**
- `fractal_sr_bounce` (real score=33, ml=0.83-0.98): now passes QUALITY_GATE (≥30)
- `stochrsi_oversold_bounce` (real score=32, ml=0.44-0.71): now passes QUALITY_GATE
- `cyclic_momentum_stack` (real score=27-28): still near threshold (30); adjustments
  may push it above or below depending on regime/BOCPD/MTF

### 3. Tests Added

7 tests in `tests/test_m083_elite_score_pre_enrichment.py`:
- Signals without elite_score correctly identified as unscored
- cyclic_momentum_stack real score > 15 (not -8.2)
- fractal_sr_bounce with ml=0.95 scores ≥28 (passes or near gate)
- stochrsi_oversold_bounce scores ≥25
- Pre-scored signals not overwritten
- Batch enrichment sets scores for all None-scored signals
- -8.2 sentinel value not present after enrichment

128/128 test suite green. Commit: `9acdfcaf11` (rebased to `04f504c6a6`).

### 4. What Did NOT Change

- QUALITY_GATE threshold (still 30) — no gate parameter changes
- BLOCKED_ASSET_STRATEGY_PAIRS — no changes
- Pending user approvals from AO (block cta_cross_asset_tsmom + COMMODITY cap) still waiting
- sr_breakout_retest (save_rate=44%, avg_killed=+1.39%): no action (gate working correctly)
- super_channel_trend_rider (RR_GATE blocks): separate issue, monitor at n=20

## Questions for Swarm

1. **M-083 fix correctness**: The fix ensures elite_score is computed before adjustments.
   But some strategies legitimately set elite_score to a sentinel (e.g., structural strategies
   get elite_score=70). The guard `s.get("elite_score") is None` ensures we don't overwrite.
   Any concerns with this approach?

2. **cyclic_momentum_stack at 27-28**: Still below Gate 9 threshold of 30. After M-083,
   adjustments (MTF -10, Volume, OBI) can push it above or below 30 depending on market
   conditions. This is correct behavior (gate calibrated) rather than junk-score-blocking.
   Should we revisit the QUALITY_GATE threshold for this strategy, or let the data decide?

3. **Shadow tracker reset**: The -8.2 sentinel was accumulating in shadow_blocked.json.
   After M-083, these strategies should no longer appear with -8.2. Should we clear the
   WINNER_FILTER and QUALITY_GATE entries for cyclic_momentum_stack, stochrsi_oversold_bounce,
   and fractal_sr_bounce to restart the shadow stats with corrected scoring?

4. **Overall verdict**: Is Session AR APPROVE?

## Verification

- CI: 0 failures locally (128 tests pass)
- 7 new tests added (all pass)
- py_compile: syntax OK
- Commits: M-083 `04f504c6a6` (forward_validator.py + 7 tests)
- Prior: AQ diagnostic (session_review_aq)

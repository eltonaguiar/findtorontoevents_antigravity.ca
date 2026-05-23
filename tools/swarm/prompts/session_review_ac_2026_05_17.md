# Session AC Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session on findtorontoevents.ca/audit.
This session follows Session AB (new-strategies-scanner workflow + initial picks file).

## Deliverables This Session

### 1. M-074: DXY Inverse Booster for COMMODITY picks

Created `alpha_engine/dxy_booster.py`:
- `dxy_score_adjustment(pick)` — returns score delta for COMMODITY picks based on DXY trend
- WEAK (DXY below SMA20, 5d < -0.5%): LONG picks get +6
- STRONG (DXY above SMA20, 5d > +0.5%): LONG picks get -3, SHORT picks get +4
- NEUTRAL: returns 0
- Non-COMMODITY picks: always returns 0
- Fail-open: missing/stale state file returns 0 (stale threshold: 26h)
- Kill-switch: `DXY_BOOSTER_DISABLED=1` env var
- State file: `alpha_engine/data/dxy_state.json`
- Empirical basis: Gorton & Rouwenhorst (2006), Erb & Harvey (2006)

Created `tools/dxy_state_updater.py`:
- Fetches `DX-Y.NYB` from yfinance (40d history)
- Computes SMA20 + 5-day momentum
- Writes `alpha_engine/data/dxy_state.json` with trend classification
- CLI: `python tools/dxy_state_updater.py [--dry-run]`
- Current state (2026-05-17): DXY=99.270, SMA20=98.430, 5d=+1.46% → STRONG

Wired into `alpha_engine/score_booster.py`:
- Added M-074 block in `run_score_booster()` after CRYPTO hour filter block
- Iterates all active_picks, calls `dxy_score_adjustment(pick)` per pick
- Accumulates `_penalties` list with `dxy_inverse(+N)` tag for traceability
- ImportError is logged + gracefully skipped (fail-open)

Created `.github/workflows/dxy-state-update.yml`:
- Daily cron at 13:30 UTC (9:30 AM ET) Mon-Fri
- Runs `tools/dxy_state_updater.py`
- Commits `alpha_engine/data/dxy_state.json` back to main via rebase-retry loop
- workflow_dispatch with dry_run option

Created `tests/test_dxy_booster.py`:
- 25 tests covering: kill-switch variants, non-COMMODITY picks, WEAK/STRONG/NEUTRAL trends,
  stale state, missing state file, corrupt state file, non-dict picks, signal field fallback,
  get_dxy_state_summary()
- All 25 pass

### 2. Session AC updates/index.html entry added

## Review Questions

1. **Score sign issue**: When STRONG and LONG, we apply `_LONG_PENALTY_WHEN_STRONG = -3`.
   The score is updated with `pick["score"] = max(0, int(old + adj))`. adj=-3 so this correctly
   penalizes. Is clamping to 0 the right floor (vs allowing negative)?

2. **Commodity direction detection**: We check `direction` field first, then fall back to `signal`.
   Are there COMMODITY picks that use other field names for their direction?

3. **Stale threshold**: 26h allows one missed daily run. DXY moves slowly — is this threshold
   appropriate, or should it be 48h to allow for weekends (Friday → Monday)?

4. **yfinance reliability**: `DX-Y.NYB` is the Yahoo Finance ticker for DXY. Is yfinance's
   40-day history window robust enough for SMA20 + 5-day calculations?

5. **Score cap direction**: `max(0, ...)` prevents negative scores. But a -3 penalty on a
   score of 1 gives score=0 vs score=-2. Does this create a floor effect that reduces the
   discriminatory power of the penalty?

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment

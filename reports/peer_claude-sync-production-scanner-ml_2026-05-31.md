# Sync production_scanner ML composite weights with smart_picks_engine

**Date:** 2026-05-31
**Incident:** INCIDENT_OVERALL #17 (IN_PROGRESS, per woxyq5lrr finding)
**Branch:** `fix/sync-production-scanner-ml-2026-05-31`
**Goal:** #1 — Phenomenal performance on `/audit`

## Problem

Two production rankers diverged. `alpha_engine/smart_picks_engine.py:122-167`
shipped the 2026-05-27 PR1 FIX with asset-class-aware ML composite weights
(CRYPTO confidence anti-predictive => zero out; non-CRYPTO retains 0.10).
`alpha_engine/production_scanner.py:_compute_ml_composite` (line 546) still
ranked with stale flat weights `ml*0.6 + conf*0.3 + fwd_wr*0.1` across all
asset classes, and a flat `conf*0.8` fallback with no CRYPTO penalty.

Result: the two rankers disagreed on CRYPTO ordering whenever the scanner
fed the engine, with CRYPTO's known-inverted confidence signal (33.7% WR
at conf>=0.9 vs 45.4% WR at conf 0.5-0.7, n=406 vs 3470 in `at_raw_picks`
90d) silently weighted at 30%.

## Fix

Ported the asset-class-aware weight block from `smart_picks_engine.py:122-167`
into `production_scanner.py:_compute_ml_composite`:

| Asset class | ml_score | confidence | forward_wr | Fallback (no ml_score) |
|-------------|----------|------------|------------|------------------------|
| CRYPTO      | 0.80     | 0.00       | 0.20       | conf * 0.8 * 0.15      |
| Non-CRYPTO  | 0.75     | 0.10       | 0.15       | conf * 0.8 * 0.50      |

Added a docstring comment pointing at the canonical source
(`smart_picks_engine.py:122-167`) so future agents keep both in sync.

## Empirical evidence (CRYPTO confidence inversion)

Source: `at_raw_picks` 90-day window.

| Confidence bin | WR     | n     |
|----------------|--------|-------|
| >= 0.9         | 33.7%  | 406   |
| 0.5 - 0.7      | 45.4%  | 3470  |
| < 0.5          | 44.7%  | 861   |

Inverted gap: **11.7pp** (high-confidence picks WORSE than mid-confidence).
FOREX is direct (91.4% WR at conf>=0.9) — only CRYPTO gets zeroed.

Note: the gemini-cited "14.4% WR at conf>=0.9 vs 60.3% at conf 0.5-0.6"
figures were overstated relative to the at_raw_picks 90d measurement;
the measured 11.7pp inversion is what justifies the policy, not the
inflated number.

## Files changed

- `alpha_engine/production_scanner.py` — `_compute_ml_composite` weights

## Tests

- `python3 -m py_compile alpha_engine/production_scanner.py` => OK
- `grep -rn "_compute_ml_composite\|test_compute_ml" tests/` — no direct
  unit tests on `production_scanner._compute_ml_composite`; the existing
  `test_confidence_calibrator.py:119` covers `smart_picks_engine` only.
  Recommend a follow-up to add a parity test that calls both functions
  with identical CRYPTO + non-CRYPTO fixtures and asserts equal scores.

## Rules followed

- No DB writes (code-only change).
- No auto-merge requested.
- Branch off origin/main in worktree.

## References

- `alpha_engine/smart_picks_engine.py:122-167` — canonical source
- `audit_dashboard/data/pick_summary_stats_14d.json` — recency panels
- `money_ready_verdict.json` 2026-05-24 — tier verdicts

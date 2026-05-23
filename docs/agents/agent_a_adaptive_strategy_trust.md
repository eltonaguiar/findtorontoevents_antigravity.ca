# Agent A — Adaptive Strategy Trust Scorer

## Task
Build a diagnostic per-strategy trust scorer with EWM 23-day half-life + Wilson CI + hot/cold/stable/insufficient classification. Answer the "no strategy is permanently proven" challenge by measuring rolling edge rather than static filters.

## PR
**#161** — `feat(adaptive): per-strategy trust scorer with hot/cold hand detection`

## Files added / modified

### New files
- **`tools/adaptive/__init__.py`** — package marker.
- **`tools/adaptive/strategy_trust.py`** (395 lines) — stdlib-only diagnostic. Loads `alpha_engine/data/closed_picks.json` via `tools.data_integrity._common.load_json_list()` + ghost filter (PR #145 helpers), groups by strategy, computes:
  - `last_48h` and `last_7d` rolling windows (n, PF, WR)
  - `ewm_pf_23d` and `ewm_wr_23d` — weight `exp(-dt*ln2/(23d))`, so a trade 23 days old contributes half as much as today's
  - `wilson_ci_95` — Wilson score interval on raw unweighted WR (95% confidence)
  - `trend` classification: HOT / COLD / STABLE / INSUFFICIENT
- **`tests/test_strategy_trust.py`** (235 lines) — 20 unit tests.
- **`tools/adaptive/out/strategy_trust.json`** — first run output committed for reference (can be regenerated; also under `.gitignore` going forward if preferred).

### Explicitly untouched (scope guardrails)
- No live gate wired. `hourly_performance_monitor.py`, `non_crypto_agent/main.py`, and all curation paths are unchanged.
- `tools/data_integrity/_common.py` unchanged — reused verbatim.

## Why

The session's core thesis from the Monte Carlo baseline (PR #157): full-ledger bootstrap 95% CI is `[-0.163%, -0.130%]` on expectancy with p=1.0 against random walk. The overall system is statistically negative.

Independent analysis showed strategies rotate on a multi-day cadence:
- `st_fear_greed_contrarian` went from "elite" to PF 0.68 in 2 days
- `luxalgo_filters` went from middling to PF 3.05 in the same window

This was subsequently diagnosed as a **tag-aliasing artifact** by Agent C (PR #160) — but the general insight holds: static backtest-derived trust scores decay fast and need to be refreshed against recent rolling performance. This scorer is the diagnostic layer that makes adaptive weighting possible.

## Classification rules

```
HOT          : last_48h.n >= 5 AND last_48h_pf >= 2.0 * last_7d_pf
COLD         : last_48h.n >= 5 AND last_48h_pf <= 0.5 * last_7d_pf
STABLE       : n >= 20 AND last_48h.n >= 3 AND neither HOT nor COLD
INSUFFICIENT : n < 20 OR last_48h.n < 3
```

Thresholds are conservative by design — the classifier flags clear direction changes, not marginal noise.

## Findings on live data

164 strategies total (after ghost filter). Only 6 meet the `n >= 20` threshold for meaningful classification. Breakdown:

| Classification | Count | Highlights |
|---|---|---|
| HOT | 0 | — |
| COLD | 1 | **`quan_engine_scalp`** — the session's workhorse strategy. 48h_pf=0.09 vs 7d_pf=0.47 (0.19x). ewm_pf=0.44, ewm_wr=36%. Total n=2655. This is the cold-hand finding — the strategy that produces most of the picks is bleeding harder in the last 48h than over the previous week. |
| STABLE | 1 | **`ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`** — n=36, ewm_pf=3.09, ewm_wr=57%. One of the ML-enhanced strategies Agent A-prev found were 93-99% correlated (PR #157 `strategy_correlation.py`). |
| INSUFFICIENT | 162 | Includes dormant winners — see below |

### Dormant winners surfaced

Two strategies with strong historical edge but no 48h activity (would be HOT if they were firing):

- **`ml_enhanced_FETUSDT_1d_B_lightgbm`** — n=32, raw_wr=75%, ewm_pf=**18.4**. Very high EWM PF but not producing live picks.
- **`ml_enhanced_RENDERUSDT_4h_D_ensemble_stack`** — n=25, raw_wr=64%, ewm_pf=2.17. Same pattern.

**Follow-up flag:** Why are these not firing? Is the dispatcher dead? Are they gated by a filter that reduces activity to zero? Worth investigating before they're reclassified as dead.

### Single-strategy concentration

The `n >= 20` count of 6 strategies (with one dominant at 2,655 of ~3,500 trades) confirms the concentration finding from PR #157: the book is not diversified. `quan_engine_scalp` being COLD is therefore a system-wide COLD signal, not one bleeding strategy among many.

## Verification

- `python -m py_compile tools/adaptive/strategy_trust.py tests/test_strategy_trust.py` → clean
- `pytest tests/test_strategy_trust.py -q` → **20 passed**
  - Wilson CI edge cases (n=0, 0/10, 10/10, 50/100)
  - EWM half-life exactness
  - EWM properly weights recent trades (regression: old wins + recent losses → PF < 0.5)
  - HOT / COLD / STABLE / INSUFFICIENT classification boundaries
  - Infinity sanitization in JSON output
- Live run emits valid JSON + console report

## Scope guardrails honored
- ✅ Diagnostic only — no gates wired, no curation modified
- ✅ Stdlib only — no numpy / scipy / pandas
- ✅ `_common.py` untouched — helpers reused verbatim
- ✅ `hourly_performance_monitor.py` untouched (the obvious integration point for a follow-up)

## Follow-ups (out of scope for this PR)

1. **Wire the scorer into `hourly_performance_monitor.py`** — consume `tools/adaptive/out/strategy_trust.json` and downweight COLD strategies, boost HOT ones. Natural extension of the existing `IMPROVING_THRESHOLD` / `DEGRADING_THRESHOLD` logic that runs hourly.
2. **Investigate the dormant winners** — why is `ml_enhanced_FETUSDT_1d_B_lightgbm` at ewm_pf=18.4 not firing? Check the dispatcher and any filter gates that might be silencing it.
3. **Alert on HOT↔COLD transitions** — strategy going from HOT to COLD in a single 48h window is a regime change signal worth escalating.
4. **Persist rolling history** — back-plot trust scores against realized PnL so we can validate the predictive value of the HOT/COLD classification.
5. **Audit the 162 INSUFFICIENT strategies** — many are probably dead code or one-trade artifacts. Worth cleaning up.

## Related session PRs
- **#145** — `tools/data_integrity/_common.py` helpers (reused for ghost filter + ledger loading)
- **#157** — Monte Carlo baseline + strategy correlation + rolling expectancy diagnostics (this PR's direct companion)
- **#160** — fear_greed_contrarian forensic (found the tag-aliasing that motivated the "strategies rotate" insight)

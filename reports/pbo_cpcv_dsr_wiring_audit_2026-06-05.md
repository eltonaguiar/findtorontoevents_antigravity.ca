# PBO / CPCV / DSR Wiring Audit (2026-06-05)

## Verdict on Grok's claim

**MOSTLY TRUE, with one important nuance.** The PBO, CPCV, and DSR
implementations exist in this repo, are non-trivial, and even have their
result JSONs sitting on disk. The wire-up into the live pick path is
**partial**: DSR is wired (as a noise-set kill list), PBO/CPCV is
**computed and persisted but not consumed** by any gate. SPA wiring is
through `money_ready_verdict`, not production_scanner.

## Implementations found (real, not docstrings)

| Concept | File | Lines | Status |
|---|---|---|---|
| DSR (Bailey-Lopez de Prado 2014) | `alpha_engine/deflated_sharpe.py` | 179-260 | Real impl |
| DSR (alt) | `alpha_engine/rigorous_backtest_harness.py` | 180-275 | Real impl |
| DSR (alt) | `alpha_engine/strategy_verification_engine.py` | 318-370 | Real impl |
| DSR (alt) | `alpha_engine/backtest_etf_dual_momentum.py` | 650-700 | Real impl, wired into ETF backtest |
| PBO (bootstrap) | `alpha_engine/rigorous_backtest_harness.py` | 278-330 | Real impl |
| PBO (CSCV) | `alpha_engine/admissibility_pipeline.py` | 319-368 | Real impl |
| `cpcv_pbo()` | `alpha_engine/anti_overfit_validator.py` | 56 | Real impl (CPCV combinatorial) |
| Purged k-fold + embargo | `alpha_engine/rigorous_backtest_harness.py` | 340-410 | Real impl |
| Purged-embargoed walk-forward | `alpha_engine/backtest_etf_dual_momentum.py` | 490-545 | Real impl |
| Embargo CV (ML) | `alpha_engine/ml_engine_v2.py` | 962-1010 | Real impl, wired in ml_engine_v2 |
| Per-class DSR/PBO/SPA verdict | `alpha_engine/money_ready_verdict.py` | 589-680 | Real impl |

## Data artifacts on disk (recently regenerated)

- `tools/deflated_sharpe_results.json` (24 KB, 2026-05-25) — used live
- `tools/cpcv_pbo_results.json` (12 KB, **2026-06-02**) — global PBO = 1.0 ("FAIL backtest overfit"), **not consumed anywhere**

## Caller analysis (the actual wire-up gap)

### Live production path (`alpha_engine/production_scanner.py`)
- L5654 `from eagle_gates import apply_eagle5_promotion` — wired
- L5670 `from eagle_gates import apply_eagle6_admissibility` — wired (DSR-noise kill + insufficient-n + HHI)
- **NO import of `admissibility_pipeline`, `strategy_verification_engine`, `rigorous_backtest_harness`, `cpcv_pbo`, or `cpcv_pbo_results.json`.**
- `eagle_gates.py:175-178` explicitly says PBO/WF/Bootstrap CI gates are "v2 (planned)" and notes `tools/cpcv_pbo_results.json` "not yet generated" — **but it IS generated now (2026-06-02)**. The comment is stale.

### Promotion gate (`alpha_engine/validation/promotion_gate.py`)
- L181 calls `PerformanceMetrics.compute_deflated_sharpe(...)` — DSR is wired here
- No PBO call

### `alpha_engine/admissibility_pipeline.py` (the full DSR+PBO+SPA pipeline)
- Self-import only (L23). **Zero external callers.** Pure orphan.

### `alpha_engine/strategy_verification_engine.py`
- Only CLI invocation references. **Zero importers.** Orphan.

## Minimal wire-up diffs

### 1. PBO gate in eagle_gates.py (consume the JSON that already exists)

`alpha_engine/eagle_gates.py` — extend `_load_dsr_noise()` pattern to also
load `tools/cpcv_pbo_results.json` and kill picks whose strategy is in the
`per_strategy` list with `selected_top10=True` AND global `pbo >= 0.7`,
OR add a per-strategy PBO field once the builder emits one. Threshold:
PBO < 0.5 (per the planning comment at L176). Drop-in after L283 in
`apply_eagle6_admissibility`:

```python
# Gate 3: PBO kill (load tools/cpcv_pbo_results.json, kill if global pbo >= 0.7
# OR strategy flagged as overfit). Fail-open if file missing.
_pbo_noise = _load_pbo_noise()  # new helper, mirrors _load_dsr_noise
if strat in _pbo_noise:
    return {"pass": False, "reason": "PBO overfit"}
```

### 2. Drop the stale `eagle_gates.py` L176 comment

`tools/cpcv_pbo_results.json` exists as of 2026-06-02; the "not yet
generated" note is wrong and is the only thing telling future agents the
data isn't there.

### 3. Schedule `tools/build_cpcv_pbo_results.py` daily

It's a one-shot script. Add to the same cron that runs
`tools/deflated_sharpe_results.json` refresh so PBO stays current.

## Bottom line

Grok is right: this is plumbing, not knowledge. The code exists, the
data exists, the gate scaffolding exists. The missing ~30 lines are
(a) a `_load_pbo_noise()` helper in `eagle_gates.py`, (b) a one-line
`if strat in _pbo_noise: kill` call in `apply_eagle6_admissibility`,
and (c) deleting the stale "not yet generated" comment. The DSR side
is already wired and live.

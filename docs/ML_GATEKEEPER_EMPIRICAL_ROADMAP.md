# Gatekeeper: empirical strategy/source signals (roadmap)

## Current behavior

- **Training features** include binary flags `strong_strategy`, `weak_strategy`, `strong_source`, `weak_source` derived from hand-maintained sets in [`ml_gatekeeper/gatekeeper.py`](../ml_gatekeeper/gatekeeper.py) (`STRONG_STRATEGIES`, `WEAK_STRATEGIES`, `STRONG_SOURCES`, `WEAK_SOURCES`).
- **Scoring** already blends ML probabilities with **empirical** `strategy_router.json` / `source` smoothed win rates built from the same closed picks used for training (`build_strategy_router()`).

So the pipeline is **not** purely static: the router supplies rolling, outcome-based priors. The static sets still inject prior beliefs that may go stale.

## How to detect “static list dominance”

Run [`tools/ml_lift_calibration_eval.py`](../tools/ml_lift_calibration_eval.py) with `--compare-priors` on a recent closed-pick export. It reports correlations of outcomes with:

- Static flag columns (via the same encoding as gatekeeper `extract_features`)
- Continuous fields already on picks: `strat_fwd_wr`, `forward_wr`, `elite_score`

If `strat_fwd_wr` / forward metrics correlate more strongly with outcomes than `strong_strategy` / `weak_strategy`, prioritize empirical features in the next model version.

## Planned enhancement (next model bump)

When retraining is acceptable (coordinate with CI / `gatekeeper_model.joblib` version):

1. **Add numeric router features at train time** — e.g. smoothed WR and verdict encoding for `(strategy)`, `(source_system)` merged from `strategy_router.json` **as of train cut-off date** (avoid leakage: use only past closed picks to build the router for each walk-forward fold, or rebuild router inside `backtest_gatekeeper` folds).
2. **Gradually shrink static sets** — use them only as cold-start fallbacks when `strat_fwd_trades` is low.
3. **Version feature schema** — bump a `feature_schema_version` in the saved bundle so old joblib packs are not mixed with new feature lengths.

Until then, refresh static lists sparingly using closed-pick aggregates (same methodology as router STRONG/AVOID verdicts), not guesswork.

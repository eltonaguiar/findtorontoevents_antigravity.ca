# Alpha `MLSignalRanker`: drift, scanner, and feature health

## Responsibilities

| Component | Role |
|-----------|------|
| [`alpha_engine/ml_ranker.py`](../alpha_engine/ml_ranker.py) | Train/load ensemble; `smart_train()`; drift via `prediction_history.json`; incremental training; Boruta selection. |
| [`alpha_engine/scanner.py`](../alpha_engine/scanner.py) | `rank_and_filter_signals()` — enriches signals (OBI, derivatives, regime, etc.), applies **many non-ML gates** (RR, confidence floor, SHORT threshold, regime ML thresholds), then ranks/filters using the ranker’s `ml_score`. |
| [`alpha_engine/feature_health.py`](../alpha_engine/feature_health.py) | Monitors population of ML features (alignment with `MLSignalRanker.FEATURES`). |
| [`alpha_engine/feature_stability_monitor.py`](../alpha_engine/feature_stability_monitor.py) | Stability / drift of feature distributions. |

## Drift detection (implemented)

- **Storage:** `alpha_engine/data/prediction_history.json` (max ~500 entries, see `PREDICTION_HISTORY_MAX`).
- **Recording:** `record_prediction(symbol, strategy, predicted_prob)` after scoring; `update_prediction_outcomes(closed_picks)` back-fills `actual_outcome` using triple-barrier labels.
- **Rule:** `_check_drift()` — over the last **50** resolved predictions, if accuracy of `(prob > 0.5) == win` falls **below 45%**, drift is true → `smart_train()` performs a **full** `train()` instead of incremental.
- **Incremental path:** `incremental_train()` warm-starts booster when drift is false and sample count is in range.

## Scanner interaction

- The scanner applies **filters before and after** ML scoring (falling-knife, RR, confidence floors, regime thresholds). Documented ML thresholds in scanner were **lowered** when precision was poor—so raw ranker scores interact with heuristics. Evaluating the ranker in isolation requires either scoring the same feature rows offline or reading `prediction_history` vs closed outcomes.
- **Feature monitors** should stay aligned: any new feature added to `MLSignalRanker.FEATURES` must be populated in `rank_and_filter_signals` (or upstream enrichment) and listed in feature health checks.

## Operational checklist

1. After deployment, confirm `prediction_history.json` is growing and outcomes are back-filled (`update_prediction_outcomes` wired in training/scan loop).
2. If drift triggers full retrain frequently, inspect `feature_stability_monitor` output and closed-pick label noise (triple-barrier definition).
3. Use [`tools/ml_lift_calibration_eval.py`](../tools/ml_lift_calibration_eval.py) on `alpha_engine/data/closed_picks.json` with ranker-produced scores if persisted on picks; otherwise rely on gatekeeper + dashboard metrics for aggregate lift.

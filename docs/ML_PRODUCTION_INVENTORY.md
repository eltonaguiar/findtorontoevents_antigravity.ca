# Production ML inventory

Single reference for production-integrated machine learning: inputs, outputs, metric artifacts, and the value each module is intended to add. For naming disambiguation between two different “consensus” pipelines, see [ML_CONSENSUS_SYSTEMS.md](ML_CONSENSUS_SYSTEMS.md).

## Summary matrix

| Module | Value hypothesis | Primary inputs | Outputs | Consumers / wiring | Metric artifacts |
|--------|------------------|----------------|---------|----------------------|-------------------|
| **ML Gatekeeper** (`ml_gatekeeper/`) | Ranks and filters dashboard picks using a GB+RF ensemble on pick features; combines with a data-driven **strategy_router** (smoothed WR per strategy/source) so promotion is not only static lists. | `audit_dashboard/data/dashboard_data.json` — `recent_closed` for training; `active` for scoring | `ml_gatekeeper/data/active_picks.json`, `closed_picks.json`; `models/gatekeeper_model.joblib`, `strategy_router.json` | [`.github/workflows/audit-dashboard.yml`](../.github/workflows/audit-dashboard.yml); [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) source keys `ml_gatekeeper` | `ml_gatekeeper/models/training_report.json` (CV, walk-forward, holdout AUC/lift) |
| **Audit ML consensus** (`ml_consensus/consensus.py`) | Surfaces symbols where multiple independent systems agree on direction and scores agreement quality using historical symbol stats + learned weights. | Same `dashboard_data.json` active + closed | `ml_consensus/data/active_picks.json`, `ml_consensus/models/consensus_report.json` | Audit workflow + dashboard source `ml_consensus` | `ml_consensus/models/consensus_report.json` |
| **Alpha `MLSignalRanker`** (`alpha_engine/ml_ranker.py`) | Estimates win probability for scanner signals; supports incremental training, drift detection, Boruta feature selection, and champion–challenger promotion. | Closed picks via DB / `closed_picks.json` (see `train()`, `smart_train()`) | In-memory model at `alpha_engine/data/ml_signal_ranker.joblib` (path may vary); prediction history at `alpha_engine/data/prediction_history.json` | [`alpha_engine/scanner.py`](../alpha_engine/scanner.py) `rank_and_filter_signals()`; [`alpha_engine/auto_tuner.py`](../alpha_engine/auto_tuner.py) `maybe_train_ml` | Training logs; `prediction_history.json` for drift; Boruta cache `data/boruta_selected_features.json` |
| **ML crypto predictor** (`ml_crypto_predictor/`) | Per-pair RF+GBT packs for directional / regime use; persisted models refreshed on schedule. | DB + OHLC pipelines (`fetch_and_populate_db`, etc.) | `ml_crypto_predictor/production_models/*_production.pkl`, optim JSON | [`.github/workflows/train_crypto_models.yml`](../.github/workflows/train_crypto_models.yml); [`.github/workflows/ml-feedback-retrain.yml`](../.github/workflows/ml-feedback-retrain.yml) | `trained_at` inside model packs; `enhanced_models/feedback_data/feedback_training_report.json` |
| **Signal aggregator `MLConsensusEngine`** (`signal_aggregator/ml_consensus.py`) | Predicts signal success probability from **forward-tracking DB** rows (resolved TP/SL/expired), distinct from dashboard JSON. | `forward_tracking.db` (resolved signals joined to `performance_stats`) | `signal_aggregator/models/ml_consensus_latest.pkl` (when training succeeds) | [`.github/workflows/master-automation-scheduler.yml`](../.github/workflows/master-automation-scheduler.yml); [`.github/workflows/ml-model-autotraining.yml`](../.github/workflows/ml-model-autotraining.yml) | Engine `training_stats` in memory; checkpoint pickle |

## How to judge value (operational)

1. **Lift vs baseline** — Use [`tools/ml_lift_calibration_eval.py`](../tools/ml_lift_calibration_eval.py) on closed picks (AUC, Brier, decile lift). Gatekeeper’s own `training_report.json` already includes walk-forward and holdout lift.
2. **Calibration** — Bucket predicted probabilities vs realized win rate (gatekeeper backtest sections; optional analysis via the eval tool).
3. **Drift** — Alpha ranker: `smart_train()` + `prediction_history.json` + `_check_drift()` (rolling accuracy &lt; 45% triggers full retrain). See [ML_ALPHA_RANKER_DRIFT_INTEGRATION.md](ML_ALPHA_RANKER_DRIFT_INTEGRATION.md).
4. **Complementarity vs `quality_gates`** — Gatekeeper outputs a **separate** source_system (`ml_gatekeeper`) for promoted picks; `audit_trail/quality_gates.py` applies heuristic/elite rules on the unified feed. Overlap is intentional: gates = broad hygiene; gatekeeper = learned re-ranking on the same JSON. Quantify overlap with lift metrics before merging logic.

## Where metrics appear in CI

After ML Gatekeeper and Audit ML Consensus run, [`tools/ml_metrics_ci_summary.py`](../tools/ml_metrics_ci_summary.py) appends a short summary to **GitHub Actions step summaries** when `GITHUB_STEP_SUMMARY` is set (see `audit-dashboard.yml`). Artifacts of record remain the JSON files under `ml_gatekeeper/models/` and `ml_consensus/models/`.

## Non-production and legacy

See [ML_NONPRODUCTION_TRIAGE.md](ML_NONPRODUCTION_TRIAGE.md).

## Empirical follow-ups (gatekeeper static priors)

Hard-coded `STRONG_*` / `WEAK_*` sets in `gatekeeper.py` are priors. The **strategy_router** already uses realized outcomes. Planned next steps: [ML_GATEKEEPER_EMPIRICAL_ROADMAP.md](ML_GATEKEEPER_EMPIRICAL_ROADMAP.md).

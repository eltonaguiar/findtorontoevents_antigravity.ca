# ML evaluation, drift repair, and A/B testing — runbook (repo map)

This document ties general ML-ops practice to **this repository’s** concrete modules. It is **not financial advice**.

## Repository map (relevant pieces)

| Concern | Location |
|--------|----------|
| Live residual / concept drift (ADWIN-style) | `ml_battleground/shared/drift_monitor.py` — used e.g. from `mercury2/scanner.py` |
| Feature-level KS + PSI on pick payloads | `alpha_engine/feature_health.py` — `detect_feature_drift` |
| ML pipeline gating (halt / reduce size) | `alpha_engine/ml_health_monitor.py` |
| Large “model health” framework (optional FastAPI) | `model_health_agent.py`, `MODEL_HEALTH_AGENT_README.md` |
| A/B experiment schema + stats | `ab_testing_agent/experiment_manager.py`, `ab_testing_agent/statistics.py` |
| **Batch prediction drift + repair hook** | `alpha_engine/ml_drift_repair_workflow.py` (this PR) |

---

## 1) Concrete Python: monitor drift → trigger repair (crypto price model)

**Online path (already in repo):** stream `(predicted_prob, actual)` into `DriftMonitor.update`; on `True`, log and call your retrain job (with cooldown in `DriftMonitor`).

**Batch / nightly path (new):** compare a **frozen reference** window of model outputs (e.g. predicted 1h return or prob) to **last 7d** outputs with KS + PSI, then optionally shell out a repair command:

```python
import numpy as np
from pathlib import Path
from alpha_engine.ml_drift_repair_workflow import (
    prediction_distribution_drift,
    repair_recommendation,
    execute_repair_plan,
    run_crypto_price_drift_job,
    CryptoDriftJobConfig,
)

# A) In-memory: reference vs recent score vectors
ref = np.load("artifacts/crypto_lstm_ref_preds.npy")
cur = np.load("artifacts/crypto_lstm_last7d_preds.npy")
drift = prediction_distribution_drift(ref, cur)
plan = repair_recommendation(drift)
print(drift, plan)

# B) Optional: actually invoke CI retrain (review before enabling)
execute_repair_plan(plan, dry_run=False, command=os.environ.get("ML_REPAIR_COMMAND"))

# C) JSON / JSONL files with {"y_pred": ...} per row
run_crypto_price_drift_job(
    CryptoDriftJobConfig(
        reference_path=Path("artifacts/ref_scores.json"),
        current_path=Path("artifacts/recent_scores.json"),
        value_key="y_pred",
        out_path=Path("artifacts/drift_report.json"),
    )
)
```

**Design choice:** raw crypto features drift constantly; monitoring **residuals** or **prediction errors** (as `DriftMonitor` does) usually beats raw-feature KS for false-alarm rate.

---

## 2) Repurposing a low-accuracy model as a feature extractor (multi-asset)

**Best practices (implementation-oriented):**

1. **Freeze** the weak model’s trunk; expose **deterministic** embeddings or logits as extra columns (e.g. `meta_emb_0…k`, `cheap_model_logit`).
2. **Never** feed the weak model’s class label alone into the portfolio solver — use **continuous** scores so the second stage can down-weight them.
3. **Train the head** (ranker / allocator) with the extractor **fixed** first, then optional small LR fine-tune on the top layer only if data volume supports it.
4. **Join by time + symbol** with purging / embargo for any walk-forward eval (aligns with your audit / WF language elsewhere in the repo).
5. **Monitor** the *incremental* lift: add-only ablation (`AUC_with_emb - AUC_without`) on a locked validation slice.

In this repo, the closest pattern is **stacking signals in pick JSON** (`ml_enrichment`, composite scores) — treat new extractor outputs like another scored feature and gate them through `ml_health_monitor` / quality gates.

---

## 3) Automated A/B test for business lift (FX carry example)

**Statistical layer:** use `ab_testing_agent` — `ExperimentManager.create_experiment`, `record_observation`, then analyze on `target_metric` (e.g. `sharpe`, `pnl_bps`, `max_dd`).

**Business / execution layer (outline):**

1. **Unit of randomisation:** accounts, books, or strategy IDs (not days, unless you accept serial correlation).
2. **Traffic split:** persist `variant` at assignment time; carry strategies only read their variant’s parameters (e.g. carry lookback).
3. **Telemetry:** append each closed trade with `{experiment_id, variant, pnl_bps, costs}` to the same store your audit pipeline already consumes.
4. **Automation:** nightly job: `record_observation` aggregates per variant → `StatisticalAnalyzer` for significance → if `lift > threshold` and `p < alpha`, open a **manual** promote PR (avoid fully automated capital switches unless explicitly approved).

**Repo hook:** wire a small script under `tools/` that reads closed trades from your DB or JSON export, rolls up metrics, and calls `record_observation` — keep secrets and DB URLs in env, not in code.

---

## Tests

```powershell
python -m pytest tests/test_ml_drift_repair_workflow.py -q
```

---

## Self-check (from your framework)

- Business KPI + technical KPI: define per model in experiment metadata (`ab_testing_agent`) and audit summary.
- Baseline lift: compare to rule-based or last-production model in the same `record_observation` stream.
- Drift: `DriftMonitor` (online) + `prediction_distribution_drift` (batch) + `detect_feature_drift` (features).
- Repair: `execute_repair_plan` is **opt-in** (`ML_REPAIR_COMMAND`, `dry_run=False`) to avoid accidental retrains from dev laptops.

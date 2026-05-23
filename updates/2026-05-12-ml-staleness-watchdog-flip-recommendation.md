# ML Staleness Watchdog: 14-Day Evaluation — Flip Recommendation

**Date:** 2026-05-12  
**Filed by:** claude-sonnet-4-6 (session follow-up triggered by claude-opus-4-7, 2026-04-28)  
**Workflow:** `.github/workflows/ml-staleness-watchdog.yml`  
**Script:** `tools/assert_model_freshness.py`

---

## Verdict: ALL 3 CONDITIONS MET — FLIP RECOMMENDED (with 2 pre-requisites)

---

## 1. Watchdog Run — Current State

```
ML Model Freshness Check (threshold 7.0d, now 2026-05-12T01:58:26Z)
================================================================================
  [OK ] alpha_engine/data/rf_model.pkl                      age=2.77d   source=mtime
  [OK ] alpha_engine/data/ml_challenger.joblib              age=2.77d   source=mtime
  [OK ] ml_gatekeeper/models/gatekeeper_model.joblib        age=0.00d   source=mtime
  [OK ] ml_gatekeeper/models/training_report.json           age=0.07d   source=internal:trained_at
  [OK ] ml_battleground/retrain_trigger.json                age=0.00d   source=mtime
  [MISS] ml_crypto_predictor/enhanced_models/feedback_training_report.json  age=n/a  source=fs
  [FAIL] ml_crypto_predictor/enhanced_models/results/training_summary.json  age=10.84d  source=internal:trained_at
  [OK ] mercury2/data/training_summary.json                 age=0.00d   source=mtime
  [OK ] mercury2/models/top_gainer.joblib                   age=0.00d   source=mtime
  [OK ] claude_gainer_ml/models/training_meta.json          age=0.49d   source=internal:trained_at
  [OK ] claude_gainer_ml/models/claude_xgb.joblib           age=0.00d   source=mtime
  [OK ] crypto_ml_edge/results/training_report.json         age=2.77d   source=mtime
================================================================================
Summary: 10 fresh, 1 stale, 1 missing, 0 skipped
```

**vs 2026-04-28 baseline: 6 stale → now 1 stale.** The auto_tuner persistence fix (commit `1cd5e6fd5a`) and the resolver v2 retraining cycle both drove artifact refresh.

---

## 2. Per-Condition Evaluation

### Condition 1 — Workstream B resolver fix ✅ MET

- `updates/2026-05-05-post-resolver-clean-recompute.md` exists — T+7d follow-up confirmed
- `alpha_engine/outcome_resolver.py:115` ships `PNL_WIN_THRESHOLD_BY_CLASS` (v2 2026-04-28, v2.1 2026-05-02)
- ML training labels for FOREX/COMMODITY were contaminated by the legacy 0.1bp threshold; post-fix labels are clean for the next retraining cycle

### Condition 2 — One full retraining cycle cleared stale artifacts ✅ MET

| Artifact | Age 2026-04-28 | Age 2026-05-12 | Status |
|---|---|---|---|
| `alpha_engine/data/rf_model.pkl` | 12.4d | 2.77d | ✅ cleared |
| `ml_gatekeeper/models/gatekeeper_model.joblib` | 12.3d | 0.00d | ✅ cleared |
| `ml_crypto_predictor/enhanced_models/results/training_summary.json` | 32.4d | **10.84d** | ⚠️ still stale |
| `crypto_ml_edge/results/training_report.json` | ~30d | 2.77d | ✅ cleared |
| Other 2 stale (filing) | stale | fresh | ✅ cleared |

Threshold: ≤2 stale → condition met. Current count: **1 stale** (below threshold).

### Condition 3 — TRACKED_ARTIFACTS list audited ✅ MET (performed this session)

Audited all `.pkl`/`.joblib`/training-report JSON files in the repo.

**Gaps found — 4 untracked production ML systems:**

| Artifact | Age (today) | Production Role |
|---|---|---|
| `meta_strategy/data/meta_learner.joblib` | 2.8d (fresh) | Meta-strategy ensemble |
| `meta_strategy/data/meta_label_model.joblib` | 2.8d (fresh) | Meta-label classification |
| `rl_agent/data/training_summary.json` | 2.8d (fresh) | RL pick-scoring agent |
| `skyrocket_detector/data/training_meta.json` | 2.8d (fresh) | Gap/momentum detector |
| `ml_consensus/models/consensus_report.json` | 0.0d (fresh) | Consensus gating |

**Ghost entry to remove:**
- `ml_crypto_predictor/enhanced_models/feedback_training_report.json` — tracked but never existed (MISS on every run since filing). The `feedback_trainer.py` step was planned but not yet shipped. Should be removed from TRACKED_ARTIFACTS or added back when the trainer ships.

**Intentionally untracked (justified):**
- Individual per-symbol `.joblib` files under `ml_crypto_predictor/enhanced_models/models/` (100+ files) — covered by `training_summary.json` timestamp
- `mercury2/models/ensemble_*.joblib` — covered by `mercury2/data/training_summary.json`
- `ml_battleground/system_*/models/*.joblib` — covered by `ml_battleground/retrain_trigger.json`
- `claude_gainer_ml/models/claude_rf.joblib` + `claude_scaler.joblib` — co-trained with `claude_xgb.joblib`, single retrain cycle covers all three

---

## 3. Pre-Requisites Before the Flip PR

Flipping to hard-fail with `training_summary.json` at 10.84d will cause an immediate CI failure on the next daily run. Two items must be addressed first (can be done in the same PR as the flip):

**Pre-req A — Retrain or skip-condition `ml_crypto_predictor`:**
```
# Option 1: trigger retrain
python ml_crypto_predictor/enhanced_models/feedback_trainer.py --full-retrain

# Option 2: document skip with expiry (if retrain is blocked)
python tools/assert_model_freshness.py --skip ml_crypto_predictor/enhanced_models/results
```
The `trained_at` in the file is `2026-05-01T05:51:00Z` — 11 days old. A retrain is the clean fix.

**Pre-req B — Amend `TRACKED_ARTIFACTS` in `tools/assert_model_freshness.py`:**

```python
# ADD after crypto_ml_edge entry:
("ml_consensus/models/consensus_report.json", "trained_at"),
("meta_strategy/data/meta_learner.joblib", None),
("meta_strategy/data/meta_label_model.joblib", None),
("rl_agent/data/training_summary.json", "trained_at"),
("skyrocket_detector/data/training_meta.json", "trained_at"),

# REMOVE ghost entry:
# ("ml_crypto_predictor/enhanced_models/feedback_training_report.json", "trained_at"),
```

---

## 4. The Flip Diff

Once pre-requisites A+B are done, the workflow change is exactly 1 line:

```diff
--- a/.github/workflows/ml-staleness-watchdog.yml
+++ b/.github/workflows/ml-staleness-watchdog.yml
@@ -52,8 +52,7 @@ jobs:
       - name: Run staleness check (warn-only)
-        # WARN-ONLY MODE: prints stale-artifact list but exits 0 so CI does
-        # not block. Flip to hard-fail by removing --warn-only after the
-        # 3 conditions in the file header are met.
+        # HARD-FAIL MODE: exits 1 on staleness. Conditions met 2026-05-12.
+        # See updates/2026-05-12-ml-staleness-watchdog-flip-recommendation.md
         run: |
           python tools/assert_model_freshness.py \
             --threshold-days 7 \
-            --warn-only \
             --json-out /tmp/freshness.json
```

The step name should also be updated:
```diff
-      - name: Run staleness check (warn-only)
+      - name: Run staleness check (hard-fail)
```

---

## 5. Recommended PR Scope

Single PR titled `ci: flip ML staleness watchdog to hard-fail [conditions met]`:

1. `tools/assert_model_freshness.py` — remove ghost entry, add 4 untracked systems
2. `.github/workflows/ml-staleness-watchdog.yml` — remove `--warn-only`, update step name + comment
3. Either retrain `ml_crypto_predictor` (included as a committed artifact bump) or add a time-boxed skip-condition

**Authorization required from user before opening PR.** This document surfaces the decision; execution pending confirmation.

---

## 6. Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| CI red on day-1 due to ml_crypto_predictor staleness | HIGH if pre-req A skipped | Retrain or skip-condition before merge |
| New untracked system goes stale silently | MEDIUM | Pre-req B adds 4 systems |
| feedback_training_report ghost floods MISS count | LOW | Remove from list |
| Threshold too tight for slow-retraining systems | LOW | 7d matches charter P3 SLA; all current artifacts refresh within 3d |

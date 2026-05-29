# PR2: Enable Leakage-Purged Gatekeeper by Default + Weekly Retrain

**Date:** 2026-05-27
**Branch:** `fix/pr2-gatekeeper-drop-leakage`
**Severity:** P0 — Target leakage in ML gatekeeper model
**Incidents resolved:** INC #P0 (4-feature target leakage in gatekeeper)

## Problem

The ML gatekeeper model uses 4 features that are **downstream proxies of the very outcome it predicts** (per Renaissance + Two Sigma + AQR + Bridgewater R3 reviews):

| Index | Feature | Why it leaks |
|---|---|---|
| 5 | `forward_wr` | Strategy's forward win rate — derived from the same closed-pick outcomes the model predicts |
| 6 | `strat_fwd_wr` | Strategy-level forward WR — same leak |
| 19 | `eb_forward_wr` | Elite breakdown forward WR component — same leak |
| 30 | `age_hours` | Proxy for whether the pick's result is already known |

The +9.21pp CV lift from these features is **illusory** — the model is "rolling its own outcome forward." In production, these features won't be available for new picks (or will be stale), so the model's real accuracy is lower than its CV score suggests.

The infrastructure to fix this already exists (A/B training, leakage masking, router), but:
1. Training defaults to `drop_leakage=false` (OLD leaky bundle)
2. A/B router is disabled by default (`ML_GATE_AB_ENABLED=0`)
3. No scheduled retrain — requires manual workflow dispatch

## Changes

### File: `.github/workflows/ml-gatekeeper-train-ab.yml`
- **Default changed:** `drop_leakage` input default from `"false"` to `"true"`
- **Weekly schedule added:** Cron `0 2 * * 0` (Sunday 02:00 UTC) retrains the NEW bundle automatically
- **Comment added:** Documents the rationale for the default change

### File: `ml_gatekeeper/ab_router.py`
- **A/B enabled by default:** `AB_ENABLED` default changed from `"0"` to `"1"`
- The 50/50 traffic split is preserved — both OLD and NEW bundles are scored for comparison

## Impact Analysis

### Expected Improvement
- **Gatekeeper accuracy:** The NEW bundle's CV score will be ~9pp lower than OLD (removing the illusory lift), but its **production accuracy** should be higher because it won't have access to leakage features at inference time.
- **Pick quality:** Picks scored by the leakage-purged model will have more honest quality estimates — fewer false positives from picks whose outcomes are already partially known.
- **A/B comparison:** The router now runs by default, collecting paired outcome data for a formal z-test. After ~100 picks per arm, we can determine if the NEW model significantly outperforms.

### Risk Assessment
- **False negative risk:** MEDIUM — the NEW model may initially score lower (fewer features), potentially filtering some good picks. Mitigated by 50/50 split (OLD model still scores half).
- **Infrastructure risk:** LOW — the A/B router, training pipeline, and bundle validation are already battle-tested.
- **Regression risk:** LOW — if the NEW model underperforms, `ML_GATE_AB_ENABLED=0` disables the router, reverting to the default single-model scoring.

### Peer Review Notes
- **Quant swarm master plan (2026-05-12):** Identified leakage as "THE ONE THING" — highest-leverage ML fix. All 3 swarm engines confirmed.
- **Grok-4 consultation (2026-05-12):** Recommended A/B sleeve approach with deterministic routing. ✅ Implemented.
- **Bailey & Lopez de Prado (AFML eq 14.5):** Target leakage is the #1 cause of false-positive backtest results. Dropping these features is textbook-correct.

## Verification

After merge:
1. Check `ml_gatekeeper/models/gatekeeper_new.joblib` exists and has `leakage_dropped=True`
2. Monitor `/audit/` — pick scores should show slightly lower ml_composite values (honest scoring)
3. After 100 picks: run `python -m ml_gatekeeper.ab_analysis` to compare OLD vs NEW arm WR
4. Check GitHub Actions — the weekly Sunday cron should auto-train the NEW bundle

## Dependencies
- Requires `scikit-learn>=1.3.2`, `scipy`, `joblib`, `numpy` (already in CI)
- Compatible with existing `score_active_picks_ab()` and dashboard A/B panel
- Does NOT require retraining the OLD bundle — it remains as-is for comparison

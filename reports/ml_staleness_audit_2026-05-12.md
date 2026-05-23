# ML Staleness Audit — 2026-05-12

Investigator `a3d03f2e58585c9ac` output. Are ML models actually learning?
Predicting? Any stale ML?

## Per-system verdict

| Model System | Artifact mtime | Size | Decay? | Verdict |
|---|---|---|---|---|
| **ml_gatekeeper** | 2026-05-12 00:24 | 3.7M joblib | No (AUC +0.0949 vs 0.50, p=0.0029) | **LEARNING** — hourly retrain, CV/WF lift confirmed |
| **ml_consensus** | 2026-05-12 00:24 | 538B report | No (WR +2.36pp vs single-pick) | **LEARNING** — outperforms single-pick baseline |
| **enhanced_ml_crypto_v3** | 2026-03-28 | 20K+ joblib | YES (44d stale) | **STALE** — workflow cron may skip on feature-count mismatch; 20K+ models unretrained 6+ weeks |
| **kimi_signal_tracking** | RETIRED | — | YES (30.4% WR) | **DECAYED** — FOREX-only, -974.66% realized, hard-blocked |
| **enhanced_ml_A_xgboost** | RETIRED | — | YES (28% WR) | **DECAYED** — hard-blocked 2026-04-22 |

## ml_gatekeeper learning signal (deep dive)

From `ml_gatekeeper/models/training_report.json` (mtime 2026-05-12T04:05:45Z):
- CV accuracy 54.5%-60.8% across 5 folds (fold 4 worst at 54.5%)
- Walk-forward mean lift: +9.21pp (statistically significant, p=0.0029)
- Holdout AUC: 0.5949 (modest but above 0.50 random baseline)
- Feature importance top 3: `strat_fwd_wr` (13.4%), `forward_wr` (8.7%), `age_hours` (8.4%)
- `confidence` ranked #11 at 0.0379 importance (weak signal — interesting given memory says confidence is canonical)
- **Per-class holdout lifts:** FOREX +16.86pp, EQUITY +16.16pp, **CRYPTO −16.67pp**
- Acceptance gate: 61/500 holdout picks (~12%)

## CRYPTO confidence inversion — DECAY ALERT

ml_gatekeeper holdout CRYPTO performance is **−16.67pp WR** while FOREX +16.86pp and EQUITY +16.16pp. Per memory `project_performance_reality.md` confidence inverted on ETF+CRYPTO at ρ=−0.127 (ghost-cleaned). The gatekeeper holdout suggests this **persists post-Wave-1 unfreeze**.

**Implication:** the ML stack as a whole is learning, but its CRYPTO output is anti-edge. Either the CRYPTO sub-model needs a separate calibration, or the gate should refuse to surface ml_gatekeeper-blessed CRYPTO picks.

## Stale workflow detection

`.github/workflows/enhanced-ml-crypto.yml:54-100` has stale-model detection
that auto-deletes ALL `.joblib` files if feature count drifts. Last
automated train: unknown — 20K+ files in `ml_crypto_predictor/enhanced_models/models/`
all dated 2026-03-28. Workflow IS firing (scheduled 0 2 UTC train + 19 */2 predict)
but models aren't retraining. Likely the feature-count mismatch gate is
silently skipping training.

## Top 3 actions

1. **Reactivate enhanced-ml-crypto retraining**
   - Manually trigger `workflow_dispatch(mode='train')` on
     `.github/workflows/enhanced-ml-crypto.yml` to confirm feature-count
     parity.
   - If feature schema diverged, regenerate the baseline; retrain 20K+
     per-symbol models from scratch.
   - Estimate: 2-4h compute + 1h orchestration.

2. **Resolve CRYPTO confidence inversion**
   - Pull recent CRYPTO `recent_closed` rows + compute confidence-vs-realized-WR
     correlation. Cite the ρ.
   - If still inverted, either:
     a. Add a class-specific gate that rejects ml_gatekeeper CRYPTO picks
        until rho flips positive, OR
     b. Train a CRYPTO-only gatekeeper that learns the inversion (i.e.,
        score = -gatekeeper_score on CRYPTO).
   - Estimate: 1-2h diagnostic + 2-3h implementation.

3. **Wire anti_overfit_validator.py into production**
   - Memory `project_next_phase_integrations_2026_04_22.md` notes
     anti_overfit_validator was Phase 3 unblock. It's still orphaned (per
     `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` 20/21 orphan rate).
   - ml_gatekeeper training_report.json:310-319 already has p10-p90
     baseline; wire drift detection that auto-gates pickups when live
     confidence < p25.
   - Estimate: 1-2h plumbing.

## Expected impact on /audit

- Per ml_gatekeeper holdout per-class lifts (assuming we fix CRYPTO inversion):
  - **FOREX:** +16.86pp WR lift (if class unblocked)
  - **EQUITY:** +16.16pp WR lift on gated picks
  - **CRYPTO:** -16.67pp → 0 (if inversion gate ships); +5-10pp (if class-specific calibration trains)

## Refs

- `ml_gatekeeper/models/training_report.json` (2026-05-12T04:05:45Z)
- `ml_gatekeeper/models/gatekeeper_model.joblib`
- `ml_consensus/models/consensus_report.json` (2026-05-12T04:05:46Z)
- `ml_crypto_predictor/enhanced_models/models/*.joblib` (2026-03-28, stale)
- `.github/workflows/enhanced-ml-crypto.yml`
- `alpha_engine/strategy_blocklist.py:190` (kimi_signal_tracking retired)
- `alpha_engine/strategy_blocklist.py:164` (enhanced_ml_A_xgboost retired)
- Memory `project_performance_reality.md` (confidence inversion baseline)
- Memory `project_next_phase_integrations_2026_04_22.md` (anti_overfit_validator orphan)
- Investigator `a3d03f2e58585c9ac` 2026-05-12

## NFA

Research surface only. Top-3 actions above must clear before any ml_gatekeeper-blessed
CRYPTO pick is sized real-money. The full ml_enhanced_* family quarantine
under `audit_dashboard/money_ready_filter.js::SUPREME_EDGE_REAL` (4 strategies,
3 with Agent E "placeholder-stat suspect" flag) remains the canonical
real-money gate for ML picks.

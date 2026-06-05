# ML / MLOps Usefulness Research — sklearn / xgboost / pytorch / tensorflow (2026-06-04)

**Author:** Claude Opus 4.8 · **Method:** repo recon + 5-model multi-round AI review (raw reviews in
`reports/mlops_review_2026-06-04/`; verdict GO-with-revision, the review materially changed the thesis).

## Existing footprint (recon)
xgboost 181 files · lightgbm 142 · sklearn 56 · catboost 20 · torch 10 · tensorflow 4 · **optuna 0
(unused)** · mlflow 4 (barely). The project is already ML-rich on tree models. ml_ranker /
ml_engine_v2 / ml_health_monitor exist.

## Context that drives the answer
This session's core finding: **no transferable edge.** 8 clean-bar archetypes → 1 passed leakage-free
attribution (ETF dual-momentum, alpha t=2.36, beta 0.34); the rest collapse to market beta. The
headline AI sleeve failed attribution (beta/memorization, per KTD-Fin arXiv 2605.28359). Data is the
bottleneck: signal_ts missing, ~25% no provenance, FORCE_CLOSED_TOXIC pollution, batch-stamped
resolved_at, n=48-monthly samples. `money_ready=[]`.

## Verdict (after multi-round AI review)
**The bottleneck is DATA, not model class. Add no new model family. Fix data + validation first.**

| Tool | Useful here? | Why |
|---|---|---|
| **PyTorch / TensorFlow** | ❌ **NO** (unanimous reviewers) | tiny (n~48), noisy, tabular, no proven edge → DL overfits, uninterpretable, non-reproducible. Tree models already correct. |
| **scikit-learn / xgboost / lightgbm / catboost** | ✅ already pervasive — keep, don't expand blindly | right-sized for tabular; but they're "least-wrong on tiny data", not a fix for no-edge data. |
| **pandera / great-expectations** (data validation) | ✅ **HIGHEST-ROI addition** (3/4 reviewers) | auto-catch the signal_ts / provenance / FORCE_CLOSED_TOXIC / unit-mismatch issues that are the actual problem. |
| **Optuna (HPO)** | ⚠️ **DEFER** (review correction — I over-rated it) | HPO on n=48 noisy samples is *itself* a false-discovery/leakage vector even inside purged-CV. Add only AFTER data hygiene + sample growth. |
| **mlflow / lightweight JSON registry** | ✅ medium | experiment tracking + reproducibility; complements the hypothesis_registry / pre-registration (M-107). |
| **drift monitoring** | ✅ already partial (ml_health_monitor) — wire to the gate-stack | |

## Recommended sequence (revised by review)
1. **Data reconstruction FIRST** (not just validation): finish signal_ts/provenance backfill (PR #484), remediate FORCE_CLOSED_TOXIC at the resolver (INCIDENT #95), fix batch-stamped resolved_at. *Catching errors is cheap; fixing them is the work* (reviewer).
2. **Data-validation gates** (pandera) as CI on the pick/feature pipeline — highest-ROI MLOps.
3. **ML strictly as a FILTER** on the one proven sleeve (H-103) + already-significant-alpha candidates — never a new predictor on no-edge classes (matches the repo's prior "rule-first, ML-as-filter" guidance).
4. **Mandatory pre-promotion gates** for any ML model: #111 attribution (alpha t≥2, IR≥0.10) + DSR/PBO + purged-embargoed CV. Pre-register (M-107).
5. **Explicit ban (review addition):** do NOT use LLM/tournament outputs as ML features until their knowledge-cutoff leakage mechanism (KTD-Fin) is controlled — else you bake memorization into the model.
6. **Defer Optuna** until 1-2 are done and sample sizes grow.

## Single highest-ROI addition: data-validation gates (pandera). Single thing to AVOID: PyTorch/TensorFlow (and any new HPO/model family before data hygiene + attribution pass on existing tree pipelines).

## Review dissent (recorded)
cloudflare-llama argued against being "too dismissive of neural nets" + wanted more quantitative
metrics + interpretability discussion. Noted but outweighed: the other 3 reviewers + the n=48/no-edge
reality make DL a clear overfit risk here. paid-mode flagged H-103's capacity may be too small for
ML-as-filter to move PnL enough to justify infra — a real caveat to weigh before building.

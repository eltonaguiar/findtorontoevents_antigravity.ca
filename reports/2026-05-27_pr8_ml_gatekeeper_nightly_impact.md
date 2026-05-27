---
title: "PR #8 Impact Analysis — Nightly ML Gatekeeper A/B Training"
date: 2026-05-27
pr_branch: fix/ml-gatekeeper-ab-nightly
priority: highest single-line ROI per MiMo v2.5 Pro audit
---

# PR #8 Impact Analysis

## What this PR does

Adds two daily cron triggers to `.github/workflows/ml-gatekeeper-train-ab.yml`:
- **19:07 UTC** → trains OLD arm (gatekeeper_old.joblib, with leakage features as baseline)
- **19:17 UTC** → trains NEW arm (gatekeeper_new.joblib, leakage-purged via `ML_GATE_DROP_LEAKAGE=1`)

Updates the "Resolve arm name" + "Verify bundle stamping" steps to derive `drop_leakage` from `github.event.schedule` when the trigger is `schedule` rather than `workflow_dispatch`.

## Why this matters — the gap discovered

Per the codebase audit during this session:

- `ml-gatekeeper-train-ab.yml` exists but **has never run** (0 runs in workflow history)
- `ml-gatekeeper-ab-bootstrap.yml` exists but **has never run** (0 runs)
- Result: `ml_gatekeeper/models/` on `origin/main` contains only `training_report.json`, `strategy_router.json`, `drift_baseline.json` — **no actual model bundles** (`gatekeeper_old.joblib`, `gatekeeper_new.joblib`)
- Therefore `score_active_picks_ab()` is **silently falling back to single-model scoring** since the function's bootstrap comment explicitly says "Until both files exist, score_active_picks_ab() falls back to single-model scoring and the entire A/B infrastructure (ab_analysis.py, rollback tracker, …) does nothing."

The A/B infrastructure was built but never deployed.

MiMo v2.5 Pro identified `ML_GATE_DROP_LEAKAGE=1` as the **single highest-ROI single-line fix** in the entire ML stack. This PR doesn't change a one-line flag — the flag already exists. **It makes the existing infrastructure actually run.**

## Evidence of the impact

Per the existing codebase (verified):
- `ml_gatekeeper/gatekeeper.py:80` documents 4 leakage features (`forward_wr`, `strat_fwd_wr`, `eb_forward_wr`, `age_hours`) that are downstream proxies of the outcome being predicted
- `tools/retrain_gatekeeper_clean.py:12` says: *"Set `ML_GATE_DROP_LEAKAGE=1` and workflow_dispatch again"*
- MiMo audit: high-confidence picks (≥0.9) have 14.4% WR; mid-confidence picks (0.5-0.6) have 60.3% WR. **Calibration inversion is severe.**
- Drop the 4 leaky features and the calibration should rotate back to normal monotonic behavior.

## Why a cron rather than a one-shot dispatch

A one-shot dispatch would train the bundles once, but they'd age. Models trained on labels from week N degrade against the live distribution of week N+1, N+2, ... (concept drift). Nightly retraining keeps both arms fresh AND lets the existing A/B router (PR #921) actually do its job — compare NEW vs OLD week-over-week and accumulate the z-test evidence (PR #924 Phase D).

## Blast radius

| Layer | Impact |
|---|---|
| **Workflow file** | Only `ml-gatekeeper-train-ab.yml` — 2 new cron lines + 9 lines of step logic |
| **Models trained** | 2 bundles committed per day under `ml_gatekeeper/models/` (~1-5 MB each) |
| **Downstream** | `score_active_picks_ab()` activates on next audit-dashboard cron tick after first successful bundle commit (so NEW arm starts scoring picks within ~24h) |
| **Reversibility** | Trivial — delete the schedule block, workflow goes back to dispatch-only |
| **CI cost** | 2× ~10 min training jobs per night = ~600 GH Actions minutes/month |

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Bundle file size grows the repo | `.gitignore` already covers most `.joblib`; bundles are small (~1-5 MB). Track if month-over-month |
| Two arms train back-to-back at 19:07 + 19:17 — concurrency clash | Workflow has no `concurrency:` group; arms train in distinct jobs. Safe. |
| First nightly run after merge writes commits but A/B router doesn't read them until cache cycle | Acceptable lag (~1 hour); document in audit-dashboard run notes |
| Leakage-purged model could underperform on legacy in-sample WR metrics | This is THE POINT — the A/B analysis (PR #921) measures NEW vs OLD on truly-out-of-sample picks. If NEW loses, we learn. |
| If `train_gatekeeper.py` breaks at the env-var read | Verified: `ml_gatekeeper/gatekeeper.py:91` defines `_drop_leakage_enabled()` reading `ML_GATE_DROP_LEAKAGE`. Safe. |

## What this does NOT do

- Does NOT activate `score_active_picks_ab()` as primary scorer (that needs separate wiring in audit-dashboard cron — out of scope; tracked separately)
- Does NOT retroactively re-score the 84+ days of stale `signal_outcomes` table (P0 — needs MySQL access)
- Does NOT fix the 4-feature leakage in models trained before this PR
- Does NOT change confidence weighting in `smart_picks_engine.py` (`_w_conf=0.10` was already lowered from 0.30 in commit `5d411e848`)

## Verification plan (post-merge)

1. **24h after merge**: confirm 2 cron runs fire (one for each arm), look for commits like `feat(ml-gate-ab): bootstrap gatekeeper_old + gatekeeper_new bundles [skip ci]`
2. **48h after merge**: confirm `ml_gatekeeper/models/gatekeeper_old.joblib` and `ml_gatekeeper/models/gatekeeper_new.joblib` exist on `origin/main`
3. **7 days after merge**: run `python tools/operator_status_check.py` and verify `ab_router_effect()` is no longer reporting fallback-to-single-model
4. **30 days after merge**: pull `audit_trail/data/ab_analysis_results.json` (created by ab_analysis workflow) — if NEW > OLD by ≥5pp WR on common picks, promote NEW to primary

## Related (out of this PR)

- ML_GATE bootstrap workflow_dispatch already triggered this session (run `26489636249`) to immediately bootstrap both bundles before the nightly cron kicks in
- Phase 1.2 MySQL relabel SQL (`tools/relabel_closed_picks_mysql.sql`) — gates the post-merge data quality
- `tools/retrain_gatekeeper_clean.py` already exists; nightly cron supersedes manual invocation

## Peer review status

To be reviewed via `/swarm-second-opinion` (deepseek + xai) before merge. See PR comments for swarm output.

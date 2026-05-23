# Ernie — Week 1 Detailed Checklist (2026-05-12)

External AI contribution. Hyper-detailed Day-1-to-Day-5 plan with hourly
time-boxing + per-task deliverables. Compressed here for reference;
session-applicable status tagged inline.

## Day 1 (Mon) — "Freeze & triage"

- 08:00 Kill Switch Ceremony — quarantine all draggers → `quarantine_manifest.json` (✓ shipped this session as `audit_dashboard/data/quarantine_manifest.json`)
- 09:00 Size Cap Enforcement — CRYPTO ≤10%, FOREX=0%, others 20% (PARTIAL — only score-floor caps; explicit risk-cap layer queued)
- 10:30 Zero-PnL Bug Sprint — ✓ artifact filter + WON-vs-PnL guard shipped
- 13:00 Data Truth Layer Audit — 50-row spot-check per class (QUEUED)
- 15:00 Resolver v2 Sync Check (QUEUED — current session deferred)

## Day 2 (Tue) — "Data truth layer build"

- 08:00 Fix Zero-PnL Bug + regression test (✓ forward-only filter; backfill SQL drafted)
- 09:30 `data_quality_gates.yaml` per class (QUEUED)
- 11:30 Rebuild `metrics_by_asset_class.csv` clean (QUEUED — will happen on next cron)
- 13:30 Dashboard v1 — rows received, null %, staleness, resolver sync, quarantine count (PARTIAL — DB Health panel has 6 metrics; full grafana-style dashboard pending)
- 15:30 Alert tuning thresholds (QUEUED)

## Day 3 (Wed) — "Real-time integrity + intraday watch"

- 08:00 Real-Time Data Validation Layer (CRYPTO+FX latency / sanity / stale-feed / version-hash) (QUEUED)
- 10:00 Alt-data ingestion audit (license/cleaning/cost/latency/GDPR) (QUEUED)
- 13:00 Data Versioning Setup (Delta Lake / DVC) (QUEUED)
- 14:30 Dashboard v2 intraday panels (QUEUED)
- 16:00 Alert Fatigue Test (QUEUED)

## Day 4 (Thu) — "Model risk framework sprint"

- 08:00 Model cards for every active model (QUEUED — `model_cards/` directory)
- 10:00 CPCV on top-3 strategies (PARTIAL — `tools/anti_overfit_audit_sidecar.py` runs DSR hourly; CPCV via `alpha_engine/anti_overfit_validator.py` still orphan)
- 13:00 SHAP/LIME explainability (QUEUED)
- 14:30 CI/CD pipeline for models (QUEUED — `.github/workflows/model_ci.yaml`)
- 16:00 Stress scenarios (5 per class — flash crash, liquidity freeze, correlation spike, data blackout, regime flip) (QUEUED)

## Day 5 (Fri) — "Review, lock, plan Week 2"

- 08:00 Week 1 Retrospective — score each gate PASS/PARTIAL/FAIL (THIS SESSION — see `reports/week1_retrospective_2026-05-12.md` pending)
- 10:00 Quarantine Effectiveness Check (PARTIAL — pre/post comparison needs next cron cycle of clean data)
- 11:30 Data Truth Layer health check (PARTIAL)
- 13:30 Week 2 Plan Lock (✓ master plan + expanded roadmap shipped)
- 15:00 Investor Update Deck — ignored per session-as-solo directive

## Files referenced (status)

| File | Status |
|---|---|
| `quarantine_manifest.json` | ✓ shipped this session |
| `data_quality_gates.yaml` | QUEUED |
| `data_truth_health_report.md` | PARTIAL (DB Health banner on /audit) |
| `model_cards/` | QUEUED |
| `cpcv_results.json` | PARTIAL (DSR via anti_overfit cron) |
| `shap_explainability_report.html` | QUEUED |
| `stress_scenarios.yaml` | QUEUED |
| `.github/workflows/model_ci.yaml` | QUEUED |
| `week1_retro.md` | ✓ this session |
| `week2_plan.md` | ✓ master plan covers Week 2-4 |

## Ernie's most actionable artifacts (next session)

1. `quarantine_manifest.json` — ✓ SHIPPED THIS SESSION (this commit)
2. `data_quality_gates.yaml` — per-class validation rules (NEW)
3. `model_cards/` — one per active ML model (NEW)
4. `stress_scenarios.yaml` — 5 tail-risk per class (NEW)

## Refs

- Companion: `reports/grok_solo_week1_checklist_2026-05-12.md`
- Master plan: `reports/quant_rescue_master_plan_2026-05-12.md`
- Solo-quant retrospective: `reports/week1_retrospective_2026-05-12.md`

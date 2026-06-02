# Verified pilot surfacing follow-up

## What was broken

The ETF forward-pilot fix in `tools/strategy_admit.py` made the per-strategy admit artifact honest, but the broader admissibility payload and verified-edge strip were still stale. They could miss the committed pilot dashboard snapshot, report ETF lab status as `null`, and hide the best forward-pilot candidate from the main audit honesty strip.

## What changed

1. `tools/strategy_admissibility_report.py` now loads the pilot dashboard from either `reports/pilot_forward_dashboard.json` or the committed fallback `audit_dashboard/data/pilot_forward_dashboard.json`, then publishes a `best_candidate` and `candidate_sleeves` summary under `edge_surfaces.verified_lab`.
2. `alpha_engine/verified_promotion_gate.py` now uses the same dashboard fallback, fixes the ETF walk-forward alias lookup (`dual_momentum_etf`), and emits `best_forward_candidate` in `verified_edge_status.json`.
3. `audit_dashboard/dashboard_enhancements.js` now shows the best forward-pilot candidate in the audit honesty strip, including the forward count and current blockers.

## Verification

Regenerated `audit_dashboard/data/strategy_admissibility.json` and `audit_dashboard/data/verified_edge_status.json` from the updated scripts in the clean ETF branch. The refreshed payload now shows ETF dual momentum as the best forward-pilot candidate with a real walk-forward PASS and forward blockers, instead of a missing/blank pilot state.

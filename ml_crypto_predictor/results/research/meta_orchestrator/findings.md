# meta_orchestrator_researcher — first trigger watchdog target identified

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** mo_001 — Which class/source should spawn a deep-dive first?

**Result:** `rapid_fire` (n=207, PF 0.158, p=1.0) is the cleanest demote candidate.

**Routing under HANDOFF_MAP:** `rapid_fire` → `multiple_testing_researcher` (deflation) → `vol_targeting_researcher` → `transaction_cost_researcher`.

**Wire-up:** `ml_crypto_predictor/researchers/coordinator.py` extension — trigger watchdog tailing `dashboard_payload.json`.


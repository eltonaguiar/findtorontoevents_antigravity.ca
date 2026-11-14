# finpredict-v3 — Final Deliverable (2026-11-14)

Auditor subtree: `finpredict-v3` · Archive: `final_2026_11_14/finpredict-v3/`

This folder consolidates the finpredict-v3 day's work: a runnable prediction-system
data-hygiene guardian, a rigorous ML/horizon validation harness, and cross-peer
reviews. Everything is read-only/additive tooling + findings — no live pipeline code
was changed as part of the audit itself.

## Contents

| Subfolder | What's here | Status |
|---|---|---|
| `01_audit/` | `PREDICTION_DATA_HYGIENE_AUDIT.md` — verified defects in the live `dashboard_data.json` (stale crypto price, frozen phantoms, date-only seeds, null-price classes, survivorship, dead metrics) + per-class remediation plan | findings |
| `02_tools_guardian/` | Runnable guardian tooling: `pi_data_hygiene.py`, `pi_fundamental_ranker.py`, `pi_horizon_validation.py` + tests | runnable, tested |
| `03_peer_reviews/` | Peer reviews (R2, 6 peers): v1–v4, ML-audit, scratch-hippodraco, hilarious-seer + consolidated overall | review |
| `04_research_validation/` | ML validation README + horizon-harness run results (n≥60, n≥30) + harness source | evidence |
| `05_final/` | summary / verdict docs | final |
| `06_evidence/` | raw evidence manifest + live payload references | evidence |

## Verdict (bottom line)

- **No asset class / ML model is proven money-ready.** On honest intrabar numbers the
  harness shows 0/6 groups pass at n≥60 and 0/26 at n≥30. The honest answer is the
  negative result.
- **Highest-value production defects** (multi-peer-verified): PnL-unit mix bug
  (`dashboard_generator.py:8065-8072`), stale/frozen crypto prices, 11 frozen closed
  FOREX phantoms, date-only futures seeds, and target leakage in the gatekeeper
  (now masked ON by default — commit `d8c8dd25581` is on `origin/main`, needs sign-off).
- **Best remediation source**: scratch-hippodraco `QW-ALL-1..9` (implementation-ready,
  verified file:line) merged under v2's reconciliation backbone.

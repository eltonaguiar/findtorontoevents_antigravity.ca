# Bridge shows policy-clean metrics, not the friendlier raw cohort (2026-11-19)

**Scope:** `tools/build_audit_surface_truth.py`,
`audit_dashboard/audit_surface_truth_banner.js`.

## What was wrong

The "Money-ready bridge — policy-clean truth" banner on `/audit` showed
**COMMODITY PF 1.0418 / verdict WATCH** while the canonical ledger in the same
repo says **COMMODITY KILL, PF 0.1044, net −3.3%/trade (CI [−5.14, −2.03])** and
the surface-truth file's *own* `policy_clean_pf` is **0.469**.

Cause: the generator copied `verdict` and `pf` from `money_ready_verdict.json`
(a different cohort) and only carried `policy_clean_pf` as an unused extra
field; the banner rendered `pf`. A class that loses money was displayed on the
profitable side of 1.0, on a panel titled "policy-clean truth".

## Change

- `display_metrics(block, pc)` picks what the bridge **shows**:
  - if the policy-clean cohort has `n >= 20`, show `policy_clean_pf` and label
    the basis `policy_clean_net`;
  - a raw `WATCH`/`READY` verdict becomes `NOT_READY` when policy-clean PF < 1;
  - otherwise fall back to the raw figure (`pf_basis: "raw"`).
- Each class row now carries `display_pf`, `display_verdict`, `pf_basis`; the
  raw `pf`/`verdict` remain for transparency.
- The banner renders `display_pf` (falls back to `pf`).

Result for the current data: COMMODITY → **0.4691 / NOT_READY** (policy-clean),
CRYPTO → 0.258, FOREX → 0.1646 — all consistent in sign with audit3.

## Verification

`pytest tests/test_asset_class.py tests/test_audit3_coverage_alpha.py tests/test_audit3_tribunal.py -q`
→ **154 passed**. `display_metrics` spot-checked on COMMODITY, a thin cohort
(n=5, keeps raw), and a genuinely strong cohort (keeps WATCH, basis policy-clean).

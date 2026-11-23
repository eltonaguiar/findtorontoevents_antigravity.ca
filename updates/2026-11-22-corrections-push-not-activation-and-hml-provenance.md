# Corrections to the 2026-11-22 record

Two corrections, preserved at the operator's explicit request
("Your catch that pushing does not activate a schedule was correct; keep it in the record").

## 1. Pushing does NOT activate a `schedule:` trigger

An earlier session claim that "pushing activates the cron" was **WRONG**.

- GitHub fires `schedule:` triggers only from the workflow file as it exists on the
  repository's **default branch**. A pushed branch, even a pushed PR branch, does not
  activate it.
- **Pushing alone did not activate the measurement.** The merge to `main` was what was
  required.
- **Status:** the merge has NOT happened. Branch `m2-residual/fx-cost-overlap-scheduler`
  (`692d30d7e62`) is pushed, but `origin/main` (`4e1adc252fd` at the time of writing) does
  **not** contain `.github/workflows/fx-cost-overlap.yml`. The weekday London/NY-overlap
  FOREX cost measurement is therefore **still inert**, and FX mean-reversion remains
  UNKNOWN.
- The authorised merge was attempted but **STOPPED**: `git merge-tree origin/main
  692d30d7e62` reports **18 conflicting paths** (including
  `alpha_engine/production_scanner.py`, `alpha_engine/money_ready_verdict.py`,
  `alpha_engine/audit3_tribunal.py`, `alpha_engine/cost_gate.py`,
  `.github/workflows/audit-dashboard.yml`, `.github/workflows/sign-coherence-gate.yml`,
  `reports/claim_register.json`, `audit_dashboard/data/audit3_ledger.json`). Nothing was
  forced and nothing was bypassed. The branch is 44 commits ahead of a merge base
  (`d1172ea42`) that is far behind current `main`, so the diff is 862 files, not 5.
- **Retry path:** rebase/cherry-pick only the five scheduler files onto current `main` on a
  fresh branch, then re-open the PR.

## 2. The HML pre-registration was operator-requested

`docs/preregistration/HML_VALUE_TEST_2026-11-22.md` was **requested by the operator at 18:40**
on 2026-11-22. An earlier session note **incorrectly** described it as an "unrequested scope
deviation". That characterisation was false and is corrected here.

It is a **pre-registration with no result claimed**. It was committed as `8df189f317` on
`prereg/hml-value-test-2026-11-22` and opened as **PR #1065**. It was deliberately **not
merged**: it awaits human review of the pre-declared kill rule (OOS annualised net return on
committed capital <= 4.3%, or one-sided 95% upper bound <= 4.3%).

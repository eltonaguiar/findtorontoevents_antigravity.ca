# Fix: Unified Audit Dashboard “Commit updated data” bash heredoc failure

## Symptom

GitHub Actions run **24491360509** (and similar) failed at **Commit updated data** with:

- `here-document at line 73 delimited by end-of-file (wanted 'PYEOF')`
- `syntax error: unexpected end of file`

The job had already created a `[skip ci]` commit; the next shell lines never ran reliably, so **push/deploy could be skipped or the step exited2**.

## Root cause

The post-rebase **publish consistency** check used an inline `python3 <<'PYEOF'` heredoc **inside a nested `if`/`for` block**. In GitHub Actions `run: |` blocks, YAML strips only the **minimum** indentation shared by all lines. Lines inside the inner block keep **extra leading spaces**, so the closing `PYEOF` line was **not** at column 0. Bash treats a quoted heredoc delimiter as literal: the closing word must start at the beginning of the line (unless using `<<-` with tab-indented bodies). The delimiter was never matched → script truncated → **exit 2**.

This is **not** a non-crypto logic bug; it is a **shell/YAML interaction** that blocked the whole publish loop. It could leave operators thinking the “non-crypto pipeline is fried” when the real failure was **commit/push**.

## Fix

- Added `.github/scripts/verify_dashboard_publish_consistency.py` with the same checks (payload vs `dashboard_data.json`, attribution fields, `portfolio_uniqueness`).
- Replaced the inline heredoc in `.github/workflows/audit-dashboard.yml` with `python3 .github/scripts/verify_dashboard_publish_consistency.py`.
- Registered the script in the workflow’s `push.paths` so changes auto-trigger the dashboard workflow.

The script also **stderr-warns** if `summary.non_crypto_performance` is missing (empty dict), which helps spot generator regressions without failing the step.

## Verification

- `python .github/scripts/verify_dashboard_publish_consistency.py` from repo root exits 0 when `audit_trail/data/dashboard_payload.json` and `audit_dashboard/data/dashboard_data.json` match and checks pass.

## Live /audit JS

- `VERIFY_REMOTE=1 npx playwright test tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"` passed against `https://findtorontoevents.ca/audit/` (no critical `pageerror` / console errors in the test’s filters).

## Silent CI failures (non-crypto and friends)

Several audit pipeline steps use **`continue-on-error: true`**, including **non-crypto consensus**, **non-crypto quality enhancer**, **non-crypto pick audit**, and **Hyro** substeps (with a follow-up warning step). Failures are aggregated into **`audit_trail/data/pipeline_health.json`** and the **“Audit Pipeline Health”** job step summary. For operational checks:

1. Open the workflow run → **Build pipeline health report** log → `degraded_steps`.
2. On the built site, inspect embedded payload or download `dashboard_data.json` and read `metadata` / freshness if exposed.

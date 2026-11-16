# 2026-11-16 — GitHub Actions queue audit and workflow guards

## What was broken / observed
- **Ghost queued runs (queue blocker):** 51 runs in `queued` state dating 2026-08-07 → 2026-11-11 (e.g. `robust-edge-miner` 32203529158, `Audit Hourly Update` 43097722505, duplicate stale `ALPHA ENGINE - Dynamic Runner` entries). `gh run cancel` failed with `Cannot cancel a workflow run that is completed`; REST `POST /actions/runs/{id}/cancel` returned 409 `Cannot cancel a workflow run that has not been queued yet`. Runs appear as queue ghosts not removable via CLI/API from this environment.
- **Anomalous latest failures on `main`:** push-triggered runs with **0 jobs / no logs** on commit `a14c99440b4ba24e584d1cdb525b4368e8db5016`:
  - `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` — run [43788940508](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43788940508) (`total_count: 0` jobs)
  - `.github/workflows/mysql-q001-sync.yml` — run [43788941580](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43788941580) (`total_count: 0` jobs)
  Both workflows’ configured triggers do not include `push` (`ml-gatekeeper-ab-bootstrap` is `workflow_dispatch`-only; `mysql-q001-sync` is `schedule` + `workflow_dispatch`). YAML validated locally as parseable.
- **Latest-run failures (job-execution):** none found on `main` at check time; in-progress scheduled runs appeared healthy. `Discord Bot  Persistent` run 43745604081 was long-running in its designed 5h50m bot step (not treated as hung).

## What changed
- Added defensive job-level event guards (no trigger changes):
  - `ml-gatekeeper-ab-bootstrap.yml`: `if: github.event_name == 'workflow_dispatch'` on `bootstrap` job.
  - `mysql-q001-sync.yml`: `if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'` on `mysql-sync` job.
- **Intent:** prevent accidental execution if GitHub ever dispatches an unexpected event type; harmless when triggers behave correctly. **Note:** this does not retroactively clear existing 0-job ghost/failure records and may not prevent platform-level 0-job startup anomalies that occur before job evaluation.

## Downstream impact assessment (`findtorontoevents.ca/audit`)
- **No direct impact on `/audit` pipeline expected.** Neither workflow is listed in `.github/workflows/audit-dashboard.yml` push-path dependencies (push trigger removed 2026-05-19; cron/dispatch drives refresh) and neither writes `audit_dashboard/data/dashboard_data.json` or other audit dashboard payloads consumed by the live audit site.
  - `ml-gatekeeper-ab-bootstrap.yml` is manual-only and commits model bundles to `ml_gatekeeper/models/` only when explicitly run.
  - `mysql-q001-sync.yml` is a dated/manual DB sync that writes reports (`reports/mysql_q001_sync_*.json`); not part of audit dashboard generation/deploy steps.
- **Verification after merge:** confirm next `Unified Audit Dashboard` cron/dispatch run succeeds and `https://findtorontoevents.ca/audit/` data freshness is unchanged; no audit dashboard code/data paths modified by this change.

## How verified
- `gh run list/view/api` checks for queued/in-progress/completed state, job counts, and workflow histories.
- Local YAML parse check: both workflow files load via `yaml.safe_load` with expected `on` triggers.
- Git diff limited to the two workflow files + this doc.

## Revert plan
If these guards cause unintended skips on legitimate runs:
```bash
git revert <commit_sha>
# or manually remove the added `if:` lines from:
# - .github/workflows/ml-gatekeeper-ab-bootstrap.yml (jobs.bootstrap.if)
# - .github/workflows/mysql-q001-sync.yml (jobs.mysql-sync.if)
git add .github/workflows/ml-gatekeeper-ab-bootstrap.yml .github/workflows/mysql-q001-sync.yml
git commit -m "revert: remove gha workflow event guards"
git push origin main
```

## Remaining manual follow-up
- **Ghost queued runs:** require Actions UI (logged-in) or GitHub Support; not cancellable via `gh`/API in observed state.
- **0-job anomaly runs:** inspect in GitHub UI for startup/registration diagnostics if they recur on future pushes; consider workflow re-registration/renaming only with explicit intent and after confirming no hidden trigger source.

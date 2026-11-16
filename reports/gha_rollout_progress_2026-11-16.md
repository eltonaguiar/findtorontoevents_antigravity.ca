# GHA Hygiene Rollout — Progress

**Date:** 2026-11-16 (ongoing)
**Owner:** ghactions-v4 / meituan-longcat-2-5
**Design:** reports/gha_rollout_approach.md

## Result

| Metric | Before | After |
|--------|--------|-------|
| Active workflows | 356 | 356 |
| Missing concurrency | 161 | **1** (`_dynamic-runner-template.yml`, no triggers — doc stub, intentionally left) |
| Missing/incomplete timeout | 65 | **0** |

## Batches landed (all on origin/main)

| Batch | Scope | Files | Commit |
|-------|-------|-------|--------|
| Canary + A | 2 canary + hourly timeout-only + */15 heavy backtest | 5 | `9c1f5138ea4` |
| B/C/D | */2h, */4h, */6h, */12h | 43 | `a0a0d9e0304` |
| E/F | daily + weekly | 80 | `d49a6ca750a` |
| G | non-cron / deploy / one-shot | 34 | `85faf20d0b8` |
| H | per-job timeouts (multi-job) | 11 | `a61d1da733c` |

Plus earlier: 29 high-frequency workflows (prior sessions).

## Conventions applied
- `concurrency.group = ${{ github.workflow }}-${{ github.ref }}`
- `cancel-in-progress: true` for read-only scanners; **false** for workflows that push/deploy (so a superseded run finishes its push)
- `timeout-minutes`: 30 default; 90 for heavy backtests; per-job for multi-job workflows
- Helper: `tools/gha_add_hygiene.py` (`--timeout`, `--cancel-in-progress`), `tools/gha_add_job_timeout.py`
- Fixed helper bug: step-level `timeout-minutes` (8-space indent) no longer masks job-level absence

## Reusable workflow (Phase 4) — CANARY landed

- `.github/workflows/gha-scan-job.yml` — `on: workflow_call`, inputs `python-version`, `pip-packages`, `run-command` (required), `commit-paths`, `commit-message`, `fetch-depth`, `timeout-minutes`, `pre-run`; secrets `GH_PAT`, `MYSQL_PASSWORD`, `FRED_API_KEY`; output `changed`. Bakes in the repo's DB/FRED env and `assert_no_conflict_markers.sh` + `safe_push.sh`.
- Canary conversions (commit `7a14df40ecc`): `consensus-outcome-tracker.yml`, `adaptive-trust-tuner.yml`.
- **Gate:** observe 3–5 scheduled runs of both canaries before any mass conversion (design §2.4). Rollback = revert `7a14df40ecc`.
- 39 simple conversion candidates identified (checkout + setup-python + pip + ≤3 run steps, no conditionals); full 181-candidate list in the design doc.

## Remaining
1. `_dynamic-runner-template.yml` — no triggers, documentation stub; leave as-is.
2. ~~Batch I: 2 static group collisions~~ **VERIFIED 2026-11-16: not collisions.** `edge-stability-shared` (edge-stability-daily + edge-stability-refresh, same job on two schedules) and `movies-database-refresh` (4 movie workflows that all write the same DB) are deliberate cross-workflow serialization. Left unchanged.
3. Observe post-rollout: confirm no new failures/queue growth (cron + actions-failure-guardian).
4. Reusable `gha-scan-job.yml` — canary first.
5. Peer PRs: ghactions (ETF SHORT gate), ghactions-v3 (commit hardening).
6. QA Market Validation: TIINGO + TWELVE_DATA secrets (GitHub UI).
7. 51 phantom queued runs (GitHub Support).

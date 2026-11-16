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

## Remaining
1. `_dynamic-runner-template.yml` — no triggers, documentation stub; leave as-is.
2. Batch I: 2 static group collisions (`edge-stability-daily`/`edge-stability-refresh`, `fetch-movies*`) — verify whether they actually collide.
3. Observe post-rollout: confirm no new failures/queue growth (cron + actions-failure-guardian).
4. Reusable `gha-scan-job.yml` — canary first.
5. Peer PRs: ghactions (ETF SHORT gate), ghactions-v3 (commit hardening).
6. QA Market Validation: TIINGO + TWELVE_DATA secrets (GitHub UI).
7. 51 phantom queued runs (GitHub Support).

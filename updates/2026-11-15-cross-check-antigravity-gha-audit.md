# Cross-check of the Antigravity 14-day GitHub Actions audit (2026-11-15)

Antigravity scanned 366 workflows over 14 days (`audit_gha_14d.py` →
`audit_14d_report.json`) and dispatched three subagents. This cross-checks each
claim against the live API and the actual `main` tree.

## Their claims vs verified reality

| claim | verdict | evidence |
|---|---|---|
| "10 unresolved `failure` workflows" | **inflated** | 5 of the 7 named had a **success later the same day**: `algorithm-competition-refresh` (success 11-15 08:48, last failure 11-08), `torontoevent-algorithm-refresh` (08:48 / 11-08), `stale-branch-cleanup` (08:48 / 11-09), `weekly_score_quartile_spread` (08:48 / 11-09), `pead-shadow-collector` (08:39 / 11-13). Only `verified-pilot-daily` (never green) and `mirror-site` were genuinely unresolved. |
| "3 scheduled workflows haven't run in 14 days" | **1 of 3 false** | `model-picks-emission` ran **successfully at 09:16** today (daily `22 1 * * *`). `mysql-q001-sync` uses `0 8 24 5 *` = **once a year** (May 24), so not running in 14 days is by design. Only `poc-picks-checkpoint` is genuinely inert — its crons are hardcoded one-offs (`0 21 18 7 *`, `0 21 20 7 *` = 2026-07-18/20). |
| "duplicate YAML keys across workflows" | **not reproducible** | 0 duplicate keys across all **362** active `.github/workflows/*.yml` (custom loader that reports duplicate mapping keys). 0 files with a missing/empty `on:` block. |
| `audit_gha_14d.py` / `audit_14d_report.json` | **not in the repo** | Neither file exists anywhere in the tree, so the 366-workflow result cannot be re-run or audited by anyone else. Every number in this doc was re-derived from the API instead. |
| #797 fixed the pilot, closed as superseded by `742252a0d62` | **correct** | `742252a0d62` ("repair verified pilot, corrupted scripts, …", 2026-11-15 04:14 -0500) **is an ancestor of `origin/main`**. It adds `pymysql` to the install step and wraps `_write_basket_to_db` in `try/except Exception` → `[DB] Skipping DB write (unavailable in environment)`. |

### The actual pilot failure (confirmed, since fixed)

Run 43696245567 (08:48, sha `ac15d8174` — **before** the fix):

```
1 FAILED STEP(S):
  rc=1  .../python3 verified_strategies/paper_pilot/forex_carry_g10_pilot.py --one-shot --write-db
    stderr: tools/db_env.py line 123, in get_stocks_creds
    ValueError: no DB password found — set DB_PASSWORDS_JSON (canonical) or any of:
      MYSQL_PASSWORD, DB_STOCKS_PASSWORD, DB_PASS_STOCKS, DB_PASSWORD
```

Root cause: `get_stocks_creds(*, raise_on_missing: bool = True)` raises by default,
and the workflow passes **no DB credentials** to the step (only `VERIFY_SKIP_FRED`
and `VERIFIED_PILOT_WALKFORWARD`). With the post-fix `try/except`, the paper pilot
now degrades to "skip DB write" instead of failing the job.

## What they missed — fixed here

`branch-large-file-dup-guard` was the single largest source of bogus check
results: **20 cancelled of 22 runs**, and it showed `fail` on PR #790/#794. Its
`concurrency: group: branch-large-file-dup-guard` puts **every non-main branch in
one group**, so concurrent branches cancel each other's checkout mid-run
(observed: `Fetch branch refs → ##[error]The operation was canceled`).

Fix: `group: branch-large-file-dup-guard-${{ github.ref }}` — cancellations now
only apply within one branch, so a PR's check reflects that PR.

## Still open / flagged, not changed here

- `poc-picks-checkpoint.yml` — dead one-off crons; harmless but permanently inert.
  Changing its schedule is a product decision, so it is only flagged.
- `forex-agent.yml` + `forex-smart-picks.yml` are `disabled_manually` — financial
  workflows switched off; needs an owner decision.
- Antigravity's PR **#794** is `CONFLICTING`/`DIRTY` (+528/−7, 10 files) and its
  only failing check is the guard fixed above.
- `mirror-site`: my #795/#801 fixes are merged; verification still in flight.

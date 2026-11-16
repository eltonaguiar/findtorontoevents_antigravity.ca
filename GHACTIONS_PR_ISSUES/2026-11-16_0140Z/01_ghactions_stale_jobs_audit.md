# GitHub Actions Stale / Failed / Queue Audit
- Date: 2026-11-16T01:40Z
- Repo: eltonaguiar/findtorontoevents_antigravity.ca
- Method: GitHub REST API (367 workflows enumerated; latest run + conclusion per workflow) + log inspection.

## Summary of Health
- 330 / 367 workflows have a **successful latest run**. Pipeline is fundamentally healthy.
- 6 workflows have a latest run that ended in **failure**, 1 in **cancelled** — see below.
- High-frequency guardians are green: `actions-failure-guardian` (30-min), `db-freshness-guardian` (hourly), `regime-terminal` (30-min), `gha-stale-workflows-audit` (daily 05:30), `audit-hourly-update` (hourly).

## 1. Failed jobs with NO subsequent successful run (stale) — priority order

| Workflow | Last run | Verdict |
|---|---|---|
| **Model Picks Emission (finpredict-v4 tactical allocation)** | 2026-11-16T01:26:58Z FAILURE (daily 01:22 cron) | **Active daily job, stale failure.** Root cause in logs below. |
| Mermaid Test Deploy | 2026-11-14T18:23Z FAILURE (branch `wiring`) | Test/one-off branch deploy; push 403 auth error. Not on main. |
| Audit Frontend Manifest | 2026-11-15T22:56Z CANCELLED (branch `fix/etf-short-gate-vix-combos`) | Branch-only cancellation. Low impact. |
| ML Gatekeeper A/B Bootstrap | 2026-05-27 FAILURE | Dead ~6 months — cleanup candidate. |
| DB Freshness Check (Legacy Manual) | 2026-05-23 FAILURE | Legacy — cleanup candidate. |
| MySQL Q-001 — Create picks table + sync from JSON | 2026-05-24 FAILURE | One-time migration — cleanup candidate. |
| DB Secret Scan | 2026-06-05 FAILURE | Dead ~5 months — cleanup candidate. |

### Model Picks Emission — root cause (run 43786331675)
Step `Run tactical allocation emitter` (`2026-11-15_AM_plan/finpredict-v4/05_simulation/emit_tactical_picks.py`):
```
1 Failed download: ['GLD']: OperationalError('database is locked')
Traceback ... emit_tactical_picks.py line 127 in <module>
  line 64 in calc
  pandas ... IndexError: single positional indexer is out-of-bounds
##[error]Process completed with exit code 1.
```
Cause: yfinance download of **GLD** failed (sqlite `database is locked`), returning an empty frame; `calc()` then indexes a positional row that doesn't exist → `IndexError`. The script has **no graceful handling for failed downloads**, so one failed ticker kills the whole daily emission. It is the only failure since the last success on 2026-11-15T09:16Z.

## 2. Jobs that haven't run in a long time (silent / never-ran)
Verified via per-workflow API (no recent run):
- **Fast Stocks Competition High Frequency Scanner** (`fast-stocks-competition.yml`, cron `0 14,18 * * 1-5`) — **zero runs ever**. Silent scheduled job; last expected weekday trigger was 2026-11-13 14:00/18:00 UTC and nothing occurred. Investigate trigger/filename mismatch.
- Never-ran (no run ever) that are manual/dispatch-only by design (not actionable): Clear Channel Command, Closed Picks Command, Dynamic Runner Template, WSL Runner Manager, DB Credentials Test, Deploy Strategy Bundle, Resolver Step 5-6/7, MySQL Dedup Fix, RL Agent (PPO), Test Fast Variants, REAL 2-Hour Challenge, Fix Ghost Cards, Deploy MOVIESHOWS3 Hotfix, Deploy FC API Hotfix, Deploy fc/api/.env.
- Overdue-but-expected infrequent (all successful when last run, within cadence): monthlys weekly jobs, `Alpha Engine - Weekly Validation Suite` (6d), `Beta Portfolio Refresh (monthly)` (14d), `ML Monthly Full Retrain` (14d), `UEPS Value Resolver Quarterly` (45d).

## 3. Jobs holding up the queue / churn
- **ALPHA ENGINE - Dynamic Runner (Cloud or Local)** — the dominant noise + queue consumer. Cron `18,48` (every 30 min). Of ~7 recent runs, **every one was cancelled**, at the workflow's 60-min `timeout-minutes` budget. Evidence (run 43760178670): job `alpha-engine` started 21:08:13Z, ran exactly 60 min, killed 22:08:28Z → `cancelled`. The `production_scanner.py` cycle exceeds 60 min, so the runs **hit the timeout and die before completing their push**, every cycle. The YAML comments even note push failure is non-fatal and “data self-heals next cycle” — meaning it re-runs and re-dies. This is effectively a perpetual re-run loop consuming the queue. Currently: 1 run in_progress (01:00Z) + 1 pending (01:22Z).
- Other currently queued/in_progress at audit time: `multi-asset-scanner` (queued), `Unified Audit Dashboard` (pending), `Crypto Signal Engine` + `Gainer Predictor Scanner` (in_progress). Normal, but add to the total concurrency load.

## Recommended actions
1. **Model Picks Emission (fix, high value):** wrap each yfinance download in `emit_tactical_picks.py` (`calc()` / line ~64, call site line 127) in try/except; on failed download skip that ticker (log + continue) instead of indexing an empty frame. Re-run the workflow to confirm success. This is the only stale *main* failure.
2. **ALPHA Dynamic Runner:** raise `timeout-minutes` above the real cycle (e.g. 90–120) OR split the pipeline, so runs stop dying at 60 min. Also confirm the recurring cancellations aren't a concurrency-group interaction killing queued runs.
3. **Cleanup (low risk):** disable/delete dead workflows — ML Gatekeeper A/B Bootstrap, DB Freshness Check (Legacy Manual), MySQL Q-001, DB Secret Scan, Mermaid Test Deploy.
4. **Investigate:** Fast Stocks Competition High Frequency Scanner has never triggered despite a weekday cron.

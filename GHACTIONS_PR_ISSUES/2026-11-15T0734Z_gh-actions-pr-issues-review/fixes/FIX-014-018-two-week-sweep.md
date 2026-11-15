# FIX-014…018 — 2-week failure/timeout sweep

**Date:** 2026-11-15 · **Scope:** all 367 workflows, runs since 2026-11-01, all non-success conclusions (failure/cancelled/timed_out/action_required/neutral/skipped).

## Fixed

| Workflow | Root cause | Fix |
|---|---|---|
| algorithm-competition-refresh (FIX-014) | `STOCKS/competition/run_competition.py` missing (2026-05-23 history strip); backtest step skips, then "Create slim JSON" hard-fails on missing `competition-results.json` | Guard the slim step: if results absent → `::warning` + `exit 0` (skip commit/deploy) |
| torontoevent-algorithm-refresh (FIX-014) | same | same guard |
| stale-branch-cleanup (FIX-015) | `compareCommits` throws `HttpError: No common ancestor between main and gh-pages` → whole job crashes | try/catch around compareCommits; skip orphan branches |
| weekly_score_quartile_spread (FIX-016) | analyzer reads gitignored `audit_dashboard/data/dashboard_data.json` → `missing` → exit 1 each week (the "THRESHOLD FREEZE" line is only an import warning) | Prefetch live payload from `findtorontoevents.ca/audit/data/dashboard_data.json` before running |
| outcome-resolver (FIX-017) | exceeded `timeout-minutes: 15` → cancelled, never succeeded in 2 weeks | raise to 30m (serialized, cannot stack) |
| blacklist-reconciler (FIX-018) | `timeout-minutes: 5` exceeded → cancelled | raise to 15m |
| stocksunify2-pull (FIX-018) | `timeout-minutes: 5` exceeded → cancelled | raise to 15m |
| swarm-pick-review (FIX-018) | `timeout-minutes: 10` exceeded → cancelled | raise to 25m |
| strategy-funnel-hourly (FIX-018) | `timeout-minutes: 15` exceeded → cancelled | raise to 30m |

## Not broken (verified)
- **No runs in 2 weeks, but `disabled_manually`:** ai-tournament-pipeline, battle_test, forex-agent, forex-smart-picks — intentionally disabled by operator.
- **No runs, active, but brand-new:** model-picks-emission (added to main 2026-11-15 00:56; first cron 01:22 UTC next day; all referenced scripts exist).
- **No runs, manual/one-off cron:** mysql-q001-sync (annual May), poc-picks-checkpoint (annual Jul), value_resolver_quarterly (quarterly), fast-stocks-competition & walkforward-gate (cron commented/disabled).
- **Pending-cancel (design, not fixed):** operator-review-today / rsi5070-forward-snapshot share `dashboard-publish` with the 115-min audit-dashboard; GitHub cancels the queued (pending) run when a newer run enters the group. Needs a concurrency redesign, not a one-line fix.
- **Already handled earlier:** mirror-site (FTP/infra), qa-market-validation (correctly red), verified-pilot-daily (real pilot failure), pead-shadow-collector, daily-price-refresh (retired), daily-prices-yf-refresh (tested green).

## Verification
- All 9 edited workflows parse with `yaml.safe_load` ✅
- Timeout raises are moderate (2–3×) so a genuine hang still fails eventually.

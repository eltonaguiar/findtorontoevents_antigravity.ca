# Notes — Actions health (detail)

Source: GitHub REST API, unauthenticated, 2026-11-14 ~16:20Z. 12 pages × 100 runs = **1,200 runs
scanned**, spanning 11:18Z–16:22Z, yielding **185 distinct workflows** (of 365 registered).

## Aggregate of last-run conclusions (185 workflows)
success 163 · failure 7 · cancelled 4 · in_progress 10 · skipped 1.

## Failures (7)
| Workflow | Last run (UTC) | Failing step |
|---|---|---|
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 16:19 | (step UNVERIFIED — logs admin-only) |
| Sports endpoint smoke + Playwright | 16:18 | (UNVERIFIED) |
| ALPHA ENGINE FAST — Tighter TP/SL | 16:10 | (UNVERIFIED) |
| Signal Tracking & Validation - Beat the Market | 16:01 | (UNVERIFIED) |
| CI Tests | 14:37 | (UNVERIFIED) |
| robust-edge-miner | 12:43 | (UNVERIFIED) |
| Mirror: findtorontoevents.ca ↔ torontoevent.net | 12:11 | (UNVERIFIED) |

## Independently probed failures earlier today (per-workflow API)
- **ALPHA ENGINE - Live Autonomous Scanner** — run 43603342689, failure 14:09Z, step
  `Full cycle (validate + generate + tweak)`.
- **Daily Prices yfinance Refresh** — run 43521235051, failure; step
  `python3 tools/refresh_daily_prices_yf.py --days 30`. Also failed 2026-11-12 (two consecutive nights).

## Cancelled (0 jobs executed)
Unified Audit Dashboard at 11:14Z, 14:14Z, **16:14Z** (3 of the last 10 scheduled hours);
Outcome Resolver 16:19Z; Academic Strategies Daily 13:00Z; STOCKSUNIFY2 daily-stocks pull 13:10Z.
Cancelled-while-queued runs report `jobs=[]` — they never consumed a runner. Net effect:
~70% of hourly publishes complete.

## Audit-critical workflows: healthy
Hyro daily (13:37Z), Hyro Quan Bridge (05:42Z), ETF Emitter (12:16Z), Bond Agent (Nov 13 14:33Z),
Commodities Agent (Nov 13 20:01Z), DB Freshness Guardian (15:01Z), Asset Class Freshness Watchdog
(13:35Z), Money-Ready Registry Gate (14:37Z), Money-Ready Verdict Snapshot (06:22Z), ML Gatekeeper
Train A/B (Nov 13 19:16Z), Pick Funnel nightly (04:05Z), Consensus Outcome Tracker (15:33Z).

## Warnings
Workflows emit `::warning::` annotations (freshness tripwires for anti_overfit / walkforward /
ma_strategy; PF-reconciliation divergence). Reading annotation bodies requires repo-admin access →
**UNVERIFIED**. The tripwire list notably **omits** `hyro_pick_performance.json`, which is exactly
the file that went 157h stale.

## Not verified
- 180 of 365 workflows (daily/weekly/monthly; no run in the 5h window). Their last-run status is
  **UNVERIFIED** — the unauthenticated API budget (60 req/h) cannot cover 365 per-workflow calls.
- Root causes of the 7 failures (logs are admin-only; `actions/runs/{id}/logs` returned HTTP 403).

# Dormant workflow triage: 62 flagged, 3 disabled

**Date:** 2026-11-25 · **Method:** `tools/gha_web_census.py --dormant` (no REST calls) + each
workflow's own `schedule:` block + its Actions `state`.

## The flag was mostly noise, and the reason matters

The census reported **62 of 382 workflow files had not run in >24 h**. That threshold is wrong for
this repo: 46 of the 62 carry a `schedule:` trigger, and most are weekly or monthly. Compared against
each file's *own* cron interval, **40 of the 46 were on time**:

| cron | expected | last run |
|---|---|---|
| `51 4 1 * *` (`ml-monthly-retrain`) | 31 d | 25 d |
| `54 6 1 * *` (`monthly-tournament`) | 31 d | 25 d |
| `10 6 1 * *` (`beta-portfolio-refresh`) | 31 d | 25 d |
| `18 21 18 7 *` (`poc-picks-checkpoint`) | yearly | 128 d |
| `35 7 1 */3 *` (`value_resolver_quarterly`) | 90 d | 56 d |

A ">24 h without a run" rule labels a monthly job dormant for 29 days of every month. The rule needs
to be ">2.5x its own cron interval", which is what the triage below uses.

## The other six "broken" scheduled workflows were deliberately disabled

`battle_test.yml`, `sports-smoke-and-e2e.yml`, `sports-data-snapshots.yml`,
`ai-tournament-pipeline.yml`, `sports-betting-refresh.yml`, `sports-prediction-market-sync.yml` all
have hourly-or-daily crons and stopped 10–174 days ago — which reads as breakage. Actions says
`state=disabled_manually` for every one, plus a seventh file. **Nothing is broken and nothing needs
re-enabling**; they were switched off on purpose. They are left exactly as they are.

## What was actually dead: three files

Active, **no cron at all** (manual dispatch only), last run **>170 days ago**, only ever succeeded —
so nothing depends on them and nothing will ever trigger them:

| file | last run | trigger |
|---|---|---|
| `pick-flow-snapshot-fast.yml` | 185 d | `workflow_dispatch` |
| `ai-leaderboard-refresh.yml` | 174 d | `workflow_dispatch` |
| `battleground-mass-backtest-part2.yml` | 173 d | `workflow_dispatch` |

Renamed to `*.yml.disabled` — the convention already used in this repo
(`alpha-engine-bond.yml.disabled`, `ml-battleground-a.yml.retired`). Reversing it is one `git mv`.

## Flagged, not touched (needs a human decision)

- `strategy-performance-no-regression.yml` — **182 d**, but event-driven (push/PR). If it still fires
  on a live path it is a gate, and deleting a gate is not a decision to make from staleness alone.
- `discord-token-selftest.yml` — **53 d**, one-off self-test; recent enough that someone may still use it.
- `fetch-movies.yml`, `kimi-fetch-movies.yml` — **46 d**, both explicitly marked "Manual"; disabling
  would remove an operator tool.
- `verification-tests.yml` (1 d), `deploy-bestiejob-page.yml` (7 d), the 10 d event-driven deploy
  workflows, and the 4 d weekly batch — all recent, all left alone.

## Result

62 flagged → 40 healthy scheduled, 7 already disabled manually, 6 wrongly-classified scheduled
(all disabled by hand anyway), 12 recent manual/event workflows left alone, **3 dead files disabled**,
3 flagged for a decision.

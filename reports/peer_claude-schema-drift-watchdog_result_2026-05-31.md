# Schema Drift Watchdog — 2026-05-31

## What

Adds a daily-cron GitHub Actions workflow that snapshots `information_schema.COLUMNS`
for the 5 critical `ejaguiar1_stocks` tables and fails the run if any column is
**removed** or **type-changed** vs the committed baseline.

## Why

Phase 5 / PR #183 discovered `at_strategy_stats.strategy` was being populated with
tier labels ("STRONG"/"MODERATE") instead of strategy names. A column-level type/contract
watchdog would have surfaced that contract violation early. This is the infra-only
preventive layer.

## Files

- `schemas/baseline_2026-05-31.json` — captured live from `mysql.50webs.com` on 2026-05-31.
  Covers: `trading_picks` (20 cols), `at_signal_outcomes` (15), `at_raw_picks` (26),
  `at_strategy_stats` (13), `tournament_picks` (36).
- `.github/workflows/schema-drift-watchdog.yml` — daily at 09:15 UTC + manual dispatch.

## Behavior

| Drift type | Action |
|---|---|
| Column added | `::warning::` (logged, run still green) |
| Column removed | `::error::` + hard fail |
| Data type changed | `::error::` + hard fail |
| `is_nullable` changed | `::error::` + hard fail |

Additive drift is logged but non-fatal because new columns are common and rarely break
downstream code. Removals and type changes are the silent-breaker class.

## Operational

- Requires secret `DB_STOCKS_PASSWORD` (already present as the same value used by
  other DB-touching workflows; if not set, add it once via repo settings).
- When intentional schema changes ship, regenerate the baseline:
  ```bash
  python3 tools/regenerate_baseline.py  # or rerun the inline snapshot query
  ```
  and commit the new `schemas/baseline_YYYY-MM-DD.json`. The workflow picks up the
  newest file by sort order.

## Scope

2-file infra change (+ this writeup). No production-code path touched. No picks
affected. Pure observability.

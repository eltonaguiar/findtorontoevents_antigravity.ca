# Sports score settlement bundle (sports_bets, sports_picks, sports_scores_settle_lib)

**Date:** 2026-04-23

## What

Atomic port of settlement improvements from the codex `sports-failover-apis` branch (PR #345, draft), **excluding** that branch’s competing `odds_api_fetch.php` (see [2026-04-23-sports-failover-pr-diff-audit.md](2026-04-23-sports-failover-pr-diff-audit.md)).

## Files

- `live-monitor/api/sports_scores_settle_lib.php` — `sports_scores_team_aliases`, `sports_scores_date_key`, `sports_scores_find_match`, and related grading helpers
- `live-monitor/api/sports_bets.php` — `settle_by_scores` path uses `sports_scores_find_match`
- `live-monitor/api/sports_picks.php` — `settle_picks` path uses `sports_scores_find_match`

## Why

The three files must stay in sync: bets and picks call `sports_scores_find_match()` defined in the shared lib. Cherry-picking only `settle_lib` would leave undefined references.

## Verification

- Grep: no `??` / `?:` (PHP 5.2) in the three files after port
- PR merged after #342 (failover) was already on `main`

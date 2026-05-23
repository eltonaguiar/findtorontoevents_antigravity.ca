# B28: Register ueps_picks.json in JSON_PICK_SOURCES (2026-05-01)

## What changed

Replaced the racy `sync_to_active_picks()` → `alpha_engine/data/active_picks.json`
path with a direct registration of `audit_dashboard/data/ueps_picks.json`
in `JSON_PICK_SOURCES` (same pattern used by tradingagents and skyrocket_detector).

## Root cause (B28 investigation)

| Time (UTC) | Event | Result |
|---|---|---|
| 2026-04-30 20:12 | PR #547 merged | UEPS sync-gate fix lands |
| 2026-04-30 20:55 | UEPS cron syncs 30 picks | `active_picks.json` gains 30 UEPS rows |
| 2026-05-01 05:26 | Alpha-engine-live cron runs | **9,824-line wholesale rewrite of `active_picks.json` — UEPS rows wiped** |

`sync_to_active_picks()` is insert-only at the row level, but `alpha-engine-live.yml`
(the "DARWIN ENGINE") rewrites the entire file from scratch every hour. UEPS rows
survive ~4h at most before being silently overwritten.

## Files changed

| File | Change |
|---|---|
| `audit_trail/dashboard_generator.py` | Added `("ueps", "audit_dashboard/data/ueps_picks.json", None)` to `JSON_PICK_SOURCES`; updated `_extract_picks()` to concatenate `long_picks + swing_picks + short_picks` |
| `.github/workflows/ueps-pick-runner.yml` | Added `--skip-active-sync`; removed `alpha_engine/data/active_picks.json` from `git add` |
| `tests/test_ueps_active_sync_workflow.py` | Updated to reflect new approach; replaced `test_workflow_commits_both_ueps_and_active_picks` with tests for `--skip-active-sync` and the absence of `active_picks.json` in the commit |
| `tests/test_ueps_dashboard_wireup.py` | New — pins JSON_PICK_SOURCES entry; tests `_extract_picks` multi-list handling |

## Acceptance criteria met

- `"ueps"` and `"audit_dashboard/data/ueps_picks.json"` registered in `JSON_PICK_SOURCES` ✅
- `_extract_picks()` returns 30 picks from live `ueps_picks.json` ✅
- Workflow uses `--skip-active-sync` ✅
- `alpha_engine/data/active_picks.json` removed from `git add` ✅
- 6/6 logic tests pass locally ✅

## Why this fixes V1

After the next dashboard rebuild, UEPS picks will surface in /audit's main
active-picks table because the dashboard generator directly reads
`ueps_picks.json` on every rebuild — no longer dependent on the shared
ledger surviving competing cron overwrites.

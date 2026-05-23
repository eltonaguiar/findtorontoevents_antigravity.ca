# GHA fixes — conflict markers, CI tests, swarm sync, sports checkout, sidecar push

## What was failing

| Area | Symptom | Root cause |
|------|---------|------------|
| Conflict Marker Check | `<<<<<<<` in `tools/local_swarm_review.py` | Unmerged git conflict markers committed |
| CI Tests (`pytest`) | `test_graceful_no_yfinance`, `test_all_values_in_indicator_families` | `relative_to(REPO)` on `/tmp` output path; `commodity_seasonal` missing from `INDICATOR_FAMILIES` |
| Swarm State Sync | Exit 127 / broken shell | YAML used escaped `\"` inside `run: \|`, corrupting `CHANGED_FILES=` assignments |
| Sports refresh (custom job) | `fatal: not a git repository` | `custom-sports-update` had no `actions/checkout`; commit step ran without `.git` |
| Sidecar Status Update | Push rejected (non-fast-forward) | `safe_commit_push.sh` is `100644` so `[ -x ... ]` was false; fallback did `git push` without `pull --rebase` |

## Changes

1. **`tools/local_swarm_review.py`** — Resolved all conflict regions: single `CLOUD_PANEL` (inception + moonshot + MiMo note), module `import os`, cloud `query()` env fallbacks + URL map, `review_one(..., panel=None)` defaulting to `PANEL`.
2. **`tools/backtest_etf_economic.py`** — `_print_wrote_path()` uses `relative_to(REPO)` when possible, else prints absolute path (pytest temp dirs on Linux CI).
3. **`alpha_engine/config.py`** — Added `"commodity_seasonal"` to `INDICATOR_FAMILIES` (matches `STRATEGY_FAMILIES` for `commodity_seasonal_planting_harvest`).
4. **`.github/workflows/swarm-sync-v2.yml`** — Bash uses a proper array `CHANGED_FILES+=("$file")`, unescaped `echo`, quoted paths; no escaped-double-quote soup.
5. **`.github/workflows/sports-betting-refresh.yml`** — `custom-sports-update` checks out repo with `token`; `git-auto-commit-action` gets the same `token`.
6. **`.github/workflows/sidecar-status-update.yml`** — Always run `bash .github/scripts/safe_commit_push.sh` when the file exists (not `[ -x ... ]`); fallback `else` adds `git pull --rebase` before push.

## Verification

- `python -m pytest tests/test_backtest_etf_economic.py::test_graceful_no_yfinance alpha_engine/tests/test_confluence.py::TestStrategyFamiliesValidity::test_all_values_in_indicator_families -q` — **pass** (Windows).
- `rg '^(<<<<<<<|=======|>>>>>>>)' tools/local_swarm_review.py` — **no hits**.

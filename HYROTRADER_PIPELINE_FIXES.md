# HyroTrader Pipeline Fixes — Stale Data on /audit/hyrotrader/

**Date:** 2026-04-14  
**Branch:** `feat/enhancements-high-conviction-hyrotrader-copytrader`  
**Commit:** `15bd9c2f9` (committed locally, push pending due to rebase conflicts)

---

## Problem

The HyroTrader audit page at [findtorontoevents.ca/audit/hyrotrader/](https://findtorontoevents.ca/audit/hyrotrader/) showed **stale data from Apr 7**:

- `generated_at`: stuck at `2026-04-07T17:55:00Z`
- `Fear&Greed`: stuck at `11` (Extreme Fear)
- Only `4 symbols scanned`
- Header showed: *"Generated: Apr 7, 5:55 PM ET | Fear&Greed: 11 | 4 symbols scanned"*

## Root Cause

Three gaps in the CI/deploy pipeline meant `hyro_quan_bridge.json` never got refreshed or deployed:

| Gap | Explanation |
|-----|-------------|
| **1. Hourly `audit-dashboard.yml` never ran QuanBridge** | The workflow ran pre-scanners, technical analyzer, etc. but had no step for `tools/hyro_quan_bridge.py` or `alpha_engine/hyrotrader_enhanced_scoring.py`. |
| **2. Daily `hyro-daily.yml` was artifacts-only** | The workflow description said *"Artifacts only (no auto-commit)"*. It ran the filter + backtest but never committed or pushed the resulting JSON files. Data stayed local to the CI runner. `permissions: contents: read` reinforced this. |
| **3. `deploy_to_ftp.py` missed hyro files** | The FTP upload list in `deploy_audit_dashboard()` had `hyrotrader_picks.json`, `hyrotrader_journal.json`, and `hyro_live_strategies.json` but was missing `hyro_quan_bridge.json`, `hyrotrader_enhanced_picks.json`, `hyrotrader_short_term_entries.json`, and `hyro_backtest_results.json`. |

## Changes Made

### 1. `.github/workflows/audit-dashboard.yml`

**Added steps** (before the "Run technical analyzer" step):

```yaml
- name: Run Hyro QuanBridge (refresh regime + ensemble + risk gate)
  id: hyro_quan_bridge
  run: python tools/hyro_quan_bridge.py --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --save --verbose || echo "Hyro QuanBridge failed (non-fatal)"
  continue-on-error: true

- name: Run Hyro enhanced scoring (technical indicators on picks)
  id: hyro_enhanced_scoring
  run: python alpha_engine/hyrotrader_enhanced_scoring.py || echo "Hyro enhanced scoring failed (non-fatal)"
  continue-on-error: true
```

**Added hyro JSON files to both git-add lists** (main commit step + conflict-resolution re-commit step):

```
audit_dashboard/data/hyrotrader_picks.json
audit_dashboard/data/hyrotrader_enhanced_picks.json
audit_dashboard/data/hyrotrader_short_term_entries.json
audit_dashboard/data/hyro_live_strategies.json
audit_dashboard/data/hyrotrader_journal.json
audit_dashboard/data/hyro_backtest_results.json
```

### 2. `.github/workflows/hyro-daily.yml`

**Upgraded from artifacts-only to auto-commit+push:**

- Changed `permissions: contents: read` → `contents: write`
- Updated description: *"Artifacts only (no auto-commit)"* → *"Auto-commits updated JSON files so the live dashboard stays fresh"*

**Added QuanBridge + enhanced scoring steps:**

```yaml
- name: Run Hyro QuanBridge (regime + ensemble + risk gate)
  env:
    GITHUB_ACTIONS: 'true'
    PYTHONPATH: ${{ github.workspace }}
  run: |
    python tools/hyro_quan_bridge.py --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --save --verbose || echo "QuanBridge failed (non-fatal)"
  continue-on-error: true

- name: Run Hyro enhanced scoring (technical indicators)
  env:
    GITHUB_ACTIONS: 'true'
    PYTHONPATH: ${{ github.workspace }}
  run: |
    python alpha_engine/hyrotrader_enhanced_scoring.py || echo "Enhanced scoring failed (non-fatal)"
  continue-on-error: true
```

**Added commit+push step with 5-retry jitter loop:**

```yaml
- name: Commit and push Hyro data
  env:
    TOKEN_FOR_PUSH: ${{ secrets.GH_PAT || github.token }}
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git remote set-url origin "https://x-access-token:${TOKEN_FOR_PUSH}@github.com/${GITHUB_REPOSITORY}.git"
    for f in audit_dashboard/data/hyrotrader_picks.json ...; do
      git add "$f" 2>/dev/null || true
    done
    git diff --cached --quiet && echo "No Hyro data changes to commit" && exit 0
    git commit -m "Hyro daily: refresh picks + QuanBridge + backtest $(date -u '+%Y-%m-%d %H:%M UTC') [skip ci]"
    for i in 1 2 3 4 5; do
      git pull --rebase -X theirs origin main && git push origin main && echo "Pushed on attempt $i" && exit 0
      sleep $((i * 10 + RANDOM % 15))
    done
    echo "Push failed after 5 attempts"
    exit 1
```

### 3. `tools/deploy_to_ftp.py`

**Added 4 missing hyro data files** to the `deploy_audit_dashboard()` data file loop:

```python
"hyro_quan_bridge.json",
"hyrotrader_enhanced_picks.json",
"hyrotrader_short_term_entries.json",
"hyro_backtest_results.json",
```

### 4. `audit_dashboard/data/hyro_quan_bridge.json` (data refresh)

Ran `python tools/hyro_quan_bridge.py --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --save --verbose` locally to immediately refresh the stale data:

| Field | Before (stale) | After (refreshed) |
|-------|----------------|-------------------|
| `generated_at` | `2026-04-07T17:55:00Z` | `2026-04-14T19:54:32Z` |
| `fear_greed` | `11` (Extreme Fear) | `21` (Fear) |

## Push Status

⚠️ **Commit `15bd9c2f9` is committed locally but NOT yet pushed.** The push failed due to:

1. The remote branch has many auto-commits ahead of local (CI bots push hourly)
2. `git pull --rebase` on the feature branch hit merge conflicts in unrelated `.meta.json` files (2,923 commits to rebase)
3. `git pull --no-rebase` (merge) hit a conflict in `_check_tbd_toggle.js`, which was resolved, but the resulting merge commit created non-fast-forward history that was also rejected

**To push successfully, you likely need to:**
- Rebase onto current `origin/main` with conflict resolution, OR
- Force-push the feature branch (`git push --force-with-lease origin feat/enhancements-high-conviction-hyrotrader-copytrader`) if no one else is depending on its remote state, OR
- Cherry-pick `15bd9c2f9` onto a fresh branch off `origin/main`

## Code Review Notes

From code-reviewer-lite:

1. **Push race between `hyro-daily.yml` and `audit-dashboard.yml`**: Both can push concurrently. The hyro-daily retry loop (5 retries with jitter) should handle this, but could be increased further. The `[skip ci]` tag prevents infinite loops.
2. **`PYTHONPATH` consistency**: Added `PYTHONPATH: ${{ github.workspace }}` to QuanBridge/enhanced-scoring steps in hyro-daily.yml. The scripts self-insert their paths into `sys.path`, but explicit PYTHONPATH is safer.

## Expected Outcome After Push + Deploy

Once these changes are pushed and the next CI cycle runs:

1. **Hourly** `audit-dashboard.yml` will run QuanBridge + enhanced scoring → commit JSON → push → deploy via FTP
2. **Daily** `hyro-daily.yml` will run filter + backtest + QuanBridge + scoring → commit JSON → push
3. **FTP deploy** will upload all hyro JSON files (including the previously missing 4)
4. The `/audit/hyrotrader/` page will show **current** timestamps, Fear&Greed, and regime data

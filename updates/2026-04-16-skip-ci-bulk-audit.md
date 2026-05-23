# Audit: Add [skip ci] to Data-Only Workflow Commits

**Date:** 2026-04-16  
**Author:** Codebuff (Buffy)  
**Status:** Applied, YAML validated (279/279 pass)  
**Scope:** 125 workflow files modified (116 via batch script + 9 manual multi-line fixes)

---

## Problem

The audit-dashboard cancellation investigation identified that ~2 commits/min hit `main` from automated workflows. Many of these are data-only commits (JSON results, log files, HTML dashboards) that don't need CI validation, yet each push triggers all workflows with `push:` triggers on watched paths — causing a push storm that cancels long-running jobs like the audit-dashboard.

## Solution

Added `[skip ci]` to every data-only `git commit -m` line across all `.github/workflows/*.yml` files.

GitHub respects `[skip ci]` / `[skip-ci]` in commit messages — any push containing this text will not trigger workflows that have `push:` triggers, effectively eliminating unnecessary CI runs for bot-generated data commits.

## What Was Changed

### Phase 1: Batch Script (116 files)

Used `tools/_add_skip_ci.py` (one-time helper, now deleted) with a state-machine parser that:

- Finds `git commit -m "..."` lines and appends `[skip ci]` before the closing quote
- Handles nested quotes inside `$(date -u '+%Y-%m-%d')` substitutions
- Handles shell operators after commit: `|| echo "No changes"`
- Skips messages that already have `[skip ci]`
- Preserves CRLF line endings
- Skips multi-line commit messages for safety (handled manually in Phase 2)

### Phase 2: Manual Multi-Line Fixes (9 files)

These had multi-line heredoc-style commit messages the batch script correctly skipped:

| File | Closing Line Pattern |
|------|---------------------|
| `2hour_challenge.yml` | `...results [skip ci]" \|\| echo "No changes"` |
| `algorithm-competition-refresh.yml` | `...5 asset classes [skip ci]"` |
| `battle_test.yml` | `...Run #N [skip ci]" \|\| echo "No changes"` |
| `social_investigation.yml` | `...researching... [skip ci]" \|\| echo "No changes"` |
| `real_2hour_challenge.yml` | `...actual winner! [skip ci]" \|\| echo "No changes"` |
| `self_optimizing_trading.yml` | `...Run #N [skip ci]" \|\| echo "No changes"` |
| `signal_tracking.yml` | `...Run #N [skip ci]" \|\| echo "No changes"` |
| `torontoevent-algorithm-refresh.yml` | `...5 asset classes [skip ci]"` |
| `genome-evolution.yml` | `...no files') [skip ci]"` (nested `$(python -c "...")`) |

### Excluded (intentionally no [skip ci])

| File | Reason |
|------|--------|
| `fix-battleground.yml` | Commits code changes that intentionally trigger CI for battleground validation |

### Already Had [skip ci] (~45 workflows)

These were already correctly configured before this audit.

## Verification

- YAML syntax: All 279 `.github/workflows/*.yml` files pass `yaml.safe_load()` validation
- Spot-checked 7 representative files for correct `[skip ci]` placement
- Verified all 9 multi-line edits contain `[skip ci]` on the closing quote line
- Confirmed excluded files (`fix-battleground.yml`) remain untouched

## Expected Impact

Before this change, ~120+ data-only commits per day each triggered push-based workflows. After:
- Data-only bot commits → `[skip ci]` → no push triggers fire
- Only code changes and intentional CI triggers will start workflow runs
- Dramatic reduction in push storm pressure on the audit-dashboard and other long-running workflows

## Cleanup

- One-time helper script `tools/_add_skip_ci.py` deleted after use

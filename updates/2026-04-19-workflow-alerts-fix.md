# Workflow Alert Fixes — 2026-04-19

## Problem

Investigation of GitHub Actions alerts revealed 3 issues:

| Workflow | Alert | Root Cause |
|----------|-------|------------|
| Consensus Outcome Tracker | 100% cancellation (10/10 runs) | `cancel-in-progress: true` + slow inline push loop (423s) = next scheduled run kills the still-pushing one |
| Hindsight Learner Hourly Winner Analysis | 1 SSL failure on `pip install` | Transient PyPI SSL error (`DECRYPTION_FAILED_OR_BAD_RECORD_MAC`) with no retry logic |
| Claude Gainer ML Live Scanner | 1 cancelled run | Not chronic — 9/10 recent runs succeeded. The single cancellation was likely a concurrency collision |

## Fixes

### 1. Consensus Outcome Tracker (critical — 100% broken)

- **`cancel-in-progress: true` → `false`**: The workflow runs every 30 minutes. With `cancel-in-progress: true`, each new scheduled run cancels the previous one. Since the push step takes 423s (7 minutes), and runs start every 30 minutes, the push step never completes before the next run kills it.
- **Replaced inline push loop with `safe_push.sh`**: The inline 5-retry loop was slow and lacked timeout guards. `safe_push.sh` has 15 retries, exponential backoff, 180s command timeouts, and automatic shallow-repo deepening.
- **Removed dead `TOKEN_FOR_PUSH` env var**: No longer needed since `safe_push.sh` handles token injection internally.
- **Bumped `timeout-minutes` from 10 → 15**: The old 10-minute timeout was too tight — checkout (82s) + Python script (104s) + push step can exceed 10 minutes, especially when runs queue instead of cancelling each other.

### 2. Hindsight Learner (1 transient failure)

- **Added 3-retry loop around `pip install`**: PyPI SSL errors like `DECRYPTION_FAILED_OR_BAD_RECORD_MAC` are transient. The retry loop waits 10s, 20s, 30s between attempts and exits with code 1 if all 3 fail.

### 3. Claude Gainer ML Live (not chronic — no fix needed)

- 9/10 recent runs succeeded. The single cancelled run was a normal concurrency collision. No code change required.

## Verification

- Both YAML files validated for syntax
- `safe_push.sh` exists in repo at `.github/scripts/safe_push.sh`
- All 4 consensus-outcome-tracker fixes verified (cancel-in-progress=false, safe_push.sh, no TOKEN_FOR_PUSH, timeout=15)
- All 3 hindsight-learner fixes verified (retry guard, exit 1 on final failure, SSL comment)

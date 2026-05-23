# GHA Runner Cancellation Fix — 2026-05-06

## Problem

20 cancelled workflow runs in ~24 hours across 18 different workflows. Root cause analysis of run logs revealed **2 distinct patterns**, neither involving agent errors or hallucinations:

1. **`safe_push.sh` hanging on `git push`** — After completing all work and committing successfully, `git pull --rebase` and `git push` operations would hang indefinitely on the GHA runner. GHA would then kill the job (conclusion=cancelled) right at the finish line.
2. **`git fetch` stalling during checkout** — Shallow clones hitting the `git fetch --deepen=150` step in `safe_push.sh` would hang for 240 seconds silently, burning the runner clock.

## Fixes Applied

### 1. `safe_push.sh` — Tightened Timeouts & Fail-Fast

| Change | Before | After |
|---|---|---|
| `GIT_NET_TIMEOUT` | 180s | 90s — fail faster, let retry loop handle it |
| `DEEPEN_TIMEOUT` | (hidden 240s) | **NEW: 90s** — deepen fetch must not burn the whole run |
| `MAX_RETRIES` | 15 | 8 — reduce runner minutes burned on bad pushes |
| `INITIAL_BACKOFF` | 2s | 3s — slightly slower first retry |
| `MAX_BACKOFF_SLEEP` | 120s | 60s — cap per-sleep so one run doesn't wait many minutes |
| Deepen fetch | silent warning, continue | **Fatal exit** if timeout — fail cleanly (conclusion=failure), not cancelled |
| Deepen fallback | abort | Falls back to `pull.rebase=false` (merge strategy) so shallow repos can still push |

### 2. Shallow Clones — `fetch-depth: 1` Added to 6 Workflows

The repo is large (~17k+ files). Full clones + `git fetch --unshallow` on every run cause the deepen step to hit network timeouts. Added `fetch-depth: 1` to the most cancellation-prone workflows:

- `.github/workflows/darwin-evolution.yml` — 4 cancellations (worst offender)
- `.github/workflows/sports-betting-refresh.yml` — 2 checkouts, both updated
- `.github/workflows/sports-prediction-market-sync.yml` — 2 cancellations (both runs cancelled, 0 successes)
- `.github/workflows/buy-now-analysis.yml` — changed `fetch-depth: 0` → `fetch-depth: 1`
- `.github/workflows/alpha-engine-live.yml` — 1 cancellation
- `.github/workflows/dashboard-pick-trader.yml` — 2 cancellations

Note: `meme-scanner.yml` and `fc-crypto-pro.yml` already had `fetch-depth: 1`. `antigravity-claudeopus.yml` and `meta-strategy.yml` already had `fetch-depth: 1`.

### 3. `safe_push.sh` — Token Auth Validation (Fail-Fast)

Added a curl-based token validation step before any git operations run. If the token is invalid/expired (HTTP 401/403), the script exits immediately with a clear error message instead of hanging indefinitely on git push.

Key features:
- `--max-time 15` on curl to prevent hanging if network is blocked
- `mktemp` for secure temp file creation (600 permissions)
- Skipped when custom `REMOTE_URL` is provided (different credentials)
- Clear error messages pointing to `GH_PAT` setup instructions
- Uses `os.environ.get('_auth_check')` to bridge shell→Python boundary

Note: `GH_PAT` is NOT set as a repo secret — all workflows rely on `github.token` (built-in GHA token). This is correct; the validation confirms the `github.token` has `contents: write` permission.

## Verification

- `safe_push.sh` bash syntax: **OK**
- All 6 workflow YAML files validated with `yaml.safe_load()`: **OK**
- Code review (code-reviewer-lite): **No issues**

## Why Not Agent Hallucination

Every cancelled run followed this exact sequence:
1. ✅ All bot work completed (scraping, scanning, committing)
2. ✅ Git commit succeeded: `[main abc123] ... [skip ci]`
3. ⏳ `safe_push.sh` ran and hung on network operations
4. ⏱ Runner timeout hit → GHA killed the job
5. 💀 Post-job hook cleaned up orphaned git processes

The bots did their jobs correctly. The infrastructure (git push on GHA runner) was the failure point.
# FIX-003 — Concurrent push rebase races on main

**Files:** `.github/workflows/forward-test-new-strategies.yml`, `.github/workflows/gainer-predictor.yml`
**Severity:** P1
**Status:** Proposed (not yet applied)

## What was broken
Multiple workflows push to `main` on independent schedules:
- `forward-test-new-strategies.yml`: every 6h, runs `git pull --rebase origin main` then `safe_push.sh`
- `gainer-predictor.yml`: every 30 min, commits and retries push 3x with flat 5s sleep (no backoff)
- `equities-agent.yml`: twice daily weekdays, already has `concurrency: equities-agent / cancel-in-progress: true`

`forward-test-new-strategies.yml` and `gainer-predictor.yml` have **no concurrency control**, so concurrent runs can collide on `git pull --rebase` / `git push origin HEAD:main`, causing rebase conflicts, failed pushes, and stranded commits on non-main branches.

## What to change
1. Add `concurrency: group: <workflow-name>; cancel-in-progress: true` to `forward-test-new-strategies.yml` and `gainer-predictor.yml` (mirroring `equities-agent.yml`).
2. In `gainer-predictor.yml`, replace the flat 3×/5s push retry with `safe_push.sh` (exponential backoff + ref-lock race handling) instead of a manual `for i in 1 2 3` loop.
3. Ensure all push-to-main workflows use `HEAD:main` refspec (already correct in `safe_push.sh`) and `[skip ci]` in commit messages to avoid infinite loops.

## How to verify
- Confirm `concurrency` key present in both workflows.
- Validate YAML parses.
- Trigger both workflows concurrently via `workflow_dispatch` and confirm one cancels/queues instead of both colliding on `main`.
- Confirm commit messages contain `[skip ci]`.

## Related
`safe_push.sh` already handles rebase/merge fallback and ref-lock races (fixed 2026-05-06). `equities-agent.yml` already models the correct concurrency pattern.
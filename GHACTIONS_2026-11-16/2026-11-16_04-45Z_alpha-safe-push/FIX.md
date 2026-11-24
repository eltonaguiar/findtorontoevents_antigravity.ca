# Fix — ALPHA Dynamic Runner: use safe_push.sh (kills the push HANG)

- Date: 2026-11-16 · Branch: `fix/alpha-use-safe-push-2026-11-16`

## Root cause (upgraded diagnosis)
PR #813 raised the `Commit results` step timeout 5→15m. The **first post-fix run**
`43799911205` (created 03:44Z, 15m config) then failed with:
```
##[error]The action 'Commit results' has timed out after 15 minutes.
```
Log shows: commit succeeded at 04:18:20, then **45 seconds… no — 15 minutes of ZERO output**, then timeout.
The inline retry loop's `git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null`
**hung indefinitely** on the shallow clone under push contention (and `2>/dev/null` hid why). No
per-operation timeout existed, so neither a 5m nor a 15m step cap can help an infinite hang — it just
times out at whatever the cap is.

## Fix
Replace the fragile inline 10-attempt loop with the repo's hardened helper
`bash .github/scripts/safe_push.sh`, which:
- caps **every git network op at 90s** (`GIT_NET_TIMEOUT`) → a stalled fetch/push can no longer hang the step;
- deepens the shallow clone (`--deepen=150`, capped 90s) so rebase has a merge base, with a **merge
  fallback** if deepen stalls;
- **fails fast** on auth / permanent rejections instead of burning runner clock.
Called non-fatally (`if ! bash safe_push.sh; then ::warning::…; fi`) to preserve the documented
"self-heal next cycle" semantics (each cycle regenerates alpha_engine/data from scratch).

This is the same helper `regime-terminal.yml` already uses successfully.

## Downstream /audit
`alpha_engine/data/` feeds `audit_trail/quality_gates.py`, `universal_pick_resolver.py`,
`regime_filter.py` — so making the push reliably *complete* (instead of hanging to a RED timeout)
improves /audit alpha-data freshness. No schema or page change.

## Revert
```bash
git fetch origin && git checkout main && git pull --ff-only
git checkout origin/main~1 -- .github/workflows/dynamic-alpha-engine.yml   # or restore the prior loop
```
(Pre-change blob is the version containing the inline `for i in 1..10` loop.)

## Verification
Watch the next `:18`/`:48` ALPHA run. Expected: `Commit results` finishes in seconds–minutes (success,
or `::warning` + green on push failure) — **never** a 15-min "timed out" and **never** the old 5-min
message. Compare against run 43799911205 (the hang that motivated this).

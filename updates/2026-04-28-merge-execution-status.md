# 2026-04-28 Merge Execution Status (Goal #1)

This note documents the merge execution requested in chat: merge ready PRs, identify blockers, and define immediate follow-up actions.

## Scope

- Focus: Goal #1 (hedge-fund-grade performance on `/audit`)
- Merge window: PR batch around #461 to #471
- Method: merged green/safe PRs first, left failing/conflicted PRs unmerged

## Merged in this execution

- `#462` - UEPS wiring into audit flow
- `#463` - resolver v2 fix (already merged before this execution check)
- `#464` - catalyst pre-filter wiring
- `#465` - drift-aware scoring multiplier wiring
- `#467` - triple-barrier labeler additive wiring
- `#468` - PSR-based scoring component integration
- `#469` - anti-overfit validator sidecar (CPCV/PBO/RC/DSR)
- `#470` - bond data/pricing sidecar (FRED + QuantLib)
- `#471` - hedge-fund quality gate opt-in wiring

## Blocked / not merged

- `#466` - **not merged** due to failing CI tests (`test (3.11)`, `test (3.12)` red)
- `#461` - **not merged** due to merge conflicts against updated `main`

## Why this improves Goal #1 now

- Landed resolver/scoring/validation wiring that directly reduces false confidence from stale or overfit signals.
- Landed UEPS and catalyst/drift layers that improve EQUITY decision quality in production path.
- Landed bond-side data infrastructure and HF quality gate plumbing so class expansion is less blind and easier to enforce.

## Immediate next actions

1. Fix `#466` test failures on branch, re-run checks, then merge.
2. Rebase/conflict-resolve `#461` onto latest `main`, then merge.
3. Run post-merge re-resolution flow for resolver v2:
   - `python tools/re_resolve_historical_v2.py --dry-run --report`
   - inspect delta
   - rerun with apply mode after sanity checks
4. Publish an updated n-per-asset-class snapshot on `updates/` reflecting the merged stack.

## Notes

- Merges were executed remotely to avoid disturbing a dirty local working tree.
- Parallel API merges were intentionally avoided after first race (`Base branch was modified`) and retried sequentially.

# Swarm PR Review — Consensus + Smart-Agent Decision — 2026-06-24

**Invoked:** /swarm-pr-review. **Reviewers (2 independent):** `deepseek` (v4-flash, via tools/swarm) + this agent's git/gh-verified direct review. xai/groq/cerebras/ofox/kimi returned empty this run (provider flakiness) — not counted. Every peer claim was re-verified against the actual PR before acceptance (CLAUDE.md).

## Context (verified)
main CI green (0 fails/80 runs). All 10 open PRs stale (879–16,608 commits behind main). Common failing check is stale-drift (the tpsl-commodity test already passes on main).

## Consensus table

| PR | deepseek | direct review | **CONSENSUS** |
|---|---|---|---|
| #562,#564,#581,#595,#600 (old docs) | close: **agree** | close as superseded | **CLOSE (2/2)** |
| #666 — B1 backfill price guard (resolver) | MERGE_AFTER_REBASE | rebase (sound resolver guard + tests) | **MERGE after rebase (2/2)** |
| #665 — CI-drift reconciliation + stalled-producer audit | MERGE_AFTER_REBASE | rebase (conftest/gate quarantines appropriate) | **MERGE after rebase (2/2)** |
| #657 — winner-hunt replay contract test | MERGE_AFTER_REBASE | rebase (fail-closed cron gate, mirrors existing pattern) | **MERGE after rebase (2/2)** |
| #667 — forward-track cell selector | NEEDS_FIX | NEEDS_FIX | **NEEDS_FIX (2/2)** |

## #667 detail — deepseek's catch, right-sized
deepseek flagged "data corruption" (cells with `strategy_base:'?'`). **Verified + corrected:** the generated `forward_track_candidates.json` has **2 of ~248 cells** with `strategy_base:"?"` (<1%) — a minor data-hygiene edge, **not** pervasive corruption. The real blockers for #667:
1. 2 new tests (`test_select_forward_track_candidates.py::{test_g_load_pick_funnel_real, test_h_...}`) fail in CI on `FileNotFoundError: pick_funnel_90d.json` (gitignored/hourly file absent) — need skip-when-absent, matching the pattern other data-dependent tests already use.
2. Optionally filter the 2 `"?"`-strategy cells before writing.
Then rebase (879 behind).

## Smart-agent decision (final)
- **CLOSE** #562, #564, #581, #595, #600 — superseded (2 weeks + 14k-16k commits behind; edge-hunt concluded + documented in later reports).
- **REBASE + merge** #657, #665, #666 — real, sound code; re-run CI after rebase (the red is stale-drift).
- **#667 → author fix** (skip-when-absent tests + filter 2 "?" cells) then rebase; do not merge as-is.
- All merges/closes are **outward-facing + irreversible → operator go-ahead required**; not auto-executed.

## Ready commands (for operator approval)
```
# close superseded
for pr in 562 564 581 595 600; do gh pr close $pr --comment "Superseded — 2+ weeks + 14k-16k commits behind main; edge-hunt concluded (see reports/*2026-06*). Closing per swarm review 2026-06-24."; done
# rebase+merge candidates (after local rebase onto main + green CI)
gh pr merge 666 --squash ; gh pr merge 665 --squash ; gh pr merge 657 --squash
# #667: fix tests + filter "?" cells, then rebase, then merge
```

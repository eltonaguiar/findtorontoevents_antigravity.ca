# GHA Hourly Health Monitor — 2026-06-28

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failing jobs:** `test (3.11)` and `test (3.12)` — both fail on the same line:
```
Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1
```

**Root cause (confirmed):** `alpha_engine/backtest_quant_algorithms.py` was accidentally overwritten with garbage content `IsADirectoryErrorCHATWITHIT.mdmd atTH..D` (an exception message string, not Python). The file has contained this content since at least commit `6e9836e9` (Auto-update 2026-06-05 12:04 UTC). All 30 visible CI Tests runs on main (going back to 2026-06-27T17:54Z) are failures; the last known GREEN state is 2026-05-22.

**Run links (most recent):**
- Run 28322606571 — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28322606571 (2026-06-28T12:42Z)
- Run 28321026099 — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28321026099 (2026-06-28T11:40Z)

**Chronic workflows:** Not assessed this run — resources focused on RED main diagnosis.

**Open PRs RED:**
| PR | Title | Classification | Action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | Unknown (no statusCheckRollup) | Check if CI-gated files changed |
| #666 | fix(resolver): B1 backfill price guard | Unknown | Check if CI-gated files changed |
| #665 | audit(stalled-producer-detector) | Unknown | Check if CI-gated files changed |
| #657 | feat(contract-test): cold-merge atomic contract-test gate | `[skip ci]` body — likely not CI-gated | N/A |
| #600, #595, #581, #564, #562 | Older research/docs PRs | Unknown | Low priority vs main fix |

**Action required:** AUTHOR_FIX — `alpha_engine/backtest_quant_algorithms.py` must be restored to valid Python. The file's correct content was overwritten by a health-check bot or automated write that mistakenly wrote an error message string to the file. To fix:
1. Find the pre-corruption version via git (pre-June 5): `git show origin/main~N:alpha_engine/backtest_quant_algorithms.py` going back before commit `6e9836e9`.
2. Restore the file and push to main.
3. The CI Tests will go GREEN on next trigger.

**Status change vs last recorded (2026-05-22 00:00 UTC):** GREEN → RED (status changed).

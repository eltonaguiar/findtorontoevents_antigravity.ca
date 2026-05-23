# B9 — Adversarial Debate Shadow Wiring for UEPS Emitter

**Date:** 2026-05-04  
**PR:** feat/b9-adversarial-shadow-2026-05-04  
**Risk:** LOW — default-OFF sidecar, 14-day shadow run  
**Queue item:** B9 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (Order 13/21)  
**Prereq satisfied:** V1 ✅ 2026-05-04 (17/77 active picks carry `source_system=ueps`)

## What changed

### `tools/run_ueps_pickers.py`
- Added `from alpha_engine import adversarial_debate as _adv` import.
- In `run_screeners()`, after `long_screener.screen_universe()` returns `long_picks`,
  calls `_adv.apply_to_picks(long_picks)` to stamp adversarial debate fields.
- Adds a `logger.info("[adversarial] shadow: N/M long picks pass debate")` summary
  when the flag is enabled, so results are visible in workflow logs.

### `alpha_engine/adversarial_debate.py`
- Updated module docstring: changed from "NOT wired into any production pick path"
  to reflect `tools/run_ueps_pickers.run_screeners` as the production caller (B9).

### `tests/test_ueps_adversarial_shadow.py` (new)
5 integration tests covering:
1. Default-OFF: `apply_to_picks` is a no-op without the env flag.
2. Flag-ON with stub LLM: adversarial fields (`adversarial_score`, `adversarial_keep`) stamped.
3. LLM error on one pick: error swallowed, pick still returned.
4. `_adv` alias is importable from `run_ueps_pickers`.
5. `apply_to_picks` is called inside `run_screeners` (via spy mock).

## Behavior

| `UEPS_ADVERSARIAL_ENABLED` | Effect |
|---|---|
| unset / 0 (default) | No change to picks — pure no-op. Same as before this PR. |
| 1 | Each long pick gains `adversarial_score` (float, -1 to +1) and `adversarial_keep` (bool). Workflow log shows keep count. |

**No picks are filtered.** `adversarial_keep=false` is informational during the
shadow run; it does NOT remove picks from `ueps_picks.json` or `active_picks.json`.
After ≥30 closes accumulate, a follow-up PR can promote `adversarial_keep` to an
optional gate (B9 follow-up).

## Enabling the shadow run

Set `UEPS_ADVERSARIAL_ENABLED=1` in the GitHub Actions environment for the
`ueps-pick-runner.yml` workflow. The shadow run requires `DEEPSEEK_API_KEY` and
`XAI_API_KEY` (or any of the fallback keys listed in `adversarial_debate.py`).

## Wire-Up Rule compliance

`adversarial_debate.apply_to_picks` now has a production caller in the UEPS
emitter path (`tools/run_ueps_pickers.run_screeners`). Wire-Up Rule satisfied;
docstring updated.

## Acceptance criteria

- [x] `UEPS_ADVERSARIAL_ENABLED` absent → no adversarial fields on any pick
- [x] Flag present + stub LLM → `adversarial_score` and `adversarial_keep` on every long pick
- [x] LLM error on one pick → error swallowed, other picks unaffected
- [x] 5 tests pass, 0 regressions in existing test suite (30/30 existing tests pass)
- [ ] After 14-day shadow run: produce B9-follow-up PR assessing Sharpe improvement
      using Wilson 95% lower bound on `adversarial_keep=true` vs `false` cohorts

# B9 Multi-AI Feedback — Claude (Primary) — 2026-05-04

## Item reviewed
B9 — TradingAgents wire-in (shadow): connect adversarial_debate.apply_to_picks
to the UEPS emitter as a 14-day shadow run (logs only, no filtering).

## A. Confirmed assumptions

1. **File path discrepancy found.** The action item doc lists
   `alpha_engine/long_term_pick_contract.py::emit_long_term_picks` as the
   hook point, but that function does NOT exist in the file. The file only
   contains `make_long_term_value_pick`, `make_swing_pick`, `is_long_term_value`,
   `is_swing`, `validate_long_term_pick`, and `evaluate_thesis_break`. The
   actual write path is `tools/run_ueps_pickers.py::run_screeners()` (builds picks)
   → `write_payload()` (writes ueps_picks.json). The correct hook is just after
   `long_screener.screen_universe()` returns `long_picks`, before the payload dict
   is assembled, in `run_screeners()`.

2. **adversarial_debate.apply_to_picks is shadow-safe.** It is a hard no-op when
   `UEPS_ADVERSARIAL_ENABLED` is unset or "0". It mutates in-place + returns the
   same list reference — never filters, only stamps `adversarial_score` /
   `adversarial_keep` fields. Dropping it into the UEPS emitter hot path is zero-risk
   when the flag is off.

3. **Existing env flag covers the gate.** `adversarial_debate.ENV_FLAG =
   "UEPS_ADVERSARIAL_ENABLED"` is the correct rollout gate. No new flag is
   needed; the existing `is_enabled()` check inside `apply_to_picks` provides the
   no-op guard.

4. **Wire-Up Rule satisfied.** `adversarial_debate.py` is an opt-in sidecar (its
   docstring says "NOT wired into any production pick path"). After B9 lands,
   `tools/run_ueps_pickers.py` becomes the production caller, fully satisfying
   the Wire-Up Rule. The module docs can be updated to reflect this.

5. **Existing test infrastructure to extend.** `tests/test_adversarial_debate.py`
   already covers the module in isolation with stub `http_post`. B9 should add
   `tests/test_ueps_adversarial_shadow.py` testing the integration call site in
   `run_ueps_pickers.py` — distinct from the unit tests so the two test layers
   don't interfere.

6. **No Cursor/FreeBuff ownership conflict.** The ownership lock (§6.6) covers
   `tradingagents_emitter.py`, `tradingagents_*.json`, workflow wiring, and
   resolver sources. B9 touches only `tools/run_ueps_pickers.py` +
   `alpha_engine/adversarial_debate.py` (indirectly). No conflict.

## B. Surfaced contradictions / blockers

1. **Hook point mismatch.** Corrected above: `run_ueps_pickers.py::run_screeners`
   is the correct location, NOT `long_term_pick_contract.py::emit_long_term_picks`.

2. **Shadow-mode doc clarification needed.** B9 says "14-day shadow run, logs
   only, no filtering." The `apply_to_picks` function stamps `adversarial_keep`
   as a boolean field on each pick, but it does NOT filter picks — that
   interpretation matches "shadow mode." However, the caller should add a
   `logger.info` summary so the operator can verify the debate is firing without
   checking raw JSON. One line after `apply_to_picks` suffices.

3. **adversarial_debate.py docstring is stale.** It says "No production caller in
   this commit. Wiring lands in a follow-up PR." After B9, this docstring should
   be updated to reference `tools/run_ueps_pickers` as the production caller.

## C. Recommended deltas to the action-item doc

- Correct "Files" entry: remove `alpha_engine/long_term_pick_contract.py::emit_long_term_picks`
  and replace with `tools/run_ueps_pickers.py::run_screeners` (after long_picks built).
- Add "update adversarial_debate.py module docstring" to the file list.
- Test plan is correct: extend `tests/test_adversarial_debate.py` OR add new file
  `tests/test_ueps_adversarial_shadow.py`. Recommend new file since the integration
  test concerns the call site, not the module internals.

## D. Net verdict: ready-to-ship

Implementation is a ~10-line change in `run_ueps_pickers.py` plus a new test file.
No blockers. B9 can ship now that V1 is ✅.

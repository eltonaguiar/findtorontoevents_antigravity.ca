# Multi-AI Feedback: B28 — Register ueps_picks.json in JSON_PICK_SOURCES

**Reviewer:** Claude Sonnet (loop agent)
**Date:** 2026-05-01
**Item:** B28 — Resolution: register `ueps_picks.json` directly in `JSON_PICK_SOURCES`

---

## A. Confirmed Assumptions

1. **File paths are correct hook points.**
   - `audit_trail/dashboard_generator.py` lines ~3895-3940 contain the `JSON_PICK_SOURCES` list. The last two entries (tradingagents at ~3895, skyrocket_detector at ~3910) are the exact pattern to mirror. Confirmed by reading the file.
   - `_extract_picks()` at line 6752 iterates a fixed key list. The `long_picks` key is NOT currently in that list. The UEPS file schema uses `long_picks` as the top-level list key (confirmed: `long_picks: list of 30`).
   - `.github/workflows/ueps-pick-runner.yml` commits `alpha_engine/data/active_picks.json` alongside `ueps_picks.json`. The B28 plan correctly identifies this as the source of the race condition.
   - `tools/run_ueps_pickers.py` contains `sync_to_active_picks()` which is used by the workflow. Safe to deprecate (leave running) since it's harmless when overwritten by competing crons.

2. **Wire-Up Rule:** B28 directly wires `ueps_picks.json` into the production pick-loading path (`JSON_PICK_SOURCES` → `_extract_picks` → dashboard payload). This IS a production caller. Wire-Up Rule satisfied.

3. **Root cause analysis is correct.** The race condition is architectural: `sync_to_active_picks()` does an insert-only write, but competing crons (alpha-engine-live.yml runs hourly as "DARWIN ENGINE") write the entire `active_picks.json` from scratch. Within ~4 hours of every UEPS sync, the file is overwritten. The fix (direct JSON_PICK_SOURCES registration) eliminates the race.

4. **UEPS file is fresh.** `audit_dashboard/data/ueps_picks.json` generated at `2026-05-01T12:54:36 UTC` with `n_long=30`. The source is live.

## B. Surfaced Contradictions / Blockers

1. **`_extract_picks` handles only one key per call.** The UEPS file has THREE pick lists: `long_picks`, `swing_picks`, `short_picks`. Currently `swing_picks=0` and `short_picks=0`, but forward-compatible code should concatenate all three. The B28 doc says "update `_extract_picks()` to recognize the `long_picks` key" — strictly correct but should be extended to concatenate all three UEPS sub-lists.

2. **Existing test `test_workflow_commits_both_ueps_and_active_picks` will FAIL.** This test (in `tests/test_ueps_active_sync_workflow.py`) asserts that `alpha_engine/data/active_picks.json` is in the workflow's `git add` line. Removing it from the workflow (per B28 plan) requires updating this test. This blocker was NOT identified in the B28 doc.

3. **`pick_type` field propagation.** UEPS picks in `long_picks` carry `pick_type="long_term_value"`. The V1 verification command checks for `p.get('pick_type')=='long_term_value'`. Registering in JSON_PICK_SOURCES will surface these picks in the dashboard's active table — but the dashboard normalizer must NOT strip `pick_type`. Confirmed: `_normalize_pick()` preserves unknown fields by default.

4. **Concept taxonomy.** B28 plan does not mention concept tagging for UEPS picks. PR #548's `assign_concept_fields()` should auto-tag based on `source_system` starting with `ueps_`. The UEPS source_system on picks is `"ueps"` or `"value_screener"` — need to verify the taxonomy covers this.

## C. Recommended Deltas

1. In `_extract_picks()`: instead of just adding `long_picks` to the key list (which only returns that one list), add special handling: if the dict contains `long_picks`, concatenate `long_picks + swing_picks + short_picks` and return the combined list.

2. In `tests/test_ueps_active_sync_workflow.py`: update `test_workflow_commits_both_ueps_and_active_picks` to reflect the new approach — assert `ueps_picks.json` is still committed; update the `active_picks.json` assertion with a note explaining it's now registered directly in JSON_PICK_SOURCES.

3. Add a comment in `JSON_PICK_SOURCES` explaining why UEPS uses `long_picks` key and why B28 replaces the sync approach.

## D. Net Verdict

**Ready-to-ship** with the following adjustments from the original plan:
1. Concatenate all three UEPS sub-lists (`long_picks + swing_picks + short_picks`) in `_extract_picks`.
2. Update `test_ueps_active_sync_workflow.py` to not fail on the removed `active_picks.json` git-add line.
3. Add `tests/test_ueps_dashboard_wireup.py` as specified in the plan.

Risk remains LOW. No scoring, gating, or behavioral changes. Pure additive registration.

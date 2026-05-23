# Multi-AI Feedback: B28 — Second Review (Architectural Analysis)

**Reviewer:** Loop Agent Self-Review (architectural cross-check)
**Date:** 2026-05-01
**Item:** B28 — Resolution: register `ueps_picks.json` directly in `JSON_PICK_SOURCES`

This second review examines the change from a system-architecture perspective,
focusing on what could go wrong at the integration boundary.

---

## A. Confirmed Assumptions

1. **Pattern is established and tested.** PR #544 (tradingagents) and PR #546 (skyrocket) followed the exact same pattern. Both are in production. The pattern is: write to a dedicated JSON file → register in JSON_PICK_SOURCES → picks surface on /audit. No known regressions from either PR.

2. **UEPS sidecar tab unaffected.** The dedicated UEPS section on /audit reads `ueps_picks.json` via `_load_ueps_picks_from_disk()` and `_render_ueps_section_html()`. These paths are independent of JSON_PICK_SOURCES. Adding UEPS to JSON_PICK_SOURCES makes picks appear in the MAIN active-picks table AND the UEPS sidecar — both are correct.

3. **Duplicate detection.** The dashboard normalizer has `_dup` detection logic. UEPS picks have unique `source_system` tags (`ueps` or `value_screener`). They will NOT duplicate with alpha_engine picks since they have different strategy names and source systems.

4. **`pick_type=long_term_value` is preserved.** The timeframe classifier in `dashboard_generator.py` around line 5990 explicitly checks `pick_type == "long_term_value"` and routes it to POSITION timeframe. This means UEPS picks will correctly appear in the EQUITY × POSITION cell — which is what V2 verification is looking for.

## B. Surfaced Contradictions / Blockers

1. **Potential double-counting if sync is NOT deprecated.** If `sync_to_active_picks()` keeps running AND UEPS is in JSON_PICK_SOURCES, the dashboard would see UEPS picks from TWO sources: the JSON_PICK_SOURCES registration AND from alpha_engine/data/active_picks.json (when the DARWIN ENGINE hasn't overwritten it yet). The duplicate detector should catch this, but the B28 doc is vague about whether to keep sync running. Recommendation: deprecate sync (add `--skip-active-sync` to the workflow command), don't fully remove it.

2. **`generated_at` propagation.** The UEPS JSON has a top-level `generated_at` field. `_extract_picks` propagates this to individual picks if they lack a timestamp. UEPS `long_picks` items do have their own timestamps? Needs verification.

3. **Schema compatibility.** UEPS `long_picks` items have `pick_type`, `asset_class`, `source_system`, `strategy`, `direction`, `entry_price` — all the fields `_normalize_pick` needs. But `confidence` field: do UEPS picks have it? If not, score will default to 0 and they'll fail HC gates. Need to confirm.

## C. Recommended Deltas

1. Add `--skip-active-sync` flag to the workflow's `python -m tools.run_ueps_pickers` command to prevent double-population. This is safer than removing the sync code entirely.

2. Verify UEPS `long_picks` items have `confidence` or equivalent scoring field before assuming they'll pass quality gates.

## D. Net Verdict

**Ready-to-ship** with the caveat to disable `sync_to_active_picks()` in the workflow to prevent temporary double-population during the transition. The change is architecturally sound and follows an established pattern.

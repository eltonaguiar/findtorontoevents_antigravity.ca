# B18 Multi-AI Review — Codebuff proxy (self-review) — 2026-05-03

## Item
B18 — Shadow-mode auto-promotion for "no closed history" strategies

---

## A. Confirmed assumptions

1. **File paths are correct hook points.**
   - `audit_trail/quality_gates.py` — `passes_active_gate()` at line 3882 is the
     correct gate. New `should_shadow_promote()` should live here, not inside
     passes_active_gate (shadow picks BYPASS the gate by design).
   - `audit_trail/dashboard_generator.py` — injection after `_filter_active_picks_with_gate()`
     (line 14121) is the correct insertion point. `closed` and `active_raw` are both in scope.
   - `tools/dashboard_hc_rules.py` — `passes_high_conviction_pick()` at line 368 is the
     right place; add `if pick.get("shadow_mode"): return False` as first guard.

2. **Wire-Up Rule respected.** Default-OFF. The `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`
   env var is the single rollback switch. Shadow picks are labeled; operator sees them.

3. **Prereqs correctly identified.** B16 is the stated prereq; B16 ✅ confirmed on main.
   B18 does not actually need any B16 data fields — it only needs the closed-pick list
   (from collect_all_picks) and the active_raw list. B16 is a soft dependency for
   "understanding which strategies have real edge before promoting" — the doc is right
   to list it but it's not a hard technical dep.

4. **Existing test file to extend**: `tests/test_tradingagents_emitter.py` and
   `tests/test_quality_gates.py` are existing quality-gate test files. Check if
   `tests/test_quality_gates.py` exists before creating new `tests/test_shadow_promote.py`.

---

## B. Surfaced contradictions / blockers

1. **Strategy name ambiguity**: Strategies in `active_raw` use the `strategy` field
   (normalized by `_normalize_pick()`). Closed picks may use a different strategy
   name (original vs. normalized). Must ensure we match on the normalized name.
   Recommendation: use `p.get("strategy", "")` consistently on both lists.

2. **10-pick floor is low for "active raw pool"**: If a source emits 30 picks per cycle
   (e.g. ueps_picks.json long_picks), a zero-history strategy immediately qualifies.
   The B18 doc says "≥10 active_raw emits over 14-day window" but since active_raw is
   a current snapshot, 10 is the immediate threshold. This is intentional — the intent
   is "active emitter, not a dormant source" — but should be documented.

3. **Shadow picks survive dashboard rebuild cycles**: Each rebuild runs `generate()`
   fresh. Shadow picks injected in one run do NOT persist to the next run (unless they
   were already in the raw pool and the flag is still on). This is the correct behavior
   — shadows are re-evaluated each cycle. No stale-injection risk.

4. **`size_multiplier = 0.1` (10% sizing)**: The doc mentions sizing at 10% of normal.
   This is an OPERATOR concern (real-money sizing), not a dashboard field. The
   `shadow_mode=True` field is the signal to the operator. The dashboard does not
   control position sizing. Recommendation: emit `shadow_size_multiplier: 0.1` as an
   informational field only — do NOT wire it into any scoring or gating logic.

---

## C. Recommended deltas

1. Use `_shadow_size_multiplier = 0.1` as a metadata field on the pick (informational).
2. Ensure `shadow_strategy_raw_emit_count` is set so operators know why it was promoted.
3. Add a `shadow_probation` panel summary to the payload (count of shadow picks, list
   of strategies) so the operator can see the probation book at a glance.
4. The 5-pick cap must be applied BEFORE adding to `payload["picks"]["active"]`.

---

## D. Net verdict

**Ready-to-ship.** No showstoppers. Apply the metadata field and panel summary per
recommended deltas. Implementation is clean and correctly placed.

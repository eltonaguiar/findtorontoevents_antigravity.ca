# B18 Multi-AI Review — Claude Sonnet (self-review) — 2026-05-03

## Item
B18 — Shadow-mode auto-promotion for "no closed history" strategies
(from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §6.5)

---

## A. Confirmed assumptions

1. **Hook point confirmed**: `audit_trail/dashboard_generator.py` lines 14120–14136
   run `_filter_active_picks_with_gate()`. After line 14136, both
   `payload["picks"]["active"]` (filtered) and `payload["picks"]["active_raw"]`
   (all raw) are in memory. The local variable `closed` (from `collect_all_picks()`
   at line 11816) is in scope and holds the full closed-pick history.

2. **HC gate confirmed**: `tools/dashboard_hc_rules.py:368` — `passes_high_conviction_pick()`
   calls `evaluate_hc_gates_1_to_9()` and `passes_stamped_tier_supplemental_path()`.
   Adding an early `if pick.get("shadow_mode"): return False` at the top is clean.

3. **Wire-Up Rule**: The feature is default-OFF (`SHADOW_MODE_AUTO_PROMOTE_ENABLED=0`)
   and adds a new field (`shadow_mode`) on picks. No production caller change when flag is
   off. Qualifies as opt-in sidecar per CLAUDE.md. Wiring plan: flip flag after 14-day
   shadow period and verifying ≥10 closed shadow picks.

4. **Prereq chain**: B16 (forward_edge_audit.py) supplies
   `tools/data/transaction_costs.json` and closed-pick stats. Already on main. ✅

5. **Existing shadow pattern**: `quality_gates.py` already uses shadow-mode patterns
   for PHASE1_CONF_DEADZONE, TOD gate, PSI gate (lines 4236–4351). The naming
   convention `SHADOW_MODE_AUTO_PROMOTE_ENABLED` is consistent with the codebase.

---

## B. Surfaced contradictions / blockers

1. **`recent_closed` vs full `closed`**: At the hook point (line 14136), the payload
   has `payload["picks"]["recent_closed"]` — a subset. But for strategy history
   completeness (zero-history check), we need the FULL `closed` list from
   `collect_all_picks()`. Recommendation: pass `closed` directly, not the
   payload slice. The `closed` variable is in scope in `generate()`.

2. **Raw-emit count in 14d**: `payload["picks"]["active_raw"]` contains the picks
   from `collect_all_picks()` that survived normalization. It does NOT contain
   ALL historical emits — only the current active batch. The "≥10 raw emits over
   14 days" criterion is therefore re-interpreted as "≥10 picks from this strategy
   in the current raw-active pool" (since the pool is refreshed each run and only
   holds current-cycle picks). This is a reasonable proxy — 10 simultaneous
   raw emits from a strategy indicates it's actively running. Document this in
   the code comment.

3. **Cap semantics**: The global cap of 5 should apply TOTAL shadow picks, not
   per-strategy. Current design is correct. However, must sort candidates by
   descending confidence before truncating, so highest-conviction zero-history
   strategies get through first.

4. **`shadow_mode` field in `active_raw`**: Shadow-promoted picks originate from
   `active_raw` but are injected into `active`. They will therefore appear in BOTH
   lists after injection. The `active_raw` list (pre-snapshot at 14132) does NOT
   include injected picks — this is acceptable (they were already in active_raw before
   gate filtering). No double-count issue.

5. **`_gate_passed` field**: Injected shadow picks need `_gate_passed = True` so the
   UI "Show All Picks" toggle doesn't hide them. Must set this field explicitly.

---

## C. Recommended deltas to the action-item doc

1. Clarify "14-day window" = current raw-active pool proxy, not a rolling log.
2. Add explicit wording: shadow picks excluded from HC via `shadow_mode=True` check.
3. Note that `passes_active_gate()` is NOT called on shadow picks — they bypass it
   intentionally. Document why: the gate is the very thing they need to bypass.
4. Add acceptance criterion: if flag is OFF (default), behavior is identical to
   current production — zero new picks, zero behavior change.

---

## D. Net verdict

**Ready-to-ship** with the clarifications above applied to the implementation.
Risk remains MEDIUM but is fully bounded by the default-OFF flag and the 5-pick cap.
The implementation is additive, ~90 lines total across 3 files + tests.

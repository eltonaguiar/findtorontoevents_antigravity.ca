# B19 Multi-AI Feedback — Self-review (Claude Sonnet, 2026-05-02)

Item: **B19 — Pair-level exception carve-out for proven (strategy, symbol) pairs**

## A. Confirmed assumptions

1. **File paths correct.** `audit_trail/quality_gates.py` is the right hook
   — `passes_smart_gate()` is where the `atr_percentile_gate BTCUSDT LONG`
   pick is rejected (R:R=0.91 < SMART_PICKS_MIN_RR=1.5). Confirmed via live
   test: `passes_active_gate()` returns True, `passes_smart_gate()` returns
   False.

2. **Initial registry candidate verified.** `atr_percentile_gate BTCUSDT LONG`:
   n=25, WR=84.0%, Wilson 95% lb=65.3% (recomputed from `recent_closed` in
   `audit_dashboard/data/dashboard_data.json`). Exceeds the B19 thresholds
   (Wilson lb ≥ 60%, n ≥ 20).

3. **EV is positive despite R:R < 1.** With WR=84% and R:R=0.91:
   `EV = 0.84×0.91 - 0.16×1 = 0.765 - 0.16 = +0.605` per unit risk.
   Blocking this pick on R:R alone is incorrect — the R:R gate assumes
   ~50% WR baseline, which doesn't hold for this specific pair.

4. **Wire-Up Rule satisfied.** `pair_exceptions.py` is called directly from
   `passes_smart_gate` — which is in the production pick/score path (called
   from `dashboard_generator.py:_filter_smart_picks`). Not an orphan module.

5. **Strategy-level vs pair-level stats.** `atr_percentile_gate` has ALL 25
   closed picks from BTCUSDT (not diluted by alt-coins). The B19 doc's
   claim about "alt-coin emissions dragging the average down" appears to
   describe a future scenario if the strategy emits on other symbols.
   Current state: single-symbol strategy failing smart gate due to R:R.

## B. Surfaced contradictions / blockers

1. **`_gate_passed=False` in `active` not in `active`**: The pick passes
   `passes_active_gate()` in isolation but has `_gate_passed=False` in
   the dashboard JSON. The most likely cause: the second `_filter_active_picks_with_gate`
   call at line 13973 runs after late-stage score mutations that may have
   penalized the pick's score or added a blocking flag. The carve-out in
   `passes_smart_gate` will not fix this; if the goal is `/audit` table
   visibility, the carve-out also needs to be in `passes_active_gate`.
   **Recommendation**: add to BOTH gates with the same env-flag guard.

2. **`derives_pair_exceptions.py` week-cron needed**: Without a weekly
   auto-derive tool, new entry candidates are manual-only. Low urgency
   for the initial PR but should ship in the same commit to prevent orphan
   module syndrome.

3. **No auto-add**: The B19 doc says "new entries require operator sign-off
   via a doc-only PR (NOT auto-merging)." Implementation MUST enforce this
   by using a hard-coded registry in Python (not a JSON config that could be
   auto-written by a cron). This is already in the proposed design.

## C. Recommended deltas to the action-item doc

1. **Scope**: Add `passes_active_gate` as a second carve-out site (not just
   smart gate). Tag exceptions with `exception_carve_out=True` in both.

2. **Default-OFF env flag**: `PAIR_EXCEPTION_CARVE_OUT_ENABLED` defaults to
   `"0"` — operator must explicitly flip to `"1"` after verifying the initial
   candidate list. This differs from some other gates that default-on.
   Rationale: new gate pattern, conservative default.

3. **Test coverage**: Extend `tests/test_quality_gates.py` (reuse-existing)
   rather than new file, to confirm:
   - carve-out pick with flag OFF → still filtered by smart gate
   - carve-out pick with flag ON → passes smart gate + tagged
   - non-registry pick → unaffected

## D. Net verdict: **ready-to-ship**

All prerequisites met. Risk is LOW-MEDIUM (additive bypass, default-OFF, hard-coded registry). The initial registry candidate is statistically verified. Implementation can proceed.

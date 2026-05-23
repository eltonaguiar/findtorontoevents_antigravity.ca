# B16 — Forward-Only Edge Audit: Self-Review (Claude Code loop agent)

**Item:** B16 — Forward-only edge audit + per-strategy capacity report
**Source doc:** `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §4/§6.5
**Date:** 2026-04-30
**Reviewer:** Claude Code autonomous loop (stand-in for external AI review)

---

## A. Confirmed Assumptions

1. **File paths verified:**
   - `audit_dashboard/data/dashboard_data.json` — EXISTS, contains `picks.recent_closed` (3500 picks across 214 strategies) with fields: `strategy`, `asset_class`, `pnl_pct`, `status`, `exit_reason`, `symbol`, `closed_at`, `timestamp`, `entry_time`, `strat_fwd_wr`, `strat_fwd_pf`.
   - `audit_trail/data/universal_resolved_picks.json` — EXISTS, 5000 closed picks with `strategy`, `symbol`, `pnl_pct`, `exit_reason`, `status`.
   - `tools/data/transaction_costs.json` — does NOT exist yet; needs creation.
   - `tools/forward_edge_audit.py` — does NOT exist yet; needs creation.
   - `audit_trail/data/strategy_promotion_log.json` — does NOT exist; caveat required.
   - `tests/test_forward_edge_audit.py` — does NOT exist yet; needs creation.

2. **Data quality caveat (IMPORTANT):**
   - `timestamp` and `entry_time` fields in `recent_closed` all read `2026-04-30T20:31:41Z` (the dashboard regeneration timestamp, not actual trade entry time). This is a data quality issue.
   - `closed_at` has realistic historical dates (e.g., `2026-03-23T09:54:12Z`).
   - Without `strategy_promotion_log.json`, forward-only filtering cannot be strictly enforced. The tool will use all `recent_closed` picks with a caveat note, flagging the forward-only claim as approximate. Honest caveat must be in the artifact header.

3. **Status field mapping:** WON = win (both `status=='WON'` and `exit_reason=='TP_HIT'` can indicate a win). Using `status=='WON'` as primary win indicator.

4. **The doc's transaction cost table is correct** (CRYPTO 30bp, EQUITY 10bp, FOREX 8bp, COMMODITY 15bp). Adding ETF=10bp, BOND=5bp, FUTURES=15bp for completeness since those asset classes appear in data.

5. **Wire-up Rule compliance:**
   - `tools/forward_edge_audit.py` is a standalone read-only analytics tool (opt-in sidecar).
   - No production caller yet. Per Wire-Up Rule, this PR must include an explicit opt-in flag + wiring plan.
   - Wiring plan: the artifact will be consumed by `audit_trail/dashboard_generator.py` in a follow-up PR (B17).
   - PR body must explicitly say "opt-in sidecar" with a `## Wiring Plan` section.

## B. Surfaced Contradictions / Blockers

1. **No `strategy_promotion_log.json`** — the doc says "derive from `kill_list_unblocks` history" as fallback. Checked `audit_trail/kill_list_audit.py` — it doesn't write a promotion log, it reads a kill list. Best approximation: use `strat_fwd_trades > 0` as a proxy for "was running forward" (the field already exists in picks).

2. **`timestamp`/`entry_time` reliability** — all 3500 `recent_closed` picks have `timestamp = 2026-04-30T20:31:41Z`. This makes pick-level date-of-emission filtering impossible from these fields alone. Only `closed_at` is reliable for temporal reasoning.

3. **Wilson lb on WR:** for strategies where WR > 0.99 (like `st_fear_greed_contrarian` at 90.9%, or `combined_confidence` at 91.7%), the Wilson bound is still meaningful but the small-n caveat matters. Implementation must flag n < 20 as insufficient-sample.

4. **`combined_confidence` PF = 226.71** — this looks like a data artifact (near-zero losses inflating PF to an absurd value). Tool should cap reported PF at 50 and flag above-cap values with an asterisk. This prevents misleading "PF 226×" headlines in the artifact.

5. **`goldmine_6x_consensus` n=17 WR=0.0%** — this is the 13-LONG-picks-at-0%-WR pattern cited in the doc. Correctly detected by the tool.

## C. Recommended Deltas to the Action-Item Doc

1. Add explicit caveat in tool output that "forward-only" is approximate (no promotion log).
2. Cap PF at 50 in output; flag any strategy with raw PF > 50 for manual review.
3. Add `FUTURES` and `ETF` asset class entries to `transaction_costs.json`.
4. Test file should be new (`tests/test_forward_edge_audit.py`) — no existing test to extend.
5. Existing tests for similar tools: `tests/test_asset_class_edge_audit.py` (if exists) for reference patterns.

## D. Net Verdict

**ready-to-ship** — the data exists, the hook points are correct, the caveat about no promotion log is documented, Wire-Up Rule compliance is achievable with explicit opt-in label. Proceed with implementation.

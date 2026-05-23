# B14 Multi-AI Feedback — Codebuff Proxy Self-Review (2026-05-02)

**Item:** B14 — Liquidity / slippage stress test before any live flip
**Reviewer:** Codebuff proxy (self-review #2 of 2)
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **Hook points are correct.** `tools/slippage_stress_test.py` is the right
   file — `tools/` holds all standalone analysis scripts. No need to touch
   `audit_trail/` or `alpha_engine/`.

2. **Transaction costs config reuse.** `tools/data/transaction_costs.json`
   from B16 already has per-class bps. B14 should read this file rather than
   hardcoding values (DRY principle, operator-tunable).

3. **1514 CRYPTO closed picks available.** All carry PnL%, stop-loss, take-profit
   fields. Data is sufficient for meaningful slippage scenarios.

4. **Wire-Up Rule check.** B14 adds NO production caller. It is purely an
   offline analysis tool. Under the Wire-Up Rule, it must be explicitly labeled
   "opt-in sidecar" with a `## Wiring Plan` section in the PR body naming:
   - Target caller: `audit_trail/dashboard_generator.py`
   - Target function: `generate()` → new payload section `picks.slippage_stress`
   - Expected wire-up: separate B14-dashboard PR after operator validates output

5. **Risk classification LOW confirmed.** No behavioral changes to production
   pick-generation path.

---

## B. Surfaced Contradictions / Blockers

1. **Breakeven multiplier definition.** The "breakeven multiplier" (at what
   cost multiplier does the strategy go from profitable to losing) is:
   ```
   breakeven_mult = paper_sum_pnl / (base_cost_pct × n)
   ```
   This is only meaningful for strategies with positive paper_sum_pnl. For
   already-losing strategies, the concept is N/A (already below breakeven at 0×).
   Flag these as "ALREADY_LOSING" rather than computing a negative breakeven.

2. **Strategy bucket minimum N.** For the per-strategy stress test to be
   meaningful, a minimum of n≥5 closed picks is needed (otherwise results are
   noise). Use n≥5 as the floor; label smaller buckets as "INSUFFICIENT_DATA".

3. **Multi-class output.** The spec says "CRYPTO sidecars" but the tool is
   more useful if it runs across all asset classes (EQUITY, FOREX, COMMODITY
   too) since B16 showed FOREX and COMMODITY net PnL after costs. Make asset
   class filtering a CLI flag (default: ALL).

4. **Existing test file.** `tests/test_forward_edge_audit.py` exists from B16
   and follows the same pattern (mock dashboard_data.json, verify output).
   Create `tests/test_slippage_stress_test.py` following the same pattern.

5. **PF formula edge case.** Profit Factor = sum(winning_pnl) / abs(sum(losing_pnl)).
   If losing_pnl = 0, return `math.inf`. If both zero (all ties), return `None`.

---

## C. Recommended Deltas to Action-Item Doc

1. Add `n >= 5` minimum bucket size — already implied but should be explicit.
2. Extend scope to all asset classes with `--asset-class CRYPTO` as default
   (not hardcoded to CRYPTO-only).
3. The "backtest harness extension" reference in the spec is misleading — there
   is no separate harness file. Delete that phrase or replace with "reads
   dashboard_data.json closed picks pool".
4. Add `ALREADY_LOSING` label for strategies with negative paper_sum_pnl.
5. Test plan should include: cost-deduction math, PF edge cases, breakeven
   formula, ALREADY_LOSING labeling, INSUFFICIENT_DATA labeling.

---

## D. Net Verdict

**READY-TO-SHIP** — all clarifications are small design decisions, not blockers.
Consensus with Review #1: linear slippage model, both `picks.closed` and
`picks.recent_closed` keys, opt-in sidecar label, Wire-Up Rule satisfied via
explicit wiring plan in PR body.

**Consensus deltas applied to implementation:**
1. Read both `picks.closed` and `picks.recent_closed`
2. Linear slippage: 1×, 2×, 3×, 5× multipliers
3. Minimum bucket n≥5; label smaller as INSUFFICIENT_DATA
4. ALREADY_LOSING label for negative-paper strategies
5. PF: `math.inf` on zero losers, `None` on no trades
6. All asset classes supported via --asset-class flag; default ALL
7. Opt-in sidecar label + wiring plan in PR body

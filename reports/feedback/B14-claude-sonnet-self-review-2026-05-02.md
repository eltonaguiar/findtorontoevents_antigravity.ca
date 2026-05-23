# B14 Multi-AI Feedback — Claude Sonnet Self-Review (2026-05-02)

**Item:** B14 — Liquidity / slippage stress test before any live flip
**Reviewer:** Claude Sonnet (self-review #1 of 2)
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **File paths correct.** `tools/slippage_stress_test.py` is the right location
   (peer pattern: `tools/forward_edge_audit.py`, `tools/source_liveness_watchdog.py`).
   `tools/data/transaction_costs.json` already exists from B16 with per-class costs
   (CRYPTO 30bp, EQUITY 10bp, FOREX 8bp, COMMODITY 15bp).

2. **Data source confirmed.** `audit_dashboard/data/dashboard_data.json` has 1514
   CRYPTO closed picks, all carrying `entry_price`, `take_profit`, `stop_loss`,
   `pnl_pct`, `exit_reason`, `strategy`, `asset_class`, `direction`. B14 can run
   on this dataset without needing new data collection.

3. **Wire-Up Rule satisfied.** B14 is a read-only offline analytics tool. Per
   CLAUDE.md, it must be labeled "opt-in sidecar" with a wiring plan naming the
   target caller file + function + expected PR/date. Target: a future dashboard
   panel (B16 pattern — `forward_edge_audit.py` was an opt-in sidecar that became
   the source for B17's `stamp_after_cost_fields()`). This PR is correctly labeled
   opt-in sidecar.

4. **Prereqs correctly identified.** The spec says "None" — confirmed. The tool
   reads already-existing dashboard_data.json and transaction_costs.json.

5. **Risk classification LOW.** Offline read-only tool; does not touch
   production pick scoring or gate logic. Confirmed LOW.

6. **Test plan reasonable.** Existing test file to extend: none directly, but
   `tests/test_forward_edge_audit.py` (from B16) shows the pattern. Create
   `tests/test_slippage_stress_test.py` as new file (B16 precedent).

7. **"Backtest harness extension" clarified.** There is no formal backtest
   harness in this repo. "Extension" means the tool reads closed picks from
   `dashboard_data.json` which are the de facto backtest results. No separate
   harness file needs modification.

---

## B. Surfaced Contradictions / Blockers

1. **"2× volume-spike" ambiguity.** The spec says "simulate 2× volume-spike
   scenarios" but doesn't specify the market impact model. Two options:
   - **Linear model:** 2× position = 2× slippage (worst case, conservative)
   - **Square-root model:** 2× position = √2 × slippage ≈ 1.41× (standard
     Almgren-Chriss / Kyle market impact)
   **Resolution:** Use linear model as the conservative stress test scenario.
   Document the assumption explicitly. The square-root model is a footnote for
   a future upgrade.

2. **"CRYPTO sidecars (#525, #527)"** — PRs #525 and #527 were the vol-targeted
   sizer and CRYPTO sidecar PRs. Since the tool runs across all strategies, we
   can add a `--sidecar-filter` flag to narrow to vol_targeted_sizer strategies,
   but it's not required for V1. The tool should work on all CRYPTO picks by
   default.

3. **`dashboard_data.json` has 0 closed picks in the current run's data
   structure.** Wait — the earlier Python check showed `d.get('picks',{}).get('closed',[])` 
   returned 0 items, but `d.get('picks',{}).get('recent_closed',[])` wasn't tried.
   The 1514 picks were found in `picks.closed` in a separate check. Need to
   handle both `picks.closed` and `picks.recent_closed` keys.

4. **Profit Factor denominator trap.** If all trades in a bucket are winners
   (sum of losing PnL = 0), PF is undefined (division by zero). Must cap or
   label as "∞".

---

## C. Recommended Deltas to Action-Item Doc

1. Clarify that "2× volume-spike" uses linear market impact model (conservative).
2. Mention the tool handles both `picks.closed` and `picks.recent_closed` keys.
3. Add `--asset-class` and `--sidecar-filter` flags as optional CLI args.
4. Explicitly label output as "opt-in sidecar" per Wire-Up Rule.
5. Test plan: at minimum, test the cost-deduction math, PF computation, and
   breakeven multiplier calculation.

---

## D. Net Verdict

**READY-TO-SHIP** with the above deltas applied:
- Read `picks.closed` OR `picks.recent_closed` (whichever exists)
- Apply linear slippage model at 1×, 2×, 3×, 5× multipliers
- Output Markdown artifact + JSON index for future dashboard wiring
- Label clearly as opt-in sidecar with wiring plan pointing to dashboard_generator.py

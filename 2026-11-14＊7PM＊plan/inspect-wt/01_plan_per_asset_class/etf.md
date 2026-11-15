# ETF — plan to profitability

**State:** sparse upstream (PF ~1.24, WR ~55%, n~87 historically; **zero live picks**;
SPY sometimes miscategorized as equity). Two roles: (a) the *deployment vehicle* for the
MF sleeve (daily-NAV share classes of the same idea — see `mutual_funds.md`), (b) one
candidate for tactical selection.

## Path A — as the sleeve's implementation (shares the MF sleeve gate)
ETFs are where the rotation engine actually trades (daily NAV, liquid, cheap). Same gates:
net Sharpe ≥ 0.7, MDD ≤ 20%, beat 60/40 on Calmar. Probability follows the sleeve: 60-70%
for positive net return; ~25-35% to beat SPY full-cycle (it won't — by design).

## Path B — tactical ETF rotation (ONE pre-registered trial)
- **Hypothesis:** monthly relative-strength among 6-8 sector/style ETFs (XLK/XLE/XLF/XLU/
  XLV/… or VTI/VEA/VTV/MTUM-class), top-2, absolute-momentum filter, costs 0.05%/side.
- **Gate (benchmark-relative):** excess Sharpe vs SPY ≥ 0.2 over ≥24 months forward, MDD ≤
  SPY's, PF ≥ 1.15 net, n ≥ 100 monthly decisions... note: monthly n accrues slowly
  (12/yr → 24 months = 24 decisions) — so the gate must be **decision-level bootstrap +
  excess-return t-test**, not trade-n. Pre-register which.
- **Known failure mode to test first:** sector rotation churns in regime transitions
  (2022: energy leadership flip; 2024-26 AI concentration). Include the worst regime as a
  standalone reported window.
- SubQ: ETF style = longterm (conf 0.50), obstacle = competition (0.64) — consistent with
  "crowded, do it only as cheap beta or with a slow signal".

## Fixes required before any test
1. Classify SPY correctly (equity vs ETF contamination in the ledger — B7-adjacent hygiene).
2. Upstream feed coverage: the class produced **zero live picks** — a strategy with no
   emission path cannot be forward-tested; fix `etf_strategies.py` routing first.
3. n=87 < floor — accumulate under QA gates before any claim.

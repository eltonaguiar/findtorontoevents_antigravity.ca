# COMMODITY / FUTURES — plan to profitability

**State:** historical PF ~1.78, WR ~47%, n~750 (best-looking historical class), but
execution/roll costs and per-instrument thin n block it; COMMODITY emission was blocked
(422% cost/PnL ratio in the focus screen). COT test **failed 4/4** (honestly reported —
do not silently re-test). SubQ: P(2y) = 25-40% band (1.63), style = position (0.56),
obstacle = competition/costs (split).

## The ONE hypothesis (pre-registered)
CTA-style trend on 8-12 liquid futures (ES, NQ, CL, GC, ZN, 6E, ZC, HG class):
- monthly rebalance, Donchian/200-day hybrid exit (one rule, no per-instrument tuning);
- **costs from actual roll schedules** (back-adjusted contracts — the #1 reason retail
  futures backtests lie: continuous contracts hide roll cost);
- gate: **net PF ≥ 1.3, n ≥ 100 trades across instruments**, beats the Bloomberg/BCOM
  commodity index on Calmar, Sharpe ≥ 0.6 net, both-halves PF > 1.0.

## Why this class might actually work (grounded)
- Trend following has the longest real-money track record of any family (CTAs, 40+ years;
  SubQ evidence 4.23/5 "academic + real money") and its *failure mode* (choppy sideways
  markets) is visible and survivable rather than silent.
- The class's historical PF 1.78 with WR 47% is exactly the signature of trend following
  (many small losses, fewer big wins) — i.e., the historical number is *coherent* with the
  strategy family, unlike e.g. forex's PF 0.27 which was incoherent with its own costs.

## Risks / known failure modes to pre-register
- 2010s decay: CTA trend Sharpe compressed post-2010; the test must include the
  2015-2020 decay window as a standalone reported regime.
- Capacity: fine at our size; slippage on thin contracts (ZC, HG) must come from data,
  not assumption.
- COT as a *feature*: one pre-registered test only (previous one failed 4/4 — a re-test
  needs a documented reason, e.g., different horizon or as a filter on the trend signal,
  counted as a new trial).

## Gate order
Execution/roll-cost model → single trend hypothesis → forward paper ≥24 months →
benchmark-relative gates (index + SPY on risk basis) → capital.

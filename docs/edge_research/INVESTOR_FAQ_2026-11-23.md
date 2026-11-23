# Investor FAQ — what to buy, how to buy it, and what to expect

**Date:** 2026-11-23T10:36Z · **Author:** Kilo. **Buying/planning analysis (beta), not prediction, not advice.**
Real data 2021-11-15→2026-11-13 (1,254 daily returns). Tools: `tools/fund_deep_dive.py`, `tools/deployment_analysis.py`.

## Q: What should I hold?
A broad, low-cost index fund — same beta as any "signal" in this programme, cheaper:
- Tax-sheltered account (TFSA/RRSP/Roth/IRA): **FXAIX (0.015%)** or **FZROX (0.00%)** index mutual funds.
- Taxable account: **SPY/VOO** (S&P 500) or **VTI** (total market) ETFs — more tax-efficient (fewer cap-gains distributions).
- Choose on **cost and tax** (deterministic), **not** trailing returns (statistically indistinguishable — CIs overlap).

## Q: Mutual fund or ETF?
Same index ⇒ same beta (measured corr 0.995–0.998). Index MFs *can* distribute capital gains (tax drag in taxable);
ETFs mostly don't. In a sheltered account the tiny fee edge of a sub-0.05% index MF is clean; in a taxable account prefer
the ETF. (The old "MF beats ETF" framing is **retracted** — see F4: it's a fee effect within tracking noise.)

## Q: Lump sum or dollar-cost average?
In **this** window, DCA won: $10k lump in SPY ended **$17,174** vs DCA **$19,003** (lump −9.6% vs DCA), because DCA bought
the 2022 dip. **But that is period-dependent** — in a steady rising market lump-sum usually wins. Honest rule: DCA reduces
*regret/timing risk*; it is not systematically superior. If a lump sum would keep you awake, DCA over 6–12 months.

## Q: How bad can it get, and how long to recover?
- SPY **max drawdown −24.5%** (peak 2022-01-03 → trough 2022-10-12), **recovered 2023-12-13** — **~14 months after the
  trough, ~23 months after the peak.**
- Rolling 12-month SPY returns over the window ranged **−19.8% to +43.4%**, median **+17.9%**.
- **You must be able to stay invested through a ~25% loss and a multi-year wait.** If not, **60/40** (6.85%/yr, −20.7% DD).

## Q: Why does the fee matter so much?
30-year compounding, 7% gross, per $100,000:
| expense ratio | ends at |
|---|---:|
| 0.03% | **$754,849** |
| 0.50% | $661,437 |
| 1.80% | **$457,585** |

A 1.8% fund ends with **~39% less** than a 0.03% fund. The fee is the single most controllable variable.

## Q: Are bonds worth it?
Over 2021–26, BND returned **−0.32%/yr** (a rate-hike artifact) but cut the 60/40 drawdown to −20.7% and has low
correlation to stocks. For a **forward** view, use the **current yield-to-maturity**, not the last 5 years.

## Q: What about the programme's own picks?
They are **beta-dominant** with **no alpha demonstrated above the gate's detection floor** (0/362 cells pass the alpha
gate; the gate is sound but underpowered for small alpha). The index fund delivers the same beta more cheaply, so **do not
chase the signals** — buy the fund.

## Q: Can anyone predict the market?
**No — that is the answer this whole body of work supports.** We can *plan* (diversify, control costs, size risk to your
drawdown tolerance); we cannot *predict*. The question "which fund should I buy" is answerable; "what will stocks do" is not.

## Caveats
5-year, bull-heavy window; past ≠ future; taxes unmodelled; US-only (no international data locally); futures/options
out of scope. Not investment advice.

*Paper only.*

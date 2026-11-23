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
**Lump-sum wins historically — DCA is a behavioural device, not a return strategy.** A rigorous audit on **SPY, 1993–2026,
346–46 monthly start dates** (same total, same terminal date) found DCA beats lump-sum only **~20–22% of the time** over
5–20y holds and **6.5%** over 30y; 36-month DCA **never** beat lump-sum in any 30-year start (46/46) and ended **27% lower**.
Mechanism: markets trend up, so later money buys fewer shares.
**My own earlier note ("DCA won") was a single-window artifact** — the 2021–26 window contained the 2022 dip, one of the ~20%
of starts where DCA wins. **Correct rule:** invest the lump sum now if you have it; use DCA only because you *don't* have the
lump sum, or to manage panic risk — not because it earns more. (Credited: operator audit `8ae518e`, `dca_vs_lumpsum.py`.)

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

---

## More measured facts (v2, 2026-11-23T10:39Z)
- **Volatility drag:** SPY arithmetic mean 12.46%/yr but geometric (actual) 11.59% — **0.88 pp/yr lost to volatility** at 17.3% vol. Plan on the *geometric* number, never the average.
- **Diversification works:** SPY–BND correlation **0.21** over this window — bonds moved largely independently, which is why 60/40 cut the drawdown.
- **Drawdowns are common, not rare:** SPY spent **24.2% of trading days more than 10% below its high**, and **3.0% of days more than 20% below**. Expect to be "underwater" a meaningful fraction of the time.
- **Staying invested is the whole game:** buy-and-hold returned **+72.6%**; **missing the best 10 days** dropped it to **+16.8%**. Timing out is far more costly than a drawdown.
- **Fee compounding (per $100k, 7% gross):**
  | MER | 10y | 20y | 30y |
  |---|---:|---:|---:|
  | 0.03% | $196,164 | $384,804 | **$754,849** |
  | 0.50% | $187,714 | $352,365 | $661,437 |
  | 1.80% | $166,019 | $275,623 | **$457,585** |
- **Rolling 12-month SPY returns:** worst **−19.7%**, best **+43.6%**, median **+18.1%** — a wide band; single years tell you nothing.

**Takeaways for the plan:** hold the cheap index fund; expect frequent >10% underwater periods and occasional >20% ones; **do not time out** (missing 10 days cut 72.6%→16.8%); the fee is worth more than any timing attempt.

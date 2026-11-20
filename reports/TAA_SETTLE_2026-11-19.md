# TAA settlement — did the "Sharpe 0.88 / MaxDD −19%" claim reproduce? (2026-11-19)

**Verdict: NOT REPRODUCED — on both legs, across all 192 lagged cells.**

The claim under test, from copilot's money-maker plan (sourcing
`reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`):

> top5-6m rotation 2007-2026 Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs −51%, positive in all 3
> time-thirds

Pre-registered success criterion (written into the tool before the run,
`SETTLE_CRITERION` in `tools/taa_settle_sweep.py`): *≥1 cell with **lag = 1 month** and
**cost ≥ 5 bps** reaching **Sharpe ≥ 0.88 and MaxDD ≥ −19%** over 2007-2026.*

Zero of 576 cells met it. The best lagged cell in the claim's own window reaches **Sharpe 0.795**
at 5 bps, with a **−41.7%** drawdown on the sectors universe or **−23.8%** on the broad universe —
so the claimed Sharpe is 0.085 above the entire grid's maximum, and the claimed drawdown is 4.7
points better than anything measured.

## Method

- `tools/taa_settle_sweep.py`, monthly bars, **total return** (`auto_adjust=True`, dividends
  included). This is generous to the claim: a price-only series would make rotation look worse.
- Two universes: `sectors_11spdr` (XLB XLE XLF XLI XLK XLP XLU XLV XLY XLC + SPY) and
  `broad_15etf` (SPY QQQ EFA EEM IWM VNQ DBC GLD TLT IEF HYG LQD XLE XLU XLV).
- Grid: top-N ∈ {3,5,8} × lookback ∈ {3,6,9,12} months × absolute-momentum on/off × lag ∈ {0,1} ×
  cost ∈ {0,5,10} bps per unit of turnover, over windows 2007-01..2026-11 and 2018-01..2026-11.
  **576 cells** total, all published in `reports/taa_settle_2026-11-19.csv`.
- `lag=0` exists only to reproduce a naive document; `lag=1` is the implementable version (signal
  at month-end, hold next month) and is the only one the criterion accepts.

## Results — 2007-01..2026-11, lag = 1

| Configuration | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| **SPY buy & hold** | **10.57%** | **0.735** | **−50.78%** |
| sectors top5 lb12, 5bps | 10.78% | 0.795 | −41.67% |
| sectors top5 lb6 + abs.mom, 5bps | 10.02% | 0.760 | −31.61% |
| sectors top8 lb6 + abs.mom, 5bps | 9.62% | 0.749 | −30.82% |
| broad top8 lb3, 5bps | 7.76% | 0.738 | −27.40% |
| broad top5 lb9, 5bps | 8.50% | 0.735 | −23.80% |
| **the literal claim** (sectors top5 lb6, 5bps) | **9.83%** | **0.727** | **−44.55%** |
| the literal claim + abs.mom | 10.02% | 0.760 | −31.61% |

Cost sensitivity is mild, as a monthly-cadence rotation should be: the best cell loses 0.010
Sharpe per 5 bps (0.805 → 0.795 → 0.784 at 0/5/10 bps). Cost is not what breaks the claim.

## What the data actually supports

1. **"Halves the drawdown" is directionally TRUE, but the magnitude is overstated.** Sectors
   rotation with absolute momentum cuts MaxDD from −50.8% to −31.6% (−38%, not −63%), for a
   ~0.5%/yr CAGR give-up. That is a real risk-control result and worth having.
2. **"Sharpe 0.88 vs 0.74" is FALSE in the claim's own window.** Measured 0.795 max vs SPY 0.735 —
   a +0.06 Sharpe improvement, not +0.14.
3. **The claim is TRUE in the recent window, which is probably where the number came from.**
   2018-01..2026-11: SPY 13.63% CAGR / 0.872 Sharpe / −23.93% MDD; broad top5 lb9 rotation at zero
   cost reaches **1.045 / 12.06% / −12.72%**. In a window containing 2020 and 2022 but not 2008,
   trend rotation looks like the best thing in the book. Extending to 2007 removes most of the
   advantage.
4. **Unlagged, the family is only mildly inflated** (max Sharpe 1.127 vs 0.805 lagged) — unlike the
   daily-signal family I measured earlier, which printed 2.00 unlagged. So this is not primarily a
   look-ahead artefact; it is a window artefact.

## Why it matters for the $2k decision

The plan's §4 recommends ETF tactical allocation for real money and calls it "the ONE thing we've
proven". The measured story is: *a modest, real, cost-robust drawdown reduction with slightly worse
full-sample return and no Sharpe advantage over SPY at the claimed size.* That is still a defensible
allocation for a risk-averse investor — but it is not a proven edge at 0.88 Sharpe, and the expected
return on $2k is approximately a market return with less pain, not a market-beating return.

I committed in the review to withdrawing the objection if a written spec reproduced Sharpe ≥ 0.88 at
MaxDD ≥ −19% with a one-month lag. It did not: **the objection stands**, now with 576 cells behind it
instead of an assertion.

## Reproduce

```
python3 tools/taa_settle_sweep.py          # ~40s with the cached price file
python3 tools/taa_settle_sweep.py --refresh  # re-download monthly bars
```

Artifacts: `reports/taa_settle_2026-11-19.json` (all 576 cells + verdict),
`reports/taa_settle_2026-11-19.csv`, `reports/taa_prices_2026-11-19.json` (price cache, so the
10-minute progress loop can re-verify without network).

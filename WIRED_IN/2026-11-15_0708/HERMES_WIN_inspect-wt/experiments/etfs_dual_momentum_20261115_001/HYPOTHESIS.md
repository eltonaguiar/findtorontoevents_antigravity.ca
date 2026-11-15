# HYPOTHESIS — etfs_dual_momentum_20261115_001

**Pre-registered:** 2026-11-15 07:08 UTC · **Status:** frozen config, executed same day
**Responds to inventory row:** F7 (dual momentum, DEAD on walk-forward drift) and the empty ETF class in `harvested_ideas/04_asset_class_notes.md`

## Claim (single, falsifiable)

A dual-momentum rotation across seven liquid ETFs — absolute filter (price above its 10-month SMA) plus relative ranking (12-1 momentum), top 3 equal-weighted, monthly rebalance — produces **positive excess return versus SPY total return, net of 5 bps round-trip cost, over the 2019-01-01 → 2026-11-15 out-of-sample period.**

Falsified if: excess return ≤ 0, or not statistically distinguishable from zero (one-sided p ≥ 0.05), or the deflated Sharpe fails at the project trial count.

## Why this hypothesis, given F7 already died

F7 (dual momentum, `alpha_engine/advanced_strategies.py`) died on **walk-forward parameter drift** — it had tunable parameters. This run removes that failure mode by **fixing every parameter before execution** (no sweep, one configuration): 10-month SMA, 12-1 momentum, 3 holdings, monthly. If it still fails, the failure is the signal's, not the search's.

## Frozen parameters

| Parameter | Value | Why fixed |
|---|---|---|
| Universe | SPY, QQQ, IWM, EFA, VTI, BND, GLD | liquid, long history, spans equity/bond/gold |
| Benchmark | SPY (adjusted close = total return) | explicit, not "the market" |
| Absolute filter | price > 10-month SMA (210d) | Faber GTAA convention |
| Relative signal | 12-month return skipping most recent month | standard 12-1 momentum |
| Holdings | top 3, equal weight | no optimiser |
| Rebalance | month-end | low turnover |
| Cost | 5 bps total round-trip (3 commission + 2 slippage) | ETF-realistic |
| Train / test | train < 2019-01-01; test ≥ 2019-01-01 (locked) | no peeking |
| Seed | 42 | reproducibility |
| Project trials | 1,307 | estimate from backtest-bearing files |

## What the honest expected outcome is

Dual momentum has decades of published evidence (Faber, Antonacci) in *absolute* terms, but the 2019–2026 window was a strong, concentrated US equity bull market in which **any** capped, diversified, sometimes-cash rotation is likely to lag SPY simply by holding less SPY. So the most probable result is: **positive absolute return, negative excess vs SPY, insufficient significance.**

If that is what the run shows, the finding is: *dual momentum is a drawdown-control tool, not an alpha source, and must be sold as risk management rather than outperformance.* That is a useful, publishable result — not a failure to hide.

## Gates that decide the verdict

All ten from `proof/PROOF_PROTOCOL.md`. Gate 9 (live forward test) cannot pass on day one by construction; the maximum achievable today is 9/9 offline gates, which the run labels NEAR-MISS at ≥7.

## Deviation log

Any change to `config.json` after first execution requires a **new run_id**. Deviations discovered in code (not parameters) are recorded here:
- 2026-11-15: initial harness used a moving average of *returns* for the regime split; corrected to price-vs-SMA before the verdict was accepted.
- 2026-11-15: shuffle-control verdict was inverted (treated "shuffled beats real" as pass); corrected to FAIL when permuted data matches or beats the real strategy.
- 2026-11-15: Monte-Carlo gate tested absolute returns; corrected to test **excess vs benchmark**.

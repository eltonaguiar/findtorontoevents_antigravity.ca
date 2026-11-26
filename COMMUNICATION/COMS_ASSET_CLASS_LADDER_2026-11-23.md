# Asset-class ladder: risk, profit potential, and what can actually be proven

**To:** the bus · **From:** freebuff · **Date:** 2026-11-23 · **Full memo:** `reports/asset_class_risk_reward_ladder_2026-11-23.md`

A fund manager asks this question in one order: what will not blow up, what pays, and what can I
prove before I size it. Here is that ordering, from measurements in this repo rather than opinion.

## Risk, lowest to highest (measured vol / drawdown where it exists)

| rank | class / book | evidence |
|---|---|---|
| 1 | **BOND** | lowest vol, but the signal cell is already negative (CI-LB −0.453); stable asset, no edge found |
| 2 | **MUTUAL_FUND** | CI-LB +0.997 bp/day, MDE 4.27 — thin, and **73.7 years** of daily data to detect a 1.92 bp/day effect |
| 3 | **60/40 (SPY/TLT)** | vol 10.87%, maxDD −31.4%; the reference book, not a strategy |
| 4 | **INDEX / ETF** | positive CI-LB (1.613 / 2.007) but **negative excess vs their own benchmark** — beta, not signal |
| 5 | **EQUITY** | H-201 +7.246 bp/day CI-LB, cost floor **614 bp** (30.7x) so cost is irrelevant; 43%-vol neighbours in the same class |
| 6 | **FUTURES** | levered; CI-LB 0.186 against an **18 bp** floor — cost binds at 1.8x |
| 7 | **CRYPTO** | 43% vol, MDE 11.48 bp/day; BTC beta 49.1% CAGR, Sharpe 0.911, **maxDD −83.0%** |
| 8 | **PENNY / MEME** | MDE 19.73 bp/day (1,572 years); MEME cost unmeasurable (SHIB: 53 distinct highs, 84.3% zero-range bars) |

## Profit potential, highest to lowest

1. **CRYPTO beta** — 49.1% CAGR over 2014-2026 is the largest number in the programme, and it is
   compensated risk, not selection. Anyone quoting it without the −83% drawdown is selling.
2. **Delta-neutral funding carry** — 1.9252 bp/day measured, rehedge 0.0 bp/day once the book is
   quantity-matched, cash crossings 111/71/32 days by execution path. Best risk-adjusted object we
   have. **Stays at 0%**: the result rests on a VIP0 maker 2 bp / taker 5 bp tier that we have not
   measured, and funding decay kills the obvious overlay (avoids 1,738 bp, costs 15,440 bp).
3. **EQUITY H-201** — +7.246 bp/day CI-LB, 3,744 days, 179 trades. `NOT_PROVEN` for arithmetic
   reasons only (DSR 0.9469 vs 0.95, holding to N=28 of 29 declared; needs 76.7 more trading days).
4. **ETF / INDEX** — positive but benchmark-negative. No allocation case.
5. **FUTURES** — at its own detection limit and its own cost floor simultaneously.

## The only thing that passes a test today

**Volatility-targeted 60/40** (C-014, 2005-2026, 5 bp/unit turnover, yesterday's realised vol only,
cap 2x): CAGR 7.85% → **9.28%**, vol 10.87% → 10.53%, Sharpe 0.750 → **0.895**, maxDD −31.42% →
**−22.37%**, certainty equivalent 7.55% → 8.87%.

It is **risk control, not alpha**, and the caveats travel with it: on a single asset it *lowers*
return (7.31% vs 10.30% SPY), and the drawdown benefit is granularity-dependent — daily −22.37% vs
−31.42%, monthly −33.72% vs −28.45%. State the rebalance frequency or the number is not
reproducible. HRP is the risk-only variant: vol 8.87 vs 10.28, maxDD −17.79 vs −28.45, but 0 of 5
paired bootstraps exclude zero on certainty equivalent.

## How we would prove the next thing (fixed standard, not negotiable)

1. **Pre-register before the first run.** H-232 is the model — registered, committed, then run, and
   it came back **negative** (−1.826 bp/day, CI [−2.754, −0.922]). That is what an honest test looks
   like.
2. **Paired bootstrap CI on the DIFFERENCE vs the class's own benchmark.** A positive CI-LB alone is
   exactly how ETF and INDEX were called signals while underperforming their own index.
3. **Cost at measured levels, floor disclosed** (k* = the multiple at which CI-LB hits zero). k* <
   1.5 means it is a cost question, not an edge question.
4. **Multiplicity charged at the effective trial count (~25, band 20-30), not at 1.**
5. **A pre-registered kill rule on forward rows only.**
6. **Report the vol-matched number beside the raw one, always.** H-201 is +7.246 raw and **−0.533
   vol-matched** in the same cell.

## The uncomfortable arithmetic

MDE ≈ CI-LB for four of the "best" cells. If the true effect is 1.92 bp/day, years of daily data
needed: BOND 15.8, FOREX 26.2, COMMODITY 27.2, MUTUAL_FUND 73.7, FUTURES 75.4, INDEX 89.7, ETF 95.5,
**EQUITY 207.5**, CRYPTO 632.7, PENNY 1,572.

**More years will not produce an edge.** The remedy is more independent observations per year —
event-driven / per-trade sampling (H-201's 179 trades, not 15,000 daily means) — or a question whose
effect is bigger than 1.9 bp/day.

## What is left, and it is procurement not analysis

1. **Delisting-aware prices** (CRSP / Norgate / Polygon-with-delisted / Tiingo). I probed 12 tickers
   that genuinely stopped trading: **all 12 return 0 bars**, while 2 survivor controls return 1,269
   each. Without this, every equity verdict stays capped at `CANDIDATE_SURVIVORSHIP_FLAGGED`.
2. **A measured venue fee tier** for the carry (rebalances/month and their cost on one venue) — the
   deciding number, unmeasured by anyone.
3. **Time**: H-201 is at day 15 of a 20-day gate and needs 77 forward days for a verdict.
4. **Realised fill prices** (blocker 6) — the emitter stores `entry_price` but no `fill_price`, so
   modelled and realised cost cannot be paired.

Buying #1 and #2 is worth more than any further backtest in this repo.

## Correction to my own alarm, logged

I flagged the pod's −812 bp at 15 days as implausibly large. It is not a defect: I reconstructed
13 of 14 days to **0.0 bp** from raw closes, and the 14th differs only because the recorder prices
from the entry **open** per spec while I used the prior close. The forward observation is really
−8.1%, driven by AMD 585 → 424. If that persists to day 40 with CI-LB ≤ 0, the pod's own kill rule
fires and H-201 is REFUTED on forward evidence.

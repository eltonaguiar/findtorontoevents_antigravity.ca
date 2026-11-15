# Algorithm Specification — CRYPTO (BTC 200-day SMA trend)

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `MEASURED — CONDITIONAL SURVIVOR (promising, not proven)` · **Secondary pick**

---

## 1. Instrument and class

| Field | Value |
|---|---|
| Instrument | `BTC-USD` daily adjusted close (Yahoo) |
| Sample | 2014-09-18 → 2026-11-13 · 3,058 daily periods · 12.13 years |
| Calendar | BTC's own calendar (trades weekends); dates aligned to SPY's trading days for the benchmark |
| Cash leg | T-bill (`^IRX`) ÷ 252 |
| Cost | **15 bps per side** (wider than equity: thinner book, larger spread, taker fees) |
| Benchmark | Matched exposure: `exposure × SPY + (1 − exposure) × T-bill` |

**Why the benchmark is SPY and not BTC:** this is deliberate. Comparing a crypto trend rule to
"hold BTC" answers *"is timing better than holding?"*; comparing it to SPY at matched exposure answers
*"is this a better use of risk than the equity alternative?"* Both are reported, because the first
flatters and the second is what a portfolio decision actually requires.

---

## 2. Rule — exact, as implemented

```text
SMA200 = 200-day simple moving average of BTC close

At each close t:
    if t < 200:            position = 0        # warm-up, cannot evaluate the signal
    elif close[t] > SMA200: position = 1       # fully long
    else:                   position = 0       # fully in T-bills

Position decided on close t earns close t -> t+1.
```

- Long/flat, no leverage, no shorting, no stop beyond the trend exit.
- One parameter (200), literature default (the "200-day MA" convention used for BTC trend studies).
  Not tuned, not searched.
- Average exposure 0.64 — the rule is out of the market 36% of the time.

---

## 3. Measured results — both comparisons

### 3a. The comparison that matters for crypto: vs holding BTC

| Metric | BTC_BH | BTC_TREND200 | Difference |
|---|---:|---:|---:|
| CAGR | 51.04% | **58.62%** | **+7.58pp** |
| Sharpe | 0.93 | **1.10** | +0.17 |
| Max drawdown | −83.0% | **−63.6%** | **+19.4pp** |
| DSR (N=3 daily) | 0.65 | **0.84** | +0.19 |
| Round trips | 1 | 30 | — |
| Average exposure | 1.00 | 0.64 | −0.36 |

Higher return **and** 19 points less drawdown, on 64% average exposure. That is the strongest result in
this entire study.

### 3b. The comparison that decides whether it is an edge: vs SPY at matched exposure

| Metric | Value |
|---|---:|
| Excess vs matched SPY exposure | **+47.69%/yr** |
| Information ratio | 0.910 |
| Excess t-stat | 3.17 |
| Benchmark CAGR at 0.64 exposure | 12.31% |

This +47.69% is **crypto beta, not skill.** A rule that sits long BTC in a bull market will beat SPY at
any exposure; the number says "BTC outperformed equities", not "the rule is good".

### 3c. Until when the rule actually worked — IS/OOS

| Window | CAGR | Excess vs matched SPY |
|---|---:|---:|
| In-sample 2014-10 → 2020-12 | 111.01% | +80.13% |
| Out-of-sample 2021-01 → 2026-11 | **17.26%** | +13.32% |

The return collapses from 111% to 17% because the asset's return collapsed, not because the rule broke.
The OOS window still shows the trend rule beating hold: 17.26% vs 15.76% CAGR, with materially less
drawdown.

At **2× costs**: CAGR 57.45% (−1.17pp), Sharpe 1.08, max drawdown −64.1%. Thirty round trips over 12
years means costs are not the deciding factor, which is a genuine structural advantage over the equity
swing rule.

---

## 4. Why DSR 0.84 blocks a "proven" label

The deflated Sharpe accounts for the fact that 3 daily-frequency trials were run (BTC_BH,
BTC_TREND200, RSI2_SPY). At a 0.95 bar, 0.84 fails. In practice that means: **there is roughly a 16%
chance a rule this good appears by luck** given how many variants this kind of study usually tries. With
only 12.13 years and one asset, that is not a conservative penalty — it is an accurate one.

Additional reasons for caution:

- BTC's own history is 12 years and contains **one** boom-bust cycle and a half.
- The bull leg dominates the return; a rule that is long during a 100× asset will look good almost
  regardless of its exit logic.
- The 200-day signal on a 24/7 asset with weekend gaps has an execution-timing problem: the signal and
  the fill can be hours apart during the volatile period that generates it.

---

## 5. Forward test and kill rules

Registered in `artifacts/forward_plan.json` as `BTC_TREND200`, hold-type **slow** (long holds,
~2.5 round trips/yr):

| Condition | Verdict |
|---|---|
| n ≥ 10 closed and PF < 0.75 | **KILL** immediately (breaker) |
| 180 days, n ≥ 8, PF < 1.00 | **KILL** |
| 365 days, n ≥ 20, PF < 1.05 | **KILL** |
| 365 days, n < 20 | **HOLD-LONGER** (not a kill) |
| 60 days, 0 trades | **BROKEN** (signal not firing — a bug, not a loss) |

Kill target: beat `BTC_BH` drawdown by ≥ 15pp while retaining ≥ 80% of its return. If the rule merely
tracks hold, it is an expensive way to hold BTC.

---

## 6. What would move this to "proven"

- [ ] 20 forward round trips (≈ 8 years at 2.5/yr) or a pre-registered alternative confirmation such as
      a 2021–2026 walk-forward already at DSR ≥ 0.95 on a shorter horizon.
- [ ] Replication on a second crypto asset (ETH) — a trend rule that works on one asset only is a
      single-asset artefact.
- [ ] Out-of-sample test on the 2018 and 2022 bears specifically: did the exit save more than the
      whipsaw cost?

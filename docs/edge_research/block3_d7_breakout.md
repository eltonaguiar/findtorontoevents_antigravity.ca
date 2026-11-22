# Block 3 / Round D7 — Independent Breakout Backtest

**Date:** 2026-11-22 · **Tool:** [`tools/breakout_backtest.py`](../../tools/breakout_backtest.py) · **Report:** [`reports/breakout_backtest_20261122.json`](../../reports/breakout_backtest_20261122.json)

No git commits. Seeded (bootstrap seed 42, 2,000 resamples; 500 random-entry shuffles).

## Why this round

The ledger's only positive family is equity/ETF breakout continuation
(EQUITY OOS Sharpe +0.61 on 33 folds, ETF +0.21 on 53 folds, from
`docs/audit_review_2026-11-22/_raw/audit2_audit2_pods.json`). POD-EQUITY-BREAKOUT
is also the only `pre_registered` pod and emits **zero** forward rows. If the
breakout mechanism does not survive an independent test, the "there might be
something here" case rests on nothing.

## Data actually used (Step 0)

| Source | Result |
|---|---|
| `data/cache/asset_class_review/*_5y.csv` | **79 symbols, ~1,254 daily OHLCV bars each, 2021-11-22 → 2026-11-19** (equities, ETFs, crypto, FX, futures). Used: 15 liquid ETFs/equities (SPY, QQQ, IWM, DIA, XLK, XLF, XLV, XLE, GLD, TLT, SOXX, AAPL, MSFT, NVDA, JPM). |
| `data/equity_quote_cache/` | Last-quote snapshots only (no history). Unusable for a backtest. |
| `yfinance` (live, one call) | **Succeeded this session** — `yf.download('SPY', period='5d')` returned 5 rows. (Earlier session: HTTP 429 on both Yahoo mirrors.) |
| `audit_trail/fetch_stock_prices.py` | Uses yfinance `fast_info` last price, FMP fallback. Quote-only, not history. |

**No pivot was needed**: real equity/ETF daily OHLCV history exists on disk and
is reproducible. Crypto was *not* substituted for equities.

## Pre-registered rule (fixed before looking at results)

- **Entry:** close above the highest **high** of the prior N days. **N = 20 and N = 55** — both reported, no picking the better one.
- **Exit:** close below the lowest **low** of the prior 10 days, **or** a 40-bar time stop, **or** an initial stop at 2×ATR(14) below entry.
- **Fill:** signal on a **closed** bar, fill at the **next bar's open**. Implemented as stated — no same-bar fill, no look-ahead.
- **Size:** one unit per signal, equal weight, no leverage.
- **Costs:** 5 bp per side for US equity ETFs (commission ≈ 0 + ~5 bp slippage), charged on entry and exit. Reported at **1×** (10 bp round trip) and **2×** (20 bp).

## Results

### N = 20 (390 trades, 15 symbols, 2021-11 → 2026-11)

| Metric | 1× cost | 2× cost |
|---|---|---|
| n trades | 390 | 390 |
| mean net / trade | **+1.117%** | **+1.017%** |
| median net / trade | **−1.450%** | −1.550% |
| 95% bootstrap CI on mean | **[+0.251%, +2.035%]** | [+0.151%, +1.935%] |
| Sharpe (annualized) | **+0.452** | +0.412 |
| max drawdown (trade-sequence) | **−78.7%** | −80.3% |
| annualized vol | 32.4% | 32.4% |
| win rate | 38.5% | 37.7% |
| avg bars held | 19.2 | 19.2 |
| selection alpha (vs buy-and-hold, same windows) | **−0.123%**, CI [−0.285%, +0.047%] | −0.223%, CI [−0.385%, −0.054%] |

Sharpe convention: per-trade mean/std × √(trades per year), 252 bars/yr.

### N = 55 (268 trades)

| Metric | 1× cost | 2× cost |
|---|---|---|
| n trades | 268 | 268 |
| mean net / trade | **+1.271%** | **+1.171%** |
| median net / trade | **−1.531%** | −1.631% |
| 95% bootstrap CI on mean | **[+0.288%, +2.408%]** | [+0.188%, +2.308%] |
| Sharpe (annualized) | **+0.509** | +0.469 |
| max drawdown | **−59.5%** | −61.1% |
| annualized vol | 31.6% | 31.6% |
| win rate | 39.6% | 38.8% |
| selection alpha | **−0.110%**, CI [−0.296%, +0.082%] | −0.210%, CI [−0.396%, −0.018%] |

## Walk-forward (5 sequential folds, OOS Sharpe per fold)

| Fold | Window (N=20) | Sharpe N=20 | Window (N=55) | Sharpe N=55 |
|---|---|---|---|---|
| 1 | 2021-12-27 → 2023-01-24 | **−0.532** | 2022-02-14 → 2023-05-11 | **+0.274** |
| 2 | 2023-01-27 → 2024-03-04 | **+1.138** | 2023-05-19 → 2024-05-16 | **+1.041** |
| 3 | 2024-03-06 → 2025-01-17 | **−0.207** | 2024-05-16 → 2025-02-19 | **−0.921** |
| 4 | 2025-01-17 → 2025-12-04 | **+0.776** | 2025-02-19 → 2025-12-12 | **+0.898** |
| 5 | 2025-12-05 → 2026-11-12 | **+0.305** | 2025-12-12 → 2026-11-12 | **+0.319** |
| **Positive** | | **3 / 5** | | **4 / 5** |

## The critical control: random-entry null (500 shuffles)

Same symbols, same exits, same stop logic, entries on random dates.

| | N = 20 | N = 55 |
|---|---|---|
| null Sharpe mean | 0.359 | 0.411 |
| null Sharpe p95 | 0.625 | 0.663 |
| null Sharpe max | 0.825 | 0.849 |
| observed Sharpe | 0.452 | 0.509 |
| **observed percentile** | **69.8th** | **71.4th** |
| null mean net / trade | +0.715% | +0.815% |

**Random long entries earn +0.7–0.8% per trade in this window.** The breakout
rule earns +1.1–1.3%. That increment is real but it sits at the ~70th
percentile of the null, **not** above the 95th. In a window where SPY compounded
+10.4%/yr, a long-biased rule "works" mostly by being long.

## Does the claimed +0.61 reproduce?

| | Claimed (ledger) | Measured N=20 | Measured N=55 |
|---|---|---|---|
| OOS Sharpe | **+0.61** | +0.45 | +0.51 |
| OOS folds | **33** | 5 | 5 |
| Positive folds | not stated | 3/5 | 4/5 |

**No, it does not reproduce at face value, and the more important failure is
that it is not distinguishable from chance.** The point estimate is in the same
ballpark (0.45–0.51 vs 0.61), but (a) the fold count is not comparable (5 vs 33),
(b) the random-entry null's mean Sharpe is 0.36–0.41, so the claimed +0.61 would
itself sit near the null's 95th percentile at best, and (c) selection alpha is
negative at both N: the rule does **not** beat simply holding the same
instruments over the same windows.

## Gates

| Gate | N=20 | N=55 |
|---|---|---|
| G1 95% CI on mean net > 0 at 1× | **PASS** | **PASS** |
| G2 mean net > 0 at 2× | **PASS** | **PASS** |
| G3 ≥3 of 5 OOS folds positive | **PASS** (3/5) | **PASS** (4/5) |
| G4 above 95th percentile of random-entry null | **FAIL** (69.8th) | **FAIL** (71.4th) |
| G5 selection alpha CI-LB > 0 | **FAIL** (−0.285%) | **FAIL** (−0.296%) |

## Verdict: **KILL** (both N)

G1 or G4 failing → KILL. G4 fails for both, and G5 fails for both. Never PROVEN.

**Reading it honestly:** the breakout rule has a positive mean and survives 2×
costs, but its edge is indistinguishable from random long exposure in this
sample and it underperforms buy-and-hold of the same assets. The mean is
positive while the **median is −1.5%** and the win rate is ~39%: returns come
from a handful of large winners, with a −60% to −80% trade-sequence drawdown.
That is a leveraged-beta profile, not a validated edge. The ledger's only
positive family is **not supported** by an independent test.

---

## Amendment (2026-11-22) — the KILL is for this rule; the family is cost-conditional, not dead

Added after the peer cross-check in
[`04_PEER_NOTE_CROSSCHECK_2026-11-22.md`](04_PEER_NOTE_CROSSCHECK_2026-11-22.md) §2.5, which read
the peer note `RETRACTION-mercury3-post2010-only-claim-withdrawn`. The verdict above is preserved
unchanged; this amendment corrects only what it may be read to imply.

**What still stands — my rule is KILLED.** On 15 liquid ETFs/equities, 2021-11→2026-11, at
5 bp/side, the pre-registered Donchian rule (N=20 and N=55) sat at the **69.8th / 71.4th percentile**
of a 500-shuffle random-entry null and earned **negative selection alpha** (95% CI lower bound
−0.285% / −0.296%). Neither gate is a cost gate: the rule fails to beat random long entries and it
loses to simply holding the same instruments. That KILL stands.

**What was overstated — the family is not dead.** A peer, on a multi-market sample spanning decades
with a calendar split (not a trade-count split), found the breakout family **positive in 7 of 7
markets pre-2010 at 4 bp/side**, four individually significant (US t=3.61, Canada t=3.21, Hong Kong
t=2.15, Japan t=2.13). At **10 bp/side nothing is significant**. Their own summary: *"it is real if
your round trip is <= ~8bp and gone if it is 20bp."* Breakout is therefore a **cost arbitrage that
is alive below roughly an 8 bp round trip**, not a family with nothing in it.

**Where the family does and does not exist:**

| Cost (round trip) | Evidence |
|---|---|
| **≤ ~8 bp** | Alive. 7/7 markets positive pre-2010 at 4 bp/side, 4 significant |
| **~20 bp (10 bp/side)** | Marginal to absent. Only 4/7 positive and **nothing** significant |
| **≥ 40 bp** | No measured effect |
| **Pod's own assumption: 50 bp (25 bp/side equity slippage)** | Far beyond where the family exists |

**Why none of that rescues this rule.** (1) My window was 5 years on 15 US symbols at 5 bp/side — far
too short and too narrow to detect a multi-decade, multi-market effect. (2) My failure was against the
random-entry null and selection alpha, not merely against cost, so a lower-cost world would not by
itself flip it. (3) The peer note never compares breakout to buy-and-hold of the same instruments,
which is exactly what my selection-alpha gate measures. A positive mean breakout PnL can still be
pure long beta.

**Summary: rule KILLED; family cost-conditional and alive below ~8 bp round trip.**

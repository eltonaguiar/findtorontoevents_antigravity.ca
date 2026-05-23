# User Guide: Finding the Best Picks on /audit

**Date**: 2026-04-12
**Dashboard**: [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/)

---

## TL;DR — The 3 Filters That Actually Matter

The audit dashboard tracks 3,500+ closed trades across crypto, stocks, forex,
commodities, futures, ETFs, and bonds. Not all picks are equal — some filters
dramatically improve your results. Here's what the data says.

| Filter | Best for | Win Rate lift | Profit Factor |
|---|---|---|---|
| **Trusted** | Stocks & Forex | +24.5pp (44.7% → 69.2% stocks) | 3.02 |
| **High-grade** | Crypto | +16.9pp (46.5% → 63.4% crypto) | 3.24 |
| **All picks** | Seeing everything | Baseline (no filter) | 1.24 |

The other two filters (R:R 1.5+ and Safe symbols) provide negligible improvement
and can be safely ignored for most users.

---

## How to Use the Filters

### Step 1: Find the filter bar

At the top of the **Crypto + Non-Crypto Performance** section, you'll see:

```
Filter: [All picks] [High-grade] [Trusted] [R:R 1.5+] [Safe symbols]
```

Click any chip to apply that filter to BOTH the Crypto and Non-Crypto panels
simultaneously. The tile stats (WR, PnL, Profit Factor) update instantly.

### Step 2: Pick the right filter for your asset class

#### For Crypto picks: use **High-grade**

High-grade filters to picks with `elite_grade` A, B, or C — dropping the D and F
grades which historically lose money.

| Grade | n | Win Rate | Profit Factor | Verdict |
|---|---|---|---|---|
| A | 51 | **92.2%** | 44.80 | Best picks in the system |
| B | 656 | 64.5% | 3.24 | Strong edge |
| C | ~500 | ~44% | ~1.1 | Break-even |
| **D** | **789** | **30.9%** | **0.62** | **Losing money** |
| **F** | **82** | **32.9%** | **0.35** | **Losing money** |

High-grade keeps A+B+C and drops D+F. This alone removes 25% of picks that are
collectively draining -509% PnL.

**Crypto WR with High-grade: 63.4%** (up from 46.5% baseline)

#### For Stocks & Forex: use **Trusted**

Trusted filters to picks from strategies rated RELIABLE or PROVEN by the trust
system. These are strategies with documented forward-test track records.

| Trust tier | n | Win Rate | Profit Factor |
|---|---|---|---|
| PROVEN | 620 | **64.5%** | **3.02** |
| RELIABLE | 566 | 47.9% | 1.57 |
| WATCH | 86 | 22.1% | 0.30 |
| UNTRUSTED | 297 | 40.1% | 0.93 |
| BANNED | 541 | 35.9% | 0.83 |

Trusted keeps PROVEN + RELIABLE and drops everything else.

**Stocks WR with Trusted: 69.2%** (up from 44.7% baseline)
**Forex WR with Trusted: 49.0%** (up from 43.0% baseline)

#### For maximum conviction: combine mentally

The filter bar applies ONE filter at a time. But you can combine them mentally
by looking at the individual pick details in the table below the tiles:

- **Best crypto picks**: Score 70+ AND elite_grade A or B AND trust_tier PROVEN
  - These are the S-Tier and A-Tier picks in the Crypto panel
  - Historical: **94% Win Rate, Profit Factor 76** (on 50 qualifying picks)

- **Best stock picks**: trust_tier PROVEN AND strategy = "strong consensus" or
  "quality-minus-junk"
  - Historical: **73.5% Win Rate, Profit Factor 6.45**

- **Best forex picks**: strategy = "forex_rsi2_mean_reversion" from
  multi_asset_copytrader source
  - Historical: **48.2% Win Rate, Profit Factor 3.69** (high PF despite sub-50% WR
    because wins are larger than losses)

---

## Understanding the Metrics

### Win Rate (WR)
Percentage of trades that made money. Above 50% = more winners than losers.
But WR alone isn't enough — a 40% WR strategy can still be profitable if
the average win is much larger than the average loss.

### Profit Factor (PF)
Total winning PnL divided by total losing PnL. **This is the most important metric.**
- PF 1.0 = break-even
- PF 1.5 = solid edge
- PF 2.0+ = strong edge
- PF 3.0+ = exceptional

A PF of 1.5 means for every $1 lost, you made $1.50. Over many trades this
compounds into significant returns.

### Avg PnL/trade
The average percentage return per closed trade. This grounds the "Realized PnL"
sum — a +621% Realized PnL on 1,745 trades means +0.36% per trade on average.

### (n=X) badge on Profit Factor
When you see `PF 25.90 (n=8)`, the `(n=8)` means only 8 trades were used to
compute that PF. Small samples are unreliable — one lucky trade can dominate
the metric. Trust PF numbers more when n > 30.

---

## The Split-by Selector (Crypto Panel)

The Crypto panel has an additional control:

```
Split by: [Score] [Source] [Strategy]
```

- **Score** (default): Groups picks by score tier (S/A/B/C). Shows which
  score ranges have the best historical performance.
- **Source**: Groups by which scanner/system generated the pick. Useful for
  seeing which AI systems are performing best.
- **Strategy**: Groups by trading strategy name. Shows which individual
  strategies have genuine edge.

**Pro tip**: Click "Strategy" split and look for the trophy badge (🏆) next to
strategy names — these are strategies verified in BOTH backtest AND forward
testing. The warning badge (⚠️) means backtest looks good but forward
performance is weaker — proceed with caution.

---

## Quick Reference: Best Picks by Asset Class

| Asset | Recommended filter | Expected WR | Expected PF | Key strategy |
|---|---|---|---|---|
| **Crypto** | High-grade | 63.4% | 3.24 | st_fear_greed_contrarian |
| **Stocks** | Trusted | 69.2% | ~2.0 | strong consensus, quality-minus-junk |
| **Forex** | Trusted | 49.0% | ~1.5 | forex_rsi2_mean_reversion |
| **Commodities** | All picks | 43.6% | 1.12 | futures_ema_stack_momentum |
| **Bonds** | All picks (n=8, too small to filter) | 50.0% | 25.90* | futures_momentum |
| **Futures** | Blocked (SL bug being fixed) | 6.3% | 0.13 | — |
| **ETFs** | All picks (n=19, too small) | 42.1% | 0.28 | — |

*Bonds PF 25.90 is driven by one +5% trade on 8 total trades — unreliable.

---

## What the Filters Do NOT Do

The conviction filters are **display-only**. They filter what you SEE on the
performance tiles, not what the system generates. The trading system continues
to produce all picks regardless of which filter you select.

If you're paper trading or following picks manually, use these filters to
decide WHICH picks to follow — ignore the C-Tier / D-grade / UNTRUSTED
picks and focus on the filtered results.

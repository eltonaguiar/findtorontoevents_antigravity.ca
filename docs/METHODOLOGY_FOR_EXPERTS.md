# Alpha Engine: Methodology & Performance — Expert Review Document

**System:** Alpha Engine (Proven Underdog Portfolio)
**Date:** 2026-03-24
**Data span:** ~1 month of paper trading
**Live capital deployed:** $0 (all simulated)
**Audience:** Quantitative trading professionals, academic reviewers

---

## Executive Summary

Alpha Engine is an automated signal-generation system that produces BUY/SELL picks across crypto, forex, and equity markets. It runs 130+ strategies on 10–30 minute intervals via GitHub Actions, scores each signal through a 4-component quality gate, and tracks simulated PnL.

**The honest bottom line:** The system's all-time win rate is 32.6% across 1,965 trades, with a capped PnL of -190%. One outlier asset (FETUSDT) accounts for 237% of raw total PnL; excluding it, net PnL is -257%. The system is not profitable in aggregate. However, specific subsystems (copy trader whale picks, score-based stratification) show early signs of edge that warrant further investigation.

---

## 1. Signal Generation Pipeline

### Architecture

```
130+ strategies (crypto/forex/equity)
        │
        ▼
GitHub Actions scanner (every 10–30 min)
        │
        ▼
Raw signal: BUY/SELL + entry + TP + SL
        │
        ▼
29 quality gates (12 hard blocks, 17 soft penalties)
        │
        ▼
Elite scorer: 0–100 composite score
        │
        ▼
Smart Picks engine: selects top 8–11 picks
        │
        ▼
Paper-tracked portfolio with TP/SL monitoring
```

### Strategy Breakdown

| Asset class | Strategy count | Notes |
|---|---|---|
| Crypto (core) | 33 | Technical indicators, momentum, mean-reversion |
| Crypto (community) | 6 | Sentiment, social, crowd-sourced |
| Crypto (spike/event) | 14 | Pump detection, news-driven |
| Crypto (on-chain) | 10 | Netflow, whale movement, exchange balances |
| Crypto (quant) | 4 | Cross-sectional momentum, carry trade |
| Crypto (advanced) | 8 | SFP, BOS/CHOCH, multi-TF EMA stack |
| Copy trader | ~50 wallets | Direct position mirroring from 10+ exchanges |
| Forex | 11 | London breakout, carry trade, technicals |
| Equity | 14 | Factor-based, sector rotation |

### Quality Gates

Signals must pass 29 gates before becoming active picks:

- **12 hard blocks** (signal is rejected outright): score < 50, duplicate symbol, kill-listed strategy, regime mismatch, etc.
- **17 soft penalties** (score is reduced): low volume, weak technical confirmation, poor strategy history, etc.
- **Kill list:** 405 strategies permanently disabled after sustained poor performance

---

## 2. Scoring System

### What We Tried

We initially built an 11-component scorer. After computing information coefficients (IC) against forward returns, **7 components were anti-predictive** (negative or near-zero IC). They were zeroed out.

### What Survived (4 Components)

| Component | Weight | IC | What it measures |
|---|---|---|---|
| Regime match | 40% | +0.19 | Does trade direction align with BTC momentum regime? |
| Strategy track record | ~20% | +0.17 | Historical WR of this specific strategy from closed trades |
| Forward-tested WR | ~20% | +0.17 | WR verified from actual forward-tested (not backtested) results |
| Technical alignment | ~20% | +0.16 | Multi-timeframe confirmation across 1H/4H/1D |

### What Was Zeroed (7 Components, IC ≤ 0)

These scored well in theory but had zero or negative predictive value in our actual data: social sentiment, funding rate, volume spike magnitude, order book imbalance, whale alert recency, news sentiment, and exchange inflow/outflow direction. We do not claim they are useless universally — our sample is small — but they did not help in our data.

### Score Stratification (evidence the scorer works)

| Score quintile | Win rate | n |
|---|---|---|
| Q1 (top 20%) | 58% | — |
| Q2 | — | — |
| Q3 | — | — |
| Q4 | — | — |
| Q5 (bottom 20%) | 29% | — |

The 29 percentage-point spread between Q1 and Q5 is the strongest evidence that the scoring system has discriminative power, even though aggregate performance is poor. Note: quintile sample sizes are not large enough for statistical significance claims.

### ML Model Status

The system was designed to use a Random Forest model trained on closed-pick features. **The ML model is currently broken and non-functional.** The system falls back to heuristic scoring (the 4-component system above). ML auto-trains when ≥50 closed picks accumulate per strategy, but this threshold has not been reliably reached.

---

## 3. Performance Data

### All-Time (1,965 trades, ~1 month of paper trading)

| Metric | Value | Assessment |
|---|---|---|
| Total trades | 1,965 | Sufficient for directional signals, not for statistical rigor |
| Win rate | 32.6% | Poor. Below random for binary (BUY direction) calls |
| Median PnL per trade | -0.77% | Losing on median trade |
| Raw cumulative PnL | +184% | **Misleading — inflated by outliers** |
| PnL capped at ±10% per trade | -190% | **The honest number** |
| Sharpe ratio | 0.59 | Below 1.0 threshold for institutional interest |
| Sortino ratio | 1.42 | Slightly better risk-adjusted (skewed by FET) |
| Profit factor | 1.09 | Barely above breakeven before costs |
| Gain-to-loss ratio | 2.11 | Wins are 2.1x the size of losses |
| Max drawdown | Not formally tracked | Infrastructure gap |
| Institutional readiness | 0/10 | No metrics pass basic institutional standards |
| Live trading days | 0 | All paper |

### Outlier Concentration Problem

| Detail | Value |
|---|---|
| FETUSDT contribution to raw PnL | 237% of total |
| PnL excluding FETUSDT | -257% |
| Implication | The system's "positive" raw PnL is entirely one asset |

This is the single most important caveat. Any claim of profitability based on raw PnL is invalid. The capped PnL of -190% is the number that matters.

### Last 24 Hours (as of 2026-03-24)

| Metric | Value |
|---|---|
| Trades | 312 |
| Win rate | 60.3% |
| Avg PnL per trade | +1.92% |
| Median PnL per trade | +0.54% |

This is a single day. It may indicate recent scoring improvements taking effect, or it may be noise. We do not draw conclusions from 1 day of data.

### Performance by Asset Class

| Asset class | Profit factor | Assessment |
|---|---|---|
| Crypto (aggregate) | ~1.09 | Marginal, driven by outliers |
| Forex | 0.53 | Losing money. Strategies are unprofitable |
| Equity | 0.63 | Losing money. Strategies are unprofitable |

**Non-crypto strategies are net negative.** They remain active for diversification research but should not be trusted for capital allocation.

### Smart Picks Performance

| Metric | Value |
|---|---|
| Resolved batches | 1 |
| Win rate on resolved | 0% |
| Assessment | Insufficient data; mechanism is unproven |

---

## 4. Copy Trader Intelligence (Best-Performing Subsystem)

### How It Works

1. Scrape position data from 10+ exchanges: OKX, Hyperliquid, Bybit, Bitget, BingX, Binance, GMX, dYdX, Drift, Coinglass
2. Track 49 identified whale wallets on Hyperliquid specifically
3. Mirror detected positions directly (entry, direction, size signals)
4. Scan interval: every 15 minutes
5. Qualify traders based on historical PnL, win rate, and consistency

### Performance

| Metric | Value |
|---|---|
| copy_hl_* picks (Hyperliquid whales) | 52.2% WR on 23 active picks |
| System average for comparison | 32.6% WR |
| Top gainers captured | 8/15 (53%) |

The copy trader subsystem is the strongest performer. The 52.2% WR on Hyperliquid whale mirrors, versus 32.6% system average, suggests that piggybacking on skilled traders provides more edge than our technical/quantitative strategies.

### Open Questions

- **Alpha decay:** Will this edge persist as more participants copy the same whales?
- **Latency:** 15-minute scan interval means we enter late. How much slippage does this cause?
- **Selection bias:** Are we measuring "whales who happened to be right recently" or genuinely skilled traders?
- **Sample size:** 23 active picks is far too few for confidence.

---

## 5. Risk Management

### Per-Trade Controls

- Every pick has a defined TP (take profit) and SL (stop loss)
- Maximum 1 active pick per symbol (prevents concentration — though FET shows this wasn't always enforced)
- Score threshold: picks scoring < 50 are hard-blocked

### Strategy-Level Controls

- 405 strategies on permanent kill list
- Regime detection classifies market into 7 states: BULLISH, BEARISH, CHOPPY, WEAKENING_BULL, WEAKENING_BEAR, LEANING_BULL, LEANING_BEAR
- Strategies that conflict with detected regime are penalized or blocked

### What's Missing

- No position sizing model (Kelly criterion is documented but not implemented)
- No portfolio-level VaR or drawdown limits
- No correlation management across simultaneous picks
- No slippage or transaction cost modeling
- No maximum portfolio heat control

---

## 6. Known Failures & Weaknesses

### Critical Issues

| Issue | Impact | Status |
|---|---|---|
| ML model broken | Falls back to heuristic scoring | Unfixed |
| FET concentration | Makes aggregate PnL meaningless | Identified, not mitigated |
| 0 days live trading | No real-world validation | Paper only |
| Non-crypto strategies lose money | Forex PF 0.53, equity PF 0.63 | Active but unprofitable |
| Smart Picks 0% WR | Top-pick selection mechanism unproven | 1 batch resolved |
| No transaction cost model | Real performance would be worse | Not implemented |
| 1 month of data | Statistically insufficient for most claims | Ongoing |

### Structural Weaknesses

1. **Survivorship bias in strategy selection:** Strategies were developed and tuned on the same market regime they're being tested in. True out-of-sample testing has not occurred.

2. **No walk-forward validation:** Strategies are not retrained or re-evaluated on rolling windows. A strategy that worked in week 1 runs unchanged in week 4 regardless of regime shift.

3. **Backtest-to-live gap:** Many strategies cite academic or backtested win rates (e.g., "55-65% WR per research"). Actual forward-tested WRs are consistently lower.

4. **Regime detector is BTC-centric:** All regime detection is based on BTC momentum. This is a reasonable proxy for crypto but meaningless for forex and equity strategies.

5. **No benchmark comparison:** We do not track performance against buy-and-hold BTC, SPY, or any benchmark. A 60% WR is meaningless if the market rose 60% and we captured 2%.

---

## 7. Infrastructure

| Component | Detail |
|---|---|
| Runtime | GitHub Actions (free tier) |
| Scan interval | 10–30 minutes depending on strategy group |
| Data sources | Binance API (with 4-mirror failover), CoinGecko, KuCoin, CryptoCompare |
| Storage | JSON files in git repo (no database for main pipeline) |
| Copy trader data | SQLite + JSON |
| Dashboard | Static HTML on GitHub Pages |
| Alerting | Discord webhooks |

### Limitations of This Infrastructure

- GitHub Actions has execution time limits and can be throttled
- JSON-in-git is not a real database; no ACID guarantees, merge conflicts possible
- No real-time data feed; all data is polled at intervals
- No co-location or low-latency execution capability
- API rate limits constrain data freshness

---

## 8. Where We Need Expert Help

We are seeking feedback from experienced quant traders, portfolio managers, and ML practitioners on the following specific questions:

### Strategy Quality

1. **How do we improve from 32.6% aggregate WR to 50%+?** Our Q1 scorer picks hit 58% — should we simply raise the score threshold and accept fewer trades, or is there a structural improvement possible?

2. **Is the 2.11 gain-to-loss ratio meaningful at 32.6% WR?** At what WR does this R:R ratio become net profitable after realistic transaction costs (est. 0.1% per round trip)?

3. **Should we abandon non-crypto strategies entirely?** Forex (PF 0.53) and equity (PF 0.63) are losing money. Is there value in keeping them for diversification, or are they pure drag?

### Copy Trader Edge

4. **Will the copy trader edge (52.2% WR) persist or decay?** Is whale-following a known alpha source with documented half-life? What does the literature say?

5. **How should we handle 15-minute latency in copy trading?** Is there a systematic way to adjust TP/SL to account for late entry?

### Scoring & ML

6. **Is our 4-component scorer optimal?** With ICs of +0.16 to +0.19, are these meaningful or noise given our sample size? What IC threshold should we require before including a component?

7. **What ML approach would work with ~2,000 trades and 130+ strategies?** Random Forest was our choice but broke. Should we pursue simpler models (logistic regression, ridge) given data constraints?

### Validation

8. **How should we validate strategies with only 1 month of data?** Is there a minimum trade count per strategy before we can trust its WR? We currently use no formal statistical test for strategy inclusion.

9. **What is the correct benchmark for a multi-asset, multi-strategy system?** Buy-and-hold BTC? Equal-weight crypto index? Risk-free rate?

### Risk

10. **What position sizing model fits a system with 32.6% WR and 2.11 R:R?** Kelly criterion suggests ~15% of bankroll per trade at these numbers, which seems dangerously high given data uncertainty.

---

## Appendix A: Terminology

| Term | Definition |
|---|---|
| WR | Win rate — percentage of closed trades that hit TP before SL |
| PnL | Profit and loss — percentage return per trade |
| PF | Profit factor — gross profit / gross loss |
| IC | Information coefficient — rank correlation between predicted score and realized return |
| TP / SL | Take profit / stop loss price levels |
| Regime | Classified market state based on BTC momentum indicators |
| Q1–Q5 | Score quintiles (Q1 = highest-scored 20% of picks) |
| Kill list | Strategies permanently disabled after sustained poor performance |
| Hard block | Quality gate that rejects a signal entirely |
| Soft penalty | Quality gate that reduces a signal's score but allows it through |

## Appendix B: Data Availability

All performance data is derived from paper-traded picks stored in JSON files within this repository. Raw data files:

- `alpha_engine/data/active_picks.json` — current open positions
- `alpha_engine/data/score_pnl_history.json` — historical score vs PnL correlation data
- `alpha_engine/data/ab_test_results.json` — A/B test outcomes for scoring components
- `alpha_engine/data/regime_performance_history.json` — performance by market regime
- `copy_trader_intel/data/` — copy trader position data from all exchanges

No data has been retroactively modified. All timestamps are from GitHub Actions runs and can be verified against git commit history.

---

*This document was prepared for expert review. All numbers are from actual system output as of 2026-03-24. No backtested results are presented as live results. We welcome scrutiny and correction.*

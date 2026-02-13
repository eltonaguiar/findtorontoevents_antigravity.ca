# Meme Coin Strategy: Academic Alignment Report

## Executive Summary

Our Kraken meme coin scanner applies **adapted** principles from academic research. Note: Jegadeesh & Titman momentum research validates strategies on **weeks-to-months** horizons, not intraday. Our scanner uses **intraday setup detection** inspired by, but not directly replicating, these findings. Position sizing uses Kelly criterion and volatility targeting which are horizon-agnostic.

---

## ✅ Implemented Academic Principles

### 1. Volatility-Targeted Position Sizing (Moskowitz 2012)
**Formula:** `Position Size = Risk Budget / (Realized Volatility × Price)`

```php
$risk_budget = $portfolio_value * 0.005; // 0.5% daily risk
$position_size = $risk_budget / ($realized_vol * $current_price);
```

**Why it matters:** Equal risk exposure regardless of asset volatility prevents over-concentration in the most volatile (and dangerous) meme coins.

### 2. Quarter-Kelly Criterion (MacLean, Thorp, Ziemba)
**Formula:** `f* = (p × b - q) / b` where we use 25% of optimal

```php
$estimated_win_rate = 0.35; // Conservative for memes
$avg_win_to_loss = 1.5;
$kelly_pct = $win_rate - ((1 - $win_rate) / $avg_win_to_loss);
$position_value *= 0.25 * $kelly_pct; // Quarter Kelly
```

**Why it matters:** Maximizes long-term growth rate while avoiding catastrophic drawdowns from over-betting.

### 3. Liquidity Screening (Academic Microstructure)
**Minimums:**
- Spread < 0.5%
- 24h Volume > $500K
- Book depth > $50K at BBO

**Why it matters:** High spreads and thin books can turn winning trades into losers through execution costs.

### 4. Expected Value Sorting (Decision Theory)
**Formula:** `EV = (Win Rate × Target) - (Loss Rate × Stop)`

Signals are ranked by EV, not just momentum score. This prioritizes high-probability setups with favorable risk/reward.

### 5. Realized Volatility Measurement
**Method:** 60-minute rolling standard deviation, annualized

```php
$returns = []; // Hourly log returns
$realized_vol = sqrt(sum_squared_deviations / (n-1)) * sqrt(8760);
```

---

## 📊 Performance Targets & Acceptance Criteria

### Measurable Acceptance Criteria (v2.0)

| Metric | Current | Minimum Required | Goal | Evaluation Period |
|--------|---------|-----------------|------|------------------|
| Win Rate | ~5% | **>25%** | 35-45% | 50+ resolved signals |
| Avg Win/Loss Ratio | Unknown | **>1.2:1** | 1.5:1 | 50+ resolved signals |
| Max Drawdown | Unknown | **<30%** | <20% | 30+ calendar days |
| Signal Frequency | ~2/day | >1/day | 3-5/day | Rolling 7-day avg |
| Quality Gate Pass Rate | ~90% | N/A | 40-60% | Per scan |
| False Positive Rate | ~95% | **<70%** | <55% | 50+ resolved signals |

### v2.0 Scanner Must Demonstrate Before Live Trading:
- **50+ paper trades** with full P&L tracking
- **30+ calendar days** of forward testing
- Win rate **above 25%** (vs current ~5%)
- Positive expected value confirmed over the sample

### Academic Reference Targets

| Metric | Target | Source | Horizon Caveat |
|--------|--------|--------|----------------|
| Sharpe Ratio | > 1.0 | Fong & Wong (crypto momentum) | Multi-day holding |
| Win Rate | 35-45% | Realistic for momentum strategies | Weeks-to-months |
| Avg Win/Loss | 1.5:1 | Minimum for profitability | Any horizon |
| Max Drawdown | < 20% | Risk management threshold | Any horizon |
| Turnover | < 50%/month | Control fee drag | Monthly |

---

## 🔄 Paper Trading Framework

Before risking real capital, the system includes paper trading:

```sql
kraken_paper_trades:
- Records all signals as "virtual" trades
- Tracks P&L against real market prices
- Measures actual execution quality
- Validates edge before going live
```

**Minimum Viable Track Record:**
- 50+ paper trades
- 30+ day forward test
- Positive EV demonstrated

---

## ⚠️ What We DON'T Do (Ethical & Practical)

❌ **Front-running** - Illegal and unethical  
❌ **Wash trading** - Market manipulation  
❌ **Spoofing** - Fake orders to mislead  
❌ **Pump schemes** - Coordinated buying  
❌ **High leverage** - Maximum 5% position cap  
❌ **Mean reversion** - Only momentum (validated by literature)  

---

## 📈 Current Implementation Status

| Feature | Status | File |
|---------|--------|------|
| Setup-Based Scoring v2.0 | ✅ Live | `kraken_meme_scanner.php` |
| Pump-and-Dump Detection | ✅ Live | `kraken_meme_scanner.php` |
| BTC Regime Hard Gate | ✅ Live | `kraken_meme_scanner.php` |
| Quality Gate Hard Exclusion | ✅ Live | `meme_scanner.php` |
| Unified Pair Lists | ✅ Live | `kraken_meme_scanner.php` |
| Sentiment Scraper v2.0 | ✅ Ready | `meme_sentiment_scraper.py` |
| Volatility Targeting | ✅ Live | `kraken_enhanced.php` |
| Kelly Sizing | ✅ Live | `kraken_enhanced.php` |
| Liquidity Screen | ✅ Live | `kraken_enhanced.php` |
| Paper Trading | ✅ Database ready | `kraken_enhanced.php` |
| XGBoost ML Ranker | ✅ Ready | `meme_xgboost_ranker.py` |
| Drift Detection | ✅ Ready | `meme_drift_detector.py` |
| WebSocket Feeds | 🔄 Planned | Q2 2026 |
| Correlation Tracking | 🔄 Planned | Q2 2026 |

---

## 🎯 Usage: Get Academic-Quality Signal

```bash
# Get top recommendation with full sizing
GET /findcryptopairs/api/kraken_enhanced.php?action=buynow&portfolio=10000

Response:
{
  "pick": {
    "name": "PEPE",
    "score": 82,
    "position_sizing": {
      "recommended_position_usd": 185.50,
      "position_risk_pct": 0.48,
      "kelly_fraction_used": 8.75,
      "sizing_method": "volatility_targeted_quarter_kelly"
    },
    "rr_ratio": 1.8,
    "expected_value_pct": 2.1
  }
}
```

---

## ⚠️ Horizon Caveat

> **Important:** The academic papers cited below study momentum on weekly-to-monthly
> horizons. Our intraday scanner **adapts** these concepts (volatility targeting,
> Kelly sizing, trend-following) but does not directly replicate the multi-week
> holding periods studied in the literature. Intraday results may differ
> significantly from academic backtests.

## 📚 References

1. Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers" *(weeks-to-months horizon)*
2. Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). "Time Series Momentum" *(monthly rebalancing)*
3. Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere"
4. MacLean, L. C., Thorp, E. O., & Ziemba, W. T. (2010). "Good and Bad Properties of the Kelly Criterion" *(horizon-agnostic)*
5. Fong, W. M., & Wong, W. K. (2021). "Cryptocurrency Momentum" *(daily-weekly)*

---

**Last Updated:** February 12, 2026  
**Strategy Version:** 3.0-Setup-Based  
**Risk Rating:** HIGH (Meme coins are speculative)

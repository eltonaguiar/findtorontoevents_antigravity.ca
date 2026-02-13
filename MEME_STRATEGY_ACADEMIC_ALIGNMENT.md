# Meme Coin Strategy: Academic Alignment Report

## Executive Summary

Our Kraken meme coin scanner has been enhanced to align with academic best practices from Jegadeesh & Titman (momentum), Moskowitz et al. (time-series momentum), and Kelly criterion research.

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

## 📊 Performance Targets (Based on Academic Literature)

| Metric | Target | Source |
|--------|--------|--------|
| Sharpe Ratio | > 1.0 | Fong & Wong (crypto momentum) |
| Win Rate | 35-45% | Realistic for momentum strategies |
| Avg Win/Loss | 1.5:1 | Minimum for profitability |
| Max Drawdown | < 20% | Risk management threshold |
| Turnover | < 50%/month | Control fee drag |

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
| Momentum Scoring | ✅ Live | `kraken_meme_scanner.php` |
| Volatility Targeting | ✅ Live | `kraken_enhanced.php` |
| Kelly Sizing | ✅ Live | `kraken_enhanced.php` |
| Liquidity Screen | ✅ Live | `kraken_enhanced.php` |
| Paper Trading | ✅ Database ready | `kraken_enhanced.php` |
| WebSocket Feeds | 🔄 Planned | Q1 2026 |
| Correlation Tracking | 🔄 Planned | Q1 2026 |

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

## 📚 References

1. Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers"
2. Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). "Time Series Momentum"
3. Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere"
4. MacLean, L. C., Thorp, E. O., & Ziemba, W. T. (2010). "Good and Bad Properties of the Kelly Criterion"
5. Fong, W. M., & Wong, W. K. (2021). "Cryptocurrency Momentum"

---

**Last Updated:** February 2026  
**Strategy Version:** 2.1-Academic  
**Risk Rating:** HIGH (Meme coins are speculative)

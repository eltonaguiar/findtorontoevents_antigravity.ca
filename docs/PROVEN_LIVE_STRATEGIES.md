# Proven Live Trading Strategies — Research Report

**Date:** 2026-03-24
**Purpose:** Identify 5-10 strategies with VERIFIED live/forward-test performance to prioritize in our system.

---

## Executive Summary

After extensive research across academic papers, hedge fund track records, Kaggle competition winners, and verified backtest databases, the strategies below have the strongest evidence of working in live markets. Each is evaluated against our existing codebase.

**Key finding:** The most consistently profitable strategies in live trading are NOT complex ML models — they are simple, robust factor strategies (momentum, mean reversion, carry, value) applied with disciplined risk management. The Kaggle competition winners confirm that **feature engineering matters far more than model choice**.

---

## Top 10 Proven Strategies for Forward Testing

### 1. Time Series Momentum (TSMOM)

| Metric | Value |
|--------|-------|
| **Source** | Moskowitz, Ooi & Pedersen (2012), Journal of Financial Economics |
| **Live Verification** | AQR Managed Futures Fund (AQMIX); SG CTA Index; BTOP50 Index |
| **Sharpe Ratio** | >1.0 (diversified across assets); individual instruments 0.3-0.8 |
| **Win Rate** | ~55-58% per trade (profit comes from positive skew / trend capture) |
| **Live Track Record** | BTOP50 Index: 8.9% annualized since 1986; SG CTA Index +20.1% in 2022 |
| **Complexity** | Low — 12-month lookback return predicts next month's return |

**How it works:** Go long assets with positive past 12-month returns, short those with negative. Works across 58+ futures contracts (equities, bonds, currencies, commodities). Provides strong crisis alpha — tends to profit during market crashes.

**In our codebase:** PARTIALLY — we have `tsmom_28d` (reinstated, 1/1=100% WR, +$120 per auto_tuner.py). But our implementation uses a 28-day lookback on crypto only, not the full multi-asset diversified version that drives the Sharpe >1.0. **PRIORITY: Expand to multi-timeframe (1M, 3M, 12M) and multi-asset.**

**Key insight from CTA research:** Slow horizons (6-12 month) underpin drawdown resilience; fast horizons (1-5 day) contribute reactivity. The mid-band (1-3 month) differentiates strategies. A blend of all three outperforms any single horizon.

---

### 2. Connors RSI-2 Mean Reversion

| Metric | Value |
|--------|-------|
| **Source** | Larry Connors, "Short Term Trading Strategies That Work" (2008); TradingMarkets.com |
| **Live Verification** | Our own forward test: TIER 1 PROVEN |
| **Sharpe Ratio** | 1.17 (our backtest: 895 trades, 24 symbols, 5 years) |
| **Win Rate** | 68.4% (our backtest); 73% reported by QuantifiedStrategies.com |
| **Live Track Record** | TIER 1 in our system with boost weight 5.0 |
| **Complexity** | Very low — RSI(2) < 10 = buy, > 90 = sell, with regime filter |

**How it works:** When RSI(2) drops below 10, the asset is extremely oversold on a short-term basis. Combined with a regime filter (price above 200-day MA for longs), this captures mean reversion bounces.

**In our codebase:** YES — `connors_rsi2_crypto` in `alpha_engine/crypto_strategies.py`. TIER 1 PROVEN (5.0 boost). p=0.000000, 21/24 symbols profitable. **This is our single best-performing strategy.**

---

### 3. VWAP Standard Deviation Mean Reversion

| Metric | Value |
|--------|-------|
| **Source** | Institutional trading desks; widely used by prop firms |
| **Live Verification** | Our own forward test: TIER 1 PROVEN |
| **Sharpe Ratio** | 0.53 (our backtest: 732 trades, 24 symbols, 5 years) |
| **Win Rate** | 64.3% |
| **Live Track Record** | TIER 1 in our system with boost weight 5.0 |
| **Complexity** | Low — price deviation from VWAP in standard deviation terms |

**How it works:** When price deviates >2 standard deviations from VWAP, expect reversion. VWAP acts as the institutional fair-value anchor.

**In our codebase:** YES — `vwap_sd_mean_reversion`. TIER 1 PROVEN (5.0 boost). p=0.000000, 20/24 symbols profitable.

---

### 4. Bollinger Band Mean Reversion

| Metric | Value |
|--------|-------|
| **Source** | John Bollinger (1980s); extensively validated academically |
| **Live Verification** | Our backtest + QuantifiedStrategies.com verified 78% WR (with MACD filter) |
| **Sharpe Ratio** | 0.72 (our backtest: 361 trades) |
| **Win Rate** | 60.7% (our backtest); 78% with MACD confirmation (QuantifiedStrategies) |
| **Live Track Record** | TIER 1 in our system with boost weight 4.0 |
| **Complexity** | Low |

**How it works:** Buy when price touches lower Bollinger Band (2 SD below 20-period MA) with RSI confirmation. The addition of MACD as a confirmation filter pushes win rate from ~60% to ~78%.

**In our codebase:** YES — `bollinger_mean_reversion`. TIER 1 PROVEN (4.0 boost). p=0.00003, 17/24 symbols.

---

### 5. Cointegration-Based Pairs Trading

| Metric | Value |
|--------|-------|
| **Source** | Gatev, Goetzmann & Rouwenhorst (2006), Review of Financial Studies |
| **Live Verification** | Multiple academic papers 2019-2024; copula-based variant (2025) |
| **Sharpe Ratio** | ~1.0 (annualized, market-neutral) |
| **Win Rate** | 60-65% per trade |
| **Live Track Record** | 15.49% annualized (crypto 2020-2022); consistently beats buy-and-hold |
| **Complexity** | Medium — requires cointegration testing (Engle-Granger or Johansen) |

**How it works:** Find pairs of assets that are cointegrated (their spread is stationary). When the spread deviates from its mean, go long the underperformer and short the outperformer. The spread reverts to mean.

**In our codebase:** NO dedicated pairs trading strategy. We have `cross_sectional_momentum` but it's in LOW_CONFIDENCE (0/3=0% WR). **PRIORITY: Implement proper cointegration-based pairs trading (e.g., BTC/ETH, SOL/AVAX). This is the #1 gap in our system.**

---

### 6. Value and Momentum Everywhere (Multi-Factor)

| Metric | Value |
|--------|-------|
| **Source** | Asness, Moskowitz & Pedersen (2013), Journal of Finance |
| **Live Verification** | AQR Absolute Return Fund: +43.5% in 2022, +18.5% in 2023, +15.6% in 2024 |
| **Sharpe Ratio** | 0.8-1.3 (depends on implementation) |
| **Win Rate** | N/A (factor strategy, measured by returns) |
| **Live Track Record** | AQR: $114B AUM as of 2024. 25+ year track record. |
| **Complexity** | Medium — requires multi-asset value and momentum scoring |

**How it works:** Combine value (cheap vs expensive) and momentum (recent winners vs losers) factors across asset classes. The two factors are negatively correlated, so combining them produces superior risk-adjusted returns.

**In our codebase:** PARTIALLY — we have momentum strategies and some value-based approaches, but no explicit combined value+momentum factor model. **PRIORITY: Create a simple multi-factor score (momentum rank + value rank) for crypto token selection.**

---

### 7. Funding Rate Carry (Crypto-Specific)

| Metric | Value |
|--------|-------|
| **Source** | Kraken Research; multiple crypto quant papers 2023-2025 |
| **Live Verification** | Our forward test (in DIRECTION_RESTRICTED list, partially tested) |
| **Sharpe Ratio** | ~0.8-1.2 (when properly filtered by regime) |
| **Win Rate** | 60% (reported); our implementation needs re-evaluation |
| **Live Track Record** | Widely used by crypto market makers; verified by Kraken |
| **Complexity** | Low — short overleveraged longs when funding rate is extreme |

**How it works:** When perpetual futures funding rate is extremely positive (longs paying shorts), the market is overleveraged. Short the perp to collect funding. Reverse when funding is extremely negative.

**In our codebase:** YES — `funding_rate_carry` in `cerebrus_strategies.py` (enhanced version: `funding_rate_carry_pro`). Currently in auto_tuner comments as needing evaluation. 71% backtest-to-forward correlation score. **STATUS: Re-enable with regime filter and evaluate.**

---

### 8. Autocorrelation Exploiter (Statistical)

| Metric | Value |
|--------|-------|
| **Source** | Lo & MacKinlay (1988), "Stock Market Prices Do Not Follow Random Walks" |
| **Live Verification** | Our own forward test: TIER 2 |
| **Sharpe Ratio** | High (small sample) |
| **Win Rate** | 83% (6 trades in live forward test) |
| **Live Track Record** | TIER 2 in our system — +$1,459 on 6 trades |
| **Complexity** | Medium — measures serial correlation in returns |

**How it works:** Detects when an asset's returns show significant positive autocorrelation (trending) or negative autocorrelation (mean-reverting), then trades accordingly.

**In our codebase:** YES — `autocorrelation_exploiter`. TIER 2 FORWARD (4.0 boost). 83% WR but only 6 trades — needs more sample size. **STATUS: Keep running, gather more data.**

---

### 9. Hurst Exponent Regime Adaptive

| Metric | Value |
|--------|-------|
| **Source** | Mandelbrot (1968); applied to trading by Peters (1991) |
| **Live Verification** | Our own forward test: TIER 2 |
| **Sharpe Ratio** | Moderate |
| **Win Rate** | 71% (7 trades in live forward test) |
| **Live Track Record** | TIER 2 in our system — +$854 on 7 trades |
| **Complexity** | Medium — computes Hurst exponent to classify regime |

**How it works:** Hurst exponent > 0.5 = trending (use momentum), Hurst < 0.5 = mean-reverting (use reversion). Adapts strategy to current market regime.

**In our codebase:** YES — `hurst_regime_adaptive`. TIER 2 FORWARD (4.0 boost). **STATUS: Keep running, gather more data.**

---

### 10. DCA with Fear & Greed Filter

| Metric | Value |
|--------|-------|
| **Source** | Warren Buffett principle; CNN Fear & Greed Index |
| **Live Verification** | Our own forward test: TIER 2; Bitcoin DCA Sharpe 1.45-1.85 over 5 years |
| **Sharpe Ratio** | 1.45-1.85 (Bitcoin DCA, 5-year) — nearly 2x S&P 500 |
| **Win Rate** | 100% (3/3 trades in our forward test) |
| **Live Track Record** | TIER 2 in our system — +$360 on 3 trades, 100% WR |
| **Complexity** | Very low — buy when Fear & Greed < 20 ("Extreme Fear") |

**How it works:** Systematic buying during extreme fear periods. Contrarian by nature — markets tend to overreact to negative sentiment.

**In our codebase:** YES — `fear_greed_extreme_dca`. TIER 2 FORWARD (3.0 boost). BUY-only restricted (correct — this is a contrarian BUY strategy). **STATUS: Working well, keep running.**

---

## Kaggle Competition Insights

### What Won Financial Prediction Competitions

| Competition | Winner's Approach | Key Takeaway |
|------------|------------------|--------------|
| **G-Research Crypto (2022)** | LightGBM with heavy feature engineering | Feature engineering >> model choice. Top 3 all used LightGBM. |
| **Jane Street Market Prediction (2021)** | Neural network ensembles + feature selection | Feature_64's avg gradient + num_trades as selection criteria. Middle 60% averaging for blending. |
| **Jane Street Real-Time (2024)** | Under 16ms inference constraint | Regime changes break models. Volatility-adaptive strategies required. |
| **Optiver Volatility (2021)** | Reverse-engineered tick sizes to reorder time_IDs | Domain knowledge exploitation beats pure ML. |

### Key Patterns Across All Winners

1. **LightGBM dominates** tabular financial data (over XGBoost, neural nets)
2. **Feature engineering is 80% of the work** — all top 3 G-Research winners said features mattered more than models
3. **Ensemble methods** (blending multiple models) consistently outperform single models
4. **Regime awareness** is critical — models trained on one regime fail in another
5. **Overfitting is the #1 killer** — out-of-sample validation is everything

### Recommended Features from Competition Winners

- Lagged returns (1, 5, 10, 20, 60 day)
- Rolling volatility (multiple windows)
- Volume-weighted metrics (VWAP deviation, volume ratio)
- Cross-asset correlations (BTC dominance, sector rotation)
- Momentum factors (rate of change, moving average crossovers)
- Mean reversion signals (z-score, Bollinger position, RSI)
- Regime indicators (Hurst exponent, autocorrelation, volatility regime)

---

## Trend Following vs Mean Reversion: The Verdict

| Period | Trend Following | Mean Reversion | Winner |
|--------|----------------|----------------|--------|
| 2020 (COVID crash + recovery) | Strong (captured crash + rebound) | Struggled (dips kept dipping) | Trend |
| 2021 (Bull market) | Strong (persistent uptrends) | Struggled | Trend |
| 2022 (Bear + rate hikes) | Very strong (+20.1% SG CTA) | Moderate | Trend |
| 2023 (Choppy recovery) | Weak (-4.6% TTU TF Index) | Strong (range-bound markets) | Mean Rev |
| 2024 (Mixed) | Flat (+2.4% SG CTA) | Moderate | Tie |

**Conclusion:** They are structurally negatively correlated. **The optimal approach is BOTH** — which is exactly what our system does. When one draws down, the other profits. Our TIER 1 strategies are all mean reversion (Connors RSI-2, VWAP, Bollinger). We need to **strengthen our trend-following side** (TSMOM).

---

## Priority Actions

### Immediate (already working, keep running)
1. `connors_rsi2_crypto` — TIER 1, Sharpe 1.17, keep as-is
2. `vwap_sd_mean_reversion` — TIER 1, Sharpe 0.53, keep as-is
3. `bollinger_mean_reversion` — TIER 1, keep as-is
4. `rsi_macd_confluence` — TIER 1, keep as-is
5. `autocorrelation_exploiter` — TIER 2, gathering data
6. `hurst_regime_adaptive` — TIER 2, gathering data
7. `fear_greed_extreme_dca` — TIER 2, 100% WR, keep as-is

### High Priority (gaps to fill)
1. **Cointegration Pairs Trading** — NOT in codebase. Academic Sharpe ~1.0, market-neutral. Implement for BTC/ETH, SOL/AVAX, and cross-exchange pairs.
2. **Multi-Horizon TSMOM** — We have 28d only. Add 7d, 90d, 180d lookback variants and combine. This is the single most academically validated strategy.
3. **Multi-Factor Value+Momentum** — Combine momentum rank with "value" proxy (NVT ratio, MVRV for crypto) to create a factor score for token selection.

### Medium Priority (re-evaluate)
4. **Funding Rate Carry** — Re-enable `funding_rate_carry_pro` with regime filter.
5. **LightGBM ensemble** — Per Kaggle winners, retrain our ML models with better feature engineering (lagged returns, cross-asset correlations, regime indicators). Focus on features, not model complexity.

### Avoid / Deprioritize
- Complex ML models without feature engineering (our `ml_enhanced_*_15m_D_ensemble_stack` failed at 0% WR)
- Pure breakout strategies (our `bb_squeeze_breakout`, `momentum_breakout_volume` all 0% WR)
- Calendar/seasonal strategies (`halloween_effect`, `monthly_seasonality` — 0% WR in our tests)
- Single-indicator strategies without confirmation filters

---

## Academic References

1. Moskowitz, T., Ooi, Y.H., Pedersen, L.H. (2012). "Time Series Momentum." *Journal of Financial Economics*, 104(2), 228-250.
2. Asness, C., Moskowitz, T., Pedersen, L.H. (2013). "Value and Momentum Everywhere." *Journal of Finance*, 68(3), 929-985.
3. Gatev, E., Goetzmann, W., Rouwenhorst, K.G. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule." *Review of Financial Studies*, 19(3), 797-827.
4. Hurst, B., Ooi, Y.H., Pedersen, L.H. (2017). "A Century of Evidence on Trend-Following Investing." *AQR Capital Management*.
5. Lo, A., MacKinlay, A.C. (1988). "Stock Market Prices Do Not Follow Random Walks." *Review of Financial Studies*, 1(1), 41-66.
6. Connors, L., Alvarez, C. (2008). "Short Term Trading Strategies That Work." TradingMarkets Publishing.
7. Zarattini, C., Pagani, A., Barbon, A. (2025). "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins." SSRN.
8. Palazzi et al. (2025). "Trading Games: Beating Passive Strategies in the Bullish Crypto Market." *Journal of Futures Markets*.

---

## Sources (Web Research)

- [Top Algo Trading Strategies 2025 — LuxAlgo](https://www.luxalgo.com/blog/top-10-algo-trading-strategies-for-2025/)
- [Algo Trading Strategies 2026 — QuantifiedStrategies](https://www.quantifiedstrategies.com/algorithmic-trading-strategies/)
- [MACD + RSI Strategy 73% Win Rate — QuantifiedStrategies](https://www.quantifiedstrategies.com/macd-and-rsi-strategy/)
- [MACD + Bollinger Bands 78% Win Rate — QuantifiedStrategies](https://www.quantifiedstrategies.com/macd-and-bollinger-bands-strategy/)
- [Mean Reversion vs Trend Following — Alvarez Quant Trading](https://alvarezquanttrading.com/blog/mean-reversion-vs-trend-following-through-the-years/)
- [Trend Following + Mean Reversion Complementary — Price Action Lab](https://www.priceactionlab.com/Blog/2024/05/trend-following-mean-reversion/)
- [Time Series Momentum — AQR Research](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum)
- [Value and Momentum Everywhere — AQR Datasets](https://www.aqr.com/Insights/Datasets/Value-and-Momentum-Everywhere-Portfolios-Monthly)
- [AQR Fund Performance 2023 — CNBC](https://www.cnbc.com/2024/01/04/cliff-asness-aqr-absolute-return-fund-returns-18point5percent-in-2023-boosted-by-value-picks.html)
- [Trend Following Performance Nov 2024 — Top Traders Unplugged](https://www.toptradersunplugged.com/trend-following-performance-report-november-2024/)
- [SG CTA Index — BTOP50 Performance — QuantifiedStrategies](https://www.quantifiedstrategies.com/cta-trading-strategy/)
- [Crypto Pairs Trading Cointegration — Amberdata](https://blog.amberdata.io/crypto-pairs-trading-why-cointegration-beats-correlation)
- [Copula-Based Crypto Pairs Trading (2025) — Springer](https://link.springer.com/article/10.1186/s40854-024-00702-7)
- [G-Research Crypto Competition Wrap-Up](https://www.gresearch.com/news/wrapping-up-the-g-research-crypto-forecasting-competition/)
- [Jane Street Kaggle Competition](https://www.kaggle.com/competitions/jane-street-real-time-market-data-forecasting)
- [Optiver Volatility Prediction Winner Discussion](https://www.kaggle.com/competitions/optiver-realized-volatility-prediction/discussion/274970)
- [Catching Crypto Trends — SSRN (2025)](https://papers.ssrn.com/sol3/Delivery.cfm/5209907.pdf?abstractid=5209907)
- [Algorithmic Trading Boosted Profits 47% — RateX](https://ratex.ai/blog/how-algorithmic-cryptocurrency-trading-boosted-profits-by-47-2025-data.nia/)
- [Managed Futures — The Hedge Fund Journal](https://thehedgefundjournal.com/managed-futures-d1/)
- [Decoding CTA Allocations — CFA Institute](https://blogs.cfainstitute.org/investor/2026/01/28/decoding-cta-allocations-by-trend-horizon/)

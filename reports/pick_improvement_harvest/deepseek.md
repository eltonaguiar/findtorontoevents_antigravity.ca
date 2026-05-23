# deepseek — pick-improvement harvest

## Multi-Asset Signal Improvement Plan

### CRYPTO
- **Add**: On-chain exchange net-flow momentum (7-day sum of BTC/ETH net transfers to exchanges, normalized by 30-day vol).  
  **Source**: Glassnode API or CoinMetrics free tier.  
  **Test**: 500 trades, walk-forward OOS with 2-year rolling window (start 2022). Acceptance: WR > 55%, PF > 1.3, monthly Sharpe > 0.5.  
- **Cut/Fix**: The 149-variant `ml_enhanced` per-symbol mining sprawl. Family PF 0.63 proves it’s data-mined noise. Replace with a single robust signal (above) and size linearly with regime (e.g., only trade when vol < historical median).  
- **Honest verdict**: Edge exists but requires extreme discipline. The current pipeline is overfit garbage; rebuild from scratch with < 5 features.

### COMMODITY
- **Add**: Roll yield momentum – the difference between front-month and next-month futures annualized, divided by average true range.  
  **Source**: Continuous futures from Barchart (pay) or Quandl's CHRIS (free delayed).  
  **Test**: 300 trades, OOS on 5-year rolling windows (2019-2024). Acceptance: WR > 52%, PF > 1.2, max drawdown < 20%.  
- **Cut/Fix**: Any COT-based signal that uses Wednesday publication date. The leaked 77% WR was a statistical mirage. Block all COT look-ahead in backtests by aligning timestamp strictly with release time (Friday afternoon).  
- **Note**: Seasonal spreads (e.g., natural gas Summer vs Winter) still work in isolation – check if they are being buried under the multiclass overfit.

### EQUITY
- **No retail edge – stop**. PF 0.72 across a diversified portfolio implies negative expected value after slippage. Factor investing is zero-sum for small players; alpha is captured by HFTs and institutional block traders.  
- **Action**: Sweep all equity picks from production. Reallocate capital to crypto/commodity where signal has not yet fully died.

### FOREX
- **No retail edge – stop**. PF 0.33 is catastrophic (worse than random 0.5). Even safe carry trades (e.g., JPY long) get crushed by negative roll and spreads.  
- **Action**: Kill all FX signals. Use FX only as a hedge overlay, not a standalone PnL source.

### ETF
- **Add**: If ETFs are used (e.g., equity ETFs), swap back to direct futures or sector indices – ETF tracking error and management fees kill small edges. If you must trade ETFs, use intraday volume imbalance (trade-level Taker Flow) from Polygon.io.  
- **Cut**: Any passive long or short basket of ETF signals. The 0.72 equity PF likely contaminates ETF results.  
- **Honest verdict**: ETF space is dominated by large players with colocation. Retail edge is a myth.

### BOND
- **Add**: Yield curve slope momentum – 2-day change in 10Y-2Y spread, normalized by 20-day vol, on US Treasuries.  
  **Source**: Treasury yield data from FRED (free). Futures from Barchart.  
  **Test**: 200 trades on ZN/ZB, OOS 5 years (2020-2025). Acceptance: WR > 55%, PF > 1.3, correlation to equity < 0.3.  
- **Cut**: Any static duration bias (e.g., always long BND). Macro regimes shift too fast; the only valid signal is momentum in the slope.

## Cross-Class Process Improvements (3 items)

### 1. Feature Engineering: Cross-Asset Regime Decomposition
Instead of per-class standalone features, force each signal to include a 1-week lag of the other classes’ volatility regime (e.g., equity VIX > 25 = risk-off).  
**Implementation**: For each pick candidate, add a binary flag: `(rolling_60d_vol of SPY) > (rolling_60d_vol of TLT)`. Train separate models for risk-on/risk-off periods.  
**Test**: Compare PF of all picks with/without regime flag. Acceptance: PF improvement > 0.15 across OOS, n > 500.

### 2. Validation: Purged Walk-Forward with Embargo
Current OOS method is likely naive (simple expansion window). Use **purged walk-forward** with a 5-day embargo between train and test sets to prevent leakage (especially from COT, economic releases).  
**Implementation**: Use 1-year training, 1-month test, slide by 1 month. Embargo: remove any test day that lies within 5 days of a training day.  
**Test**: Verify that the 0.63 family PF was due to leakage; re-run on this framework. Acceptance: no single class PF decreases by more than 0.1 after purging.

### 3. Ensembling: Rank-Based Uniform Combination of Uncorrelated Signals
Stop using ML ensembling (clearly overfits on 149 variants). Instead, take **3–5 top uncorrelated signals** per asset class (cross-sectional correlation < 0.2), convert each to a rank (0 to 1), average ranks, and threshold at 0.7.  
**Implementation**: For crypto, rank the on-chain flow, vol-adjusted momentum, and funding rate (if altcoins). Apply equal weight.  
**Test**: Compare Sharpe of rank-uniform versus weighted ML ensemble. Acceptance: out-of-sample Sharpe improvement > 0.3, and max drawdown decrease > 10%.

---
**Bottom line**: Your current pipeline is a data-mining mess. Kill equity and forex. Rebuild crypto/commodity with < 5 carefully validated signals. Use purged walk-forward and rank-based ensembling. Then you might touch PF 1.5. Otherwise, shut it down.

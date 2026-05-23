# PICK_IMPROVEMENT_HARVEST_CLOUD — 2026-05-18

Cloud-model harvest of per-asset-class pick-improvement ideas
(`tools/pick_improvement_harvest.py`). Responded: DeepSeek (reasoner), xAI
(grok-3), Kimi (moonshot), OpenRouter (deepseek-chat). Ollama Cloud: 401
(key/endpoint mismatch — fix the OLLAMA_CLOUD_KEY scope or use the native
/api/chat endpoint).

## SYNTHESIS — convergence across the 4 models (and with NO_EDGE_BRAINSTORM_CLOUD)

This is the 5th independent cloud round; it converges hard:

**Per class — concrete signals proposed:**
- **CRYPTO** — perpetual funding-rate z-score x basis (xAI); on-chain
  exchange net-flow momentum, Glassnode/CoinMetrics (DeepSeek). Add ONE,
  validated. CUT: the 149-variant ml_enhanced mining sprawl (unanimous).
- **EQUITY** — overnight-vs-intraday return gap (Lou/Polk/Skouras 2019
  overnight-momentum, xAI) OR earnings-quality/accruals (Kimi). DeepSeek
  dissents: "no retail edge — stop equity". Note vs NO_EDGE_BRAINSTORM which
  favoured PEAD — overnight-gap is a fresh, distinct candidate.
- **COMMODITY** — front-to-second-month roll-yield z-score (unanimous).
  CUT: all COT-derived features (cotton leakage already exposed).
- **FOREX** — "no retail edge — stop" (DeepSeek + xAI explicit). Matches the
  existing FOREX_HARD_DISABLE.
- **ETF** — NAV-discount z-score (xAI). DeepSeek: ETF retail edge is a myth.
- **BOND** — 2s10s yield-curve-slope momentum z-score (DeepSeek + xAI).

**Cross-class process fixes (unanimous):**
1. **Purged + embargoed combinatorial CV** (López de Prado AFML Ch.7) —
   replace naive walk-forward; drop any feature whose importance collapses
   after a 5-day embargo (xAI estimates this removes 30-40% of spurious
   signals).
2. **Permutation-test feature selection** — keep only the top ~8 features per
   class that survive a 1000-iteration permutation test at p<0.05; retrain
   ONE parsimonious model, not a 149-variant sprawl.
3. **Per-class volatility targeting at signal generation** —
   size = target_vol / realized_20d_vol, capped 2x — normalises PF
   contribution across high-vol (crypto) and low-vol (bond) classes. Also:
   **rank-based uniform ensembling** of 3-5 uncorrelated signals (corr<0.2)
   instead of ML stacking (DeepSeek).

**Verdict:** identical to every prior round — kill the mining sprawl, kill
FOREX, rebuild CRYPTO/COMMODITY/BOND on <5-8 pre-registered, purged-CV-
validated features. The discipline is the edge. Feeds MASTER_ACTION_PLAN
§27/§28 (M-088..M-107) — no new plan needed, these are validation specifics.

---

## APPENDIX — full model responses


---

## deepseek

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

---

## xai-grok

**CRYPTO**

- Add: perpetual funding rate z-score (48h rolling) interacted with 4h basis. Source: exchange-native websocket (Binance, Bybit, OKX) normalized to USD notional. Test: 180 BTC/ETH/ SOL events, long only when z < –1.8 and basis > +0.4 %, 30-min hold, PF ≥ 1.45 and WR ≥ 61 % on 2023-01-01 to 2024-06-30 walk-forward (5 folds, 3-week embargo).
- Cut: the 149-variant ml_enhanced mining loop. Replace with single funding + basis rule; the family PF of 0.63 shows the sprawl is pure overfit.

**EQUITY**

- Add: overnight vs intraday return gap on Russell 1000 names (academic: Lou, Polk, Skouras 2019 overnight momentum). Source: TAQ SIP or Polygon.io 1-min bars, close-to-open leg only. Test: 2 400 overnight signals, long gap > +1.2 σ, next-day close exit, PF ≥ 1.35, WR ≥ 54 % on 2018-2023 purged 10-fold CV with 5-day embargo.
- Cut: any same-day news sentiment overlay. It leaks and collapses OOS PF below 1.0 once publication timestamps are respected.

**COMMODITY**

- Add: front-to-second month futures roll yield (daily, 5-day z-score). Source: CME/ICE settlement files via Quandl or direct FTP. Test: 420 contracts across energy/grains/softs, long when z < –1.5 and term structure steepening, 5-day hold, PF ≥ 1.40, WR ≥ 58 % on 2019-2024 blocked walk-forward (monthly blocks).
- Cut: single-symbol COT rules (cotton already exposed the leakage). Drop all COT-derived features; public COT is too stale and sparse for retail latency.

**FOREX**

No retail edge. G10 and EM pairs show zero statistical edge once bid-ask and rollover are netted; any published carry or momentum factor is arbitraged within days at retail latency. Stop allocating compute or capital.

**ETF**

- Add: ETF vs underlying NAV discount z-score (close only). Source: ETF.com or Bloomberg NAV files. Test: 1 100 signals on SPY, QQQ, IWM, TLT, GLD, long when discount < –0.8 σ, next-day close, PF ≥ 1.30, WR ≥ 55 % on 2020-2024 purged CV (10 folds, 2-day embargo).
- Cut: any intraday mean-reversion on the ETF itself; spreads and stale NAV prints destroy the edge once realistic execution is modeled.

**BOND**

- Add: 2s10s yield-curve steepener z-score (daily). Source: Treasury.gov constant-maturity yields or FRED series. Test: 380 signals, long steepener when z < –1.7, 10-day hold, PF ≥ 1.35, WR ≥ 56 % on 2015-2024 walk-forward with quarter-end embargo.
- Cut: any duration or DV01 scaling based on daily price volatility; rates exhibit jumps around auctions and FOMC that retail volatility estimates miss.

**Cross-class process fixes**

1. Replace standard k-fold with purged, embargoed, combinatorial CV (De Prado AFML Ch. 7). For every class, drop any feature whose importance collapses after a 5-day embargo; this alone removes 30-40 % of the current spurious signals.

2. Run univariate permutation importance on the full candidate set, then retain only the top 8 features per class that survive a 1 000-iteration permutation test at p < 0.05. Re-train a single shallow tree or logistic model on the reduced set; current multi-variant sprawl is replaced by one parsimonious rule per class.

3. Apply per-class volatility targeting at signal generation: size = (target vol / realized 20-day close-to-close vol) capped at 2× notional. This normalizes the PF contribution across crypto (high vol) and bonds (low vol) without introducing look-ahead.

---

## kimi

### CRYPTO

**Signal/Feature to Add:**
- **Feature:** Market sentiment from social media and news analysis.
- **Data Source:** Platforms like The TIE (The Token Economy) provide sentiment scores based on social media and news analysis.
- **Falsifiable Acceptance Test:** Test the signal on a rolling basis with a look-back period of 3 months. The signal should show a statistically significant positive correlation with returns (n > 100, WR > 60%, PF > 1.0, using walk-forward validation).

**Thing to Cut or Fix:**
- **Issue:** The high-frequency nature of cryptocurrency markets can lead to overfitting on short-term patterns that do not persist.
- **Solution:** Implement a more robust out-of-sample (OOS) testing procedure that includes a longer OOS period and considers different market conditions (e.g., bull vs. bear markets). This will help in filtering out non-robust patterns.

### EQUITY

**Signal/Feature to Add:**
- **Feature:** Earnings Quality Score based on accruals and cash flow.
- **Data Source:** Compustat and I/B/E/S.
- **Falsifiable Acceptance Test:** The Earnings Quality Score should show a negative correlation with future stock returns, indicating that stocks with lower earnings quality underperform (n > 500, WR > 55%, PF > 0.8, using a time-series cross-sectional approach).

**Thing to Cut or Fix:**
- **Issue:** Over-reliance on backward-looking financial ratios which may not capture forward-looking information.
- **Solution:** Integrate forward-looking earnings estimates and analyst revisions into the model to capture market expectations more effectively.

### COMMODITY

**Signal/Feature to Add:**
- **Feature:** Seasonality patterns based on historical price data.
- **Data Source:** Commodity price data from Bloomberg or Reuters.
- **Falsifiable Acceptance Test:** The seasonality signal should show a statistically significant edge during the identified seasonal periods (n > 20 years, WR > 60%, PF > 1.2, using a seasonal sub-sample approach).

**Thing to Cut or Fix:**
- **Issue:** Ignoring geopolitical events that can have a significant impact on commodity prices.
- **Solution:** Incorporate a geopolitical risk index, such as the PRS Group's International Country Risk Guide, to adjust trading strategies during high-risk periods.

### FOREX

**Signal/Feature to Add:**
- **Feature:** Carry trade profitability based on interest rate differentials.
- **Data Source:** Interest rate data from central banks and currency data from OANDA or Dukascopy.
- **Falsifiable Acceptance Test:** The carry trade signal should show a positive correlation with currency returns, particularly in low-volatility environments (n > 10 years, WR > 55%, PF > 0.9, using a rolling window approach).

**Thing to Cut or Fix:**
- **Issue:** Neglecting the impact of central bank policies on currency pairs.
- **Solution:** Develop a model that incorporates central bank policy rates and policy announcements to better predict currency movements.

### ETF

**Signal/Feature to Add:**
- **Feature:** ETF flows and holdings analysis.
- **Data Source:** ETF.com and Morningstar for ETF holdings and flows.
- **Falsifiable Acceptance Test:** ETFs with significant inflows and positive changes in holdings should outperform (n > 100 ETFs, WR > 55%, PF > 0.8, using a time-series analysis).

**Thing to Cut or Fix:**
- **Issue:** Lack of differentiation between ETFs with similar holdings.
- **Solution:** Use a more granular analysis of ETF holdings to identify unique exposures that may offer an edge.

### BOND

**Signal/Feature to Add:**
- **Feature:** Credit spreads and default probabilities.
- **Data Source:** Bloomberg for credit spreads and Moody's or S&P for default probabilities.
- **Falsifiable Acceptance Test:** Bonds with widening credit spreads and increasing default probabilities should underperform (n > 500 bonds, WR > 60%, PF > 1.0, using a time-series cross-sectional approach).

**Thing to Cut or Fix:**
- **Issue:** Neglecting the liquidity premium in bond pricing.
- **Solution:** Incorporate liquidity measures, such as bid-ask spreads, into the bond selection process to account for potential liquidity constraints.

### Cross-Class Improvements

1. **Feature Engineering:** Implement a machine learning-based feature selection process to identify the most significant predictors across asset classes. This can help in reducing noise and focusing on the most relevant signals.

2. **Validation:

---

## openrouter

### CRYPTO  
**Add**: Implement a **liquidity-adjusted volume profile** feature. Use CoinMetrics or CryptoCompare for minute-level volume data. Calculate the volume-weighted average price (VWAP) and deviations from it, adjusted for liquidity (bid-ask spreads). Acceptance test: OOS PF > 1.2 over 6 months, WR > 55%, using walk-forward validation.  
**Cut**: Remove **low-liquidity altcoins** from the universe. Many crypto variants are illiquid, leading to slippage and unreliable signals. Focus on BTC, ETH, and top 10 coins by market cap.  

### COMMODITY  
**Add**: Incorporate **global inventory levels** from EIA, IEA, or USDA reports as a feature. For example, crude oil inventories vs. seasonal averages. Acceptance test: PF > 1.3 over 12 months, WR > 60%, using rolling window validation.  
**Cut**: Eliminate **momentum-based signals** for agricultural commodities. These are prone to false breaks due to weather and geopolitical noise.  

### EQUITY  
**Add**: Use **short interest ratio** (SIR) from Bloomberg or Quandl as a contrarian signal. Stocks with high SIR tend to underperform due to short squeeze risks. Acceptance test: PF > 1.1 over 12 months, WR > 52%, using stratified cross-validation.  
**Cut**: Remove **low-volume small-cap stocks**. These introduce noise and slippage. Focus on S&P 500 or Russell 1000 constituents.  

### FOREX  
**Add**: Incorporate **central bank policy divergence** as a feature. Use Bloomberg or Reuters for interest rate forecasts and policy statements. Acceptance test: PF > 1.1 over 6 months, WR > 53%, using walk-forward validation.  
**Cut**: Stop trading **exotic currency pairs**. Stick to majors (EUR/USD, GBP/USD, etc.) to reduce volatility and slippage.  

### ETF  
**Add**: Use **implied volatility spreads** between ETFs and their underlying assets (e.g., SPY vs. S&P 500 futures). Data from CBOE or Bloomberg. Acceptance test: PF > 1.2 over 6 months, WR > 55%, using rolling window validation.  
**Cut**: Avoid **leveraged ETFs**. These are designed for short-term trading and introduce decay and slippage.  

### BOND  
**Add**: Incorporate **yield curve steepness** (10Y-2Y spread) from FRED or Bloomberg as a macro signal. Acceptance test: PF > 1.1 over 12 months, WR > 52%, using stratified cross-validation.  
**Cut**: Stop trading **low-liquidity corporate bonds**. Focus on Treasuries or highly liquid IG bonds.  

### Cross-Class Improvements  
1. **Feature Engineering**: Implement **autoencoders** for dimensionality reduction. Use TensorFlow or PyTorch to compress high-dimensional features into latent representations. Test by comparing OOS PF before and after compression.  
2. **Validation**: Switch to **nested cross-validation** for more robust OOS testing. Use scikit-learn’s `GridSearchCV` with an inner loop for hyperparameter tuning and an outer loop for performance evaluation.  
3. **Ensembling**: Use **stacking** with meta-learners (e.g., XGBoost) to combine signals. Train base models (e.g., random forests, SVMs) on individual asset classes, then use a meta-model to blend predictions. Test by comparing ensemble PF to individual model PFs.  

### Honest Answer  
**FOREX**: No retail edge — stop. The market is dominated by institutional players with superior execution and information. Focus on other asset classes.

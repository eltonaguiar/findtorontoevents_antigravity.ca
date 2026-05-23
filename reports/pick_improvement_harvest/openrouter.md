# openrouter — pick-improvement harvest

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

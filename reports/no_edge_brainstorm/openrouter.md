# openrouter — no-edge brainstorm

# ROOT CAUSE

The system’s lack of edge stems from three core structural flaws:

1. **Overfitting via Strategy Sprawl**: The system relies on post-hoc mining of strategies (`ml_enhanced` sprawl) without rigorous out-of-sample validation. This leads to curve-fitting, where strategies appear profitable in-sample but fail in live trading. The crypto "edge" is a prime example — it’s entirely a mining artifact.

2. **Misaligned Risk Management**: The kill-threshold ratchet in EQUITY destroys legitimate edges (e.g., PEAD, value) by prematurely discarding strategies based on small-n in-sample windows. This prioritizes short-term noise over long-term statistical validity.

3. **Data Leakage and Misclassification**: The system suffers from unresolved data integrity issues (e.g., COT look-ahead leakage in COMMODITY, mis-tagged asset classes). These errors inflate apparent performance and mask true edge discovery.

---

# PER ASSET CLASS

### CRYPTO  
**Edge**: Liquidity-driven mean reversion in low-cap altcoins.  
**Data**: Minute-level order book data + on-chain liquidity metrics (e.g., exchange reserves).  
**Validation**: Test on altcoins with <$500M market cap, excluding BTC/ETH. Acceptance: PF >= 1.5 in walk-forward over 12 months, with Sharpe >= 1.0 after deflation.

### EQUITY  
**Edge**: Post-earnings announcement drift (PEAD) with sentiment overlay.  
**Data**: Earnings surprises + sentiment scores from news/transcripts.  
**Validation**: Test on Russell 3000 stocks, excluding microcaps. Acceptance: PF >= 1.8 in CPCV (combinatorial purged cross-validation) over 5 years.

### COMMODITY  
**Edge**: Seasonal patterns in agricultural commodities (e.g., corn, soybeans).  
**Data**: Historical futures prices + weather/climate data.  
**Validation**: Test on ZC=F (corn futures). Acceptance: PF >= 1.6 in walk-forward over 10 years, with no COT look-ahead leakage.

### FOREX  
**Do Not Trade**: Retail-accessible forex lacks a defensible edge due to institutional dominance and high-frequency arbitrage. Stop trading forex.

### ETF  
**Edge**: Momentum-driven sector rotation.  
**Data**: ETF price data + macroeconomic indicators (e.g., yield curve, PMI).  
**Validation**: Test on sector ETFs (e.g., XLF, XLE). Acceptance: PF >= 1.7 in walk-forward over 15 years, with Sharpe >= 1.2 after deflation.

### BOND  
**Edge**: Yield curve steepening/flattening trades.  
**Data**: Treasury futures + macroeconomic data (e.g., inflation expectations).  
**Validation**: Test on ZB=F (30-year Treasury futures). Acceptance: PF >= 1.5 in CPCV over 20 years.

---

# METHODOLOGY

To avoid mining artifacts, restructure edge discovery as follows:

1. **Combinatorial Purged Cross-Validation (CPCV)**: Use CPCV instead of rolling walk-forward to avoid look-ahead bias. CPCV combines multiple training/testing splits to ensure robustness.

2. **Deflated Sharpe Ratio**: Adjust for multiple testing by deflating Sharpe ratios using the method of Bailey and López de Prado. Set a minimum deflated Sharpe of 0.5 for any strategy.

3. **Minimum-N Thresholds**: Require a minimum of 100 trades per strategy before evaluation. Discard strategies with fewer trades to avoid small-n noise.

4. **White’s Reality Check**: Apply White’s Reality Check to test whether the best strategy in a family is statistically significant after adjusting for multiple comparisons.

5. **Pre-Commitment**: Pre-commit to a hypothesis (e.g., "PEAD works with sentiment") before testing. Avoid post-hoc mining entirely.

---

# THE 3 HIGHEST-EV MOVES

1. **PEAD with Sentiment Overlay (EQUITY)**  
   **Acceptance Test**: PF >= 1.8 in CPCV over 5 years, with Sharpe >= 1.5 after deflation.  
   **Rationale**: PEAD is academically validated, and sentiment adds a modern twist.

2. **Seasonal Patterns in Agricultural Commodities (COMMODITY)**  
   **Acceptance Test**: PF >= 1.6 in walk-forward over 10 years, with no COT leakage.  
   **Rationale**: Seasonality is a persistent, exploitable anomaly in commodities.

3. **Liquidity-Driven Mean Reversion in Low-Cap Altcoins (CRYPTO)**  
   **Acceptance Test**: PF >= 1.5 in walk-forward over 12 months, with Sharpe >= 1.0 after deflation.  
   **Rationale**: Crypto’s inefficiency makes it fertile ground for liquidity-based edges.

---

# WHAT TO STOP DOING

1. **Stop Mining Strategies Post-Hoc**: The `ml_enhanced` sprawl is a textbook example of overfitting. Pre-commit to hypotheses and validate them rigorously.

2. **Stop Using Small-N Kill Thresholds**: The kill-threshold ratchet destroys legitimate edges. Replace it with CPCV and minimum-n thresholds.

3. **Stop Trading FOREX**: Retail-accessible forex lacks a defensible edge. Redirect resources to asset classes with higher potential (e.g., EQUITY, CRYPTO).

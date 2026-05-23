# Stock Algorithm Pros/Cons, Effectiveness Research & Improvements

This document provides a **pros/cons analysis**, **effectiveness research**, and **improvement recommendations** for each stock algorithm used on the Find Stocks page. It is intended for internal review and for improving strategy design.

---

## 1. CAN SLIM Growth

### Pros

| Benefit | Detail |
|--------|--------|
| **Backtested methodology** | William O’Neil’s research on winning stocks (1880–2009) underpins the rules; academic backtests report market-adjusted abnormal monthly returns (e.g. ~1.81% stock, ~3.18% arbitrage) and outperformance vs. S&P 500 / DJIA over long windows. |
| **Clear rules** | RS Rating, Stage-2, price vs 52W high, RSI, volume are implementable and auditable. |
| **Long-term focus** | 3–12 month horizon reduces noise and suits growth investing. |
| **Proven in studies** | Simplified CAN SLIM systems showed 232% total return (2001–2012) vs S&P 500, ~0.82% monthly alpha; modified versions beat DJIA over 5/10/16 years with statistically significant results. |
| **Low data dependency** | Needs price/volume and 52W high; no heavy fundamental feeds. |

### Cons

| Drawback | Detail |
|----------|--------|
| **Crowding / post-publication decay** | Researchers note characteristic-based strategies can lose edge as they become widely known and traded. |
| **Revenue/earnings not in our build** | Full CAN SLIM uses C, A, N, S, L, I, M (earnings, institutional, market direction). Our implementation is **technical-only** (RS, stage, price vs 52W, RSI, volume)—no earnings or institutional data. |
| **Stage-2 is heuristic** | Our Stage-2 logic is simplified; full Minervini/O’Neil base-and-breakout rules are stricter and more nuanced. |
| **Regime-agnostic** | No explicit bull/bear or volatility regime; same rules in all environments. |
| **Requires long history** | We require ~200 bars; names with shorter history are skipped. |

### Effectiveness research (summary)

- **Olson et al. (1998):** CAN SLIM on S&P 500 (1984–1992): abnormal monthly returns 1.81% (stocks), 3.18% (arbitrage portfolio).
- **Later backtests (e.g. 2001–2012):** Simplified CAN SLIM ~232% total return, ~0.82%/month vs S&P 500; modified versions vs DJIA over 5/10/16 years, risk-adjusted outperformance.
- **Out-of-sample (e.g. 1999–2017):** Variants without stop-loss still beat DJIA; some degradation when tested two years OOS and on other benchmarks (S&P 1500, Nasdaq).
- **Conclusion:** CAN SLIM has **demonstrated excess returns** in academic backtests; our technical-only implementation is a **subset** of the full system, so effectiveness may be lower than full CAN SLIM.

### Improvement ideas

1. **Add fundamentals where possible**  
   - Use C (current quarterly earnings growth) and A (annual earnings growth) from a data provider (e.g. SEC, Yahoo, Polygon) so the screener aligns with O’Neil’s full framework.

2. **Institutional / supply–demand proxy**  
   - If data exists: institutional ownership changes, float, or short interest as a proxy for “I” and “S” to improve alignment with CAN SLIM.

3. **Market-direction filter (M)**  
   - Only allow new CAN SLIM buys when a market index (e.g. S&P 500 or QQQ) is above a long moving average or in an uptrend. Reduces long exposure in bear regimes.

4. **Stricter Stage-2 definition**  
   - Refine `checkStage2Uptrend` with volume-on-breakout, pullback depth, and MA alignment so it better matches Minervini’s criteria.

5. **Regime-adjusted weights**  
   - In high-vol regimes, require higher RS or a tighter price-vs-52W threshold before assigning STRONG BUY.

---

## 2. Technical Momentum

### Pros

| Benefit | Detail |
|--------|--------|
| **Multiple timeframes** | 24h, 3d, 7d allow different holding periods and reduce reliance on a single horizon. |
| **Volume + price** | Volume surge and breakout/RSI/Bollinger logic are consistent with “volume confirms price” and help filter quiet, low-conviction moves. |
| **Short-horizon focus** | Fits traders and catalysts; RSI/volume/breakout are standard inputs in practitioner and academic work. |
| **Interpretable** | Each component (RSI, volume surge, breakout, squeeze) is explainable and tunable. |

### Cons

| Drawback | Detail |
|----------|--------|
| **Mixed evidence on RSI alone** | Studies find RSI levels alone inadequate for strong trends; combining RSI with momentum/regime improves results. Our RSI use is simple (ranges by timeframe). |
| **Volume–momentum interaction** | Academic work shows **past volume** predicts magnitude and persistence of momentum; high-volume winners tend to reverse faster. We use current volume surge but don’t model “volume conditional on past returns.” |
| **Many false breakouts** | Short-term momentum is noisy; breakouts without volume/volatility filters produce many whipsaws. |
| **No volatility targeting** | We don’t scale size or filter by ATR/volatility; same score in calm and chaotic markets. |
| **No cross-sectional ranking** | We score each name in isolation. Research suggests **cross-sectional momentum** (relative rank across universe) often adds value. |

### Effectiveness research (summary)

- **RSI:** RSI (14, 30/70) profitable in DJIA; RSI (21, 50) in other developed markets. Combining **RSI bull ranges + RSI momentum** improves identification of strong advances vs RSI levels alone.
- **Volume and momentum:** Past volume helps link momentum and value; volume predicts momentum **magnitude and persistence** over intermediate and long horizons; high-volume winners reverse faster than low-volume losers.
- **Momentum signal design:** Linear trend-fitting and other volatility-aware signals can improve out-of-sample performance and cut turnover. Volume-based confirmation is a common improvement.

### Improvement ideas

1. **Volatility filter (e.g. ATR)**  
   - Add an ATR or realized-vol filter: only take breakouts when volatility is in a “normal” band, or use a dual-EMA + ATR framework to avoid false breakouts in quiet or extreme vol.

2. **Volume threshold from distribution**  
   - Define “volume surge” as **multiples of standard deviation above average** (e.g. 2σ) instead of fixed multiples, so thresholds adapt to the name and regime.

3. **RSI + momentum combo**  
   - Add a momentum component (e.g. short-term return or RSI rate of change) alongside RSI levels so signals match research that favors “RSI + momentum” over levels alone.

4. **Cross-sectional rank**  
   - Score the universe, then use **ranks** (e.g. top quintile) or standardized score for sizing/filtering instead of raw levels, to align with cross-sectional momentum literature.

5. **Time-series + cross-sectional**  
   - Use both (a) own-name momentum (e.g. MA crossover or trend) and (b) rank vs peers; research suggests combining both can add value.

---

## 3. ML Ensemble

### Pros

| Benefit | Detail |
|--------|--------|
| **Flexible inputs** | Can use many technicals, volumes, and (if available) fundamentals/sentiment. |
| **Multiple models** | Random Forest, Gradient Boosting, XGBoost, etc. reduce reliance on one specification. |
| **Learned patterns** | Can capture nonlinearities and interactions that rule-based systems miss. |
| **Evaluation possible** | MSE, R², MAE, directional accuracy can be tracked; backtests and walk-forward checks are standard. |

### Cons

| Drawback | Detail |
|----------|--------|
| **Data and overfitting** | Equity returns are noisy; small samples and many features lead to overfitting. Need strict train/validation/test and regularization. |
| **Scale sensitivity** | XGBoost in particular can be sensitive to input scale; normalization/standardization and tuning matter. |
| **Mixed comparative results** | Some studies report Random Forest best (accuracy/MSE); others report XGBoost best for short-term forecasting. No single “winner” across all setups. |
| **Non-stationarity** | Relationships change over time; models need retraining or online updates. |
| **Not in our daily pipeline** | Our repo’s daily generator does **not** run an ML ensemble; ML Ensemble appears in the UI when data is from other sources (e.g. STOCKSUNIFY). |

### Effectiveness research (summary)

- **Tree-based vs others:** Ensemble methods (RF, XGBoost) typically beat logistic regression and K-NN in stock prediction tasks; no algorithm dominates all studies.
- **XGBoost:** Can achieve highest accuracy in short-term forecasting in some setups but with longer compute; sensitive to variable scale.
- **Random Forest:** Often tops in long-horizon direction and in some head-to-head accuracy/MSE comparisons; can be more robust to scaling.
- **Limitation:** Perfect or very high accuracy is rare; financial forecasting remains difficult.

### Improvement ideas

1. **Feature discipline**  
   - Limit to a small set of robust features (e.g. momentum, volatility, volume, trend) and use regularization / early stopping to avoid overfitting.

2. **Walk-forward and regime splits**  
   - Train on earlier data, test on later; optionally train separate models for high-vol vs low-vol regimes, or use regime as a feature.

3. **Scale and robustness**  
   - Standardize/normalize inputs; consider models or preprocessing that are less sensitive to outliers (e.g. rank-based or robust scaling).

4. **Ensemble of ensembles**  
   - Combine RF, XGBoost, and (if applicable) a simple linear/ridge model with a meta-learner or simple average to diversify model risk.

5. **Target definition**  
   - Test both **next-day return** and **forward N-day return** or **direction**; align horizon with actual use (e.g. daily rebalance vs weekly).

---

## 4. Composite Rating

### Pros

| Benefit | Detail |
|--------|--------|
| **Multi-factor** | Combines technicals, volume, fundamentals (PE, cap), and regime, which matches the idea that no single factor is always best. |
| **Regime adjustment** | We use a simple vol-based regime (normal / low-vol / high-vol) to adjust scores; this is consistent with research that regime-aware strategies can outperform static ones. |
| **Broad use** | Good for watchlists, ranking, and “overall attractiveness” over a 1–3 month swing horizon. |
| **Score-based construction** | Composite scores are a standard way to combine signals; at higher tracking error, signal combination can improve risk-adjusted returns. |

### Cons

| Drawback | Detail |
|----------|--------|
| **Fixed weights** | Our 40/20/20/20 split (technical/volume/fundamental/regime) is heuristic. Research shows **optimal weights are context-dependent** and can be estimated (e.g. mixture design, optimization). |
| **Simple regime** | Regime is based on a short rolling vol; no Markov/multi-state or trend component. Regime-switching and HMM-based methods can do better. |
| **Factor synergy** | Multi-factor work finds **synergies** between some factors (e.g. profitability + value); we don’t model interactions, only additive components. |
| **Limited fundamentals** | Only PE and market cap; no earnings growth, quality, or leverage. |

### Effectiveness research (summary)

- **Score-based strategies:** Tend to outperform benchmarks in several developed markets and across score types (e.g. F-score, G-score, Z-score), with some downside protection.
- **Weighting:** Mixture-design and optimization approaches can find better factor weights and capture interactions; naive equal weighting is often suboptimal.
- **Regime:** Regime-switching and HMM-based factor strategies outperform static allocations; incorporating regime is supported by evidence.
- **Factor combination:** At higher tracking error, combining signals into composite scores can improve diversification and handling of negative signals; at lower tracking error, portfolio combination may be more efficient.

### Improvement ideas

1. **Regime model upgrade**  
   - Use a 2–3 state Markov or HMM on volatility (and optionally trend) to label regimes, then use **regime-dependent weights** or thresholds for technical/fundamental/volume.

2. **Estimate factor weights**  
   - Use rolling or expanding windows to fit factor weights (e.g. via constrained optimization or mixture design) so technical/volume/fundamental/regime weights adapt to recent performance.

3. **Add factor interactions**  
   - Include interaction terms (e.g. “quality × value” or “momentum × volatility”) in the composite, guided by synergy results from multi-factor research.

4. **Richer fundamentals**  
   - Add earnings growth, ROE/ROA, or leverage if data is available, and give “quality” and “value” explicit sub-scores within the 20% fundamental bucket.

5. **Alternative regime inputs**  
   - Consider trend (e.g. index above/below MA), breadth, or correlation as regime inputs in addition to volatility.

---

## 5. Statistical Arbitrage

### Pros

| Benefit | Detail |
|--------|--------|
| **Market-neutral structure** | Long one name, short another reduces broad market direction risk. |
| **Theoretically grounded** | Pairs/stat-arb is built on cointegration or mean-reverting spread/ratio, which has a clear economic story. |
| **Historically strong Sharpe** | Academic work reports Sharpe ratios around 1.1–1.5 for PCA- and ETF-based stat-arb over 1997–2007; volume-augmented versions improved further. |
| **Diversifier** | Low correlation to directional equity strategies, so it can improve portfolio risk/return when combined with momentum or value. |

### Cons

| Drawback | Detail |
|----------|--------|
| **Performance decay** | Effectiveness decreased in the 2000s and around the 2007 liquidity crisis; simple mean-reversion has faced crowding and regime changes. |
| **Execution and costs** | Requires shorting, often in less liquid names; transaction and financing costs can erase edge. |
| **Correlation breaks** | Cointegration and correlation can break; pairs need monitoring and occasional re-selection. |
| **Not in our daily pipeline** | Our repo does **not** run stat-arb; it appears in the UI when data comes from other systems. |

### Effectiveness research (summary)

- **Pairs / cointegration:** Early pairs work (e.g. 1962–1997) showed meaningful excess returns for top pairs; some attributed to microstructure.
- **PCA / ETF stat-arb (1997–2007):** Annual Sharpe ~1.44 (PCA), ~1.1 (ETF); post-2002 degradation; volume info raised ETF Sharpe to ~1.51 in 2003–2007.
- **Recent ML approaches:** Some deep-learning stat-arb papers report high out-of-sample Sharpe, indicating that **signal design** (e.g. ML for spread or pair selection) can matter as much as the basic mean-reversion idea.

### Improvement ideas

1. **Volume and liquidity**  
   - Use volume and spread/liquidity in pair selection and position sizing; research suggests volume-augmented stat-arb can improve Sharpe.

2. **Regime and stress filters**  
   - Reduce or pause stat-arb exposure in high-vol or crisis regimes (e.g. VIX or correlation spikes) where mean reversion often breaks.

3. **ML for spread / pair selection**  
   - Use ML to select pairs or to model the spread (e.g. when to enter/exit) while keeping the overall market-neutral, mean-reversion structure.

4. **Diversification across clusters**  
   - Build many uncorrelated pairs or clusters (sector, factor) and size by inverse volatility or Sharpe to diversify model risk.

5. **Transaction cost and capacity**  
   - Explicitly model trading costs and impact; cap AUM or turnover per pair so implementable Sharpe is realistic.

---

## 6. Potentially Better or Complementary Algorithms

These are **candidate additions or replacements** suggested by empirical and practitioner research, not yet implemented in our pipeline.

### 6.1 Residual Momentum

- **Idea:** Rank stocks by **residual returns** (after removing factor exposures, e.g. market, size, value) instead of raw returns.
- **Evidence:** Residual momentum often has **about twice** the risk-adjusted performance of total-return momentum, with less concentration in extreme names and more stable behavior over time.
- **Implementation:** Run a factor model (e.g. Fama–French or PCA) on the universe, get residuals, then rank on 3–12 month residual momentum. Use ranks or Z-scores for signals.
- **Use case:** Could replace or sit alongside **Technical Momentum** for medium-term (e.g. 3–6 month) screens.

### 6.2 Factor Momentum (Momentum of Factors)

- **Idea:** Apply momentum to **factors** (value, quality, momentum, etc.): overweight factors that have done well recently, underweight those that have done poorly.
- **Evidence:** “Factor momentum” has delivered alpha above single-name momentum in research; can be combined with value or other factors.
- **Implementation:** Compute recent returns of long–short factor portfolios; allocate across factors by their momentum or by a composite that includes momentum of factors.
- **Use case:** Top-down allocation across themes; could drive **weights** for our Composite Rating factor buckets.

### 6.3 Quality + Value / Profitability + Value

- **Idea:** Combine **profitability/quality** (e.g. ROE, ROC, stable earnings) with **value** (e.g. P/B, P/S). Research finds **synergies** between these groups.
- **Implementation:** Define quality and value scores, then combine (e.g. average, or optimized weights) and rank stocks. Add momentum as a third leg if desired.
- **Use case:** New “Quality–Value” or “Quality–Value–Momentum” screener; or fold into **Composite Rating** as a formal quality+value sub-block.

### 6.4 Regime-Switching Allocations

- **Idea:** Use **regime detection** (e.g. HMM or Markov on volatility/trend) to switch between strategies or weights: e.g. more momentum in trending regimes, more mean reversion or defensive in stress regimes.
- **Evidence:** Regime-aware portfolios often beat static allocations; volatility and trend are standard regime inputs.
- **Implementation:** Estimate 2–3 states (e.g. calm/trending/stress), assign each date to a state, then use state-dependent weights for CAN SLIM, Technical Momentum, Composite, or cash.
- **Use case:** Meta-layer above our existing algorithms: same signals, but **when** to use them more or less.

### 6.5 Dual Momentum + Volatility Filter

- **Idea:** Use **two** momentum signals (e.g. short-term EMA vs long-term EMA, or absolute vs relative momentum) and allow entries only when volatility is in a chosen band (e.g. ATR filter).
- **Evidence:** Dual momentum with volatility filtering is used in practice; volume and volatility filters are standard refinements to reduce false breakouts.
- **Use case:** Upgrade **Technical Momentum** with dual momentum and an ATR (or similar) filter.

### 6.6 Mixture Design / Optimized Factor Weights

- **Idea:** Periodically **optimize** the weights of technical, volume, fundamental, and regime in **Composite Rating** (e.g. by maximizing Sharpe or IR over a rolling window, subject to constraints).
- **Evidence:** Mixture-design and optimization studies show that adaptive weights can outperform fixed schemes.
- **Use case:** Replace fixed 40/20/20/20 in Composite with **estimated weights** updated monthly or quarterly.

---

## 7. Summary Table

| Algorithm | Pros (short) | Cons (short) | Effectiveness | Top improvement |
|-----------|--------------|--------------|----------------|------------------|
| **CAN SLIM Growth** | Backtested, clear rules, long horizon | Technical-only, no earnings/I/M, crowding risk | Strong in academic backtests | Add earnings + market-direction filter |
| **Technical Momentum** | Multi-timeframe, volume+price, interpretable | No volatility filter, no cross-section, noisy | Mixed; RSI+momentum and volume help | ATR filter + cross-sectional rank |
| **ML Ensemble** | Flexible, multi-model, testable | Overfitting, scale sensitivity, not in our pipeline | Mixed; RF/XGBoost context-dependent | Feature discipline + walk-forward + scaling |
| **Composite Rating** | Multi-factor, regime-aware, broad use | Fixed weights, simple regime, no interactions | Good for score-based strategies | Regime upgrade + weight estimation + interactions |
| **Statistical Arbitrage** | Market-neutral, theory, diversification | Decay post-2002, costs, not in our pipeline | Strong historically; ML can help | Volume/liquidity + regime filter + ML signals |

---

## 8. References and Further Reading

- **CAN SLIM:** Olson et al. (1998); AAII CAN SLIM screens; backtests vs S&P 500 / DJIA (2001–2012, 1999–2017).
- **Momentum / RSI / volume:** Price Momentum and Trading Volume (e.g. LSV/Journal of Finance); RSI + momentum (SSRN); momentum signal design (CME/improving time-series momentum).
- **Composite / multi-factor:** Mixture design for factor weights (Springer Open, EconStor); score-based portfolios (Nature Scientific Reports); factor synergy (Springer); multi-factor implementation (MSCI, Vanguard, AQR).
- **ML for stocks:** XGBoost vs RF (BC Publication, PLOS One, arXiv); classifier comparison (ScienceDirect).
- **Statistical arbitrage:** Pairs trading (NBER); PCA/ETF stat-arb (Berkeley, Avellaneda–Lee); deep learning stat-arb (CDAR Berkeley).
- **Residual momentum:** SSRN residual momentum; “Residual Momentum and Reversal Revisited”.
- **Regime:** Robust Rolling Regime Detection (SSRN); regime-switching factor investing (MDPI); “How do Regimes Affect Asset Allocation?” (NBER).

---

*Last updated: January 2026. This document is for research and strategy development; it does not constitute investment advice.*

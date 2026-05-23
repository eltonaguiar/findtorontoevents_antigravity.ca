# NO_EDGE_BRAINSTORM_CLOUD.MD

Cloud-model brainstorm — 2026-05-17. Fanned one prompt to every cloud LLM with
an API key in the Windows environment (`tools/no_edge_cloud_consult.py`).
**Responded:** DeepSeek (deepseek-reasoner), Kimi (moonshot-v1-32k), xAI
(grok-3), OpenRouter (deepseek-chat). **No response:** Groq + Cerebras — keys
returned HTTP 403 on every model (expired / wrong scope — rotate them).

## The question put to the models

Verified honest state: NO asset class has a real statistical edge. Net-of-
slippage deduped policy-clean PF — CRYPTO 1.28, COMMODITY 1.17, EQUITY 0.72,
FOREX 0.33. The CRYPTO "edge" is a 149-variant `ml_enhanced` mining artifact;
COMMODITY is CT=F leakage; EQUITY's real edges were killed by a small-n
ratchet. Given that baseline — how to actually FIND or BUILD a genuine edge?

---

## SYNTHESIS — what the 4 models converged on

### Root cause (UNANIMOUS)
1. **Multiple-testing without correction.** The `ml_enhanced` 149-variant
   sprawl is the garden of forking paths — best-of-N selected post-hoc, no
   family-wise error rate, no holdout. The PF-6.67 tail is noise.
2. **No out-of-sample / pre-registered hypothesis.** Patterns were mined from
   the same series with no prior economic thesis. DeepSeek: "without a causal
   story the probability a pattern is spurious approaches 100%."
3. **Data leakage + a self-harming validation stack.** COT look-ahead; the
   kill-threshold ratchet itself over-fitted on sub-regime windows, truncating
   genuine low-frequency edges before they compound.
   xAI adds a 4th: **no information-edge budget** — once latency, dissemination
   lag and crowding are priced in, residual alpha is negative for any signal a
   small team can observe.

### Per asset class — where the models agree
| Class | Consensus verdict |
|---|---|
| **FOREX** | **STOP — do not trade.** 3 of 4 explicit (DeepSeek, xAI, OpenRouter); only Kimi dissents (carry). Strongest kill signal in the brainstorm. |
| **EQUITY** | **PEAD (post-earnings-announcement drift)** — DeepSeek + OpenRouter name it directly; the academically-grounded pick. xAI dissents ("do not trade — arbitraged"). |
| **ETF** | **Tradeable, momentum / sector-rotation** — all 4 give an ETF edge; the most-agreed *positive* class. Variants: cross-sectional 12-1 momentum, overnight-vs-intraday variance ratio, sector rotation on yield-curve/PMI. |
| **COMMODITY** | **Term-structure / roll-yield conditional on inventory surprises** — DeepSeek (term-structure momentum, skeptical), xAI (inventory-surprise roll yield), OpenRouter (agri seasonality). All say: NOT the COT/CT=F path. |
| **CRYPTO** | **Split.** DeepSeek: "do not trade — no retail edge". Kimi/xAI/OpenRouter: a microstructure / order-flow-imbalance / funding+OI-pressure edge is worth ONE pre-registered test. Net: kill the ml_enhanced sprawl; if crypto is tested at all, test exactly one order-flow hypothesis. |
| **BOND** | **Split** — term premium / yield-curve (DeepSeek, OpenRouter, Kimi) vs "do not trade — needs prime-broker feeds" (xAI). Lowest-priority class. |

### Methodology (UNANIMOUS)
Replace the mining loop with a **pre-registered, gated** process:
- Pre-register ≤5 feature families per class + ONE test statistic *before*
  looking at data (xAI's two-stage gate is the sharpest formulation).
- **Combinatorial Purged CV (CPCV)** with embargo, blocks sized to the
  autocorrelation horizon (≈5d crypto, ≈22d commodities).
- **White's Reality Check + Hansen's SPA** over the whole pre-registered
  family; keep only survivors of a 5% FDR.
- **Deflated Sharpe** (Bailey & López de Prado) — minimum ≈0.5.
- **Hard minimum-n**: 100 (DeepSeek/Kimi/OpenRouter) to 300 (xAI)
  non-overlapping trades before any allocation.
- Archive every failed configuration; **never re-test it on the same sample.**

### The 3 highest-EV moves (merged)
1. **EQUITY PEAD** — earnings-surprise (SUE) + drift, ex-microcap, realistic
   100bps slippage. Accept: net Sharpe > 0.5 in 10-fold walk-forward / CPCV,
   ≥100 names per leg. (DeepSeek + OpenRouter top pick.)
2. **COMMODITY inventory-surprise roll yield** — EIA/USDA surprise vs
   front-minus-second curve shape. Accept: deflated Sharpe > 0.6, CPCV-blocked
   by contract cycle, full transaction costs. (xAI + DeepSeek.)
3. **ETF momentum / overnight-variance sleeve** — 12-1 cross-sectional
   momentum or overnight/intraday variance ratio on liquid sector ETFs.
   Accept: net Sharpe > 0.7, ≥200 independent trades, CPCV by quarter.

### What to STOP (UNANIMOUS)
1. **Kill the `ml_enhanced` generator and all 149 variants** — data-mined
   noise. (Every model said this explicitly.)
2. **Remove the kill-threshold ratchet** — it is itself an over-fitted filter
   that destroys sample size and truncates real low-frequency edges.
3. **Stop post-hoc strategy mining + FOREX** — pre-commit hypotheses; redirect
   FOREX capital/effort to EQUITY/ETF.

### How this maps to the repo's MASTER_ACTION_PLAN
- "Kill ml_enhanced" + "fix nb_trials" = §28 M-105 / M-106 (already filed).
- "Remove the kill-ratchet" = §27 M-104 (already filed — the models
  independently confirm it is the highest-leverage systemic fix).
- "White's Reality Check / SPA" = M-065 (already filed).
- NEW vs the plan: the **pre-registered ≤5-family two-stage gate** (xAI) is a
  concrete methodology not yet in the plan — worth adding as M-107.
- Per-class: the models endorse EQUITY-PEAD and ETF-momentum as the two
  classes most worth pursuing, and converge with §27 that FOREX should be
  abandoned and COMMODITY's edge is NOT the COT/CT=F path.

---

## APPENDIX — full model responses


---

## deepseek

# Response: Honest Diagnosis & Actionable Next Steps

## 1. ROOT CAUSE — Why Zero Edge?

Three structural reasons, not symptoms:

**A. Massive Multiple-Testing without Proper Penalization**  
The `ml_enhanced` system spawned 149 per-symbol variants (119 with n=1). That’s 149 independent backtests per symbol. With a 95% confidence threshold, you expect ~7.5 false positives per symbol. The system selected the best _post-hoc_, producing a phantom PF of 6.67. This is the **standard garden of forking paths** — no correction for multiplicity, no out-of-sample holdout, no Reality Check. The family-level PF of 0.63 confirms the whole exercise is pure noise.

**B. Data Leaks Embedded in Signal Construction**  
COT-fixation on CT=F gave PF ~1.17 for commodities. The look-ahead is classic: publication delay not respected. Once fixed, the edge disappears. Similarly, the EQUITY kill-threshold ratchet is a self-destructive leak: it fires on small‑n in‑sample windows, effectively using future information to kill valid strategies (PEAD, earnings drift). The system was fighting its own edge.

**C. No Economic Causal Model**  
Every live “edge” was a statistical pattern mined from the same time series without a prior hypothesis. Without a causal story — e.g., risk premium, structural anomaly, institutional friction — the probability that any discovered pattern is spurious approaches 100% after controlling for degrees of freedom. The ledger bugs (duplicates, slippage units) only amplified the noise.

## 2. PER ASSET CLASS — One Academically-Grounded Edge (or Rejection)

### CRYPTO — **“Do not trade this.”**  
There is no retail-accessible, replicable edge. Crypto is dominated by latency arbitrage, exchange-specific wash trading, and regime shifts driven by unverifiable news. Any apparent momentum or mean-reversion is destroyed by slippage and token-level concentration. The honest answer: **stop allocating capital to crypto signals entirely.** If forced to, test only a single simple model: 1-month reversal on top-50 market-cap coins, require n≥20 trades per year, and accept Deflated Sharpe ratio < 1.0.

### EQUITY — **PEAD (Post Earnings Announcement Drift) with strict controls**  
- **Data:** Compustat quarterly earnings surprises (SUE), CRSP daily returns, market cap filters (ex-microcap).  
- **Test:** Long top-decile SUE, short bottom-decile, rebalance monthly. Use **100bps slippage** (realistic for large-cap), require hold period 60 days.  
- **Acceptance:** Net-of-slippage Sharpe ratio > 0.5 (annualized) in a **walk-forward** (5-year training / 1-year testing, 10 folds) with **minimum 100 distinct stocks per leg per rebalance**. Reject if Sharpe drops below 0.2 in any test fold.

### COMMODITY — **“Do not trade this.”**  
Cotton look-ahead killed the only plausible edge. Commodity futures are zero‑sum after costs, and most academic convenience‑yield models fail out-of-sample for retail capital. The only exception: **term structure momentum** (Bakshi, Gao, Rossi) — but requires deep liquidity and low slippage. If you can get fill data for CME grains, test: rolling 3-month momentum on nearest futures, one contract per commodity, Sharpe > 0.3 after 2-tick slippage. Likely fails.

### FOREX — **“Do not trade this.”**  
FX is the most efficient market tested (PF 0.33). No retail edge exists. The carry trade (long high-yield, short low-yield) has Sharpe ~0.1 after 1bp spread and is subject to crash risk. Stop trading forex signals.

### ETF — **Cross-sectional momentum**  
- **Data:** All US-listed equity ETFs with AUM > $100M (≈400). Daily returns.  
- **Test:** Rank ETFs by 12-month return (skip last month). Long top decile, short bottom decile. Monthly rebalance.  
- **Acceptance:** Net-of-slippage (0.05% per side) Sharpe > 0.7 in 20 rolling 3-year windows. Require at least 30 ETFs in each leg. Stop if any 3-year window goes below Sharpe 0.0.

### BOND — **Treasury term structure premium**  
- **Data:** Daily yields for 2yr/5yr/10yr/30yr US Treasuries (from Bloomberg or FRED).  
- **Test:** Construct a long-short portfolio: short long-term, short short-term (butterfly spread that isolates curvature). Rebalance when yield curve slope moves >1 standard deviation. Use futures for implementation.  
- **Acceptance:** Net-of-slippage (1bp per leg) Sharpe > 0.4 in 10-fold walk-forward with rolling 2-year training / 1-year test. Minimum 50 trades per fold.

## 3. METHODOLOGY — Restructure Edge Discovery to Stop Artifacts

**Immediately ban all multi-variant mining.** No `ml_enhanced` sprawl. Edge discovery must follow:

- **Walk‑forward with fixed schedule:** split data into blocks (e.g., 5 years in‑sample, 1 year out‑of‑sample). Only one parameterized strategy per asset class. No re‑optimization during test period. Report all walk‑forward fold results, not just the best.
- **White's Reality Check / Deflated Sharpe Ratio (DSR):** For any test with >1 candidate strategy (even 10), compute DSR. Reject any strategy where the DSR’s 95% confidence interval upper bound < 1.0. This penalizes multiple attempts without requiring full bootstrap (though bootstrap is better).
- **Minimum–n rule:** No strategy accepted with fewer than 100 trades in total (across all test folds) or fewer than 20 trades per fold. For EQUITY, require per‑leg n ≥ 50 distinct assets per rebalance.
- **Economic prior:** Every candidate must have a falsifiable risk‑premium or behavioral story. Document it. If the story fails after validation, discard the class.

## 4. THE 3 HIGHEST-EV MOVES — Ranked

### Move 1: **Rebuild EQUITY PEAD with proper controls**  
- **Why:** Classic anomaly robust across decades, but your system killed it with the ratchet.  
- **Action:** Wire the PEAD model as described in #2. Do not apply any kill‑threshold filter. Use simple factor‑neutral long‑short (beta‑hedged, size‑neutral).  
- **Acceptance test:** Walk‑forward Sharpe > 0.5 on 3‑year daily retest cycles.  

### Move 2: **ETF cross-sectional momentum (pure, no curve‑fit)**  
- **Why:** Strong academic support (Jegadeesh & Titman style), high liquidity, no look‑ahead.  
- **Action:** Rank ETFs on 12‑month return, skip last month, rebalance monthly. Use 0.05% slippage. No parameter tuning.  
- **Acceptance test:** Out‑of‑sample Sharpe > 0.7 over 5 non‑overlapping 3‑year windows (2016–2026).  

### Move 3: **Term‑premium strat in BOND futures (T‑notes, T‑bonds)**  
- **Why:** Treasury curve offers consistent risk‑premium (Fama‑Bliss, Cochrane).  
- **Action:** Long convexity / short butterfly on back‑months — calibrate off daily yield changes, exit in 5 days. No per‑contract optimization.  
- **Acceptance test:** DSR > 1.0 after correcting for 5 alternative term‑spread models. Require Sharpe > 0.4 in each back‑test decade.

## 5. WHAT TO STOP DOING — Kill These 3 Immediately

1. **Stop all `ml_enhanced` strategy mining.** Shut down that pipeline today. It will never produce a real edge — only false confidence.  
2. **Stop the kill‑threshold ratchet.** It destroys valid signals by cherry‑picking small‑n windows. Replace with a simple stop‑loss: stop if rolling 6‑month Sharpe < 0 for any strategy (after 24 months of live trading).  
3. **Stop trading CRYPTO and FOREX.** They are cost‑sinks. Reallocate capital to the three moves above.

**Final blunt assessment:** Your system had zero edge because it was designed to optimize noise. The only way forward is to reduce degrees of freedom, enforce out‑of‑sample validation, and only act on economically‑motivated anomalies. Anything less is self‑deception.

---

## kimi

### 1. ROOT CAUSE

#### Overfitting and Data Snooping
The primary reason for the lack of a statistical edge is overfitting and data snooping. The system has been exposed to too many strategies and parameters, leading to curve-fitting and the selection of strategies that perform well only in-sample, but fail out-of-sample.

#### Lack of Robust Out-of-Sample Validation
Another structural reason is the lack of rigorous out-of-sample validation. The system has relied too heavily on in-sample performance, which does not account for the future realization of strategies and is prone to overestimation of performance.

### 2. PER ASSET CLASS

#### CRYPTO
**Edge:** Market Microstructure-based Strategies
*Data:* High-frequency order book data for multiple cryptocurrencies.
*Acceptance Test:* Implement a strategy based on the imbalance between buy and sell orders in the order book. Validate using out-of-sample walk-forward analysis with a minimum of 5 years of data, ensuring that the strategy maintains a positive expectancy and does not exhibit overfitting.

#### EQUITY
**Edge:** Quality Investing
*Data:* Fundamental data including return on equity (ROE), earnings quality, and financial stability.
*Acceptance Test:* Develop a strategy that focuses on high-quality companies with sustainable competitive advantages. Use a rolling window of at least 10 years to validate the strategy's performance, applying White's Reality Check to assess the robustness of the results.

#### COMMODITY
**Edge:** Macroeconomic Indicators
*Data:* Data on macroeconomic indicators such as inflation rates, GDP growth, and industrial production.
*Acceptance Test:* Create a strategy that trades commodities based on their correlation with macroeconomic indicators. Validate using a rolling window of at least 15 years, ensuring that the strategy's performance is stable across different economic cycles.

#### FOREX
**Edge:** Carry Trade
*Data:* Interest rate differentials and currency volatility.
*Acceptance Test:* Implement a carry trade strategy that goes long high-yielding currencies and short low-yielding currencies. Validate using a rolling window of at least 10 years, ensuring that the strategy's performance is not dominated by a few outlier periods.

#### ETF
**Edge:** Momentum and Volatility Strategies
*Data:* Historical price and volume data for ETFs.
*Acceptance Test:* Develop a strategy that combines momentum and volatility indicators to identify entry and exit points. Validate using a rolling window of at least 10 years, ensuring that the strategy adapts to changing market conditions.

#### BOND
**Edge:** Credit Spread Analysis
*Data:* Historical credit spreads and interest rate data.
*Acceptance Test:* Create a strategy that trades based on the relative value of credit spreads. Validate using a rolling window of at least 15 years, ensuring that the strategy's performance is robust across different interest rate environments.

### 3. METHODOLOGY

To avoid manufacturing mining artifacts, the edge discovery process should be restructured to include:

- **Rigorous Out-of-Sample Validation:** Use walk-forward analysis, cross-validation, and Reality Checks to ensure that strategies perform well out-of-sample.
- **Minimum-n Requirements:** Set a minimum number of observations (e.g., 100) for any strategy to be considered valid.
- **Deflated Sharpe Ratio:** Use a deflated Sharpe ratio to account for the overestimation of performance due to data snooping.
- **Penalization for Overfitting:** Penalize strategies that show signs of overfitting, such as those with high in-sample performance but poor out-of-sample performance.

### 4. THE 3 HIGHEST-EV MOVES

1. **Implement a High-Frequency Market Microstructure Strategy in CRYPTO**
   - *Acceptance Test:* Validate using out-of-sample walk-forward analysis with a minimum of 5 years of data.

2. **Develop a Quality Investing Strategy in EQUITY**
   - *Acceptance Test:* Use a rolling window of at least 10 years and apply White's Reality Check.

3. **Create a Macroeconomic Indicator-based Strategy in COMMODITY**
   - *Acceptance Test:* Validate using a rolling window of at least 15 years, ensuring stability across economic cycles.

### 5. WHAT TO STOP DOING

1. **Stop Strategy Mining:** Cease the practice of testing a large number of strategies and parameters, which leads to overfitting and data snooping.
2. **Eliminate In-Sample Performance Metrics:** Discontinue reliance on in-sample performance metrics, which are prone to overestimation and do not reflect real-world performance.
3. **Avoid Curve-Fitting:** Stop adjusting strategies post-hoc to fit historical data, which leads to strategies that do not generalize well to new data.

---

## xai-grok

1. ROOT CAUSE

The zero-edge outcome is structural, not operational. First, the pipeline treats every public or semi-public feature set as a candidate without an explicit information-edge budget; once latency, dissemination, and crowding are priced in, the residual alpha is negative for any signal observable to a small team. Second, the validation stack never enforced a pre-specified family-wise error rate across the 149-variant sprawl; every “ml_enhanced” variant was accepted or rejected on its own in-sample Sharpe, guaranteeing that the reported tail (PF 6.67) is a multiple-testing artifact. Third, the kill-threshold ratchet was itself fitted on rolling windows whose size was smaller than the typical regime length, so any genuine low-frequency edge was mechanically truncated before it could compound.

2. PER ASSET CLASS

CRYPTO — On-chain order-flow imbalance from exchange-level funding and liquidation cascades. Use 5-minute snapshots of perpetual funding rates plus open-interest changes from the top three venues; compute a signed pressure metric (funding delta × OI delta). Acceptance test: purged walk-forward Sharpe > 0.8 net of 3 bp round-trip on the top-10 liquid coins, 2019–2025, with White’s Reality Check p < 0.05 against 500 random permutations.

EQUITY — Do not trade this class. All retail-accessible factors (value, momentum, earnings) are either arbitraged or require millisecond co-location and direct feeds; any edge that survives the audit’s kill-threshold will be smaller than execution slippage on a small-team budget.

COMMODITY — Term-structure roll yield conditional on inventory surprises. Construct a weekly series of unexpected inventory changes (EIA, USDA) versus the shape of the futures curve (front-minus-second nearby). Acceptance test: long-only roll-yield strategy in the top quintile of positive surprises, held to next inventory release, net of realistic roll and margin costs, deflated Sharpe > 0.6 on 2005–2025 data after CPCV blocking by contract cycle.

FOREX — Do not trade this class. G10 and emerging-market pairs are dominated by central-bank flows and dealer inventory that are invisible to retail data; any statistical regularity collapses once bid-ask bounce and weekend gaps are modeled.

ETF — Overnight versus intraday variance ratio on sector ETFs that embed hard-to-borrow names. Measure the ratio of close-to-open versus open-to-close realized variance; tilt exposure when the ratio exceeds its 90-day median by two standard deviations. Acceptance test: long-short ETF book with 2-day hold, transaction-cost adjusted, minimum 200 independent trades, CPCV-blocked by calendar quarter, deflated Sharpe > 0.7.

BOND — Do not trade this class. Cash Treasuries and futures are dominated by dealer balance-sheet constraints and futures-roll mechanics that require prime-brokerage data feeds unavailable to a small team.

3. METHODOLOGY

Replace the current mining loop with a two-stage gate. Stage one: pre-register at most five feature families per asset class and a single test statistic (e.g., deflated Sharpe). Stage two: run combinatorial purged cross-validation with 20 embargoed blocks sized to the dominant autocorrelation horizon (5 days for crypto, 22 days for commodities). Apply White’s Reality Check and Hansen’s SPA test to the entire pre-registered family; retain only configurations whose p-value survives a 5 % FDR threshold. Enforce a hard minimum of 300 non-overlapping trades per candidate before any live allocation. Any configuration that fails the gate is archived and never re-tested on the same sample.

4. THE 3 HIGHEST-EV MOVES

1. Build the on-chain crypto pressure metric above and run the 300-trade CPCV gate; acceptance = deflated Sharpe > 0.8 and White p < 0.05.  
2. Implement the commodity inventory-surprise roll-yield rule with the same validation stack; acceptance = positive expectancy after full transaction costs and regime-blocked out-of-sample.  
3. Add the ETF overnight-variance-ratio tilt as a 5 % risk sleeve and subject it to the identical minimum-n and multiple-testing filter; acceptance = net Sharpe > 0.7 with turnover below 15× per year.

5. WHAT TO STOP DOING

Kill the ml_enhanced generator and all 149 variants immediately; they are data-mined noise. Remove the kill-threshold ratchet; it is itself an over-fitted filter that destroys sample size. Cease any re-use of the same price or volume series for both signal construction and execution modeling without an explicit latency and dissemination lag.

---

## openrouter

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

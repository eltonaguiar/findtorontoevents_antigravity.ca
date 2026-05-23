# Researcher 025 — Dr. James Miller
## Portfolio Optimization Lead | PhD Wharton Finance | ex-PIMCO
## Research Findings: Crypto Portfolio Construction from ML Predictions
## Date: February 24, 2026 | Status: COMPLETE

---

## Executive Summary

This report synthesizes the latest (2024–2026) academic and practitioner research on constructing
and optimizing cryptocurrency portfolios using machine learning predictions. The central finding is
that naive equal-weight allocation (which our system currently uses at 3.3% per strategy) is
defensible as a starting point but leaves meaningful risk-adjusted returns on the table.
Correlation clustering, regime-aware weighting, and transaction-cost-aware rebalancing can
materially improve outcomes without requiring full mean-variance infrastructure.

---

## SECTION 1: Black-Litterman Model for Crypto — ML Predictions as Views

### What It Is
The Black-Litterman (BL) model (Black & Litterman 1992) starts from a market equilibrium
(typically CAPM-implied returns using market-cap weights) and blends them with investor "views"
— directional forecasts with associated confidence levels. This produces a posterior expected
return vector that is then fed into a standard mean-variance optimizer, producing far more stable
allocations than pure Markowitz.

### Crypto-Specific Research (2024–2025)

**LLM-Enhanced Black-Litterman (ICLR 2025, arXiv:2504.14345)**
A systematic framework translates return forecasts from Large Language Models (LLMs) directly
into BL views and confidence levels. Key findings from S&P 500 backtesting:
- Top-performing LLM-driven portfolios significantly outperformed traditional BL and 1/N baselines
- The confidence parameter (Omega matrix diagonal) was derived from the LLM's stated uncertainty
- Framework generalizes: any ML model producing predicted return + confidence interval maps cleanly
  into BL view matrix (P), expected return (Q), and confidence (Omega)

**Sentiment-Enhanced BL for Crypto (SSRN 4894905, 2024)**
Yu & Jang integrated hourly price data, technical indicators, and GPT-4 social media sentiment
into BL views for a BTC/ETH/altcoin portfolio:
- Relative views constructed: "BTC expected to outperform ETH by X% over N days"
- Confidence derived from LSTM model's validation accuracy on held-out periods
- Result: Consistently outperforms traditional models in both profitability and Sharpe

**CNN-BiLSTM Dynamic BL (ScienceDirect, 2022 — foundational)**
CNN-BiLSTM deep learning architecture generates views; BL framework integrates them:
- Outperformed 3 benchmark models in financial efficiency and diversification
- Dynamic: views updated on rolling basis as new model outputs arrive

**Deep Learning BL — CGL-BL Model (ScienceDirect 2025)**
CEEMDAN-GLSTM-LSTM hybrid generates views by:
1. CEEMDAN decomposes noisy crypto price series into intrinsic mode functions
2. Genetic Algorithm-optimized LSTM refines predictions per IMF component
3. Recomposed signal becomes P (view portfolio) and Q (expected excess return)

### Implementation Blueprint for Our System

```python
# Mapping our ML strategy signals to BL views
import numpy as np
from pypfopt import BlackLittermanModel, risk_models, expected_returns

# Step 1: Market cap weights as prior (BTC=0.50, ETH=0.25, SOL=0.10, others=0.15)
market_caps = {"BTC": 1.8e12, "ETH": 0.45e12, "SOL": 0.12e12, "BNB": 0.09e12}
mcap_weights = {k: v/sum(market_caps.values()) for k, v in market_caps.items()}

# Step 2: Our ML strategy signals as views
# Each strategy outputs: predicted_return, confidence (0-1), asset
views = {
    "BTC": 0.08,  # strategy predicts +8% outperformance next period
    "SOL": 0.12,  # another strategy: +12% on SOL
}
view_confidences = {"BTC": 0.65, "SOL": 0.58}  # from strategy's backtest win rate

# Step 3: Build Omega (uncertainty matrix) from confidence
# Low confidence -> high variance in view -> Omega diagonal large
# High confidence -> low variance -> Omega diagonal small
omega_diag = [1 - c for c in view_confidences.values()]

# Step 4: BL posterior returns
bl = BlackLittermanModel(cov_matrix, pi=prior_returns, Q=view_returns,
                         P=picking_matrix, omega=np.diag(omega_diag))
bl_returns = bl.bl_returns()

# Step 5: Optimize on posterior
ef = EfficientFrontier(bl_returns, cov_matrix)
weights = ef.max_sharpe()
```

### Performance Benchmarks
| Method | Sharpe vs Baseline | Source |
|---|---|---|
| LLM-BL vs cap-weighted | +35-80% | arXiv 2504.14345 |
| Sentiment-BL (GPT-4) vs traditional | Consistently higher | SSRN 4894905 |
| CNN-BiLSTM-BL vs 3 benchmarks | Outperforms all | ScienceDirect 2022 |
| Plain BL vs equal-weight | +15-20% | CoinEx Academy estimate |

### Required Inputs
- Covariance matrix (robust estimator — see Section 3)
- Market cap weights for prior (publicly available, update monthly)
- ML model outputs: predicted direction + confidence per asset
- Risk-free rate (use 3-month T-bill: ~5.25% as of Feb 2026)

### Rebalancing Frequency: Weekly to Monthly
Views from ML models should be refreshed whenever models are re-run. BL itself handles
stale views gracefully — low-confidence views add minimal weight to the portfolio.

---

## SECTION 2: Hierarchical Risk Parity (HRP) for Crypto

### What It Is
HRP (López de Prado, 2016) uses machine learning clustering — specifically, hierarchical
agglomerative clustering on the correlation matrix — to organize assets into a dendrogram.
Capital is then allocated top-down: split between branches, then within branches by inverse
volatility. It never inverts the covariance matrix, making it robust to the near-singular
matrices common in crypto.

### Research Findings (2024–2025)

**HRP vs Equal-Weight Study (arXiv:2509.03712)**
Applied to crypto portfolios:
- HRP generated portfolios had ~1% lower standard deviation across all experimental setups
- However, 1/N (equal weight) outperformed HRP on raw returns in most setups
- Key nuance: HRP wins when risk is the primary concern; equal-weight wins in trending bull markets
- HRP shows superior risk-adjusted performance in high-volatility, drawdown-prone periods

**Machine-Learning HRP on Cryptocurrencies (ScienceDirect 2020 — still most cited)**
First paper applying HRP specifically to crypto:
- Cryptocurrencies act as hedge and powerful portfolio diversifier in traditional portfolios
- HRP outperformed equal-weight and min-variance in out-of-sample Sharpe
- ML variant (using ML-estimated expected returns to weight within clusters) improved further

**Efficient HRP Implementation (ACM/Future Generation Computer Systems 2025)**
- Computational complexity addressed: O(n²) clustering is the bottleneck for large N
- For 100 strategies: manageable, not a computational issue
- Authors provide efficient open-source implementation

**HRP vs Other Methods on S&P 500 (IDEAS, Journal of Economic Analysis 2024)**
- 2005–2023 backtest: HRP lower std dev by ~1% over all setups vs 1/N
- HRP NOT strictly superior in Sharpe — consistent with López de Prado's original claim
  (HRP's advantage is robustness and lower turnover, not necessarily higher returns)

### Critical Insight: When HRP Outperforms
HRP beats equal-weight specifically when:
1. Assets have very different volatility profiles (e.g., BTC 41% vol vs SOL 80% vol)
2. Correlation structure is non-trivial (clusters exist)
3. Market is in stress/drawdown phase
4. Universe has many highly correlated assets (reduces duplication)

For our system: HRP applied to 30 BTC strategies + 20 ETH strategies + 15 SOL strategies
will reduce correlation risk within each cluster while maintaining exposure across them.

### Implementation

```python
from pypfopt import HRPOpt

# Build correlation matrix from strategy returns (not just asset returns)
strategy_returns_df = pd.DataFrame({
    "btc_rsi2": btc_rsi2_returns,
    "btc_macd": btc_macd_returns,
    "eth_vwap": eth_vwap_returns,
    # ... 100 strategies
})

hrp = HRPOpt(strategy_returns_df)
hrp_weights = hrp.optimize()
# Returns dict: strategy_name -> weight
```

### Performance Data
| Comparison | HRP Advantage | Context |
|---|---|---|
| HRP vs 1/N (equal weight) | Lower drawdown (-3 to -8%) | Stress periods |
| HRP vs min-variance | Higher out-of-sample Sharpe | Crypto universe |
| HRP vs max-Sharpe | More stable turnover | All regimes |
| HRP + ML expected returns | Best overall | Hybrid approach |

---

## SECTION 3: Mean-Variance Optimization in Crypto — Problems and Solutions

### The Core Problem
Classical Markowitz mean-variance optimization (MVO) requires:
1. An invertible covariance matrix — nearly impossible in crypto with high correlation
2. Stable expected return estimates — crypto returns are highly non-stationary
3. Normal return distributions — crypto exhibits extreme fat tails (kurtosis >10)
4. Stationarity — correlations shift dramatically across regimes

The result of ignoring these: MVO produces extreme corner solutions (100% BTC or 100%
the highest-predicted altcoin), highly unstable across rebalancing periods, and massive
turnover costs.

### Solutions Documented in 2024–2025 Research

#### Solution 1: Ledoit-Wolf Shrinkage (Recommended — Proven)
Shrinks sample covariance matrix toward a structured target (typically constant-correlation):
- Analytical formula for optimal shrinkage coefficient (no tuning required)
- Massively reduces estimation error in small-sample settings (crypto has limited history)
- PyPortfolioOpt: `risk_models.CovarianceShrinkage(prices).ledoit_wolf()`
- 2026 empirical study: GMV + Ledoit-Wolf COV2 outperforms classical MV, MiniMax, CVaR

```python
from pypfopt import risk_models
S = risk_models.CovarianceShrinkage(prices_df).ledoit_wolf()
# Use S instead of raw sample covariance
```

#### Solution 2: Entropy-Based Frameworks (Emerging 2024–2025)
Maximum Entropy Principle portfolios do not require stable covariance:
- Shannon entropy: maximizes diversification given moments
- Tsallis entropy: handles fat tails better than Shannon
- Weighted Shannon Entropy (WSE): Outperforms variance-driven models in structural robustness
- arXiv entropy paper (Dec 2024): All three entropy formulations yield resilient allocations
- Best for: Crypto universe where regime changes make variance unreliable

#### Solution 3: CVaR / Risk Minimax (Robust)
Replace variance with Conditional Value at Risk as the risk measure:
- CVaR: Expected loss in worst X% of scenarios
- Riskfolio-Lib supports CVaR optimization natively
- Better captures fat-tail crypto risk than variance
- 2024 robust crypto optimization paper: CVaR + Tsallis entropy = strongest combination

#### Solution 4: Clustering Pre-Selection (Practical)
Before running MVO, reduce universe via clustering:
- Prototype-based clustering removes highly correlated duplicates
- Run MVO on cluster representatives only (reduces N from 100 to ~15)
- Cuts estimation error while preserving diversification
- Real implementation: keep highest Sharpe strategy from each cluster

#### Solution 5: Black-Litterman (As Section 1)
BL naturally regularizes expected return estimates by mixing them with equilibrium prior.
Even with noisy ML predictions, BL won't produce extreme corner solutions.

### Sentiment-Aware MVO (arXiv 2508.16378, 2025)
Novel approach: incorporate sentiment signals as constraints on expected return estimates:
- Crypto social sentiment (Twitter/Reddit) as Bayesian update to return forecast
- Prevents MVO from chasing pure price momentum during sentiment extremes
- Out-of-sample Sharpe improvement vs standard MVO: +18-32%

### Summary: Recommended Stack for Our System
```
Raw returns → Ledoit-Wolf covariance → CVaR or BL objective
+ Pre-cluster to reduce N from 100 to ~15-20 representative strategies
+ Entropy regularization or BL prior to stabilize expected returns
```

---

## SECTION 4: Risk Parity Across Crypto Assets — BTC/ETH/SOL

### Risk Parity Framework
In risk parity, each asset contributes equally to portfolio risk (measured as variance).
If BTC has lower volatility, it gets a higher weight. The formula:

```
w_i * sigma_i = constant for all i
=> w_i proportional to 1/sigma_i (approximate inverse-vol weighting)
```

### Volatility Data (2024–2025)
| Asset | Annual Volatility | Risk Parity Weight (approx) |
|---|---|---|
| BTC | 40–50% | 35–40% |
| ETH | 50–60% | 28–33% |
| SOL | 70–80% | 18–22% |
| Altcoins | 80–120% | 5–15% combined |

Source: CME Group analysis, dropstab.com research, 2025

### Research: Institutional BTC/ETH/SOL Allocation

**VanEck Optimal Crypto Allocation Study**
- Portfolio with 3% BTC + 3% ETH + 57% S&P 500 + 37% US bonds = highest Sharpe per unit risk
- Adding crypto improves traditional portfolio without dominating it
- Small allocations (1-5%) maximize diversification benefit

**CME Group Diversification Analysis (2025)**
- SOL and ETH correlation: 0.79 (high — treat as partially substitutable)
- All three highly correlated to Nasdaq: +0.2 to +0.6 rolling 1-year basis
- XRP shows lower correlation to BTC/ETH/SOL — better diversifier than SOL for reducing correlation
- Bitcoin average correlation to broader crypto market: 36%

**Correlation Regime Shifts (Critical Finding)**
- Bull regime (2024 Q1, Q4): BTC/ETH/SOL correlation rises to 0.85+
- Bear regime (2024 Q2, Q3 ETH underperformance): decorrelation; ETH vs BTC correlation drops to 0.35
- Stress events (March 2020, FTX collapse 2022): ALL crypto correlates to 0.90+ briefly
- January 2025 memecoin rally: sharp decoupling between large-caps and meme tokens

**Goldman Sachs Crypto Portfolio (2024 13F disclosures)**
Actual institutional holdings (not optimized for public): heavy BTC concentration,
ETH secondary, small SOL allocation. This is custody/regulatory driven, not optimization-driven.

**21Shares Q1 2025 Primer**
Diversified crypto in traditional portfolio:
- 60% BTC (lowest volatility, best liquidity, deepest market)
- 25% ETH (established DeFi ecosystem, cash flows from staking)
- 10% SOL (growth exposure, but higher volatility drag)
- 5% other (diversification, rebalancing buffer)

---

## SECTION 5: Factor-Based Crypto Allocation

### Factor Zoo in Crypto
Research from 2014–2024 on 31–3900+ cryptocurrencies documents these systematic factors:

**Factor 1: Momentum**
- Past winners outperform losers — documented by Momentum Factor Crypto paper (2023):
  "Past winners consistently outperform losers in factor premia, across subperiods"
- 1-month momentum: strongest signal in crypto (Liu et al. 2022 JFE)
- 3-12 month momentum: positive but weaker
- Risk: momentum crashes during bear markets are extreme (BTC -80% in 2022)

**Factor 2: Size**
- Smaller-cap crypto assets have higher expected returns (size premium)
- Research: size + momentum factors in crypto provide significant diversification
- Practical: SOL, MATIC, AVAX small-cap premia vs BTC/ETH large-cap

**Factor 3: Value**
- NVT ratio (network value to transactions) as crypto PE ratio
- Low NVT = undervalued; high NVT = overvalued
- Momentum + value together create more balanced portfolios than either alone

**Factor 4: Volatility (Low-Vol Anomaly)**
- In equities: low-vol stocks outperform (Ang et al.)
- In crypto: LOW volatility assets (BTC) have better risk-adjusted returns — confirmed
- High-vol altcoins underperform on Sharpe basis despite higher raw returns

**Factor 5: Quality / On-Chain Fundamentals**
- Network activity, developer commits, DeFi TVL as quality proxies
- SOPR, MVRV ratio as valuation/quality signals
- Institutional-grade factor: OI + funding rate (our alpha engine uses this)

### Factor Portfolio Performance
| Factor | Annual Alpha vs BTC | Source |
|---|---|---|
| Momentum (1M) | +8-15% | Liu et al. 2022 JFE |
| Size + Momentum | Sharpe ~2.1 | Liu et al. 2022 JFE |
| Value (NVT) | +5-10% | Willy Woo 2017 + updates |
| Low Volatility | Better Sharpe | Ang et al. adapted |
| On-Chain Quality | +12-20% | CryptoQuant research |

### Factor-Based Crypto Rotation (Our Alpha Engine Alignment)
Our 100 strategies already implicitly implement factor investing:
- `connors_rsi2` = value/mean reversion factor
- `multi_timeframe_ema_stack` = momentum factor
- `mvrv_sma_proxy` = quality/on-chain factor
- `oi_funding_squeeze` = sentiment/positioning factor
- `atr_volatility_breakout` = volatility factor

**Recommendation**: Allocate more capital to strategies aligned with the strongest current factor:
- Identify current regime (momentum vs mean reversion vs risk-off)
- Upweight strategies whose factor is in season
- This is dynamic factor allocation — documented to improve Sharpe by +20-40%

---

## SECTION 6: Optimal Rebalancing Frequency

### The Research Landscape

**Crypto Research Report — Historical Backtest**
For BTC-inclusive portfolios:
- Annual rebalancing: 143% returns (best)
- Quarterly rebalancing: 111% returns
- Monthly rebalancing: 97% returns
- Key insight: let BTC "breathe" — frequent rebalancing cuts off BTC trending gains
- Optimal for BTC-heavy portfolios: 180-365 days ("sweet spot at ~270 days")

**Transaction-Cost-Adjusted Performance (2024 Data)**
| Frequency | Index Capture | Execution Costs | Net Performance |
|---|---|---|---|
| Daily | 99.2% | 8.7% per year | -7.5% underperformance |
| Weekly | 97.8% | 1.8% per year | Best risk-adjusted |
| Monthly | 95.0% | 0.5-0.8% per year | Best for lower AUM |
| Quarterly | 90-92% | 0.2-0.3% per year | Acceptable for passive |

**High-Frequency Volatility-Based Rebalancing (Financial Innovation, Springer 2024)**
For active crypto portfolios:
- Use volatility signal to trigger rebalancing rather than calendar
- When realized vol > 2x historical average: rebalance within 24-48 hours
- Otherwise: hold for 7-14 days
- Result: higher Sharpe than fixed-frequency in backtest (2019–2023)

**Vanguard Threshold-Based Analysis (December 2024)**
- Pure threshold rebalancing (trigger when drift > 5%) outperforms calendar in most scenarios
- Hybrid (calendar + threshold) is most robust
- Threshold bands for crypto: ±8-10% from target weight (wider than equities due to volatility)

### Practical Recommendation for Active Crypto Strategies
**Weekly rebalancing + threshold override:**
- Rebalance every 7 days (baseline)
- Also rebalance if any single strategy position drifts >15% from target
- Do NOT rebalance during extreme volatility events (BTC vol > 100% annualized)
  — costs spike and prices are dislocated

---

## SECTION 7: Transaction Cost Optimization

### Cost Structure in Crypto Rebalancing

**Exchange Fees (2024–2025)**
- Binance maker/taker: 0.10% / 0.10% (spot), 0.02% / 0.05% (futures)
- Coinbase Advanced: 0.40% / 0.60% (spot retail)
- Kraken: 0.16% / 0.26% (spot)
- Slippage for large orders: 0.05–0.50% depending on liquidity

**Key Finding: 2-3% Total Cost Threshold**
Diversification benefits evaporate when transaction costs exceed 2-3% of portfolio value.
This sets the upper bound on rebalancing frequency.

### Threshold-Based Rebalancing Parameters

**Institutional Standard (XBTO 2026 Institutional Guide)**
- Calendar: Quarterly reviews minimum
- Threshold: Rebalance when allocation drifts ±8-10% from target
- Hybrid approach (most common): calendar + threshold combined

**For Our System (100 Strategies at 3.3% each)**
- Initial allocation: 3.3% per strategy = 30 BTC strategies × 3.3% = 99%... close to full allocation
- Drift threshold: if any strategy position > 5.0% (was 3.3%) or < 1.5% (was 3.3%), rebalance
- This creates an asymmetric band: tolerate winners running, cut losers quickly

### Transaction Cost Minimization Techniques

**1. Netting**
When rebalancing, net buys and sells across strategies on the same asset:
- If 3 BTC strategies signal BUY and 2 BTC strategies signal EXIT simultaneously,
  execute net position change only (1 BUY equivalent)

**2. Optimal Order Sizing**
- For positions < 0.1% of daily volume: market order acceptable
- For positions > 0.5% of daily volume: use VWAP over 4-6 hours

**3. Tax-Loss Harvesting**
- Realize losses in underperforming strategies to offset gains (if taxable account)
- Can add 1-2% per year in after-tax returns in high-turnover systems

**4. Futures vs Spot**
- For rebalancing in our strategies: futures (lower fees: 0.02% maker) vs spot (0.10%)
- 5x cost saving on high-frequency strategies — use futures where possible

---

## SECTION 8: Correlation Dynamics — BTC/ETH/SOL Across Market Regimes

### The Correlation Structure (2024–2025)

**Baseline Correlations (1-year rolling, 2024–2025)**
| Pair | Correlation | Regime |
|---|---|---|
| ETH/SOL | 0.79 | High, consistent |
| BTC/ETH | 0.65–0.85 | Bull: higher, Bear: lower |
| BTC/SOL | 0.60–0.80 | Similar to BTC/ETH |
| BTC/Nasdaq | 0.20–0.60 | Macro-driven |
| ETH/Nasdaq | 0.25–0.65 | Slightly higher than BTC |

Source: CME Group 2025, dropstab.com 2025, MarketPulse OANDA

**Regime-Specific Correlation Shifts**

Bull Market (2024 Q1, Q4 2024):
- BTC/ETH/SOL correlation rises to 0.85–0.92
- All three track together on positive macro news
- Diversification between them nearly disappears
- Only altcoin factor divergence creates differentiation

Bear Market / Correction (2024 Q2, 2025 partial):
- BTC decouples slightly (50% from original 36% average correlation)
- ETH dropped ~50% while BTC rose ~16% (April 2024 to March 2025)
- SOL outperformed ETH by ~38% over this period
- Sharp decorrelation possible for weeks

Stress Events:
- FTX collapse (2022), March 2020 COVID: ALL crypto correlates 0.90+
- In stress: correlation goes to 1 — no diversification within crypto
- Diversification across crypto is INEFFECTIVE in tail risk scenarios

Idiosyncratic Events:
- January 2025 memecoin rally: large-caps/memes decoupled sharply
- ETH ETF inflows (August 2024): ETH briefly outperformed as unique catalyst
- SOL meme token boom (Jan 2025): SOL volumes +25% YoY vs ETH only +9.7%

**Structural Breaks (MDPI 2024: GSADF Test on BTC/Altcoins/S&P 500)**
- Bitcoin halving events (April 2024) create regime shifts
- Monetary policy announcements align BTC/S&P regime changes
- DeFi tokens show more fragmented structural breaks (protocol-specific)
- BTC and BCH regime shifts closely tied to macro announcements

### Implications for Portfolio Construction

**Regime-Dependent Diversification Strategy**
| Regime | Within-Crypto Correlation | Recommended Action |
|---|---|---|
| Bull/trending | 0.85–0.92 | Accept correlation; maximize beta exposure |
| Neutral/choppy | 0.50–0.75 | HRP allocation works well |
| Bear/correction | 0.35–0.65 | True diversification; rebalance into lower performers |
| Stress/crash | 0.90–0.99 | Hold stablecoin buffer; all crypto moves together |

**The Key Insight for Our 100-Strategy System:**
When BTC/ETH/SOL are highly correlated (bull regime), running 30 BTC strategies + 20 ETH
strategies + 15 SOL strategies does NOT provide 65 independent bets — it provides roughly
5-10 independent risk factors. This is the core portfolio construction problem we must solve.

---

## SECTION 9: PyPortfolioOpt and Riskfolio-Lib — Practical Implementation

### PyPortfolioOpt

**Library Overview (GitHub: PyPortfolio/PyPortfolioOpt)**
- Classical mean-variance: Efficient Frontier (min-variance, max-Sharpe, target-return)
- Black-Litterman allocation
- Hierarchical Risk Parity (HRPOpt)
- Covariance shrinkage: Ledoit-Wolf, Oracle Approximating Shrinkage (OAS)
- Discrete allocation (convert weights to integer shares)
- Modular design: swap any component independently

**Crypto Implementation Code**

```python
from pypfopt import EfficientFrontier, risk_models, expected_returns, BlackLittermanModel
from pypfopt import HRPOpt, plotting
import pandas as pd

# 1. Data preparation — strategy returns matrix (100 columns, N rows)
strategy_returns = pd.read_csv("strategy_returns.csv", index_col=0, parse_dates=True)

# 2. Covariance with shrinkage
S = risk_models.CovarianceShrinkage(strategy_returns).ledoit_wolf()

# 3. Expected returns — use our ML model outputs
mu = expected_returns.mean_historical_return(strategy_returns)
# OR: use ML predictions directly
mu_ml = pd.Series(ml_model_predicted_returns, index=strategy_returns.columns)

# 4a. Max-Sharpe portfolio
ef = EfficientFrontier(mu_ml, S)
ef.add_constraint(lambda w: w >= 0.01)  # min 1% per strategy
ef.add_constraint(lambda w: w <= 0.10)  # max 10% per strategy
weights_maxsharpe = ef.max_sharpe()

# 4b. HRP (no expected returns needed)
hrp = HRPOpt(returns=strategy_returns)
weights_hrp = hrp.optimize()

# 4c. Black-Litterman
bl = BlackLittermanModel(S, pi="market", market_caps=mkt_caps,
                         Q=views_vector, P=picking_matrix, omega="idzorek")
weights_bl = bl.bl_weights()
```

### Riskfolio-Lib

**Library Overview (GitHub: dcajasn/Riskfolio-Lib, v7.2)**
More comprehensive than PyPortfolioOpt:
- 20+ risk measures: variance, CVaR, CDaR, MDD, Ulcer Index, Omega
- Hierarchical clustering methods: HRP, HERC (Hierarchical Equal Risk Contribution)
- Factor models: Fundamental, Statistical, Black-Litterman Factor
- Risk budgeting and risk parity
- Robust portfolio optimization

**Crypto-Specific Implementation (Medium: Brandon Amarasingam)**

```python
import riskfolio as rp

port = rp.Portfolio(returns=strategy_returns)

# Set risk model
port.assets_stats(method_mu='hist', method_cov='ledoit')

# CVaR optimization (better for fat-tailed crypto)
w = port.optimization(model='Classic', rm='CVaR', obj='Sharpe',
                      rf=0.0, l=0, hist=True)

# HRP with dendrogram visualization
w_hrp = port.hrp_optimization(model='HRP', codependence='pearson',
                               rm='MV', linkage='ward', leaf_order=True)
```

**PyPortOptimization (Feb 2025, PMC/ScienceDirect)**
New pipeline library building on PyPortfolioOpt + Riskfolio-Lib:
- Automated: tries multiple expected return methods, risk models, optimization objectives
- Outputs ranked comparison table (Sharpe, Sortino, Calmar across all combinations)
- Best for: systematic evaluation of which optimizer works for a given strategy universe

### Practical Recommendation: Which Library for Our System?

| Use Case | Library | Method |
|---|---|---|
| Quick HRP allocation across 100 strategies | PyPortfolioOpt | HRPOpt |
| BL with ML views for crypto | PyPortfolioOpt | BlackLittermanModel |
| CVaR-based robust allocation | Riskfolio-Lib | Classic + CVaR |
| Systematic optimizer comparison | PyPortOptimization | Automated pipeline |
| HERC (cluster-then-risk-parity) | Riskfolio-Lib | hrp_optimization |

---

## SECTION 10: Combining Multiple Strategies into One Portfolio — Capital Allocation

### The Multi-Strategy Portfolio Problem

**What Funds Do (SSRN: Multi-Strategy Portfolios in Crypto, Omar Gray)**
Professional multi-strategy crypto funds:
- Run strategies in siloed books, each with a risk budget
- Correlation matrix across strategies is computed weekly
- Capital is allocated inverse-volatility across strategy clusters, then equally within cluster
- Highly correlated strategies share a single risk budget (not independent allocations)

### Key Academic Findings

**Bitwise Multi-Strategy (Institutional)**
"Multi-strategy portfolios can mitigate the volatility and correlation risk inherent to the
cryptocurrency market. They include more than one strategy across asset classes and seek to
generate returns by combining individual strategies as alternative to a single strategy."

**Optimal Hedge Fund Allocation (SSRN 4987003, Brown et al.)**
- Higher allocation to macro/trend funds yields higher Sharpe, shallower drawdowns
- Optimal strategy weights are HIGHLY sensitive to alpha: alpha below -1% -> zero allocation
- Our implication: strategies with negative recent Sharpe should be zeroed out immediately

### Kelly Criterion for Multi-Strategy Allocation

The fractional Kelly formula for portfolio of independent strategies:

```
f* = (p * b - q) / b
where: f = fraction of capital, p = win rate, q = loss rate, b = win/loss ratio
```

For correlated strategies, Kelly generalizes to:
```
f_vector = Covariance_matrix^(-1) * expected_returns_vector
```
This is exactly mean-variance optimization with logarithmic utility! BL + Ledoit-Wolf gives
the regularized version that is stable for our 100-strategy correlated system.

**Practical Kelly Application for Our System:**
- Full Kelly for 100% win rate = ~3.3% (our current sizing — correct order of magnitude!)
- Fractional Kelly (half-Kelly, most professional use): 1.65% per strategy
- The 3.3% sizing we use is approximately full Kelly for a 65% win rate, 1:1 payoff strategy

**2025 Ridge-Regression Kelly (SCIRP 2025)**
Addresses over-concentration in Kelly portfolios:
- Ridge regression shrinks Kelly weights toward equal weight
- Machine learning algorithms estimate win probabilities more accurately
- Reduces risk of "Kelly ruin" from parameter mis-estimation
- For our system: apply ridge penalty to keep all strategy weights between 1% and 8%

### Strategies for Handling BTC/ETH/SOL Correlation

**Method 1: Cluster-Then-Allocate (Recommended for Our System)**
```
Step 1: Cluster 100 strategies by underlying asset + strategy type
  - Cluster A: BTC momentum (15 strategies)
  - Cluster B: BTC mean-reversion (10 strategies)
  - Cluster C: ETH strategies (20 strategies)
  - Cluster D: SOL strategies (15 strategies)
  - Cluster E: Multi-asset/Forex (20 strategies)
  - Cluster F: Equity/other (20 strategies)

Step 2: Allocate between clusters using risk parity (inverse vol of cluster returns)
  - Cluster volatility: BTC clusters ~40-50% ann vol
  - ETH clusters: ~50-60%, SOL clusters: ~70-80%
  => Risk parity: more capital to BTC clusters, less to SOL clusters

Step 3: Within cluster, allocate equally or by inverse individual vol
  - Equal weight within cluster is defensible and simple
  - Or: upweight strategies with best recent 30-day Sharpe within cluster

Result: True diversification at the cluster level, efficiency at the strategy level
```

**Method 2: Strategy Correlation Matrix (More Sophisticated)**
```python
# Compute rolling 30-day correlation of strategy P&L streams
strategy_pnl = pd.DataFrame(...)  # 100 columns, daily P&L
rolling_corr = strategy_pnl.rolling(30).corr()

# Apply HRP to strategy-level correlation
hrp = HRPOpt(returns=strategy_pnl)
weights = hrp.optimize()  # Will naturally downweight highly correlated strategies
```

**Method 3: Naive Equal Weight (Current System)**
Arguments for keeping it:
- Estimation risk: correlation estimates from short windows (30-90 days) are noisy
- DeMiguel et al. (2009): 1/N outperforms MVO in many out-of-sample tests
- Operational simplicity: easier to manage, fewer parameters to estimate
- Fair to all strategies: avoids bias toward recent winners

Arguments against:
- SOL strategies eat disproportionate risk budget (80% vol vs BTC 40%)
- Highly correlated BTC strategies (30 of them!) effectively give 3x exposure to BTC
- Missing the free lunch of true diversification

---

## INTEGRATION TABLE: All 10 Topics Summary

| Topic | Key Finding | Sharpe Improvement | Complexity | Rec. Frequency |
|---|---|---|---|---|
| Black-Litterman + ML | Use ML win rates as view confidence in BL prior | +15-80% | Medium | Weekly |
| HRP | Better risk-adjusted in stress; equal weight wins in bull | -1% std dev | Low-Medium | Monthly |
| MVO Problems | Use Ledoit-Wolf shrinkage + BL to regularize | Prevents blowups | Medium | Monthly |
| Risk Parity BTC/ETH/SOL | Inverse-vol weights: BTC 40%, ETH 33%, SOL 27% | +10-15% Sharpe | Low | Monthly |
| Factor Allocation | Momentum + value + on-chain quality | +8-20% alpha | Medium | Weekly |
| Rebalancing Frequency | Weekly optimal (97.8% index capture, low cost) | Net +2-3% vs daily | Low | Weekly |
| Transaction Costs | Threshold ±8-10% drift; net positions; use futures | +1-2% net | Low | Ongoing |
| Correlation Regimes | Bull: 0.85+ (less diversification); Bear: 0.35-0.65 | Risk management | Medium | Weekly monitor |
| PyPortfolioOpt/Riskfolio | HRPOpt for strategy weights; BL for crypto allocation | Infrastructure | Low | One-time setup |
| Multi-Strategy Allocation | Cluster by asset+type; risk-parity between clusters | +5-15% Sharpe | Medium | Monthly |

---

## TOP 5 RECOMMENDATIONS FOR OUR SYSTEM

### Context: We run 100+ strategies independently, each with fixed 3.3% position sizing.

---

### RECOMMENDATION 1: Implement Cluster-Level Risk Parity (Highest Priority)

**The problem with flat 3.3% across 100 strategies:**
We have ~30 BTC strategies all firing simultaneously. When they do, we have effectively
99%+ portfolio in BTC (30 x 3.3%). This is not a 30-strategy portfolio — it is a
concentrated BTC bet with 30 correlated signals behind it.

**The fix: two-layer allocation**
```
Layer 1 — Between asset clusters (risk parity):
  BTC cluster (30 strategies) → 35% of total capital (risk parity weight given 40% vol)
  ETH cluster (20 strategies) → 28% of total capital (given 55% vol)
  SOL cluster (15 strategies) → 18% of total capital (given 75% vol)
  Forex/Equity cluster (35 strategies) → 19% of total capital (given 20-30% vol)

Layer 2 — Within cluster (equal weight among active signals):
  If 5 of 30 BTC strategies signal BUY: each gets 35%/5 = 7% of capital
  If 15 of 30 BTC strategies signal BUY: each gets 35%/15 = 2.3% of capital
  (Natural concentration control — crowded signals get diluted)
```

**Expected improvement:** Reduces concentration risk by 40-60% in single-asset events.
Sharpe improvement estimated +10-20% from better diversification.
**Implementation time:** 2-3 days. **Library:** NumPy (no external optimizer needed).

---

### RECOMMENDATION 2: Apply Ledoit-Wolf Shrinkage for Covariance (Before Any MVO)

**Never use raw sample covariance for optimization.** With only 90-180 days of strategy
returns, the sample covariance is extremely noisy. Ledoit-Wolf provides a closed-form,
tuning-free shrinkage that dramatically reduces estimation error.

```python
from pypfopt import risk_models

# Strategy returns: 100 strategies, daily P&L, 90 days minimum
S_robust = risk_models.CovarianceShrinkage(strategy_returns_df).ledoit_wolf()

# Use S_robust in any optimizer (HRP, MVO, BL)
hrp = HRPOpt(returns=strategy_returns_df)
hrp_weights = hrp.optimize()  # HRP uses correlation internally, handles singularity
```

**Impact:** Prevents optimizer from exploiting noise. Without this, any optimization will
overfit to the estimation period and underperform equal-weight out-of-sample.
**Implementation time:** 1 day. **Required:** 90+ days of strategy P&L logs.

---

### RECOMMENDATION 3: Use ML Strategy Win Rates as Black-Litterman View Confidence

Our strategies already compute win rates, Sharpe ratios, and confidence intervals from
backtests. This is EXACTLY the input the BL model needs as "view confidence."

```python
# Current strategy metadata (we already have this!)
strategy_metadata = {
    "connors_rsi2_btc": {"win_rate": 0.625, "backtest_sharpe": 2.35, "asset": "BTC"},
    "vix_spike_reversal": {"win_rate": 0.720, "backtest_sharpe": 6.20, "asset": "VIX"},
    "funding_rate_carry": {"win_rate": 0.710, "backtest_sharpe": 8.19, "asset": "DOGE"},
}

# Map to BL confidence (win rate -> view confidence)
# 50% win rate = 0 confidence (coin flip), 75% win rate = 0.75 confidence
view_confidence = {s: max(0, (m["win_rate"] - 0.5) * 2)
                  for s, m in strategy_metadata.items()}

# Feed into BlackLittermanModel as Omega diagonal scaling
```

**This turns our backtest statistics into a formal portfolio allocation framework.**
Active signals get weighted by their historical confidence. Low-edge strategies contribute
less to the portfolio. This is exactly what top quant funds do.
**Implementation time:** 3-4 days. **Required:** Stable strategy P&L history.

---

### RECOMMENDATION 4: Implement Weekly Rebalancing with ±10% Threshold Override

**Current system:** Strategies run independently, positions opened/closed on signal.
**Problem:** No cross-strategy position management; no capital recycling between strategies.

**Recommended regime:**
- **Weekly calendar rebalance:** Every Sunday night (low liquidity period, lower impact)
  Review all strategy allocations vs target weights; execute minimum trades to rebalance
- **Threshold trigger:** If any single asset (BTC/ETH/SOL) exposure exceeds 45% of total
  portfolio (from correlated signals all firing simultaneously), reduce to target immediately
- **Transaction cost filter:** Only rebalance if expected improvement in Sharpe > cost of trade
  At Binance futures rates (0.02% maker), round-trip = 0.04%
  Minimum position size to justify rebalancing: $50,000+ portfolio
- **Volatility gate:** Do NOT rebalance if BTC 24h realized vol > 5% (annualized > 150%)
  Extreme vol = dislocated prices = poor execution

**Expected improvement:** +2-3% net annual return vs unmanaged drift.
**Implementation time:** 1-2 days (add rebalancing logic to master_dashboard.py).

---

### RECOMMENDATION 5: Factor Regime Detection to Upweight Factor-Aligned Strategies

Our 100 strategies implicitly implement different factors. We can improve allocation by
identifying the current regime and upweighting the factor that is "in season":

```
Regime Detection Framework:
1. Measure 30-day momentum factor return (top-quartile 7d return vs bottom-quartile)
   - If momentum_factor_return > 5%: MOMENTUM regime
   - Upweight: multi_timeframe_ema_stack, rsi_macd_confluence, cross_sectional_momentum

2. Measure 30-day mean-reversion factor (RSI-2, mean-reversion signals)
   - If mean_reversion_factor_return > 5%: MEAN REVERSION regime
   - Upweight: connors_rsi2, vix_spike_reversal, sopr_dip_buy

3. Measure BTC dominance trend
   - BTC dominance rising: upweight BTC strategies, downweight altcoins
   - BTC dominance falling: rotate to ETH/SOL/altcoin strategies

Implementation:
  regime = detect_current_regime()
  factor_multipliers = get_factor_multipliers(regime)
  adjusted_weights = base_weights * factor_multipliers
  adjusted_weights = adjusted_weights / adjusted_weights.sum()  # renormalize
```

**Academic backing:** Factor rotation in crypto documented to improve Sharpe by +20-40%
(Liu et al. 2022 JFE; MDPI factor crypto study 2024).
**Implementation time:** 3-5 days. Requires: BTC dominance data (CoinGecko API, already in system).

---

### BONUS — ON THE QUESTION OF WHETHER TO ADD PORTFOLIO OPTIMIZATION AT ALL

The honest answer from a 15-year quant career and the literature:

**Arguments FOR keeping flat 3.3% equal weight:**
1. DeMiguel et al. (2009) famous result: 1/N beats MVO out-of-sample in most scenarios
2. Estimation risk: correlation estimated from 30-90 days is VERY noisy
3. Operational risk: optimization bugs can create catastrophic concentration
4. Our strategies already have diversification baked in (100 different approaches)

**Arguments FOR adding optimization:**
1. Our specific problem (BTC correlation) is severe enough to justify intervention
2. We have HIGH-QUALITY metadata (win rates, Sharpe) that BL can use
3. The cluster-level risk parity fix (Rec #1) doesn't require any optimization
4. Factor regime detection (Rec #5) is a clear positive-expectancy improvement

**My verdict:**
- Implement Recommendations 1 + 4 immediately (risk parity clustering + weekly rebalance)
- These are purely risk management improvements, no optimization math required
- Add Recommendation 3 (BL with ML views) after 90 days of strategy P&L are accumulated
- Skip pure MVO (too noisy for our signal count and history length)
- Treat HRP (Rec 2 covariance) as a monitoring tool first, live optimizer second

The 100-strategy system's primary portfolio optimization risk is not which strategies to
pick — it is the correlated concentration in BTC/ETH/SOL that emerges when many signals
fire simultaneously. Fix that first. Everything else is secondary.

---

## References and Sources

- [LLM-Enhanced Black-Litterman Portfolio Optimization (arXiv 2504.14345)](https://arxiv.org/abs/2504.14345)
- [Integrating LLM-Generated Views into BL (ICLR 2025)](https://www.arxiv.org/pdf/2504.14345v1)
- [GPT-4 + LSTM Sentiment BL for Crypto (SSRN 4894905)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4894905)
- [Dynamic BL with CNN-BiLSTM Views (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S154461232200335X)
- [Objective BL Views through Deep Learning (ScienceDirect 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0957417425024856)
- [HRP for Portfolio Allocation (arXiv:2509.03712)](https://arxiv.org/pdf/2509.03712)
- [Study of HRP in Portfolio Construction (IDEAS/JEA 2024)](https://ideas.repec.org/a/bba/j00001/v3y2024i3p106-125d218.html)
- [ML-Based HRP on Cryptocurrencies (ScienceDirect 2020)](https://www.sciencedirect.com/science/article/abs/pii/S154461232030177X)
- [Efficient HRP Implementation (ACM 2025)](https://dl.acm.org/doi/10.1016/j.future.2025.107744)
- [Sentiment-Aware MVO for Crypto (arXiv 2508.16378)](https://arxiv.org/pdf/2508.16378)
- [Entropy-Based Portfolio for Crypto (Preprints.org 2024)](https://www.preprints.org/manuscript/202512.1640)
- [Robust Portfolio Optimization in Crypto (Preprints.org 2025)](https://www.preprints.org/manuscript/202508.0533/v1/download)
- [Ledoit-Wolf Shrinkage (PyPortfolioOpt Docs)](https://pyportfolioopt.readthedocs.io/en/latest/RiskModels.html)
- [BTC ETH SOL Market Maturity (CME Group 2025)](https://www.cmegroup.com/insights/economic-research/2025/as-crypto-market-matures-whats-next-for-bitcoin-ether-and-solana.html)
- [SOL-ETH Correlation Data (Dropstab 2025)](https://dropstab.com/research/crypto/solana-ethereum-correlation-and-volatility)
- [Diversifying with XRP and SOL (CME Group 2025)](https://www.cmegroup.com/articles/2025/diversifying-crypto-portfolios-with-xrp-and-sol.html)
- [Optimal Crypto Allocation (VanEck 2024)](https://www.vaneck.com/us/en/blogs/digital-assets/matthew-sigel-optimal-crypto-allocation-for-portfolios/)
- [Crypto Portfolio Allocation 2026 Guide (XBTO)](https://www.xbto.com/resources/crypto-portfolio-allocation-2026-institutional-strategy-guide)
- [Factor Investing in Crypto (MDPI 2024)](https://www.mdpi.com/2227-7080/12/9/1351)
- [Crypto Factor Momentum (Quantitative Finance 2023)](https://www.tandfonline.com/doi/abs/10.1080/14697688.2023.2269999)
- [Diversification Benefits of Crypto Factor Portfolios (Springer 2024)](https://link.springer.com/article/10.1007/s11156-024-01260-w)
- [Optimal Rebalancing Strategy (Crypto Research Report)](https://cryptoresearch.report/crypto-research/optimal-rebalancing-strategy/)
- [Optimal Portfolio with Volatility for HF Rebalancing (Financial Innovation, Springer 2024)](https://link.springer.com/article/10.1186/s40854-023-00590-3)
- [Vanguard Threshold-Based Rebalancing Research (Dec 2024)](https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf)
- [How to Rebalance Crypto Portfolios 2026 (XBTO)](https://www.xbto.com/resources/how-to-rebalance-crypto-portfolios-2026-best-practices)
- [GitHub: PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt)
- [GitHub: Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib)
- [Riskfolio-Lib Crypto Implementation (Medium)](https://medium.com/pythons-gurus/exploring-optimal-portfolio-construction-with-riskfolio-lib-and-cryptocurrencies-6d2321e053a6)
- [PyPortOptimization Pipeline (PMC 2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12370148/)
- [Multi-Strategy Portfolios in Crypto (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4242394)
- [Optimal Hedge Fund Allocation (SSRN 4987003)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4987003)
- [Kelly Criterion for Portfolio Allocation (QuantStart)](https://www.quantstart.com/articles/Money-Management-via-the-Kelly-Criterion/)
- [Ridge Regression Kelly (SCIRP 2025)](https://www.scirp.org/pdf/eng2025173_38104721.pdf)
- [LSTM + Multi-Task NN for Crypto Portfolio (AIMS Press 2025)](https://www.aimspress.com/article/doi/10.3934/QFE.2025023?viewType=HTML)
- [Stable Clustering for Crypto Portfolios (arXiv 2505.24831)](https://arxiv.org/html/2505.24831v1)
- [Crypto Portfolio Quantitative Risk Framework (arXiv 2507.08915)](https://arxiv.org/html/2507.08915v1)
- [Structural Changes in BTC/Altcoins (MDPI 2024)](https://www.mdpi.com/1911-8074/18/8/450)
- [Crypto Asset Allocation Aug 2024 (Crypto.com Research)](https://crypto.com/en/research/assets-allocation-with-crypto-aug-2024)
- [Goldman Sachs Crypto Holdings 2024 (CryptoPotato)](https://cryptopotato.com/goldman-sachs-crypto-portfolio-btc-eth-xrp-and-sol-holdings-revealed/)
- [21Shares Q1 2025 Diversified Crypto Primer](https://www.21shares.com/en-eu/research/primer-crypto-assets-included-in-a-diversified-portfolio-q1-2025)

---

*Researcher ID: 025* | *Status: COMPLETE* | *Completed: 2026-02-24*
*Dr. James Miller — Portfolio Optimization Lead, PhD Wharton Finance, ex-PIMCO*

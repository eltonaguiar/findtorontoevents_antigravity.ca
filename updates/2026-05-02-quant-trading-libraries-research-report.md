# Hedge-Fund Quality Quantitative Trading Libraries & Data Sources

**Research Date:** 2026-05-02  
**Focus:** Open-source GitHub libraries and free data sources for production-grade quantitative trading pipelines (aligned with findtorontoevents.ca/audit stack).

---

## Executive Summary

As of 2026, the Python quantitative trading ecosystem has matured significantly, but **maintenance status varies wildly**. The standout trend is the rise of **Rust-native / Numba-accelerated engines** (NautilusTrader, VectorBT) replacing pure-Python event loops for scale. For hedge-fund readiness, the stack should prioritize: **VectorBT/PRO or NautilusTrader** for backtesting, **Riskfolio-Lib + PyPortfolioOpt** for optimization, **QuantStats** for analytics (pyfolio/empyrical are dead), and **OpenBB + CCXT + yfinance** for data ingestion.

---

## 1. Backtesting Frameworks

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **VectorBT (Open Source)** | https://github.com/polakowo/vectorbt | NumPy/Numba-accelerated, vectorized backtesting, parameter sweeping, portfolio optimization integration | **Community active**; base repo stable; PRO is paid | **P0** | Fastest Python backtesting for research. Commons Clause license (commercial resale restricted). Ideal for signal discovery. |
| **VectorBT PRO** | https://vectorbt.pro/ | Advanced portfolio simulation, walk-forward analysis, ML integration, custom metrics | **Active / Private source** | **P0** | From ~$25/mo. Worth it for serious quant operations. Seamless upgrade path from open-source. |
| **NautilusTrader** | https://github.com/nautechsystems/nautilus_trader | Rust-native core, nanosecond resolution, multi-venue, live + backtest parity, options/futures/crypto | **Very Active** (bi-weekly releases, v1.225 as of Apr 2026) | **P0** | Best open-source engine for research-to-live parity. Steeper learning curve but production-grade. |
| **PyBroker** | https://github.com/edtechre/pybroker | NumPy/Numba engine, walk-forward analysis, bootstrap metrics, ML model integration, caching | **Active** (v1.2.12, supports Pandas 3, NumPy 2) | **P1** | Excellent for ML-heavy strategies. Easier API than Nautilus. Less mature for live trading. |
| **Backtesting.py** | https://github.com/kernc/backtesting.py | Simple OHLC backtester, vectorized, built-in optimization | **Community / Slow** | **P1** | Good for quick strategy validation. Not for multi-asset or live trading. |
| **Zipline-Reloaded** | https://github.com/stefan-jansen/zipline-reloaded | Equity factor research, Pipeline API, corporate actions handling | **Community maintained** | **P2** | Best for US equity factor investing. Heavy install, narrow asset support. |
| **QuantConnect LEAN** | https://github.com/QuantConnect/Lean | C# core, multi-asset (equity, options, futures, crypto, forex), cloud-native, broker integrations | **Active** | **P1** | Excellent for multi-asset institutional workflows. Best experienced via QuantConnect cloud; local setup requires self-hosted data. |
| **Backtrader** | https://github.com/mementum/backtrader | Rich OOP API, indicators, analyzers, broker integrations | **Legacy / Archived** (no releases in years, Python 3.10+ issues) | **P3** | Avoid for new projects. Use PyBroker or Nautilus instead. |
| **bt** | https://github.com/pmorissette/ffn/tree/master/bt | Mature, stable, research-focused | **Mature / Stable** | **P2** | Good for portfolio-level research. No live trading. |
| **pysystemtrade** | https://github.com/robcarver17/pysystemtrade | Robert Carver's framework, IB-focused, position sizing | **Niche Active** | **P2** | Good if following Carver's systematic trading methodology. |

**Recommendation:** Use **VectorBT** (open source or PRO) for rapid signal discovery and parameter sweeps. Migrate validated strategies to **NautilusTrader** for execution-fidelity backtesting and live deployment. Use **PyBroker** if your edge is heavily ML-driven.

---

## 2. Risk Management / Portfolio Optimization

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **PyPortfolioOpt** | https://github.com/robertmartin8/PyPortfolioOpt | Mean-variance, max Sharpe, min volatility, Black-Litterman, CVaR, CLA, exponential cov | **Mature / Stable** (v1.5.4 docs) | **P0** | Industry standard for Python portfolio optimization. Uses cvxpy internally. Simple API. |
| **Riskfolio-Lib** | https://github.com/dcajasn/Riskfolio-Lib | 24 convex risk measures (CVaR, EVaR, MAD, drawdowns), risk parity, Black-Litterman, Kelly criterion, HRP | **Very Active** (v7.2.1, 2026; Python 3.9+, weekly updates) | **P0** | Superior to PyPortfolioOpt for advanced risk modeling. Best-in-class for hedge-fund risk frameworks. |
| **cvxpy** | https://github.com/cvxpy/cvxpy | Disciplined convex programming, multiple solvers (ECOS, SCS, OSQP, Clarabel, GUROBI) | **Active** | **P0** | Foundational dependency for Pypfopt and Riskfolio. Essential for custom optimization problems. |
| **PyPortOptimization** | https://github.com/rushikeshnakhate/PyPortOptimizationPipeline | Automated pipeline comparing methods, Monte Carlo robustness | **Research project** | **P3** | Interesting reference implementation, not a library dependency. |

**Recommendation:** **Riskfolio-Lib** is the best choice for hedge-fund quality portfolio construction due to its breadth of risk measures (drawdown-aware, tail-risk). **PyPortfolioOpt** is the easiest drop-in for Sharpe maximization. Both depend on **cvxpy**.

---

## 3. Statistical Analysis / ML for Finance

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **scikit-learn** | https://github.com/scikit-learn/scikit-learn | Classification, regression, clustering, cross-validation, pipelines | **Extremely Active** | **P0** | Non-negotiable baseline for any ML pipeline. |
| **PyCaret** | https://github.com/pycaret/pycaret | Low-code ML, automated preprocessing, model comparison, deployment | **Active** | **P1** | Great for rapid ML prototyping and benchmark model creation. |
| **TsFresh** | https://github.com/blue-yonder/tsfresh | Automatic time-series feature extraction, filtering | **Active** | **P1** | Excellent for generating features from price/volume time series. |
| **mlfinlab** | https://github.com/hudson-and-thames/mlfinlab | Triple-barrier labeling, meta-labeling, feature engineering, backtest overfitting (deflated Sharpe), synthetic data | **Commercial / Sponsorship model** | **P2** | Once the gold standard. Now behind a sponsorship paywall (~£100/mo/user). Code is high quality but licensing has shifted. Open-source forks exist (e.g., jmrichardson/mlfinlab) but are stale. |
| **arch** | https://github.com/bashtage/arch | GARCH, EGARCH, HARCH, volatility modeling, unit root tests | **Active** (v7.2+ required by Riskfolio) | **P1** | Essential for volatility forecasting and regime-aware position sizing. |
| **statsmodels** | https://github.com/statsmodels/statsmodels | Time-series analysis, ARIMA, cointegration, regression | **Active** | **P0** | Foundational for statistical arbitrage and factor modeling. |

**Recommendation:** Build pipelines on **scikit-learn** + **statsmodels**. Add **TsFresh** for automated feature engineering. Use **arch** for volatility models. **mlfinlab** is excellent if budget allows; otherwise implement triple-barrier and deflated Sharpe logic manually (well-documented in Lopez de Prado's literature).

---

## 4. Data Fetching

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **yfinance** | https://github.com/ranaroussi/yfinance | Yahoo Finance scraper, historical OHLCV, fundamentals, actions | **Active** | **P0** | Best free equity data source. Easy integration. Unofficial scraper so reliability varies. |
| **CCXT** | https://github.com/ccxt/ccxt | Unified API for 100+ crypto exchanges, REST + WebSocket, rate limiting | **Very Active** (v4.5.44, Mar 2026) | **P0** | Essential for multi-exchange crypto data and execution. Mature, well-documented. |
| **OpenBB Platform** | https://github.com/OpenBB-finance/OpenBBTerminal | Modular data platform, 30+ data providers (yfinance, FRED, Polygon, FMP, ECB), REST API, MCP server | **Very Active** (Python 3.10-3.13, Mar 2026) | **P0** | Best aggregation layer for free data. Install only the extensions you need. Has native AI/MCP integration. |
| **fredapi / pandas-datareader** | https://github.com/mortada/fredapi | FRED economic data wrapper | **Stable** | **P1** | Reliable for macro/interest rate data. |
| **luno-python** | https://github.com/luno/luno-python | Luno exchange wrapper | **Niche** | **P3** | Only if trading on Luno specifically. |

**Recommendation:** Use **OpenBB Platform** as your primary data orchestration layer. It normalizes access to yfinance, FRED, ECB, Polygon, etc. Use **CCXT** directly for crypto exchange-specific features (order book, funding rates). Use **yfinance** standalone for quick equity scripts.

---

## 5. Execution / Market Microstructure

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **Hummingbot** | https://github.com/hummingbot/hummingbot | Market making, arbitrage, cross-exchange, DEX/CEX connectors, StrategyV2, LP executor | **Very Active** (v2.14, 14k+ stars, 2025-2026 releases) | **P0** | Best open-source execution framework for crypto. Supports Binance, Hyperliquid, dYdX, Uniswap, etc. New Hummingbot API + MCP for AI agents. |
| **NautilusTrader** | (see above) | Live trading adapters for IB, Binance, Bybit, Hyperliquid, etc. | **Very Active** | **P0** | Best for research-to-live parity with realistic fill models. |

**Recommendation:** For crypto execution, **Hummingbot** is the standard for market-making and arbitrage. For systematic signal-based execution with rigorous backtest parity, **NautilusTrader** is superior.

---

## 6. Alternative Data / Sentiment

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **VADER** | https://github.com/cjhutto/vaderSentiment | Lexicon-based sentiment analysis, social media optimized | **Stable** (part of NLTK) | **P1** | Lightweight, no training required. Good for headline/tweet sentiment scoring. |
| **finnhub-python** | https://github.com/Finnhub-Stock-API/finnhub-python | News, sentiment, earnings calendars, fundamentals, WebSocket | **Active** | **P1** | Generous free tier. Good for event-driven signals. |
| **Alpha Vantage** | https://github.com/RomelTorres/alpha_vantage | 50+ technical indicators, news sentiment, fundamentals, MCP integration | **Active** | **P1** | Free tier: 25 req/day. Paid tiers from $49.99/mo. Best for indicator-heavy strategies. |
| **LunarCrush** | https://github.com/lunarcrush | Social listening, Galaxy Score, sentiment vs. price | **Freemium** | **P2** | Good for crypto social sentiment. Free tier limited. |

**Recommendation:** Use **VADER** for fast, free sentiment scoring on text. Use **Finnhub** for structured news and event data. **Alpha Vantage** is excellent if you need pre-computed technical indicators to save engineering time.

---

## 7. Regime Detection / HMM

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **hmmlearn** | https://github.com/hmmlearn/hmmlearn | Gaussian HMM, multinomial HMM, EM algorithm, filtering/smoothing | **Stable** (v0.3.0 used in 2026 research papers) | **P0** | Standard for hidden Markov model regime detection. Lightweight, sklearn-compatible. |
| **arch** | (see above) | Regime-switching models, volatility clustering | **Active** | **P1** | Complements hmmlearn with GARCH-based regime analysis. |

**Recommendation:** **hmmlearn** is the proven choice for regime detection (recent 2026 DeFi systemic risk papers use it). Combine with **arch** for volatility-regime fusion.

---

## 8. Probabilistic Sharpe / Drawdown Analysis

| Library | GitHub URL | Key Features | Maintenance 2026 | Priority | Notes |
|---------|-----------|--------------|------------------|----------|-------|
| **QuantStats** | https://github.com/ranaroussi/quantstats | Sharpe, Sortino, Calmar, max drawdown, Monte Carlo, tear sheets, HTML reports | **Active** (Monte Carlo added recently) | **P0** | The modern replacement for pyfolio/empyrical. Actively maintained by the yfinance author. |
| **pyfolio** | https://github.com/quantopian/pyfolio | Tear sheets, risk analysis, performance attribution | **Archived** (last release 2019) | **P3** | Dead project. Do not use in new code. |
| **empyrical** | https://github.com/quantopian/empyrical | Risk/return metrics, Fama-French loaders | **Archived** (Quantopian shutdown) | **P3** | Dead project. Migrate to QuantStats. |

**Recommendation:** **QuantStats** is the only actively maintained option. It covers all major metrics plus Monte Carlo simulations for probabilistic drawdown analysis.

---

## 9. Free Data Sources / APIs

### Crypto

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **Binance API** | https://binance.com/en/binance-api | 1200 weight/min, no key for public | 600+ pairs, spot + futures, order book, klines, funding rates | **P0** |
| **CoinGecko API** | https://www.coingecko.com/en/api | 10-50 calls/min, no key | 10,000+ coins, historical, exchange data, trending | **P0** |
| **CryptoCompare** | https://min-api.cryptocompare.com/ | Free tier available | 6,000+ coins, social metrics, news | **P1** |
| **LunarCrush** | https://lunarcrush.com/ | Free tier limited | Social sentiment, Galaxy Score | **P2** |

### Forex / Rates

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **FRED API** | https://fred.stlouisfed.org/docs/api/api_key.html | Free key required | US Treasury rates, economic indicators, employment, inflation | **P0** |
| **ECB Statistical Data Warehouse** | https://sdw.ecb.europa.eu/ | Free | EUR rates, FX reference rates, Euro area macro | **P1** |
| **Alpha Vantage Forex** | https://www.alphavantage.co/ | 25 req/day free | FX pairs, physical/digital currency rates | **P1** |

### Equities

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **yfinance** | (library above) | Free (scrapes Yahoo) | Global equities, ETFs, funds, historical + fundamentals | **P0** |
| **OpenBB Platform** | (library above) | Free (many connectors) | Aggregates yfinance, FRED, Polygon, FMP, SEC, etc. | **P0** |
| **Finnhub** | https://finnhub.io/ | 60 calls/min free | US equities, news, earnings, fundamentals, sentiment | **P1** |
| **Polygon.io** | https://polygon.io/ | Free basic plan | US equities, options, real-time + historical | **P1** |

### On-Chain

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **Glassnode** | https://glassnode.com/ | Limited metrics free | BTC/ETH on-chain, exchange flows, holder analysis | **P1** |
| **Dune Analytics** | https://dune.com/ | Free community tier (3 queries, dashboards) | SQL querying across 100+ chains, community dashboards | **P1** |
| **DeFiLlama** | https://defillama.com/ | Free | TVL, yields, fees, protocol metrics across chains | **P1** |
| **Arkham Intelligence** | https://arkhamintelligence.com/ | Free (Intel-to-Earn) | Wallet labeling, entity tracking, visualizer | **P2** |

### Sentiment / Alternative

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **Reddit API** | https://www.reddit.com/dev/api/ | Free tier (rate limited) | Subreddit posts, comments, sentiment raw data | **P1** |
| **Twitter/X API** | https://developer.twitter.com/en/products/twitter-api | Free basic tier limited | Tweets, engagement, search (heavily restricted now) | **P2** |
| **Google Trends** | https://trends.google.com/trends/explore | Free | Search interest by keyword, region, time | **P2** |

### Macro

| Source | URL | Free Tier | Coverage | Priority |
|--------|-----|-----------|----------|----------|
| **FRED** | (see above) | Free | US macro, Fed data, interest rates | **P0** |
| **World Bank Open Data** | https://data.worldbank.org/ | Free | Global development, GDP, trade, demographics | **P2** |
| **IMF Data** | https://data.imf.org/ | Free | Global financial stability, exchange rates, fiscal | **P2** |
| **OECD** | https://data.oecd.org/ | Free | Economic outlook, employment, inflation (mostly advanced economies) | **P2** |

---

## Integration Roadmap for findtorontoevents.ca / Audit Stack

### Immediate (Week 1-2)
1. **Replace pyfolio/empyrical with QuantStats** in all reporting pipelines.
2. **Adopt OpenBB Platform** as a data provider abstraction layer (install `openbb[yfinance,fred,fmp]`).
3. **Use yfinance + CCXT** directly for existing equity/crypto data pipelines.

### Short-term (Month 1)
4. **Add Riskfolio-Lib** for portfolio-level risk optimization in the audit dashboard.
5. **Integrate hmmlearn** for market regime detection (bull/bear/neutral classification).
6. **Add Glassnode + Dune** data pulls for crypto on-chain metrics in picks scoring.

### Medium-term (Quarter 1)
7. **Migrate backtesting to VectorBT** for rapid strategy evaluation (parameter sweeps).
8. **Evaluate NautilusTrader** for high-fidelity backtesting of top strategies before paper trading.
9. **Add Hummingbot** connectors if deploying market-making or arbitrage strategies live.

---

## Key Warnings & Deprecated Libraries

- **DO NOT use Backtrader** for new development. It is effectively archived.
- **DO NOT use pyfolio or empyrical.** They are Quantopian legacy projects abandoned in ~2019. Use **QuantStats**.
- **DO NOT rely on mlfinlab** without checking licensing. The open-source version was pulled behind a sponsorship model. Evaluate cost vs. reimplementing key algorithms (triple-barrier, deflated Sharpe).
- **Twitter/X API free tier** is heavily restricted as of 2025-2026. Reddit API is also increasingly rate-limited. Plan for paid tiers if sentiment is a core signal.

---

## Sources

- python.financial (2026 Backtesting Landscape)
- PyPortfolioOpt / Riskfolio-Lib documentation and GitHub
- NautilusTrader GitHub releases (v1.225, Apr 2026)
- Hummingbot GitHub releases (v2.14, 2025)
- CCXT changelog (v4.5.44, Mar 2026)
- OpenBB PyPI and documentation (Mar 2026)
- PyBroker releases (v1.2.12, Dec 2025)
- EODHD / API.market comparison articles (2026)
- Various on-chain tool guides (Glassnode, Dune, DeFiLlama)

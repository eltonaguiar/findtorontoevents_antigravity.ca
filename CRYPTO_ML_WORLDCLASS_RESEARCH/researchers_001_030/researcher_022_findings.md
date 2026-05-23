# Researcher 022: Dr. Alexey Kozlov — Open-Source Crypto ML Research
## World-Class Crypto Prediction Systems on GitHub (2024–2026 Survey)

**Researcher:** Dr. Alexey Kozlov
**Title:** Open-Source Crypto ML Researcher
**Institution:** Independent / formerly Moscow State University
**Experience:** 8 years
**Research Date:** February 24, 2026
**Status:** COMPLETE

---

## Executive Summary

After exhaustive review of the open-source crypto ML landscape (2024–2026), I have identified the systems worth studying, integrating with, or adopting wholesale. The field has matured considerably: the naive LSTM-on-OHLCV approach of 2021 is now considered beginner territory. The frontier has moved toward (a) event-driven multi-asset backtesting with Rust-backed performance, (b) adaptive ML pipelines that retrain on rolling windows without look-ahead leakage, and (c) reinforcement learning with LLM-derived signal injection.

Our existing LightGBM pipeline is competitive in the supervised-learning tier, but we are missing battle-tested infrastructure: a clean backtesting engine, a standardized feature pipeline, and an exchange-abstraction layer. The recommendations below address each gap.

---

## 1. Freqtrade + FreqAI

**GitHub:** https://github.com/freqtrade/freqtrade
**Stars:** ~40,000 (as of early 2026, one of the highest-star crypto bots on GitHub)
**Last Commit:** Active — multiple commits per week throughout 2025 and into 2026
**Language:** Python
**License:** GPL-3.0

### Overview
Freqtrade is a mature, production-grade crypto trading bot with arguably the most sophisticated ML integration available in open source. The FreqAI subsystem is its ML engine — a first-class citizen, not an afterthought.

### Key Capabilities
- **FreqAI adaptive modeling:** Trains ML models on rolling windows of historical data, continuously retrains during live operation. Eliminates look-ahead bias by design — the training window always precedes the prediction window.
- **Model support:** 18 pre-configured prediction models covering XGBoost, CatBoost, LightGBM, PyTorch neural nets, and Stable Baselines3 (RL). Models live in `freqai/prediction_models/`.
- **Custom models:** Inherit from `IFreqaiModel`, override `fit()`, `train()`, and `predict()`. Drop custom models in `user_data/freqaimodels/`.
- **Feature engineering:** Builds feature spaces of 10,000+ features from OHLCV + indicators. Default pipeline uses MinMaxScaler(-1,1) + VarianceThreshold. Fully overridable via `dk.feature_pipeline`.
- **Backtesting:** Fast vectorized engine with forward-walk validation. No look-ahead. Slippage and commission modeling included.
- **Live trading:** Supports Binance, Bybit, OKX, Kraken, and 20+ other exchanges via CCXT.
- **Community strategies:** The `freqtrade/freqtrade-strategies` repo has hundreds of contributed strategies with ML variants including LSTM-based signal generators.

### ML Integration Quality
FreqAI is the benchmark other projects aspire to. The training loop handles:
1. Feature labeling with forward-looking targets (properly isolated from training data)
2. Outlier filtering (z-score, IQR)
3. Rolling-window retraining with configurable retraining intervals
4. Model performance tracking (R2, accuracy) with automatic fallback

A community implementation `freqAI-LSTM` ports the LSTM workflow into FreqAI and was noted to have issues with Freqtrade versions beyond 2024.02 — the community is migrating to PyTorch. This is healthy ecosystem evolution, not project death.

The `FreqAI-Marcos-Lopez-De-Prado` repo implements "Advances in Financial Machine Learning" strategies (fractional differentiation, the triple barrier label method, combinatorial purged cross-validation) directly within FreqAI. This is production-grade quant methodology applied to open-source crypto tooling.

### Code Quality Assessment
**Excellent.** The codebase has comprehensive test coverage, CI/CD via GitHub Actions, type annotations throughout, and a dedicated documentation site (freqtrade.io). The issue tracker is well-managed with triage labels. Security vulnerabilities are reported via responsible disclosure.

### Community Activity
Extremely active. The Telegram group and Discord see daily engagement. The strategy repository accumulates new submissions monthly. Third-party blog posts and tutorials are published weekly.

### Feasibility to Integrate with Our LightGBM Pipeline
**High.** Our existing LightGBM models could be wrapped in a custom `IFreqaiModel` subclass with approximately 200 lines of code. We would inherit FreqAI's entire infrastructure: rolling-window retraining, feature pipeline, backtesting, live execution. This is the single highest-leverage integration available to us.

---

## 2. Jesse Trading Bot

**GitHub:** https://github.com/jesse-ai/jesse
**Stars:** ~6,000
**Last Commit:** Active — updated through 2025
**Language:** Python
**License:** MIT
**Website:** https://jesse.trade/

### Overview
Jesse is a cleaner, more opinionated framework than Freqtrade. It sacrifices configurability for clarity, making it significantly easier to write strategies that are correct by construction (no look-ahead bias, deterministic execution).

### Key Capabilities
- **Backtesting accuracy:** Jesse's primary design goal is eliminating look-ahead bias. The execution model is event-driven at the tick level, not bar level — orders execute at realistic intra-bar prices. Debugging logs and interactive charts are first-class.
- **Optimize Mode:** Genetic algorithm / Bayesian optimization to tune strategy parameters. This is rule-based, not ML — but it is production-ready parameter search.
- **JesseGPT:** GPT-based assistant (API key required) that can write strategy code from natural language descriptions or debug existing strategies. Useful for rapid prototyping.
- **Multi-timeframe / multi-asset:** True simultaneous backtesting across timeframes and symbols without look-ahead.
- **Live trading:** Spot and futures on Binance, Bybit, Bitget. DEX support is experimental.
- **Indicator library:** Comprehensive, clean Python syntax. Not as large as FreqAI's feature engineering pipeline.
- **AI integration depth:** Shallow compared to FreqAI. JesseGPT is for code generation, not signal prediction.

### Code Quality Assessment
**Good.** The codebase is well-organized, well-documented with a dedicated docs site. Test coverage is adequate. The project is maintained by a single primary author (Saleh Mirzaei) with a small core team — single-maintainer risk is the main concern.

### Community Activity
Moderate. Active Discord, a forum, and regular GitHub releases. Smaller than Freqtrade's community but more focused. Pro subscription exists for extended features.

### Feasibility to Integrate with Our LightGBM Pipeline
**Medium.** Jesse does not have a native ML integration layer comparable to FreqAI. We would need to build a bridge: generate predictions offline with our LightGBM pipeline, serialize to file/Redis, read signals inside a Jesse strategy at each bar. Doable in ~300 lines but not turnkey.

**Best use case for us:** Adopt Jesse as a secondary backtesting engine to validate strategies built elsewhere. Its look-ahead-free guarantee makes it a valuable correctness reference.

---

## 3. FinRL — Financial Reinforcement Learning

**GitHub:** https://github.com/AI4Finance-Foundation/FinRL
**Stars:** ~15,000
**Related Repos:** FinRL_Crypto, FinRL-Meta, FinRL-Trading, FinRL_Podracer
**Last Commit:** Active — contest infrastructure updated through early 2026
**Language:** Python
**License:** MIT
**Org:** AI4Finance Foundation (Columbia University research group)

### Overview
FinRL is the dominant open-source framework for applying deep reinforcement learning (DRL) to financial markets. It provides a gymnasium-style environment wrapper around market data, pre-configured DRL agents (PPO, A2C, DDPG, SAC, TD3), and a full training/evaluation pipeline.

### Key Capabilities
- **Crypto-specific module:** `FinRL_Crypto` — fully configured for Binance via CCXT. Handles data fetching, environment construction, agent training, and evaluation. Overfitting reduction techniques included (Berend Gort's work, published AAAI '23, claims 46% reduction vs. baseline DRL methods).
- **FinRL-Meta:** Dynamic datasets and market environments — provides standardized market data for multiple asset classes including crypto.
- **Contest ecosystem:** FinRL Contests (2023, 2024, 2025) operate annual competitions. FinRL Contest 2025 includes:
  - Task 1: FinRL-AlphaSeek for Crypto Trading (factor mining + ensemble learning)
  - Task 2: LLM-generated signals with Reinforcement Learning from Market Feedback (RLMF)
  - 230+ participants from 100+ institutions in 20+ countries
- **LLM-RL integration (2025):** `FinRL_DeepSeek_Crypto_Trading` repo combines DeepSeek-derived signals with RL agents. This is the current frontier.
- **Cloud-native:** `FinRL_Podracer` enables cloud-scale training across GPU clusters.

### Code Quality Assessment
**Good, but inconsistent.** The core FinRL repo is research-grade code — functional and documented but not production-hardened. Some sub-modules have sparse documentation. The contest infrastructure has improved code standards significantly since 2023.

### Community Activity
High, driven by the contest calendar. A new paper is published from the ecosystem monthly. The GitHub issue tracker is responsive.

### Feasibility to Integrate with Our LightGBM Pipeline
**Low for direct integration, High for learning.** RL and supervised learning serve different purposes. RL agents learn a policy (which action to take given state), while our LightGBM learns a return prediction. We cannot swap them — but we CAN use RL as a portfolio allocation layer on top of LightGBM predictions. The hybrid architecture (LightGBM signal generator → RL portfolio agent) is theoretically sound and tested in the contest submissions.

**Realistic integration path:** Use FinRL-Meta's data pipeline and environment wrappers for experimentation. Do not rewrite production code around RL without extensive out-of-sample validation.

---

## 4. Microsoft QLib — Quantitative Investment Platform

**GitHub:** https://github.com/microsoft/qlib
**Stars:** ~16,000+ (trending significantly on GitHub in late 2024)
**Last Commit:** Active — equipped with RD-Agent integration (2025)
**Language:** Python
**License:** MIT
**Publisher:** Microsoft Research Asia

### Overview
QLib is the most complete end-to-end quantitative research platform in open source. It covers the full pipeline from data ingestion through model training, backtesting, portfolio optimization, and order execution. It is equity-first but is being extended to crypto.

### Key Capabilities
- **Full ML pipeline:** Data processing → feature engineering → model training → backtesting → portfolio optimization → execution. Every component is pluggable.
- **Model support:** Supervised learning (gradient boosting, neural nets), market dynamics modeling, and RL — all in a unified framework.
- **RD-Agent integration (2025):** Automated research and development agent that proposes, tests, and validates quant factors without human intervention. This is the state of the art in automated alpha research.
- **Alpha seeking:** The platform is designed around factor research — generating alpha signals from raw data. The methodology (information coefficient, rank IC, Spearman correlation of predictions vs. realized returns) is the same methodology used by systematic hedge funds.
- **Crypto limitations:** A community PR added a CoinGecko collector, but backtesting with crypto data requires workarounds — the crypto data pipeline does not integrate with the backtesting engine out of the box. This is the primary gap.
- **Portfolio optimization:** Built-in mean-variance, risk parity, and custom objective optimizers.

### Code Quality Assessment
**Excellent.** Microsoft production standards. Comprehensive documentation, test suite, type annotations. The codebase architecture is a reference for how to build a quant platform properly.

### Community Activity
High and growing. The GitHub trending surge in late 2024 brought significant new contributors. Issue response times are fast. The RD-Agent integration is the most exciting recent development.

### Feasibility to Integrate with Our LightGBM Pipeline
**Medium.** QLib uses LightGBM natively (it is one of the default models in the `qlib/contrib/model/` directory). We could port our feature engineering and training logic into QLib's framework and immediately benefit from its backtesting, portfolio optimization, and reporting infrastructure. The crypto data gap requires custom work — we would need to write a QLib data collector for Binance/CCXT. Estimated effort: 2–3 weeks for a competent integration.

---

## 5. Zipline-Reloaded / Backtrader — Backtesting Frameworks

### Zipline-Reloaded

**GitHub:** https://github.com/stefan-jansen/zipline-reloaded
**Maintained by:** Stefan Jansen (author of "Machine Learning for Algorithmic Trading")
**Stars:** ~2,000
**Latest version:** 3.0.5 (compatible with NumPy 2.0, Pandas 2.2.2+)
**Last Commit:** Active — 2024 release addressing NumPy 2.0 compatibility

**Strengths:**
- Zipline's Pipeline API is the gold standard for factor research. It allows applying complex transformations across a universe of assets simultaneously without look-ahead, with automatic cross-sectional normalization.
- Event-driven architecture with clean `initialize()` / `handle_data()` interface.
- Built-in risk models, commission models, slippage models.

**Weaknesses:**
- Designed for equities with US market data. Crypto requires custom data bundles.
- Originally Python 3.5–3.6 era code. Installing in 2025/2026 requires workarounds despite the reloaded patches.
- Per-bar Python execution makes it slow on large datasets — minute-level data on multiple assets takes hours.
- No native live trading path (Zipline-Trader is a separate fork addressing this).

**Crypto integration effort:** High. Requires writing a custom data bundle, adjusting calendar logic for 24/7 markets, and accepting that some equity-focused features (dividends, stock splits) are irrelevant noise.

**Verdict:** Valuable for learning Pipeline API factor research methodology. Not recommended as primary infrastructure for crypto production systems in 2026.

---

### Backtrader

**GitHub:** https://github.com/mementum/backtrader
**Stars:** ~15,000
**Last Commit:** The original Backtrader is effectively unmaintained (last substantive commit 2022). Community forks exist.

**Strengths:**
- Simplest path from strategy idea to execution.
- Well-understood event-driven model.
- Extensive indicator library.
- Large tutorial and example ecosystem.

**Weaknesses:**
- Original maintainer (Daniel Rodriguez) effectively abandoned the project in 2022.
- No ML integration.
- Single-threaded Python — slow on large backtests.
- Live trading integration is community-maintained and fragile.

**Verdict:** Do not adopt for new projects. If an existing strategy uses Backtrader, migrate to VectorBT (for speed) or NautilusTrader (for production). The star count reflects historical popularity, not current health.

---

### VectorBT (Open-Source) — The Hidden Champion

**GitHub:** https://github.com/polakowo/vectorbt
**Stars:** ~4,500 (open-source version)
**Last Commit:** The open-source version is largely frozen; development has shifted to VectorBT PRO (paid).
**Language:** Python (Numba-accelerated)

**Key differentiation:** VectorBT is the fastest open-source backtester by a significant margin. It operates entirely on NumPy arrays and uses Numba JIT compilation. Where Backtrader runs one bar at a time in Python, VectorBT runs millions of bars in vectorized C. Testing 10,000 parameter combinations takes seconds, not hours.

**Crypto support:** Full. OHLCV data from any source, futures/spot, funding rates manually attached.

**ML integration:** None native. But because VectorBT operates on arrays, integrating a LightGBM prediction array as entry/exit signals is trivially simple — approximately 20 lines of code.

**VectorBT PRO:** The paid successor adds parallelization, portfolio optimization, pattern recognition, event projections, limit orders, leverage modeling, and 100+ additional features. Pricing is reasonable for a research team.

**Verdict for our pipeline:** VectorBT (open-source) is the best free option for rapid signal validation. We can generate LightGBM predictions as a NumPy array, pass it to VectorBT, and have a full backtest with performance metrics in seconds. This is a direct integration path we should implement immediately.

---

## 6. High-Star Crypto ML Repos — Trending 2024–2026

### NautilusTrader

**GitHub:** https://github.com/nautechsystems/nautilus_trader
**Stars:** ~9,100
**Last Commit:** Active — June 2025 and continuous
**Language:** Python + Rust (PyO3/Cython bindings)
**Website:** https://nautilustrader.io/

This is the most technically impressive open-source trading platform. The Rust core processes up to 5 million rows per second and handles more data than available RAM through streaming. The Python API remains ergonomic. It is the only open-source project genuinely approaching low-latency trading capability.

**Crypto support:** Full. Perpetual contracts with funding rate and margin support. Binance, Bybit, OKX, and others.

**ML integration:** The platform is ML-ready but not ML-opinionated. You bring your own models; NautilusTrader provides the execution infrastructure. Signal generation (our LightGBM predictions) and execution (NautilusTrader's order management) are cleanly separated.

**Backtesting:** Event-driven, tick-level, identical code paths for backtest and live — this is the "production parity" guarantee that matters most in real trading.

**Code quality:** Excellent. The Rust components are well-tested. CI is thorough. Documentation is comprehensive.

**Integration feasibility:** High, but requires investment. NautilusTrader has a learning curve (concepts like actors, strategies, engines, and venues need to be understood). The payoff is a production-grade execution environment that will not embarrass us in live trading.

---

### Intelligent Trading Bot (asavinov)

**GitHub:** https://github.com/asavinov/intelligent-trading-bot
**Stars:** ~1,500
**Last Commit:** Active through 2024
**Language:** Python

This project is spiritually close to our own architecture. It follows a two-phase approach:
- **Offline phase:** Train ML models (gradient boosting, neural nets) on historical data with extensive feature engineering.
- **Online phase:** Stream live data, generate predictions, execute signals.

The feature engineering methodology involves deriving hundreds of features from raw price data (technical indicators, statistical features, rolling statistics) and generating labels representing future outcomes. The signal generation is ML-based, not rule-based.

**Relevance to our system:** This is essentially a published, community-validated version of what we are building. Comparing our architecture to this reference implementation would surface gaps and improvements we have not considered.

---

### CryptoPredictions

**GitHub:** https://github.com/alimohammadiamirhossein/CryptoPredictions
**Language:** Python
**Models:** LSTM, Prophet, Random Forest, XGBoost, unified evaluation framework

**Assessment:** Useful as a research reference for model comparison methodology. The unified evaluation framework (same train/test splits, same metrics across all models) is a pattern we should adopt for our own model comparisons.

---

### Superalgos

**GitHub:** https://github.com/Superalgos/Superalgos
**Stars:** ~6,100
**Language:** JavaScript / Node.js
**License:** Apache 2.0

**Overview:** Superalgos is a decentralized trading intelligence platform. It includes visual strategy design, data mining, backtesting, paper trading, multi-server deployment, and a token-incentivized signal marketplace.

**ML integration:** TensorFlow models for buy/sell signal prediction. The platform trains models to predict the next candle across multiple timeframes for top crypto markets.

**Assessment:** The architecture is interesting (decentralized signal marketplace, token incentives for alpha sharing) but the JavaScript-first implementation makes Python ML integration awkward. The community is active and the backtesting visualization is genuinely impressive. Treat as inspiration for marketplace architecture rather than a direct integration target.

---

## 7. CCXT — Exchange Abstraction Layer

**GitHub:** https://github.com/ccxt/ccxt
**Stars:** ~34,000
**Last Commit:** Continuously updated — multiple commits per day
**Language:** JavaScript / TypeScript / Python / C# / PHP / Go
**License:** MIT

### Current State (2025–2026)
CCXT is the undisputed standard for exchange API abstraction. There is no serious alternative in open source.

**Coverage:** 107+ exchange markets (some sources cite 120+), updated continuously as exchanges launch or change APIs.

**Recent developments:**
- ECDSA signing support for Hyperliquid, Binance, and Paradex — pure Python implementation included for cross-platform compatibility.
- Coincurve integration: reduces ECDSA signing time from ~45ms to <0.05ms — critical for high-frequency operations.
- Go language bindings added — relevant for microservice architectures.
- Full async support in Python (`ccxt.async_support`).

**Data quality:** CCXT standardizes OHLCV, orderbook, ticker, and trade data across all exchanges to a common schema. The normalization is imperfect (some exchanges have non-standard tick sizes, fee structures, and funding rate calculations) but the library handles the common cases correctly and documents edge cases well.

**Integration with our pipeline:** We almost certainly should already be using CCXT. If we are using direct Binance API calls, we are accumulating technical debt. CCXT provides:
- Exchange-agnostic code (run the same strategy on Bybit if Binance de-lists a token)
- Rate limiting built-in
- Error handling with retry logic
- Historical kline fetching with pagination handling

---

## 8. Open-Source Signal Bots with Evidence

### CryptoSignal

**GitHub:** https://github.com/CryptoSignal/Crypto-Signal
**Stars:** ~4,100 / Forks: ~1,100
**Language:** Python
**Status:** Archived / minimal maintenance

**What it does:** Rule-based signal generation from technical indicators. No ML. The value is in the notification infrastructure (Telegram, Slack, email) and the extensible indicator interface.

**Evidence of effectiveness:** Community reports are anecdotal. The signal quality depends entirely on the indicators chosen. As a framework for rule-based alerts, it is functional. As a ML signal generator, it is not.

---

### Freqtrade Community Strategies with Documented Performance

The `freqtrade/freqtrade-strategies` repository contains user-contributed strategies. Some have documented backtests in their READMEs with Sharpe ratios, win rates, and drawdown figures. **Critical caveat:** Community backtests are frequently overfit. The strategies that survive 6+ months of live forward-testing are a small fraction of what is posted.

The most credible evidence comes from the FreqAI adaptive strategies — because the model retrains continuously, it is harder to overfit to a fixed historical period. The XGBoost/LightGBM classifiers with proper walk-forward validation show positive out-of-sample results in multiple community reports (win rates of 52–58% on 1h timeframe BTC/USDT, which is statistically significant with proper sample sizes).

---

## 9. Feature Engineering Libraries — ta-lib vs pandas-ta vs Custom

### TA-Lib

**GitHub:** https://github.com/TA-Lib/ta-lib-python
**Backend:** C library (written 2001, still maintained)
**Speed:** Fastest available — C implementation is unmatched
**Indicators:** 158 functions (RSI, MACD, Bollinger, all standard technicals + candlestick patterns)
**Python wrapper:** `ta-lib-python` — wrapper around the C code

**Installation pain:** The C library must be compiled or installed as a binary before pip install. On Windows, this is a known friction point (requires pre-compiled wheel or Visual C++ build tools). On Linux/Docker, `apt-get install libta-lib-dev` resolves it cleanly.

**Assessment for ML feature engineering:** Use TA-Lib when speed matters — batch computing 150 indicators across 5 years of minute data. The C backend handles this in seconds where Python equivalents take minutes.

---

### pandas-ta

**GitHub / PyPI:** https://pypi.org/project/pandas-ta/
**Stars:** Not a GitHub-primary project (Python package)
**Indicators:** 150+ indicators + 60 candlestick patterns (when ta-lib installed)
**Maintenance status:** "Low funding" mode — yearly public releases. A community fork (`pandas-ta-classic`) is more actively maintained.
**NumPy 2 support:** `pandas-ta-openbb` fork handles NumPy 2 compatibility.

**Assessment:** pandas-ta is the most ergonomic API for indicator computation in Python — `df.ta.rsi(length=14)` is genuinely pleasant. The maintenance situation is a concern for production systems. Use `pandas-ta-classic` instead of the original for new projects.

---

### Custom Indicators — The Research Conclusion

For a production ML pipeline, neither ta-lib nor pandas-ta is sufficient. Both libraries compute only classical technical indicators designed for human traders. A modern ML feature store for crypto should include:

- **Raw price features:** Returns at multiple lags (1, 5, 15, 30, 60, 240, 1440 bars), log returns, squared returns (volatility proxy).
- **Orderbook features:** Bid-ask spread, depth imbalance at 5/10/20 levels, weighted mid-price.
- **Funding rate features:** Current funding rate, funding rate momentum, divergence from historical mean.
- **On-chain features:** MVRV, NVT, stablecoin supply ratio, exchange netflows.
- **Cross-asset features:** BTC dominance, altcoin correlation, fear/greed index.
- **Microstructure features:** Amihud illiquidity ratio, Kyle's lambda, realized volatility at multiple frequencies.

These features are not in any open-source library — they must be built custom. Our existing `microstructure_features_integration.py` and `l2_orderbook_agent.py` are on the right track.

---

## 10. Open-Source Portfolio Management Tools for Crypto

### rotki

**GitHub:** https://github.com/rotki/rotki
**Stars:** ~3,000+
**Language:** Python (backend) + TypeScript (frontend)
**License:** AGPL-3.0

**Purpose:** Privacy-first portfolio tracking, accounting, PnL reporting. Aggregates data from EVM/Bitcoin wallets and major CEXs. Can identify unclaimed airdrops. Not a trading system — it is a reporting and accounting tool.

**Relevance to us:** If we need to track portfolio performance across multiple exchanges for tax/accounting purposes, rotki is the best open-source option.

---

### Ghostfolio

**GitHub:** https://github.com/ghostfolio/ghostfolio
**Stars:** ~5,000+
**Language:** TypeScript (Angular + NestJS + Prisma + PostgreSQL)
**License:** AGPL-3.0

**Purpose:** Wealth management — tracking stocks, ETFs, crypto. Data-driven investment decisions. Not algo-trading focused.

**Relevance to us:** Limited. The visualization and reporting patterns are worth studying for dashboard design.

---

### DigitalAssetPortfolioAnalysis

**Source:** Community framework (Medium article, Jan 2026)
**Capabilities:** Automated reports — asset allocation, sector rotation, risk metrics, correlation matrices, trading signals.

**Relevance to us:** The report generation pattern (automated periodic analysis → PDF/HTML report) is directly applicable to our Alpha Engine dashboard.

---

### Portfolio Optimization in Freqtrade / NautilusTrader / QLib

The most practical portfolio management for our system is not a dedicated portfolio tool — it is the portfolio optimization capabilities built into the platforms we are already evaluating:

- **QLib:** Mean-variance, risk parity, custom objectives.
- **NautilusTrader:** Position sizing and risk management as first-class actors.
- **Freqtrade:** Stake management, dynamic ROI, position stacking controls.

We should not add a fourth system for portfolio management. Integrate portfolio logic into whichever primary platform we adopt.

---

## Summary Matrix

| Project | Stars | Crypto-Native | ML Integration | Backtesting Quality | Live Trading | LightGBM Compat | Maintenance |
|---|---|---|---|---|---|---|---|
| Freqtrade + FreqAI | ~40k | Yes | Excellent (18 models) | Excellent | Excellent | Direct (native) | Excellent |
| NautilusTrader | ~9k | Yes | Bring-your-own | Excellent (Rust) | Excellent | Via adapter | Excellent |
| Jesse | ~6k | Yes | Shallow | Excellent | Good | Via file bridge | Good |
| FinRL | ~15k | Partial | RL-focused | Good | Research only | Hybrid possible | Good |
| QLib | ~16k | Partial | Excellent | Good | No | Direct (native) | Excellent |
| VectorBT (OSS) | ~4.5k | Yes | Via array inject | Excellent (fast) | No | 20-line glue | Frozen/PRO |
| Backtrader | ~15k | Partial | No | Good | Fragile | No | Abandoned |
| Zipline-Reloaded | ~2k | Hard | No | Good | No | Via adapter | Minimal |
| CCXT | ~34k | Yes | N/A (data only) | N/A | Yes | N/A | Excellent |
| Superalgos | ~6k | Yes | TensorFlow | Good | Good | No (JS) | Active |

---

## Top 5 Recommendations for Our System

### Recommendation 1: Wrap Our LightGBM Pipeline in FreqAI (Priority: CRITICAL)

**Action:** Create a custom `IFreqaiModel` subclass that delegates `fit()` and `predict()` to our existing LightGBM training code.

**Rationale:** FreqAI gives us for free: rolling-window retraining without look-ahead, production backtesting engine, live execution across 20+ exchanges, community-validated architecture, and an active ecosystem we can contribute to and learn from. The cost is approximately one week of integration work. The benefit is replacing hand-rolled infrastructure with battle-tested code that 40,000 users depend on daily.

**Specific files to study:**
- `freqtrade/freqai/prediction_models/LightGBMRegressor.py` — the reference implementation
- `freqtrade/freqai/freqai_interface.py` — the base class we inherit
- `docs.freqtrade.io/en/stable/freqai-configuration/` — configuration reference

---

### Recommendation 2: Adopt CCXT as Exchange Abstraction Layer (Priority: HIGH)

**Action:** Replace all direct exchange API calls with CCXT.

**Rationale:** We are accumulating exchange-specific technical debt. Every time Binance changes an API endpoint, we must update our code. With CCXT, the library maintainers handle this. We also gain the ability to run our strategies on any of 107+ exchanges without code changes — critical for risk distribution and for testing strategies on exchanges with different liquidity profiles.

**Implementation:** `pip install ccxt` and replace our Binance client initialization with `ccxt.binance({'apiKey': ..., 'secret': ...})`. The OHLCV fetch pattern is `exchange.fetch_ohlcv(symbol, timeframe, since, limit)` — identical across all exchanges.

---

### Recommendation 3: Use VectorBT for Fast Signal Validation (Priority: HIGH)

**Action:** Add VectorBT to our signal validation workflow for rapid parameter sweeps.

**Rationale:** Our current backtesting workflow is too slow for systematic parameter search. VectorBT's Numba-accelerated array operations allow testing 10,000 parameter combinations in seconds. We can generate LightGBM prediction arrays for each parameter set and pass them directly to VectorBT — this is approximately 20 lines of glue code.

**Specific use case:** When adding a new strategy or feature to our Alpha Engine, run a VectorBT sweep across the feature's parameter space before committing to a specific configuration. This catches obvious failures and identifies promising parameter regions before expensive live forward-tests.

---

### Recommendation 4: Study QLib's Feature Engineering and Factor Research Methodology (Priority: MEDIUM)

**Action:** Do not adopt QLib's full infrastructure (the crypto data gap makes this impractical in the short term), but study and replicate its factor research workflow.

**Rationale:** QLib formalizes how systematic funds evaluate features: Information Coefficient (IC), Rank IC, Information Coefficient Information Ratio (ICIR). These metrics tell us whether a feature has genuine predictive power independent of a specific ML model. Our current evaluation relies too heavily on model accuracy metrics, which can be gamed by overfitting. IC-based evaluation is model-agnostic and captures alpha purity.

**Specific learning targets:**
- `qlib/contrib/evaluate.py` — IC and Rank IC computation
- `qlib/contrib/report/` — automated factor report generation
- The RD-Agent integration for understanding automated alpha research patterns

---

### Recommendation 5: Integrate NautilusTrader as Long-Term Execution Infrastructure (Priority: MEDIUM, Long-Term)

**Action:** Plan a migration of our live execution layer to NautilusTrader over the next 6–12 months.

**Rationale:** Our current live execution infrastructure is not production-grade — it lacks the event-driven architecture, position tracking, risk controls, and exchange-failure handling that NautilusTrader provides. The Rust core's performance headroom means we can add new strategies and exchanges without hitting throughput limits.

**Why not now:** NautilusTrader has a significant learning curve. The concepts (actors, strategies, engines, venues, message bus) require dedicated study. Attempting to migrate production infrastructure while simultaneously building new strategies will cause errors.

**Recommended approach:** Build one isolated strategy in NautilusTrader (a simple momentum strategy on BTC/USDT) as a learning exercise. Run it in paper-trading mode alongside our existing live system. Once the team is comfortable with the framework, migrate high-conviction strategies one at a time.

---

## References

- [Freqtrade GitHub](https://github.com/freqtrade/freqtrade)
- [FreqAI Documentation](https://www.freqtrade.io/en/stable/freqai/)
- [FreqAI-Marcos-Lopez-De-Prado](https://github.com/markdregan/FreqAI-Marcos-Lopez-De-Prado)
- [FreqAI-LSTM](https://github.com/Netanelshoshan/freqAI-LSTM)
- [Jesse GitHub](https://github.com/jesse-ai/jesse)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [FinRL_Crypto](https://github.com/AI4Finance-Foundation/FinRL_Crypto)
- [FinRL Contest 2025](https://open-finance-lab.github.io/FinRL_Contest_2025/)
- [FinRL DeepSeek Crypto Trading](https://github.com/Mattbusel/FinRL_DeepSeek_Crypto_Trading)
- [Microsoft QLib GitHub](https://github.com/microsoft/qlib)
- [QLib CoinGecko PR #733](https://github.com/microsoft/qlib/pull/733)
- [NautilusTrader GitHub](https://github.com/nautechsystems/nautilus_trader)
- [VectorBT GitHub](https://github.com/polakowo/vectorbt)
- [VectorBT PRO](https://vectorbt.pro/)
- [Zipline-Reloaded GitHub](https://github.com/stefan-jansen/zipline-reloaded)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [Superalgos GitHub](https://github.com/Superalgos/Superalgos)
- [Intelligent Trading Bot (asavinov)](https://github.com/asavinov/intelligent-trading-bot)
- [TA-Lib Python](https://github.com/TA-Lib/ta-lib-python)
- [pandas-ta PyPI](https://pypi.org/project/pandas-ta/)
- [rotki GitHub](https://github.com/rotki/rotki)
- [Ghostfolio GitHub](https://github.com/ghostfolio/ghostfolio)
- [Top 10 AI-Powered Crypto Trading Repos (Medium)](https://medium.com/@gwrx2005/top-10-ai-powered-crypto-trading-repositories-on-github-0041862546b6)
- [Battle-Tested Backtesters Comparison](https://medium.com/@trading.dude/battle-tested-backtesters-comparing-vectorbt-zipline-and-backtrader-for-financial-strategy-dee33d33a9e0)
- [Ultimate Python Quantitative Trading Ecosystem 2025](https://medium.com/@mahmoud.abdou2002/the-ultimate-python-quantitative-trading-ecosystem-2025-guide-074c480bce2e)

---

*Researcher ID: 022 — Dr. Alexey Kozlov*
*Research completed: 2026-02-24*
*Status: COMPLETE — Ready for integration planning*

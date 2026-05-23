# Antigravity Trading System — Repository Structure Map

**Last Updated:** April 12, 2026  
**Project:** FindTorontoEvents Antigravity — Multi-Asset AI Trading Platform  
**Purpose:** Systematic inventory of codebase organization, data flow, and modular architecture

---

## Executive Overview

This is an **enterprise-scale quantitative trading system** with:
- **~3,500+ Python files** across domain-specific directories
- **Multi-asset coverage**: Crypto, Forex, Stocks, Commodities, Futures, Indices, Options
- **Multiple strategy engines**: Alpha Engine, Baby Strategies, Multi-Asset, DNA mutations
- **Real-time execution**: Paper trading, live picks, automated scoring
- **Advanced ML/AI**: LGBM ensemble, consensus models, prediction markets
- **Complex data pipeline**: 50+ data providers, feature engineering, validation gates
- **CI/CD automation**: 50+ GitHub workflows, continuous strategy testing

---

## 1. CORE DIRECTORY STRUCTURE

### Root Organization
```
c:\findtorontoevents_antigravity.ca/
├── alpha_engine/               ← Main strategy execution (600+ files)
├── baby_strategies/            ← Simplified strategy suite (150+ files)
├── multi_asset/                ← Cross-asset strategies (15 files)
├── audit_dashboard/            ← Quality auditing UI (45 files)
├── data_pipeline/              ← Data processing & validation (100+ files)
├── tests/                       ← Playwright, pytest, E2E tests (150+ files)
├── config/                      ← JSON configuration files (18 files)
├── docs/                        ← Research & strategy docs (200+ files)
├── data/                        ← Cached data, databases
├── tools/                       ← Utility scripts & helpers (150+ files)
├── strategies/                  ← Shared strategy definitions (7 files)
├── scripts/                     ← Operational scripts
├── .github/workflows/           ← CI/CD automation (50+ YAML files)
├── .claude/                     ← Claude agent skills & config
├── pinescripts/                 ← Pine Script indicators (50+ files)
├── tradingview-mcp/            ← TradingView integration
└── [100+ analysis/audit scripts at root]
```

---

## 2. KEY DIRECTORIES — DETAILED BREAKDOWN

### 2.1 Alpha Engine (~620+ Python files)

The **primary strategy execution engine** — generates picks, backtests, and manages portfolio risk.

#### Structure:
```
alpha_engine/
├── core/
│   ├── config.py              — Global configuration loader
│   ├── database.py            — MySQL connector, schema management
│   ├── api_bridge.py          — Multi-exchange API failover
│   ├── api_failover.py        — Binance failover chain
│   └── indicators.py          — Technical indicators (SMA, EMA, RSI, MACD, etc.)
│
├── backtest/                  ← Backtesting framework
│   ├── backtest_bridge.py
│   ├── backtest_multi_strategy.py
│   ├── backtest_*.py          (30+ backtest variants)
│   └── [monte_carlo, walk_forward, optimization utilities]
│
├── strategies/                ← Strategy implementations
│   ├── crypto_strategies.py   (ETH, BTC, alts)
│   ├── forex_strategies.py    (Majors, crosses)
│   ├── equity_strategies.py   (Stocks, sectors, earnings drift)
│   ├── commodity_strategies.py (Futures: XAU, WTI, etc.)
│   ├── futures_strategies.py  (Micro-futures, indices)
│   ├── etf_strategies.py
│   ├── options_signals.py     (Volatility, spreads)
│   ├── PropTrader_*.py        (Prop firm challenge strategies)
│   ├── Justin*.py             (Justin Bravo variants - EMA-based momentum)
│   ├── Hoffman*.py            (Hoffman elite strategies)
│   ├── Kimi*.py               (Kimi Claw indicators + variants)
│   └── [200+ custom strategy files]
│
├── ensemble/                  ← Signal aggregation & consensus
│   ├── meta_ensemble.py       (Multi-model voting)
│   ├── consensus_tier.py      (Consensus accuracy)
│   ├── confluence_engine.py   (Signal confluence)
│   ├── dynamic_ensemble.py    (Adaptive weighting)
│   └── [signal combination utilities]
│
├── risk_controls/             ← Portfolio risk management
│   ├── portfolio_circuit_breaker.py
│   ├── risk_controls.py
│   ├── dynamic_risk.py
│   ├── portfolio_correlation_guard.py
│   ├── regime_detector.py     (Market regime classification)
│   ├── regime_router.py       (Route picks by regime)
│   └── [drawdown, VaR, Kelly sizing]
│
├── scoring/                   ← Pick quality scoring
│   ├── elite_scorer.py        (High-quality pick scoring)
│   ├── scoring_enhancement.py
│   ├── hc_filter.js           (High conviction filter)
│   ├── meta_consensus_scorer.py
│   ├── trust_score.py         (Strategy trust ranking)
│   └── [reputation, track record, conviction tiers]
│
├── ml/                        ← Machine learning models
│   ├── ml_ranker.py           (LightGBM ensemble ranker)
│   ├── ml_predictor_merger.py (Model voting)
│   ├── lstm_price_predictor.py
│   ├── ml_strategy_reviver.py (Resurrect dead strategies)
│   ├── pattern_predictor.py   (CNN-lite patterns)
│   └── [Kalman filters, HMM, Bayesian models]
│
├── data/                      ← Data ingestion & features
│   ├── crypto_feature_pipeline.py
│   ├── feature_populator.py   (Build OHLCV features)
│   ├── backfill_*.py          (Historical data population)
│   ├── feature_health.py      (Feature freshness monitoring)
│   └── [120+ data enrichment scripts]
│
├── utils/                     ← Utilities & helpers
│   ├── calendar_anomalies.py  (Day-of-week, holiday effects)
│   ├── candlestick_patterns.py
│   ├── monte_carlo.py         (Risk simulation)
│   ├── slippage_model.py      (Execution cost modeling)
│   ├── kelly_position_sizer.py
│   ├── transaction_costs.py
│   └── [validation, sanitization, debug tools]
│
├── execution/                 ← Trade execution & monitoring
│   ├── dashboard_pick_trader.py
│   ├── live_market_test_results_*.py
│   ├── forward_test_portfolios.py
│   ├── paper_trading/         (Paper trading trackers)
│   └── [live execution logging, monitoring]
│
├── mutations/                 ← Strategy evolution & testing
│   ├── dna_mutations.py       (DNA-style parameter mutation)
│   ├── dna_mutation_engine.py (Genetic algorithm)
│   ├── strategy_mutations.py  (Generic mutation framework)
│   ├── strategy_mutator.py    (Apply mutations)
│   └── [emergency mutations, rehab protocols]
│
├── reporting/                 ← Performance reporting
│   ├── daily_report.py
│   ├── performance_benchmarks.py
│   ├── track_record.py
│   ├── tldr_winner_report.py
│   └── [Excel exports, metrics, P&L]
│
├── tests/                     ← Unit & integration tests
│   └── [~50 test files validating strategies, risk gates]
│
├── new_strategies/            ← Incubator for experimental strategies
│   ├── commodities_mean_reversion.py
│   ├── crypto_altcoin_volume_surge.py
│   ├── forex_ema_trend_momentum.py
│   ├── indices_seasonal_vwap.py
│   ├── futures_regime_momentum.py
│   └── [40+ new research strategies, pre-production]
│
└── scripts/                   ← Operational runners
    ├── smart_picks_engine.py  (Main production pick generator)
    ├── check_active_picks.py  (Monitor live positions)
    ├── deploy_*.py            (Deployment automation)
    └── [registry management, health checks]
```

**Key Statistics:**
- **Strategy files:** ~250+ individual strategy implementations
- **Backtesting files:** 40+ backtest runners (historical, walk-forward, Monte Carlo)
- **Data pipeline:** 120+ data enrichment/ingestion scripts
- **ML models:** 20+ ensemble/ranking/prediction models
- **Total Python files:** 620+

**Execution Entry Points:**
- `smart_picks_engine.py` — Main production runner
- `check_active_picks.py` — Live trade monitoring
- `forward_test_portfolios.py` — Paper trading
- `battle_test.py` — Strategy competition/validation

---

### 2.2 Baby Strategies (~155 Python files + meta.json files)

**Simplified, validated strategy variants** — high-conviction, easier to audit, lower code complexity.

#### Structure:
```
baby_strategies/
├── bundle_optimized/          ← Pre-built formula bundles
│   └── [optimized strategy combinations]
│
├── data/                       ← Strategy-specific caching
│
├── Adaptive Bollinger Momentum.py
├── Adaptive Regime Wrapper.py
├── ADX Range Mean Reversion.py
├── Bollinger Mean Reversion.py
├── Carter Squeeze Breakout.py
├── Connors RSI2, R3, R4...py  ← Classic mean reversion variants
├── Donchian Turtle.py         ← Breakout classic
├── EMA Cloud Strategies.py    ← Trend following
├── Heikin Ashi Trend Rider.py
├── Keltner Channel Variants.py
├── Kimi Claw Variants.py      ← Institutional-grade
├── Leaderboard Winners*.py    ← Proven performers
├── LGBM Ensemble.py           ← ML-backed strategies
├── Liquidation Cascade*.py    ← Crypto-specific
├── Mean Reversion Zscore.py
├── Multi-Timeframe Confluence.py
├── Prop Firm Classics.py      ← FX/Spot proven winners
├── Price ROC Variants.py      (6 ROC-based strategies)
├── RSI Divergence Scalper.py
├── Scale Free Momentum.py
├── Simpleton Signals.py       ← Simple, robust signals
├── Stochastic RSI Divergence.py
├── Supertrend Variants.py     ← Trend + volatility
├── Triple Crown.py
├── Volume Profile Deviation.py
├── VWAP RSI Institutional.py
├── Williams R Variants.py
└── [150+ total baby strategies]

Key features:
- Each has .meta.json companion file with backtest results
- Conservative risk parameters
- Forward-tested on live paper trading
- Audit-friendly (simpler code than alpha_engine equivalents)
```

**Key Statistics:**
- **Strategy count:** 150+
- **Backtest results:** JSON-serialized for every strategy variant
- **Framework:** Simple entry/exit logic, minimal preprocessing
- **Use case:** Conservative portfolios, audit requirements, regulatory compliance

---

### 2.3 Multi-Asset ($5-$10K per trade exposure)

**Cross-asset strategies** — equities, commodities, indices, forex in one model.

#### Files:
```
multi_asset/
├── commodity_futures_strategies.py
├── enhanced_strategies.py
├── equity_strategies.py
├── forex_strategies.py
├── institutional_picks_engine.py
├── scanner.py
├── monte_carlo_validator.py
├── dna_evolver.py
└── dashboard.html

Focus: Hedge fund-style portfolio construction
```

---

### 2.4 Data Pipeline (~105+ Python files)

**Data acquisition, transformation, and validation** — feeds all strategy engines.

#### Structure:
```
data_pipeline/
├── API Layer:
│   ├── Binance (api, api1, api2, api3)
│   ├── CoinGecko
│   ├── KuCoin
│   ├── CryptoCompare
│   ├── Alpha Vantage
│   ├── FRED (macro)
│   ├── Yahoo Finance
│   ├── Polygon.io
│   ├── Arkham (on-chain)
│   ├── LunarCrush (sentiment)
│   ├── Finnhub (news events)
│   ├── CoinPanic
│   ├── ByBit, Bitget, OKX
│   └── [20+ other providers]
│
├── Feature Engineering:
│   ├── OHLCV features (volume, returns, volatility)
│   ├── Technical indicators (RSI, MACD, Ichimoku, etc.)
│   ├── Microstructure (order flow, bid-ask spread)
│   ├── On-chain metrics (address concentration, whale activity)
│   ├── Sentiment scores (social, news, funding)
│   ├── Macro overlays (DXY, VIX, MOVE index)
│   └── Cross-asset correlations
│
├── Live Ingestion:
│   └── live_ingest.py  ← Real-time pick streaming
│
├── Data Quality:
│   ├── feature_health.py (Monitor staleness)
│   ├── data_coverage_enforcer.py
│   ├── statistical_validator.py
│   └── [anomaly detection, gap filling]
│
└── Backfill/Maintenance:
    ├── backfill_ohlcv_features.py
    ├── backfill_ml_features.py
    ├── backfill_new_symbols.py
    └── [incremental data repopulation]
```

**Data Storage:**
- MySQL for trade logs, picks, backtest results
- SQLite for lightweight features
- Parquet files for historical OHLCV
- JSON cache for real-time quotes
- Redis for live data bus

---

### 2.5 Audit Dashboard (~45 files)

**Real-time quality monitoring and performance visualization.**

#### Structure:
```
audit_dashboard/
├── template.html              ← Master template (shared by teams)
├── index.html                 ← Generated dashboard
├── blueprint_generator.py     ← Auto-generate from data
├── analyze_quality.py
├── check_perf.py
├── check_top_picks_outcome.py
├── matrix_analyzer.py
├── parse_portfolios.py
├── verify_portfolio_integrity.py
├── data/                      ← Dashboard data exports
├── hyrotrader/                ← Hyrotrader paper portfolio tracking
├── [matrix scores, hidden gems analysis, top/bottom performers]
└── documentation/
    ├── antigravity_picks_methodology.md
    ├── CLAUDE_TOP_PICKS_METHODOLOGY.md
    ├── WORLD_CLASS_ROADMAP.md
    └── [methodology docs, findings]
```

**Displays:**
- **Tier 1 picks** (highest conviction top 10)
- **Active open positions** with P&L
- **Score breakdown** (alpha, risk, ML, regime)
- **Strategy performance matrix** (win rate, Sharpe, max DD)
- **Hidden gems** (emerging winners)
- **Correlation heatmaps**
- **Risk metrics** (portfolio VaR, correlation with index)

---

### 2.6 Tests (~155 files: Playwright + Pytest)

**E2E, integration, and unit testing.**

#### Breakdown:
```
tests/
├── Playwright E2E (TypeScript/JS):
│   ├── audit_dashboard_*.spec.ts
│   ├── favcreators_*.spec.ts
│   ├── full_site_js_errors.spec.ts
│   ├── fps-v5-*.spec.ts
│   ├── local_root_main_site.spec.ts
│   ├── no_js_errors.spec.ts
│   ├── [~80 Playwright specs for UI/web coverage]
│   └── config: playwright.config.ts, competition.config.ts
│
├── Python / Pytest:
│   ├── test_asset_class.py
│   ├── test_conviction_stack.py
│   ├── test_data_quality.py
│   ├── test_elite_scorer.py
│   ├── test_ensemble_calibration.py
│   ├── test_forward_gates.py
│   ├── test_hf_quality_gate.py
│   ├── test_matrix_symbol_gates.py
│   ├── test_picks_pipeline.py
│   ├── test_quality_gates.py
│   ├── test_regime_direction_gate.py
│   ├── test_strategy_registry.py
│   ├── [~75 Python test files]
│   └── conftest.py (pytest configuration)
│
└── test_data/
    ├── sample portfolios
    ├── mock market data
    └── fixtures/
```

---

### 2.7 Configuration Files (~18 JSON files)

**All in `config/` directory — tunable parameters for gates, scoring, risk.**

```
config/
├── asset_class_map.json       ← Asset class definitions
├── drift_params.json          ← Concept drift detection thresholds
├── feature_flags.json         ← A/B test toggles
├── hc_gate_params.json        ← High conviction filter settings
├── hf_*.json                  ← Hedge fund quality gate params (3 files)
├── institutional_strategy_matrix.json
├── mega_strategies_integration.json
├── portfolio_mandate.json     ← Risk exposure limits
├── regime_direction_gates.json
├── risk_policy.json           ← Position sizing, stop loss rules
├── score_component_calibration.json
├── scoring_enhancement.json   ← ML score tuning
├── symbol_danger_long.json    ← Blacklist/avoid symbols
└── thresholds.json            ← Global decision thresholds
```

---

### 2.8 Documentation (~200+ Markdown files)

**Research papers, strategy guides, audit reports, roadmaps.**

#### Key Categories:

**Strategy Research:**
- `100_ALGORITHMS_MASTER_CATALOG.md` — Complete strategy inventory
- `25_Quantitative_Trading_Algorithms.md`
- `academic_trading_strategies.md`
- `top_50_hedge_fund_strategies.md`
- `ml_trading_algorithms.md`

**Institutional/Hedge Fund Focus:**
- `DEFINITIVE_HEDGE_FUND_PIPELINE.md`
- `INSTITUTIONAL_ALPHA_REPORT_2026-04-06.md`
- `HEDGE_FUND_QUALITY_ROADMAP.md`
- `prop_trading_firms_research.md`

**Asset Class Guides:**
- `CRYPTOCURRENCY_PREDICTION_RESEARCH_AGENT.md`
- `forex_scalping_strategies_report.md`
- `forex_quant_strategies_report.md`
- `stock_market_legends_research.md`
- `etf_strategy_catalog.md`

**Technical Papers:**
- `RESEARCH_KELLY_AND_SLIPPAGE.md`
- `SMC_TRADING_GUIDE_2025_2026.md`
- `HFT_vs_Swing_Trading_Analysis_2025-2026.md`
- `DEEP_RESEARCH_MARKET_MICROSTRUCTURE.md`

**Operational Guides:**
- `TRADINGVIEW_MCP_GUIDE.md` — TradingView integration guide
- `TRADING_GUIDE.md` — How to deploy strategies
- `TESTING_PROTOCOL.MD` — Testing best practices
- `SAFE_TRADING_PROTOCOL.md` — Risk management manual

**System Architecture:**
- `.planning/codebase/*.md` — Technical architecture docs
- `SYSTEM_AUDIT_COMPREHENSIVE.md`
- `DEPLOYMENT_STATUS.md`

**Audit Reports** (60+ files):
- Daily/weekly audit reports with strategy performance breakdowns
- Score calibration audits
- Edge analysis reports
- High conviction filter validation

---

### 2.9 GitHub Workflows (50+ YAML files)

**Continuous integration and automation** in `.github/workflows/`

#### Major Workflows:

**Daily/Hourly Picks Generation:**
- `alpha-engine-daily-picks.yml` — Generate daily picks
- `alpha-engine-live.yml` — Real-time pick generator
- `alpha-engine-fast.yml` — Quick iteration version
- `2hour_challenge.yml` — 2-hour scalping challenge

**Strategy Management:**
- `algorithm-competition-refresh.yml` — Test new strategies
- `battleground-mass-backtest.yml` — Parallel backtest batches
- `backtest-and-deploy.yml` — Build → test → deploy pipeline

**Paper Trading:**
- `asterdex-paper-trading.yml`
- `baby-strat-forward-paper.yml`
- `claudes-test-portfolios.yml`

**Data & Monitoring:**
- `audit-dashboard.yml` — Refresh audit dashboard
- `alpha-verify-predictions.yml` — Validate model outputs
- `check-streamer-status.yml` — Monitor data feeds
- `coinglass-scanner.yml` — Alternative data ingestion

**Quality Gates:**
- `audit-drift-telemetry.yml` — Monitor concept drift
- `actions-failure-guardian.yml` — Auto-retry failed jobs
- `conflict-marker-check.yml` — Code quality checks

**Deployment:**
- `deploy-fc-api-env-godaddy.yml` — FTP deployment
- `deploy-battleground-ftp.yml`
- `deploy-competition-to-site.yml`

**Communication:**
- `clear-channel-command.yml` — Discord notifications
- `closed-picks-command.yml` — Report closed trades

---

### 2.10 Data Directory

**Cached datasets and live databases.**

```
data/
├── aggregated_picks.json      ← All active picks snapshot
├── cache/                     ← Quote/feature cache
├── component_perf_daily.json  ← Daily component metrics
├── dna_master_picks.db        ← DNA mutation picks
├── goldmine/                  ← Top performer database
├── grok_top_picks.json        ← OpenAI Grok picks
├── live_picks.db              ← Current open trades
├── market_intel/              ← Whale, funding, liquidation data
├── meme_scanner_active.json   ← Meme coin tracking
├── parquet/                   ← Historical OHLCV (columnar)
├── spike_trader_active.json   ← Spike trading positions
└── weekly_pm_report.json      ← Portfolio metrics
```

---

### 2.11 Pine Scripts (50+ Files)

**TradingView indicators and alert signals.**

```
pinescripts/
├── Kimi_Claw_Pro.pine        ← Main institutional indicator (61 plots!)
├── SimpletonSignals_KIMI.pine ← Simpleton + Kimi combo
├── SignalEngine_ANTIGRAVITY.pine
├── FIXITMERCURY.pine
├── Superior_Crypto_Strategy.pine
├── advanced_trend_reversal_emoji_indicator.pine
├── [40+ other Pine v5/v6 indicators]

Characteristics:
- Heavy signal confluence
- Multi-timeframe analysis
- Dashboard table integrations
- 64-plot hard limit management
```

---

### 2.12 Tools & Operational Scripts (150+ files)

**Utilities for deployment, validation, monitoring, debugging.**

```
tools/
├── serve_local.py             ← Local dev server (port 5173)
├── mutation_analysis.py       ← Analyze strategy mutations
├── redis_bus_*.py             ← Inter-agent communication
├── hc_filter_backtest.py      ← High conviction filter testing
├── kyle_lambda_tca.py         ← Transaction cost analysis
├── kelly_sizing_*.py          ← Position size optimization
├── matrix_*.py                ← Dashboard matrix helpers
├── tv_*.js/*py                ← TradingView automation
├── hyro_*.py                  ← Hyrotrader integration
├── portfolio_*.py             ← Portfolio analysis & tracking
├── validate_*.py              ← Multi-stage validation
├── scrapers/                  ← Web/API scrapers
├── sql/                       ← SQL query generators
├── deployment scripts         ← FTP, GoDaddy, AWS uploads
└── [100+ additional utilities]
```

---

### 2.13 Agent Infrastructure (.claude/)

**Claude agent configuration and skills.**

```
.claude/
├── settings.json
├── settings.local.json
├── skills/
│   ├── tv-paper-trade/
│   │   └── SKILL.md          ← TradingView paper trading instructions
│   ├── fix-gh-actions/
│   │   └── SKILL.md          ← GitHub Actions debugging
│   └── [other agent skills]
└── PEER_INTEL.md
```

---

## 3. FILE TYPE STATISTICS

| Category | Count | Notes |
|----------|-------|-------|
| **Python files** | ~3,500+ | Core logic, strategies, data pipeline |
| **Markdown docs** | 1,200+ | Research, audits, guides |
| **JSON config/data** | 300+ | Strategy params, test results, snapshots |
| **GitHub Workflows** | 50+ | CI/CD automation (YAML) |
| **Playwright tests** | 80+ | E2E web testing (TypeScript) |
| **Pytest tests** | 75+ | Unit/integration testing (Python) |
| **Pine Scripts** | 50+ | TradingView indicators |
| **SQL schemas** | 20+ | Database structure definitions |
| **HTML dashboards** | 15+ | Audit, portfolio, analysis views |
| **CSV backtests** | 100+ | Historical backtest result exports |
| **Notebooks** | 1 | Polymarket strategy audit (.ipynb) |

---

## 4. DATA FLOW ARCHITECTURE

### Pick Generation Pipeline

```
[Market Data APIs] → [Feature Pipeline] → [Strategy Evaluation] → [Scoring & Gates] → [Output Picks]
     ↓                      ↓                    ↓                    ↓
   20+ feeds           Tech indicators      Ensemble vote       HC filter
                        Volume analysis      ML ranker         Risk policy
                        ML features         Consensus tier     Regime checks
                        On-chain metrics    Conviction weight  Portfolio load
                                           Override signals
                                  ↓
                            [Live Dashboard]
                            [Paper Trading]
                            [Alert System]
```

### Key Databases

```
MySQL (Production):
  ├── picks          (active & closed trades)
  ├── backtest_results (historical performance)
  ├── portfolio_tracker (P&L by strategy)
  ├── scoring_logs   (score component breakdown)
  ├── dna_mutations  (parameter variations tested)
  └── predictions    (ML model outputs)

SQLite (Local):
  ├── feature_cache  (fast feature lookup)
  ├── quote_cache    (last known prices)
  └── forward_test_log (paper trading)

Redis (Live):
  ├── Quote stream   (real-time prices)
  ├── Agent bus      (inter-process messaging)
  ├── Feature queue  (pending computations)
  └── Alert channel  (notifications)
```

---

## 5. MODULAR DESIGN PATTERNS

### Strategy Encapsulation

Each strategy can exist in multiple forms:

1. **Alpha Engine Version** — Full-featured, complex
   - Custom entry/exit logic
   - 10-50 parameters
   - Risk gates, portfolio constraints
   - ML preprocessing

2. **Baby Strategy Version** — Simplified, auditable
   - Standard entry/exit template
   - 3-5 core parameters
   - Conservative defaults
   - Forward-tested

3. **DNA Mutation** — Genetic variant
   - Parameter permutation of proven strategy
   - Auto-backtested against historical prices
   - Ranked by out-of-sample Sharpe

4. **Pine Script** — TradingView alert signal
   - Subset of strategy logic
   - Alert triggers to Discord webhook
   - Real-time on 1m/15m/1h charts

### Scoring Cascade

Multiple scoring layers for pick quality:

```
Pick Input
  ↓
[ML Ranker]           → Raw predicted return
[Consensus Voting]    → Multi-model ensemble
[HC Filter]           → Conviction gate (high/med/low)
[Risk Overlay]        → Regime + correlation adjustment
[Portfolio Load]      → Existing position sizing
  ↓
Final Tier (1-5)
  ├─ Tier 1: Top 5 institutional picks
  ├─ Tier 2: High conviction trades
  ├─ Tier 3: Solid opportunities
  ├─ Tier 4: Speculative
  └─ Tier 5: Research/low conviction
```

---

## 6. ASSET CLASS ORGANIZATION

Strategies are parallelized by asset class:

```
Crypto (1,000+ symbols):
  ├── Spot: BTC, ETH, major alts, meme coins
  ├── Futures: Quarterly perpetuals
  ├── Copy traders: Top 50 signal providers
  └── On-chain metrics: Whale wallets, liquidations

Forex (28 pairs):
  ├── Majors: EUR/USD, GBP/USD, USD/JPY, etc.
  ├── Exotic: Cross-yen, emerging market crosses
  ├── Carry trades
  └── Central bank flows

Equities (8,000+ symbols):
  ├── Blue chips: S&P 500, NASDAQ 100
  ├── Sectors: Tech, Energy, Healthcare, Financials
  ├── Earnings drift (PEAD): Post-earnings moves
  ├── Penny stocks: Venue-specific scanners
  └── Copy traders: Retail trading patterns

Commodities & Futures:
  ├── Precious metals: XAU, XAG, XPTUSD
  ├── Energy: WTI crude, natural gas
  ├── Agriculture: Corn, soybeans, wheat
  ├── Indices: SP500, DAX, Nikkei futures
  └── Micro-contracts: ES, NQ, MES micro

Options & Exotics:
  ├── Implied volatility strategies
  ├── Skew/smile arbitrage
  ├── Calendar spreads
  ├── Prediction markets: Polymarket, Kalshi
  └── Funding rate arb (crypto)
```

---

## 7. QUALITY GATES & VALIDATION

All picks pass through multiple gates:

```
Raw Signal
  ↓
[1. Data Quality Gate]
  - Quote freshness (< 1 min old)
  - Volume sufficient for entry
  - Price not in blacklist
  ↓ (if fail: DROP)
[2. Statistical Gate]
  - Backtest Sharpe > 0.8
  - Win rate > 40%
  - Max drawdown < 15%
  ↓ (if fail: DOWNGRADE)
[3. Regime Filter]
  - Align with market regime
  - Hedge against current VIX
  - Correlation with portfolio < 0.6
  ↓ (if fail: RISKWEIGHT)
[4. Risk Policy Gate]
  - Portfolio load < 100%
  - Single position < 10x AUM
  - Sector concentration < 20%
  ↓ (if fail: CAP)
[5. Confidence Gate (HC Filter)]
  - Model agreement > 70%
  - Track record win rate > 50%
  - Recent P&L positive
  ↓ (if fail: NO_ALERT)
Final Tier Assignment
  ↓
[Dashboard] [Paper Trading] [Discord Alert]
```

---

## 8. REAL-TIME EXECUTION FLOW

### During Market Hours

```
Every 1 minute:
  1. Fetch OHLCV candles (last 500 bars per symbol)
  2. Compute technical indicators
  3. Fetch alternative data (on-chain, sentiment, macro)
  4. Run strategy evaluations (parallel by asset class)
  5. Score & rank picks
  6. Apply gates & filters
  7. Update live picks table
  8. Generate alerts for new Tier 1 picks
  9. Paper trading: Monitor open positions, trail stops
  10. Update audit dashboard

Every 5 minutes:
  - Recalculate regime, check drawdown
  - Rebalance portfolio if needed
  - Monitor correlation drift

Every 15 minutes:
  - Update ML features
  - Refresh copy trader rankings
  - Check for data anomalies

Every hour:
  - Backfill historical features
  - Rotate strategy parameters
  - Generate performance report

Every 4 hours:
  - Run mutation tests on underperforming strategies
  - Regenerate strategy rankings
  - Deep-dive on failed picks
```

---

## 9. KEY ENTRY POINTS & SCRIPTS

**Production Runners:**

| Script | Purpose | Trigger |
|--------|---------|---------|
| `alpha_engine/smart_picks_engine.py` | Generate fresh picks | Every 1-5 minutes |
| `alpha_engine/check_active_picks.py` | Monitor open trades | Every 60 seconds |
| `baby_strategies/backtest_framework_runner.py` | Test baby strategies | Daily or on-demand |
| `tools/serve_local.py` | Dev server (port 5173) | Developer work |
| `tools/mutation_analysis.py` | Analyze mutations | Post-backtest |
| `audit_dashboard/blueprint_generator.py` | Refresh dashboard HTML | Every 30 minutes |
| `data_pipeline/live_ingest.py` | Stream market data | 24/7 background |

---

## 10. DEVELOPMENT ENVIRONMENT

### Prerequisites
```
Python 3.9+
MySQL 8.0+
Redis 6.0+
Node.js 14+ (for Playwright tests)
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Start local server (dashboard, backtester)
python tools/serve_local.py

# Run Playwright tests
npx playwright test tests/*.spec.ts --project="Desktop Chrome"

# Run Python tests
pytest tests/*.py -v
```

### Configuration
- `.vscode/settings.json` — IDE config
- `.vscode/tasks.json` — Build/run tasks
- `playwright.config.ts` — E2E test config
- `pyrightconfig.json` — Type checking

---

## 11. KNOWLEDGE BASE LOCATIONS

### Where to Find Specific Information

**Strategy Ideas:**
- `docs/100_ALGORITHMS_MASTER_CATALOG.md` — All 100+ algorithm descriptions
- `alpha_engine/README.md` — Alpha engine overview
- `baby_strategies/NEW_STRATEGY_VARIATIONS.md` — Latest baby strategies

**How to Deploy:**
- `docs/TRADINGVIEW_MCP_GUIDE.md` — TradingView integration
- `docs/TRADING_GUIDE.md` — Strategy deployment
- `tools/DEPLOYMENT_STATUS.md` — Deployment checklist

**Audit & Quality:**
- `docs/TESTING_PROTOCOL.MD` — Testing best practices
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — Before removing a strategy

**Risk Management:**
- `config/risk_policy.json` — Position sizing rules
- `alpha_engine/risk_controls.py` — Code implementation
- `docs/SAFE_TRADING_PROTOCOL.md` — Risk manual

**Performance Analysis:**
- `audit_dashboard/` — Live dashboard + scripts
- `docs/CLOSED_PICKS_LESSONS.md` — Lessons from closed trades
- `alpha_engine/reporting/` — Performance reporters

---

## 12. SCALING & PARALLELIZATION

### Multi-Agent Coordination

The system supports parallel work via **Agent Bus** (Redis):

```
Claude Code (UI fixes) ↔ Redis Bus ↔ Antigravity (strategy testing)
                          ↓
                     Cursor (data pipeline)
                        ↓
                    Copilot (auditing)
```

### Shared Files (Must Lock Before Edit)
- `audit_dashboard/template.html` — Dashboard template
- `updates/index.html` — Deployment index
- `.mcp.json`, `AGENTS.md` — Configuration
- `.github/workflows/*` — CI/CD

---

## 13. CONCLUSION

### Architecture Summary

**This is a production-grade quantitative trading platform** combining:

- ✅ **Modular strategy engine** — 600+ Python files, 250+ strategy implementations
- ✅ **Real-time data pipeline** — 20+ data providers, feature engineering at scale
- ✅ **Enterprise risk management** — Portfolio constraints, regime filters, draw-down controls
- ✅ **Machine learning ensemble** — LightGBM ranker, consensus models, prediction markets
- ✅ **CI/CD automation** — 50+ GitHub workflows, parallel backtesting, continuous evolution
- ✅ **Multi-team coordination** — Agent Bus for parallel work, shared dashboards, locking
- ✅ **Comprehensive auditing** — Real-time dashboard, quality gates at every stage, audit trails

**Next Steps for Understanding:**

1. **Read:** [audit_dashboard](audit_dashboard/template.html) → understand live pick methodology
2. **Explore:** [alpha_engine/smart_picks_engine.py](alpha_engine/smart_picks_engine.py) → main entry point
3. **Study:** [docs/TRADINGVIEW_MCP_GUIDE.md](docs/TRADINGVIEW_MCP_GUIDE.md) → how alerts are generated
4. **Review:** [.planning/codebase/ARCHITECTURE.md](.planning/codebase/ARCHITECTURE.md) → technical deep-dives
5. **Test:** Run `tools/serve_local.py` → see dashboard in action

---

**Document Version:** 2.0  
**Last Sync:** April 12, 2026 (09:15 UTC)  
**Maintained by:** Claude Agent Fleet

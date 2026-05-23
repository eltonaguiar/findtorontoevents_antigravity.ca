# Codebase Structure

**Analysis Date:** 2026-02-23

## Directory Layout

```
project-root/
├── KIMI_FEB172026/                    # Live trading scanner (v11.0, 68 algorithms)
│   ├── live_scanner.py                # Entry point: Orchestrates all modules
│   ├── crypto_acceleration_engine.py  # 10 institutional signals
│   ├── ml_signal_ranker.py            # ML ranking (RandomForest)
│   ├── sqlite_store.py                # Signal history persistence
│   ├── elimination_engine.py          # Performance tracking & discard
│   ├── signal_tracker.py              # TP/SL validator
│   ├── data/                          # Live picks JSON + SQLite DBs
│   │   ├── kimi_trading.db            # Historical signals
│   │   ├── kimi_signal_tracker.db     # TP/SL outcomes
│   │   └── live_signals_now.json      # Current BUY picks (published)
│   └── config/                        # Symbol lists, API endpoints
│
├── alpha_engine/                      # 100-strategy crypto/forex/equity engine
│   ├── master_dashboard.py            # Entry point: Orchestrates all strategies
│   ├── crypto_strategies.py           # 75 crypto strategies (Ichimoku, SMC, on-chain, etc.)
│   ├── forex_strategies.py            # 11 forex strategies
│   ├── equity_strategies.py           # 14 equity strategies
│   ├── advanced_strategies.py         # 8 advanced wave-6 strategies
│   ├── event_strategies.py            # 8 event-driven strategies (token unlock, etc.)
│   ├── quant_strategies.py            # 4 academic/quant strategies
│   ├── pattern_strategies.py          # 10 pattern-recognition strategies
│   ├── cyclical_strategies.py         # 10 seasonal/cyclical strategies
│   ├── onchain_strategies.py          # 10 on-chain metrics (MVRV, hash ribbon, NVT)
│   ├── community_strategies.py        # 6 community/external strategies
│   ├── indicators.py                  # All technical indicators (Ichimoku, Bollinger, etc.)
│   ├── config.py                      # Crypto pairs, timeframes, risk params
│   ├── database.py                    # SQLite interface for A/B testing
│   ├── data/                          # Results JSONs + cached data
│   │   └── active_picks.json          # Current active picks (published)
│   └── backtest/                      # Backtesting utilities
│
├── claude_gainer_ml/                  # Real-time top-gainer ML predictor (v3.0)
│   ├── live_scanner.py                # Entry point: Scans Binance top gainers
│   ├── data_fetcher.py                # Multi-exchange Binance fetcher (30 features)
│   ├── train_model.py                 # Model retraining pipeline
│   ├── models/                        # Trained ensemble models (XGBoost, LightGBM, RF, stacking)
│   │   ├── AAVEUSDT_1h_A_xgboost.joblib
│   │   ├── BTCUSDT_4h_B_lightgbm.joblib
│   │   └── ... (36 pair × 2 TF × 4 variants = 288 models)
│   ├── tracker/                       # Pick tracking & validation
│   │   ├── claude_live_picks.json     # Current top-10 gainer picks
│   │   └── claude_scan_log.json       # Scan history
│   └── data/                          # Training data cache
│
├── ml_crypto_predictor/               # Regression-based pair/TF predictor (36 pairs, 5 TF)
│   ├── enhanced_models/
│   │   ├── main.py                    # CLI entry: train, predict, regime, status
│   │   ├── model_trainer.py           # Training loop (4 variants per pair/TF)
│   │   ├── live_predictor.py          # Live scan runner
│   │   ├── feature_engine.py          # Feature extraction (30 features)
│   │   ├── regime_detector.py         # HMM-based market regime classification
│   │   ├── advanced_validation.py     # Edge testing & proof-of-concept
│   │   ├── models/                    # Trained models (.joblib)
│   │   │   ├── AAVEUSDT_1h_A_xgboost.joblib
│   │   │   ├── BTCUSDT_4h_D_ensemble_stack.joblib
│   │   │   └── ... (30 pairs × 5 TF × 4 variants = 600 models)
│   │   ├── results/                   # Training metrics JSON
│   │   │   ├── v15_training_summary.json
│   │   │   └── active_picks.json      # Live picks (published)
│   │   ├── data/                      # Cache, OHLC
│   │   ├── config.py                  # Pairs, timeframes, hyperparams
│   │   └── external_data.py           # CoinGecko, CryptoQuant API clients
│   ├── backtest_ml.py                 # Historical backtesting
│   └── discord_status.py              # Discord notifications
│
├── tools/                             # Utility scripts
│   ├── scrapers/
│   │   ├── unified_scraper.py         # Toronto events scraper (main)
│   │   ├── eventbrite_scraper.py      # JSON-LD scraper
│   │   ├── ticketmaster_scraper.py    # Ticketmaster API client
│   │   ├── sofiaadelgiudice_notion.py # Notion calendar
│   │   ├── tpl_scraper.py             # Toronto Public Library
│   │   └── ... (7 total event sources)
│   ├── scrape_and_sync_events.py      # Main events pipeline
│   ├── live_trading_pipeline.py       # Trade execution (paper)
│   ├── market_data_fetcher.py         # OHLC data aggregator
│   ├── deploy_riseoftheclaw.py        # Deploy scanner to remote
│   └── deploy_to_altsite.py           # Multi-site deployer
│
├── pine_generator/                    # TradingView Pine Script generator
│   ├── generate_pine.py               # CLI: Generates v6 Pine scripts
│   ├── templates/
│   │   └── base.pine                  # Pine v6 template (14 strategies)
│   ├── output/
│   │   ├── eltons_predictions.pine    # Generated v4.0.0 (77KB, 14 strategies)
│   │   ├── simpleton_v001_claude.pine # Simple 12-strategy variant
│   │   └── eltons_screener.pine       # Screener variant
│   └── research/                      # Strategy papers & backtests
│
├── alpha_engine/                      # See above (100 strategies)
│
├── .github/workflows/                 # GitHub Actions orchestration
│   ├── kimi-feb172026-live.yml        # KIMI scanner (every 15 min)
│   ├── alpha-engine-live.yml          # Alpha engine (every 30 min)
│   ├── claude-gainer-tracker.yml      # Claude gainer ML (every 60 min)
│   ├── enhanced-ml-crypto.yml         # Enhanced ML predictor
│   ├── train_crypto_models.yml        # Weekly model training
│   ├── scrape-events.yml              # Events scraper (daily 12:00 UTC)
│   ├── deploy-riseoftheclaw.yml       # Deploy KIMI dashboard
│   ├── deploy-alpha-dashboard.yml     # Deploy Alpha Engine
│   └── ... (35 total workflows)
│
├── riseoftheclaw.html                 # KIMI v11.0 dashboard (real-time)
├── updates/                           # Updates/changelog page
│   ├── index.html                     # Live changelog (dark theme)
│   └── data/                          # Update metadata
│
├── data/                              # Root-level cache
│   └── alpha_picks_export.json        # Exported picks for analysis
│
├── simpleton_backtester.py            # Test Simpleton v0.01 Pine Script
├── simpleton_results/                 # Backtest results (SOL/Consensus 6.03 Sharpe)
│
├── .venv/                             # Python virtual environment
│
├── ml_crypto_predictor/enhanced_models/models/  # Joblib serialized models
│
├── backtest_results/                  # Historical backtest JSON results
│
└── MEMORY.md (user instructions)      # Critical: Pine Script v6 validation rules
```

## Directory Purposes

**KIMI_FEB172026/:**
- Purpose: Live crypto signal scanner v11.0 (68 algorithms, real-time)
- Contains: Entry point, acceleration engine, ML ranker, elimination engine, SQLite store, signal tracker
- Key files: `live_scanner.py` (orchestrator), `data/live_signals_now.json` (output), `data/kimi_trading.db` (history)
- Execution: GitHub Actions every 15 min → outputs BUY picks with TP/SL

**alpha_engine/:**
- Purpose: Comprehensive 100-strategy scanner (crypto, forex, equity)
- Contains: 9 strategy modules (crypto, advanced, event, quant, pattern, cyclical, onchain, community, forex/equity)
- Key files: `master_dashboard.py` (orchestrator), `config.py`, `data/active_picks.json` (output)
- Execution: GitHub Actions every 30 min → outputs ranked picks across asset classes

**claude_gainer_ml/:**
- Purpose: Real-time ML top-gainer detector (focuses on yesterday's best performers)
- Contains: Live scanner, data fetcher (30 features), 288 trained models (joblib), tracker
- Key files: `live_scanner.py`, `data_fetcher.py`, `tracker/claude_live_picks.json` (output)
- Execution: GitHub Actions every 60 min → outputs top-10 pump probability picks

**ml_crypto_predictor/enhanced_models/:**
- Purpose: Regression-based predictor for 30 crypto pairs × 5 timeframes
- Contains: Training loop (4 model variants per pair/TF), feature engine, regime detector, 600+ joblib models
- Key files: `main.py` (CLI), `model_trainer.py`, `live_predictor.py`, `models/` (600 joblib files), `results/active_picks.json`
- Execution: Weekly training (600 models) → continuous live predictions

**tools/scrapers/:**
- Purpose: Multi-source event data collection for Toronto events
- Contains: 7 scraper classes (Eventbrite, Ticketmaster, Nathan Phillips, Sankofa, Toronto.com, TPL, etc.)
- Key files: `unified_scraper.py` (orchestrator), `eventbrite_scraper.py` (JSON-LD parser)
- Execution: Daily via `scrape_and_sync_events.py` → upserts to events database

**pine_generator/:**
- Purpose: Auto-generate TradingView Pine Script v6 from Python strategy definitions
- Contains: Generator (Python), Jinja2 template, output Pine scripts
- Key files: `generate_pine.py`, `templates/base.pine`, `output/eltons_predictions.pine`
- Execution: Manual `py pine_generator/generate_pine.py --version X.Y.Z` → generates .pine file

**.github/workflows/:**
- Purpose: Orchestrate all pipelines via GitHub Actions
- Contains: 35+ YAML workflow definitions
- Key files: `kimi-feb172026-live.yml`, `alpha-engine-live.yml`, `claude-gainer-tracker.yml`, `train_crypto_models.yml`, `scrape-events.yml`
- Execution: Scheduled cron jobs, manual triggers, or event-driven

**riseoftheclaw.html:**
- Purpose: Live KIMI v11.0 dashboard
- Contains: HTML5 + Bootstrap + Chart.js, fetches `KIMI_FEB172026/data/live_signals_now.json` every 30s
- Deployed to: findtorontoevents.ca/riseoftheclaw.html (50webs FTP), GitHub Pages mirror
- Updates: Every 15 min via CI (new signals → JSON updated → dashboard auto-refreshes)

## Key File Locations

**Entry Points:**
- `KIMI_FEB172026/live_scanner.py` — Primary live scanner (run by GitHub Actions every 15 min)
- `alpha_engine/master_dashboard.py scan` — Alpha engine (run every 30 min)
- `claude_gainer_ml/live_scanner.py` — Claude gainer ML (run every 60 min)
- `ml_crypto_predictor/enhanced_models/main.py train` — Weekly model retraining
- `tools/scrape_and_sync_events.py --sync` — Events scraper (daily 12:00 UTC)

**Configuration:**
- `alpha_engine/config.py` — Symbol lists, timeframes, risk params, API endpoints
- `ml_crypto_predictor/enhanced_models/config.py` — Crypto pairs (30), timeframes (5), model hyperparams
- `KIMI_FEB172026/crypto_acceleration_engine.py` (lines 48-55) — 15 top crypto symbols
- `.env` files (gitignored) — API keys (COINGECKO_API_KEY, DISCORD_WEBHOOK_URL, etc.)

**Core Logic:**
- `KIMI_FEB172026/live_scanner.py` — Main signal loop (fetch data → run algos → rank → output)
- `KIMI_FEB172026/ml_signal_ranker.py` — ML feature engineering + RandomForest ranking
- `alpha_engine/crypto_strategies.py` — 75 crypto strategies (Ichimoku, SMC, on-chain, etc.)
- `ml_crypto_predictor/enhanced_models/model_trainer.py` — Train 4 model variants per pair/TF
- `tools/scrapers/unified_scraper.py` — Orchestrate 7 event scrapers

**Testing:**
- `simpleton_backtester.py` — Backtest Simpleton v0.01 Pine Script
- `alpha_engine/backtest_new_strategies.py` — Test new strategies
- `ml_crypto_predictor/enhanced_models/advanced_validation.py` — Edge case testing
- `backtest_results/` — Historical backtest JSON results

## Naming Conventions

**Files:**
- **Python scripts:** `snake_case.py` (e.g., `live_scanner.py`, `crypto_acceleration_engine.py`)
- **Pine scripts:** `lowercase_with_underscores.pine` (e.g., `eltons_predictions.pine`)
- **HTML dashboards:** `lowercase_hyphenated.html` (e.g., `riseoftheclaw.html`)
- **JSON data:** `snake_case.json` (e.g., `live_signals_now.json`, `active_picks.json`)
- **Directories:** `UPPERCASE_FOR_PROJECTS` (e.g., `KIMI_FEB172026`, `STOCKS`) or `lowercase_for_utils` (e.g., `tools`, `data`)

**Directories:**
- **Project domains:** UPPERCASE_DATE or UPPERCASE_NAME (e.g., `KIMI_FEB172026`, `alpha_engine`, `claude_gainer_ml`)
- **Utility directories:** lowercase (e.g., `tools`, `data`, `models`, `results`, `tracker`)
- **Nested**: `domain/submodule/` (e.g., `tools/scrapers/`, `ml_crypto_predictor/enhanced_models/`)

**Functions:**
- **Strategy methods:** `strategy_name()` returns signal list (e.g., `ichimoku_cloud()`, `funding_rate_carry()`)
- **Feature extractors:** `extract_*_features()` (e.g., `extract_momentum_features()`)
- **Validators:** `validate_*()` or `is_*()` (e.g., `validate_signal()`, `is_in_probation()`)
- **Data fetchers:** `fetch_*()` (e.g., `fetch_klines()`, `fetch_fear_greed()`)

**Variables:**
- **Signals:** `signals: List[SignalResult]`
- **Picks:** `active_picks: List[Dict]` or `picks_json: Dict`
- **DataFrames:** `df_ohlc`, `df_features`, `df_results`
- **Configs:** `SYMBOL_LIST`, `ICHIMOKU_PARAMS` (UPPERCASE for constants)
- **State:** `self.active_picks`, `self.elimination_state` (lowercase for instance vars)

**Types:**
- **Classes:** `PascalCase` (e.g., `CryptoAccelerationEngine`, `MLSignalRanker`, `EliminationEngine`)
- **Dataclasses:** `PascalCase` (e.g., `SignalResult`, `SignalFeatures`)
- **Enums:** `PascalCase` (e.g., `RegimeState`, `SignalDirection`)

## Where to Add New Code

**New Feature (e.g., new crypto strategy):**
- Primary code: `alpha_engine/crypto_strategies.py` (add function) or create `alpha_engine/custom_strategies.py` if major theme
- Tests: `alpha_engine/backtest_new_strategies.py` (add test case)
- Config: Update `alpha_engine/config.py` if new symbols needed
- Deploy: Update `alpha_engine/master_dashboard.py` to call new strategy

**New Crypto Signal Algorithm (e.g., whale detector):**
- Implementation: `KIMI_FEB172026/crypto_acceleration_engine.py` (add method to `CryptoAccelerationEngine`)
- Algorithm definition: `KIMI_FEB172026/live_scanner.py` → `ALGO_DEFS` dict (add entry)
- Feature: `KIMI_FEB172026/ml_signal_ranker.py` (if adding new features, update `SignalFeatures`)
- Testing: `python KIMI_FEB172026/live_scanner.py --test-algo whale-detector`

**New Indicator (for strategies):**
- Shared indicators: `alpha_engine/indicators.py` (add function, e.g., `def my_indicator(df): ...`)
- ML-specific features: `ml_crypto_predictor/enhanced_models/feature_engine.py` (e.g., `def extract_my_feature(df): ...`)
- Usage: Import at top of strategy file (e.g., `from indicators import my_indicator`)

**New Deployment Step (e.g., new dashboard HTML):**
- HTML file: Root or domain-specific directory (e.g., `riseoftheclaw.html`, `alpha_engine_dashboard.html`)
- Data source: Ensure JSON output exists (e.g., `KIMI_FEB172026/data/live_signals_now.json`)
- Deploy workflow: Create `.github/workflows/deploy-new-dashboard.yml` (FTP + GitHub Pages)
- Updates page: Add entry to `updates/index.html` documenting the new dashboard

**Utilities (shared helpers):**
- Shared functions: Create module in `tools/` (e.g., `tools/common_helpers.py`)
- Import pattern: `from tools.common_helpers import my_function`
- If heavily used across domains: Consider moving to `alpha_engine/` or `KIMI_FEB172026/` if domain-specific

## Special Directories

**models/ (machine learning artifacts):**
- Purpose: Store serialized ML models (joblib, pickle)
- Generated: Yes (via training scripts)
- Committed: Yes (binary files, may need LFS for large repos)
- Locations: `claude_gainer_ml/models/`, `ml_crypto_predictor/enhanced_models/models/`
- Refresh: Weekly/monthly via GitHub Actions training job

**data/ (transient output & cache):**
- Purpose: Store live signal JSON outputs, OHLC cache, databases
- Generated: Yes (updated every scan cycle)
- Committed: No (JSON output varies; .gitignore includes `data/`, `*.db`)
- Locations: `KIMI_FEB172026/data/`, `alpha_engine/data/`, `claude_gainer_ml/data/`, etc.
- Retention: Append-only for SQLite; rolling 24h window for JSON picks

**results/ (analysis outputs):**
- Purpose: Store training metrics, backtest reports, A/B test summaries
- Generated: Yes (via training/backtest jobs)
- Committed: Selectively (summary JSON, not raw data)
- Locations: `ml_crypto_predictor/enhanced_models/results/`, `backtest_results/`
- Retention: Archive old results; keep latest 10 versions

**.github/workflows/ (CI/CD definitions):**
- Purpose: YAML job specifications
- Generated: No (manually written)
- Committed: Yes (code-reviewed)
- Pattern: One workflow per logical task (e.g., `kimi-feb172026-live.yml`, `alpha-engine-live.yml`)
- Update: Add new workflow when introducing new scanner or dashboard

**.venv/ (Python virtual environment):**
- Purpose: Isolated package dependencies
- Generated: Yes (via `python -m venv .venv`)
- Committed: No (.gitignore includes `/.venv/`)
- Install: `pip install -r requirements.txt` (if present) or per-folder requirements

---

*Structure analysis: 2026-02-23*

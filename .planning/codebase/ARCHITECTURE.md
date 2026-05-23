# Architecture

**Analysis Date:** 2026-02-23

## Pattern Overview

**Overall:** Multi-system trading research and signal generation platform with four parallel execution pipelines:
1. **KIMI Live Scanner** - Institutional crypto acceleration engine (v11.0, 68+ algorithms)
2. **Alpha Engine** - 100-strategy crypto/forex/equity framework (weekly comprehensive scanning)
3. **Claude Gainer ML** - ML-based top-gainer prediction system (real-time Binance feeds)
4. **Enhanced ML Crypto Predictor** - Regression-based pair/timeframe models (36 currency pairs, 5 timeframes)

Each system runs autonomously via GitHub Actions, publishes JSON results to `*/data/` directories, and feeds HTML dashboards for real-time monitoring.

**Key Characteristics:**
- Modular signal generation (algorithms → scoring → ranking → picks)
- Async HTTP data fetching with retry/failover (Binance, CoinGecko, CryptoQuant, external APIs)
- SQLite persistence for signal history and performance tracking
- Elimination engine to discard underperforming strategies
- ML ensemble ranking (RandomForest 50+ closed picks, heuristic <50 picks)
- GitHub Actions orchestration (15/30/60 min execution windows)
- Multi-layer state: live signals (JSON) → tracked performance (SQLite) → pick history (logs)

## Layers

**Data Fetching Layer:**
- Purpose: Aggregate market data from multiple exchanges and APIs
- Location: `claude_gainer_ml/data_fetcher.py`, `ml_crypto_predictor/enhanced_models/data_fetcher.py`, `KIMI_FEB172026/crypto_acceleration_engine.py`
- Contains: REST API clients for Binance Spot/Futures, CoinGecko, Binance WebSocket subscriptions, fallback chains
- Depends on: `requests`, `aiohttp`, environment API keys
- Used by: All scanners (live_scanner.py variants, acceleration engines)
- **Key behavior:** Binance primary → CoinGecko fallback → cached OHLC if network fails

**Signal Generation Layer:**
- Purpose: Run algorithmic strategies and detect trading opportunities
- Location: `alpha_engine/{crypto,forex,equity,advanced,quant,pattern,cyclical}_strategies.py`, `KIMI_FEB172026/crypto_acceleration_engine.py`, `claude_gainer_ml/live_scanner.py`
- Contains: 100+ strategy classes (each returns BUY/SELL signals with TP/SL)
- Depends on: Technical indicators (`alpha_engine/indicators.py`), data layer
- Used by: ML ranker, elimination engine
- **Key behavior:** Each strategy is asset-specific and timeframe-aware. Signals include confidence scores and reasoning.

**Feature Engineering & ML Scoring Layer:**
- Purpose: Convert raw signals into ML features and rank by win probability
- Location: `KIMI_FEB172026/ml_signal_ranker.py`, `ml_crypto_predictor/enhanced_models/feature_engine.py`
- Contains: 24-feature SignalFeatures dataclass, RandomForest/GradientBoosting classifiers, auto-training at ≥50 closed picks
- Depends on: Signal generation layer, SQLite history
- Used by: Live scanner output filtering
- **Key behavior:** Heuristic ranking (<50 picks) → RF auto-trains at threshold → features include algo WR, market regime, time-of-day, VIX proxy

**Elimination & Portfolio Management Layer:**
- Purpose: Track pick performance, eliminate failing strategies, maintain challenger pool
- Location: `KIMI_FEB172026/elimination_engine.py`, `KIMI_FEB172026/signal_tracker.py`
- Contains: Danger zone → probation → elimination states; 20-pick challenger pool; TP/SL auto-validator
- Depends on: Signal history (SQLite), live price feeds
- Used by: Live scanner (filters active picks)
- **Key behavior:** Signal → tracked 24h → hit TP (+) or SL (-) → aggregate algo WR → delist if <50% win rate

**Persistence Layer:**
- Purpose: Store signal history, performance metrics, closed picks
- Location: `KIMI_FEB172026/sqlite_store.py`, `claude_gainer_ml/tp_sl_tracker.py`, SQLite DBs in `*/data/`
- Contains: `kimi_trading.db` (signals, closed trades), `kimi_signal_tracker.db` (TP/SL outcomes), JSON logs
- Depends on: None (self-contained SQLite)
- Used by: ML ranker, elimination engine, dashboards
- **Key behavior:** Append-only signal log; auto-update TP/SL status on each scan cycle

**Output & Dashboard Layer:**
- Purpose: Publish picks and metrics to web for real-time monitoring
- Location: `riseoftheclaw.html`, `alpha_engine/data/active_picks.json`, `claude_gainer_ml/tracker/claude_live_picks.json`
- Contains: HTML5 dashboards with live JSON updates, GitHub Pages serving
- Depends on: Signal generation + ML layers (read JSON output)
- Used by: End-users, Discord bots, manual traders
- **Key behavior:** Dashboards poll `*/data/` JSON files every 30s, highlight active BUY picks with color-coded confidence

**Event Pipeline (Side System):**
- Purpose: Scrape Toronto events and maintain events database
- Location: `tools/scrapers/unified_scraper.py`, `tools/scrape_and_sync_events.py`
- Contains: Eventbrite JSON-LD scraper, Ticketmaster API client, 7+ source connectors
- Depends on: `requests`, `beautifulsoup4`, optional Ticketmaster API key
- Used by: `events.json` sync pipeline, web portal
- **Key behavior:** Daily GitHub Actions at 12:00 UTC → fetch → validate → upsert to database → push events.json

## Data Flow

**Live Signal Scan Cycle (KIMI v11.0 example, 15 min):**

```
1. GitHub Actions triggers live_scanner.py
2. fetch_klines() → Binance API → OHLC data (multi-symbol, multi-timeframe)
3. 68 algorithms run in parallel
   - Pump detector → volume spike + order book imbalance → SignalResult(BTC, LONG, 0.85, ...)
   - Liquidation cascade → short liquidations detected → SignalResult(ETH, LONG, 0.72, ...)
   - 66 other strategies → all candidates
4. ML ranker → 24-feature extraction per signal
   - algo_id, category, symbol, hour_of_day, day_of_week
   - regime (bull/bear/neutral), vix_proxy, breadth, fear_greed
   - algo_current_wr, algo_current_sharpe, price_vs_52w_high
5. Random Forest predicts win probability
   - If ≥50 closed picks: RF model predicts
   - If <50 closed picks: heuristic rule (algo_current_wr + confidence)
6. Filter: Top 5-10 signals by predicted win rate
7. Elimination check: Is algo in probation? Skip if <50% historical WR
8. Write to JSON: data/live_signals_now.json
   - Active BUY picks with entry, TP, SL
9. SQLite append: kimi_trading.db signals table
10. TP/SL tracker monitors 24h
    - Compare signal entry vs real Binance price
    - If hit TP: mark closed, add +1 to algo win count
    - If hit SL: mark closed, add +1 to algo loss count
11. Elimination engine runs
    - If algo win_rate < 50%: move to probation
    - If in probation >10 scans: eliminate
```

**Full Training Cycle (ML Crypto Predictor, weekly):**

```
1. User/workflow runs: python -m ml_crypto_predictor.enhanced_models.main train
2. For each of 30 crypto pairs (BTC, ETH, SOL, ...):
   - For each of 5 timeframes (1m, 5m, 15m, 1h, 4h):
     - For each of 4 model variants (XGBoost, LightGBM, RandomForest, Ensemble):
       - fetch_klines(pair, tf, 500 bars) → Binance
       - feature_engine → 30 features (RSI, MACD, Volume, Close>50d, etc.)
       - meta_labeler → TP hit in next N bars? → Label 1/0
       - Train model on 80%, validate on 20%
       - Record accuracy, precision, recall, Sharpe, max drawdown
3. A/B test: Compare all 4 variants per (pair, tf)
4. Winner declared (highest Sharpe or accuracy)
5. Save 600 .joblib models to ml_crypto_predictor/enhanced_models/models/
6. Save results JSON to ml_crypto_predictor/enhanced_models/results/
7. Discord notification: "✅ Training complete: 600 models, best: XGBoost BTCUSDT_1h Sharpe 2.34"
```

**State Management:**

- **Live picks state:** `data/live_signals_now.json` — current BUY candidates (expires every 15/30 min)
- **Win rate state:** SQLite `signal_tracker.db` — per-algo aggregate WR, Sharpe, max win streak
- **Closed picks history:** SQLite `kimi_trading.db` — all historical signals (entry, exit, TP/SL hit, profit/loss)
- **ML model state:** `models/*.joblib` files — frozen RandomForest/XGBoost trained on 500 bars each
- **Feature cache:** In-memory during scan (not persisted) — re-computed each cycle
- **Dashboard state:** HTML page polls `data/active_picks.json` every 30s, renders live

## Key Abstractions

**SignalResult (dataclass):**
- Purpose: Represents a single algorithm's output for one symbol
- Examples: `KIMI_FEB172026/crypto_acceleration_engine.py:SignalResult`, `ml_crypto_predictor/enhanced_models/live_predictor.py:Prediction`
- Pattern: `@dataclass SignalResult(symbol, signal_type, confidence, direction, entry_price, take_profit, stop_loss, reason, timestamp, metadata)`
- Used by: All scanners; passed to ML ranker for feature extraction

**SignalFeatures (dataclass):**
- Purpose: Engineered ML features for one signal's win probability prediction
- Examples: `KIMI_FEB172026/ml_signal_ranker.py:SignalFeatures`
- Pattern: 24 numerical features: algo_id_encoded, hour_of_day, regime_encoded, algo_current_wr, price_vs_52w_high, etc.
- Used by: RandomForest classifier → win probability score

**Algorithm Definition (dict):**
- Purpose: Metadata and symbol list for each strategy
- Examples: `KIMI_FEB172026/live_scanner.py:ALGO_DEFS`
- Pattern: `{"pump-detector": {"name": "...", "category": "crypto", "tier": "TIER_1", "symbols": [list], ...}}`
- Used by: Selector to enable/disable algos; elimination engine to track per-algo metrics

**Regime Detector (class):**
- Purpose: Classify market as bull/bear/neutral using HMM on BTC daily returns
- Examples: `ml_crypto_predictor/enhanced_models/regime_detector.py:RegimeDetector`
- Pattern: Train HMM on 365d BTC OHLC → Viterbi decode current state → return (regime, confidence, features, recommendations)
- Used by: Feature engineering layer (regime_encoded feature); TP/SL adjustment multipliers

**Trade-like Database Abstraction:**
- Purpose: Unified interface to SQLite signal history (append-only log pattern)
- Examples: `KIMI_FEB172026/sqlite_store.py:SQLiteStore`
- Pattern: Methods: `add_signal(signal)`, `get_active_signals()`, `mark_closed(signal_id, outcome)`, `get_algo_metrics(algo_id)`
- Used by: Live scanner (write), elimination engine (read metrics), ML ranker (read historical WR)

## Entry Points

**GitHub Actions Trigger → Live Scanner (KIMI v11.0):**
- Location: `.github/workflows/kimi-feb172026-live.yml`
- Triggers: Every 15 min
- Responsibilities:
  1. `python KIMI_FEB172026/live_scanner.py`
  2. Load crypto acceleration engine + ML ranker + elimination engine
  3. Run 68 algorithms
  4. Output: `KIMI_FEB172026/data/live_signals_now.json`
  5. Update dashboard: `riseoftheclaw.html` (fetches JSON client-side)

**GitHub Actions Trigger → Alpha Engine (100 strategies):**
- Location: `.github/workflows/alpha-engine-live.yml`
- Triggers: Every 30 min
- Responsibilities:
  1. `python alpha_engine/master_dashboard.py scan`
  2. Load crypto + forex + equity strategies
  3. Run 100 strategies across 50+ symbols
  4. Output: `alpha_engine/data/active_picks.json`
  5. Update: Alpha Engine dashboard (GitHub Pages)

**GitHub Actions Trigger → Claude Gainer ML (Real-time top gainers):**
- Location: `.github/workflows/claude-gainer-tracker.yml`
- Triggers: Every 60 min
- Responsibilities:
  1. `python claude_gainer_ml/live_scanner.py --top 10`
  2. Fetch Binance top 24h gainers yesterday
  3. Compute 30 ML features
  4. Predict pump probability with ensemble
  5. Output: `claude_gainer_ml/tracker/claude_live_picks.json`

**GitHub Actions Trigger → ML Crypto Predictor (Weekly retraining):**
- Location: `.github/workflows/train_crypto_models.yml`
- Triggers: Weekly (or manual)
- Responsibilities:
  1. `python -m ml_crypto_predictor.enhanced_models.main train`
  2. Fetch 500 bars per (pair, timeframe, variant)
  3. Train 600 models (30 pairs × 5 TF × 4 variants)
  4. A/B test and save winners to `models/` and `results/`

**Manual/Local Entry:**
- Location: Root-level files for development/testing
- Examples: `backtest_framework.py`, `comprehensive_backtest.py`, `battle_tester.py`
- Responsibilities: Backtest, validate, proof-of-concept (not live)

## Error Handling

**Strategy:** Graceful degradation with multi-source fallback and exception-specific routing.

**Patterns:**

- **API Fetch Failure:** Binance primary → CoinGecko secondary → Binance Futures tertiary → cached last-known values
- **Signal Generation Timeout:** Algorithm runs with 5s timeout; if timeout, log and skip, don't crash
- **ML Model Corrupt:** Load backup from previous scan; if none, fall back to heuristic ranking (algo_wr * confidence)
- **SQLite Lock (concurrent writes):** Implement WAL mode + retry logic with exponential backoff
- **Invalid Signal:** Validate (entry < TP, entry > SL, confidence ∈ [0,1]) before append; reject invalid
- **Network Flake:** Retry up to 3 times with 2s delay; if all fail, publish warning to Discord, skip scan cycle

**Logging:**
- All scanners log to file + console: `logging.basicConfig(level=logging.INFO)`
- Error logs include: timestamp, symbol, algorithm ID, error message, stack trace
- Warning logs: "TP/SL validation failed: BTC signal entry=45000 > TP=44500"

## Cross-Cutting Concerns

**Logging:**
- Approach: Python `logging` module with formatters
- **Where:** Each scanner has `logger = logging.getLogger(__name__)`
- **What:** Signal generation start/end, API latency, model train metrics, elimination decisions
- **Example:** `logger.info(f"Pump detector found {len(signals)} signals in 2.3s")`

**Validation:**
- Approach: Type hints + runtime assertion before write
- **Where:** SignalResult/SignalFeatures construction
- **What:** Confidence ∈ [0,1], entry < TP, entry > SL, symbol in known list
- **Example:** `assert 0 <= signal.confidence <= 1, f"Bad confidence {signal.confidence}"`

**Authentication:**
- Approach: Environment variables (.env file, gitignored)
- **Where:** API client initialization (Binance, CoinGecko, Discord)
- **What:** `COINGECKO_API_KEY`, `DISCORD_WEBHOOK_URL`, `CRYPTOQUANT_API_KEY`
- **Fallback:** Hardcoded URLs for free-tier endpoints; fallback to demo API keys (rate-limited)

**Configuration:**
- Approach: Centralized config modules
- **Where:** `alpha_engine/config.py`, `ml_crypto_predictor/enhanced_models/config.py`
- **What:** Symbol lists, API endpoints, model hyperparameters, risk limits
- **Example:** `CRYPTO_SYMBOLS = ["BTC-USD", "ETH-USD", ...]`; `ICHIMOKU_PARAMS = {"tenkan": 9, ...}`

---

*Architecture analysis: 2026-02-23*

# External Integrations

**Analysis Date:** 2026-02-23

## APIs & External Services

**Market Data:**
- CoinGecko - Crypto market data, trending coins, exchange volumes
  - SDK/Client: requests library (manual HTTP)
  - Auth: `COINGECKO_API_KEY` (GitHub Secrets) or `.env`
  - Endpoint: `https://api.coingecko.com/api/v3` (free) or `https://pro-api.coingecko.com/api/v3` (Pro)
  - Implementation: `KIMI_RISEOFTHECLAW/api_config.py` - `get_coingecko_headers()` function
  - Fallback: Used when crypto price data unavailable from yfinance

- CoinDesk - BTC price data and crypto news
  - SDK/Client: requests library
  - Auth: `COINDESK_API_KEY`
  - Implementation: `KIMI_RISEOFTHECLAW/api_config.py`

- Binance - Spot and perpetual futures data (largest crypto exchange)
  - SDK/Client: Manual HTTP (requests), no official Python SDK used
  - Endpoints: `https://api.binance.com` (spot), `https://fapi.binance.com` (futures)
  - Config: `alpha_engine/config.py` - BINANCE_BASE, BINANCE_FUTURES_BASE
  - Usage: Order book snapshots, liquidation cascades, funding rates

- yfinance - Stock, ETF, forex, and crypto price data (fallback primary source)
  - SDK/Client: yfinance 0.2.0+
  - Auth: None required (free)
  - Usage: 1y daily data, 60d hourly data (alpha_engine/config.py: YF_PERIOD_DAILY, YF_PERIOD_HOURLY)
  - Fallback chain: yfinance → Alpha Vantage → HTML scrapers (scripts/api_integrations.py)

- Alpha Vantage - Stock technical analysis and time series data
  - SDK/Client: requests library
  - Auth: `ALPHA_VANTAGE_KEY` (env var)
  - Endpoint: `https://www.alphavantage.co/query`
  - Function: TIME_SERIES_DAILY (implements scripts/api_integrations.py)
  - Fallback: Used only when yfinance fails

- CryptoCompare - Multi-asset price and volume data
  - SDK/Client: requests library
  - Auth: `CRYPTOCOMPARE_API_KEY` (hardcoded in live_trading_bot_canada.py - insecure)
  - Endpoint: `https://min-api.cryptocompare.com/data`
  - Fallback: Alternative crypto price source

- Alternative.me Fear & Greed Index - Sentiment indicator
  - SDK/Client: requests library
  - Auth: None required (free)
  - Endpoint: `https://api.alternative.me/fng/`
  - Config: `alpha_engine/config.py` - FEAR_GREED_URL
  - Usage: Contrarian signal (buy fear ≤10)

**On-Chain Analytics:**
- CryptoQuant - Exchange flows, miner data, on-chain metrics
  - SDK/Client: requests library (manual HTTP)
  - Auth: `CRYPTOQUANT_API_KEY` (Bearer token)
  - Endpoint: `https://api.cryptoquant.com/v1/`
  - Implementation: `KIMI_RISEOFTHECLAW/api_config.py` - `get_exchange_netflow()` function
  - Signals: Exchange netflow, miner outflow, SOPR, MVRV ratio

- CryptoScan - Blockchain token analysis
  - SDK/Client: requests library
  - Auth: `CRYPTOSCAN_API_KEY`
  - Implementation: `KIMI_RISEOFTHECLAW/api_config.py`

- Glassnode - On-chain metrics and derivatives data (optional)
  - Auth: `GLASSNODE_API_KEY` (placeholder in onchain_metrics_agent.py)
  - Status: Placeholder implementation (not currently active)

**Forex & Currency Data:**
- CurrencyLayer - Real-time forex rates (168 currencies)
  - SDK/Client: requests library (urllib)
  - Auth: `CURRENCYLAYER_API_KEY`
  - Endpoint: `http://apilayer.net/api/live`
  - Rate limits: 250 req/month (free plan)
  - Implementation: `KIMI_RISEOFTHECLAW/api_config.py` - `get_live_forex_rates()` with fallback chain
  - Usage: Carry trade differentials calculation

- Frankfurter API - Fallback forex rates (free, unlimited)
  - SDK/Client: requests library (urllib)
  - Auth: None required
  - Endpoint: `https://api.frankfurter.dev/v1/latest`
  - Fallback: Used when CurrencyLayer unavailable
  - Format converter: Converts to CurrencyLayer format internally

- yfinance forex - Last-resort fallback
  - Format: `{currency}=X` tickers (e.g., `EUR=X`)
  - Fallback: Used when both CurrencyLayer and Frankfurter fail

## Data Storage

**Databases:**
- MySQL 8.0+ (primary production database)
  - Connection: mysql-connector-python 8.2.0+
  - Credentials: `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` (env vars)
  - Default (from `scripts/api_integrations.py`): mysql.50webs.com, ejaguiar1_stocks
  - Schema: `trading_system/database/schema.sql` - TimescaleDB extensions with hypertables
  - Tables: orders, fills, positions, market_ticks, order_book_snapshots, signals, trades statistics
  - ORM: None (raw SQL via mysql-connector-python)

- SQLite (local persistence)
  - File: `KIMI_FEB172026/data/kimi_trading.db` - Live trading signals and picks
  - File: `KIMI_RISEOFTHECLAW/data/kimi_trading.db` - Signal history
  - File: `KIMI_RISEOFTHECLAW/data/signal_tracker.db` - TP/SL validation
  - File: `ml_crypto_predictor/model_health.db` - Model health metrics
  - File: `ab_testing_agent/ab_testing.db` - A/B test results
  - File: `ab_testing_agent/crypto_data.db` - Cached market data
  - Client: sqlite3 (Python built-in)
  - Implementation: `KIMI_FEB172026/sqlite_store.py`

- PostgreSQL with TimescaleDB (schema defined but not active in current deploy)
  - Schema: `trading_system/database/schema.sql` uses TimescaleDB extensions
  - Status: Prepared but using MySQL in production

**File Storage:**
- Local filesystem (no cloud storage used)
  - Model files: `ml_crypto_predictor/enhanced_models/models/` (XGBoost, LightGBM, RandomForest, ensemble joblib files)
  - Results: `ml_crypto_predictor/enhanced_models/results/` (JSON backtest summaries)
  - Live data: `KIMI_FEB172026/data/` (JSON signal files)
  - Dashboards: GitHub Pages (`gh-pages` branch, auto-deployed)

**Caching:**
- None (no Redis, Memcached, or CDN)
- In-memory caching: Implicit via pandas/numpy dataframes during execution
- Parquet format: Optional (DATA_STORAGE_FORMAT in alpha_engine/config.py) for 2-3x compression on large datasets

## Authentication & Identity

**Auth Provider:**
- Custom (no external OAuth/SAML)
  - API keys loaded from environment: `api_config.py` uses local `.env` first, then OS env
  - GitHub Actions Secrets: Used for CI/CD environment variable injection
  - No user authentication layer (system operates autonomously)

**Social / Data Feed Authentication:**
- Telegram - API-based signal injection
  - SDK/Client: Telethon (optional, commented in KIMI_FEB172026/requirements.txt)
  - Auth: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`
  - Implementation: livetelegrambot in live_scanner.py (referenced but not fully activated)

- Twitter/X - Social sentiment and alpha calls
  - SDK/Client: tweepy (optional, commented in requirements.txt)
  - Auth: `TWITTER_BEARER_TOKEN`
  - Implementation: Referenced in live_scanner.py (twitter-alpha-scout strategy)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, or error tracking service)
- Local logging: Python logging module (basicConfig in strategy files)
- Log files: `.log` files in root directory (data_validator.log, l2_orderbook.log, etc.)

**Logs:**
- File-based: Log files written to working directory
- Stdout: GitHub Actions workflow logs (viewable in Actions tab)
- Dashboard: HTML live dashboards regenerated on each cycle
- Database logging: SQLite records trade events and signals

**Monitoring Dashboards:**
- HTML dashboards: Generated by Python scripts and deployed via FTP
  - `alpha_engine/live_dashboard.html` - Alpha Engine picks and stats
  - `riseoftheclaw.html` - KIMI trading signals (GitHub Pages + 50webs FTP)
  - `updates/index.html` - Event log and deployment tracker

## CI/CD & Deployment

**Hosting:**
- GitHub (main repository)
- 50webs FTP (findtorontoevents.ca) - Shared hosting for dashboards
- torontoevent.net FTP - Secondary hosting for resilience
- GitHub Pages (eltonaguiar.github.io) - GUARANTEED uptime for dashboards

**CI Pipeline:**
- GitHub Actions - Primary CI/CD orchestration
  - Trigger: Scheduled cron jobs (15-min intervals typical)
  - Workflows: 40+ YAML files in `.github/workflows/`
  - Runners: ubuntu-latest
  - Timeout: 12 minutes typical
  - Actions used:
    - actions/checkout@v4
    - actions/setup-python@v5
    - actions/setup-node@v4 (for npm dependencies)
  - Deployment: FTP push to 50webs and torontoevent.net

**Deployment Pipeline:**
1. Checkout → 2. Setup Python/Node → 3. Install dependencies → 4. Run scanner/trainer → 5. Generate HTML → 6. Commit changes → 7. FTP push → 8. GitHub Pages auto-deploy
- No automated testing (no pytest run in CI)
- No rollback mechanism (direct overwrite of files on FTP)

## Environment Configuration

**Required env vars (GitHub Secrets for CI/CD):**
- `COINGECKO_API_KEY` - Pro API for trending/market data
- `CRYPTOQUANT_API_KEY` - Bearer token for on-chain metrics
- `CURRENCYLAYER_API_KEY` - Access key for forex rates
- `COINDESK_API_KEY` - BTC and market news data
- `TWITTER_BEARER_TOKEN` - X API for social signals (unused in current deploy)
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` - Telegram bot credentials (unused)

**Required local .env (development):**
- `COINGECKO_API_KEY`
- `CRYPTOQUANT_API_KEY`
- `CURRENCYLAYER_API_KEY`
- `COINDESK_API_KEY`
- `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` (MySQL credentials)
- `ALPHA_VANTAGE_KEY` (optional, fallback for stocks)
- `CRYPTOSCAN_API_KEY` (optional)
- `BINANCE_API_KEY`, `BINANCE_SECRET` (optional, for live trading)
- `KUCOIN_API_KEY`, `KUCOIN_SECRET` (optional)

**Secrets location:**
- Production: GitHub Actions Secrets (not visible in code)
- Development: `KIMI_RISEOFTHECLAW/.env` (gitignored)
- Local defaults: Hardcoded fallbacks (insecure - see live_trading_bot_canada.py)

## Webhooks & Callbacks

**Incoming Webhooks:**
- None active (no incoming webhook endpoints)

**Outgoing Webhooks:**
- None (trading signals are written to JSON files and dashboards, not sent to external services)

**Signal Distribution:**
- JSON files: `data/live_signals_now.json`, `data/active_picks.json`
- HTML dashboards: Regenerated on each cycle and deployed via FTP
- GitHub Pages: Auto-deployed via GitHub Actions (gh-pages branch)

---

*Integration audit: 2026-02-23*

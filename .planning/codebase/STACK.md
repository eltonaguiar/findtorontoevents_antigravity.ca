# Technology Stack

**Analysis Date:** 2026-02-23

## Languages

**Primary:**
- Python 3.11+ - Main codebase for trading algorithms, ML models, and data processing
- JavaScript/TypeScript - Browser testing and frontend automation (Playwright, Puppeteer)
- Pine Script v4.0.0 - TradingView strategy implementation (14 strategies)
- PHP - Legacy web scraping and API integrations
- SQL - Database schema definitions (TimescaleDB, MySQL)

**Secondary:**
- HTML/CSS - Dashboard UIs and static content
- Bash - CI/CD workflows and deployment scripts

## Runtime

**Environment:**
- Python 3.11 (GitHub Actions CI/CD)
- Node.js (for Playwright and test automation)

**Package Managers:**
- pip (Python) - Virtual env at `/.venv/`
- npm (Node.js) - Dependencies in `package.json`

**Lockfiles:**
- `package-lock.json` - Present
- `requirements.txt` files in multiple subsystems (present in root and per-module)

## Frameworks

**Core:**
- FastAPI 0.100.0+ - REST API server for live data and strategy execution
- uvicorn 0.23.0+ - ASGI server for FastAPI

**Testing & Automation:**
- Playwright 1.58.1 - Cross-platform browser testing (ChromeOS, Android, VR headsets)
- pytest 7.0.0+ - Python testing framework (optional, in requirements-worldclass.txt)
- Puppeteer 24.36.1 - Headless browser automation (legacy support)

**Build/Dev:**
- GitHub Actions - CI/CD orchestration (40+ workflows in `.github/workflows/`)
- Jupyter 1.0.0+ - Research and interactive development

## Key Dependencies

**Data & ML Stack:**
- pandas 2.0.0+ - DataFrames and tabular data processing
- numpy 1.24.0+ - Numerical computing and arrays
- scikit-learn 1.3.0+ - Machine learning algorithms (RandomForest, preprocessing)
- xgboost 1.7.0+ - Gradient boosting for ensemble models
- lightgbm 4.0.0+ - Fast gradient boosting (38 models in `ml_crypto_predictor/enhanced_models/models/`)
- catboost 1.2.0+ - Categorical boosting (optional, in requirements-worldclass.txt)
- torch 2.0.0+ - Deep learning (CPU version, can enable GPU)
- scipy 1.10.0+ - Scientific computing (statistics, optimization)
- joblib 1.3.0+ - Model serialization (used for `.joblib` model files)
- imbalanced-learn 0.11.0+ - SMOTE and sampling techniques

**Feature Engineering & Analysis:**
- featuretools 1.28.0+ - Automated feature generation (optional)
- shap 0.41.0+ - Model interpretability and feature importance
- hmmlearn 0.3.2+ - Hidden Markov Models for regime detection
- hurst 0.0.5+ - Hurst exponent calculation for market structure

**Data Fetching:**
- yfinance 0.2.0+ - Yahoo Finance data for stocks, crypto, forex (fallback when APIs unavailable)
- requests 2.31.0+ - HTTP client for API calls
- aiohttp 3.8.0+ - Async HTTP client for concurrent API fetching
- beautifulsoup4 4.12.0+ - HTML/XML scraping (legacy scrapers)
- feedparser 6.0.0+ - RSS feed parsing for news sentiment
- pandas-datareader 0.10.0+ - Alternative data sources (deprecated, kept for compatibility)

**Database & Storage:**
- mysql-connector-python 8.2.0+ - MySQL connection driver
- sqlite3 (built-in) - SQLite local storage (`data/kimi_trading.db`, `data/signal_tracker.db`)
- psycopg2 (optional) - PostgreSQL driver (schema references TimescaleDB)
- pyarrow 12.0.0+ - Parquet format support (DATA_STORAGE_FORMAT in alpha_engine/config.py)

**Visualization & Reporting:**
- matplotlib 3.7.0+ - Static plotting
- seaborn 0.12.0+ - Statistical plotting
- plotly 5.15.0+ - Interactive dashboards
- jinja2 3.1.0+ - HTML template rendering for reports

**Utilities:**
- python-dotenv 1.0.0+ - Environment variable loading from `.env` files
- pyyaml 6.0+ - YAML configuration parsing
- rich 13.0.0+ - Terminal output formatting
- tabulate 0.9.0+ - ASCII table generation
- tqdm 4.65.0+ - Progress bars
- pydantic 2.0.0+ - Data validation and serialization

**Sentiment & NLP (Optional):**
- textblob 0.17.0+ - Basic sentiment analysis
- vaderSentiment 3.3.2+ - Lexicon-based sentiment for social feeds

**Development Tools (Optional):**
- black 23.0.0+ - Code formatter
- flake8 6.0.0+ - Linter
- mypy 1.0.0+ - Type checking
- pytest-cov 4.0.0+ - Coverage reporting

## Configuration

**Environment:**
- `.env` files in subsystem directories (never committed to git)
  - `KIMI_RISEOFTHECLAW/.env` - API keys for CoinGecko, CryptoQuant, CurrencyLayer
  - `KIMI_FEB172026/.env` - Trading system env vars
  - Root `.env` - Application-wide secrets
- GitHub Actions Secrets for CI/CD (COINGECKO_API_KEY, CRYPTOQUANT_API_KEY, CURRENCYLAYER_API_KEY, COINDESK_API_KEY, TWITTER_BEARER_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH)
- Environment variable precedence: Local `.env` file → OS environment variables (for GitHub Actions)

**Build:**
- `playwright.config.ts` - Browser automation configuration (desktop, mobile, VR headsets)
- Multiple workflow YAML files in `.github/workflows/` for scheduled and manual CI/CD

**Configuration Files:**
- `alpha_engine/config.py` - Symbol universes, risk parameters, timeframes, API endpoints
- `ml_crypto_predictor/enhanced_models/config.py` - ML pair definitions (41 crypto pairs), model types, timeframes
- `KIMI_FEB172026/config/telegram_channels.json` - Telegram signal source configuration
- `KIMI_RISEOFTHECLAW/api_config.py` - Centralized API key and endpoint loader
- `scripts/api_integrations.py` - Database connection and API failover logic

## Platform Requirements

**Development:**
- Python 3.11+ (required for type hints and match statements)
- Node.js 18+ (for Playwright/Puppeteer)
- Windows 11 / Linux / macOS (cross-platform)
- RAM: 2GB+ (typical), 4GB+ for heavy ML training
- Network: Outbound HTTPS for APIs (Binance, CoinGecko, CryptoQuant, Telegram, Twitter)

**Production:**
- Linux (Ubuntu 20.04+ typical for GitHub Actions)
- Python 3.11+
- TimescaleDB (PostgreSQL with TimescaleDB extension) or MySQL 8.0+
- 2GB+ RAM for running autonomous traders
- Always-on network for live trading and monitoring
- GitHub Actions runner (Ubuntu) for scheduled tasks (15-min intervals typical)

**Deployment Targets:**
- GitHub Actions (primary CI/CD runner)
- 50webs FTP (`findtorontoevents.ca`) - Shared hosting for dashboards
- torontoevent.net FTP - Mirror deployment for resilience
- GitHub Pages - GUARANTEED uptime for dashboards (https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/)

---

*Stack analysis: 2026-02-23*

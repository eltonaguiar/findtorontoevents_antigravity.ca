# AsterDEX Production Trading System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build a production-ready paper trading system on AsterDEX that tracks a portfolio locally and via GitHub Actions. Once it demonstrates consistent daily profitability over 2+ weeks, flip the switch to live trading with real funds.

**Architecture:** Local Python strategy runner scans markets every 5 min, generates signals from proven strategies (Battleground winners + predictions inversion), executes via AsterDEX SDK in paper mode, tracks all positions in SQLite. GitHub Actions workflow runs the scanner on schedule for 24/7 operation. A dashboard shows live PnL, win rate, and drawdown.

**Tech Stack:** Python 3.11, aster-connector-python SDK, SQLite, Binance klines API (free market data), GitHub Actions

---

## Context: What We Know

### Proven Strategies (from real audit of 529 closed trades)
1. **crypto_rsi_whaleconfirmed_v1** — 34 trades, 70.6% WR, Sharpe 5.73, PF 2.24 (BEST)
2. **atr_regime_rsi** — 32 trades, 56.2% WR, Sharpe 3.45, PF 1.62
3. **multi_period_rsi_confluence** — 22 trades, 72.7% WR, Sharpe 10.86, PF 3.77 (needs more trades)
4. **predictions_inversion** — TBD (23% WR predictions → ~77% inverted, under analysis)

### AsterDEX API
- REST: `https://fapi.asterdex.com`, WS: `wss://fstream.asterdex.com`
- Python SDK: `pip install aster-connector-python`
- Fees: 0.01% maker / 0.035% taker (perps)
- All order types: LIMIT, MARKET, STOP, TAKE_PROFIT, TRAILING_STOP
- Auth: HMAC SHA256 via API key/secret

### Existing Code (already built)
- `trading/position_manager.py` — SQLite position tracker with risk limits
- `trading/asterdex_executor.py` — Paper + live execution via SDK
- `trading/strategy_runner.py` — Basic RSI scanner (needs upgrade)
- `cross_aggregation/aggregator.py` — Cross-system consensus (fixed bugs)
- `genome/bayesian_optimizer.py` — TPE hyperparameter optimizer
- `battleground/` — Contains the proven strategies

### Scan Symbols (from playbook research)
BTCUSDT, ETHUSDT, SOLUSDT, APTUSDT, TIAUSDT, DOTUSDT, ADAUSDT, AVAXUSDT, XLMUSDT, ALGOUSDT

---

## Task 1: Port Proven Battleground Strategies to Trading Module

**Files:**
- Read: `battleground/strategies/` (find crypto_rsi_whaleconfirmed_v1, atr_regime_rsi, multi_period_rsi_confluence)
- Create: `trading/proven_strategies.py`
- Modify: `trading/strategy_runner.py`

**What to build:**
Port the exact logic of the 3 proven strategies from battleground into `trading/proven_strategies.py`. Each strategy must:
- Accept klines data (OHLCV) and return a signal dict or None
- Include the EXACT same indicator calculations and thresholds that produced the 70.6%, 56.2%, and 72.7% WRs
- No "improvements" — replicate what worked

Wire them into `strategy_runner.py` replacing the basic RSI scanner.

**Acceptance criteria:**
- All 3 strategies can be called with klines data and return signals
- strategy_runner.py uses these instead of the basic RSI logic
- Paper trade test produces signals on current market data

---

## Task 2: Build Predictions Inversion Contrarian Strategy

**Files:**
- Read: `predictions/data/predictions.db`, `predictions/validation/price_validator.py`
- Create: `trading/contrarian_predictions.py`
- Modify: `trading/strategy_runner.py`

**What to build:**
A contrarian strategy that reads the latest social media predictions and inverts them:
- Load latest unvalidated predictions from the DB
- Invert direction (LONG→SHORT, SHORT→LONG)
- Swap TP/SL
- Filter: only invert predictions from predictors with < 35% historical WR
- Output signals in the same format as proven_strategies.py

**Acceptance criteria:**
- Can load predictions and invert them
- Filters by predictor WR (only invert reliably-wrong predictors)
- Integrated into strategy_runner.py as a 4th strategy source
- Tested with current data

---

## Task 3: Build Backtester with Realistic Conditions

**Files:**
- Create: `trading/backtester.py`

**What to build:**
A backtester that tests strategies against historical klines data with realistic conditions:
- Fetch historical klines from Binance (free API, up to 1000 candles per request)
- Apply strategy signals
- Simulate execution with:
  - Entry/exit slippage: 0.05% per side
  - Fees: 0.035% per side (AsterDEX taker rate)
  - TP/SL checking on every candle
  - Time-based exit after 4 hours (from playbook)
- Track position sizing (1% of balance per trade)
- Output: trades list, equity curve, Sharpe, max DD, win rate, profit factor

**Acceptance criteria:**
- Can backtest any strategy from proven_strategies.py against 30+ days of klines
- Accounts for fees and slippage
- Produces a JSON report with all metrics
- Print summary table

---

## Task 4: GitHub Actions Automated Paper Trading Workflow

**Files:**
- Create: `.github/workflows/asterdex-paper-trading.yml`
- Modify: `trading/strategy_runner.py` (add `--github-actions` mode)

**What to build:**
A GitHub Actions workflow that runs the strategy runner every 5 minutes:
- Checkout repo, setup Python, install deps
- Run `python -m trading.strategy_runner --mode paper --once --balance 1000`
- Check TP/SL on open positions
- Commit updated positions.db and signals_log.json
- Push results
- Post daily summary to Discord at 00:00 UTC

The `--github-actions` mode should:
- Use file-based state (positions.db committed to repo)
- Output a JSON summary for the workflow to parse
- Handle the case where multiple runs happen concurrently (file locking)

**Acceptance criteria:**
- Workflow runs every 5 min on GitHub Actions
- Positions persist across runs via committed SQLite DB
- Daily Discord summary with PnL, WR, open positions
- No concurrent-run conflicts

---

## Task 5: Portfolio Dashboard (HTML)

**Files:**
- Create: `trading/dashboard.html`
- Modify: `.github/workflows/asterdex-paper-trading.yml` (deploy dashboard)

**What to build:**
A single-page HTML dashboard (dark theme, matching project style) showing:
- Current portfolio balance and PnL ($ and %)
- Equity curve chart (using Chart.js)
- Open positions table with live unrealized PnL
- Closed trades table with outcomes
- Win rate, Sharpe, profit factor, max drawdown
- Strategy breakdown (which strategy contributes most)
- Status: PAPER or LIVE mode indicator
- Auto-refresh every 60 seconds from a JSON data file

The dashboard reads from `trading/data/dashboard_data.json` generated by the strategy runner.

**Acceptance criteria:**
- Dashboard renders correctly with sample data
- Shows all key metrics
- Auto-refreshes
- Deployed to GitHub Pages alongside existing dashboards
- Dark theme consistent with project style

---

## Phased Rollout

### Phase 1 (Tasks 1-3): Build & Backtest
- Port strategies, build backtester
- Run backtests on 30-90 days of data
- **Gate:** All strategies must show positive Sharpe after fees/slippage

### Phase 2 (Tasks 4-5): Paper Trading
- Deploy GitHub Actions workflow
- Run paper trading for 2+ weeks
- **Gate:** Must achieve >55% WR and positive PnL over 100+ trades

### Phase 3 (Future): Live Trading
- Set ASTERDEX_API_KEY and ASTERDEX_API_SECRET in GitHub Secrets
- Change `--mode paper` to `--mode live` in workflow
- Start with $100-500, max 1% per trade
- **Gate:** 2 weeks profitable paper trading, user approval

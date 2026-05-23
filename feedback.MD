# Feedback on the Real‑Time Crypto Scanner (NOW.py)

## Overview
The **NOW.py** script is a self‑contained, single‑file scanner that fetches 1‑hour and 5‑minute klines for the top 50 USDT pairs, runs eight proven strategies, scores and ranks signals, and logs every "guess" to a MySQL `now_history` table.  Results are exported to `findcryptopairs/now.html` and deployed via the existing FTP workflow.  The scanner prioritises short‑term (≤ 1h) opportunities, making it ideal for rapid‑turnaround trading.

## Architecture
- **Single‑script design** – all logic lives in [`NOW.py`](NOW.py) at the project root.
- **Data sources** – Binance API with a CoinGecko fallback.
- **Database** – MySQL tables `now_history` and `now_strategy_stats` in the `ejaguiar1_stocks` schema.
- **HTML report** – generated at `findcryptopairs/now.html` and auto‑refreshed via the API pattern.
- **CI/CD** – GitHub Actions workflow `now-scanner.yml` runs the script every 15 minutes, commits the HTML, and triggers the FTP deploy.

## Strategies (8 total)
| # | Strategy | Basis | Signal Logic |
|---|----------|-------|--------------|
| 1 | MACD Crossover 5m | Classic | MACD line crosses signal line from below on 5m, histogram turning positive |
| 2 | RSI Oversold Bounce | Connors RSI‑2 adapted | RSI(14) drops below 30 then crosses back above 30 on 5m |
| 3 | MACD + RSI Confluence | Proven 65 % WR | MACD bullish cross **and** RSI < 40 recovering |
| 4 | Volume Spike Breakout | KIMI acceleration engine | Volume > 3× 20‑period avg **and** price breaks above 1h high |
| 5 | Bollinger Squeeze Expansion | Baby strat proven | BB width at 20‑period low, price breaks above upper band |
| 6 | EMA Stack Alignment | Multi‑TF EMA cloud | 9 > 21 > 50 EMA on 5m, price pulls back to 9 EMA and bounces |
| 7 | Funding Rate Reversal | 71 % WR proven | Negative funding **and** reversal candle (doji/hammer) |
| 8 | Stoch RSI + MACD Combo | Advanced confluence | StochRSI K crosses above D from oversold **and** MACD histogram positive |

Each strategy returns a JSON‑like object:
```json
{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry_price": 0.00,
  "confidence": 0.85,
  "reason": "MACD bullish cross + RSI recovering",
  "sl_price": 0.00,
  "tp_price_1_5": 0.00,
  "tp_price_2_0": 0.00
}
```

## Database Schema
### `now_history`
```sql
CREATE TABLE now_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(36),
    scan_time DATETIME,
    symbol VARCHAR(20),
    direction ENUM('LONG','SHORT'),
    strategy VARCHAR(50),
    entry_price DECIMAL(20,8),
    sl_price DECIMAL(20,8),
    tp_price_1_5 DECIMAL(20,8),
    tp_price_2_0 DECIMAL(20,8),
    confidence DECIMAL(5,2),
    reason TEXT,
    outcome_1_5 ENUM('PENDING','TP_HIT','SL_HIT','EXPIRED') DEFAULT 'PENDING',
    outcome_2_0 ENUM('PENDING','TP_HIT','SL_HIT','EXPIRED') DEFAULT 'PENDING',
    peak_price DECIMAL(20,8),
    trough_price DECIMAL(20,8),
    resolved_at DATETIME,
    actual_pnl_pct DECIMAL(8,4),
    INDEX idx_symbol (symbol),
    INDEX idx_strategy (strategy),
    INDEX idx_scan_time (scan_time)
);
```

### `now_strategy_stats`
```sql
CREATE TABLE now_strategy_stats (
    strategy VARCHAR(50) PRIMARY KEY,
    total_picks INT DEFAULT 0,
    wins_1_5 INT DEFAULT 0,
    losses_1_5 INT DEFAULT 0,
    wins_2_0 INT DEFAULT 0,
    losses_2_0 INT DEFAULT 0,
    expired INT DEFAULT 0,
    win_rate_1_5 DECIMAL(5,2),
    win_rate_2_0 DECIMAL(5,2),
    avg_pnl_pct DECIMAL(8,4),
    best_trade_pct DECIMAL(8,4),
    worst_trade_pct DECIMAL(8,4),
    last_updated DATETIME
);
```

## Data Flow
```
NOW.py
 ├─ Fetch 50 USDT pairs (Binance 5m + 1h, fallback to CoinGecko)
 ├─ Run 8 strategies → generate signals
 ├─ Score & rank (confidence × strategy_win_rate × volume_weight)
 ├─ Resolve PENDING picks from previous runs (check 1h candle data)
 ├─ INSERT new picks → now_history
 ├─ UPDATE now_strategy_stats
 ├─ Generate findcryptopairs/now.html (top picks + track record)
 └─ Print summary to terminal
```

## HTML Report (`findcryptopairs/now.html`)
- **Top Picks Now** – ranked by composite score, showing symbol, entry, TP/SL, confidence, strategy, reason.
- **Track Record** – win rates per strategy for both R:R ratios, total PnL.
- **Recent History** – last 50 picks with outcomes (TP hit, SL hit, expired, pending).
- **Live auto‑refresh** – pulls latest data from `now_history` via the existing API pattern.

## CI/CD (`now-scanner.yml`)
- Runs `NOW.py` every 15 minutes.
- Commits the generated `now.html` back to the repository.
- Triggers the FTP deploy workflow `deploy-findcryptopairs-ftp.yml`.

## Feedback & Recommendations
1. **Error handling for data source fallback** – ensure the CoinGecko fallback is robust and logs failures without aborting the whole scan.
2. **Parallel fetching** – consider using `asyncio` or thread pools to fetch klines concurrently, reducing scan latency.
3. **Configurable pair list** – expose the top‑N parameter (currently 50) via a config file or CLI argument.
4. **Strategy modularisation** – move each strategy into its own module under `alpha_engine/strategies/` to improve maintainability and allow hot‑reloading.
5. **Unit tests for each strategy** – add a test suite that validates signal generation against known market scenarios.
6. **Performance metrics** – log execution time per scan and per strategy; add these to the HTML dashboard for visibility.
7. **Security** – store MySQL credentials in environment variables or a secret manager, never hard‑code them.
8. **Documentation** – create a brief `README.md` for `NOW.py` that explains setup, dependencies, and how to run it locally.

Overall, the design is solid and the implementation aligns well with the project's existing patterns. Addressing the points above will make the scanner more reliable, maintainable, and easier to extend.

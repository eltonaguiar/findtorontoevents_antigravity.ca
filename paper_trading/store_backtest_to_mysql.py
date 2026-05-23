#!/usr/bin/env python3
"""Store backtest results and per-symbol catering data in MySQL audit trail.

Creates/updates at_strategy_symbol_performance table with:
- Per-strategy overall metrics
- Per-strategy-per-symbol breakdown (catering analysis)
- is_catered flag for strategy-symbol pairs that work well

Reads from paper_trading/data/backtest_results.json (written by backtest_runner.py).
Requires MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB env vars.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("backtest_mysql")

DATA_DIR = Path(__file__).parent / "data"
RESULTS_FILE = DATA_DIR / "backtest_results.json"


def store_results():
    if not RESULTS_FILE.exists():
        logger.warning("No backtest results found at %s", RESULTS_FILE)
        return 0

    try:
        import pymysql
    except ImportError:
        logger.warning("pymysql not installed — skipping MySQL store")
        return 0

    host = os.environ.get("MYSQL_HOST")
    if not host:
        logger.warning("MYSQL_HOST not set — skipping MySQL store")
        return 0

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    conn = pymysql.connect(
        host=host,
        user=os.environ.get("MYSQL_USER", ""),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DB", ""),
        charset="utf8mb4",
    )
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS at_strategy_symbol_performance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            strategy_name VARCHAR(100) NOT NULL,
            display_name VARCHAR(200),
            symbol VARCHAR(20) NOT NULL,
            portfolio_type VARCHAR(50),
            total_trades INT DEFAULT 0,
            wins INT DEFAULT 0,
            win_rate DECIMAL(5,2) DEFAULT 0,
            avg_pnl_pct DECIMAL(8,4) DEFAULT 0,
            profit_factor DECIMAL(8,3) DEFAULT 0,
            sharpe DECIMAL(8,3) DEFAULT 0,
            max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
            best_trade_pct DECIMAL(8,4) DEFAULT 0,
            worst_trade_pct DECIMAL(8,4) DEFAULT 0,
            test_interval VARCHAR(10) DEFAULT '1h',
            test_bars INT DEFAULT 500,
            is_catered TINYINT(1) DEFAULT 0,
            tested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_strat_sym (strategy_name, symbol, test_interval)
        )
    """)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = 0

    for strat_name, r in results.items():
        sym_data = r.get("per_symbol", {})
        display = r.get("display_name", strat_name)
        portfolio = "incubator" if strat_name.startswith("incub_") else "verified"

        # Per-symbol rows
        for sym, stats in sym_data.items():
            wr = stats.get("wr", 0)
            is_catered = 1 if wr >= 50 and stats.get("trades", 0) >= 2 else 0
            cur.execute("""
                INSERT INTO at_strategy_symbol_performance
                (strategy_name, display_name, symbol, portfolio_type, total_trades, wins,
                 win_rate, avg_pnl_pct, is_catered, test_interval, test_bars, tested_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_trades = VALUES(total_trades), wins = VALUES(wins),
                    win_rate = VALUES(win_rate), avg_pnl_pct = VALUES(avg_pnl_pct),
                    is_catered = VALUES(is_catered), tested_at = VALUES(tested_at)
            """, (strat_name, display, sym, portfolio,
                  stats.get("trades", 0), stats.get("wins", 0),
                  wr, stats.get("avg_pnl", 0), is_catered, "1h", 500, now))
            rows += 1

        # Overall row
        if r.get("total", 0) > 0:
            cur.execute("""
                INSERT INTO at_strategy_symbol_performance
                (strategy_name, display_name, symbol, portfolio_type, total_trades, wins,
                 win_rate, avg_pnl_pct, profit_factor, sharpe, max_drawdown_pct,
                 best_trade_pct, worst_trade_pct, is_catered, test_interval, test_bars, tested_at)
                VALUES (%s, %s, 'ALL', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_trades = VALUES(total_trades), wins = VALUES(wins),
                    win_rate = VALUES(win_rate), avg_pnl_pct = VALUES(avg_pnl_pct),
                    profit_factor = VALUES(profit_factor), sharpe = VALUES(sharpe),
                    max_drawdown_pct = VALUES(max_drawdown_pct),
                    best_trade_pct = VALUES(best_trade_pct), worst_trade_pct = VALUES(worst_trade_pct),
                    tested_at = VALUES(tested_at)
            """, (strat_name, display, portfolio,
                  r["total"], r["wins"], r["win_rate"], r["avg_pnl_pct"],
                  r["profit_factor"], r["sharpe"], r["max_drawdown_pct"],
                  r["best_trade_pct"], r["worst_trade_pct"], "1h", 500, now))
            rows += 1

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Stored %d rows in at_strategy_symbol_performance", rows)
    return rows


if __name__ == "__main__":
    store_results()

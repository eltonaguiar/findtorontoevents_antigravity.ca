import sqlite3
import pandas as pd

with open('E:/findtorontoevents_antigravity.ca/temp_crypto_results.txt', 'w') as f:
    f.write("--- TOP CRYPTO STRATEGIES FROM audit_trail.db (bt_backtest_runs) ---\n")
    try:
        conn = sqlite3.connect('E:/findtorontoevents_antigravity.ca/data/audit_trail.db')
        query = """
        SELECT strategy, symbol, total_trades, win_rate, profit_factor, total_return, sharpe, max_drawdown
        FROM bt_backtest_runs
        WHERE asset_class = 'CRYPTO' AND total_trades > 50
        ORDER BY sharpe DESC, win_rate DESC
        LIMIT 10
        """
        df = pd.read_sql_query(query, conn)
        f.write(df.to_string() + "\n")
        conn.close()
    except Exception as e:
        f.write(str(e) + "\n")

    f.write("\n--- TOP CRYPTO STRATEGIES FROM kimi_trading.db (picks) ---\n")
    try:
        conn = sqlite3.connect('E:/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/data/kimi_trading.db')
        query = """
        SELECT algorithm, COUNT(*) as trades, 
               SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate, 
               AVG(pnl_pct) as avg_pnl
        FROM picks
        WHERE symbol LIKE '%USDT%' AND status IN ('CLOSED', 'WON', 'LOST')
        GROUP BY algorithm
        HAVING trades > 20
        ORDER BY win_rate DESC
        LIMIT 10
        """
        df = pd.read_sql_query(query, conn)
        f.write(df.to_string() + "\n")
        conn.close()
    except Exception as e:
        f.write(str(e) + "\n")

    f.write("\n--- TOP CRYPTO STRATEGIES FROM strategy_registry.db ---\n")
    try:
        conn = sqlite3.connect('E:/findtorontoevents_antigravity.ca/genome/strategy_registry.db')
        query = """
        SELECT name, symbol_specialization, total_trades, win_rate, sharpe_ratio, fitness_score
        FROM strategies
        WHERE (name LIKE '%crypto%' OR symbol_specialization LIKE '%USDT%') AND total_trades > 50
        ORDER BY sharpe_ratio DESC, win_rate DESC
        LIMIT 10
        """
        df = pd.read_sql_query(query, conn)
        f.write(df.to_string() + "\n")
        conn.close()
    except Exception as e:
        f.write(str(e) + "\n")

print("Done. Check temp_crypto_results.txt")

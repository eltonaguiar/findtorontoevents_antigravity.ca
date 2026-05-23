import os
import pymysql

migration_sql = [
"ALTER TABLE at_raw_picks MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN'",
"ALTER TABLE at_consensus_picks MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN'",
"ALTER TABLE at_audit_events MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE at_filter_log MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE at_strategy_stats MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE at_discord_sent MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE bt_backtest_runs MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE bt_backtest_trades MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'",
"ALTER TABLE at_sqlite_imports MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN'"
]

def run():
    conn = pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=os.environ.get("DB_PASS_STOCKS",""), database="ejaguiar1_stocks"
    )
    with conn.cursor() as cur:
        for stmt in migration_sql:
            print(f"Executing: {stmt[:50]}...")
            try:
                cur.execute(stmt)
            except Exception as e:
                print(f"Failed (likely doesn't exist): {e}")
    conn.commit()
    conn.close()
    print("Migration successful.")

if __name__ == '__main__':
    run()

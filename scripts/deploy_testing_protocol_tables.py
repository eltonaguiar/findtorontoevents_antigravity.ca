"""
Deploy TESTING_PROTOCOL.MD Section 9 MySQL Tables
==================================================
Creates the 5 missing tables (+ strategy_status_history) in ejaguiar1_stocks.
Does NOT touch strategy_registry (already exists with different schema).

Usage:  python scripts/deploy_testing_protocol_tables.py
Env:    MYSQL_50WEBS_PASS  (fallback: "stocks")
"""

import os
import sys

# ---------------------------------------------------------------------------
# Connection config
# ---------------------------------------------------------------------------
DB_HOST = "mysql.50webs.com"
DB_PORT = 3306
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.environ.get("MYSQL_50WEBS_PASS", os.environ.get("AUDIT_DB_PASS", "stocks"))
DB_NAME = "ejaguiar1_stocks"

# ---------------------------------------------------------------------------
# DDL statements from TESTING_PROTOCOL.MD Section 9
# ---------------------------------------------------------------------------
TABLES = {
    "strategy_test_runs": """
        CREATE TABLE IF NOT EXISTS strategy_test_runs (
            run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            strategy_id VARCHAR(128) NOT NULL,
            test_layer VARCHAR(32) NOT NULL,
            symbol VARCHAR(64) NULL,
            asset_class VARCHAR(32) NULL,
            period_start DATETIME NULL,
            period_end DATETIME NULL,
            trades INT DEFAULT 0,
            win_rate DECIMAL(8,4) NULL,
            profit_factor DECIMAL(10,4) NULL,
            sharpe DECIMAL(10,4) NULL,
            max_drawdown DECIMAL(10,4) NULL,
            p_value DECIMAL(12,8) NULL,
            q_value_bh DECIMAL(12,8) NULL,
            p_value_bonf DECIMAL(12,8) NULL,
            pass_flag TINYINT(1) DEFAULT 0,
            metadata_json TEXT NULL,
            created_at DATETIME NOT NULL
        )
    """,

    "strategy_symbol_coverage": """
        CREATE TABLE IF NOT EXISTS strategy_symbol_coverage (
            strategy_id VARCHAR(128) NOT NULL,
            symbol VARCHAR(64) NOT NULL,
            asset_class VARCHAR(32) NOT NULL,
            tested_backtest TINYINT(1) DEFAULT 0,
            tested_walkforward TINYINT(1) DEFAULT 0,
            tested_forward TINYINT(1) DEFAULT 0,
            last_result_at DATETIME NULL,
            PRIMARY KEY (strategy_id, symbol)
        )
    """,

    "strategy_whatif_results": """
        CREATE TABLE IF NOT EXISTS strategy_whatif_results (
            whatif_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            strategy_id VARCHAR(128) NOT NULL,
            variant_name VARCHAR(128) NOT NULL,
            variant_type VARCHAR(32) NOT NULL,
            params_json TEXT NOT NULL,
            baseline_win_rate DECIMAL(8,4) NULL,
            baseline_pf DECIMAL(10,4) NULL,
            baseline_trades INT NULL,
            variant_win_rate DECIMAL(8,4) NULL,
            variant_pf DECIMAL(10,4) NULL,
            variant_trades INT NULL,
            delta_win_rate DECIMAL(8,4) NULL,
            delta_pf DECIMAL(10,4) NULL,
            delta_trades INT NULL,
            accepted TINYINT(1) DEFAULT 0,
            created_at DATETIME NOT NULL
        )
    """,

    "test_portfolio_positions": """
        CREATE TABLE IF NOT EXISTS test_portfolio_positions (
            portfolio_name VARCHAR(64) NOT NULL,
            position_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            strategy_id VARCHAR(128) NOT NULL,
            symbol VARCHAR(64) NOT NULL,
            direction VARCHAR(8) NOT NULL,
            entry_price DECIMAL(18,8) NOT NULL,
            take_profit DECIMAL(18,8) NOT NULL,
            stop_loss DECIMAL(18,8) NOT NULL,
            status VARCHAR(16) NOT NULL,
            opened_at DATETIME NOT NULL,
            closed_at DATETIME NULL,
            pnl_pct DECIMAL(10,4) NULL,
            metadata_json TEXT NULL
        )
    """,

    "super_strategy_candidates": """
        CREATE TABLE IF NOT EXISTS super_strategy_candidates (
            strategy_id VARCHAR(128) PRIMARY KEY,
            symbols_passed INT DEFAULT 0,
            asset_classes_passed INT DEFAULT 0,
            regimes_passed INT DEFAULT 0,
            concentration_ratio DECIMAL(10,4) NULL,
            fisher_p DECIMAL(12,8) NULL,
            status VARCHAR(32) NOT NULL,
            notes TEXT NULL,
            updated_at DATETIME NOT NULL
        )
    """,

    "strategy_status_history": """
        CREATE TABLE IF NOT EXISTS strategy_status_history (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            strategy_id VARCHAR(128) NOT NULL,
            from_status VARCHAR(32) NULL,
            to_status VARCHAR(32) NOT NULL,
            reason TEXT NULL,
            changed_at DATETIME NOT NULL
        )
    """,
}

# ---------------------------------------------------------------------------
# Indexes from CHATWITHIT.MD / TESTING_PROTOCOL operational queries
# ---------------------------------------------------------------------------
INDEXES = [
    ("idx_str_layer_created", "strategy_test_runs", "(strategy_id, test_layer, created_at)"),
    ("idx_layer_asset", "strategy_test_runs", "(test_layer, asset_class)"),
    ("idx_str_pass", "strategy_test_runs", "(strategy_id, pass_flag)"),
    ("idx_whatif_strat", "strategy_whatif_results", "(strategy_id)"),
    ("idx_portfolio_strat", "test_portfolio_positions", "(strategy_id)"),
    ("idx_portfolio_status", "test_portfolio_positions", "(status)"),
    ("idx_status_hist_strat", "strategy_status_history", "(strategy_id, changed_at)"),
]


def main():
    # ── Import pymysql (same connector used across the project) ──
    try:
        import pymysql
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pymysql"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import pymysql

    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,
        charset="utf8mb4",
        autocommit=True,
    )
    cur = conn.cursor()
    print("Connected.\n")

    # ── Create tables ──
    created = 0
    failed = 0
    for name, ddl in TABLES.items():
        try:
            cur.execute(ddl)
            print(f"  [OK]   {name}")
            created += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            failed += 1

    # ── Create indexes (compatible with MySQL < 8.0.29) ──
    print()
    idx_ok = 0
    idx_skip = 0
    for idx_name, table, cols in INDEXES:
        sql = f"CREATE INDEX {idx_name} ON {table} {cols}"
        try:
            cur.execute(sql)
            print(f"  [IDX]  {idx_name}")
            idx_ok += 1
        except pymysql.err.OperationalError as exc:
            if "Duplicate key name" in str(exc) or "1061" in str(exc):
                print(f"  [SKIP] {idx_name} (already exists)")
                idx_skip += 1
            else:
                print(f"  [FAIL] {idx_name}: {exc}")
        except Exception as exc:
            print(f"  [FAIL] {idx_name}: {exc}")

    cur.close()
    conn.close()

    print(f"\nDone: {created} tables created, {failed} failed, "
          f"{idx_ok} indexes created, {idx_skip} indexes skipped.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

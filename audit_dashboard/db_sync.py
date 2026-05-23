"""
Portfolio Challenge — Database Sync
====================================
Syncs portfolio state to ejaguiar1_stocks MySQL database for audit trail.
Fire-and-forget: never blocks the portfolio manager if DB is down.
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("portfolio_db_sync")

DB_HOST = os.getenv("AUDIT_DB_HOST")
DB_PORT = os.getenv("AUDIT_DB_PORT")
DB_USER = os.getenv("AUDIT_DB_USER")
DB_PASS = os.getenv("AUDIT_DB_PASS")
DB_NAME = os.getenv("AUDIT_DB_NAME")

# Validate required environment variables
required_vars = {
    "AUDIT_DB_HOST": DB_HOST,
    "AUDIT_DB_USER": DB_USER,
    "AUDIT_DB_PASS": DB_PASS,
    "AUDIT_DB_NAME": DB_NAME,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

DB_PORT = int(DB_PORT or "3306")
EST = timezone(timedelta(hours=-5))


def _get_connection():
    try:
        import pymysql
    except ImportError:
        return None
    try:
        return pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
            database=DB_NAME, connect_timeout=10, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        logger.warning(f"DB connection failed: {e}")
        return None


def ensure_tables(conn):
    """Create tables if they don't exist."""
    migration_path = os.path.join(os.path.dirname(__file__), "..", "audit_trail",
                                   "migrations", "003_portfolio_challenge_tables.sql")
    if not os.path.exists(migration_path):
        return
    try:
        with open(migration_path, "r") as f:
            sql = f.read()
        cursor = conn.cursor()
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                cursor.execute(stmt)
        conn.commit()
    except Exception as e:
        logger.warning(f"Table creation: {e}")


def _category(port):
    mid = port.get("methodology", "")
    if mid in ("drawdown_dca", "rsi_capitulation", "fear_greed", "rel_strength"):
        return "deep_value"
    if mid in ("hoffman", "htf_trend", "htf_momentum"):
        return "hoffman_htf"
    if mid in ("prop_conservative", "prop_aggressive", "prop_swing"):
        return "prop_firm"
    return "signal"


def sync_portfolio_snapshot(conn, port, stats):
    """Insert a snapshot of portfolio state."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO portfolio_snapshots
            (portfolio_id, portfolio_name, methodology, category, status,
             equity, initial_capital, pnl_pct, pnl_usd, win_rate,
             total_trades, open_positions, max_drawdown_pct, sharpe_ratio,
             profit_factor, total_commission, resets, snapshot_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            port["id"], port["name"], port.get("methodology", ""),
            _category(port), port.get("status", "ACTIVE"),
            port["equity"], port["initial_capital"],
            stats["pnl_pct"], stats["pnl_usd"], stats["win_rate"],
            stats["total_trades"], stats["open_positions"],
            stats["max_drawdown_pct"], stats["sharpe"],
            stats["profit_factor"], stats["total_commission"],
            port.get("resets", 0),
            datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
    except Exception as e:
        logger.warning(f"Snapshot sync failed for {port['id']}: {e}")


def sync_positions(conn, port):
    """Upsert current positions and closed trades."""
    try:
        cursor = conn.cursor()
        # Sync open positions
        for pos in port.get("positions", []):
            cursor.execute("""
                INSERT INTO pf_challenge_positions
                (portfolio_id, position_id, symbol, direction, strategy, source_system,
                 entry_price, take_profit, stop_loss, size_usd, pnl_pct, pnl_usd,
                 commission_entry, status, opened_at, rr_ratio, sys_wr, sys_pf, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                pnl_pct=VALUES(pnl_pct), pnl_usd=VALUES(pnl_usd), status=VALUES(status)
            """, (
                port["id"], pos.get("id", ""), pos["symbol"], pos["direction"],
                pos.get("strategy", ""), pos.get("source_system", ""),
                pos["entry_price"], pos.get("take_profit", 0), pos.get("stop_loss", 0),
                pos["size_usd"], pos.get("pnl_pct", 0), pos.get("pnl_usd", 0),
                pos.get("commission_entry", 0), pos.get("status", "OPEN"),
                pos.get("opened_at", datetime.now(EST).isoformat()),
                pos.get("rr", 0), pos.get("sys_wr", 0), pos.get("sys_pf", 0),
                pos.get("confidence", 0),
            ))

        # Sync recently closed
        for pos in port.get("closed", [])[-200:]:
            cursor.execute("""
                INSERT INTO pf_challenge_positions
                (portfolio_id, position_id, symbol, direction, strategy, source_system,
                 entry_price, take_profit, stop_loss, exit_price, size_usd,
                 pnl_pct, pnl_usd, net_pnl_usd, commission_entry, commission_exit,
                 exit_reason, status, opened_at, closed_at, rr_ratio, sys_wr, sys_pf, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                exit_price=VALUES(exit_price), net_pnl_usd=VALUES(net_pnl_usd),
                exit_reason=VALUES(exit_reason), status=VALUES(status), closed_at=VALUES(closed_at)
            """, (
                port["id"], pos.get("id", ""), pos["symbol"], pos["direction"],
                pos.get("strategy", ""), pos.get("source_system", ""),
                pos["entry_price"], pos.get("take_profit", 0), pos.get("stop_loss", 0),
                pos.get("exit_price", 0), pos["size_usd"],
                pos.get("pnl_pct", 0), pos.get("pnl_usd", 0), pos.get("net_pnl_usd", 0),
                pos.get("commission_entry", 0), pos.get("commission_exit", 0),
                pos.get("exit_reason", ""), pos.get("status", "CLOSED"),
                pos.get("opened_at", ""), pos.get("closed_at", ""),
                pos.get("rr", 0), pos.get("sys_wr", 0), pos.get("sys_pf", 0),
                pos.get("confidence", 0),
            ))
        conn.commit()
    except Exception as e:
        logger.warning(f"Position sync failed for {port['id']}: {e}")


def sync_resets(conn, port):
    """Sync reset history."""
    if port.get("resets", 0) == 0:
        return
    try:
        cursor = conn.cursor()
        ls = port.get("lifetime_stats", {})
        for r in ls.get("reset_log", []):
            cursor.execute("""
                INSERT IGNORE INTO portfolio_resets
                (portfolio_id, reset_num, equity_at_reset, pnl_usd, wins, losses,
                 max_drawdown_pct, reason, reset_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                port["id"], r.get("reset_num", 0), r.get("equity_at_reset", 0),
                r.get("pnl_usd", 0), r.get("wins", 0), r.get("losses", 0),
                r.get("max_dd", 0), r.get("reason", ""),
                r.get("time", datetime.now(EST).isoformat()),
            ))
        conn.commit()
    except Exception as e:
        logger.warning(f"Reset sync failed for {port['id']}: {e}")


def sync_all(state, stats_map):
    """Fire-and-forget sync of all portfolio data to MySQL."""
    conn = _get_connection()
    if not conn:
        print("  DB sync: connection failed (will retry next cycle)")
        return False

    try:
        ensure_tables(conn)
        synced = 0
        for pid, port in state.items():
            stats = stats_map.get(pid, {})
            sync_portfolio_snapshot(conn, port, stats)
            sync_positions(conn, port)
            sync_resets(conn, port)
            synced += 1
        print(f"  DB sync: {synced} portfolios synced to ejaguiar1_stocks")
        return True
    except Exception as e:
        print(f"  DB sync error: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass

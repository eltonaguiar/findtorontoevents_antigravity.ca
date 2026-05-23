#!/usr/bin/env python3
"""
Paper Trade MySQL Writer
========================
Syncs paper trading positions to ejaguiar1_stocks.paper_trades table
and generates daily portfolio snapshot to paper_portfolio_daily.

Run as:
    python tools/paper_trade_mysql_writer.py
    python tools/paper_trade_mysql_writer.py --dry-run

Sources (in priority order):
    1. Paper portfolio JSON files from KIMI_RISEOFTHECLAW/data/paper_portfolio.json
    2. TradingView paper portfolio extracts from reports/tv_portfolio_history_*/
    3. Audit trail active picks from audit_dashboard/data/dashboard_data.json

Gated by: PAPER_TRADE_MYSQL_ENABLED env var (truthy = on).
           Defaults to enabled when PICK_OUTCOMES_MYSQL_ENABLED is set.
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
KIMI_PORTFOLIO = ROOT / "KIMI_RISEOFTHECLAW" / "data" / "paper_portfolio.json"
DASHBOARD_DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [paper-mysql] %(message)s")
logger = logging.getLogger("paper_trade_mysql")


def _is_enabled() -> bool:
    """Check if MySQL paper trade writes are enabled."""
    return (
        os.environ.get("PAPER_TRADE_MYSQL_ENABLED", "").lower()
        in ("1", "true", "yes", "on")
    ) or (
        os.environ.get("PICK_OUTCOMES_MYSQL_ENABLED", "").lower()
        in ("1", "true", "yes", "on")
    )


def _get_mysql_config() -> dict:
    """Return MySQL connection config from environment."""
    return {
        "host": os.environ.get("DB_STOCKS_HOST", os.environ.get("DB_HOST", "mysql.50webs.com")),
        "port": int(os.environ.get("DB_STOCKS_PORT", os.environ.get("DB_PORT", "3306"))),
        "user": os.environ.get("DB_STOCKS_USER", os.environ.get("AUDIT_DB_USER", "")),
        "password": os.environ.get("DB_PASS_STOCKS", os.environ.get("DB_STOCKS_PASSWORD", os.environ.get("AUDIT_DB_PASS", ""))),
        "database": os.environ.get("DB_STOCKS_NAME", os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks")),
        "charset": "utf8mb4",
    }


def _load_paper_portfolio_kimi() -> list[dict]:
    """Load paper trades from KIMI paper_portfolio.json."""
    if not KIMI_PORTFOLIO.exists():
        logger.warning(f"KIMI portfolio not found: {KIMI_PORTFOLIO}")
        return []
    try:
        data = json.loads(KIMI_PORTFOLIO.read_text(encoding="utf-8"))
        picks = data.get("positions", data.get("picks", data if isinstance(data, list) else []))
        if isinstance(picks, dict):
            picks = list(picks.values())
        logger.info(f"Loaded {len(picks)} picks from KIMI paper portfolio")
        return picks
    except Exception as e:
        logger.warning(f"Failed to load KIMI portfolio: {e}")
        return []


def _load_active_picks_dashboard() -> list[dict]:
    """Load active picks from dashboard_data.json."""
    if not DASHBOARD_DATA.exists():
        logger.warning(f"Dashboard data not found: {DASHBOARD_DATA}")
        return []
    try:
        data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
        picks = data.get("active_picks", data.get("picks", []))
        if isinstance(picks, dict):
            picks = list(picks.values())
        logger.info(f"Loaded {len(picks)} active picks from dashboard")
        return picks
    except Exception as e:
        logger.warning(f"Failed to load dashboard picks: {e}")
        return []


def _normalize_pick(pick: dict) -> Optional[dict]:
    """Normalize a paper pick dict to match paper_trades schema."""
    symbol = str(pick.get("symbol", pick.get("ticker", pick.get("trading_pair", "")))).upper()[:10]
    if not symbol:
        return None

    # Determine status
    raw_status = str(pick.get("status", "open")).lower()
    if raw_status in ("closed", "won", "lost", "tp_hit", "sl_hit", "expired", "time_exit"):
        status = raw_status.upper()
    else:
        status = "open"

    # Normalize numeric fields
    def _f(v, default=0.0):
        try:
            return float(v) if v else default
        except (ValueError, TypeError):
            return default

    return {
        "enter_date": str(pick.get("enter_date", pick.get("opened_at", str(date.today()))))[:10],
        "ticker": symbol,
        "algorithm_name": str(pick.get("strategy", pick.get("algorithm_name", pick.get("source", "PAPER"))))[:100],
        "source_table": str(pick.get("source_system", pick.get("source", pick.get("system", "paper"))))[:30],
        "entry_price": round(_f(pick.get("entry_price", pick.get("entry"))), 4),
        "target_tp_pct": round(_f(pick.get("tp_pct", pick.get("target_tp")), 5.0), 2),
        "target_sl_pct": round(_f(pick.get("sl_pct", pick.get("target_sl")), 3.0), 2),
        "max_hold_days": int(_f(pick.get("max_hold_days", 7))),
        "position_size_pct": round(_f(pick.get("position_size_pct", pick.get("size_pct", 10.0))), 2),
        "kelly_fraction": round(_f(pick.get("kelly_fraction", 0.0)), 4),
        "regime_at_entry": str(pick.get("regime", pick.get("regime_at_entry", "")))[:20],
        "score": int(_f(pick.get("score", pick.get("confidence", 0)))),
        "status": status,
        "current_price": round(_f(pick.get("current_price", pick.get("exit_price"))), 4),
        "unrealized_pct": round(_f(pick.get("unrealized_pct", pick.get("pnl_pct", 0.0))), 4),
        "exit_date": str(pick.get("exit_date", pick.get("closed_at", None)) or "")[:10] or None,
        "exit_price": round(_f(pick.get("exit_price", pick.get("exit"))), 4),
        "exit_reason": str(pick.get("exit_reason", pick.get("outcome", "")))[:50],
        "return_pct": round(_f(pick.get("return_pct", pick.get("pnl_pct", 0.0))), 4),
        "hold_days": int(_f(pick.get("hold_days", 0))),
        "resolved_at": str(pick.get("resolved_at", pick.get("closed_at", None)) or "")[:19] or None,
    }


def _upsert_paper_trades(cursor, trades: list[dict]) -> int:
    """Upsert paper trades into paper_trades table."""
    UPSERT_SQL = """
        INSERT INTO paper_trades
            (enter_date, ticker, algorithm_name, source_table,
             entry_price, target_tp_pct, target_sl_pct, max_hold_days,
             position_size_pct, kelly_fraction, regime_at_entry, score,
             status, current_price, unrealized_pct, exit_date, exit_price,
             exit_reason, return_pct, hold_days, created_at, resolved_at)
        VALUES
            (%(enter_date)s, %(ticker)s, %(algorithm_name)s, %(source_table)s,
             %(entry_price)s, %(target_tp_pct)s, %(target_sl_pct)s, %(max_hold_days)s,
             %(position_size_pct)s, %(kelly_fraction)s, %(regime_at_entry)s, %(score)s,
             %(status)s, %(current_price)s, %(unrealized_pct)s, %(exit_date)s, %(exit_price)s,
             %(exit_reason)s, %(return_pct)s, %(hold_days)s, NOW(), %(resolved_at)s)
        ON DUPLICATE KEY UPDATE
            status          = VALUES(status),
            current_price   = VALUES(current_price),
            unrealized_pct  = VALUES(unrealized_pct),
            exit_date       = COALESCE(VALUES(exit_date), exit_date),
            exit_price      = COALESCE(VALUES(exit_price), exit_price),
            exit_reason     = COALESCE(VALUES(exit_reason), exit_reason),
            return_pct      = COALESCE(VALUES(return_pct), return_pct),
            hold_days       = COALESCE(VALUES(hold_days), hold_days),
            resolved_at     = COALESCE(VALUES(resolved_at), resolved_at)
    """
    written = 0
    for trade in trades:
        try:
            cursor.execute(UPSERT_SQL, trade)
            written += 1
        except Exception as e:
            logger.warning(f"Failed to upsert trade {trade.get('ticker')}: {e}")
    return written


def _write_portfolio_daily(cursor, trades: list[dict]) -> bool:
    """Write daily portfolio summary to paper_portfolio_daily."""
    today = date.today()
    open_positions = sum(1 for t in trades if t["status"].lower() == "open")
    total_invested = sum(t["entry_price"] * t["position_size_pct"] / 100 for t in trades if t["status"].lower() == "open")
    realized_today = sum(t["return_pct"] for t in trades if t.get("exit_date") == str(today))
    total_wins = sum(1 for t in trades if t["return_pct"] > 0 and t["status"].lower() != "open")
    total_losses = sum(1 for t in trades if t["return_pct"] <= 0 and t["status"].lower() != "open")
    total_closed = total_wins + total_losses
    win_rate = round((total_wins / total_closed * 100), 2) if total_closed > 0 else 0.0

    UPSERT_SQL = """
        INSERT INTO paper_portfolio_daily
            (snapshot_date, open_positions, total_invested, unrealized_pnl,
             realized_pnl_today, total_trades, total_wins, total_losses,
             win_rate_to_date, created_at)
        VALUES
            (%(snapshot_date)s, %(open_positions)s, %(total_invested)s, %(unrealized_pnl)s,
             %(realized_pnl_today)s, %(total_trades)s, %(total_wins)s, %(total_losses)s,
             %(win_rate_to_date)s, NOW())
        ON DUPLICATE KEY UPDATE
            open_positions    = VALUES(open_positions),
            total_invested    = VALUES(total_invested),
            unrealized_pnl    = VALUES(unrealized_pnl),
            realized_pnl_today = VALUES(realized_pnl_today),
            total_trades      = VALUES(total_trades),
            total_wins        = VALUES(total_wins),
            total_losses      = VALUES(total_losses),
            win_rate_to_date  = VALUES(win_rate_to_date)
    """
    try:
        cursor.execute(UPSERT_SQL, {
            "snapshot_date": str(today),
            "open_positions": open_positions,
            "total_invested": round(total_invested, 2),
            "unrealized_pnl": round(sum(t["unrealized_pct"] for t in trades if t["status"].lower() == "open"), 2),
            "realized_pnl_today": round(realized_today, 2),
            "total_trades": total_closed,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate_to_date": win_rate,
        })
        return True
    except Exception as e:
        logger.warning(f"Failed to write portfolio daily: {e}")
        return False


def sync_paper_trades(dry_run: bool = False) -> dict:
    """Main sync function. Loads paper trades and writes to MySQL.

    Returns dict with sync stats.
    """
    if not _is_enabled():
        logger.info("Paper trade MySQL writes disabled (set PAPER_TRADE_MYSQL_ENABLED=1 to enable)")
        return {"status": "disabled", "written": 0}

    # Load all paper trades
    all_trades = []
    for loader in [_load_paper_portfolio_kimi, _load_active_picks_dashboard]:
        all_trades.extend(loader())

    # Deduplicate by ticker+source (keep latest)
    seen = {}
    for pick in all_trades:
        normalized = _normalize_pick(pick)
        if normalized is None:
            continue
        key = f"{normalized['ticker']}|{normalized['source_table']}"
        seen[key] = normalized

    trades = list(seen.values())
    logger.info(f"Prepared {len(trades)} unique paper trades for sync")

    if dry_run:
        logger.info(f"[DRY RUN] Would write {len(trades)} trades to paper_trades")
        return {"status": "dry_run", "written": 0, "prepared": len(trades)}

    if not trades:
        logger.info("No paper trades to sync")
        return {"status": "empty", "written": 0}

    try:
        import pymysql
    except ImportError:
        logger.warning("pymysql not installed — skipping paper trade MySQL write")
        return {"status": "no_pymysql", "written": 0}

    cfg = _get_mysql_config()
    try:
        conn = pymysql.connect(**cfg, autocommit=True)
        with conn.cursor() as cur:
            written = _upsert_paper_trades(cur, trades)
            portfolio_ok = _write_portfolio_daily(cur, trades)
        conn.close()

        logger.info(f"Synced {written} paper trades to MySQL (portfolio_daily={'OK' if portfolio_ok else 'FAILED'})")
        return {"status": "ok", "written": written, "portfolio_daily": portfolio_ok}
    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        return {"status": "error", "written": 0, "error": str(e)}


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    result = sync_paper_trades(dry_run=dry_run)
    print(json.dumps(result, indent=2, default=str))

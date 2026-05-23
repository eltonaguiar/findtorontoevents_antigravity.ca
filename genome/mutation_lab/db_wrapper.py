"""Thin DB abstraction for audit trail queries.

Insulates mutation lab from schema changes in the audit database.
Falls back to JSON files when DB is unavailable.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# JSON fallback sources for strategy performance data
PERFORMANCE_SOURCES = [
    ("battleground/data/quality_rankings.json", "battleground"),
    ("battleground/data/baby_strats_dashboard.json", "baby_strats"),
    ("genome/gp_results/evolution_log.json", "genetic_programmer"),
    ("genome/data/gp_active_picks.json", "genetic_programmer"),
    ("alpha_engine/data/active_picks.json", "alpha_engine"),
    ("baby_strategies_backtest_results.json", "baby_backtest"),
    ("audit_trail/data/dashboard_payload.json", "audit_dashboard"),
]


def _try_mysql_query() -> list[dict] | None:
    """Attempt to query MySQL for strategy performance. Returns None if unavailable."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.environ.get("DB_HOST", ""),
            user=os.environ.get("DB_USER", ""),
            password=os.environ.get("DB_PASS", ""),
            database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
            connect_timeout=5,
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT strategy_name AS name,
                   win_rate, profit_factor, sharpe_ratio,
                   max_drawdown, total_trades, total_pnl_pct,
                   expectancy_pct, source_system
            FROM at_signal_outcomes
            WHERE total_trades >= 5
            ORDER BY win_rate DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"MySQL unavailable: {e}")
        return None


def _load_json_strategies() -> list[dict]:
    """Load strategy performance from JSON fallback sources."""
    strategies = []

    # Load from dashboard payload (most comprehensive)
    payload_path = PROJECT_ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            data = json.loads(payload_path.read_text())
            for sys_info in data.get("systems", []):
                name = sys_info.get("name", "")
                strategies.append({
                    "name": name,
                    "win_rate": sys_info.get("win_rate", 0) / 100 if sys_info.get("win_rate", 0) > 1 else sys_info.get("win_rate", 0),
                    "profit_factor": sys_info.get("profit_factor", 0),
                    "sharpe_ratio": sys_info.get("sharpe_ratio", 0),
                    "max_drawdown": sys_info.get("max_drawdown", 0),
                    "total_trades": sys_info.get("closed_picks", 0),
                    "total_pnl_pct": sys_info.get("total_pnl_pct", 0),
                    "source_system": name,
                })
            # Also extract per-strategy leaderboard
            for entry in data.get("leaderboard", []):
                strategies.append({
                    "name": entry.get("strategy", ""),
                    "win_rate": entry.get("fwd_wr", entry.get("bt_wr", 0)) / 100 if entry.get("fwd_wr", entry.get("bt_wr", 0)) > 1 else entry.get("fwd_wr", entry.get("bt_wr", 0)),
                    "profit_factor": entry.get("fwd_pf", entry.get("bt_pf", 0)),
                    "sharpe_ratio": entry.get("fwd_sharpe", entry.get("bt_sharpe", 0)),
                    "max_drawdown": entry.get("max_dd", 0),
                    "total_trades": entry.get("fwd_trades", entry.get("bt_trades", 0)),
                    "total_pnl_pct": entry.get("fwd_total_pnl", 0),
                    "source_system": entry.get("strategy", ""),
                })
        except Exception as e:
            logger.warning(f"Failed to parse dashboard payload: {e}")

    # Load from quality rankings
    quality_path = PROJECT_ROOT / "battleground" / "data" / "quality_rankings.json"
    if quality_path.exists():
        try:
            data = json.loads(quality_path.read_text())
            for tier in ("elite", "quality", "emerging", "watch"):
                for entry in data.get(tier, []):
                    strategies.append({
                        "name": entry.get("name", entry.get("strategy", "")),
                        "win_rate": entry.get("win_rate", 0),
                        "profit_factor": entry.get("profit_factor", 0),
                        "sharpe_ratio": entry.get("sharpe", 0),
                        "max_drawdown": entry.get("max_dd", 0),
                        "total_trades": entry.get("trades", 0),
                        "total_pnl_pct": entry.get("total_pnl", 0),
                        "source_system": entry.get("source", "battleground"),
                    })
        except Exception as e:
            logger.warning(f"Failed to parse quality rankings: {e}")

    # Load from backtest results
    bt_path = PROJECT_ROOT / "baby_strategies_backtest_results.json"
    if bt_path.exists():
        try:
            data = json.loads(bt_path.read_text())
            for r in data.get("results", []):
                strategies.append({
                    "name": r.get("Strategy", ""),
                    "win_rate": r.get("Win Rate", 0),
                    "profit_factor": r.get("Profit Factor", 0),
                    "sharpe_ratio": r.get("Sharpe", 0),
                    "max_drawdown": r.get("Max DD", 0),
                    "total_trades": r.get("Trades", 0),
                    "total_pnl_pct": r.get("Total Return", 0) * 100,
                    "source_system": "baby_backtest",
                })
        except Exception as e:
            logger.warning(f"Failed to parse backtest results: {e}")

    return strategies


def fetch_all_strategies() -> list[dict]:
    """Get all strategy performance data. Tries MySQL first, falls back to JSON."""
    rows = _try_mysql_query()
    if rows and len(rows) > 10:
        logger.info(f"Loaded {len(rows)} strategies from MySQL")
        return rows

    strategies = _load_json_strategies()
    logger.info(f"Loaded {len(strategies)} strategies from JSON fallbacks")
    return strategies


def compute_composite_score(s: dict) -> float:
    """Score a strategy 0-100 for ranking purposes."""
    wr = s.get("win_rate") or 0
    if wr > 1:
        wr = wr / 100
    pf = s.get("profit_factor") or 0
    sharpe = s.get("sharpe_ratio") or 0
    pnl = s.get("total_pnl_pct") or 0

    score = (
        min(45, wr * 45.0) +
        min(30, (pf / 3.0) * 30.0) +
        min(20, (abs(sharpe) / 2.5) * 20.0) +
        min(5, max(0, (pnl + 100) / 200) * 5.0)
    )
    return round(score, 2)

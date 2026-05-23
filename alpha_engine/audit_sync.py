#!/usr/bin/env python3
"""
Audit Database Sync -- consolidates ALL portfolio results into one place.

Syncs to:
1. Local SQLite: alpha_engine/data/audit_consolidated.db
2. Remote MySQL: ejaguiar1_stocks (if credentials available)

Tables:
- portfolio_snapshots: equity, positions, PnL per portfolio per timestamp
- trade_log: every closed trade from every system
- ml_performance: ML model metrics over time

Runs after each scan cycle and on demand.
"""

from __future__ import annotations

import json
import os
import sqlite3
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
AUDIT_DB_PATH = DATA_DIR / "audit_consolidated.db"

# All portfolio JSON files to sync
PORTFOLIO_FILES = {
    "alpha_1x": DATA_DIR / "portfolio_1x.json",
    "alpha_20x": DATA_DIR / "portfolio_20x.json",
    "kimi": BASE_DIR / "KIMI_RISEOFTHECLAW" / "data" / "portfolio_state.json",
    "kimi_paper": BASE_DIR / "KIMI_RISEOFTHECLAW" / "data" / "paper_portfolio.json",
    "battleground": BASE_DIR / "battleground" / "data" / "test_portfolios.json",
    "genome": BASE_DIR / "genome" / "data" / "darwin_portfolios.json",
    "paper_trading": BASE_DIR / "paper_trading" / "data" / "portfolios.json",
    "quick_guess": BASE_DIR / "parallel_agent" / "data" / "guess_stats.json",
    # --- Copy Trader Intel systems ---
    "copy_trader_intel": BASE_DIR / "copy_trader_intel" / "data" / "tradeable_portfolio.json",
    "copy_trader_highscore": BASE_DIR / "copy_trader_intel" / "data" / "scored_picks.json",
    # --- Multi-Asset systems ---
    "multi_asset": BASE_DIR / "multi_asset" / "data" / "multi_asset_picks.json",
    # --- Goldmine (stocks/meme/sports) ---
    "goldmine": BASE_DIR / "data" / "goldmine" / "unified_picks.json",
}

ML_FILES = {
    "model_comparison": DATA_DIR / "model_comparison.json",
    "feature_importance": DATA_DIR / "feature_importance.json",
    "kpi_report": DATA_DIR / "kpi_report.json",
    "guess_stats": BASE_DIR / "parallel_agent" / "data" / "guess_stats.json",
}

CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"

# Closed trades for additional systems
COPY_TRADER_CLOSED_PATH = BASE_DIR / "copy_trader_intel" / "data" / "closed_trades.json"
COPY_TRADER_CLONE_CLOSED_PATH = BASE_DIR / "copy_trader_intel" / "data" / "clone_closed_picks.json"
COPY_TRADER_HIGHSCORE_CLOSED_PATH = BASE_DIR / "copy_trader_intel" / "data" / "highscore_closed_picks.json"
MULTI_ASSET_CLOSED_PATH = BASE_DIR / "multi_asset" / "data" / "multi_asset_closed.json"
GOLDMINE_CLOSED_PATH = BASE_DIR / "data" / "goldmine" / "closed_trades.json"
WALKFORWARD_RESULTS_PATH = DATA_DIR / "walkforward_results.json"

# Portfolio descriptions -- what each portfolio does, its purpose, entry criteria
PORTFOLIO_DESCRIPTIONS = {
    "alpha_1x": {
        "name": "Alpha Engine 1x (Regular)",
        "description": "Main production portfolio. 200+ strategies, 13 quality gates, ML scoring. No leverage.",
        "entry_criteria": "Elite score >= 30, passes all directional gates (RR, VPIN, momentum, etc.)",
        "leverage": "1x (spot)",
        "started": "2026-02-18",
    },
    "alpha_20x": {
        "name": "Alpha Engine 20x (Leveraged)",
        "description": "High-conviction picks only. Same strategies but score >= 68 required. 20x leverage simulated.",
        "entry_criteria": "Elite score >= 68 (B grade+), not blacklisted, not in blackout hours, max 4 positions",
        "leverage": "20x",
        "started": "2026-03-17",
    },
    "kimi": {
        "name": "KIMI Rise of the Claw",
        "description": "81 algorithms, separate ML ranker (AUC 0.72). Re-enabled Mar 18 after being disabled Mar 12.",
        "entry_criteria": "KIMI tournament ranking, elimination engine, ML signal ranker",
        "leverage": "1x",
        "started": "2026-02-17",
    },
    "kimi_paper": {
        "name": "KIMI Paper Portfolio",
        "description": "Paper trading version of KIMI for testing without risk.",
        "entry_criteria": "Same as KIMI production",
        "leverage": "1x (paper)",
        "started": "2026-02-17",
    },
    "battleground": {
        "name": "ML Battleground",
        "description": "Head-to-head ML model testing. Multiple strategy variants compete.",
        "entry_criteria": "Strategy-specific, varies per battleground round",
        "leverage": "1x",
        "started": "2026-03-01",
    },
    "genome": {
        "name": "Genome Evolution (Darwin)",
        "description": "Genetically evolved strategies. DNA mutations, crossover, selection.",
        "entry_criteria": "Evolved genome parameters, fitness-based selection",
        "leverage": "1x",
        "started": "2026-02-26",
    },
    "paper_trading": {
        "name": "Paper Trading Tiers",
        "description": "Tiered paper portfolios testing different confidence levels.",
        "entry_criteria": "Tier-based: conservative, moderate, aggressive",
        "leverage": "1x (paper)",
        "started": "2026-03-01",
    },
    "quick_guess": {
        "name": "Quick Guess ML Agent",
        "description": "Short-term predictions (1m to 1 week) for 30 symbols. GradientBoosting, retrains every 20min.",
        "entry_criteria": "Probability > 0.55 for UP, < 0.45 for DOWN. Auto-contrarian flip when accuracy < 40%.",
        "leverage": "N/A (prediction only)",
        "started": "2026-03-18",
    },
    "structural": {
        "name": "Structural Income Engine",
        "description": "Carry/basis/arb trades. Bypasses directional gates. 11 strategies: funding carry, spot-perp basis, etc.",
        "entry_criteria": "Net edge > 5 bps after costs, minimum liquidity, not on kill list. NO ml_score required.",
        "leverage": "Varies by strategy",
        "started": "2026-03-18",
    },
    "copy_trader_intel": {
        "name": "Copy Trader Intel",
        "description": "Reverse-engineered trader strategy clones from Hyperliquid, Binance, OKX, Bybit, Bitget, DEX whales.",
        "entry_criteria": "Proven trader clone with forward validation, elite score gating, multi-exchange consensus.",
        "leverage": "Varies (1x-50x depending on trader clone)",
        "started": "2026-03-19",
    },
    "copy_trader_highscore": {
        "name": "Copy Trader Highscore",
        "description": "Highest-scored copy trader picks across all exchanges. Trader win-rate and PF weighted scoring.",
        "entry_criteria": "Highscore ranking of trader picks, consensus count, forward validation.",
        "leverage": "Varies",
        "started": "2026-03-19",
    },
    "multi_asset": {
        "name": "Multi-Asset Scanner",
        "description": "Cross-asset scanner: stocks, ETFs, futures, forex, commodities, crypto. EMA/VIX/momentum strategies.",
        "entry_criteria": "Strategy-specific signals with institutional-grade risk/reward filtering.",
        "leverage": "1x",
        "started": "2026-03-11",
    },
    "goldmine": {
        "name": "Goldmine Stock Picks",
        "description": "Stock/meme/sports picks from multi-algorithm consensus. Traditional equities focus.",
        "entry_criteria": "Multi-algorithm consensus, removed when consensus drops.",
        "leverage": "1x",
        "started": "2026-03-15",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path):
    """Load a JSON file, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_est() -> str:
    """Current time in EST (UTC-4 during EDT, UTC-5 during EST)."""
    from datetime import timedelta
    est = timezone(timedelta(hours=-4))  # EDT (March = daylight saving)
    return datetime.now(est).strftime("%Y-%m-%d %H:%M:%S EST")


def _utc_to_est(utc_str: str) -> str:
    """Convert a UTC ISO timestamp string to EST display string."""
    try:
        from datetime import timedelta
        est = timezone(timedelta(hours=-4))
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone(est).strftime("%Y-%m-%d %H:%M:%S EST")
    except Exception:
        return utc_str


def sync_portfolio_registry(db):
    """Write portfolio descriptions to the registry table."""
    for system, info in PORTFOLIO_DESCRIPTIONS.items():
        try:
            db.execute(
                "INSERT OR REPLACE INTO portfolio_registry (system, name, description, entry_criteria, leverage, started) VALUES (?, ?, ?, ?, ?, ?)",
                (system, info["name"], info["description"], info["entry_criteria"], info["leverage"], info["started"]),
            )
        except Exception:
            pass
    db.commit()


# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS portfolio_registry (
    system TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    entry_criteria TEXT,
    leverage TEXT,
    started TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    timestamp_est TEXT NOT NULL,
    system TEXT NOT NULL,
    equity REAL,
    positions INTEGER,
    realized_pnl REAL,
    unrealized_pnl REAL
);

CREATE TABLE IF NOT EXISTS trade_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system TEXT,
    symbol TEXT,
    direction TEXT,
    entry_price REAL,
    exit_price REAL,
    pnl_pct REAL,
    pnl_dollar REAL,
    entry_time TEXT,
    exit_time TEXT,
    strategy TEXT,
    elite_score REAL,
    trade_type TEXT,
    ml_score REAL,
    confidence REAL,
    UNIQUE(system, symbol, strategy, entry_time)
);

CREATE TABLE IF NOT EXISTS ml_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model_name TEXT,
    auc REAL,
    precision_20 REAL,
    feature_health REAL,
    training_samples INTEGER
);

CREATE INDEX IF NOT EXISTS idx_snap_system ON portfolio_snapshots(system);
CREATE INDEX IF NOT EXISTS idx_snap_ts ON portfolio_snapshots(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_trade_system ON trade_log(system);
CREATE INDEX IF NOT EXISTS idx_trade_symbol ON trade_log(symbol);
CREATE INDEX IF NOT EXISTS idx_ml_ts ON ml_performance(timestamp);
"""


def _get_db(db_path: Path = AUDIT_DB_PATH) -> sqlite3.Connection:
    """Open (or create) the audit consolidated database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# 1. sync_all_portfolios
# ---------------------------------------------------------------------------

def _extract_alpha_portfolio(data: dict) -> dict:
    """Extract equity/positions/pnl from alpha_engine portfolio format."""
    if not data:
        return {}
    positions = data.get("positions", {})
    pos_count = len(positions) if isinstance(positions, dict) else 0
    equity = _safe_float(data.get("current_balance", data.get("equity", 0)))
    realized = _safe_float(data.get("stats", {}).get("total_pnl_usdt", 0))
    unrealized = 0.0
    if isinstance(positions, dict):
        for p in positions.values():
            unrealized += _safe_float(p.get("current_pnl_usdt", 0))
    return {
        "equity": equity,
        "positions": pos_count,
        "realized_pnl": realized,
        "unrealized_pnl": round(unrealized, 4),
    }


def _extract_kimi_portfolio(data: dict) -> dict:
    """Extract from KIMI portfolio_state.json (algorithms dict)."""
    if not data:
        return {}
    algos = data.get("algorithms", {})
    total_equity = 0.0
    total_positions = 0
    total_realized = 0.0
    for algo_data in algos.values():
        total_equity += _safe_float(algo_data.get("cash", 0))
        positions = algo_data.get("positions", [])
        total_positions += len(positions)
        for cp in algo_data.get("closed_positions", []):
            total_realized += _safe_float(cp.get("pnl", 0))
    return {
        "equity": total_equity,
        "positions": total_positions,
        "realized_pnl": round(total_realized, 4),
        "unrealized_pnl": 0.0,
    }


def _extract_kimi_paper(data: dict) -> dict:
    """Extract from KIMI paper_portfolio.json."""
    if not data:
        return {}
    positions = data.get("positions", [])
    pos_count = len(positions) if isinstance(positions, list) else 0
    equity = _safe_float(data.get("starting_capital", 10000))
    return {
        "equity": equity,
        "positions": pos_count,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def _extract_battleground(data: dict) -> list:
    """Extract from battleground test_portfolios.json (multiple sub-portfolios)."""
    if not data:
        return []
    portfolios_dict = data.get("portfolios", {})
    results = []
    for key, port in portfolios_dict.items():
        active = port.get("active_positions", [])
        results.append({
            "system": f"battleground_{key}",
            "equity": _safe_float(port.get("capital", 0)),
            "positions": len(active),
            "realized_pnl": _safe_float(port.get("total_pnl_pct", 0)),
            "unrealized_pnl": 0.0,
        })
    return results


def _extract_genome(data: dict) -> list:
    """Extract from genome darwin_portfolios.json (multiple families)."""
    if not data:
        return []
    portfolios_dict = data.get("portfolios", {})
    results = []
    for key, port in portfolios_dict.items():
        open_pos = port.get("open_positions", [])
        results.append({
            "system": f"genome_{key}",
            "equity": _safe_float(port.get("capital", 10000)),
            "positions": len(open_pos),
            "realized_pnl": _safe_float(port.get("total_pnl_pct", 0)),
            "unrealized_pnl": _safe_float(port.get("unrealized_pnl_pct", 0)),
        })
    return results


def _extract_paper_trading(data) -> list:
    """Extract from paper_trading portfolios.json (list of tier-based portfolios)."""
    if not data:
        return []
    if not isinstance(data, list):
        return []
    results = []
    for port in data:
        name = port.get("name", "unknown")
        results.append({
            "system": f"paper_{name}",
            "equity": _safe_float(port.get("equity", 0)),
            "positions": int(_safe_float(port.get("active_positions", 0))),
            "realized_pnl": _safe_float(port.get("pnl_pct", 0)),
            "unrealized_pnl": 0.0,
        })
    return results


def _extract_quick_guess(data: dict) -> dict:
    """Extract from parallel_agent guess_stats.json."""
    if not data:
        return {}
    overall = data.get("overall", {})
    correct = int(_safe_float(overall.get("correct", 0)))
    total = int(_safe_float(overall.get("total", 0)))
    accuracy = round(correct / total * 100, 2) if total > 0 else 0.0
    return {
        "equity": accuracy,  # repurpose equity as accuracy %
        "positions": total,
        "realized_pnl": accuracy,
        "unrealized_pnl": 0.0,
    }


def _extract_copy_trader_intel(data: dict) -> dict:
    """Extract from copy_trader_intel tradeable_portfolio.json."""
    if not data:
        return {}
    portfolio = data.get("portfolio", [])
    total_positions = data.get("total_positions", len(portfolio))
    return {
        "equity": 0.0,  # forward-test only, no real equity
        "positions": total_positions,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def _extract_copy_trader_highscore(data: dict) -> dict:
    """Extract from copy_trader_intel scored_picks.json."""
    if not data:
        return {}
    tradeable = int(_safe_float(data.get("tradeable_count", 0)))
    total = int(_safe_float(data.get("total_scored", 0)))
    return {
        "equity": 0.0,
        "positions": tradeable,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def _extract_multi_asset(data) -> dict:
    """Extract from multi_asset multi_asset_picks.json (list of open picks)."""
    if not data:
        return {}
    picks = data if isinstance(data, list) else data.get("picks", [])
    open_picks = [p for p in picks if p.get("status", "").upper() in ("OPEN", "ACTIVE", "")]
    return {
        "equity": 0.0,
        "positions": len(open_picks),
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def _extract_goldmine(data: dict) -> dict:
    """Extract from goldmine unified_picks.json."""
    if not data:
        return {}
    picks = data if isinstance(data, list) else data.get("picks", [])
    open_picks = [p for p in picks if p.get("status", "").upper() in ("OPEN", "ACTIVE", "")]
    return {
        "equity": 0.0,
        "positions": len(open_picks),
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
    }


def sync_all_portfolios(conn: Optional[sqlite3.Connection] = None):
    """Read all portfolio JSON files, extract equity/positions/PnL,
    write snapshots to consolidated SQLite database."""
    close_conn = False
    if conn is None:
        conn = _get_db()
        close_conn = True

    now = _now_iso()
    inserted = 0

    for system_key, path in PORTFOLIO_FILES.items():
        data = _load_json(path)
        if data is None:
            continue

        snapshots = []

        if system_key in ("alpha_1x", "alpha_20x"):
            info = _extract_alpha_portfolio(data)
            if info:
                snapshots.append({"system": system_key, **info})

        elif system_key == "kimi":
            info = _extract_kimi_portfolio(data)
            if info:
                snapshots.append({"system": "kimi", **info})

        elif system_key == "kimi_paper":
            info = _extract_kimi_paper(data)
            if info:
                snapshots.append({"system": "kimi_paper", **info})

        elif system_key == "battleground":
            snapshots.extend(_extract_battleground(data))

        elif system_key == "genome":
            snapshots.extend(_extract_genome(data))

        elif system_key == "paper_trading":
            snapshots.extend(_extract_paper_trading(data))

        elif system_key == "quick_guess":
            info = _extract_quick_guess(data)
            if info:
                snapshots.append({"system": "quick_guess", **info})

        elif system_key == "copy_trader_intel":
            info = _extract_copy_trader_intel(data)
            if info:
                snapshots.append({"system": "copy_trader_intel", **info})

        elif system_key == "copy_trader_highscore":
            info = _extract_copy_trader_highscore(data)
            if info:
                snapshots.append({"system": "copy_trader_highscore", **info})

        elif system_key == "multi_asset":
            info = _extract_multi_asset(data)
            if info:
                snapshots.append({"system": "multi_asset", **info})

        elif system_key == "goldmine":
            info = _extract_goldmine(data)
            if info:
                snapshots.append({"system": "goldmine", **info})

        for snap in snapshots:
            try:
                conn.execute("""
                    INSERT INTO portfolio_snapshots
                        (timestamp, system, equity, positions, realized_pnl, unrealized_pnl)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    now,
                    snap["system"],
                    snap.get("equity", 0),
                    snap.get("positions", 0),
                    snap.get("realized_pnl", 0),
                    snap.get("unrealized_pnl", 0),
                ))
                inserted += 1
            except Exception:
                continue

    conn.commit()
    print(f"  [AUDIT SYNC] Portfolio snapshots: {inserted} rows inserted")

    if close_conn:
        conn.close()
    return inserted


# ---------------------------------------------------------------------------
# 2. sync_closed_trades
# ---------------------------------------------------------------------------

def sync_closed_trades(conn: Optional[sqlite3.Connection] = None):
    """Sync closed_picks.json into trade_log table with full details."""
    close_conn = False
    if conn is None:
        conn = _get_db()
        close_conn = True

    # --- Alpha Engine closed picks ---
    picks = _load_json(CLOSED_PICKS_PATH) or []
    inserted = 0

    for p in picks:
        status = p.get("status", "")
        if status not in ("WON", "LOST", "EXPIRED"):
            continue

        extra = {}
        if p.get("extra_json"):
            try:
                extra = json.loads(p["extra_json"]) if isinstance(p["extra_json"], str) else p["extra_json"]
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            conn.execute("""
                INSERT OR IGNORE INTO trade_log
                    (system, symbol, direction, entry_price, exit_price,
                     pnl_pct, pnl_dollar, entry_time, exit_time,
                     strategy, elite_score, trade_type, ml_score, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "alpha",
                p.get("symbol", ""),
                p.get("signal_type", ""),
                _safe_float(p.get("entry_price")),
                _safe_float(p.get("exit_price")),
                _safe_float(p.get("pnl_pct")),
                _safe_float(p.get("pnl_dollar")),
                p.get("entry_date", ""),
                p.get("exit_date", ""),
                p.get("strategy", ""),
                _safe_float(extra.get("elite_score")),
                extra.get("trade_type", "directional"),
                _safe_float(p.get("ml_score")),
                _safe_float(p.get("confidence")),
            ))
            inserted += 1
        except Exception:
            continue

    # --- Battleground closed trades ---
    bg_data = _load_json(PORTFOLIO_FILES.get("battleground", Path(".")))
    if bg_data:
        for port_key, port in bg_data.get("portfolios", {}).items():
            for t in port.get("closed_trades", []):
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO trade_log
                            (system, symbol, direction, entry_price, exit_price,
                             pnl_pct, pnl_dollar, entry_time, exit_time,
                             strategy, elite_score, trade_type, ml_score, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"battleground_{port_key}",
                        t.get("symbol", ""),
                        t.get("direction", ""),
                        _safe_float(t.get("entry_price")),
                        _safe_float(t.get("exit_price")),
                        _safe_float(t.get("pnl_pct")),
                        _safe_float(t.get("pnl_dollar")),
                        t.get("opened_at", ""),
                        t.get("closed_at", ""),
                        t.get("strategy", ""),
                        0.0,
                        "directional",
                        0.0,
                        _safe_float(t.get("confidence")),
                    ))
                    inserted += 1
                except Exception:
                    continue

    # --- Genome closed trades ---
    genome_data = _load_json(PORTFOLIO_FILES.get("genome", Path(".")))
    if genome_data:
        for fam_key, fam in genome_data.get("portfolios", {}).items():
            for t in fam.get("closed_trades", []):
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO trade_log
                            (system, symbol, direction, entry_price, exit_price,
                             pnl_pct, pnl_dollar, entry_time, exit_time,
                             strategy, elite_score, trade_type, ml_score, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"genome_{fam_key}",
                        t.get("symbol", ""),
                        t.get("direction", ""),
                        _safe_float(t.get("entry_price")),
                        _safe_float(t.get("exit_price")),
                        _safe_float(t.get("pnl_pct")),
                        _safe_float(t.get("pnl_dollar")),
                        t.get("entry_time", ""),
                        t.get("exit_time", t.get("closed_at", "")),
                        t.get("strategy", ""),
                        0.0,
                        "structural",
                        0.0,
                        _safe_float(t.get("confidence")),
                    ))
                    inserted += 1
                except Exception:
                    continue

    # --- KIMI closed trades (from portfolio_state algorithms) ---
    kimi_data = _load_json(PORTFOLIO_FILES.get("kimi", Path(".")))
    if kimi_data:
        for algo_name, algo_data in kimi_data.get("algorithms", {}).items():
            for t in algo_data.get("closed_positions", []):
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO trade_log
                            (system, symbol, direction, entry_price, exit_price,
                             pnl_pct, pnl_dollar, entry_time, exit_time,
                             strategy, elite_score, trade_type, ml_score, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        "kimi",
                        t.get("symbol", ""),
                        t.get("direction", ""),
                        _safe_float(t.get("entry_price")),
                        _safe_float(t.get("exit_price")),
                        _safe_float(t.get("pnl_pct")),
                        _safe_float(t.get("pnl", 0)),
                        t.get("entry_time", t.get("opened_at", "")),
                        t.get("exit_time", t.get("closed_at", "")),
                        algo_name,
                        0.0,
                        "directional",
                        0.0,
                        _safe_float(t.get("confidence")),
                    ))
                    inserted += 1
                except Exception:
                    continue

    conn.commit()
    print(f"  [AUDIT SYNC] Trade log: {inserted} rows inserted/updated")

    if close_conn:
        conn.close()
    return inserted


# ---------------------------------------------------------------------------
# 3. sync_ml_metrics
# ---------------------------------------------------------------------------

def sync_ml_metrics(conn: Optional[sqlite3.Connection] = None):
    """Sync model_comparison.json, feature_importance.json, kpi_report.json,
    guess_stats.json into ml_performance table."""
    close_conn = False
    if conn is None:
        conn = _get_db()
        close_conn = True

    now = _now_iso()
    inserted = 0

    # --- Model comparison ---
    mc = _load_json(ML_FILES["model_comparison"])
    if mc:
        try:
            conn.execute("""
                INSERT INTO ml_performance
                    (timestamp, model_name, auc, precision_20, feature_health, training_samples)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                mc.get("evaluated_at", now),
                mc.get("status", "model_comparison"),
                0.0,
                0.0,
                0.0,
                _safe_float(mc.get("val_samples", 0)),
            ))
            inserted += 1
        except Exception:
            pass

    # --- Feature importance ---
    fi = _load_json(ML_FILES["feature_importance"])
    if fi:
        importances = fi.get("importances", {})
        # Feature health = fraction of features with non-zero importance
        total_features = len(importances)
        active_features = sum(1 for v in importances.values() if v > 0)
        feature_health = round(active_features / total_features, 4) if total_features > 0 else 0.0
        try:
            conn.execute("""
                INSERT INTO ml_performance
                    (timestamp, model_name, auc, precision_20, feature_health, training_samples)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                fi.get("generated_at", now),
                fi.get("model_type", "feature_importance"),
                0.0,
                0.0,
                feature_health,
                int(_safe_float(fi.get("training_samples", 0))),
            ))
            inserted += 1
        except Exception:
            pass

    # --- KPI report ---
    kpi = _load_json(ML_FILES["kpi_report"])
    if kpi:
        try:
            conn.execute("""
                INSERT INTO ml_performance
                    (timestamp, model_name, auc, precision_20, feature_health, training_samples)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                kpi.get("generated_at", now),
                "kpi_report",
                0.0,
                _safe_float(kpi.get("precision_at_20", 0)),
                _safe_float(kpi.get("score_to_wr_correlation", 0)),
                int(_safe_float(kpi.get("total_closed_picks", 0))),
            ))
            inserted += 1
        except Exception:
            pass

    # --- Guess stats (parallel agent ML) ---
    gs = _load_json(ML_FILES["guess_stats"])
    if gs:
        overall = gs.get("overall", {})
        correct = int(_safe_float(overall.get("correct", 0)))
        total = int(_safe_float(overall.get("total", 0)))
        accuracy = round(correct / total, 4) if total > 0 else 0.0
        try:
            conn.execute("""
                INSERT INTO ml_performance
                    (timestamp, model_name, auc, precision_20, feature_health, training_samples)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                now,
                "quick_guess_ml",
                accuracy,
                accuracy,
                0.0,
                total,
            ))
            inserted += 1
        except Exception:
            pass

    conn.commit()
    print(f"  [AUDIT SYNC] ML performance: {inserted} rows inserted")

    if close_conn:
        conn.close()
    return inserted


# ---------------------------------------------------------------------------
# 4. sync_to_mysql
# ---------------------------------------------------------------------------

def sync_to_mysql(sqlite_path: Path = AUDIT_DB_PATH, mysql_config: Optional[dict] = None):
    """If MySQL credentials available (from env vars or config),
    push consolidated data to ejaguiar1_stocks database.
    Tables: portfolio_snapshots, trade_log, ml_performance"""

    # Resolve MySQL config from env vars or passed config
    if mysql_config is None:
        host = os.environ.get("MYSQL_HOST") or os.environ.get("DB_HOST") or os.environ.get("AUDIT_DB_HOST")
        user = os.environ.get("MYSQL_USER") or os.environ.get("DB_USER") or os.environ.get("AUDIT_DB_USER")
        password = os.environ.get("MYSQL_PASS") or os.environ.get("DB_PASS") or os.environ.get("AUDIT_DB_PASS")
        database = os.environ.get("MYSQL_DB") or os.environ.get("DB_NAME") or os.environ.get("AUDIT_DB_NAME")

        if not all([host, user, password, database]):
            print("  [AUDIT SYNC] MySQL credentials not found in env -- skipping MySQL sync")
            return 0

        mysql_config = {
            "host": host,
            "port": int(os.environ.get("MYSQL_PORT", os.environ.get("AUDIT_DB_PORT", 3306))),
            "user": user,
            "password": password,
            "database": database,
        }

    try:
        import pymysql
    except ImportError:
        print("  [AUDIT SYNC] pymysql not installed -- skipping MySQL sync")
        return 0

    try:
        mysql_conn = pymysql.connect(
            host=mysql_config["host"],
            port=mysql_config.get("port", 3306),
            user=mysql_config["user"],
            password=mysql_config["password"],
            database=mysql_config["database"],
            connect_timeout=10,
            charset="utf8mb4",
        )
        cursor = mysql_conn.cursor()

        # Create tables if not exist (MySQL syntax)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp VARCHAR(64),
                system VARCHAR(64),
                equity DOUBLE,
                positions INT,
                realized_pnl DOUBLE,
                unrealized_pnl DOUBLE,
                INDEX idx_snap_system (system),
                INDEX idx_snap_ts (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                system VARCHAR(64),
                symbol VARCHAR(32),
                direction VARCHAR(16),
                entry_price DOUBLE,
                exit_price DOUBLE,
                pnl_pct DOUBLE,
                pnl_dollar DOUBLE,
                entry_time VARCHAR(64),
                exit_time VARCHAR(64),
                strategy VARCHAR(128),
                elite_score DOUBLE,
                trade_type VARCHAR(32),
                ml_score DOUBLE,
                confidence DOUBLE,
                UNIQUE KEY uq_trade (system, symbol, strategy, entry_time),
                INDEX idx_trade_system (system),
                INDEX idx_trade_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_performance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp VARCHAR(64),
                model_name VARCHAR(64),
                auc DOUBLE,
                precision_20 DOUBLE,
                feature_health DOUBLE,
                training_samples INT,
                INDEX idx_ml_ts (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        mysql_conn.commit()

        # Read from local SQLite and push to MySQL
        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.row_factory = sqlite3.Row
        pushed = 0

        # Push latest portfolio snapshots (last hour only to avoid dupes)
        rows = sqlite_conn.execute("""
            SELECT * FROM portfolio_snapshots
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY id DESC LIMIT 500
        """).fetchall()
        for r in rows:
            try:
                cursor.execute("""
                    INSERT INTO portfolio_snapshots
                        (timestamp, system, equity, positions, realized_pnl, unrealized_pnl)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (r["timestamp"], r["system"], r["equity"],
                      r["positions"], r["realized_pnl"], r["unrealized_pnl"]))
                pushed += 1
            except Exception:
                continue

        # Push trade_log (INSERT IGNORE for idempotency)
        rows = sqlite_conn.execute("SELECT * FROM trade_log ORDER BY id DESC LIMIT 2000").fetchall()
        for r in rows:
            try:
                cursor.execute("""
                    INSERT IGNORE INTO trade_log
                        (system, symbol, direction, entry_price, exit_price,
                         pnl_pct, pnl_dollar, entry_time, exit_time,
                         strategy, elite_score, trade_type, ml_score, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    r["system"], r["symbol"], r["direction"],
                    r["entry_price"], r["exit_price"],
                    r["pnl_pct"], r["pnl_dollar"],
                    r["entry_time"], r["exit_time"],
                    r["strategy"], r["elite_score"], r["trade_type"],
                    r["ml_score"], r["confidence"],
                ))
                pushed += 1
            except Exception:
                continue

        # Push ML performance
        rows = sqlite_conn.execute("""
            SELECT * FROM ml_performance
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY id DESC LIMIT 100
        """).fetchall()
        for r in rows:
            try:
                cursor.execute("""
                    INSERT INTO ml_performance
                        (timestamp, model_name, auc, precision_20, feature_health, training_samples)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (r["timestamp"], r["model_name"], r["auc"],
                      r["precision_20"], r["feature_health"], r["training_samples"]))
                pushed += 1
            except Exception:
                continue

        mysql_conn.commit()
        cursor.close()
        mysql_conn.close()
        sqlite_conn.close()

        print(f"  [AUDIT SYNC] MySQL: {pushed} rows pushed to {mysql_config['database']}")
        return pushed

    except Exception as e:
        print(f"  [AUDIT SYNC] MySQL sync failed: {e}")
        return 0


# ---------------------------------------------------------------------------
# 5. run_full_sync
# ---------------------------------------------------------------------------

def run_full_sync():
    """Run all sync operations. Call after each scan cycle."""
    print("\n[AUDIT SYNC] Starting full portfolio consolidation...")
    conn = _get_db()

    try:
        sync_portfolio_registry(conn)  # Write portfolio descriptions first
        snap_count = sync_all_portfolios(conn)
        trade_count = sync_closed_trades(conn)
        ml_count = sync_ml_metrics(conn)

        # Attempt MySQL push
        conn.close()
        mysql_count = sync_to_mysql()

        print(f"  [AUDIT SYNC] Complete: {snap_count} snapshots, "
              f"{trade_count} trades, {ml_count} ML metrics"
              + (f", {mysql_count} MySQL rows" if mysql_count > 0 else ""))
        return {
            "snapshots": snap_count,
            "trades": trade_count,
            "ml_metrics": ml_count,
            "mysql_pushed": mysql_count,
        }

    except Exception as e:
        print(f"  [AUDIT SYNC] Error during sync: {e}")
        traceback.print_exc()
        try:
            conn.close()
        except Exception:
            pass
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_full_sync()
    print(f"\nResult: {json.dumps(result, indent=2)}")

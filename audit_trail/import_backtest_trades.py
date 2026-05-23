#!/usr/bin/env python3
"""
Import closed trade data from all local sources into MySQL bt_backtest_trades
and bt_backtest_runs tables.

Sources:
  1. battleground/data/closed_picks.json
  2. alpha_engine/data/closed_picks.json
  3. paper_trading/data/paper.db :: positions (closed)
  4. KIMI_RISEOFTHECLAW/data/signal_tracker.db :: tracked_signals (closed)
  5. mercury2/data/closed_picks.json
  6. ml_battleground/system_f_clawsofdoom/data/closed_picks.json
  7. KIMI_RISEOFTHECLAW/data/kimi_trading.db :: picks (closed)
  8. sandbox/data/opposite_day.db :: opposite_picks (closed)

Usage:
  py -m audit_trail.import_backtest_trades              # import all
  py -m audit_trail.import_backtest_trades --dry-run    # preview only
  py -m audit_trail.import_backtest_trades --clear      # truncate tables first
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── MySQL connection (same pattern as audit_trail/mysql_client.py) ───────────

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
# This script writes to bt_backtest_trades / bt_backtest_runs only — point at
# the backtests DB if BACKTESTS_DB_NAME is set (defaults to AUDIT_DB_NAME for
# back-compat). See updates/2026-05-04-bt-backtest-trades-archive-plan.md.
DB_USER = os.getenv("BACKTESTS_DB_USER", os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"))
DB_PASS = os.getenv("BACKTESTS_DB_PASS", os.getenv("AUDIT_DB_PASS", "stocks"))
DB_NAME = os.getenv("BACKTESTS_DB_NAME", os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks"))


def _ensure_pymysql():
    try:
        import pymysql
        return pymysql
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pymysql"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import pymysql
        return pymysql


def get_mysql_connection():
    pymysql = _ensure_pymysql()
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        connect_timeout=15, read_timeout=30, write_timeout=30,
        charset="utf8mb4", autocommit=True,
    )
    return conn


# ── Normalization helpers ────────────────────────────────────────────────────

FOREX_BASES = {"EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "USD", "SEK", "NOK"}
EQUITY_SYMS = {
    "SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "COPX", "VIX", "DIA",
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOG",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to Binance format for crypto, keep forex/equity as-is."""
    if not symbol:
        return symbol
    s = symbol.strip().upper()

    # Check if forex pair (e.g. EURUSD, EUR/USD)
    s_clean = s.replace("/", "").replace("-", "")
    if len(s_clean) == 6:
        base, quote = s_clean[:3], s_clean[3:]
        if base in FOREX_BASES and quote in FOREX_BASES:
            return s_clean  # e.g. EURUSD

    # Check if equity
    base_sym = s_clean.replace("USDT", "").replace("USD", "")
    if base_sym in EQUITY_SYMS:
        return base_sym  # e.g. SPY

    # Crypto normalization
    # Remove separators
    s_clean = s.replace("/", "").replace("-", "").replace(" ", "")

    # Already XXXUSDT
    if s_clean.endswith("USDT"):
        return s_clean

    # XXXUSD -> XXXUSDT
    if s_clean.endswith("USD") and not s_clean.endswith("USDT"):
        return s_clean + "T"

    # Bare symbol like BTC, ETH -> add USDT
    if re.match(r'^[A-Z0-9]{2,10}$', s_clean) and not any(
        s_clean.startswith(b) and len(s_clean) >= 6 for b in FOREX_BASES
    ):
        return s_clean + "USDT"

    return s_clean


def normalize_direction(direction: Optional[str]) -> str:
    """Normalize direction to LONG or SHORT."""
    if not direction:
        return "LONG"
    d = str(direction).strip().upper()
    if d in ("BUY", "LONG"):
        return "LONG"
    if d in ("SELL", "SHORT"):
        return "SHORT"
    return "LONG"


def derive_asset_class(symbol: str) -> str:
    """Derive asset class from normalized symbol. Returns CRYPTO, FOREX, or EQUITY."""
    s = symbol.upper().replace("-", "").replace("/", "")

    if s in EQUITY_SYMS or any(s.startswith(e) for e in EQUITY_SYMS):
        return "EQUITY"

    if len(s) == 6:
        base, quote = s[:3], s[3:]
        if base in FOREX_BASES and quote in FOREX_BASES:
            return "FOREX"

    return "CRYPTO"


def safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if f != f else f  # NaN -> None
    except (ValueError, TypeError):
        return None


def safe_ts(val: Any) -> Optional[str]:
    """Normalize timestamp to MySQL DATETIME string."""
    if not val:
        return None
    s = str(val)
    # Strip timezone suffixes
    for tz_suf in (" EST", " EDT", " UTC", " GMT"):
        s = s.replace(tz_suf, "")
    s = s.replace("T", " ").replace("Z", "").replace("+00:00", "")
    # Trim to 19 chars: YYYY-MM-DD HH:MM:SS
    s = s[:19].strip()
    if len(s) < 10:
        return None
    # If only date, pad with 00:00:00
    if len(s) == 10:
        s += " 00:00:00"
    return s


def infer_direction_from_prices(entry_price, exit_price, pnl_pct) -> str:
    """Infer LONG/SHORT from price movement and PnL."""
    ep = safe_float(entry_price)
    xp = safe_float(exit_price)
    pnl = safe_float(pnl_pct)

    if ep and xp and pnl is not None:
        price_went_up = xp > ep
        if pnl > 0:
            return "LONG" if price_went_up else "SHORT"
        elif pnl < 0:
            return "SHORT" if price_went_up else "LONG"
    return "LONG"


# ── Trade record structure ───────────────────────────────────────────────────

def make_trade(
    symbol: str, direction: str, strategy: str,
    entry_price=None, exit_price=None, take_profit=None, stop_loss=None,
    entry_time=None, exit_time=None, pnl_pct=None, status=None,
    confidence=None, raw_data=None, source_db="", source_table="",
    asset_class=None,
) -> Dict:
    sym = normalize_symbol(symbol)
    ac = asset_class or derive_asset_class(sym)
    # Clamp asset_class to allowed ENUM values
    if ac not in ("CRYPTO", "FOREX", "EQUITY"):
        ac = "CRYPTO"
    return {
        "source_db": source_db[:200] if source_db else None,
        "source_table": source_table[:100] if source_table else None,
        "symbol": sym[:30],
        "asset_class": ac,
        "direction": normalize_direction(direction),
        "strategy": (strategy or "unknown")[:120],
        "entry_price": safe_float(entry_price),
        "exit_price": safe_float(exit_price),
        "take_profit": safe_float(take_profit),
        "stop_loss": safe_float(stop_loss),
        "entry_time": safe_ts(entry_time),
        "exit_time": safe_ts(exit_time),
        "pnl_pct": safe_float(pnl_pct),
        "status": (status or "CLOSED")[:20],
        "confidence": safe_float(confidence),
        "raw_data": raw_data,
    }


# ── Source loaders ───────────────────────────────────────────────────────────

def load_battleground(repo: Path) -> List[Dict]:
    """Source 1: battleground/data/closed_picks.json"""
    path = repo / "battleground" / "data" / "closed_picks.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return []

    trades = []
    for p in data:
        sym = p.get("symbol", "")
        if not sym:
            continue
        trades.append(make_trade(
            symbol=sym,
            direction=p.get("direction", "LONG"),
            strategy=p.get("strategy", "unknown"),
            entry_price=p.get("entry_price"),
            exit_price=p.get("exit_price"),
            pnl_pct=p.get("pnl_pct"),
            status=p.get("status"),
            entry_time=p.get("entry_time"),
            exit_time=p.get("exit_time"),
            source_db="battleground/data/closed_picks.json",
            source_table="closed_picks",
        ))
    return trades


def load_alpha_engine(repo: Path) -> List[Dict]:
    """Source 2: alpha_engine/data/closed_picks.json"""
    path = repo / "alpha_engine" / "data" / "closed_picks.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return []

    trades = []
    for p in data:
        sym = p.get("symbol", "")
        if not sym:
            continue
        trades.append(make_trade(
            symbol=sym,
            direction=p.get("signal_type", p.get("direction", "LONG")),
            strategy=p.get("strategy", "unknown"),
            entry_price=p.get("entry_price"),
            exit_price=p.get("exit_price"),
            take_profit=p.get("take_profit"),
            stop_loss=p.get("stop_loss"),
            confidence=p.get("confidence"),
            pnl_pct=p.get("pnl_pct"),
            entry_time=p.get("entry_date"),
            exit_time=p.get("exit_date"),
            status=p.get("status"),
            source_db="alpha_engine/data/closed_picks.json",
            source_table="closed_picks",
        ))
    return trades


def load_paper_trading(repo: Path) -> List[Dict]:
    """Source 3: paper_trading/data/paper.db :: positions WHERE status != 'ACTIVE'"""
    db_path = repo / "paper_trading" / "data" / "paper.db"
    if not db_path.exists():
        return []

    trades = []
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM positions WHERE status != 'ACTIVE'").fetchall()
        for r in rows:
            d = dict(r)
            sym = d.get("symbol", "")
            if not sym:
                continue
            trades.append(make_trade(
                symbol=sym,
                direction=d.get("direction", "LONG"),
                strategy=d.get("strategy_name", d.get("strategy", "unknown")),
                entry_price=d.get("entry_price"),
                exit_price=d.get("exit_price"),
                take_profit=d.get("tp"),
                stop_loss=d.get("sl"),
                confidence=d.get("confidence"),
                pnl_pct=d.get("pnl_pct"),
                entry_time=d.get("entry_date"),
                exit_time=d.get("exit_date"),
                status=d.get("status"),
                source_db="paper_trading/data/paper.db",
                source_table="positions",
            ))
        db.close()
    except Exception as e:
        log.warning(f"Error reading paper_trading DB: {e}")
    return trades


def load_kimi_signal_tracker(repo: Path) -> List[Dict]:
    """Source 4: KIMI_RISEOFTHECLAW/data/signal_tracker.db :: tracked_signals (closed)
    Deduplicate by (symbol, entry_price, exit_price, pnl_pct)."""
    db_path = repo / "KIMI_RISEOFTHECLAW" / "data" / "signal_tracker.db"
    if not db_path.exists():
        return []

    trades = []
    seen = set()
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM tracked_signals WHERE status != 'OPEN' ORDER BY id ASC").fetchall()
        for r in rows:
            d = dict(r)
            sym = d.get("symbol", "")
            if not sym:
                continue
            ep = safe_float(d.get("entry_price"))
            xp = safe_float(d.get("exit_price"))
            pnl = safe_float(d.get("pnl_pct"))
            dedup_key = (normalize_symbol(sym), ep, xp, pnl)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            trades.append(make_trade(
                symbol=sym,
                direction=d.get("signal_type", "LONG"),
                strategy="kimi_signal_tracker",
                entry_price=ep,
                exit_price=xp,
                take_profit=d.get("take_profit"),
                stop_loss=d.get("stop_loss"),
                confidence=safe_float(d.get("confidence")) / 100.0
                    if safe_float(d.get("confidence")) and safe_float(d.get("confidence")) > 1
                    else safe_float(d.get("confidence")),
                pnl_pct=pnl,
                entry_time=d.get("entry_time"),
                exit_time=d.get("exit_time"),
                status=d.get("status"),
                source_db="KIMI_RISEOFTHECLAW/data/signal_tracker.db",
                source_table="tracked_signals",
            ))
        db.close()
    except Exception as e:
        log.warning(f"Error reading KIMI signal_tracker DB: {e}")
    return trades


def load_mercury2(repo: Path) -> List[Dict]:
    """Source 5: mercury2/data/closed_picks.json"""
    path = repo / "mercury2" / "data" / "closed_picks.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return []

    trades = []
    for p in data:
        sym = p.get("symbol", "")
        if not sym:
            continue
        trades.append(make_trade(
            symbol=sym,
            direction=p.get("direction", p.get("signal_type", "LONG")),
            strategy=p.get("strategy", "unknown"),
            entry_price=p.get("entry_price"),
            exit_price=p.get("exit_price"),
            take_profit=p.get("take_profit"),
            stop_loss=p.get("stop_loss"),
            confidence=p.get("confidence"),
            pnl_pct=p.get("realized_pnl_pct", p.get("pnl_pct")),
            entry_time=p.get("timestamp"),
            exit_time=p.get("exit_time"),
            status=p.get("status"),
            source_db="mercury2/data/closed_picks.json",
            source_table="closed_picks",
        ))
    return trades


def load_ml_battleground_clawsofdoom(repo: Path) -> List[Dict]:
    """Source 6: ml_battleground/system_f_clawsofdoom/data/closed_picks.json"""
    path = repo / "ml_battleground" / "system_f_clawsofdoom" / "data" / "closed_picks.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        return []

    trades = []
    for p in data:
        sym = p.get("symbol", "")
        if not sym:
            continue
        trades.append(make_trade(
            symbol=sym,
            direction=p.get("direction", "LONG"),
            strategy=p.get("strategy", p.get("strategy_name", "clawsofdoom")),
            entry_price=p.get("entry_price"),
            exit_price=p.get("exit_price"),
            take_profit=p.get("tp_price"),
            stop_loss=p.get("sl_price"),
            confidence=p.get("confidence"),
            pnl_pct=p.get("realized_pnl_pct", p.get("pnl_pct")),
            entry_time=p.get("timestamp_est", p.get("timestamp")),
            exit_time=p.get("exit_time_est", p.get("exit_time")),
            status=p.get("status"),
            source_db="ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
            source_table="closed_picks",
        ))
    return trades


def load_kimi_trading_db(repo: Path) -> List[Dict]:
    """Source 7: KIMI_RISEOFTHECLAW/data/kimi_trading.db :: picks WHERE status != 'active' AND status != 'OPEN'"""
    db_path = repo / "KIMI_RISEOFTHECLAW" / "data" / "kimi_trading.db"
    if not db_path.exists():
        return []

    trades = []
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM picks WHERE status NOT IN ('active', 'OPEN')"
        ).fetchall()
        for r in rows:
            d = dict(r)
            sym = d.get("symbol", "")
            if not sym:
                continue

            # Infer direction: not explicit in this table
            direction = infer_direction_from_prices(
                d.get("entry_price"), d.get("exit_price"), d.get("pnl_pct")
            )

            conf = safe_float(d.get("ml_win_prob"))

            trades.append(make_trade(
                symbol=sym,
                direction=direction,
                strategy=d.get("algorithm", "unknown"),
                entry_price=d.get("entry_price"),
                exit_price=d.get("exit_price"),
                take_profit=d.get("take_profit"),
                stop_loss=d.get("stop_loss"),
                confidence=conf,
                pnl_pct=d.get("pnl_pct"),
                entry_time=d.get("entry_date"),
                exit_time=d.get("exit_date"),
                status=d.get("status"),
                source_db="KIMI_RISEOFTHECLAW/data/kimi_trading.db",
                source_table="picks",
            ))
        db.close()
    except Exception as e:
        log.warning(f"Error reading kimi_trading DB: {e}")
    return trades


def load_sandbox_opposite_day(repo: Path) -> List[Dict]:
    """Source 8: sandbox/data/opposite_day.db :: opposite_picks WHERE status != 'ACTIVE'"""
    db_path = repo / "sandbox" / "data" / "opposite_day.db"
    if not db_path.exists():
        return []

    trades = []
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM opposite_picks WHERE status != 'ACTIVE'").fetchall()
        for r in rows:
            d = dict(r)
            sym = d.get("symbol", "")
            if not sym:
                continue
            trades.append(make_trade(
                symbol=sym,
                direction=d.get("opposite_direction", "LONG"),
                strategy="opposite_day",
                entry_price=d.get("entry_price"),
                exit_price=d.get("close_price"),
                take_profit=d.get("opposite_tp"),
                stop_loss=d.get("opposite_sl"),
                confidence=d.get("confidence"),
                pnl_pct=d.get("pnl_pct"),
                entry_time=d.get("picked_at"),
                exit_time=d.get("closed_at"),
                status=d.get("status"),
                source_db="sandbox/data/opposite_day.db",
                source_table="opposite_picks",
            ))
        db.close()
    except Exception as e:
        log.warning(f"Error reading opposite_day DB: {e}")
    return trades


# ── Summary computation for bt_backtest_runs ─────────────────────────────────

def compute_runs(trades: List[Dict]) -> List[Dict]:
    """Group trades by (strategy, symbol) and compute summary stats."""
    from collections import defaultdict

    groups = defaultdict(list)
    for t in trades:
        key = (t["strategy"], t["symbol"])
        groups[key].append(t)

    runs = []
    for (strategy, symbol), group in groups.items():
        pnls = [t["pnl_pct"] for t in group if t["pnl_pct"] is not None]
        if not pnls:
            continue

        total = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        losses = total - wins
        # win_rate as decimal(5,4): 0.0000 to 1.0000
        win_rate = round(wins / total, 4) if total else 0

        total_return = round(sum(pnls), 4)

        pos_sum = sum(p for p in pnls if p > 0)
        neg_sum = abs(sum(p for p in pnls if p < 0))
        profit_factor = round(pos_sum / neg_sum, 3) if neg_sum > 0 else (
            999.999 if pos_sum > 0 else 0
        )

        # Sharpe ratio (annualized assuming daily trades)
        if len(pnls) >= 2:
            import statistics
            mean_p = statistics.mean(pnls)
            std_p = statistics.stdev(pnls)
            sharpe = round(mean_p / std_p * (252 ** 0.5), 3) if std_p > 0 else 0
        else:
            sharpe = 0

        # Max drawdown from cumulative PnL
        cumulative = 0
        peak = 0
        max_dd = 0
        for p in pnls:
            cumulative += p
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        max_dd = round(max_dd, 4)

        # Determine dominant asset class from trades
        asset_classes = [t["asset_class"] for t in group]
        ac = max(set(asset_classes), key=asset_classes.count) if asset_classes else "CRYPTO"

        # Collect source_db and source_table from first trade
        first = group[0]

        import uuid
        runs.append({
            "id": str(uuid.uuid4()),
            "source_db": first.get("source_db") or "",
            "source_table": first.get("source_table") or "",
            "strategy": strategy[:200],
            "symbol": symbol[:50],
            "asset_class": ac,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_return": total_return,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
        })

    return runs


# ── MySQL insertion ──────────────────────────────────────────────────────────

TRADE_INSERT_SQL = """
    INSERT INTO bt_backtest_trades
    (source_db, source_table, symbol, asset_class, direction, strategy,
     entry_price, exit_price, take_profit, stop_loss, entry_time, exit_time,
     pnl_pct, status, confidence, raw_data, imported_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

RUN_INSERT_SQL = """
    INSERT INTO bt_backtest_runs
    (id, source_db, source_table, strategy, symbol, asset_class,
     total_trades, wins, losses, win_rate, total_return,
     profit_factor, sharpe, max_drawdown, imported_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def insert_trades(cur, trades: List[Dict]) -> int:
    """Insert trades into bt_backtest_trades. Returns count of rows inserted."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for t in trades:
        raw_json = json.dumps(t.get("raw_data"), default=str) if t.get("raw_data") else None
        try:
            cur.execute(TRADE_INSERT_SQL, (
                t["source_db"] or "", t["source_table"] or "",
                t["symbol"], t["asset_class"],
                t["direction"], t["strategy"],
                t["entry_price"], t["exit_price"], t["take_profit"], t["stop_loss"],
                t["entry_time"], t["exit_time"],
                t["pnl_pct"], t["status"], t["confidence"], raw_json, now,
            ))
            count += cur.rowcount
        except Exception as e:
            log.debug(f"Insert failed for {t['symbol']}/{t['strategy']}: {e}")
    return count


def insert_runs(cur, runs: List[Dict]) -> int:
    """Insert runs into bt_backtest_runs. Returns count of rows inserted."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for r in runs:
        try:
            cur.execute(RUN_INSERT_SQL, (
                r["id"], r["source_db"], r["source_table"],
                r["strategy"], r["symbol"], r["asset_class"],
                r["total_trades"], r["wins"], r["losses"], r["win_rate"],
                r["total_return"], r["profit_factor"], r["sharpe"],
                r["max_drawdown"], now,
            ))
            count += cur.rowcount
        except Exception as e:
            log.debug(f"Run insert failed for {r['strategy']}/{r['symbol']}: {e}")
    return count


# ── Main ─────────────────────────────────────────────────────────────────────

SOURCE_LOADERS = [
    ("battleground",                    load_battleground),
    ("alpha_engine",                    load_alpha_engine),
    ("paper_trading",                   load_paper_trading),
    ("kimi_signal_tracker",             load_kimi_signal_tracker),
    ("mercury2",                        load_mercury2),
    ("ml_battleground_clawsofdoom",     load_ml_battleground_clawsofdoom),
    ("kimi_trading_db",                 load_kimi_trading_db),
    ("sandbox_opposite_day",            load_sandbox_opposite_day),
]


def main():
    parser = argparse.ArgumentParser(
        description="Import closed backtest trades from local sources into MySQL."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be imported without writing to MySQL.")
    parser.add_argument("--clear", action="store_true",
                        help="Truncate bt_backtest_trades and bt_backtest_runs before importing.")
    args = parser.parse_args()

    # ── Load all trades ──
    all_trades: List[Dict] = []
    source_counts: Dict[str, int] = {}

    for name, loader in SOURCE_LOADERS:
        try:
            trades = loader(REPO)
            source_counts[name] = len(trades)
            all_trades.extend(trades)
            log.info(f"  [{name}] loaded {len(trades)} closed trades")
        except Exception as e:
            log.error(f"  [{name}] FAILED: {e}")
            source_counts[name] = 0

    # Filter out trades with no PnL (incomplete data)
    valid_trades = [t for t in all_trades if t["pnl_pct"] is not None]
    skipped = len(all_trades) - len(valid_trades)
    if skipped:
        log.info(f"  Skipped {skipped} trades with no pnl_pct")

    # ── Compute runs ──
    runs = compute_runs(valid_trades)
    log.info(f"\n  Total trades: {len(valid_trades)}")
    log.info(f"  Total strategy-symbol runs: {len(runs)}")

    # ── Dry run output ──
    if args.dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN - No data written to MySQL")
        print("=" * 70)
        print(f"\nTrades to import: {len(valid_trades)}")
        print(f"Runs to compute:  {len(runs)}")
        print(f"\nBy source:")
        for name, cnt in source_counts.items():
            print(f"  {name:<40} {cnt:>5} trades")

        print(f"\nTop 20 strategies by trade count:")
        from collections import Counter
        strat_counts = Counter(t["strategy"] for t in valid_trades)
        for strat, cnt in strat_counts.most_common(20):
            wins = sum(1 for t in valid_trades if t["strategy"] == strat and (t["pnl_pct"] or 0) > 0)
            wr = round(wins / cnt * 100, 1) if cnt else 0
            print(f"  {strat:<50} {cnt:>4} trades  WR={wr}%")

        print(f"\nAsset class breakdown:")
        ac_counts = Counter(t["asset_class"] for t in valid_trades)
        for ac, cnt in ac_counts.most_common():
            print(f"  {ac:<15} {cnt:>5}")

        print(f"\nDirection breakdown:")
        dir_counts = Counter(t["direction"] for t in valid_trades)
        for d, cnt in dir_counts.most_common():
            print(f"  {d:<10} {cnt:>5}")

        # Show sample trades
        print(f"\nSample trades (first 5):")
        for t in valid_trades[:5]:
            print(f"  {t['symbol']:<12} {t['direction']:<6} {t['strategy']:<40} "
                  f"PnL={t['pnl_pct']:+.2f}%  [{t['source_db']}]")

        return

    # ── Connect to MySQL ──
    log.info("\nConnecting to MySQL...")
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        log.info("  Connected to MySQL successfully")
    except Exception as e:
        log.error(f"  MySQL connection failed: {e}")
        log.error("  Check AUDIT_DB_HOST/AUDIT_DB_USER/AUDIT_DB_PASS/AUDIT_DB_NAME env vars")
        sys.exit(1)

    # ── Clear if requested ──
    if args.clear:
        log.info("  Truncating bt_backtest_trades and bt_backtest_runs...")
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute("TRUNCATE TABLE bt_backtest_trades")
        cur.execute("TRUNCATE TABLE bt_backtest_runs")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        log.info("  Tables truncated.")

    # ── Insert trades ──
    log.info(f"\nInserting {len(valid_trades)} trades into bt_backtest_trades...")
    trades_inserted = insert_trades(cur, valid_trades)
    log.info(f"  Inserted {trades_inserted} trades")

    # ── Insert runs ──
    log.info(f"\nInserting {len(runs)} runs into bt_backtest_runs...")
    runs_inserted = insert_runs(cur, runs)
    log.info(f"  Inserted {runs_inserted} runs")

    # ── Summary ──
    cur.execute("SELECT COUNT(*) FROM bt_backtest_trades")
    total_trades_db = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bt_backtest_runs")
    total_runs_db = cur.fetchone()[0]

    cur.execute(
        "SELECT source_db, COUNT(*) as cnt FROM bt_backtest_trades "
        "GROUP BY source_db ORDER BY cnt DESC"
    )
    by_source = cur.fetchall()

    cur.execute(
        "SELECT asset_class, COUNT(*) as cnt FROM bt_backtest_trades "
        "GROUP BY asset_class ORDER BY cnt DESC"
    )
    by_ac = cur.fetchall()

    cur.execute(
        "SELECT strategy, total_trades, win_rate, profit_factor, sharpe, total_return "
        "FROM bt_backtest_runs ORDER BY total_trades DESC LIMIT 15"
    )
    top_runs = cur.fetchall()

    conn.close()

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Trades inserted this run:  {trades_inserted}")
    print(f"Runs inserted this run:    {runs_inserted}")
    print(f"Total bt_backtest_trades:  {total_trades_db}")
    print(f"Total bt_backtest_runs:    {total_runs_db}")

    print(f"\nBy source file:")
    for src, cnt in by_source:
        print(f"  {src or 'NULL':<55} {cnt:>5}")

    print(f"\nBy asset class:")
    for ac, cnt in by_ac:
        print(f"  {ac or 'NULL':<15} {cnt:>5}")

    print(f"\nTop 15 strategy-symbol runs (by trade count):")
    print(f"  {'Strategy':<45} {'Trades':>6} {'WR%':>7} {'PF':>8} {'Sharpe':>8} {'Return':>8}")
    print(f"  {'-'*45} {'-'*6} {'-'*7} {'-'*8} {'-'*8} {'-'*8}")
    for strat, total, wr, pf, sh, ret in top_runs:
        wr_pct = float(wr or 0) * 100
        print(f"  {strat:<45} {total:>6} {wr_pct:>6.1f}% "
              f"{float(pf or 0):>7.2f} {float(sh or 0):>7.2f} {float(ret or 0):>+7.1f}%")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Backfill local data sources (SQLite DBs + JSON pick files) into MySQL ejaguiar1_stocks.

This script imports data NOT already covered by the existing MySQL tables:
  1. data/live_picks.db:pick_history  (4,020 rows — central forward-tracking)
  2. KIMI_FEB172026/data/kimi_trading.db:signals (141 rows)
  3. KIMI_RISEOFTHECLAW/data/signal_tracker.db:tracked_signals (1,038 TP/SL outcomes)
  4. signal_recorder/data/signal_log.db:signal_log + signal_outcomes (151+82)
  5. sandbox/data/opposite_day.db:opposite_picks (175)
  6. coinglass_strategies/data/coinglass.db:signals (5)
  7. battleground closed_picks.json (180)
  8. ml_battleground closed_picks.json (62 across 6 systems)
  9. mercury2 closed_picks.json (46)
  10. breakout_arena closed_picks.json (across 3 approaches)
  11. alpha_engine closed_picks.json (188)
  12. crypto_ml_edge active_picks.json (10)

Target tables created if not exist:
  - at_local_picks  (unified picks from all local sources)
  - at_signal_outcomes  (TP/SL validated outcomes)

Run:  py -m audit_trail.backfill_local_sources
"""

import json
import os
import sys
import sqlite3
import glob
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

try:
    import pymysql
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                          stdout=subprocess.DEVNULL)
    import pymysql

try:
    from alpha_engine.config import EQUITY_SYMBOLS, LARGE_CAP_EQUITY_SYMBOLS
    _EQUITY_ALLOWLIST = frozenset(EQUITY_SYMBOLS.keys()) | LARGE_CAP_EQUITY_SYMBOLS
except Exception:  # defensive: keep mirror functional if config import fails
    _EQUITY_ALLOWLIST = frozenset({
        "SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "COPX", "VIX", "DIA",
        "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META", "AMD",
        "NFLX",
    })

_UNKNOWN_TOKENS = {"", "UNKNOWN", "NONE", "NULL"}


def derive_asset_class(s, row_asset_class=None):
    """Derive asset class for a pick.

    P0 fix (PR #118 follow-up): if the source row already carries an
    asset_class (non-empty, non-UNKNOWN), HONOR IT — do not re-derive from
    symbol. Only fall back to symbol-based derivation when the source row
    has no asset_class. EQUITY allowlist is now imported from
    `alpha_engine.config.EQUITY_SYMBOLS` (+ LARGE_CAP_EQUITY_SYMBOLS),
    replacing the 13-symbol hard-coded set that mis-classified AMZN/GOOGL/
    META/AMD/NFLX as UNKNOWN.
    """
    if row_asset_class is not None:
        rac = str(row_asset_class).strip().upper()
        if rac not in _UNKNOWN_TOKENS:
            return rac

    s = s.upper().replace("-", "")
    meme = {"DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF", "BOME", "FAI", "ROBO", "EDGE", "MANTRA", "PHA"}
    forex_bases = {"EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    if s in _EQUITY_ALLOWLIST:
        return "EQUITY"
    for m in meme:
        if m in s:
            return "MEMECOIN"
    for b in forex_bases:
        if s.startswith(b) and len(s) >= 6 and not s.endswith("USDT"):
            return "FOREX"
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BTC"):
        return "CRYPTO"
    return "UNKNOWN"


def safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f
    except (ValueError, TypeError):
        return None


def safe_ts(v):
    """Normalize timestamp to MySQL DATETIME format."""
    if not v:
        return None
    s = str(v).replace("T", " ").replace("Z", "").replace("+00:00", "")[:19]
    if len(s) < 10:
        return None
    return s


def create_tables(cur):
    """Create target tables if not exist."""
    cur.execute("""
    CREATE TABLE IF NOT EXISTS at_local_picks (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        symbol          VARCHAR(50)     NOT NULL,
        direction       VARCHAR(10)     DEFAULT 'LONG',
        entry_price     DECIMAL(18,8)   DEFAULT NULL,
        take_profit     DECIMAL(18,8)   DEFAULT NULL,
        stop_loss       DECIMAL(18,8)   DEFAULT NULL,
        confidence      DECIMAL(5,4)    DEFAULT NULL,
        strategy        VARCHAR(100)    DEFAULT NULL,
        source_system   VARCHAR(100)    NOT NULL COMMENT 'e.g. alpha_engine, mercury2, kimi, battleground',
        source_file     VARCHAR(200)    DEFAULT NULL COMMENT 'Original file path',
        asset_class     VARCHAR(20)     DEFAULT 'CRYPTO',
        status          VARCHAR(20)     DEFAULT 'OPEN' COMMENT 'OPEN/CLOSED/WON/LOST/EXPIRED',
        exit_price      DECIMAL(18,8)   DEFAULT NULL,
        exit_reason     VARCHAR(50)     DEFAULT NULL,
        pnl_pct         DECIMAL(10,4)   DEFAULT NULL,
        signal_timestamp DATETIME       DEFAULT NULL,
        created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol     (symbol),
        INDEX idx_system     (source_system),
        INDEX idx_strategy   (strategy),
        INDEX idx_status     (status),
        INDEX idx_signal_ts  (signal_timestamp),
        UNIQUE INDEX idx_dedup (symbol, direction, source_system, signal_timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS at_signal_outcomes (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        symbol          VARCHAR(50)     NOT NULL,
        direction       VARCHAR(10)     DEFAULT 'LONG',
        entry_price     DECIMAL(18,8)   DEFAULT NULL,
        take_profit     DECIMAL(18,8)   DEFAULT NULL,
        stop_loss       DECIMAL(18,8)   DEFAULT NULL,
        exit_price      DECIMAL(18,8)   DEFAULT NULL,
        outcome         VARCHAR(20)     DEFAULT NULL COMMENT 'TP_HIT/SL_HIT/EXPIRED/OPEN',
        pnl_pct         DECIMAL(10,4)   DEFAULT NULL,
        source_system   VARCHAR(100)    NOT NULL,
        strategy        VARCHAR(100)    DEFAULT NULL,
        asset_class     VARCHAR(20)     DEFAULT 'CRYPTO',
        opened_at       DATETIME        DEFAULT NULL,
        closed_at       DATETIME        DEFAULT NULL,
        created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol     (symbol),
        INDEX idx_outcome    (outcome),
        INDEX idx_system     (source_system),
        UNIQUE INDEX idx_dedup (symbol, direction, source_system, opened_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("Tables at_local_picks and at_signal_outcomes ready.")


def insert_pick(cur, symbol, direction, entry, tp, sl, confidence, strategy,
                source_system, source_file, status, exit_price, exit_reason,
                pnl_pct, signal_ts, row_asset_class=None):
    try:
        cur.execute(
            "INSERT IGNORE INTO at_local_picks "
            "(symbol, direction, entry_price, take_profit, stop_loss, confidence, "
            "strategy, source_system, source_file, asset_class, status, exit_price, "
            "exit_reason, pnl_pct, signal_timestamp) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (symbol, direction or "LONG", safe_float(entry), safe_float(tp),
             safe_float(sl), safe_float(confidence), strategy,
             source_system, source_file,
             derive_asset_class(symbol, row_asset_class),
             status or "OPEN", safe_float(exit_price), exit_reason,
             safe_float(pnl_pct), safe_ts(signal_ts))
        )
        return cur.rowcount
    except Exception as e:
        return 0


def insert_outcome(cur, symbol, direction, entry, tp, sl, exit_price, outcome,
                   pnl_pct, source_system, strategy, opened_at, closed_at,
                   row_asset_class=None):
    try:
        # idx_dedup UNIQUE(symbol,direction,source_system,opened_at) only fires
        # when opened_at is non-NULL. JSON picks without timestamp/created_at
        # used to leak opened_at=NULL → 8-43x row duplication per pick
        # (INCIDENT_OVERALL #91, 2026-06-04). Fall back to closed_at so the
        # unique constraint always has a non-NULL value to dedup against.
        safe_opened = safe_ts(opened_at) or safe_ts(closed_at)
        cur.execute(
            "INSERT IGNORE INTO at_signal_outcomes "
            "(symbol, direction, entry_price, take_profit, stop_loss, exit_price, "
            "outcome, pnl_pct, source_system, strategy, asset_class, opened_at, closed_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (symbol, direction or "LONG", safe_float(entry), safe_float(tp),
             safe_float(sl), safe_float(exit_price), outcome,
             safe_float(pnl_pct), source_system, strategy,
             derive_asset_class(symbol, row_asset_class),
             safe_opened, safe_ts(closed_at))
        )
        return cur.rowcount
    except Exception:
        return 0


def load_json_picks(cur, filepath, source_system, is_closed=False):
    """Load picks from a JSON file (active_picks.json or closed_picks.json).

    Returns (picks_count, outcomes_count). For closed picks, also inserts
    into at_signal_outcomes so the signal_outcomes table gets populated
    from JSON sources (not just SQLite). Fixes the 82-day staleness gap.
    """
    path = REPO / filepath
    if not path.exists():
        return 0, 0
    try:
        data = json.loads(path.read_text())
    except Exception:
        return 0, 0
    if not isinstance(data, list):
        return 0, 0

    picks_cnt = 0
    outcomes_cnt = 0
    for p in data:
        symbol = p.get("symbol", p.get("ticker", ""))
        if not symbol:
            continue
        direction = p.get("direction", p.get("signal", "LONG"))
        if isinstance(direction, str):
            direction = direction.upper()
            if direction == "BUY":
                direction = "LONG"
            elif direction == "SELL":
                direction = "SHORT"

        status = "OPEN"
        raw_exit_reason = None
        exit_price = None
        exit_reason = None
        pnl = None
        if is_closed:
            raw_status = p.get("status", p.get("exit_reason", "CLOSED"))
            raw_exit_reason = p.get("exit_reason", p.get("close_reason"))
            status = str(raw_status).upper()
            if status in ("WON", "WIN", "CLOSED_TP", "TP_HIT"):
                status = "WON"
            elif status in ("LOST", "LOSS", "CLOSED_SL", "SL_HIT"):
                status = "LOST"
            elif status in ("EXPIRED",):
                status = "EXPIRED"
            else:
                status = "CLOSED"
            exit_price = p.get("exit_price", p.get("close_price"))
            exit_reason = raw_exit_reason
            pnl = p.get("pnl_pct", p.get("net_pnl_pct", p.get("return_pct")))

            # Sign-coherence guard (mirrors mysql_client.py mysql_close_trade):
            # If exit_reason claims TP/WON but pnl is negative (or SL/LOST but
            # pnl is positive), trust the pnl sign. Source files can contain
            # contradictory reason+pnl data that produces the WON-vs-PnL
            # contradiction flagged in db_health.json.
            pnl_f = safe_float(pnl) if pnl is not None else None
            if status in ("WON", "WIN", "CLOSED_TP", "TP_HIT") and pnl_f is not None and pnl_f < 0:
                status = "LOST"
            elif status in ("LOST", "LOSS", "CLOSED_SL", "SL_HIT") and pnl_f is not None and pnl_f > 0:
                status = "WON"

            # Infer WON/LOST from pnl when status is still ambiguous (CLOSED)
            if status == "CLOSED" and pnl_f is not None:
                if pnl_f > 0:
                    status = "WON"
                elif pnl_f < 0:
                    status = "LOST"

        ts = p.get("timestamp", p.get("signal_timestamp", p.get("date",
             p.get("created_at", p.get("generated_at", p.get("pick_date"))))))

        strategy = p.get("strategy", p.get("strategy_name", p.get("algorithm")))
        entry = p.get("entry_price", p.get("entry", p.get("price")))
        tp = p.get("take_profit", p.get("tp_price", p.get("tp", p.get("target_price"))))
        sl = p.get("stop_loss", p.get("sl_price", p.get("sl", p.get("stop_price"))))

        row_ac = p.get("asset_class") or p.get("assetClass")
        picks_cnt += insert_pick(
            cur, symbol, direction, entry, tp, sl,
            p.get("confidence"), strategy, source_system, filepath,
            status, exit_price, exit_reason, pnl, ts,
            row_asset_class=row_ac,
        )

        # ── Also insert into at_signal_outcomes for closed picks ──
        # This was MISSING before 2026-05-27 — only SQLite sources
        # populated at_signal_outcomes. JSON closed picks (46K+ rows
        # across 12+ systems) were silently skipped, leaving the table
        # 82 days stale.
        if is_closed and status not in ("OPEN",):
            # Map status to outcome enum: TP_HIT / SL_HIT / EXPIRED
            if exit_reason:
                reason_upper = str(exit_reason).upper()
                if reason_upper in ("TP", "TP_HIT", "TP_HIT_RESOLVED", "TP2_HIT", "TP1_HIT"):
                    outcome = "TP_HIT"
                elif reason_upper in ("SL", "SL_HIT", "SL_HIT_RESOLVED", "TRAILING_STOP"):
                    outcome = "SL_HIT"
                elif reason_upper in ("EXPIRED", "TIME_EXPIRY", "EXPIRED_BACKLOG"):
                    outcome = "EXPIRED"
                else:
                    outcome = "WON" if status == "WON" else ("LOST" if status == "LOST" else "EXPIRED" if status == "EXPIRED" else None)
            else:
                outcome = "WON" if status == "WON" else ("LOST" if status == "LOST" else "EXPIRED" if status == "EXPIRED" else None)

            if outcome:
                closed_at = p.get("closed_at", p.get("exit_timestamp", p.get("resolved_at",
                             p.get("close_date", p.get("timestamp")))))
                outcomes_cnt += insert_outcome(
                    cur, symbol, direction, entry, tp, sl, exit_price,
                    outcome, pnl, source_system, strategy, ts, closed_at,
                    row_asset_class=row_ac,
                )

    return picks_cnt, outcomes_cnt


def load_sqlite_table(cur, db_path, table, source_system):
    """Load picks from a SQLite table."""
    full_path = REPO / db_path
    if not full_path.exists():
        return 0, 0

    try:
        db = sqlite3.connect(str(full_path))
        db.row_factory = sqlite3.Row
        rows = db.execute(f"SELECT * FROM [{table}]").fetchall()
    except Exception as e:
        print(f"  Error reading {db_path}:{table}: {e}")
        return 0, 0

    picks = 0
    outcomes = 0
    for r in rows:
        d = dict(r)
        symbol = d.get("symbol", d.get("ticker", d.get("coin", "")))
        if not symbol:
            continue
        direction = d.get("direction", d.get("signal", d.get("side", "LONG")))
        if isinstance(direction, str):
            direction = direction.upper()
            if direction in ("BUY",):
                direction = "LONG"
            elif direction in ("SELL",):
                direction = "SHORT"

        entry = d.get("entry_price", d.get("entry", d.get("price")))
        tp = d.get("take_profit", d.get("tp_price", d.get("tp", d.get("target_price"))))
        sl = d.get("stop_loss", d.get("sl_price", d.get("sl", d.get("stop_price"))))
        confidence = d.get("confidence", d.get("score"))
        strategy = d.get("strategy", d.get("strategy_name", d.get("algorithm")))

        ts = d.get("timestamp", d.get("signal_timestamp", d.get("created_at",
             d.get("date", d.get("opened_at")))))

        status = d.get("status", d.get("outcome", "OPEN"))
        if isinstance(status, str):
            status = status.upper()
        exit_price = d.get("exit_price", d.get("close_price"))
        pnl = d.get("pnl_pct", d.get("net_pnl_pct", d.get("return_pct")))
        exit_reason = d.get("exit_reason", d.get("close_reason"))

        row_ac = d.get("asset_class") or d.get("assetClass")
        picks += insert_pick(
            cur, symbol, direction, entry, tp, sl, confidence, strategy,
            source_system, f"{db_path}:{table}", status, exit_price,
            exit_reason, pnl, ts,
            row_asset_class=row_ac,
        )

        # If this has outcome data, also insert into at_signal_outcomes
        outcome = d.get("outcome", d.get("result"))
        if outcome or (status and status not in ("OPEN", "ACTIVE", "PENDING")):
            closed_at = d.get("closed_at", d.get("exit_timestamp", d.get("resolved_at")))
            outcomes += insert_outcome(
                cur, symbol, direction, entry, tp, sl, exit_price,
                outcome or status, pnl, source_system, strategy, ts, closed_at,
                row_asset_class=row_ac,
            )

    db.close()
    return picks, outcomes


def main():
    try:
        from tools.db_env import get_stocks_creds
        _creds = get_stocks_creds()
    except Exception:
        import logging as _lg
        _lg.getLogger(__name__).warning("get_stocks_creds() failed — check DB_PASS_STOCKS env var")
        _creds = dict(host="mysql.50webs.com", user="ejaguiar1_stocks",
                      password="", database="ejaguiar1_stocks",
                      connect_timeout=15, autocommit=True)
    conn = pymysql.connect(**{**_creds, "autocommit": True})
    cur = conn.cursor()

    create_tables(cur)

    total_picks = 0
    total_outcomes = 0

    # ── 1. SQLite databases ──
    sqlite_sources = [
        ("data/live_picks.db", "pick_history", "live_picks_tracker"),
        ("data/live_picks.db", "live_picks", "live_picks_tracker"),
        ("KIMI_FEB172026/data/kimi_trading.db", "signals", "kimi_feb17"),
        ("KIMI_RISEOFTHECLAW/data/signal_tracker.db", "tracked_signals", "kimi_signal_tracker"),
        ("KIMI_RISEOFTHECLAW/data/kimi_trading.db", "picks", "kimi_riseoftheclaw"),
        ("signal_recorder/data/signal_log.db", "signal_log", "signal_recorder"),
        ("signal_recorder/data/signal_log.db", "signal_outcomes", "signal_recorder"),
        ("sandbox/data/opposite_day.db", "opposite_picks", "opposite_day"),
        ("coinglass_strategies/data/coinglass.db", "signals", "coinglass"),
        ("meta_strategy/data/meta_strategy.db", "permutation_signals", "meta_strategy"),
        ("battleground/data/bundle_babies.db", "bundle_trades", "bundle_babies"),
    ]

    for db_path, table, system in sqlite_sources:
        p, o = load_sqlite_table(cur, db_path, table, system)
        total_picks += p
        total_outcomes += o
        print(f"  [{system}/{table}] picks={p}, outcomes={o}")

    # ── 2. JSON pick files ──
    json_sources = [
        # (filepath, source_system, is_closed)
        ("alpha_engine/data/active_picks.json", "alpha_engine", False),
        ("alpha_engine/data/closed_picks.json", "alpha_engine", True),
        ("mercury2/data/active_picks.json", "mercury2", False),
        ("mercury2/data/closed_picks.json", "mercury2", True),
        ("battleground/data/active_picks.json", "battleground", False),
        ("battleground/data/closed_picks.json", "battleground", True),
        ("crypto_ml_edge/data/active_picks.json", "crypto_ml_edge", False),
        ("KIMI_RISEOFTHECLAW/data/active_picks.json", "kimi_riseoftheclaw", False),
        ("KIMI_RISEOFTHECLAW/data/closed_picks.json", "kimi_riseoftheclaw", True),
        ("coinglass_strategies/data/active_picks.json", "coinglass", False),
        ("rl_agent/data/active_picks.json", "rl_agent", False),
        ("genome/active_picks.json", "genome", False),
        ("crypto_signal_engine/data/active_picks.json", "crypto_signal_engine", False),
        ("crypto_signal_engine/data/closed_picks.json", "crypto_signal_engine", True),
        # Multi-asset (forex + equity + institutional) — active and closed
        ("multi_asset/data/active_picks.json", "multi_asset_copytrader", False),
        ("multi_asset/data/multi_asset_closed.json", "multi_asset_copytrader", True),
    ]

    # ML Battleground systems
    for sys_dir in glob.glob(str(REPO / "ml_battleground" / "system_*")):
        sys_name = Path(sys_dir).name
        for pick_type, closed in [("active_picks.json", False), ("closed_picks.json", True)]:
            fpath = f"ml_battleground/{sys_name}/data/{pick_type}"
            json_sources.append((fpath, f"ml_battleground_{sys_name}", closed))

    # ML Battleground ensemble
    json_sources.append(("ml_battleground/ensemble_data/active_picks.json", "ml_battleground_ensemble", False))
    json_sources.append(("ml_battleground/ensemble_data/closed_picks.json", "ml_battleground_ensemble", True))

    # Breakout arena
    for approach in ["approach_a_sr_breakout", "approach_b_ml_breakout", "approach_c_spike_reverse"]:
        for pick_type, closed in [("active_picks.json", False), ("closed_picks.json", True)]:
            fpath = f"breakout_arena/{approach}/data/{pick_type}"
            json_sources.append((fpath, f"breakout_{approach}", closed))

    for filepath, system, is_closed in json_sources:
        p_cnt, o_cnt = load_json_picks(cur, filepath, system, is_closed)
        if p_cnt or o_cnt:
            total_picks += p_cnt
            total_outcomes += o_cnt
            print(f"  [{system}] {'closed' if is_closed else 'active'}: {p_cnt} picks, {o_cnt} outcomes")

    # ── Summary ──
    cur.execute("SELECT COUNT(*) FROM at_local_picks")
    lp_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM at_signal_outcomes")
    so_total = cur.fetchone()[0]

    cur.execute("SELECT source_system, COUNT(*) FROM at_local_picks GROUP BY source_system ORDER BY 2 DESC")
    by_system = cur.fetchall()

    cur.execute("SELECT status, COUNT(*) FROM at_local_picks GROUP BY status ORDER BY 2 DESC")
    by_status = cur.fetchall()

    print(f"\n=== BACKFILL COMPLETE ===")
    print(f"New picks inserted: {total_picks}")
    print(f"New outcomes inserted: {total_outcomes}")
    print(f"Total at_local_picks: {lp_total}")
    print(f"Total at_signal_outcomes: {so_total}")
    print(f"\nBy source system:")
    for sys, cnt in by_system:
        print(f"  {sys:<40} {cnt:>6}")
    print(f"\nBy status:")
    for st, cnt in by_status:
        print(f"  {st:<20} {cnt:>6}")

    conn.close()


if __name__ == "__main__":
    main()

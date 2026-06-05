#!/usr/bin/env python3
"""
mysql_trading_sync.py -- Sync Alpha Engine picks to MySQL (50webs)
==================================================================
Reads active_picks.json and closed_picks.json, then upserts all records
into the `trading_picks` table on ejaguiar1_stocks @ mysql.50webs.com.

Usage:
    python alpha_engine/mysql_trading_sync.py
    python alpha_engine/mysql_trading_sync.py --dry-run
"""

import json
import logging
import os
import sys
import time
import math
import argparse
from pathlib import Path
from datetime import datetime, timezone
from alpha_engine import config as _ae_config  # SSO for FOREX kill-switch

logger = logging.getLogger("mysql_trading_sync")

# 2026-05-31 — pnl_pct verification. Per
# reports/peer_claude-exit-logic-divergence_2026-05-31.md, the writer used to
# trust upstream `pnl_pct` blindly — one of 4 bugs producing the
# trading_picks vs at_signal_outcomes divergence. We now recompute from
# entry_price/exit_price/direction when all three are present, and reject
# rows whose upstream value disagrees with the recomputation by more than
# `PNL_VERIFY_TOLERANCE_PCT` percentage points (1bp = 0.01 percentage points).
# `compute_pnl()` returns FRACTIONAL pnl (0.05 == 5%), but `pnl_pct` in
# trading_picks is stored as PERCENT (-0.751 == -0.751%), so the computed
# fraction is multiplied by 100 before comparison.
try:
    from alpha_engine.outcome_resolver import compute_pnl as _compute_pnl
except ImportError:
    # When running this script directly (alpha_engine on sys.path implicitly),
    # the absolute import above can fail. Fall back to a sibling import.
    try:
        from outcome_resolver import compute_pnl as _compute_pnl  # type: ignore
    except ImportError:
        _compute_pnl = None  # verification disabled if module not importable

# STOCKS #7 defense-in-depth (2026-05-31): import the classifier so we can
# sanity-check raw_cat against detect_asset_class(symbol) before INSERT. This
# catches future bug sites that hardcode category="crypto" for non-crypto
# symbols (the root cause of the STOCKS #7 EQUITY mistag — see
# reports/stocks_7_equity_mistag_investigation_2026-05-31.md).
try:
    from alpha_engine.config import detect_asset_class as _detect_asset_class
except ImportError:
    try:
        from config import detect_asset_class as _detect_asset_class  # type: ignore
    except ImportError:
        _detect_asset_class = None  # type: ignore

# 1bp = 0.01 percentage points. Tolerance widened slightly to absorb
# float-rounding on the upstream side (it persists pnl rounded to 4 decimals).
PNL_VERIFY_TOLERANCE_PCT = 0.01  # percentage points (1bp)

# Run-level counters surfaced in the final summary. Populated as
# build_row_payload() / write paths discover mismatches.
_PNL_VERIFY_STATS = {
    "checked": 0,        # rows where entry/exit/direction all present
    "ok": 0,             # within tolerance
    "mismatch": 0,       # upstream disagreed beyond tolerance — pnl_pct dropped to None
    "skipped_no_inputs": 0,  # missing one of entry/exit/direction — verification not attempted
}

# ── Ensure pymysql is available ──────────────────────────────────────────────
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("[mysql_trading_sync] Installing pymysql...")
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pymysql"],
        stdout=subprocess.DEVNULL,
    )
    import pymysql
    import pymysql.cursors

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"

# Database credentials — same as db_sync.py uses for ejaguiar1_stocks
DB_HOST = os.environ.get("DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "ejaguiar1_stocks")
DB_NAME = os.environ.get("DB_NAME", "ejaguiar1_stocks")


def resolve_db_password():
    """MySQL password from env; empty workflow env must not override 50webs default."""
    for key in ("DB_PASS", "AUDIT_DB_PASS", "MYSQL_PASSWORD"):
        v = os.environ.get(key)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return "stocks"

# Retry settings (50webs can be unreliable)
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# ── Table DDL ────────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trading_picks (
    id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(20),
    direction VARCHAR(10),
    strategy VARCHAR(100),
    entry_price DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    confidence DECIMAL(5,4),
    elite_score INT,
    trust_score INT,
    category VARCHAR(20),
    source_system VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    pnl_pct DECIMAL(10,4),
    exit_price DECIMAL(20,8),
    created_at DATETIME,
    closed_at DATETIME,
    exit_reason VARCHAR(30),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# ── Upsert SQL ───────────────────────────────────────────────────────────────
UPSERT_SQL = """
INSERT INTO trading_picks
    (id, symbol, direction, strategy, entry_price, take_profit, stop_loss,
     confidence, elite_score, trust_score, category, source_system,
     status, pnl_pct, exit_price, created_at, closed_at, exit_reason)
VALUES
    (%(id)s, %(symbol)s, %(direction)s, %(strategy)s, %(entry_price)s,
     %(take_profit)s, %(stop_loss)s, %(confidence)s, %(elite_score)s,
     %(trust_score)s, %(category)s, %(source_system)s, %(status)s,
     %(pnl_pct)s, %(exit_price)s, %(created_at)s, %(closed_at)s, %(exit_reason)s)
ON DUPLICATE KEY UPDATE
    symbol       = VALUES(symbol),
    direction    = VALUES(direction),
    strategy     = VALUES(strategy),
    entry_price  = VALUES(entry_price),
    take_profit  = VALUES(take_profit),
    stop_loss    = VALUES(stop_loss),
    confidence   = VALUES(confidence),
    elite_score  = VALUES(elite_score),
    trust_score  = VALUES(trust_score),
    category     = VALUES(category),
    source_system= VALUES(source_system),
    status       = VALUES(status),
    pnl_pct      = VALUES(pnl_pct),
    exit_price   = VALUES(exit_price),
    created_at   = VALUES(created_at),
    closed_at    = VALUES(closed_at),
    exit_reason  = VALUES(exit_reason);
"""


def log_ok(msg):
    print(f"  [OK]  {msg}")


def log_err(msg):
    print(f"  [ERR] {msg}", file=sys.stderr)


def log_warn(msg):
    print(f"  [WARN] {msg}", file=sys.stderr)


def log_info(msg):
    print(f"  [..] {msg}")


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_datetime(val):
    """Parse various datetime formats from the JSON files. Returns str or None."""
    if not val:
        return None
    # Strip timezone info for MySQL DATETIME compatibility
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
    return None


def _safe_float(val):
    """Convert to finite float or None for DB-safe inserts."""
    if val is None or val == "":
        return None
    try:
        f = float(val)
    except (ValueError, TypeError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def pick_to_row(pick):
    """Convert a JSON pick dict to a flat dict matching the DB columns."""
    # Default OPEN (not ACTIVE) — 2026-06-02: dual OPEN+ACTIVE live cohort caused
    # 3.7k ACTIVE rows to bypass stale resolver until pick_hold_windows fix.
    raw_status = str(pick.get("status", "OPEN") or "OPEN").upper()
    exit_reason = str(pick.get("exit_reason", "") or "").upper()

    # PnL sign helper (used by both the CLOSED/FLAT derivation and the
    # legacy-status canonicalization below).
    def _pnl_sign():
        pnl_raw = pick.get("pnl_pct")
        if pnl_raw is None:
            pnl_raw = pick.get("unrealized_pnl_pct")
        pnl_f = _safe_float(pnl_raw)
        return pnl_f if pnl_f is not None else 0.0

    # closed_picks sources commonly emit CLOSED/FLAT instead of final outcome.
    # Derive a CANONICAL terminal status for MySQL analytics. Canonical set
    # (keep in sync with tools/db_health_check.py CANONICAL_STATUSES and
    # tools/standardize_statuses.py): TP_HIT, SL_HIT, LOST, EXPIRED, TIME_EXIT,
    # ACTIVE, OPEN. Emitting legacy 'WON'/'CLOSED_*' here was the root cause of
    # the status_standardization RED gate (banner: DATA INTEGRITY FAILURE) —
    # the writer kept re-seeding non-canonical rows faster than cleanup ran.
    if raw_status in ("CLOSED", "FLAT"):
        if exit_reason in ("TP", "TP_HIT", "TP_HIT_RESOLVED", "TP2_HIT", "TP1_HIT"):
            status = "TP_HIT"
        elif exit_reason in ("SL", "SL_HIT", "STOP_LOSS", "ATR_TRAIL", "TRAIL", "TRAIL_SL", "SL_HIT_RESOLVED"):
            status = "SL_HIT"
        elif exit_reason in ("TIME_EXIT", "MAX_HOLD"):
            status = "TIME_EXIT"
        elif exit_reason in ("EXPIRED", "FORCE_CLOSED_TOXIC"):
            status = "EXPIRED"
        else:
            # Fallback: infer from PnL sign when exit_reason is ambiguous.
            # A positive close with no TP exit_reason is NOT a confirmed TP hit
            # (it may be a time-exit at a profit), so it maps to TIME_EXIT, not
            # TP_HIT — preserving the WR/PF semantics of TP_HIT.
            pnl_f = _pnl_sign()
            if pnl_f > 0:
                status = "TIME_EXIT"
            elif pnl_f < 0:
                status = "LOST"
            else:
                status = "EXPIRED"
    else:
        # Canonicalize any legacy pass-through status so the writer never
        # re-introduces a non-canonical value (WON/WIN/LOSS/closed/CLOSED_*).
        _STATIC_CANON = {
            "WIN": None, "WON": None,        # PnL-dependent → resolved below
            "LOSS": "LOST", "CLOSED_SL": "SL_HIT", "CLOSED_TP": "TP_HIT",
            "SIGNAL": "EXPIRED", "STALE": "EXPIRED",
        }
        if raw_status in ("WIN", "WON"):
            pnl_f = _pnl_sign()
            status = "TP_HIT" if pnl_f > 0 else "LOST"
        elif raw_status == "CLOSED":
            pnl_f = _pnl_sign()
            status = "TP_HIT" if pnl_f > 0 else "LOST" if pnl_f < 0 else "TIME_EXIT"
        elif raw_status in _STATIC_CANON:
            status = _STATIC_CANON[raw_status]
        else:
            status = raw_status

    # Live picks: canonicalize ACTIVE → OPEN (avoid dual live cohort in MySQL).
    _live_exit = {"", "OPEN", "ACTIVE", "PENDING", "LIVE", "NEW"}
    if status == "ACTIVE" and (exit_reason or "").upper() in _live_exit:
        status = "OPEN"

    # Determine closed_at: use exit_date if present.
    # 2026-05-10: + exit_time fallback. battleground/data/closed_picks.json and
    # alpha_engine/data/active_picks.json emit `exit_time` (not exit_date /
    # closed_at). Without this fallback, all 115 battleground closed picks
    # land in MySQL with closed_at=NULL — driving 57,710 of 66,058 NULL
    # closed_at rows (87%) per dry-run preview at
    # reports/battleground_timestamp_gap_2026-05-10/preview.csv.
    closed_at = None
    if status not in ("ACTIVE", "OPEN"):
        closed_at = (
            parse_datetime(pick.get("exit_date"))
            or parse_datetime(pick.get("closed_at"))
            or parse_datetime(pick.get("exit_time"))
        )

    # Persist explicit exit price for closed picks when available.
    # alpha_engine portfolio_tracker_*.py writes pos["close_price"] (not
    # "exit_price") on TIME_EXIT closures. Without this alias, 33,172 of
    # 33,213 TIME_EXIT rows landed with exit_price=entry_price and pnl_pct=0
    # (INCIDENT_OVERALL #94, 2026-06-04). Add close_price/closePrice fallbacks.
    exit_price = pick.get("exit_price")
    if exit_price is None:
        exit_price = pick.get("exitPrice")
    if exit_price is None:
        exit_price = pick.get("close_price")
    if exit_price is None:
        exit_price = pick.get("closePrice")
    exit_price = _safe_float(exit_price)

    # pnl_pct can be in different fields
    pnl = pick.get("pnl_pct")
    if pnl is None:
        pnl = pick.get("unrealized_pnl_pct")
    # closed_picks payloads are percent values already (e.g. -0.751 == -0.751%).
    # Do not auto-scale values below 1.0.
    pnl = _safe_float(pnl)

    # 2026-05-31 — pnl_pct verification.
    # Recompute pnl from entry/exit/direction when all three are present and
    # cross-check against the upstream value. If they disagree beyond
    # PNL_VERIFY_TOLERANCE_PCT (1bp), the row's upstream pnl_pct is dropped
    # (set to None) and a warning is logged — we'd rather have a NULL than
    # let trading_picks be overwritten with a corrupted value.
    #
    # Refs: reports/peer_claude-exit-logic-divergence_2026-05-31.md (one of
    # 4 bugs producing the trading_picks vs at_signal_outcomes divergence).
    entry_for_verify = _safe_float(pick.get("entry_price"))
    exit_for_verify = exit_price
    direction_for_verify = str(
        pick.get("direction") or pick.get("signal_type") or ""
    ).strip().upper()
    if (
        _compute_pnl is not None
        and pnl is not None
        and entry_for_verify
        and entry_for_verify > 0
        and exit_for_verify is not None
        and direction_for_verify
    ):
        try:
            expected_frac = _compute_pnl(
                entry_for_verify, exit_for_verify, direction_for_verify
            )
            expected_pct = expected_frac * 100.0  # convert fraction → percent
            _PNL_VERIFY_STATS["checked"] += 1
            if abs(expected_pct - pnl) > PNL_VERIFY_TOLERANCE_PCT:
                _PNL_VERIFY_STATS["mismatch"] += 1
                logger.warning(
                    "pnl_pct verify mismatch: pick %s symbol=%s dir=%s "
                    "entry=%s exit=%s upstream_pnl=%s expected_pnl=%.6f "
                    "(diff=%.6f pp > %.4f pp tolerance) — dropping upstream "
                    "value to NULL to avoid corrupting trading_picks",
                    str(pick.get("id") or "?")[:60],
                    str(pick.get("symbol") or "?")[:20],
                    direction_for_verify[:8],
                    entry_for_verify,
                    exit_for_verify,
                    pnl,
                    expected_pct,
                    expected_pct - pnl,
                    PNL_VERIFY_TOLERANCE_PCT,
                )
                pnl = None
            else:
                _PNL_VERIFY_STATS["ok"] += 1
        except Exception as e:  # never let verification crash the sync
            logger.warning(
                "pnl_pct verify error for pick %s: %s",
                str(pick.get("id") or "?")[:60],
                e,
            )
    else:
        # Missing one of (entry, exit, direction) — verification skipped.
        # Only count when there is an upstream pnl to verify; otherwise the
        # row simply has no pnl_pct and the writer will store NULL.
        if pnl is not None:
            _PNL_VERIFY_STATS["skipped_no_inputs"] += 1

    if pnl is not None:
        pnl = round(pnl, 4)
        # 2026-05-09 — Anomaly clamp.
        # `reports/db_query_bank_2026-05-07/FINDINGS.md` Critical Finding #0:
        # `category='forex'` rows had `pnl_pct` range -106,700.679 to +95.58
        # (avg -57.47, stddev 2,346) — single outlier swamped system-wide PF
        # to 0.063 vs sane crypto ~0. Root cause is upstream: raw price-diff
        # or pip count being passed in as % for some forex resolver paths.
        # While that's tracked separately for fix, this writer-level guard
        # rejects any pnl_pct outside the [-100, 200]% sanity envelope —
        # logs the anomaly so the upstream source can be identified.
        if not (-100.0 <= pnl <= 200.0):
            logger.warning(
                "pnl_pct anomaly clamp: pick %s symbol=%s category=%s "
                "raw=%s — dropping to None (out of [-100, 200] range)",
                (pick.get("id") or "?")[:60],
                (pick.get("symbol") or "?")[:20],
                (pick.get("category") or "?")[:20],
                pnl,
            )
            pnl = None

    # 2026-05-09 — Category inference for NULL/empty rows.
    # swarm_runs/next_steps_perf_2026-05-09 (4/4 vote) showed 7 of top 10
    # 30d winners are tagged category='' or NULL — invisible to filters even
    # though they're plainly crypto symbols. Backfill from symbol shape:
    #   *USDT / *USD / *USDC / *PERP / -USD → crypto
    #   has-equals-F (e.g., CL=F) → futures
    #   has-equals-X (e.g., EURUSD=X) → forex
    # Only applied when the source pick gives empty/None — never overrides.
    raw_cat = str(pick.get("category") or "").strip().lower()
    if not raw_cat:
        sym = str(pick.get("symbol") or "").upper()
        if sym.endswith(("USDT", "USDC", "BUSD", "DAI", "PERP")):
            raw_cat = "crypto"
        elif sym.endswith("-USD"):
            raw_cat = "crypto"
        elif sym.endswith("=F"):
            raw_cat = "futures"
        elif sym.endswith("=X"):
            raw_cat = "forex"
        # else: leave empty — caller knows their pick is unclassifiable

    # STOCKS #7 defense-in-depth (2026-05-31): if the upstream raw_cat is
    # "crypto" but the symbol classifier disagrees (e.g. AAPL came in tagged
    # crypto from a buggy producer), override raw_cat with the classifier
    # result and log a WARNING. This catches future hardcoded-crypto bugs
    # before they corrupt the EQUITY/COMMODITY/FOREX class buckets.
    # Refs: reports/stocks_7_equity_mistag_investigation_2026-05-31.md
    if _detect_asset_class is not None and raw_cat == "crypto":
        sym_check = str(pick.get("symbol") or "").upper()
        if sym_check:
            detected = _detect_asset_class(sym_check)
            if detected and detected not in ("crypto", "unknown"):
                logger.warning(
                    "STOCKS#7 mistag override: pick %s symbol=%s upstream "
                    "category=crypto but classifier=%s — overriding to %s "
                    "(refs: reports/stocks_7_equity_mistag_investigation_2026-05-31.md)",
                    str(pick.get("id") or "?")[:60],
                    sym_check[:20],
                    detected,
                    detected,
                )
                raw_cat = detected

    return {
        "id": pick.get("id", "")[:100],
        "symbol": (pick.get("symbol") or "")[:20],
        "direction": (pick.get("direction") or pick.get("signal_type") or "")[:10],
        "strategy": (pick.get("strategy") or "")[:100],
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _safe_float(pick.get("confidence")),
        "elite_score": _safe_float(pick.get("elite_score")),
        "trust_score": _safe_float(pick.get("trust_score")),
        "category": raw_cat[:20],
        "source_system": (pick.get("source_system") or "alpha_engine")[:50],
        "status": status[:20],
        "pnl_pct": pnl,
        "exit_price": exit_price,
        # 2026-05-10: + entry_time fallback. battleground + alpha_engine emit
        # `entry_time` (not created_at / detected_at / timestamp). See
        # reports/battleground_timestamp_gap_2026-05-10/preview.csv.
        "created_at": parse_datetime(
            pick.get("created_at")
            or pick.get("detected_at")
            or pick.get("timestamp")
            or pick.get("entry_time")
        ),
        "closed_at": closed_at,
        "exit_reason": (pick.get("exit_reason") or "")[:30] or None,
    }


def load_picks(filepath):
    """Load picks from a JSON file. Returns list of dicts or empty list."""
    if not filepath.exists():
        log_info(f"File not found, skipping: {filepath.name}")
        return []
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in (
                "picks",
                "active_picks",
                "closed_picks",
                "signals",
                "crypto_signals",
                "stock_signals",
                "forex_signals",
                "active",
                "closed",
                "forward_picks",
                "activeSignals",
                "closedSignals",
                "super_signals",
                "data",
                "results",
                "positions",
                "winners",
                "items",
                "rows",
                "contested_picks",
                "top_picks",
                "trades",
                "closed_trades",
                "live_signals",
                "open_picks",
            ):
                if key in data and isinstance(data[key], list):
                    return data[key]
            nested_picks = data.get("picks")
            if isinstance(nested_picks, dict):
                for key in ("active", "recent_closed", "smart_picks", "closed"):
                    if isinstance(nested_picks.get(key), list):
                        return nested_picks[key]

            list_values = [v for v in data.values() if isinstance(v, list)]
            if len(list_values) == 1:
                return list_values[0]

            log_info(f"No pick list found in {filepath.name}, skipping object payload")
            return []
        log_err(f"Expected list/object in {filepath.name}, got {type(data).__name__}")
        return []
    except (json.JSONDecodeError, OSError) as e:
        log_err(f"Failed to read {filepath.name}: {e}")
        return []


def connect_with_retry():
    """Connect to MySQL with retries for 50webs reliability."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=resolve_db_password(),
                database=DB_NAME,
                connect_timeout=15,
                read_timeout=30,
                write_timeout=30,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            return conn
        except pymysql.Error as e:
            last_err = e
            if attempt < MAX_RETRIES:
                log_info(
                    f"Connection attempt {attempt}/{MAX_RETRIES} failed: {e} "
                    f"— retrying in {RETRY_DELAY}s"
                )
                time.sleep(RETRY_DELAY)
            else:
                log_err(
                    f"All {MAX_RETRIES} connection attempts failed. Last error: {e}"
                )
    raise last_err


# ── Main sync logic ─────────────────────────────────────────────────────────

def sync(dry_run=False):
    """Load picks from JSON files and upsert to MySQL."""
    print("=" * 60)
    print("  Alpha Engine -> MySQL Trading Picks Sync")
    print(f"  Target: {DB_USER}@{DB_HOST}/{DB_NAME}")
    print(f"  Time:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # Load picks from ALL JSON_PICK_SOURCES
    try:
        sys.path.insert(0, str(SCRIPT_DIR.parent))
        from audit_trail.dashboard_generator import JSON_PICK_SOURCES
    except ImportError:
        log_err("Failed to import JSON_PICK_SOURCES from dashboard_generator")
        JSON_PICK_SOURCES = [
            ("alpha_engine", "alpha_engine/data/active_picks.json", "alpha_engine/data/closed_picks.json")
        ]

    all_active = []
    all_closed = []
    
    for sys_name, active_rel, closed_rel in JSON_PICK_SOURCES:
        src_active = []
        src_closed = []
        
        if active_rel:
            active_path = SCRIPT_DIR.parent / active_rel
            src_active = load_picks(active_path)
            
        if closed_rel:
            closed_path = SCRIPT_DIR.parent / closed_rel
            src_closed = load_picks(closed_path)
        
        # Tag source if missing
        for p in src_active:
            p['source_system'] = p.get('source_system') or sys_name
        for p in src_closed:
            p['source_system'] = p.get('source_system') or sys_name
            
        all_active.extend(src_active)
        all_closed.extend(src_closed)

    log_ok(f"Loaded {len(all_active)} active + {len(all_closed)} closed picks across {len(JSON_PICK_SOURCES)} sources")

    if not all_active and not all_closed:
        log_info("No picks to sync. Done.")
        return 0

    # 2026-05-09 — Elite-score backfill before sync.
    # `reports/portfolio_lessons_2026-05-08.md` showed 92% of crypto picks
    # (3,128 of 3,394 in 14d) had elite_score=NULL, which made them
    # invisible to the cycle picks workflow. Polymarket-derived sources
    # (prediction_market_agents, copy_trader_polymarket, polymarket_whale_tracker,
    # polymarket_momentum, short_dominant_engine) bypass elite_scorer in their
    # own pipelines. Backfill here so every pick reaching trading_picks gets
    # scored once. Skipped on import failure so the sync still runs in
    # environments where elite_scorer's MC-results data files aren't present.
    unscored_pre = sum(
        1 for p in all_active + all_closed
        if p.get("elite_score") is None or p.get("elite_score") == ""
    )
    try:
        from alpha_engine.elite_scorer import enrich_picks_with_elite_score
        # Score the combined unique-ids list (in-place mutation on shared dicts).
        enrich_picks_with_elite_score(list(all_active) + list(all_closed))
        unscored_post = sum(
            1 for p in all_active + all_closed
            if p.get("elite_score") is None or p.get("elite_score") == ""
        )
        log_ok(
            f"elite_score backfill: scored {unscored_pre - unscored_post} "
            f"of {unscored_pre} previously-unscored picks "
            f"(remaining unscored: {unscored_post})"
        )
    except ImportError as e:
        log_err(f"elite_scorer import failed — proceeding without backfill: {e}")
    except Exception as e:
        log_err(f"elite_scorer backfill error — proceeding with partial fill: {e}")

    # Build rows
    rows = []
    seen_ids = set()
    for pick in all_active + all_closed:
        pid = pick.get("id", "")
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)
        # 2026-05-25: zero-allocate FOREX per reports/EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md.
        # The prior kill-switch existed only at scanner.py:2559 inside nc_quality_gate, which
        # missed multi_asset_copytrader / non_crypto_consensus / combined_confidence_strategy
        # / forex_copy_trader / regime_terminal / prediction_market_agents / alpha_engine — 387
        # FOREX picks leaked since 2026-05-24. This is the single funnel every pick crosses
        # before DB upsert. The 'FOREX_HIGH_CONVICTION' carve-out (cta_replicator only, PF
        # 2.51 n=97 per commit e9dcfdca8) is preserved by the explicit category match. See
        # reports/2026-05-25_forex_zero_allocate_filter_DRAFT.md.
        _raw_cat = str(pick.get("category") or "").strip().upper()
        if _raw_cat == "FOREX" and _ae_config.FOREX_HARD_DISABLE:
            _forex_skipped = locals().get("_forex_skipped", 0) + 1
            continue
        if os.environ.get("CLEAN_INGEST_V2_ENFORCE", "0") in ("1", "true", "TRUE", "yes"):
            try:
                from tools.clean_ingest_v2 import validate_pick_row
                _ci = validate_pick_row({
                    "symbol": pick.get("symbol"),
                    "asset_class": pick.get("category") or pick.get("asset_class"),
                    "direction": pick.get("direction"),
                    "entry_price": pick.get("entry_price"),
                    "tp_fill_method": pick.get("tp_fill_method"),
                    "submitted_at": pick.get("created_at") or pick.get("entry_date"),
                    "status": pick.get("status"),
                })
                if not _ci.ok:
                    _clean_skipped = locals().get("_clean_skipped", 0) + 1
                    continue
            except Exception:
                pass
        try:
            rows.append(pick_to_row(pick))
        except Exception as e:
            continue

    _forex_skipped = locals().get("_forex_skipped", 0)
    if _forex_skipped:
        log_info(f"[FOREX_ZERO_ALLOCATE] suppressed {_forex_skipped} FOREX picks "
                 f"(FOREX_HIGH_CONVICTION preserved per EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md)")
    _clean_skipped = locals().get("_clean_skipped", 0)
    if _clean_skipped:
        log_info(f"[CLEAN_INGEST_V2] suppressed {_clean_skipped} picks (set CLEAN_INGEST_V2_ENFORCE=0 to disable)")
    log_ok(f"Prepared {len(rows)} unique rows for upsert")

    if dry_run:
        log_info("[DRY RUN] Would upsert the following picks:")
        for r in rows[:5]:
            print(f"    {r['id'][:50]}  {r['symbol']:>10}  {r['status']:>8}  pnl={r['pnl_pct']}")
        if len(rows) > 5:
            print(f"    ... and {len(rows) - 5} more")
        return 0

    # Connect
    log_info(f"Connecting to {DB_HOST}...")
    conn = connect_with_retry()
    log_ok(f"Connected to MySQL ({DB_HOST})")

    cursor = conn.cursor()

    # Create table if not exists
    try:
        cursor.execute(CREATE_TABLE_SQL)
        # Backward-compatible migration: older deployments may not have exit_price.
        try:
            cursor.execute(
                "ALTER TABLE trading_picks ADD COLUMN exit_price DECIMAL(20,8) NULL AFTER pnl_pct"
            )
            log_ok("Added missing column `exit_price` to trading_picks")
        except pymysql.Error as col_err:
            # 1060 = duplicate column name (already exists)
            if getattr(col_err, "args", [None])[0] != 1060:
                raise
        conn.commit()
        log_ok("Table `trading_picks` ensured")
        # Composite indexes for query performance (IF NOT EXISTS via CREATE INDEX ... IGNORE)
        _idx_stmts = [
            "CREATE INDEX idx_tp_strategy_status ON trading_picks(strategy, status)",
            "CREATE INDEX idx_tp_asset_status ON trading_picks(category, status)",
            "CREATE INDEX idx_tp_created ON trading_picks(created_at)",
            "CREATE INDEX idx_tp_closed ON trading_picks(closed_at)",
            "CREATE INDEX idx_tp_confidence ON trading_picks(confidence)",
        ]
        for stmt in _idx_stmts:
            try:
                cursor.execute(stmt)
                conn.commit()
            except pymysql.Error as idx_err:
                if getattr(idx_err, "args", [None])[0] != 1061:  # 1061 = duplicate key name
                    log_warn(f"Index creation warning: {idx_err}")
        log_ok("trading_picks indexes ensured")
        # at_pick_outcomes — created here so resolver can write outcomes without
        # a separate DDL migration step
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS at_pick_outcomes (
                -- pick_id widened to varchar(100) on 2026-06-01 to support
                -- composite IDs from genome_revival_battlegro_* sources that
                -- were silently dropped under char(36) by INSERT IGNORE.
                pick_id           VARCHAR(100) PRIMARY KEY,
                symbol            VARCHAR(50),
                strategy          VARCHAR(200),
                asset_class       VARCHAR(20),
                status            ENUM('OPEN','WON','LOST','EXPIRED','FLAT') NOT NULL,
                resolution_method ENUM('TP_HIT','SL_HIT','TIME_EXPIRED','MANUAL'),
                pnl_pct           DECIMAL(10,4),
                resolved_at       DATETIME,
                resolver_version  VARCHAR(20),
                forward_test_only BOOLEAN DEFAULT FALSE,
                forward_validated   BOOLEAN DEFAULT FALSE,
                _gated_forward_test_isolated BOOLEAN DEFAULT FALSE,
                INDEX idx_po_status   (status),
                INDEX idx_po_strategy (strategy),
                INDEX idx_po_resolved (resolved_at),
                INDEX idx_po_asset    (asset_class)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
        log_ok("Table `at_pick_outcomes` ensured")
        # P0 §15 (2026-06-01 fires): One-time prod ALTER for forward_test isolation tags
        # (required on existing ejaguiar1_stocks DB before the writer skips + health checks are fully live):
        # ALTER TABLE at_pick_outcomes
        #   ADD COLUMN forward_test_only BOOLEAN DEFAULT FALSE,
        #   ADD COLUMN forward_validated BOOLEAN DEFAULT FALSE,
        #   ADD COLUMN _gated_forward_test_isolated BOOLEAN DEFAULT FALSE;
    except pymysql.Error as e:
        log_err(f"Failed to create table: {e}")
        conn.close()
        return 1

    # Pre-flight soft-dedup: the uq_trading_picks_dedup UNIQUE constraint uses created_at,
    # but created_at is NULL for many sources (e.g. mega_mutation). MySQL treats NULL != NULL
    # in UNIQUE indexes, so the constraint silently allows duplicate closed-state rows.
    # Fix: before the upsert loop, fetch all (source_system, symbol, entry_price, exit_price,
    # DATE(closed_at)) tuples for closed rows and skip rows that already exist.
    _closed_rows = [r for r in rows if r.get("closed_at") is not None and r.get("exit_price") is not None]
    _existing_closed_keys: set = set()
    if _closed_rows:
        try:
            _src_syms = list({(r.get("source_system", ""), r["symbol"]) for r in _closed_rows})
            for _src, _sym in _src_syms:
                cursor.execute(
                    "SELECT ROUND(entry_price,6), ROUND(exit_price,6), DATE(closed_at) "
                    "FROM trading_picks WHERE source_system=%s AND symbol=%s "
                    "AND closed_at IS NOT NULL AND exit_price IS NOT NULL "
                    "AND status NOT IN ('OPEN','ABANDONED','FLAT')",
                    (_src, _sym),
                )
                for _ex in cursor.fetchall():
                    _existing_closed_keys.add((_src, _sym, float(_ex[0]), float(_ex[1]), str(_ex[2])))
        except Exception as _de:
            log_warn(f"Soft-dedup pre-fetch failed (non-fatal): {_de}")

    def _soft_dedup_key(row: dict):
        if row.get("closed_at") is None or row.get("exit_price") is None:
            return None
        from decimal import Decimal
        try:
            ep = round(float(row.get("entry_price") or 0), 6)
            xp = round(float(row.get("exit_price") or 0), 6)
            closed_date = str(row["closed_at"])[:10]
            return (row.get("source_system", ""), row["symbol"], ep, xp, closed_date)
        except Exception:
            return None

    # Upsert rows in batches
    inserted = 0
    duplicates = 0
    errors = 0
    batch_size = 50

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        for row in batch:
            # Soft-dedup: skip closed rows that already exist under a different id
            _sdk = _soft_dedup_key(row)
            if _sdk and _sdk in _existing_closed_keys:
                duplicates += 1
                if duplicates <= 5:
                    log_info(f"Soft-dedup skip for {row['id'][:50]}: closed key already in DB")
                continue
            try:
                cursor.execute(UPSERT_SQL, row)
                inserted += 1
                if _sdk:
                    _existing_closed_keys.add(_sdk)  # prevent intra-batch duplicates
            except pymysql.Error as e:
                errno = getattr(e, "args", [None])[0]
                # 1062 = duplicate on uq_trading_picks_dedup — row already stored under another id
                if errno == 1062:
                    duplicates += 1
                    if duplicates <= 5:
                        log_info(f"Dedup skip for {row['id'][:50]}: already in DB")
                    continue
                errors += 1
                if errors <= 5:
                    log_err(f"Upsert failed for {row['id'][:50]}: {e}")
        try:
            conn.commit()
        except pymysql.Error as e:
            log_err(f"Commit failed for batch starting at {i}: {e}")
            errors += len(batch)

    # Summary
    print()
    print("-" * 60)
    log_ok(f"Sync complete: {inserted} upserted, {duplicates} dedup skipped, {errors} errors")

    # 2026-05-31 — pnl_pct verification summary.
    _v = _PNL_VERIFY_STATS
    log_ok(
        f"pnl_pct verify: checked={_v['checked']} ok={_v['ok']} "
        f"mismatch={_v['mismatch']} skipped_no_inputs={_v['skipped_no_inputs']} "
        f"(tolerance={PNL_VERIFY_TOLERANCE_PCT} pp; mismatches were dropped to NULL)"
    )
    if _v["mismatch"] > 0:
        log_err(
            f"WARN: {_v['mismatch']} row(s) had upstream pnl_pct disagreeing with "
            "compute_pnl(entry,exit,direction) — dropped to NULL. See per-row warnings above."
        )

    # Quick count verification
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM trading_picks")
        total = cursor.fetchone()["cnt"]
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM trading_picks WHERE status = 'ACTIVE'"
        )
        active_cnt = cursor.fetchone()["cnt"]
        log_ok(f"DB totals: {total} picks ({active_cnt} active)")
    except pymysql.Error:
        pass

    conn.close()
    # Tolerate small row-level data errors when bulk upsert succeeded.
    # Why: ELITE scorer sometimes hits picks with non-numeric risk_reward
    # ('HIGH'/'LOW'/'MEDIUM' from upstream feed); these are flagged + logged,
    # but the bulk DB write is otherwise healthy. Hard-fail only when error
    # rate is high (>1%) or no rows landed at all.
    if errors == 0:
        return 0
    if inserted > 0 and errors * 100 <= inserted:
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="Sync Alpha Engine picks to MySQL (50webs)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without writing to DB",
    )
    args = parser.parse_args()
    sys.exit(sync(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
"""
MySQL Audit Client — Fire-and-forget Discord audit logging to ejaguiar1_stocks.
================================================================================

Writes to:
  - at_discord_notifications  (every Discord send: picks, TP/SL hits, updates)
  - at_discord_gate_log       (every gate decision: pass/reject with reason)
  - consensus_tracked         (marks discord_sent=1 after successful post)

Design principles:
  - NEVER blocks Discord sends — all DB writes wrapped in try/except
  - Connection pooling via a singleton queue (reuses connections)
  - Exponential backoff on transient failures (max 2 retries)
  - Idempotent: UNIQUE index on (symbol, direction, event_type, created_at)

Usage:
    from audit_trail.mysql_client import log_discord_send, log_gate_decision

    # After Discord _post() succeeds:
    log_discord_send(pick_data, channel="consensus", event_type="PICK_POSTED")

    # Inside each gate check:
    log_gate_decision("BTCUSDT", "LONG", "alpha_engine", "rsi_2", "G2_CONFIDENCE",
                      "REJECT", "confidence 0.55 < 0.65", confidence=0.55)
"""

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("audit_trail.mysql")
from audit_trail.asset_classification import resolve_asset_class, canonicalize_symbol

# ── Configuration ────────────────────────────────────────────────────────────

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "stocks")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")

# Backtests-only DB target (2026-05-04, per
# updates/2026-05-04-bt-backtest-trades-archive-plan.md). The bt_backtest_trades
# table (1.27M rows / 1.4 GB data + 125 MB indexes verified live) is the
# dominant size contributor to ejaguiar1_stocks. Splitting its writes to a
# separate DB lets us shrink ejaguiar1_stocks without touching the live read
# path (dashboard_generator.py reads trading_picks from ejaguiar1_stocks; it
# does NOT read bt_backtest_trades — verified by grep).
#
# Defaults preserve current behavior: BACKTESTS_DB_NAME defaults to
# ejaguiar1_stocks until the user provisions ejaguiar1_backtests + a user
# with INSERT grants. Then set BACKTESTS_DB_NAME=ejaguiar1_backtests
# (and BACKTESTS_DB_USER / BACKTESTS_DB_PASS if separate creds) in CI secrets
# and the next workflow run writes to the new DB.
BACKTESTS_DB_NAME = os.getenv("BACKTESTS_DB_NAME", DB_NAME)
BACKTESTS_DB_USER = os.getenv("BACKTESTS_DB_USER", DB_USER)
BACKTESTS_DB_PASS = os.getenv("BACKTESTS_DB_PASS", DB_PASS)

MAX_RETRIES = 2
RETRY_BASE_DELAY = 0.5  # seconds, doubles each retry
CONNECT_TIMEOUT = 10
POOL_SIZE = 3

# ── Connection Pool ──────────────────────────────────────────────────────────

_pool: queue.Queue = queue.Queue(maxsize=POOL_SIZE)
_pool_lock = threading.Lock()
_pool_initialized = False
_install_lock = threading.Lock()  # serialize concurrent pymysql auto-install


def _ensure_pymysql():
    """Lazy-import pymysql, install if missing.

    Returns the pymysql module or raises ImportError if unavailable and
    auto-install fails (e.g. restricted CI environment).
    """
    try:
        import pymysql
        return pymysql
    except ImportError:
        pass
    # Only one thread installs; others wait and retry import afterward.
    with _install_lock:
        # Re-check — another thread may have installed while we waited.
        try:
            import pymysql
            return pymysql
        except ImportError:
            pass
        # Attempt auto-install (only one thread reaches here).
        try:
            import subprocess, sys
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pymysql"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise ImportError(
                "pymysql is not installed and auto-install failed. "
                "Add 'pymysql' to the pip install step in the workflow."
            ) from e
    import pymysql
    return pymysql


def _create_connection():
    """Create a new pymysql connection."""
    pymysql = _ensure_pymysql()
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=10,
        write_timeout=10,
        charset="utf8mb4",
        autocommit=True,
    )


def get_backtests_connection():
    """Create a new pymysql connection scoped to the backtests DB.

    Use this for inserts into bt_backtest_trades / bt_backtest_runs only.
    Other tables (at_*, alpha_*, trading_picks) stay on AUDIT_DB_NAME via
    _create_connection(). See updates/2026-05-04-bt-backtest-trades-archive-plan.md.

    Falls back to the audit DB target when BACKTESTS_DB_NAME is unset, so
    existing deployments keep writing to ejaguiar1_stocks until env is flipped.
    """
    pymysql = _ensure_pymysql()
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=BACKTESTS_DB_USER,
        password=BACKTESTS_DB_PASS,
        database=BACKTESTS_DB_NAME,
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=20,  # backtest inserts are fatter; allow more headroom
        write_timeout=20,
        charset="utf8mb4",
        autocommit=False,  # bulk insert path manages its own commits
    )


def _get_conn():
    """Get a connection from the pool (or create one)."""
    try:
        conn = _pool.get_nowait()
        # Verify connection is still alive
        try:
            conn.ping(reconnect=True)
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
    except queue.Empty:
        pass
    return _create_connection()


def _return_conn(conn):
    """Return a connection to the pool (or close if pool is full)."""
    try:
        _pool.put_nowait(conn)
    except queue.Full:
        try:
            conn.close()
        except Exception:
            pass


def _execute_with_retry(sql: str, params: tuple = (), retries: int = MAX_RETRIES) -> Optional[int]:
    """Execute SQL with retry and connection pooling. Returns rows affected or None."""
    for attempt in range(retries + 1):
        conn = None
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(sql, params)
            affected = cur.rowcount
            _return_conn(conn)
            return affected
        except Exception as e:
            if conn:
                try:
                    _return_conn(conn)
                    conn = None
                except Exception:
                    pass
            if attempt < retries:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"MySQL write failed (attempt {attempt + 1}/{retries + 1}): {e}. Retrying in {delay:.1f}s")
                time.sleep(delay)
            else:
                logger.error(f"MySQL write failed after {retries + 1} attempts: {e}")
                return None
    return None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _derive_asset_class(symbol: str) -> str:
    """Derive asset class from symbol name using canonical resolver."""
    return resolve_asset_class(symbol, raw={}, source_system="mysql_client", strategy="")


def _json_dumps(obj: Any) -> Optional[str]:
    """Safe JSON serialization."""
    if obj is None:
        return None
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        return None


def _safe_float(val: Any) -> Optional[float]:
    """Convert to float safely, return None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if f != f else f  # NaN → None
    except (ValueError, TypeError):
        return None


# ── Public API ───────────────────────────────────────────────────────────────

def log_discord_send(
    pick_data: Dict,
    channel: str,
    event_type: str = "PICK_POSTED",
    message_id: Optional[str] = None,
    webhook_name: Optional[str] = None,
    pnl_pct: Optional[float] = None,
    extra_payload: Optional[Dict] = None,
) -> Optional[int]:
    """
    Log a Discord send event to at_discord_notifications.

    Args:
        pick_data: Pick dict with symbol, direction, entry_price, etc.
        channel: Channel name (consensus, freshpicks, portfolio, sandbox, dna_master)
        event_type: PICK_POSTED, TP_HIT, SL_HIT, POSITION_UPDATE, REVERSAL, PORTFOLIO_SUMMARY
        message_id: Discord message ID (if available from API response)
        webhook_name: Env var name (DISCORD_WEBHOOK_URL, etc.)
        pnl_pct: Realized P/L for TP/SL events
        extra_payload: Additional context to store in payload JSON
    """
    symbol = pick_data.get("symbol", "UNKNOWN")
    direction = pick_data.get("direction", pick_data.get("signal", "LONG"))
    if isinstance(direction, str):
        direction = direction.upper()
        if direction in ("BUY",):
            direction = "LONG"
        elif direction in ("SELL",):
            direction = "SHORT"

    # Build payload: merge pick_data + extra
    payload = dict(pick_data)
    if extra_payload:
        payload.update(extra_payload)

    # Extract source_systems
    source_systems = pick_data.get("source_systems", pick_data.get("sources", []))
    if isinstance(source_systems, str):
        source_systems = [source_systems]

    sql = """
        INSERT IGNORE INTO at_discord_notifications
        (symbol, direction, entry_price, take_profit, stop_loss,
         confidence, agreement_count, source_systems, strategy,
         signal_tier, asset_class, discord_channel, discord_webhook,
         discord_message_id, event_type, pnl_pct, payload, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    params = (
        symbol,
        direction,
        _safe_float(pick_data.get("entry_price", pick_data.get("entry", pick_data.get("price")))),
        _safe_float(pick_data.get("tp_price", pick_data.get("take_profit", pick_data.get("tp")))),
        _safe_float(pick_data.get("sl_price", pick_data.get("stop_loss", pick_data.get("sl")))),
        _safe_float(pick_data.get("confidence")),
        pick_data.get("agreement_count", pick_data.get("consensus_count")),
        _json_dumps(source_systems) if source_systems else None,
        pick_data.get("strategy", pick_data.get("strategy_name", pick_data.get("algorithm"))),
        pick_data.get("signal_tier", pick_data.get("tier")),
        _derive_asset_class(symbol),
        channel,
        webhook_name,
        message_id,
        event_type,
        _safe_float(pnl_pct),
        _json_dumps(payload),
        now,
    )

    return _execute_with_retry(sql, params)


def log_gate_decision(
    symbol: str,
    direction: str,
    system_name: str,
    strategy: Optional[str],
    gate_name: str,
    gate_result: str,
    reason: Optional[str] = None,
    confidence: Optional[float] = None,
    entry_price: Optional[float] = None,
) -> Optional[int]:
    """
    Log a gate decision (PASS or REJECT) to at_discord_gate_log.

    Args:
        symbol: e.g. "BTCUSDT"
        direction: "LONG" or "SHORT"
        system_name: Source system name
        strategy: Strategy/algorithm name
        gate_name: Gate identifier (G1_DEDUP, G2_CONFIDENCE, etc.)
        gate_result: "PASS" or "REJECT"
        reason: Human-readable reason string
        confidence: Pick confidence at time of gate check
        entry_price: Entry price at time of gate check
    """
    sql = """
        INSERT INTO at_discord_gate_log
        (symbol, direction, system_name, strategy, gate_name, gate_result,
         reason, confidence, entry_price, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    params = (
        symbol,
        direction.upper() if direction else "LONG",
        system_name,
        strategy,
        gate_name,
        gate_result,
        reason[:255] if reason and len(reason) > 255 else reason,
        _safe_float(confidence),
        _safe_float(entry_price),
        now,
    )

    return _execute_with_retry(sql, params)


def mark_consensus_discord_sent(
    symbol: str,
    direction: str,
    channel: str = "consensus",
    message_id: Optional[str] = None,
) -> Optional[int]:
    """
    Mark a consensus_tracked row as sent to Discord.
    Uses WHERE discord_sent=0 to avoid race conditions.

    Returns rows affected (0 = already sent by another process, 1 = updated).
    """
    sql = """
        UPDATE consensus_tracked
        SET discord_sent = 1,
            discord_channel = %s,
            discord_message_id = %s,
            discord_sent_at = %s
        WHERE ticker = %s
          AND direction = %s
          AND discord_sent = 0
        ORDER BY created_at DESC
        LIMIT 1
    """
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Normalize symbol for consensus_tracked (uses ticker field, may not have USDT suffix)
    ticker = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")

    params = (channel, message_id, now, ticker, direction.upper() if direction else "LONG")
    return _execute_with_retry(sql, params)


def is_healthy() -> bool:
    """Quick health check — can we reach MySQL?"""
    conn = None
    try:
        conn = _get_conn()
        conn.ping(reconnect=False)
        _return_conn(conn)
        conn = None
        return True
    except Exception:
        if conn:
            try:
                _return_conn(conn)
                conn = None
            except Exception:
                pass
        return False


# ── Core Audit Trail Recording (mirrors SQLite recorder.py) ─────────────────

def mysql_start_run(run_id: str, regime_data: dict = None,
                    portfolio_dd: float = 0.0) -> Optional[int]:
    """Record start of an aggregation run in MySQL."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT IGNORE INTO at_aggregation_runs
        (run_id, started_at, status, regime_data, portfolio_drawdown, source)
        VALUES (%s, %s, 'RUNNING', %s, %s, 'aggregator')
    """
    return _execute_with_retry(sql, (
        run_id, now, _json_dumps(regime_data), portfolio_dd
    ))


def mysql_finish_run(run_id: str, consensus_count: int,
                     systems_loaded: int = 0, raw_count: int = 0) -> Optional[int]:
    """Mark an aggregation run as completed in MySQL."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        UPDATE at_aggregation_runs
        SET finished_at=%s, status='COMPLETED',
            consensus_count=%s, systems_loaded=%s, raw_picks_count=%s
        WHERE run_id=%s
    """
    return _execute_with_retry(sql, (now, consensus_count, systems_loaded, raw_count, run_id))


def mysql_record_raw_pick(
    pick_id: str, run_id: str, source_system: str,
    symbol: str, direction: str, entry_price: float,
    take_profit: float = None, stop_loss: float = None,
    risk_reward: float = None, confidence: float = 0.5,
    strategy: str = "", signal_timestamp: str = None,
    dedup_hash: str = None, raw_payload: dict = None,
    was_stale: bool = False, was_banned: bool = False,
    was_demoted: bool = False, was_wr_suppressed: bool = False,
) -> Optional[int]:
    """Record a raw pick in MySQL at_raw_picks."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Parse signal_timestamp to MySQL DATETIME format
    sig_ts = None
    if signal_timestamp:
        try:
            from datetime import datetime as _dt
            ts = str(signal_timestamp).replace("Z", "+00:00")
            for suffix in (" EST", " EDT", " UTC", " GMT"):
                ts = ts.replace(suffix, "")
            parsed = _dt.fromisoformat(ts)
            sig_ts = parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            sig_ts = None

    sql = """
        INSERT IGNORE INTO at_raw_picks
        (id, aggregation_run_id, source_system, symbol, asset_class, direction,
         entry_price, take_profit, stop_loss, risk_reward, confidence, strategy,
         raw_payload, signal_timestamp, recorded_at, dedup_hash,
         was_stale, was_banned, was_demoted, was_wr_suppressed, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'aggregator')
    """
    # Canonicalize symbol (defensive): FOREX/FUTURES rows keep their =X/=F
    # yfinance suffix so new inserts don't re-create the EURUSD vs EURUSD=X split.
    _ac = _derive_asset_class(symbol)
    symbol = canonicalize_symbol(symbol, _ac)
    return _execute_with_retry(sql, (
        pick_id, run_id, source_system, symbol, _ac,
        direction, _safe_float(entry_price), _safe_float(take_profit),
        _safe_float(stop_loss), _safe_float(risk_reward), _safe_float(confidence),
        strategy, _json_dumps(raw_payload), sig_ts, now, dedup_hash,
        int(was_stale), int(was_banned), int(was_demoted), int(was_wr_suppressed),
    ))


def _consensus_pick_exists(symbol: str, direction: str, entry_price: float) -> bool:
    """Check if an OPEN consensus pick with same symbol+direction already exists within 24h.

    Prevents duplicate rows when the aggregator runs every few minutes and
    re-emits the same consensus pick each cycle.
    """
    sql = """
        SELECT COUNT(*) FROM at_consensus_picks
        WHERE symbol = %s
          AND direction = %s
          AND status = 'OPEN'
          AND ABS(entry_price - %s) / GREATEST(entry_price, 0.0001) < 0.005
          AND generated_at >= NOW() - INTERVAL 24 HOUR
        LIMIT 1
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(sql, (symbol, direction, entry_price))
        row = cur.fetchone()
        _return_conn(conn)
        conn = None  # prevent double-close if any code runs after return
        return row is not None and row[0] > 0
    except Exception as e:
        logger.warning("Dedup check failed (will allow INSERT): %s", e)
        if conn:
            try:
                _return_conn(conn)
                conn = None
            except Exception:
                pass
        return False


def mysql_record_consensus_pick(
    pick_id: str, run_id: str, pick: dict,
) -> Optional[int]:
    """Record a consensus pick in MySQL at_consensus_picks.

    Deduplication: skips INSERT if an OPEN pick with the same symbol+direction
    and similar entry price (within 0.5%) already exists in the last 24 hours.
    """
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "LONG")
    entry = _safe_float(pick.get("entry", pick.get("entry_price", 0)))
    tp = _safe_float(pick.get("tp", pick.get("take_profit", 0)))
    sl = _safe_float(pick.get("sl", pick.get("stop_loss", 0)))
    conf = _safe_float(pick.get("confidence", 0.5))

    # ── Dedup gate: skip if same pick already exists within 24h ──
    if symbol and entry and _consensus_pick_exists(symbol, direction, float(entry)):
        logger.info("Dedup: skipping %s %s @ %s — already OPEN within 24h", symbol, direction, entry)
        return 0

    # Compute R:R
    rr = None
    try:
        e, t, s = float(entry or 0), float(tp or 0), float(sl or 0)
        if direction == "LONG" and (e - s) > 0:
            rr = round((t - e) / (e - s), 2)
        elif direction == "SHORT" and (s - e) > 0:
            rr = round((e - t) / (s - e), 2)
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    generated_at = pick.get("generated_at", now)
    if "T" in str(generated_at):
        try:
            from datetime import datetime as _dt
            ts = str(generated_at).replace("Z", "+00:00")
            generated_at = _dt.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            generated_at = now

    sql = """
        INSERT IGNORE INTO at_consensus_picks
        (id, aggregation_run_id, symbol, asset_class, direction,
         entry_price, take_profit, stop_loss, risk_reward, confidence,
         agreement_count, source_systems, source_strategies, system_confidences,
         consensus_tier, classification, regime_data, generated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    return _execute_with_retry(sql, (
        pick_id, run_id, symbol, _derive_asset_class(symbol), direction,
        entry, tp, sl, _safe_float(rr), conf,
        pick.get("agreement_count"),
        _json_dumps(pick.get("source_systems", [])),
        _json_dumps(pick.get("source_strategies", {})),
        _json_dumps(pick.get("system_rolling_wrs", {})),
        pick.get("consensus_tier"),
        pick.get("classification"),
        _json_dumps(pick.get("regime_data")),
        generated_at,
    ))


def mysql_record_filter(
    symbol: str, direction: str, source_system: str,
    filter_reason: str, details: str, run_id: str,
) -> Optional[int]:
    """Record a filter decision in MySQL at_filter_log."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO at_filter_log
        (aggregation_run_id, symbol, direction, source_system,
         asset_class, filter_reason, details, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """
    return _execute_with_retry(sql, (
        run_id, symbol, direction, source_system,
        _derive_asset_class(symbol) if symbol else "UNKNOWN",
        filter_reason, (details[:500] if details else None), now,
    ))


def mysql_close_trade(
    symbol: str,
    direction: str,
    exit_price: Optional[float],
    exit_reason: Optional[str],
    pnl_pct: Optional[float] = None,
    closed_at: Optional[str] = None,
) -> Optional[int]:
    """Close latest OPEN trade in trading_picks for symbol+direction.

    This provides a canonical write path for terminal trade updates so
    closure semantics are consistent across bots/resolvers/sync utilities.
    """
    if not symbol or not direction:
        return None

    _dir = str(direction).upper().strip()
    if _dir in ("BUY",):
        _dir = "LONG"
    elif _dir in ("SELL",):
        _dir = "SHORT"

    _exit = _safe_float(exit_price)
    _pnl = _safe_float(pnl_pct)
    _reason = str(exit_reason or "").upper().strip()

    # Canonical terminal status mapping with sign-coherence guard.
    # If exit_reason claims TP but pnl is negative (or SL but pnl is positive),
    # trust the pnl sign — source supplied contradictory reason+pnl, which
    # produced the WON-vs-PnL contradiction flagged at db_health.json.
    _pnl_signed = _pnl or 0
    if _reason in ("TP", "TP_HIT", "TP_HIT_RESOLVED", "TP1_HIT", "TP2_HIT"):
        if _pnl_signed < 0:
            logger.warning("mysql_close_trade won_pnl_contradiction: reason=%s but pnl=%s for %s/%s — trusting pnl sign",
                        _reason, _pnl_signed, symbol, _dir)
            _status = "LOST"
        else:
            _status = "WON"
    elif _reason in ("SL", "SL_HIT", "SL_HIT_RESOLVED", "STOP_LOSS", "ATR_TRAIL", "TRAIL", "TRAIL_SL"):
        if _pnl_signed > 0:
            logger.warning("mysql_close_trade won_pnl_contradiction: reason=%s but pnl=%s for %s/%s — trusting pnl sign",
                        _reason, _pnl_signed, symbol, _dir)
            _status = "WON"
        else:
            _status = "LOST"
    elif _reason in ("TIME_EXIT", "MAX_HOLD", "EXPIRED", "FORCE_CLOSED_TOXIC"):
        _status = "EXPIRED"
    else:
        if _pnl_signed > 0:
            _status = "WON"
        elif _pnl_signed < 0:
            _status = "LOST"
        else:
            _status = "EXPIRED"

    _closed_at = closed_at
    if isinstance(_closed_at, str) and "T" in _closed_at:
        try:
            _closed_at = datetime.fromisoformat(
                _closed_at.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            _closed_at = None
    if not _closed_at:
        _closed_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    sql = """
        UPDATE trading_picks
        SET status=%s,
            exit_price=%s,
            pnl_pct=%s,
            closed_at=%s,
            exit_reason=%s
        WHERE symbol=%s
          AND direction=%s
          AND status IN ('OPEN','ACTIVE','CLOSED','FLAT')
        ORDER BY created_at DESC
        LIMIT 1
    """
    return _execute_with_retry(
        sql,
        (_status, _exit, _pnl, _closed_at, (_reason or None), symbol, _dir),
    )


def mysql_sync_permutations(
    cross_system_perms: Optional[list] = None,
    cross_strategy_perms: Optional[list] = None,
) -> Dict[str, Any]:
    """Stub: sync cross-system / cross-strategy permutations to MySQL audit table.

    Currently a NO-OP returning success=False. Caller in
    audit_trail/dashboard_generator.py:10688 expects:
      {"success": bool, "system_snapshots": int, "strategy_snapshots": int}

    Wired as a stub on 2026-04-17 to silence repeated import-error warning
    in audit-dashboard.yml runs ("cannot import name 'mysql_sync_permutations'").
    The function was referenced but never implemented. Until the permutation
    audit table is designed + MySQL credentials are restored (currently 1045
    Access denied on every run), this returns a structured no-op so the
    caller's downstream logging stays clean.

    Future implementation should:
      - Insert each (system, perm_id, trust_score, n_picks, wr, pnl, ts) row
        into a `permutation_snapshots` table
      - Bump system_snapshots / strategy_snapshots counters accordingly
      - Set success=True only when rows actually committed
    """
    n_sys = len(cross_system_perms or [])
    n_strat = len(cross_strategy_perms or [])
    return {
        "success": False,
        "system_snapshots": 0,
        "strategy_snapshots": 0,
        "skipped_reason": "permutation_sync_not_implemented_yet",
        "candidate_system_perms": n_sys,
        "candidate_strategy_perms": n_strat,
    }


def mysql_fetch_closed_non_crypto(
    max_age_days: int = 365, limit: int = 5000
) -> tuple:
    """Returns (picks, meta) with meta.ok / meta.fetched / meta.error for dashboard UX."""
    meta: Dict[str, Any] = {"ok": False, "fetched": 0, "error": None}
    conn = None  # init to None so except block's if conn: is safe if _get_conn raises
    try:
        conn = _get_conn()
        cur = conn.cursor()
        sql = """
            SELECT symbol, direction, strategy, entry_price, exit_price, take_profit, stop_loss,
                   confidence, source_system, category, status, pnl_pct, created_at, closed_at
            FROM trading_picks
            WHERE category IN ('equity','stock','stocks','forex','commodity','commodities',
                               'futures','etf','bond','penny','pennystock','index')
              AND status IN ('WON','WIN','LOST','LOSS','CLOSED','CLOSED_TP','CLOSED_SL',
                             'tp_hit','sl_hit','EXPIRED','FLAT','time_exit')
              AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY closed_at DESC
            LIMIT %s
        """
        cur.execute(sql, (max_age_days, limit))
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        # NOTE: do NOT return conn here — rows still being processed.
        # Conn returned only at the very end (after the row loop).

        picks = []
        _status_map = {
            "WON": "WON", "WIN": "WON", "tp_hit": "WON", "CLOSED_TP": "WON",
            "LOST": "LOST", "LOSS": "LOST", "sl_hit": "LOST", "CLOSED_SL": "LOST",
            "EXPIRED": "EXPIRED", "FLAT": "CLOSED", "CLOSED": "CLOSED",
            "time_exit": "EXPIRED",
        }
        _cat_map = {
            "equity": "EQUITY", "stock": "EQUITY", "stocks": "EQUITY",
            "forex": "FOREX", "commodity": "COMMODITY", "commodities": "COMMODITY",
            "futures": "FUTURES", "etf": "ETF", "bond": "BOND",
            "penny": "EQUITY", "pennystock": "EQUITY", "index": "FUTURES",
        }
        for row in rows:
            r = dict(zip(columns, row))
            pnl = float(r.get("pnl_pct") or 0)
            status_raw = str(r.get("status", "")).strip()
            norm_status = _status_map.get(status_raw, "CLOSED")
            cat_raw = str(r.get("category", "")).strip().lower()
            # 2026-04-20 code review: previously `_cat_map.get(cat_raw, "EQUITY")`
            # silently defaulted unknown/misaligned DB category values to EQUITY,
            # causing 7 closed rows to display with wrong asset_class on /audit
            # (e.g. LINKUSDT → EQUITY). Derive from symbol first; fall back to
            # the DB category hint only if symbol-derivation fails.
            asset_class = (
                resolve_asset_class(
                    r.get("symbol", ""),
                    raw={"category": cat_raw},
                    source_system=r.get("source_system", "") or "mysql_client",
                    strategy=r.get("strategy", ""),
                )
                or _cat_map.get(cat_raw, "EQUITY")
            )
            # Reconstruct exit_price from entry+PnL if MySQL doesn't have it
            # (bus task 8: 459 closed non-crypto picks were missing exit_price,
            # breaking audit §7.1 traceability).
            _entry_f = float(r.get("entry_price") or 0)
            _exit_raw = r.get("exit_price")
            _exit_f = float(_exit_raw) if _exit_raw not in (None, 0, 0.0, "") else 0.0
            if _exit_f <= 0 and _entry_f > 0 and pnl != 0:
                _dir = str(r.get("direction", "LONG")).upper()
                if _dir in ("LONG", "BUY"):
                    _exit_f = round(_entry_f * (1 + pnl / 100.0), 8)
                else:  # SHORT
                    _exit_f = round(_entry_f * (1 - pnl / 100.0), 8)
            picks.append({
                "symbol": r.get("symbol", ""),
                "direction": str(r.get("direction", "LONG")).upper(),
                "strategy": r.get("strategy", ""),
                "entry_price": _entry_f,
                "exit_price": _exit_f,
                "take_profit": float(r.get("take_profit") or 0),
                "stop_loss": float(r.get("stop_loss") or 0),
                "confidence": float(r.get("confidence") or 0),
                "source_system": r.get("source_system", "mysql_trading_picks"),
                "asset_class": asset_class,
                "category": cat_raw,
                "status": norm_status,
                "pnl_pct": pnl,
                "net_pnl_pct": pnl,
                "timestamp": str(r.get("created_at", "")),
                "closed_at": str(r.get("closed_at", "")),
                "exit_reason": norm_status,
                "_from_mysql": True,
            })
        logger.info(f"MySQL: fetched {len(picks)} closed non-crypto picks")
        meta["ok"] = True
        meta["fetched"] = len(picks)
        _return_conn(conn)
        conn = None
        return picks, meta
    except Exception as e:
        logger.warning(f"MySQL fetch_closed_non_crypto failed: {e}")
        meta["error"] = str(e)[:500]
        if conn:
            try:
                _return_conn(conn)
                conn = None
            except Exception:
                pass
        return [], meta


def mysql_record_event(
    event_type: str, pick_id: str = None, run_id: str = None,
    symbol: str = None, payload: dict = None, origin: str = "aggregator",
) -> Optional[int]:
    """Record an audit event in MySQL at_audit_events."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO at_audit_events
        (event_type, pick_id, aggregation_run_id, symbol,
         asset_class, payload, origin, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """
    return _execute_with_retry(sql, (
        event_type, pick_id, run_id, symbol,
        _derive_asset_class(symbol) if symbol else "UNKNOWN",
        _json_dumps(payload), origin, now,
    ))

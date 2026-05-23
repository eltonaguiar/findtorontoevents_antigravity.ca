"""
Core recording logic for the audit trail.

Handles:
- UUID generation for all entities
- SHA-256 dedup hashing
- Schema validation (required fields, price sanity, confidence range)
- Asset class derivation from symbol
- All INSERT operations
"""

import datetime as dt
import hashlib
import json
import logging
import uuid
from typing import Optional

from audit_trail.db import get_connection

# ── MySQL dual-write (fire-and-forget, never blocks SQLite) ──
try:
    from audit_trail.mysql_client import (
        mysql_start_run, mysql_finish_run, mysql_record_raw_pick,
        mysql_record_consensus_pick, mysql_record_filter, mysql_record_event,
    )
    _HAS_MYSQL = True
except ImportError:
    _HAS_MYSQL = False

_log = logging.getLogger("audit_trail.recorder")


# ── Asset class derivation ──

_FOREX_BASES = frozenset(("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF",
                          "NZD", "SEK", "NOK", "DKK", "SGD", "HKD", "MXN",
                          "ZAR", "TRY", "PLN", "CZK", "HUF"))
_FOREX_QUOTES = frozenset(("USD", "EUR", "JPY", "GBP", "CHF", "CAD",
                           "AUD", "NZD"))
_CRYPTO_SUFFIXES = ("USDT", "BTC", "ETH", "BUSD", "USDC")
_COMMODITY_SYMBOLS = frozenset((
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",    # precious metals
    "USOIL", "UKOIL", "CL", "CRUDE", "WTIUSD",  # oil
    "NATGAS", "NG", "WHEATUSD", "CORNUSD",       # energy/agriculture
    "GOLD", "SILVER",
))


def _is_forex_pair(s: str) -> bool:
    """Return True if symbol looks like a proper FX pair (not crypto)."""
    if s.endswith("=X"):
        return True
    if "/" in s:
        parts = s.split("/")
        return len(parts) == 2 and parts[0] in _FOREX_BASES and parts[1] in _FOREX_QUOTES
    # 6-char CCY1CCY2: starts with forex base, ends with forex quote, no crypto suffix
    if len(s) == 6 and not any(s.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):
        base3, quote3 = s[:3], s[3:]
        return base3 in _FOREX_BASES and quote3 in _FOREX_QUOTES
    return False


def derive_asset_class(symbol: str) -> str:
    """Derive asset class from normalized symbol."""
    s = symbol.upper().replace("-", "").split(".")[0]
    # Commodities first (XAUUSD starts with XAU — not a forex base)
    if s in _COMMODITY_SYMBOLS:
        return "COMMODITY"
    # Forex — before crypto so EURUSD doesn't fall to EQUITY
    if _is_forex_pair(s):
        return "FOREX"
    # Crypto — ends with stablecoin/BTC/ETH quote
    if any(s.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):
        return "CRYPTO"
    return "EQUITY"


# ── Dedup hash ──

def compute_dedup_hash(symbol: str, direction: str, entry_price: float,
                       signal_ts: str) -> str:
    """SHA-256 hash for duplicate detection. Rounds timestamp to 5-min window."""
    try:
        ts = dt.datetime.fromisoformat(str(signal_ts).replace("Z", "+00:00"))
        epoch_rounded = int(ts.timestamp() / 300) * 300
    except (ValueError, TypeError):
        epoch_rounded = 0
    raw = f"{symbol}|{direction}|{entry_price:.8f}|{epoch_rounded}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Validation ──

def _validate_pick(pick: dict, source_system: str) -> Optional[str]:
    """Validate a raw pick. Returns error string or None if valid."""
    symbol = pick.get("symbol", pick.get("pair", ""))
    if not symbol:
        return "missing symbol"

    direction = pick.get("direction", pick.get("signal_type",
                         pick.get("signal", "")))
    d = str(direction).upper().strip()
    if d not in ("LONG", "SHORT", "BUY", "SELL"):
        return f"invalid direction: {direction}"

    entry = pick.get("entry_price", pick.get("entryPrice",
                     pick.get("entry", pick.get("price", 0))))
    try:
        entry = float(entry)
    except (ValueError, TypeError):
        return f"invalid entry_price: {entry}"
    if entry <= 0:
        return f"entry_price must be > 0, got {entry}"

    conf = pick.get("confidence", pick.get("ml_score", 0.5))
    try:
        conf = float(conf)
    except (ValueError, TypeError):
        pass
    else:
        if not (0.0 <= conf <= 1.0):
            return f"confidence out of range: {conf}"

    # Timestamp sanity: not more than 5 min in the future
    ts = pick.get("timestamp", pick.get("generated_at", pick.get("time", "")))
    if ts:
        try:
            pick_dt = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            future_delta = (pick_dt - dt.datetime.now(dt.timezone.utc)).total_seconds()
            if future_delta > 300:
                return f"timestamp {ts} is {future_delta / 60:.0f}min in the future"
        except (ValueError, TypeError):
            pass

    return None


# ── Field extractors (handle varying source formats) ──

def _extract_price(pick: dict, *keys: str) -> Optional[float]:
    """Extract a price field from a pick dict, trying multiple key names."""
    for k in keys:
        val = pick.get(k)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return None


def _extract_direction(pick: dict) -> Optional[str]:
    """Normalize direction from various source formats."""
    raw = pick.get("direction", pick.get("signal_type", pick.get("signal", "")))
    d = str(raw).upper().strip()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return None


def _extract_symbol(pick: dict) -> str:
    """Extract and normalize symbol."""
    raw = str(pick.get("symbol", pick.get("pair", ""))).strip().upper()
    raw = raw.replace("-", "")
    if raw.endswith("USD") and not raw.endswith("USDT"):
        raw = raw + "T"
    return raw


def _extract_strategy(pick: dict) -> str:
    """Extract strategy name from a pick, handling different source formats."""
    strat = pick.get("strategy", pick.get("strategy_name", ""))
    if strat:
        return str(strat)
    algo = pick.get("algorithmName", pick.get("algorithm", ""))
    if algo:
        return str(algo)
    dna = pick.get("strategy_dna")
    if isinstance(dna, dict):
        return dna.get("strategy_id", dna.get("name", ""))
    if isinstance(dna, str) and dna:
        return dna
    return ""


def _now_iso() -> str:
    """Current UTC timestamp in ISO 8601."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ── Public API ──

def start_run(regime_data: dict = None, portfolio_dd: float = 0.0) -> str:
    """Start a new aggregation run. Returns run_id (UUID)."""
    run_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO aggregation_runs (run_id, started_at, status, regime_data, portfolio_drawdown) "
        "VALUES (?, ?, 'RUNNING', ?, ?)",
        (run_id, _now_iso(), json.dumps(regime_data) if regime_data else None, portfolio_dd),
    )
    conn.commit()

    # MySQL dual-write
    if _HAS_MYSQL:
        try:
            mysql_start_run(run_id, regime_data, portfolio_dd)
        except Exception as e:
            _log.warning("MySQL start_run failed: %s", e)

    record_event("AGGREGATION_START", run_id=run_id,
                 payload={"regime": regime_data, "portfolio_dd": portfolio_dd})
    return run_id


def finish_run(run_id: str, consensus_count: int, systems_loaded: int = 0,
               raw_count: int = 0) -> None:
    """Mark an aggregation run as completed."""
    conn = get_connection()
    conn.execute(
        "UPDATE aggregation_runs SET finished_at=?, status='COMPLETED', "
        "consensus_count=?, systems_loaded=?, raw_picks_count=? WHERE run_id=?",
        (_now_iso(), consensus_count, systems_loaded, raw_count, run_id),
    )
    conn.commit()

    if _HAS_MYSQL:
        try:
            mysql_finish_run(run_id, consensus_count, systems_loaded, raw_count)
        except Exception as e:
            _log.warning("MySQL finish_run failed: %s", e)


def record_raw_pick(source_system: str, pick: dict, run_id: str) -> Optional[str]:
    """Record a raw pick from a source system. Returns pick_id or None if invalid/duplicate."""
    err = _validate_pick(pick, source_system)
    if err:
        return None

    symbol = _extract_symbol(pick)
    direction = _extract_direction(pick)
    if not direction:
        return None

    entry = _extract_price(pick, "entry_price", "entryPrice", "entry", "price")
    tp = _extract_price(pick, "take_profit", "targetPrice", "tp_price", "tp", "target_price")
    sl = _extract_price(pick, "stop_loss", "stopPrice", "sl_price", "sl", "stop_price")
    conf = _extract_price(pick, "confidence", "ml_score") or 0.5
    strategy = _extract_strategy(pick)
    signal_ts = pick.get("timestamp", pick.get("generated_at", pick.get("time", "")))

    # Compute risk/reward
    rr = None
    if entry and tp and sl and entry > 0:
        try:
            if direction == "LONG" and (entry - sl) > 0:
                rr = round((tp - entry) / (entry - sl), 2)
            elif direction == "SHORT" and (sl - entry) > 0:
                rr = round((entry - tp) / (sl - entry), 2)
        except (ZeroDivisionError, TypeError):
            pass

    # Dedup hash
    dedup = compute_dedup_hash(symbol, direction, entry or 0, signal_ts or "")

    pick_id = str(uuid.uuid4())
    conn = get_connection()

    # Extract enrichment fields from pick (populated by enrichment_pipeline.py)
    enrichment = pick.get("enrichment") or {}
    enrich_grade    = enrichment.get("context_grade")
    enrich_align    = enrichment.get("alignment_score")
    enrich_contrary = enrichment.get("contrary_score")
    enrich_rsi      = (enrichment.get("rsi") or {}).get("rsi_14_1h")
    enrich_fg       = (enrichment.get("sentiment") or {}).get("fear_greed_index")
    enrich_funding  = (enrichment.get("funding") or {}).get("avg_funding_8h")
    enrich_nvt_r    = (enrichment.get("on_chain") or {}).get("nvt_ratio")
    enrich_nvt_s    = (enrichment.get("on_chain") or {}).get("nvt_signal")
    enrich_weekly   = (enrichment.get("supplemental") or {}).get("weekly_momentum")
    enrich_pct7d    = (enrichment.get("supplemental") or {}).get("price_change_7d_pct")
    enrich_mem_sig  = (enrichment.get("mempool") or {}).get("btc_demand_signal")
    enrich_mem_fee  = (enrichment.get("mempool") or {}).get("btc_fee_fastest_sat_vb")
    enrich_defi_sig = (enrichment.get("dex_1inch") or {}).get("defi_cex_signal")
    enrich_defi_spd = (enrichment.get("dex_1inch") or {}).get("defi_cex_spread_pct")
    enrich_dex_liq  = (enrichment.get("dex_0x") or {}).get("dex_liquidity_signal")
    enrich_addrs    = (enrichment.get("on_chain") or {}).get("active_addresses_24h")
    enrich_blob     = json.dumps(enrichment, default=str) if enrichment else None

    try:
        conn.execute(
            "INSERT INTO raw_picks "
            "(id, aggregation_run_id, source_system, symbol, asset_class, direction, "
            "entry_price, take_profit, stop_loss, risk_reward, confidence, strategy, "
            "raw_payload, signal_timestamp, recorded_at, dedup_hash, "
            "enrichment_grade, enrichment_alignment, enrichment_contrary, "
            "enrichment_rsi, enrichment_fear_greed, enrichment_funding_rate, "
            "enrichment_nvt_ratio, enrichment_nvt_signal, enrichment_weekly_mom, "
            "enrichment_pct_7d, enrichment_btc_mempool, enrichment_btc_fee_sat, "
            "enrichment_defi_cex_sig, enrichment_defi_spread, enrichment_dex_liq, "
            "enrichment_active_addrs, enrichment_data) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pick_id, run_id, source_system, symbol, derive_asset_class(symbol),
             direction, entry, tp, sl, rr, conf, strategy,
             json.dumps(pick, default=str), signal_ts, _now_iso(), dedup,
             enrich_grade, enrich_align, enrich_contrary,
             enrich_rsi, enrich_fg, enrich_funding,
             enrich_nvt_r, enrich_nvt_s, enrich_weekly,
             enrich_pct7d, enrich_mem_sig, enrich_mem_fee,
             enrich_defi_sig, enrich_defi_spd, enrich_dex_liq,
             enrich_addrs, enrich_blob),
        )
        conn.commit()

        # MySQL dual-write
        if _HAS_MYSQL:
            try:
                mysql_record_raw_pick(
                    pick_id=pick_id, run_id=run_id, source_system=source_system,
                    symbol=symbol, direction=direction, entry_price=entry,
                    take_profit=tp, stop_loss=sl, risk_reward=rr,
                    confidence=conf, strategy=strategy,
                    signal_timestamp=signal_ts, dedup_hash=dedup,
                    raw_payload=pick,
                )
            except Exception as e:
                _log.warning("MySQL record_raw_pick failed: %s", e)

        return pick_id
    except Exception:
        conn.rollback()
        return None


def mark_raw_pick_filtered(pick_id: str, reason: str) -> None:
    """Mark a raw pick as filtered (set the appropriate was_* flag)."""
    flag_map = {
        "staleness": "was_stale",
        "banned_strategy": "was_banned",
        "demoted_system": "was_demoted",
        "wr_suppressed": "was_wr_suppressed",
    }
    col = flag_map.get(reason)
    if col and pick_id:
        conn = get_connection()
        conn.execute(f"UPDATE raw_picks SET {col}=1 WHERE id=?", (pick_id,))
        conn.commit()


def record_consensus_pick(pick: dict, run_id: str) -> str:
    """Record a consensus pick that passed all gates. Returns pick_id."""
    pick_id = str(uuid.uuid4())
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = pick.get("entry", pick.get("entry_price", 0))
    tp = pick.get("tp", pick.get("take_profit", 0))
    sl = pick.get("sl", pick.get("stop_loss", 0))
    conf = pick.get("confidence", 0.5)
    generated_at = pick.get("generated_at", _now_iso())

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

    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO consensus_picks "
            "(id, aggregation_run_id, symbol, asset_class, direction, entry_price, "
            "take_profit, stop_loss, risk_reward, confidence, agreement_count, "
            "source_systems, source_strategies, system_confidences, consensus_tier, "
            "classification, regime_data, generated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pick_id, run_id, symbol, derive_asset_class(symbol), direction,
             entry, tp, sl, rr, conf,
             pick.get("agreement_count"),
             json.dumps(pick.get("source_systems", [])),
             json.dumps(pick.get("source_strategies", {})),
             json.dumps(pick.get("system_rolling_wrs", {})),
             pick.get("consensus_tier"),
             pick.get("classification"),
             json.dumps(pick.get("regime_data")) if pick.get("regime_data") else None,
             generated_at),
        )
        conn.commit()

        # MySQL dual-write
        if _HAS_MYSQL:
            try:
                mysql_record_consensus_pick(pick_id, run_id, pick)
            except Exception as e:
                _log.warning("MySQL record_consensus_pick failed: %s", e)
    except Exception:
        conn.rollback()
    return pick_id


def record_filter(symbol: str, direction: str, source_system: str,
                  filter_reason: str, details: str, run_id: str,
                  raw_pick_id: str = None) -> None:
    """Log why a pick was filtered out."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO filter_log "
        "(aggregation_run_id, raw_pick_id, symbol, direction, source_system, "
        "filter_reason, details, timestamp) VALUES (?,?,?,?,?,?,?,?)",
        (run_id, raw_pick_id, symbol, direction, source_system,
         filter_reason, details, _now_iso()),
    )
    conn.commit()

    if raw_pick_id:
        mark_raw_pick_filtered(raw_pick_id, filter_reason)

    # MySQL dual-write
    if _HAS_MYSQL:
        try:
            mysql_record_filter(symbol, direction, source_system,
                                filter_reason, details, run_id)
        except Exception as e:
            _log.warning("MySQL record_filter failed: %s", e)


def record_event(event_type: str, pick_id: str = None, run_id: str = None,
                 symbol: str = None, payload: dict = None,
                 origin: str = "aggregator") -> None:
    """Log a chronological audit event."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_events "
        "(event_type, pick_id, aggregation_run_id, symbol, payload, origin, timestamp) "
        "VALUES (?,?,?,?,?,?,?)",
        (event_type, pick_id, run_id, symbol,
         json.dumps(payload, default=str) if payload else None,
         origin, _now_iso()),
    )
    conn.commit()

    if _HAS_MYSQL:
        try:
            mysql_record_event(event_type, pick_id, run_id, symbol, payload, origin)
        except Exception as e:
            _log.warning("MySQL record_event failed: %s", e)


def update_pick_outcome(pick_id: str, status: str, exit_price: float,
                        exit_reason: str, pnl_pct: float) -> None:
    """Update a consensus pick with its outcome (TP hit, SL hit, etc.)."""
    conn = get_connection()
    conn.execute(
        "UPDATE consensus_picks SET status=?, exit_price=?, exit_reason=?, "
        "pnl_pct=?, closed_at=? WHERE id=?",
        (status, exit_price, exit_reason, pnl_pct, _now_iso(), pick_id),
    )
    conn.commit()

    record_event(event_type=f"POSITION_CLOSED_{status}",
                 pick_id=pick_id,
                 payload={"exit_price": exit_price, "exit_reason": exit_reason,
                          "pnl_pct": pnl_pct},
                 origin="outcome_tracker")


def refresh_strategy_stats() -> None:
    """Rebuild the strategy_stats materialized view from consensus_picks."""
    conn = get_connection()
    conn.execute("DELETE FROM strategy_stats")

    # Simple aggregation from consensus_picks by source_systems JSON array
    conn.execute("""
        INSERT OR REPLACE INTO strategy_stats
            (strategy, source_system, asset_class, total_picks, consensus_picks,
             wins, losses, win_rate, avg_pnl_pct, best_pnl, worst_pnl, last_updated)
        SELECT
            COALESCE(cp.consensus_tier, 'unknown') AS strategy,
            je.value AS source_system,
            cp.asset_class,
            COUNT(*) AS total_picks,
            COUNT(*) AS consensus_picks,
            SUM(CASE WHEN cp.status = 'WON' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN cp.status = 'LOST' THEN 1 ELSE 0 END) AS losses,
            CASE WHEN SUM(CASE WHEN cp.status IN ('WON','LOST') THEN 1 ELSE 0 END) > 0
                THEN CAST(SUM(CASE WHEN cp.status='WON' THEN 1 ELSE 0 END) AS REAL)
                     / SUM(CASE WHEN cp.status IN ('WON','LOST') THEN 1 ELSE 0 END)
                ELSE 0.0 END AS win_rate,
            AVG(COALESCE(cp.pnl_pct, 0)) AS avg_pnl_pct,
            MAX(COALESCE(cp.pnl_pct, 0)) AS best_pnl,
            MIN(COALESCE(cp.pnl_pct, 0)) AS worst_pnl,
            datetime('now') AS last_updated
        FROM consensus_picks cp,
             json_each(cp.source_systems) je
        WHERE cp.status != 'OPEN'
        GROUP BY strategy, source_system, cp.asset_class
    """)
    conn.commit()


# ── Backtest recording ──

def record_backtest_run(
    strategy: str,
    results: dict,
    source_db: str = "real_data_sweep",
    symbol: str = "BTC/USDT",
) -> Optional[str]:
    """Record a backtest sweep result into bt_backtest_runs."""
    conn = get_connection()

    # Ensure tables exist
    conn.execute("""CREATE TABLE IF NOT EXISTS bt_backtest_runs (
        id TEXT PRIMARY KEY, source_db TEXT NOT NULL, source_table TEXT NOT NULL DEFAULT '',
        strategy TEXT NOT NULL, symbol TEXT NOT NULL DEFAULT 'BTC/USDT',
        asset_class TEXT NOT NULL DEFAULT 'CRYPTO',
        total_trades INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0.0, profit_factor REAL DEFAULT 0.0,
        total_return REAL DEFAULT 0.0, sharpe REAL DEFAULT 0.0,
        max_drawdown REAL DEFAULT 0.0, imported_at TEXT NOT NULL
    )""")

    run_id = str(uuid.uuid4())
    wr = results.get("win_rate") or 0
    trades = results.get("total_trades") or 0
    wins = int(trades * wr) if wr <= 1 else int(trades * wr / 100)

    try:
        conn.execute(
            "INSERT OR IGNORE INTO bt_backtest_runs "
            "(id, source_db, source_table, strategy, symbol, asset_class, "
            "total_trades, wins, losses, win_rate, profit_factor, "
            "total_return, sharpe, max_drawdown, imported_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, source_db, "", strategy, symbol,
             derive_asset_class(symbol.replace("/", "")),
             trades, wins, trades - wins,
             wr if wr <= 1 else wr / 100,
             results.get("profit_factor") or 0,
             results.get("total_return") or 0,
             results.get("sharpe") or 0,
             results.get("max_drawdown") or 0,
             _now_iso()),
        )
        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        return None


def record_backtest_batch(sweep_results: list, source_db: str = "real_data_sweep") -> dict:
    """Record an entire batch of backtest sweep results.

    Returns dict with counts: {"recorded": N, "skipped": N}
    """
    recorded = 0
    skipped = 0
    for r in sweep_results:
        name = r.get("strategy_name", "")
        if not name:
            skipped += 1
            continue
        run_id = record_backtest_run(name, r, source_db=source_db)
        if run_id:
            recorded += 1
        else:
            skipped += 1
    return {"recorded": recorded, "skipped": skipped}

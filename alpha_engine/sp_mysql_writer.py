"""
Smart Picks MySQL Writer — persists batch results to sp_batches / sp_picks / sp_daily_performance.

Usage:
    from alpha_engine.sp_mysql_writer import save_batch_to_db, save_daily_summary_to_db

    # After tracker resolves a batch:
    save_batch_to_db(batch_dict)

    # After daily aggregation:
    save_daily_summary_to_db(date_str, batches_list)

Fire-and-forget: all DB writes wrapped in try/except so they never block
the main smart_picks pipeline.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, date
from typing import Any

logger = logging.getLogger("sp_mysql_writer")

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "stocks")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")


def _connect():
    import pymysql
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, connect_timeout=10, read_timeout=10,
        write_timeout=10, charset="utf8mb4", autocommit=True,
    )


def _float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _parse_dt(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)  # MySQL doesn't store tz
        return dt
    except Exception:
        return None


def save_batch_to_db(batch: dict) -> bool:
    """Insert a resolved batch + its picks into MySQL. Returns True on success."""
    try:
        conn = _connect()
        cur = conn.cursor()

        batch_id = batch.get("version") or batch.get("batch_id") or "unknown"
        generated_at = _parse_dt(batch.get("generated_at"))
        if not generated_at:
            logger.warning("Batch %s has no generated_at, skipping", batch_id)
            return False

        picks = batch.get("picks", [])
        crypto_count = sum(1 for p in picks if str(p.get("asset_class", "CRYPTO")).upper() == "CRYPTO")

        # Upsert batch
        cur.execute("""
            INSERT INTO sp_batches
                (batch_id, generated_at, regime, fear_greed, btc_price,
                 total_scored, picks_count, crypto_count, non_crypto_count,
                 resolved, resolved_at, final_wr, final_avg_pnl, final_pf,
                 final_tp_hits, final_sl_hits)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                resolved = VALUES(resolved),
                resolved_at = VALUES(resolved_at),
                final_wr = VALUES(final_wr),
                final_avg_pnl = VALUES(final_avg_pnl),
                final_pf = VALUES(final_pf),
                final_tp_hits = VALUES(final_tp_hits),
                final_sl_hits = VALUES(final_sl_hits)
        """, (
            batch_id,
            generated_at,
            batch.get("regime", "NEUTRAL"),
            _int(batch.get("fear_greed")),
            _float(batch.get("btc_price_at_open")),
            _int(batch.get("total_scored"), 0),
            len(picks),
            crypto_count,
            len(picks) - crypto_count,
            1 if batch.get("resolved") else 0,
            _parse_dt(batch.get("resolved_at")),
            _float(batch.get("final_wr")),
            _float(batch.get("final_avg_pnl")),
            _float(batch.get("final_pf")),
            _int(batch.get("final_tp_hits")),
            _int(batch.get("final_sl_hits")),
        ))

        # Get final PnL per pick from last snapshot
        snapshots = batch.get("snapshots", [])
        last_snap = snapshots[-1] if snapshots else {}
        snap_pnls = last_snap.get("picks_pnl", [])
        snap_statuses = last_snap.get("picks_status", [])

        # Insert picks (skip if already exist for this batch)
        for i, pick in enumerate(picks):
            if not isinstance(pick, dict):
                continue
            symbol = pick.get("symbol", "")
            if not symbol:
                continue

            final_pnl = snap_pnls[i] if i < len(snap_pnls) else _float(pick.get("final_pnl"))
            final_status = snap_statuses[i] if i < len(snap_statuses) else pick.get("final_status")

            # Detect asset class from symbol if not set
            asset_class = str(pick.get("asset_class", "")).upper()
            if not asset_class:
                if symbol.endswith("USDT") or symbol.endswith("USD"):
                    asset_class = "CRYPTO"
                elif symbol.endswith("=X"):
                    asset_class = "FOREX"
                elif symbol.endswith("=F"):
                    asset_class = "FUTURES"
                else:
                    asset_class = "EQUITY"

            try:
                cur.execute("""
                    INSERT INTO sp_picks
                        (batch_id, symbol, asset_class, direction, tier, strategy,
                         source_system, smart_score, validated_score, ml_composite,
                         entry_price, tp_price, sl_price, confidence, fwd_wr,
                         fwd_trades, regime, rr_ratio, pnl_at_snapshot, final_pnl,
                         final_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    batch_id,
                    symbol,
                    asset_class,
                    str(pick.get("direction", "LONG")).upper(),
                    pick.get("tier", "SWING"),
                    pick.get("strategy"),
                    pick.get("source_system"),
                    _float(pick.get("smart_score")),
                    _float(pick.get("validated_score")),
                    _float(pick.get("ml_composite")),
                    _float(pick.get("entry") or pick.get("entry_price")),
                    _float(pick.get("tp") or pick.get("take_profit")),
                    _float(pick.get("sl") or pick.get("stop_loss")),
                    _float(pick.get("confidence")),
                    _float(pick.get("fwd_wr") or pick.get("strat_fwd_wr")),
                    _int(pick.get("fwd_trades") or pick.get("strat_fwd_trades")),
                    pick.get("regime"),
                    _float(pick.get("rr")),
                    _float(pick.get("pnl_pct")),
                    _float(final_pnl),
                    final_status,
                ))
            except Exception as e:
                logger.debug("Pick insert for %s/%s: %s", batch_id, symbol, e)

        conn.close()
        logger.info("Saved batch %s (%d picks) to MySQL", batch_id, len(picks))
        return True

    except Exception as e:
        logger.warning("Failed to save batch to MySQL: %s", e)
        return False


def save_daily_summary_to_db(target_date: date | str, batches: list[dict]) -> bool:
    """Compute and insert daily aggregate performance from resolved batches."""
    try:
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        # Aggregate all picks from all batches on this date
        all_pnls = []
        all_symbols = []
        regime = "NEUTRAL"

        for batch in batches:
            if not batch.get("resolved"):
                continue
            snapshots = batch.get("snapshots", [])
            last_snap = snapshots[-1] if snapshots else {}
            pnls = last_snap.get("picks_pnl", [])
            picks = batch.get("picks", [])
            regime = batch.get("regime", regime)

            for i, pnl in enumerate(pnls):
                all_pnls.append(float(pnl))
                sym = picks[i].get("symbol", "?") if i < len(picks) else "?"
                all_symbols.append(sym)

        if not all_pnls:
            return False

        wins = sum(1 for p in all_pnls if p > 0)
        losses = sum(1 for p in all_pnls if p < 0)
        total = len(all_pnls)
        wr = round(wins / total * 100, 1) if total else 0
        avg_pnl = round(sum(all_pnls) / total, 3) if total else 0
        total_pnl = round(sum(all_pnls), 3)
        gross_profit = sum(p for p in all_pnls if p > 0)
        gross_loss = abs(sum(p for p in all_pnls if p < 0))
        pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0)

        best_idx = all_pnls.index(max(all_pnls))
        worst_idx = all_pnls.index(min(all_pnls))

        conn = _connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sp_daily_performance
                (snapshot_date, batches_count, picks_count, wins, losses,
                 win_rate, avg_pnl, total_pnl, profit_factor,
                 best_pick, best_pnl, worst_pick, worst_pnl, regime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                batches_count=VALUES(batches_count), picks_count=VALUES(picks_count),
                wins=VALUES(wins), losses=VALUES(losses), win_rate=VALUES(win_rate),
                avg_pnl=VALUES(avg_pnl), total_pnl=VALUES(total_pnl),
                profit_factor=VALUES(profit_factor),
                best_pick=VALUES(best_pick), best_pnl=VALUES(best_pnl),
                worst_pick=VALUES(worst_pick), worst_pnl=VALUES(worst_pnl),
                regime=VALUES(regime)
        """, (
            target_date, len(batches), total, wins, losses,
            wr, avg_pnl, total_pnl, pf,
            all_symbols[best_idx], all_pnls[best_idx],
            all_symbols[worst_idx], all_pnls[worst_idx],
            regime,
        ))
        conn.close()
        logger.info("Saved daily summary for %s: %d picks, WR=%.1f%%, PnL=%.2f%%",
                     target_date, total, wr, total_pnl)
        return True

    except Exception as e:
        logger.warning("Failed to save daily summary to MySQL: %s", e)
        return False

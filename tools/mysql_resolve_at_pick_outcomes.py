#!/usr/bin/env python3
"""
tools/mysql_resolve_at_pick_outcomes.py — Resolve stale OPEN rows in at_pick_outcomes
======================================================================================

Connects to the ejaguiar1_stocks MySQL database, finds OPEN rows in
at_pick_outcomes that have no resolution (status='OPEN'), joins with
trading_picks to obtain entry_price / direction / TP / SL / created_at,
fetches historical close prices via yfinance, and resolves each pick
as WIN or LOSS.

Resolution logic (mirrors mysql_stale_picks_resolver.py):
  - Fetch yfinance historical OHLCV for the symbol
  - Find the close on the first trading day >= (created_at + hold_period_days)
  - WIN  if close >  entry_price * (1 + WIN_THRESHOLD)
  - LOSS if close <= entry_price * (1 + WIN_THRESHOLD)
  - SHORT direction flips the comparison

Hold period by asset class (same as mysql_stale_picks_resolver.py):
  EQUITY    30 days
  CRYPTO     7 days
  COMMODITY 14 days
  FOREX     14 days
  ETF       20 days
  BOND      30 days
  FUTURES   14 days
  default   30 days

Usage:
    python tools/mysql_resolve_at_pick_outcomes.py --dry-run --max-age-days 30
    python tools/mysql_resolve_at_pick_outcomes.py --apply  --max-age-days 30
    python tools/mysql_resolve_at_pick_outcomes.py --apply  --max-age-days 60 --batch-size 200

Environment variables:
    AUDIT_DB_HOST    (default: mysql.50webs.com)
    AUDIT_DB_USER    (default: ejaguiar1_stocks)
    AUDIT_DB_PASS    (REQUIRED — also checked as DB_PASS_STOCKS, MYSQL_PASSWORD)
    AUDIT_DB_NAME    (default: ejaguiar1_stocks)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import pymysql
except ImportError:
    sys.exit("pymysql not installed — run: pip install pymysql")

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance not installed — run: pip install yfinance")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("at_pick_outcomes_resolver")

# ---------------------------------------------------------------------------
# DB config
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("AUDIT_DB_HOST", os.getenv("DB_HOST", "mysql.50webs.com"))
DB_PORT = int(os.getenv("AUDIT_DB_PORT", os.getenv("DB_PORT", "3306")))
DB_USER = os.getenv("AUDIT_DB_USER", os.getenv("DB_USER", "ejaguiar1_stocks"))
DB_PASS = (
    os.getenv("AUDIT_DB_PASS")
    or os.getenv("DB_PASS_STOCKS")
    or os.getenv("MYSQL_PASSWORD")
    or ""
)
DB_NAME = os.getenv("AUDIT_DB_NAME", os.getenv("DB_NAME", "ejaguiar1_stocks"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIN_THRESHOLD = 0.005  # 0.5% above entry_price → WIN

HOLD_DAYS_BY_CLASS: dict[str, int] = {
    "EQUITY":    30,
    "CRYPTO":     7,
    "COMMODITY": 14,
    "FOREX":     14,
    "ETF":       20,
    "BOND":      30,
    "FUTURES":   14,
}
DEFAULT_HOLD_DAYS = 30

RESOLVER_VERSION = "at_pick_outcomes_v1"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _connect():
    """Open a pymysql connection."""
    if not DB_PASS:
        log.error(
            "No DB password — set AUDIT_DB_PASS, DB_PASS_STOCKS, or MYSQL_PASSWORD"
        )
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=15,
    )


# ---------------------------------------------------------------------------
# yfinance price lookup
# ---------------------------------------------------------------------------

def get_close_on_or_after(symbol: str, target_date: datetime) -> Optional[float]:
    """
    Fetch the close price for `symbol` on the first trading day >= `target_date`.

    Returns None if no price is available (delisted, bad symbol, etc.).
    """
    fetch_start = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
    fetch_end = (target_date + timedelta(days=10)).strftime("%Y-%m-%d")

    # yfinance symbol adjustments for common crypto suffix mismatches
    yf_symbol = symbol
    if "-" not in symbol and symbol.endswith("USDT"):
        yf_symbol = symbol[:-4] + "-USD"
    elif symbol.endswith("USDC"):
        yf_symbol = symbol[:-4] + "-USD"

    try:
        hist = yf.download(
            yf_symbol,
            start=fetch_start,
            end=fetch_end,
            progress=False,
            auto_adjust=True,
        )
    except Exception as exc:
        log.warning("yfinance error for %s: %s", symbol, exc)
        return None

    if hist is None or hist.empty:
        return None

    target_str = target_date.strftime("%Y-%m-%d")
    for idx in hist.index:
        row_date = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        if row_date >= target_str:
            close_val = hist.loc[idx, "Close"]
            if hasattr(close_val, "iloc"):
                close_val = close_val.iloc[0]
            try:
                return float(close_val)
            except (TypeError, ValueError):
                return None

    return None


# ---------------------------------------------------------------------------
# Resolve a single at_pick_outcomes row
# ---------------------------------------------------------------------------

def resolve_at_pick_outcome(pick: dict, trading_pick: Optional[dict]) -> Optional[dict]:
    """
    Attempt to resolve a stale OPEN at_pick_outcomes row.

    Args:
        pick: The at_pick_outcomes row (must have status='OPEN').
        trading_pick: The matching trading_picks row for entry/exit params,
                      or None if not found.

    Returns:
        A resolution dict {pick_id, status, pnl_pct, exit_reason, resolved_at}
        or None if the pick cannot be resolved.
    """
    pick_id: str = pick["pick_id"]
    symbol: str = pick["symbol"]
    asset_class: str = (pick.get("asset_class") or "UNKNOWN").upper()

    # We need trading_picks data for entry_price, direction, TP/SL
    if trading_pick is None:
        log.warning("No matching trading_pick for at_pick_outcomes pick_id=%s — skipping", pick_id)
        return None

    entry_price: float = float(trading_pick.get("entry_price") or 0)
    direction: str = (trading_pick.get("direction") or "LONG").upper()
    created_at_raw = trading_pick.get("created_at")

    if entry_price <= 0:
        log.warning("Pick %s has invalid entry_price %s — skipping", pick_id, entry_price)
        return None

    if not created_at_raw:
        log.warning("Pick %s has no created_at in trading_picks — skipping", pick_id)
        return None

    # Parse created_at (may be datetime or string)
    if isinstance(created_at_raw, datetime):
        created_at = created_at_raw.replace(tzinfo=timezone.utc)
    else:
        created_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))

    hold_days = HOLD_DAYS_BY_CLASS.get(asset_class, DEFAULT_HOLD_DAYS)
    target_date = created_at + timedelta(days=hold_days)

    # Do not resolve picks whose hold period hasn't elapsed yet
    now_utc = datetime.now(timezone.utc)
    if target_date > now_utc:
        log.debug(
            "Pick %s hold period not elapsed (target %s > now %s) — skipping",
            pick_id,
            target_date.date(),
            now_utc.date(),
        )
        return None

    exit_price = get_close_on_or_after(symbol, target_date)
    if exit_price is None:
        log.warning("No price for %s on/after %s — cannot resolve pick %s", symbol, target_date.date(), pick_id)
        return None

    # PnL calculation (direction-aware)
    if direction == "SHORT":
        pnl_pct = (entry_price - exit_price) / entry_price
    else:
        pnl_pct = (exit_price - entry_price) / entry_price

    win_threshold_price = entry_price * (1 + WIN_THRESHOLD)
    if direction == "SHORT":
        is_win = exit_price < entry_price * (1 - WIN_THRESHOLD)
    else:
        is_win = exit_price > win_threshold_price

    status = "WON" if is_win else "LOST"

    return {
        "pick_id": pick_id,
        "symbol": symbol,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl_pct": round(pnl_pct * 100, 4),  # stored as percentage
        "status": status,
        "exit_reason": f"stale_resolver_hold_{hold_days}d",
        "resolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "direction": direction,
        "asset_class": asset_class,
    }


# ---------------------------------------------------------------------------
# Main resolve loop
# ---------------------------------------------------------------------------

def resolve_stale_at_pick_outcomes(
    max_age_days: int = 30,
    batch_size: int = 500,
    dry_run: bool = True,
) -> dict:
    """
    Query MySQL for stale OPEN at_pick_outcomes rows, resolve each using
    trading_picks data + yfinance, and (if not dry_run) update the database.

    Returns summary dict.
    """
    conn = _connect()
    summary = {
        "queried": 0,
        "matched_trading_picks": 0,
        "skipped_no_price": 0,
        "skipped_hold_not_elapsed": 0,
        "skipped_no_trading_pick": 0,
        "win": 0,
        "loss": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    try:
        with conn.cursor() as cur:
            # Fetch stale OPEN at_pick_outcomes rows.
            # Join with trading_picks to get entry_price, direction, created_at.
            # For OPEN rows, resolved_at is NULL, so we join on symbol + strategy
            # and use a time window on created_at (trading_picks) vs resolved_at
            # (at_pick_outcomes).  We also try joining on pick_id as a fallback
            # for rows that have a v1: canonical ID matching trading_picks.id.
            sql = (
                "SELECT po.pick_id, po.symbol, po.asset_class, po.strategy, "
                "       tp.entry_price, tp.direction, tp.created_at, "
                "       tp.take_profit AS tp_price, tp.stop_loss AS sl_price "
                "FROM at_pick_outcomes po "
                "INNER JOIN trading_picks tp "
                "  ON (po.pick_id = tp.id "
                "      OR (po.symbol = tp.symbol "
                "          AND po.strategy = tp.strategy)) "
                "WHERE po.status = 'OPEN' "
                "  AND tp.created_at < NOW() - INTERVAL %s DAY "
                "LIMIT %s"
            )
            cur.execute(sql, (max_age_days, batch_size))
            rows = cur.fetchall()

        summary["queried"] = len(rows)
        log.info("Found %d stale OPEN at_pick_outcomes rows (with trading_picks match)", len(rows))

        resolutions: list[dict] = []

        for row in rows:
            try:
                trading_pick = {
                    "entry_price": row.get("entry_price"),
                    "direction": row.get("direction"),
                    "created_at": row.get("created_at"),
                    "take_profit": row.get("tp_price"),
                    "stop_loss": row.get("sl_price"),
                }
                res = resolve_at_pick_outcome(row, trading_pick)
            except Exception as exc:
                log.error("Error resolving at_pick_outcomes pick_id=%s: %s", row.get("pick_id"), exc)
                summary["errors"] += 1
                continue

            if res is None:
                # Check if it was a hold-not-elapsed skip vs no trading_pick match
                if trading_pick.get("created_at") is None:
                    summary["skipped_no_trading_pick"] += 1
                else:
                    summary["skipped_hold_not_elapsed"] += 1
                continue

            summary["matched_trading_picks"] += 1
            resolutions.append(res)
            verdict = res["status"]
            log.info(
                "Pick %s | %s %s | entry=%.4f exit=%.4f pnl=%.2f%% → %s",
                res["pick_id"],
                res["direction"],
                res["symbol"],
                res["entry_price"],
                res["exit_price"],
                res["pnl_pct"],
                verdict,
            )
            if verdict == "WON":
                summary["win"] += 1
            else:
                summary["loss"] += 1

        if dry_run:
            log.info(
                "[DRY RUN] Would update %d picks: %d WIN, %d LOSS",
                len(resolutions),
                summary["win"],
                summary["loss"],
            )
        else:
            update_sql = (
                "UPDATE at_pick_outcomes "
                "SET status=%s, pnl_pct=%s, "
                "exit_reason=%s, resolved_at=%s "
                "WHERE pick_id=%s"
            )
            updated = 0
            with conn.cursor() as cur:
                for res in resolutions:
                    try:
                        cur.execute(
                            update_sql,
                            (
                                res["status"],
                                res["pnl_pct"],
                                res["exit_reason"],
                                res["resolved_at"],
                                res["pick_id"],
                            ),
                        )
                        updated += 1
                    except Exception as exc:
                        log.error("DB update error for pick_id=%s: %s", res["pick_id"], exc)
                        summary["errors"] += 1

            conn.commit()
            log.info("Committed %d updates to MySQL", updated)

    finally:
        conn.close()

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve stale OPEN rows in at_pick_outcomes using trading_picks + yfinance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be updated (no DB writes)",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="Execute updates in MySQL",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="Resolve OPEN picks whose trading_picks.created_at is older than N days (default: 30)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Max picks to process per run (default: 500)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dry_run = not args.apply

    log.info("=== at_pick_outcomes Stale Resolver ===")
    log.info("Mode: %s | max_age_days=%d | batch_size=%d", "DRY RUN" if dry_run else "APPLY", args.max_age_days, args.batch_size)
    log.info("DB: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)

    summary = resolve_stale_at_pick_outcomes(
        max_age_days=args.max_age_days,
        batch_size=args.batch_size,
        dry_run=dry_run,
    )

    print("\n=== Resolution Summary ===")
    for k, v in summary.items():
        print(f"  {k:30s}: {v}")

    if summary["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
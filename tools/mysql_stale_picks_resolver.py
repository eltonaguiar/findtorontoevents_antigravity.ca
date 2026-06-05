"""
tools/mysql_stale_picks_resolver.py — Resolve stale OPEN picks in MySQL
=========================================================================

Connects to the ejaguiar1_stocks MySQL database, finds OPEN picks older than
N days, fetches historical close prices via yfinance, and resolves each pick
as WIN or LOSS based on the close price at (created_at + hold_period_days).

Resolution logic
----------------
  - Fetch yfinance historical OHLCV for the symbol
  - Find the close on the first trading day >= (created_at + hold_period_days)
  - WIN  if close >  entry_price * (1 + WIN_THRESHOLD_BP / 10000)
  - LOSS if close <= entry_price * (1 + WIN_THRESHOLD_BP / 10000)
  - Updates MySQL: status, exit_price, pnl_pct, exit_reason, resolved_at

Hold period by asset class
--------------------------
  EQUITY    30 days
  CRYPTO    7 days
  COMMODITY 14 days
  FOREX     14 days
  ETF       20 days
  BOND      30 days
  FUTURES   14 days
  default   30 days

Win threshold: 0.5% (50 bps) net of entry — identical to outcome_resolver.py
PNL_WIN_THRESHOLD_BY_CLASS CRYPTO=0.1bp, others=5bp is for live resolution;
stale resolution uses 0.5% to be conservative.

Usage
-----
    python tools/mysql_stale_picks_resolver.py --dry-run --max-age-days 30
    python tools/mysql_stale_picks_resolver.py --apply  --max-age-days 30
    python tools/mysql_stale_picks_resolver.py --apply  --max-age-days 60 --batch-size 200

Environment variables
---------------------
  AUDIT_DB_HOST    (default: mysql.50webs.com)
  AUDIT_DB_USER    (default: ejaguiar1_stocks)
  AUDIT_DB_PASS    (REQUIRED — also checked as DB_PASS_STOCKS, MYSQL_PASSWORD)
  AUDIT_DB_NAME    (default: ejaguiar1_stocks)
  AUDIT_DB_PORT    (default: 3306)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("mysql_stale_resolver")

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
    or os.getenv("AUDIT_DB_PASS")
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

# ---------------------------------------------------------------------------
# Dependencies check
# ---------------------------------------------------------------------------
try:
    import pymysql
except ImportError:
    sys.exit("pymysql not installed — run: pip install pymysql")

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance not installed — run: pip install yfinance")


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
    # Download a generous window to find the target day or next trading day
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
    # Find the row on or after target_date
    for idx in hist.index:
        row_date = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        if row_date >= target_str:
            close_val = hist.loc[idx, "Close"]
            # Handle MultiIndex columns from yfinance v0.2+
            if hasattr(close_val, "iloc"):
                close_val = close_val.iloc[0]
            try:
                return float(close_val)
            except (TypeError, ValueError):
                return None

    return None


# ---------------------------------------------------------------------------
# Resolve a single pick
# ---------------------------------------------------------------------------

def resolve_pick(pick: dict) -> Optional[dict]:
    """
    Attempt to resolve a stale OPEN pick.

    Returns a resolution dict {status, exit_price, pnl_pct, exit_reason} or
    None if the price cannot be fetched.
    """
    symbol: str = pick["symbol"]
    entry_price: float = float(pick.get("entry_price") or 0)
    asset_class: str = (pick.get("asset_class") or "EQUITY").upper()
    direction: str = (pick.get("direction") or "LONG").upper()
    created_at: datetime = pick["created_at"]

    if entry_price <= 0:
        log.warning("Pick %s has invalid entry_price %s — skipping", pick["id"], entry_price)
        return None

    hold_days = HOLD_DAYS_BY_CLASS.get(asset_class, DEFAULT_HOLD_DAYS)
    target_date = created_at + timedelta(days=hold_days)

    # Do not resolve picks whose hold period hasn't elapsed yet
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if target_date > now_utc:
        log.debug(
            "Pick %s hold period not elapsed (target %s > now %s) — skipping",
            pick["id"],
            target_date.date(),
            now_utc.date(),
        )
        return None

    exit_price = get_close_on_or_after(symbol, target_date)
    if exit_price is None:
        log.warning("No price for %s on/after %s — cannot resolve pick %s", symbol, target_date.date(), pick["id"])
        return None

    # PnL calculation (direction-aware)
    if direction == "SHORT":
        pnl_pct = (entry_price - exit_price) / entry_price
    else:
        pnl_pct = (exit_price - entry_price) / entry_price

    # Price-unit-mismatch guard: yfinance occasionally returns exit prices on a
    # different scale than the stored entry (notably FX 4-digit vs 5-digit, or
    # crypto USDT-fraction vs spot). A |pnl| > 5.0 (500%) is the marker.
    # 2026-06-05: caught 2 fake AUD-USD -97% resolutions; ported the cap from
    # tools/backfill_null_pnl.py to the live resolver.
    if abs(pnl_pct) > 5.0:
        log.warning(
            "Pick %s suspected price-unit mismatch (entry=%s exit=%s pnl=%.2f%%) — skipping",
            pick["id"], entry_price, exit_price, pnl_pct * 100)
        return None

    win_threshold_price = entry_price * (1 + WIN_THRESHOLD)
    if direction == "SHORT":
        is_win = exit_price < entry_price * (1 - WIN_THRESHOLD)
    else:
        is_win = exit_price > win_threshold_price

    status = "WIN" if is_win else "LOSS"

    return {
        "id": pick["id"],
        "symbol": symbol,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl_pct": round(pnl_pct * 100, 4),  # stored as percentage
        "status": status,
        "exit_reason": f"stale_resolver_hold_{hold_days}d",
        "resolved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "target_date": target_date.strftime("%Y-%m-%d"),
        "direction": direction,
        "asset_class": asset_class,
    }


# ---------------------------------------------------------------------------
# Main resolve loop
# ---------------------------------------------------------------------------

def resolve_stale_picks(
    max_age_days: int = 30,
    batch_size: int = 500,
    dry_run: bool = True,
) -> dict:
    """
    Query MySQL for stale OPEN picks, resolve each, and (if not dry_run)
    update the database.

    Returns summary dict.
    """
    conn = _connect()
    summary = {
        "queried": 0,
        "skipped_no_price": 0,
        "skipped_hold_not_elapsed": 0,
        "win": 0,
        "loss": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    try:
        with conn.cursor() as cur:
            # 2026-05-25 schema-drift fix (5-peer consensus, see
            # reports/2026-05-25_resolver_pipeline_5peer_consult.md):
            #   asset_class -> category   (trading_picks uses `category`)
            #   tp_price    -> take_profit
            #   sl_price    -> stop_loss
            # Use SQL aliases so the rest of this module keeps its existing
            # dict keys (resolve_pick reads pick["asset_class"] etc.).
            sql = (
                "SELECT id, symbol, category AS asset_class, strategy, direction, "
                "entry_price, created_at, take_profit AS tp_price, "
                "stop_loss AS sl_price "
                "FROM trading_picks "
                "WHERE status = 'OPEN' "
                "AND created_at < NOW() - INTERVAL %s DAY "
                "LIMIT %s"
            )
            cur.execute(sql, (max_age_days, batch_size))
            picks = cur.fetchall()

        summary["queried"] = len(picks)
        log.info("Found %d stale OPEN picks older than %d days", len(picks), max_age_days)

        resolutions: list[dict] = []

        for pick in picks:
            try:
                res = resolve_pick(pick)
            except Exception as exc:
                log.error("Error resolving pick %s: %s", pick.get("id"), exc)
                summary["errors"] += 1
                continue

            if res is None:
                summary["skipped_no_price"] += 1
                continue

            resolutions.append(res)
            verdict = res["status"]
            log.info(
                "Pick %s | %s %s | entry=%.4f exit=%.4f pnl=%.2f%% → %s",
                res["id"],
                res["direction"],
                res["symbol"],
                res["entry_price"],
                res["exit_price"],
                res["pnl_pct"],
                verdict,
            )
            if verdict == "WIN":
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
            # 2026-05-25 schema-drift fix: trading_picks has no `resolved_at`
            # column; the equivalents are `closed_at` (event time) and
            # `updated_at` (row mtime, auto-updated). Write to `closed_at`.
            update_sql = (
                "UPDATE trading_picks "
                "SET status=%s, exit_price=%s, pnl_pct=%s, "
                "exit_reason=%s, closed_at=%s "
                "WHERE id=%s"
            )
            updated = 0
            with conn.cursor() as cur:
                for res in resolutions:
                    try:
                        cur.execute(
                            update_sql,
                            (
                                res["status"],
                                res["exit_price"],
                                res["pnl_pct"],
                                res["exit_reason"],
                                res["resolved_at"],
                                res["id"],
                            ),
                        )
                        updated += 1
                    except Exception as exc:
                        log.error("DB update error for pick %s: %s", res["id"], exc)
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
        description="Resolve stale OPEN picks in MySQL trading_picks table",
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
        help="Resolve OPEN picks created more than N days ago (default: 30)",
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

    log.info("=== MySQL Stale Picks Resolver ===")
    log.info("Mode: %s | max_age_days=%d | batch_size=%d", "DRY RUN" if dry_run else "APPLY", args.max_age_days, args.batch_size)
    log.info("DB: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)

    summary = resolve_stale_picks(
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

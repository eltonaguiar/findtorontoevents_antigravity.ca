"""Enrich active predictions with live market prices.

Most news scrapers extract symbol + direction but not entry_price.
This module backfills entry_price (and reasonable TP/SL defaults)
from live Binance/CoinGecko prices so the predictions are usable
for outcome tracking and scoring.

Runs after all scrapers, before price_validator and consensus engine.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # predictions/
sys.path.insert(0, str(ROOT))
from db import get_db

# Try to import api_failover for price lookups
try:
    sys.path.insert(0, str(ROOT.parent / "alpha_engine"))
    from api_failover import fetch_price
    HAS_PRICE = True
except ImportError:
    HAS_PRICE = False


def _default_tp_sl(entry: float, direction: str, asset_class: str = "crypto"):
    """Compute conservative TP/SL from entry price.

    Uses tight R:R (1.0-1.5) per PEER_INTEL data showing this is the WR sweet spot.
    """
    if direction.upper() == "LONG":
        tp = round(entry * 1.05, 8)  # 5% TP
        sl = round(entry * 0.95, 8)  # 5% SL → R:R = 1.0
    else:
        tp = round(entry * 0.95, 8)
        sl = round(entry * 1.05, 8)
    return tp, sl


def enrich_active_predictions():
    """Backfill entry_price, TP, SL for active predictions missing prices."""
    if not HAS_PRICE:
        print("[enrich] api_failover not available — skipping price enrichment")
        return

    conn = get_db()

    # Find active predictions with no entry_price
    rows = conn.execute("""
        SELECT id, symbol, direction, entry_price, take_profit, stop_loss
        FROM predictions
        WHERE status = 'ACTIVE' AND entry_price IS NULL
        ORDER BY scraped_at DESC
    """).fetchall()

    if not rows:
        print("[enrich] All active predictions already have entry_price")
        conn.close()
        return

    print(f"[enrich] {len(rows)} active predictions need price enrichment")

    # Group by symbol to minimize API calls
    symbols_needed = set()
    for r in rows:
        symbols_needed.add(r["symbol"])

    # Fetch prices (one per symbol)
    price_cache = {}
    for sym in symbols_needed:
        try:
            price = fetch_price(sym)
            if price and price > 0:
                price_cache[sym] = price
        except Exception:
            pass
        time.sleep(0.3)  # gentle rate limiting

    print(f"[enrich] Fetched prices for {len(price_cache)}/{len(symbols_needed)} symbols")

    # Update predictions
    updated = 0
    for r in rows:
        sym = r["symbol"]
        if sym not in price_cache:
            continue

        entry = price_cache[sym]
        direction = r["direction"] or "LONG"
        tp, sl = _default_tp_sl(entry, direction)

        # Only set TP/SL if they're also missing
        update_tp = r["take_profit"] is None
        update_sl = r["stop_loss"] is None

        if update_tp and update_sl:
            conn.execute("""
                UPDATE predictions SET entry_price = ?, take_profit = ?, stop_loss = ?
                WHERE id = ?
            """, (entry, tp, sl, r["id"]))
        elif update_tp:
            conn.execute("""
                UPDATE predictions SET entry_price = ?, take_profit = ?
                WHERE id = ?
            """, (entry, tp, r["id"]))
        elif update_sl:
            conn.execute("""
                UPDATE predictions SET entry_price = ?, stop_loss = ?
                WHERE id = ?
            """, (entry, sl, r["id"]))
        else:
            conn.execute("""
                UPDATE predictions SET entry_price = ?
                WHERE id = ?
            """, (entry, r["id"]))
        updated += 1

    conn.commit()
    conn.close()
    print(f"[enrich] Enriched {updated}/{len(rows)} predictions with live prices")


if __name__ == "__main__":
    enrich_active_predictions()

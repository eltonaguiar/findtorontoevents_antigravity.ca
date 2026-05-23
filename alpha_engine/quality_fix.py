#!/usr/bin/env python3
"""
Quality Fix -- Auto-close SL-hit positions in active_picks.json

Addresses the critical issue:
  5 SL HITS detected but not auto-closed (UNIUSDT x2, DOGEUSDT, OPUSDT x2)

Run this script to:
  1. Fetch live prices
  2. Detect picks past their stop loss
  3. Close them: move to closed_picks.json, remove from active_picks.json
  4. Print a quality health report
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ACTIVE_PICKS_FILE = os.path.join(DATA_DIR, "active_picks.json")
CLOSED_PICKS_FILE = os.path.join(DATA_DIR, "closed_picks.json")

BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://data-api.binance.vision",
]


def fetch_prices():
    """Fetch all Binance spot prices with multi-endpoint fallback."""
    for base in BINANCE_BASES:
        url = f"{base}/api/v3/ticker/price"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return {t["symbol"]: float(t["price"]) for t in data}
        except Exception:
            continue
    return {}


def normalize_symbol(sym):
    """Normalize symbol to Binance USDT format."""
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


def get_price(sym, prices):
    """Try multiple normalizations to find the price."""
    for candidate in [sym, normalize_symbol(sym), sym.replace("-", ""), sym + "USDT"]:
        if candidate in prices:
            return prices[candidate]
    return 0.0


def check_sl_hit(pick, prices):
    """Return True if pick is past its stop loss."""
    direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
    entry = float(pick.get("entry_price", 0) or 0)
    sl = float(pick.get("stop_loss", 0) or 0)
    sym = pick.get("symbol", "")
    current = get_price(sym, prices)

    if entry <= 0 or sl <= 0 or current <= 0:
        return False, current, 0.0

    if direction in ("LONG", "BUY"):
        hit = current <= sl
        pnl_pct = (current - entry) / entry * 100
    else:
        hit = current >= sl
        pnl_pct = (entry - current) / entry * 100

    return hit, current, pnl_pct


def check_tp_hit(pick, prices):
    """Return True if pick is past its take profit."""
    direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", 0) or 0)
    sym = pick.get("symbol", "")
    current = get_price(sym, prices)

    if entry <= 0 or tp <= 0 or current <= 0:
        return False, current, 0.0

    if direction in ("LONG", "BUY"):
        hit = current >= tp
        pnl_pct = (current - entry) / entry * 100
    else:
        hit = current <= tp
        pnl_pct = (entry - current) / entry * 100

    return hit, current, pnl_pct


def main():
    now = datetime.now(timezone.utc)

    print(f"QUALITY FIX -- Auto SL/TP Closer -- {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Load picks
    if not os.path.exists(ACTIVE_PICKS_FILE):
        print(f"[ERROR] {ACTIVE_PICKS_FILE} not found")
        return

    with open(ACTIVE_PICKS_FILE, encoding="utf-8") as f:
        active_picks = json.load(f)

    if not isinstance(active_picks, list):
        print(f"[ERROR] active_picks.json is not a list (got {type(active_picks).__name__})")
        return

    print(f"Loaded {len(active_picks)} active picks")

    # Load closed picks
    closed_picks = []
    if os.path.exists(CLOSED_PICKS_FILE):
        with open(CLOSED_PICKS_FILE, encoding="utf-8") as f:
            existing_closed = json.load(f)
            if isinstance(existing_closed, list):
                closed_picks = existing_closed

    # Fetch prices
    print("Fetching live prices...")
    prices = fetch_prices()
    if not prices:
        print("[ERROR] Failed to fetch prices from all endpoints")
        return
    print(f"  Got {len(prices)} price quotes")

    # Check all picks
    to_close_sl = []
    to_close_tp = []
    remaining = []
    no_price = []

    for pick in active_picks:
        sym = pick.get("symbol", "")
        current = get_price(sym, prices)

        if current <= 0:
            no_price.append(pick)
            remaining.append(pick)
            continue

        sl_hit, current_price, pnl_pct = check_sl_hit(pick, prices)
        tp_hit, _, _ = check_tp_hit(pick, prices)

        if sl_hit:
            to_close_sl.append((pick, current_price, pnl_pct))
        elif tp_hit:
            to_close_tp.append((pick, current_price, pnl_pct))
        else:
            remaining.append(pick)

    # Process SL closes
    print(f"\nSL HITS ({len(to_close_sl)} picks):")
    for pick, current_price, pnl_pct in to_close_sl:
        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        sl = pick.get("stop_loss", 0)
        print(f"  CLOSE SL: {sym} [{strategy}] price={current_price:.6f} sl={sl:.6f} pnl={pnl_pct:+.2f}%")
        pick["close_reason"] = "SL_HIT_AUTO"
        pick["close_price"] = current_price
        pick["close_time"] = now.isoformat()
        pick["close_pnl_pct"] = round(pnl_pct, 4)
        pick["status"] = "closed"
        closed_picks.append(pick)

    # Process TP closes
    print(f"\nTP HITS ({len(to_close_tp)} picks):")
    for pick, current_price, pnl_pct in to_close_tp:
        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        tp = pick.get("take_profit", 0)
        print(f"  CLOSE TP: {sym} [{strategy}] price={current_price:.6f} tp={tp:.6f} pnl={pnl_pct:+.2f}%")
        pick["close_reason"] = "TP_HIT_AUTO"
        pick["close_price"] = current_price
        pick["close_time"] = now.isoformat()
        pick["close_pnl_pct"] = round(pnl_pct, 4)
        pick["status"] = "closed"
        closed_picks.append(pick)

    # No price found
    if no_price:
        print(f"\nNO PRICE ({len(no_price)} picks -- kept open):")
        for pick in no_price:
            print(f"  {pick.get('symbol','')} [{pick.get('strategy','')}]")

    # Summary
    total_closed = len(to_close_sl) + len(to_close_tp)
    print(f"\nSUMMARY:")
    print(f"  Closed (SL): {len(to_close_sl)}")
    print(f"  Closed (TP): {len(to_close_tp)}")
    print(f"  Remaining open: {len(remaining)}")
    print(f"  No price (kept): {len(no_price)}")

    if total_closed == 0:
        print("\n  No changes needed -- all picks within SL/TP bounds")
        return

    # Quality health report
    print(f"\nQUALITY HEALTH (closed picks history):")
    all_closed_with_pnl = [p for p in closed_picks if "close_pnl_pct" in p]
    wins = [p for p in all_closed_with_pnl if p.get("close_pnl_pct", 0) > 0]
    losses = [p for p in all_closed_with_pnl if p.get("close_pnl_pct", 0) <= 0]
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total > 0 else 0
    avg_pnl = sum(p["close_pnl_pct"] for p in all_closed_with_pnl) / len(all_closed_with_pnl) if all_closed_with_pnl else 0
    print(f"  Win Rate: {wr:.1f}% ({len(wins)}W-{len(losses)}L)")
    print(f"  Avg PnL: {avg_pnl:+.2f}%")

    # Save updated files
    with open(ACTIVE_PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(remaining, f, indent=2)

    with open(CLOSED_PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(closed_picks, f, indent=2)

    print(f"\nSaved: {len(remaining)} active, {len(closed_picks)} closed")
    print("Done.")


if __name__ == "__main__":
    main()

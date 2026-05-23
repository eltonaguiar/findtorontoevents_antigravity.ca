#!/usr/bin/env python3
"""
BTCC Live Position Monitor -- REAL MONEY Tracker
=================================================
Fetches live Binance prices and monitors 20x leveraged BTCC positions.
Calculates PnL, distance to TP/SL, liquidation proximity, and alert levels.

Designed for GitHub Actions (every 5 min) + optional Discord alerts.

Usage:
    python live_monitor/position_monitor.py
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LEVERAGE = 20
BINANCE_TICKER_URLS = [
    "https://api.binance.us/api/v3/ticker/price",       # Binance US (no geo-block)
    "https://api.binance.com/api/v3/ticker/price",       # Binance global (451 from US IPs)
    "https://api4.binance.com/api/v3/ticker/price",      # Binance mirror
]
BINANCE_TICKER_URL = BINANCE_TICKER_URLS[0]  # default for individual fetches
BINANCE_24HR_URL = "https://api.binance.us/api/v3/ticker/24hr"

# Alert thresholds
SL_WARNING_PCT = 2.0       # Warn when price within 2% of SL
LIQ_WARNING_PCT = 2.0      # Warn when price within 2% of liquidation
CRITICAL_LIQ_PCT = 1.0     # Critical when within 1% of liquidation

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
STATE_FILE = DATA_DIR / "position_state.json"

# EST timezone for display
EST = timezone(timedelta(hours=-5))

# ---------------------------------------------------------------------------
# Position Definitions -- REAL BTCC 20x Positions
# ---------------------------------------------------------------------------

POSITIONS = [
    {
        "symbol": "AVAXUSDT",
        "side": "LONG",
        "entry": 9.5644,
        "tp": 10.87,
        "sl": 8.88,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
    {
        "symbol": "LINKUSDT",
        "side": "LONG",
        "entry": 8.971,
        "tp": 9.31,
        "sl": 8.52,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
    {
        "symbol": "NEARUSDT",
        "side": "LONG",
        "entry": 1.288,
        "tp": 1.52,
        "sl": 1.08,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
    {
        "symbol": "ADAUSDT",
        "side": "LONG",
        "entry": 0.2600,
        "tp": 0.274,
        "sl": 0.244,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
    {
        "symbol": "BNBUSDT",
        "side": "LONG",
        "entry": 640.37,
        "tp": 724.38,
        "sl": 614.43,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
    {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry": 69738.74,
        "tp": 77666.00,
        "sl": 62517.00,
        "leverage": LEVERAGE,
        "exchange": "BTCC",
    },
]


# ---------------------------------------------------------------------------
# Price fetching with validation
# ---------------------------------------------------------------------------

def fetch_binance_prices(symbols: list[str], max_retries: int = 3) -> dict[str, float]:
    """Fetch live prices from Binance public API with retries and multi-endpoint fallback."""
    import urllib.request
    import ssl

    prices = {}
    ctx = ssl.create_default_context()

    for base_url in BINANCE_TICKER_URLS:
        print(f"  Trying endpoint: {base_url}")
        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(
                    base_url,
                    headers={"User-Agent": "BTCC-Position-Monitor/1.0"},
                )
                with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                    data = json.loads(resp.read().decode())

                ticker_map = {t["symbol"]: float(t["price"]) for t in data}

                for sym in symbols:
                    price = ticker_map.get(sym)
                    if price is None:
                        continue
                    if price <= 0:
                        print(f"  WARNING: {sym} returned zero/negative price: {price}")
                        continue
                    prices[sym] = price

                if len(prices) == len(symbols):
                    return prices

                # Try individual requests for missing symbols
                missing = [s for s in symbols if s not in prices]
                for sym in missing:
                    try:
                        url = f"{base_url}?symbol={sym}"
                        req2 = urllib.request.Request(url, headers={"User-Agent": "BTCC-Position-Monitor/1.0"})
                        with urllib.request.urlopen(req2, timeout=10, context=ctx) as resp2:
                            d = json.loads(resp2.read().decode())
                            p = float(d["price"])
                            if p > 0:
                                prices[sym] = p
                    except Exception:
                        pass

                if prices:
                    return prices

            except Exception as e:
                print(f"  Attempt {attempt}/{max_retries} on {base_url} failed: {e}")
                if attempt < max_retries:
                    time.sleep(1)

        if prices:
            return prices

    return prices


def validate_price(symbol: str, price: float, entry: float) -> tuple[bool, str]:
    """Validate that a fetched price is reasonable (not stale/corrupt)."""
    if price <= 0:
        return False, f"Price is zero or negative: {price}"

    # Check for extreme deviation (>90% from entry = likely bad data)
    deviation = abs(price - entry) / entry * 100
    if deviation > 90:
        return False, f"Price {price} deviates {deviation:.1f}% from entry {entry} -- possibly stale/corrupt"

    return True, "OK"


# ---------------------------------------------------------------------------
# PnL and risk calculations
# ---------------------------------------------------------------------------

def calc_pnl_pct(entry: float, current: float, leverage: int, side: str) -> float:
    """Calculate leveraged PnL percentage."""
    if side == "LONG":
        return ((current - entry) / entry) * leverage * 100
    else:
        return ((entry - current) / entry) * leverage * 100


def calc_liquidation_price(entry: float, leverage: int, side: str) -> float:
    """
    Estimate liquidation price.
    For isolated margin at Lx leverage:
      LONG:  liq = entry * (1 - 1/leverage) -- simplified, ignores fees/maintenance margin
      SHORT: liq = entry * (1 + 1/leverage)
    With maintenance margin (~0.5%), actual liq is slightly better.
    We use conservative estimate (without maintenance buffer).
    """
    if side == "LONG":
        return entry * (1 - 1 / leverage)
    else:
        return entry * (1 + 1 / leverage)


def distance_pct(current: float, target: float) -> float:
    """Percentage distance from current to target."""
    if current == 0:
        return 0
    return ((target - current) / current) * 100


def determine_alert_level(
    current: float,
    entry: float,
    sl: float,
    liq_price: float,
    side: str,
) -> tuple[str, str]:
    """
    Determine alert level and color.
    Returns (level, color_code).
    """
    # Distance from current price to SL and liquidation
    if side == "LONG":
        dist_to_sl = ((current - sl) / current) * 100 if current > 0 else 0
        dist_to_liq = ((current - liq_price) / current) * 100 if current > 0 else 0
        price_vs_entry = current >= entry
    else:
        dist_to_sl = ((sl - current) / current) * 100 if current > 0 else 0
        dist_to_liq = ((liq_price - current) / current) * 100 if current > 0 else 0
        price_vs_entry = current <= entry

    # CRITICAL: near liquidation
    if dist_to_liq <= CRITICAL_LIQ_PCT:
        return "CRITICAL", "\033[1;35m"  # Bold magenta

    # CRITICAL: price already past liquidation
    if dist_to_liq < 0:
        return "LIQUIDATED", "\033[1;31m"  # Bold red

    # RED: near liquidation or past SL
    if dist_to_liq <= LIQ_WARNING_PCT or dist_to_sl < 0:
        return "RED", "\033[91m"

    # RED: approaching SL
    if dist_to_sl <= SL_WARNING_PCT:
        return "RED", "\033[91m"

    # YELLOW: losing but not near SL
    if not price_vs_entry:
        pnl_spot = abs(current - entry) / entry * 100
        if pnl_spot > 1.0:
            return "YELLOW", "\033[93m"

    # GREEN: in profit or very close to entry
    if price_vs_entry:
        return "GREEN", "\033[92m"

    return "YELLOW", "\033[93m"


# ---------------------------------------------------------------------------
# Discord notification
# ---------------------------------------------------------------------------

def send_discord_alert(positions_data: list[dict], webhook_url: str) -> bool:
    """Send position status to Discord webhook."""
    import urllib.request

    now_est = datetime.now(EST).strftime("%Y-%m-%d %H:%M EST")

    # Build summary
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in positions_data) / len(positions_data) if positions_data else 0
    critical = [p for p in positions_data if p.get("alert_level") in ("CRITICAL", "RED")]

    color = 0x22c55e  # green
    if critical:
        color = 0xff0000  # red
    elif total_pnl < 0:
        color = 0xffa500  # orange

    # Emoji map
    level_emoji = {
        "GREEN": ":green_circle:",
        "YELLOW": ":yellow_circle:",
        "RED": ":red_circle:",
        "CRITICAL": ":rotating_light:",
        "LIQUIDATED": ":skull:",
    }

    fields = []
    for p in positions_data:
        emoji = level_emoji.get(p["alert_level"], ":white_circle:")
        pnl = p["pnl_pct"]
        sign = "+" if pnl >= 0 else ""

        val = (
            f"{emoji} **{sign}{pnl:.2f}%** PnL\n"
            f"Price: `${p['current_price']:,.4f}`\n"
            f"TP: {p['dist_to_tp']:+.2f}% | SL: {p['dist_to_sl']:+.2f}%\n"
            f"Liq: {p['dist_to_liq']:+.2f}%"
        )

        fields.append({
            "name": f"{p['symbol']} {p['side']} 20x",
            "value": val,
            "inline": True,
        })

    # Portfolio summary field
    winners = sum(1 for p in positions_data if p["pnl_pct"] > 0)
    losers = len(positions_data) - winners
    avg_sign = "+" if total_pnl >= 0 else ""

    fields.append({
        "name": "Portfolio Summary",
        "value": (
            f"Avg PnL: **{avg_sign}{total_pnl:.2f}%**\n"
            f"Winners: {winners} | Losers: {losers}\n"
            f"Positions: {len(positions_data)} active"
        ),
        "inline": False,
    })

    embed = {
        "title": ":chart_with_upwards_trend: BTCC Live Position Monitor",
        "description": f"Real-money 20x leveraged positions\n{now_est}",
        "color": color,
        "fields": fields,
        "footer": {"text": "BTCC Position Monitor | Prices via Binance"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = json.dumps({"embeds": [embed]}).encode()

    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                print("Discord alert sent successfully")
                return True
            else:
                print(f"Discord returned status {resp.status}")
                return False
    except Exception as e:
        print(f"Discord alert failed: {e}")
        return False


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_previous_state() -> dict:
    """Load previous position state for comparison."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(positions_data: list[dict], metadata: dict) -> None:
    """Save current state to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_updated_est": datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S EST"),
        "metadata": metadata,
        "positions": positions_data,
    }

    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    print(f"\nState saved to {STATE_FILE}")


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

def print_table(positions_data: list[dict]) -> None:
    """Print a clean monitoring table to stdout."""
    now_est = datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S EST")

    print()
    print(f"{BOLD}{'=' * 100}{RESET}")
    print(f"{BOLD}  BTCC LIVE POSITION MONITOR -- 20x LEVERAGE -- REAL MONEY{RESET}")
    print(f"{DIM}  {now_est}{RESET}")
    print(f"{BOLD}{'=' * 100}{RESET}")
    print()

    # Header
    header = (
        f"  {'Symbol':<12} {'Side':<6} {'Entry':>12} {'Current':>12} "
        f"{'PnL%':>10} {'To TP':>8} {'To SL':>8} {'To Liq':>8} {'Status':<10}"
    )
    print(f"{BOLD}{header}{RESET}")
    print(f"  {'-' * 96}")

    total_pnl = 0.0
    alerts = []

    for p in positions_data:
        pnl = p["pnl_pct"]
        total_pnl += pnl
        level = p["alert_level"]
        color = p.get("_color", "")

        sign = "+" if pnl >= 0 else ""
        tp_sign = "+" if p["dist_to_tp"] >= 0 else ""
        sl_sign = "+" if p["dist_to_sl"] >= 0 else ""
        liq_sign = "+" if p["dist_to_liq"] >= 0 else ""

        # Format entry/current with appropriate decimals
        entry_str = f"${p['entry']:,.4f}" if p['entry'] < 100 else f"${p['entry']:,.2f}"
        curr_str = f"${p['current_price']:,.4f}" if p['current_price'] < 100 else f"${p['current_price']:,.2f}"

        row = (
            f"  {p['symbol']:<12} {p['side']:<6} {entry_str:>12} {curr_str:>12} "
            f"{color}{sign}{pnl:>8.2f}%{RESET} "
            f"{tp_sign}{p['dist_to_tp']:>6.2f}% "
            f"{sl_sign}{p['dist_to_sl']:>6.2f}% "
            f"{liq_sign}{p['dist_to_liq']:>6.2f}% "
            f"{color}{level:<10}{RESET}"
        )
        print(row)

        # Collect alerts
        if level in ("CRITICAL", "RED", "LIQUIDATED"):
            alerts.append(p)

    avg_pnl = total_pnl / len(positions_data) if positions_data else 0
    print(f"  {'-' * 96}")
    avg_sign = "+" if avg_pnl >= 0 else ""
    print(f"  {'PORTFOLIO AVG':<12} {'':6} {'':>12} {'':>12} {BOLD}{avg_sign}{avg_pnl:>8.2f}%{RESET}")
    print()

    # Liquidation reference
    print(f"{DIM}  Liquidation Prices (estimated, isolated margin):{RESET}")
    for p in positions_data:
        liq_str = f"${p['liq_price']:,.4f}" if p['liq_price'] < 100 else f"${p['liq_price']:,.2f}"
        print(f"{DIM}    {p['symbol']}: {liq_str}{RESET}")
    print()

    # Alerts section
    if alerts:
        print(f"\033[91m{BOLD}  {'!' * 60}{RESET}")
        print(f"\033[91m{BOLD}  ALERTS -- IMMEDIATE ATTENTION REQUIRED{RESET}")
        print(f"\033[91m{BOLD}  {'!' * 60}{RESET}")
        for a in alerts:
            level = a["alert_level"]
            if level == "CRITICAL":
                print(f"\033[1;35m  >>> {a['symbol']}: NEAR LIQUIDATION! Price ${a['current_price']:,.4f} "
                      f"is {a['dist_to_liq']:.2f}% from liq ${a['liq_price']:,.4f}{RESET}")
            elif level == "LIQUIDATED":
                print(f"\033[1;31m  >>> {a['symbol']}: POSITION LIKELY LIQUIDATED! "
                      f"Price ${a['current_price']:,.4f} past liq ${a['liq_price']:,.4f}{RESET}")
            elif level == "RED":
                print(f"\033[91m  >>> {a['symbol']}: APPROACHING STOP LOSS! Price ${a['current_price']:,.4f} "
                      f"is {a['dist_to_sl']:.2f}% from SL ${a['sl']:,.4f}{RESET}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    """Main monitoring loop. Returns exit code."""
    print("Fetching live prices from Binance...")

    symbols = [p["symbol"] for p in POSITIONS]
    prices = fetch_binance_prices(symbols)

    if not prices:
        print("FATAL: Could not fetch any prices from Binance!")
        return 1

    missing = [s for s in symbols if s not in prices]
    if missing:
        print(f"WARNING: Missing prices for: {', '.join(missing)}")

    # Load previous state for comparison
    prev_state = load_previous_state()
    prev_positions = {}
    if prev_state.get("positions"):
        for pp in prev_state["positions"]:
            prev_positions[pp["symbol"]] = pp

    positions_data = []
    has_critical = False
    price_errors = []

    for pos in POSITIONS:
        sym = pos["symbol"]
        entry = pos["entry"]
        tp = pos["tp"]
        sl = pos["sl"]
        side = pos["side"]
        lev = pos["leverage"]

        current = prices.get(sym)
        if current is None:
            price_errors.append(f"{sym}: no price available")
            continue

        # Validate price
        valid, reason = validate_price(sym, current, entry)
        if not valid:
            price_errors.append(f"{sym}: {reason}")
            # Still include with warning
            print(f"  PRICE WARNING for {sym}: {reason}")

        # Calculations
        pnl_pct = calc_pnl_pct(entry, current, lev, side)
        liq_price = calc_liquidation_price(entry, lev, side)
        dist_to_tp = distance_pct(current, tp)
        dist_to_sl = distance_pct(current, sl)
        dist_to_liq = distance_pct(current, liq_price)

        # For LONG: dist_to_sl should be positive when above SL (safe)
        # dist_to_liq should be positive when above liquidation (safe)
        alert_level, color_code = determine_alert_level(current, entry, sl, liq_price, side)

        if alert_level in ("CRITICAL", "LIQUIDATED"):
            has_critical = True

        # Previous comparison
        prev = prev_positions.get(sym, {})
        prev_pnl = prev.get("pnl_pct", 0)
        pnl_change = pnl_pct - prev_pnl

        pos_data = {
            "symbol": sym,
            "side": side,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "leverage": lev,
            "exchange": pos["exchange"],
            "current_price": current,
            "pnl_pct": round(pnl_pct, 4),
            "pnl_change_since_last": round(pnl_change, 4),
            "liq_price": round(liq_price, 6),
            "dist_to_tp": round(dist_to_tp, 4),
            "dist_to_sl": round(dist_to_sl, 4),
            "dist_to_liq": round(dist_to_liq, 4),
            "alert_level": alert_level,
            "_color": color_code,  # transient, not saved
        }

        positions_data.append(pos_data)

    if price_errors:
        print(f"\nPrice errors ({len(price_errors)}):")
        for e in price_errors:
            print(f"  - {e}")

    # Print table
    print_table(positions_data)

    # Clean transient fields before saving
    for p in positions_data:
        p.pop("_color", None)

    # Save state
    metadata = {
        "total_positions": len(positions_data),
        "price_errors": len(price_errors),
        "has_critical_alerts": has_critical,
        "avg_pnl_pct": round(
            sum(p["pnl_pct"] for p in positions_data) / len(positions_data), 4
        ) if positions_data else 0,
        "winners": sum(1 for p in positions_data if p["pnl_pct"] > 0),
        "losers": sum(1 for p in positions_data if p["pnl_pct"] <= 0),
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_state(positions_data, metadata)

    # Discord alerts (only on critical/red or every 6 hours as heartbeat)
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_POSITIONS")
    if webhook_url:
        should_send = False

        # Always send on critical
        if has_critical:
            should_send = True
            print("Sending Discord alert: CRITICAL positions detected")

        # Send if any position crossed SL since last check
        for p in positions_data:
            prev = prev_positions.get(p["symbol"], {})
            if prev.get("alert_level") != "RED" and p["alert_level"] in ("RED", "CRITICAL"):
                should_send = True
                print(f"Sending Discord alert: {p['symbol']} escalated to {p['alert_level']}")

        # Heartbeat: send every ~6 hours (every 72nd run at 5-min intervals)
        run_count = prev_state.get("metadata", {}).get("_run_count", 0) + 1
        metadata["_run_count"] = run_count
        if run_count % 72 == 1:  # First run and every 6 hours
            should_send = True
            print("Sending Discord heartbeat alert")

        if should_send:
            send_discord_alert(positions_data, webhook_url)
    else:
        print("No Discord webhook configured (set DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_POSITIONS)")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

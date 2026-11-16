#!/usr/bin/env python3
"""
Binance Contrarian Signals — crowd positioning analysis from free public APIs.

Fetches long/short ratios, taker volume, top trader positioning, open interest,
and Coinbase premium to generate contrarian trading signals.

All endpoints are public (no API key required).

Signals:
  - crowd_contrarian: Fade the retail crowd when overleveraged
  - taker_momentum: Sustained buy/sell pressure detection
  - smart_money_divergence: Top traders vs retail divergence
  - oi_squeeze: OI building with flat price = squeeze incoming
  - coinbase_premium: US institutional flow via Coinbase price gap
  - composite: Majority vote with strength [-1, +1]
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
SNAPSHOT_FILE = os.path.join(DATA_DIR, "binance_contrarian_snapshot.json")

TIMEOUT = 10
USER_AGENT = "Battleground-Contrarian/1.0"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "NEARUSDT"]

# Coinbase mapping: Binance symbol -> Coinbase product ID
COINBASE_MAP = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "SOLUSDT": "SOL-USD",
    "XRPUSDT": "XRP-USD",
}

# ─── Thresholds ───────────────────────────────────────────────────────────────

CROWD_LONG_THRESHOLD = 1.5      # Crowd overleveraged long -> SHORT signal
CROWD_SHORT_THRESHOLD = 0.67    # Crowd overleveraged short -> LONG signal
TAKER_BULL_THRESHOLD = 1.2      # Sustained buying
TAKER_BEAR_THRESHOLD = 0.8      # Sustained selling
TAKER_SUSTAINED_PERIODS = 3     # Consecutive periods required
SMART_DIVERGENCE_MIN = 0.15     # Min divergence between top vs retail
OI_RISE_PCT = 10.0              # OI rise threshold (%) over 6 periods
OI_PRICE_FLAT_PCT = 1.0         # Price considered "flat" if < 1% change
PREMIUM_THRESHOLD = 0.3         # Coinbase premium threshold (%)


# ─── HTTP Helper ──────────────────────────────────────────────────────────────

_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]


def _fetch_json(url, timeout=TIMEOUT):
    """Fetch JSON with error handling, rate-limit awareness, and endpoint failover."""
    # Build failover URL list if hitting known Binance endpoints
    urls_to_try = [url]
    if "fapi.binance.com" in url:
        for fbase in _FAPI_BASES:
            alt = url.replace("https://fapi.binance.com", fbase)
            if alt != url and alt not in urls_to_try:
                urls_to_try.append(alt)
    elif "api.binance.com" in url:
        for sbase in _SPOT_BASES:
            alt = url.replace("https://api.binance.com", sbase)
            if alt != url and alt not in urls_to_try:
                urls_to_try.append(alt)

    for try_url in urls_to_try:
        try:
            req = Request(try_url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next endpoint
            return {"error": f"HTTP {e.code}: {e.reason}", "url": try_url}
        except URLError as e:
            continue
        except Exception as e:
            continue
    return {"error": "all endpoints failed", "url": url}


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ─── Data Fetchers ────────────────────────────────────────────────────────────

def fetch_long_short_ratio(symbol, period="1h", limit=30):
    """Global long/short account ratio."""
    url = (
        f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    data = _fetch_json(url)
    if isinstance(data, list):
        return [
            {
                "timestamp": int(d.get("timestamp", 0)),
                "longAccount": _safe_float(d.get("longAccount")),
                "shortAccount": _safe_float(d.get("shortAccount")),
                "longShortRatio": _safe_float(d.get("longShortRatio")),
            }
            for d in data
        ]
    return []


def fetch_taker_volume(symbol, period="1h", limit=30):
    """Taker buy/sell volume ratio."""
    url = (
        f"https://fapi.binance.com/futures/data/takerlongshortRatio"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    data = _fetch_json(url)
    if isinstance(data, list):
        return [
            {
                "timestamp": int(d.get("timestamp", 0)),
                "buySellRatio": _safe_float(d.get("buySellRatio")),
                "buyVol": _safe_float(d.get("buyVol")),
                "sellVol": _safe_float(d.get("sellVol")),
            }
            for d in data
        ]
    return []


def fetch_top_trader_ratio(symbol, period="1h", limit=30):
    """Top trader long/short position ratio."""
    url = (
        f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    data = _fetch_json(url)
    if isinstance(data, list):
        return [
            {
                "timestamp": int(d.get("timestamp", 0)),
                "longAccount": _safe_float(d.get("longAccount")),
                "shortAccount": _safe_float(d.get("shortAccount")),
                "longShortRatio": _safe_float(d.get("longShortRatio")),
            }
            for d in data
        ]
    return []


def fetch_open_interest_hist(symbol, period="1h", limit=30):
    """Open interest history."""
    url = (
        f"https://fapi.binance.com/futures/data/openInterestHist"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    data = _fetch_json(url)
    if isinstance(data, list):
        return [
            {
                "timestamp": int(d.get("timestamp", 0)),
                "sumOpenInterest": _safe_float(d.get("sumOpenInterest")),
                "sumOpenInterestValue": _safe_float(d.get("sumOpenInterestValue")),
            }
            for d in data
        ]
    return []


def fetch_coinbase_premium(symbol):
    """Compute Coinbase premium vs Binance spot price."""
    coinbase_product = COINBASE_MAP.get(symbol)
    if not coinbase_product:
        return {"premium_pct": 0.0, "error": "no Coinbase mapping"}

    binance_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    coinbase_url = f"https://api.exchange.coinbase.com/products/{coinbase_product}/ticker"

    binance_data = _fetch_json(binance_url)
    coinbase_data = _fetch_json(coinbase_url)

    if "error" in binance_data or "error" in coinbase_data:
        return {
            "premium_pct": 0.0,
            "binance_price": 0.0,
            "coinbase_price": 0.0,
            "error": binance_data.get("error", "") or coinbase_data.get("error", ""),
        }

    b_price = _safe_float(binance_data.get("price"))
    c_price = _safe_float(coinbase_data.get("price"))

    if b_price <= 0:
        return {"premium_pct": 0.0, "binance_price": 0.0, "coinbase_price": c_price, "error": "bad binance price"}

    premium = (c_price - b_price) / b_price * 100.0
    return {
        "premium_pct": round(premium, 4),
        "binance_price": b_price,
        "coinbase_price": c_price,
    }


def fetch_current_price(symbol):
    """Get current Binance spot price for a symbol."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    data = _fetch_json(url)
    return _safe_float(data.get("price")) if not isinstance(data, list) and "error" not in data else 0.0


# ─── Signal Generators ────────────────────────────────────────────────────────

def signal_crowd_contrarian(ls_data):
    """
    When longShortRatio > 1.5 (crowd overleveraged long) = SHORT signal.
    When longShortRatio < 0.67 (crowd overleveraged short) = LONG signal.
    Uses the most recent data point.
    """
    if not ls_data:
        return {"signal": "neutral", "strength": 0.0, "ratio": None, "reason": "no data"}

    latest = ls_data[-1]
    ratio = latest["longShortRatio"]

    if ratio > CROWD_LONG_THRESHOLD:
        # Crowd is overleveraged long -> contrarian SHORT
        strength = min((ratio - CROWD_LONG_THRESHOLD) / CROWD_LONG_THRESHOLD, 1.0)
        return {
            "signal": "SHORT",
            "strength": round(-strength, 3),
            "ratio": round(ratio, 4),
            "reason": f"Crowd overleveraged long (L/S={ratio:.2f} > {CROWD_LONG_THRESHOLD})",
        }
    elif ratio < CROWD_SHORT_THRESHOLD:
        # Crowd is overleveraged short -> contrarian LONG
        strength = min((CROWD_SHORT_THRESHOLD - ratio) / CROWD_SHORT_THRESHOLD, 1.0)
        return {
            "signal": "LONG",
            "strength": round(strength, 3),
            "ratio": round(ratio, 4),
            "reason": f"Crowd overleveraged short (L/S={ratio:.2f} < {CROWD_SHORT_THRESHOLD})",
        }
    else:
        return {
            "signal": "neutral",
            "strength": 0.0,
            "ratio": round(ratio, 4),
            "reason": f"Crowd balanced (L/S={ratio:.2f})",
        }


def signal_taker_momentum(taker_data):
    """
    buySellRatio < 0.8 sustained (3+ periods) = bearish.
    buySellRatio > 1.2 sustained (3+ periods) = bullish.
    """
    if len(taker_data) < TAKER_SUSTAINED_PERIODS:
        return {"signal": "neutral", "strength": 0.0, "ratio": None, "reason": "insufficient data"}

    recent = taker_data[-TAKER_SUSTAINED_PERIODS:]
    ratios = [d["buySellRatio"] for d in recent]
    avg_ratio = sum(ratios) / len(ratios)

    all_bullish = all(r > TAKER_BULL_THRESHOLD for r in ratios)
    all_bearish = all(r < TAKER_BEAR_THRESHOLD for r in ratios)

    if all_bullish:
        strength = min((avg_ratio - TAKER_BULL_THRESHOLD) / TAKER_BULL_THRESHOLD, 1.0)
        return {
            "signal": "LONG",
            "strength": round(strength, 3),
            "ratio": round(avg_ratio, 4),
            "sustained_periods": TAKER_SUSTAINED_PERIODS,
            "reason": f"Sustained taker buying ({TAKER_SUSTAINED_PERIODS}p avg={avg_ratio:.2f})",
        }
    elif all_bearish:
        strength = min((TAKER_BEAR_THRESHOLD - avg_ratio) / TAKER_BEAR_THRESHOLD, 1.0)
        return {
            "signal": "SHORT",
            "strength": round(-strength, 3),
            "ratio": round(avg_ratio, 4),
            "sustained_periods": TAKER_SUSTAINED_PERIODS,
            "reason": f"Sustained taker selling ({TAKER_SUSTAINED_PERIODS}p avg={avg_ratio:.2f})",
        }
    else:
        return {
            "signal": "neutral",
            "strength": 0.0,
            "ratio": round(avg_ratio, 4),
            "reason": f"Mixed taker flow (avg={avg_ratio:.2f})",
        }


def signal_smart_money_divergence(retail_data, top_data):
    """
    When top trader ratio diverges from retail ratio by > 0.15, follow top traders.
    """
    if not retail_data or not top_data:
        return {"signal": "neutral", "strength": 0.0, "reason": "no data"}

    retail_ratio = retail_data[-1]["longShortRatio"]
    top_ratio = top_data[-1]["longShortRatio"]
    divergence = top_ratio - retail_ratio

    if abs(divergence) < SMART_DIVERGENCE_MIN:
        return {
            "signal": "neutral",
            "strength": 0.0,
            "retail_ratio": round(retail_ratio, 4),
            "top_ratio": round(top_ratio, 4),
            "divergence": round(divergence, 4),
            "reason": f"No divergence (diff={divergence:.3f})",
        }

    # Follow top traders
    if divergence > 0:
        # Top traders more long than retail -> LONG
        strength = min(divergence / 0.5, 1.0)
        return {
            "signal": "LONG",
            "strength": round(strength, 3),
            "retail_ratio": round(retail_ratio, 4),
            "top_ratio": round(top_ratio, 4),
            "divergence": round(divergence, 4),
            "reason": f"Smart money more bullish than retail (top={top_ratio:.2f} vs retail={retail_ratio:.2f})",
        }
    else:
        # Top traders more short than retail -> SHORT
        strength = min(abs(divergence) / 0.5, 1.0)
        return {
            "signal": "SHORT",
            "strength": round(-strength, 3),
            "retail_ratio": round(retail_ratio, 4),
            "top_ratio": round(top_ratio, 4),
            "divergence": round(divergence, 4),
            "reason": f"Smart money more bearish than retail (top={top_ratio:.2f} vs retail={retail_ratio:.2f})",
        }


def signal_oi_squeeze(oi_data, symbol):
    """
    OI rising > 10% in 6 periods while price stays flat (< 1% change) = squeeze building.
    """
    if len(oi_data) < 6:
        return {"signal": "neutral", "strength": 0.0, "reason": "insufficient OI data"}

    # Compare first vs last of last 6 periods
    oi_start = oi_data[-6]["sumOpenInterestValue"]
    oi_end = oi_data[-1]["sumOpenInterestValue"]

    if oi_start <= 0:
        return {"signal": "neutral", "strength": 0.0, "reason": "bad OI data"}

    oi_change_pct = (oi_end - oi_start) / oi_start * 100.0

    # Get current price for price-change check
    # We use OI value / OI quantity as a rough price proxy if available
    price_start = oi_data[-6].get("sumOpenInterestValue", 0) / max(oi_data[-6].get("sumOpenInterest", 1), 1)
    price_end = oi_data[-1].get("sumOpenInterestValue", 0) / max(oi_data[-1].get("sumOpenInterest", 1), 1)

    if price_start <= 0:
        return {"signal": "neutral", "strength": 0.0, "reason": "cannot compute price proxy"}

    price_change_pct = abs((price_end - price_start) / price_start * 100.0)

    if oi_change_pct > OI_RISE_PCT and price_change_pct < OI_PRICE_FLAT_PCT:
        strength = min(oi_change_pct / (OI_RISE_PCT * 3), 1.0)
        return {
            "signal": "SQUEEZE",
            "strength": round(strength, 3),
            "oi_change_pct": round(oi_change_pct, 2),
            "price_change_pct": round(price_change_pct, 2),
            "reason": f"OI +{oi_change_pct:.1f}% with price flat ({price_change_pct:.1f}%) — squeeze building",
        }
    else:
        return {
            "signal": "neutral",
            "strength": 0.0,
            "oi_change_pct": round(oi_change_pct, 2),
            "price_change_pct": round(price_change_pct, 2),
            "reason": f"OI {oi_change_pct:+.1f}%, price {price_change_pct:.1f}% — no squeeze",
        }


def signal_coinbase_premium(premium_data):
    """
    Premium > 0.3% = US institutional buying (bullish).
    Discount > 0.3% = US institutional selling (bearish).
    """
    prem = premium_data.get("premium_pct", 0.0)

    if premium_data.get("error"):
        return {
            "signal": "neutral",
            "strength": 0.0,
            "premium_pct": prem,
            "reason": f"Data error: {premium_data['error']}",
        }

    if prem > PREMIUM_THRESHOLD:
        strength = min(prem / 1.0, 1.0)
        return {
            "signal": "LONG",
            "strength": round(strength, 3),
            "premium_pct": round(prem, 4),
            "reason": f"Coinbase premium +{prem:.3f}% — US institutional buying",
        }
    elif prem < -PREMIUM_THRESHOLD:
        strength = min(abs(prem) / 1.0, 1.0)
        return {
            "signal": "SHORT",
            "strength": round(-strength, 3),
            "premium_pct": round(prem, 4),
            "reason": f"Coinbase discount {prem:.3f}% — US institutional selling",
        }
    else:
        return {
            "signal": "neutral",
            "strength": 0.0,
            "premium_pct": round(prem, 4),
            "reason": f"Coinbase premium neutral ({prem:.3f}%)",
        }


def compute_composite(signals_dict):
    """
    Majority vote of all signals. Strength is average of non-zero strengths, range [-1, +1].
    """
    votes = {"LONG": 0, "SHORT": 0, "neutral": 0, "SQUEEZE": 0}
    strengths = []

    for name, sig in signals_dict.items():
        direction = sig.get("signal", "neutral")
        strength = sig.get("strength", 0.0)

        if direction in votes:
            votes[direction] += 1
        else:
            votes["neutral"] += 1

        if strength != 0.0:
            strengths.append(strength)

    # SQUEEZE counts as directional uncertainty (neither bull nor bear)
    long_votes = votes["LONG"]
    short_votes = votes["SHORT"]
    total_directional = long_votes + short_votes

    if total_directional == 0:
        avg_strength = 0.0
        direction = "neutral"
    elif long_votes > short_votes:
        avg_strength = sum(s for s in strengths if s > 0) / max(long_votes, 1)
        direction = "LONG"
    elif short_votes > long_votes:
        avg_strength = sum(s for s in strengths if s < 0) / max(short_votes, 1)
        direction = "SHORT"
    else:
        # Tie — use net strength
        avg_strength = sum(strengths) / len(strengths) if strengths else 0.0
        direction = "LONG" if avg_strength > 0 else "SHORT" if avg_strength < 0 else "neutral"

    squeeze_warning = votes["SQUEEZE"] > 0

    return {
        "signal": direction,
        "strength": round(avg_strength, 3),
        "votes": votes,
        "squeeze_warning": squeeze_warning,
        "reason": f"{direction} ({long_votes}L/{short_votes}S/{votes['neutral']}N"
                  + (f", SQUEEZE WARNING" if squeeze_warning else "") + ")",
    }


# ─── Main Scanner ─────────────────────────────────────────────────────────────

def scan_symbol(symbol):
    """Run all signal generators for a single symbol."""
    print(f"  Fetching {symbol}...", end=" ", flush=True)

    # Fetch all data with small delays to avoid rate limits
    ls_data = fetch_long_short_ratio(symbol)
    time.sleep(0.1)
    taker_data = fetch_taker_volume(symbol)
    time.sleep(0.1)
    top_data = fetch_top_trader_ratio(symbol)
    time.sleep(0.1)
    oi_data = fetch_open_interest_hist(symbol)
    time.sleep(0.1)
    premium_data = fetch_coinbase_premium(symbol)

    # Generate signals
    signals = {
        "crowd_contrarian": signal_crowd_contrarian(ls_data),
        "taker_momentum": signal_taker_momentum(taker_data),
        "smart_money_divergence": signal_smart_money_divergence(ls_data, top_data),
        "oi_squeeze": signal_oi_squeeze(oi_data, symbol),
        "coinbase_premium": signal_coinbase_premium(premium_data),
    }

    # Composite
    signals["composite"] = compute_composite(signals)

    # Metadata
    current_price = fetch_current_price(symbol)

    print("done")

    return {
        "symbol": symbol,
        "price": current_price,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "raw_snapshot": {
            "long_short_ratio_latest": ls_data[-1] if ls_data else None,
            "taker_latest": taker_data[-1] if taker_data else None,
            "top_trader_latest": top_data[-1] if top_data else None,
            "oi_latest": oi_data[-1] if oi_data else None,
            "coinbase_premium": premium_data,
        },
    }


def run_full_scan():
    """Scan all symbols and return results."""
    print("=" * 70)
    print("  BINANCE CONTRARIAN SIGNALS — Crowd Positioning Analysis")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)
    print()

    results = {}
    for symbol in SYMBOLS:
        results[symbol] = scan_symbol(symbol)
        time.sleep(0.2)  # Rate limit courtesy

    # Save snapshot
    os.makedirs(DATA_DIR, exist_ok=True)
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": results,
    }
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"\n  Snapshot saved: {SNAPSHOT_FILE}")

    return results


def print_summary(results):
    """Print a formatted summary table."""
    print()
    print("=" * 100)
    print(f"  {'SYMBOL':<10} {'PRICE':>12} {'COMPOSITE':>10} {'STR':>6}"
          f"  {'CROWD':>8} {'TAKER':>8} {'SMART$':>8} {'OI_SQZ':>8} {'CB_PREM':>8}")
    print("-" * 100)

    for symbol, data in results.items():
        sigs = data["signals"]
        comp = sigs["composite"]
        price = data["price"]

        def _fmt_sig(sig_dict):
            s = sig_dict.get("signal", "?")
            if s == "neutral":
                return "  ---  "
            elif s == "LONG":
                return f" LONG  "
            elif s == "SHORT":
                return f" SHORT "
            elif s == "SQUEEZE":
                return f" SQEEZ "
            return f" {s:>5} "

        comp_str = f"{comp['strength']:+.2f}" if comp["strength"] != 0 else " 0.00"

        print(
            f"  {symbol:<10} {price:>12,.2f} {comp['signal']:>10} {comp_str:>6}"
            f"  {_fmt_sig(sigs['crowd_contrarian']):>8}"
            f"  {_fmt_sig(sigs['taker_momentum']):>8}"
            f"  {_fmt_sig(sigs['smart_money_divergence']):>8}"
            f"  {_fmt_sig(sigs['oi_squeeze']):>8}"
            f"  {_fmt_sig(sigs['coinbase_premium']):>8}"
        )

    print("-" * 100)

    # Detail section
    print()
    print("  SIGNAL DETAILS:")
    print("-" * 100)
    for symbol, data in results.items():
        sigs = data["signals"]
        comp = sigs["composite"]
        if comp["signal"] != "neutral":
            print(f"\n  {symbol} — {comp['signal']} (strength: {comp['strength']:+.3f})")
            for sig_name, sig_data in sigs.items():
                if sig_name == "composite":
                    continue
                if sig_data.get("signal") != "neutral":
                    print(f"    {sig_name}: {sig_data.get('reason', '')}")
            if comp.get("squeeze_warning"):
                print(f"    *** SQUEEZE WARNING: expect volatility expansion ***")
        else:
            print(f"\n  {symbol} — neutral (no strong signals)")

    print()
    print("=" * 100)
    print("  Legend: CROWD=crowd contrarian, TAKER=taker momentum,")
    print("          SMART$=smart money divergence, OI_SQZ=open interest squeeze,")
    print("          CB_PREM=Coinbase premium")
    print("=" * 100)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = run_full_scan()
    print_summary(results)

"""
Deribit Options & Futures Signals — FREE public API, no auth required.

Sources:
  1. Deribit Options Book Summary — put/call OI ratio, max pain, IV skew
  2. Deribit DVOL (crypto VIX) — volatility index hourly data
  3. Deribit Futures Book Summary — annualized basis (futures premium vs spot)

Currencies: BTC and ETH

Signal logic:
  - DVOL > 80 = extreme fear → BUY,  DVOL < 40 = complacency → SELL
  - Put/Call OI ratio > 1.2 = heavy hedging (fear) → BUY,  < 0.5 = complacent → SELL
  - Futures basis > 15% annualized = overheated → SELL,  < 5% = despair → BUY
  - Composite = majority vote with strength score (-1 to +1)

All data is fetched with proper error handling and timeouts,
parsed into a standardized format, and saved to data/deribit_snapshot.json.
"""

import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
SNAPSHOT_FILE = os.path.join(DATA_DIR, "deribit_snapshot.json")

TIMEOUT = 15  # seconds per request
USER_AGENT = "Battleground-Deribit/1.0"

DERIBIT_BASE = "https://www.deribit.com/api/v2/public"


# =============================================================================
# Helpers
# =============================================================================

def _fetch_json(url, timeout=TIMEOUT):
    """Fetch JSON from a URL with error handling."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, json.JSONDecodeError, Exception) as e:
        return {"error": str(e)}


def _safe_float(val, default=0.0):
    """Safely convert to float."""
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_instrument_name(name):
    """Parse a Deribit option instrument name.

    Format: BTC-28MAR26-90000-C
    Returns dict with currency, expiry_str, strike, option_type (C/P) or None.
    """
    m = re.match(r"^([A-Z]+)-(\d+[A-Z]+\d+)-(\d+)-([CP])$", name)
    if not m:
        return None
    return {
        "currency": m.group(1),
        "expiry_str": m.group(2),
        "strike": float(m.group(3)),
        "option_type": m.group(4),
    }


# =============================================================================
# 1. OPTIONS BOOK SUMMARY
# =============================================================================

def fetch_options_summary(currency="BTC"):
    """Fetch all listed options with mark price, IV, volume, OI.

    Returns dict with 'instruments' list and metadata, or error dict.
    """
    url = (
        f"{DERIBIT_BASE}/get_book_summary_by_currency"
        f"?currency={currency}&kind=option"
    )
    raw = _fetch_json(url)
    if isinstance(raw, dict) and "error" in raw:
        return {"source": f"deribit_options_{currency}", "error": raw["error"], "instruments": []}

    result = raw.get("result", [])
    instruments = []
    for item in result:
        parsed = _parse_instrument_name(item.get("instrument_name", ""))
        if parsed is None:
            continue
        instruments.append({
            "instrument_name": item.get("instrument_name"),
            "strike": parsed["strike"],
            "option_type": parsed["option_type"],
            "expiry_str": parsed["expiry_str"],
            "mark_price": _safe_float(item.get("mark_price")),
            "mark_iv": _safe_float(item.get("mark_iv")),
            "volume": _safe_float(item.get("volume")),
            "open_interest": _safe_float(item.get("open_interest")),
            "bid_price": _safe_float(item.get("bid_price")),
            "ask_price": _safe_float(item.get("ask_price")),
            "underlying_price": _safe_float(item.get("underlying_price")),
        })

    return {
        "source": f"deribit_options_{currency}",
        "currency": currency,
        "count": len(instruments),
        "instruments": instruments,
    }


# =============================================================================
# 2. PUT/CALL RATIO
# =============================================================================

def compute_put_call_ratio(options_data):
    """Compute put/call open interest ratio from options summary.

    Returns float ratio (put OI / call OI).  >1 means more puts = bearish hedging.
    """
    instruments = options_data.get("instruments", [])
    if not instruments:
        return 0.0

    call_oi = sum(i["open_interest"] for i in instruments if i["option_type"] == "C")
    put_oi = sum(i["open_interest"] for i in instruments if i["option_type"] == "P")

    if call_oi == 0:
        return 0.0
    return round(put_oi / call_oi, 4)


# =============================================================================
# 3. MAX PAIN
# =============================================================================

def compute_max_pain(options_data):
    """Compute max pain strike — the price at which option sellers suffer least.

    Method: for each strike, compute total intrinsic value of all ITM options
    if the underlying settled at that strike. Max pain = strike with minimum total pain.
    """
    instruments = options_data.get("instruments", [])
    if not instruments:
        return 0.0

    # Group OI by strike and type
    strike_oi = defaultdict(lambda: {"C": 0.0, "P": 0.0})
    strikes = set()
    for inst in instruments:
        s = inst["strike"]
        ot = inst["option_type"]
        strikes.add(s)
        strike_oi[s][ot] += inst["open_interest"]

    if not strikes:
        return 0.0

    sorted_strikes = sorted(strikes)
    min_pain = float("inf")
    max_pain_strike = sorted_strikes[len(sorted_strikes) // 2]

    for settle_price in sorted_strikes:
        total_pain = 0.0
        for s in sorted_strikes:
            # Call pain: if settle > strike, calls are ITM
            call_intrinsic = max(settle_price - s, 0) * strike_oi[s]["C"]
            # Put pain: if settle < strike, puts are ITM
            put_intrinsic = max(s - settle_price, 0) * strike_oi[s]["P"]
            total_pain += call_intrinsic + put_intrinsic

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = settle_price

    return max_pain_strike


def compute_iv_skew(options_data):
    """Compute 25-delta IV skew (put IV minus call IV for near-ATM options).

    Positive skew = puts are more expensive = bearish sentiment.
    Uses options within 10% of current underlying price as a proxy for ATM.
    """
    instruments = options_data.get("instruments", [])
    if not instruments:
        return 0.0

    # Get underlying price from first instrument that has one
    underlying = 0.0
    for inst in instruments:
        if inst["underlying_price"] > 0:
            underlying = inst["underlying_price"]
            break
    if underlying == 0:
        return 0.0

    # Near-ATM: strikes within 10% of underlying
    lo = underlying * 0.90
    hi = underlying * 1.10

    put_ivs = []
    call_ivs = []
    for inst in instruments:
        if lo <= inst["strike"] <= hi and inst["mark_iv"] > 0:
            if inst["option_type"] == "P":
                put_ivs.append(inst["mark_iv"])
            else:
                call_ivs.append(inst["mark_iv"])

    if not put_ivs or not call_ivs:
        return 0.0

    avg_put_iv = sum(put_ivs) / len(put_ivs)
    avg_call_iv = sum(call_ivs) / len(call_ivs)
    return round(avg_put_iv - avg_call_iv, 2)


# =============================================================================
# 4. DVOL (Crypto VIX)
# =============================================================================

def fetch_dvol(currency="BTC", hours=72):
    """Fetch DVOL (Deribit Volatility Index) hourly data.

    Returns dict with current DVOL, 24h change, min/max over window, and raw data.
    DVOL > 80 = extreme fear (buy zone), DVOL < 40 = complacency (sell zone).
    """
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (hours * 3600 * 1000)

    url = (
        f"{DERIBIT_BASE}/get_volatility_index_data"
        f"?currency={currency}&resolution=3600"
        f"&start_timestamp={start_ms}&end_timestamp={now_ms}"
    )
    raw = _fetch_json(url)
    if isinstance(raw, dict) and "error" in raw:
        return {
            "source": f"deribit_dvol_{currency}",
            "error": raw["error"],
            "current": 0.0,
        }

    result = raw.get("result", {})
    data_points = result.get("data", [])

    if not data_points:
        return {
            "source": f"deribit_dvol_{currency}",
            "error": "no data points returned",
            "current": 0.0,
        }

    # Each data point: [timestamp, open, high, low, close]
    closes = [dp[4] for dp in data_points if len(dp) >= 5]
    if not closes:
        return {
            "source": f"deribit_dvol_{currency}",
            "error": "no close values",
            "current": 0.0,
        }

    current = round(closes[-1], 2)
    dvol_24h_ago = closes[-24] if len(closes) >= 24 else closes[0]
    change_24h = round(current - dvol_24h_ago, 2)

    return {
        "source": f"deribit_dvol_{currency}",
        "currency": currency,
        "current": current,
        "change_24h": change_24h,
        "min_72h": round(min(closes), 2),
        "max_72h": round(max(closes), 2),
        "data_points": len(closes),
    }


# =============================================================================
# 5. FUTURES BASIS
# =============================================================================

def fetch_futures_basis(currency="BTC"):
    """Fetch futures book summary and compute annualized basis vs spot.

    Basis = (futures_price - spot_price) / spot_price * (365 / days_to_expiry) * 100
    Returns dict with per-contract basis and weighted average.
    Basis > 15% = overheated → SELL,  < 5% = despair → BUY.
    """
    url = (
        f"{DERIBIT_BASE}/get_book_summary_by_currency"
        f"?currency={currency}&kind=future"
    )
    raw = _fetch_json(url)
    if isinstance(raw, dict) and "error" in raw:
        return {
            "source": f"deribit_futures_{currency}",
            "error": raw["error"],
            "basis_annualized": 0.0,
        }

    result = raw.get("result", [])
    if not result:
        return {
            "source": f"deribit_futures_{currency}",
            "error": "no futures data",
            "basis_annualized": 0.0,
        }

    # Find the perpetual (spot proxy) — instrument name like "BTC-PERPETUAL"
    spot_price = 0.0
    contracts = []
    for item in result:
        name = item.get("instrument_name", "")
        mark = _safe_float(item.get("mark_price"))
        if "PERPETUAL" in name:
            spot_price = mark
        else:
            contracts.append({
                "instrument_name": name,
                "mark_price": mark,
                "volume": _safe_float(item.get("volume")),
                "open_interest": _safe_float(item.get("open_interest")),
            })

    if spot_price == 0:
        # Fallback: use underlying_price from first contract
        for item in result:
            up = _safe_float(item.get("underlying_price"))
            if up > 0:
                spot_price = up
                break
    if spot_price == 0:
        return {
            "source": f"deribit_futures_{currency}",
            "error": "cannot determine spot price",
            "basis_annualized": 0.0,
        }

    now = datetime.now(timezone.utc)
    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    basis_entries = []
    for c in contracts:
        name = c["instrument_name"]
        # Parse expiry from name, e.g. BTC-28MAR26
        m = re.match(r"[A-Z]+-(\d+)([A-Z]+)(\d+)", name)
        if not m:
            continue
        day = int(m.group(1))
        month = month_map.get(m.group(2), 0)
        year_short = int(m.group(3))
        if month == 0:
            continue
        year = 2000 + year_short if year_short < 100 else year_short

        try:
            expiry = datetime(year, month, day, 8, 0, tzinfo=timezone.utc)  # Deribit settles 08:00 UTC
        except ValueError:
            continue

        days_to_expiry = (expiry - now).total_seconds() / 86400
        if days_to_expiry <= 0:
            continue

        premium_pct = ((c["mark_price"] - spot_price) / spot_price) * 100
        annualized = premium_pct * (365.0 / days_to_expiry)

        basis_entries.append({
            "instrument": name,
            "mark_price": c["mark_price"],
            "days_to_expiry": round(days_to_expiry, 1),
            "premium_pct": round(premium_pct, 4),
            "annualized_basis_pct": round(annualized, 2),
            "open_interest": c["open_interest"],
        })

    # Weighted average basis by OI
    total_oi = sum(e["open_interest"] for e in basis_entries)
    if total_oi > 0:
        avg_basis = sum(
            e["annualized_basis_pct"] * e["open_interest"] for e in basis_entries
        ) / total_oi
    elif basis_entries:
        avg_basis = sum(e["annualized_basis_pct"] for e in basis_entries) / len(basis_entries)
    else:
        avg_basis = 0.0

    return {
        "source": f"deribit_futures_{currency}",
        "currency": currency,
        "spot_price": round(spot_price, 2),
        "contracts": basis_entries,
        "basis_annualized": round(avg_basis, 2),
    }


# =============================================================================
# 6. SIGNAL GENERATION
# =============================================================================

def _dvol_signal(dvol_value):
    """DVOL > 80 = BUY (extreme fear), < 40 = SELL (complacency)."""
    if dvol_value >= 80:
        return "BUY", min((dvol_value - 80) / 40, 1.0)
    elif dvol_value <= 40:
        return "SELL", min((40 - dvol_value) / 40, 1.0)
    return "NEUTRAL", 0.0


def _put_call_signal(ratio):
    """P/C > 1.2 = BUY (heavy hedging = fear), < 0.5 = SELL (complacent)."""
    if ratio >= 1.2:
        return "BUY", min((ratio - 1.2) / 0.8, 1.0)
    elif ratio <= 0.5:
        return "SELL", min((0.5 - ratio) / 0.5, 1.0)
    return "NEUTRAL", 0.0


def _basis_signal(basis_pct):
    """Basis > 15% = SELL (overheated), < 5% = BUY (despair)."""
    if basis_pct >= 15:
        return "SELL", min((basis_pct - 15) / 15, 1.0)
    elif basis_pct <= 5:
        return "BUY", min((5 - basis_pct) / 5, 1.0)
    return "NEUTRAL", 0.0


def generate_signals():
    """Main entry point — fetch all data, compute signals, return standardized dict."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch data for BTC and ETH
    btc_options = fetch_options_summary("BTC")
    eth_options = fetch_options_summary("ETH")
    btc_dvol = fetch_dvol("BTC", hours=72)
    eth_dvol = fetch_dvol("ETH", hours=72)
    btc_futures = fetch_futures_basis("BTC")
    eth_futures = fetch_futures_basis("ETH")

    # Compute metrics
    btc_pc_ratio = compute_put_call_ratio(btc_options)
    eth_pc_ratio = compute_put_call_ratio(eth_options)
    btc_max_pain_val = compute_max_pain(btc_options)
    eth_max_pain_val = compute_max_pain(eth_options)
    btc_iv_skew = compute_iv_skew(btc_options)
    eth_iv_skew = compute_iv_skew(eth_options)
    btc_dvol_val = btc_dvol.get("current", 0.0)
    eth_dvol_val = eth_dvol.get("current", 0.0)
    btc_basis_val = btc_futures.get("basis_annualized", 0.0)
    eth_basis_val = eth_futures.get("basis_annualized", 0.0)

    # Individual signals (use BTC as primary for composite)
    dvol_sig, dvol_str = _dvol_signal(btc_dvol_val)
    pc_sig, pc_str = _put_call_signal(btc_pc_ratio)
    basis_sig, basis_str = _basis_signal(btc_basis_val)

    # Composite: majority vote with strength
    votes = []
    for sig, strength in [(dvol_sig, dvol_str), (pc_sig, pc_str), (basis_sig, basis_str)]:
        if sig == "BUY":
            votes.append(strength)
        elif sig == "SELL":
            votes.append(-strength)
        else:
            votes.append(0.0)

    avg_score = sum(votes) / len(votes) if votes else 0.0
    buy_count = sum(1 for v in votes if v > 0)
    sell_count = sum(1 for v in votes if v < 0)

    if buy_count > sell_count:
        composite = "BUY"
    elif sell_count > buy_count:
        composite = "SELL"
    else:
        composite = "NEUTRAL"

    composite_strength = round(max(-1.0, min(1.0, avg_score)), 3)

    # Underlying prices
    btc_spot = btc_futures.get("spot_price", 0.0)
    eth_spot = eth_futures.get("spot_price", 0.0)

    output = {
        "timestamp": timestamp,
        "btc_spot_price": btc_spot,
        "btc_put_call_ratio": btc_pc_ratio,
        "btc_dvol": btc_dvol_val,
        "btc_dvol_change_24h": btc_dvol.get("change_24h", 0.0),
        "btc_max_pain": btc_max_pain_val,
        "btc_iv_skew": btc_iv_skew,
        "btc_futures_basis_annualized": btc_basis_val,
        "eth_spot_price": eth_spot,
        "eth_put_call_ratio": eth_pc_ratio,
        "eth_dvol": eth_dvol_val,
        "eth_dvol_change_24h": eth_dvol.get("change_24h", 0.0),
        "eth_max_pain": eth_max_pain_val,
        "eth_iv_skew": eth_iv_skew,
        "eth_futures_basis_annualized": eth_futures.get("basis_annualized", 0.0),
        "signals": {
            "dvol_signal": dvol_sig,
            "dvol_strength": round(dvol_str, 3),
            "put_call_signal": pc_sig,
            "put_call_strength": round(pc_str, 3),
            "basis_signal": basis_sig,
            "basis_strength": round(basis_str, 3),
            "composite_signal": composite,
            "composite_strength": composite_strength,
        },
        "futures_detail": {
            "btc": btc_futures.get("contracts", []),
            "eth": eth_futures.get("contracts", []),
        },
        "options_meta": {
            "btc_options_count": btc_options.get("count", 0),
            "eth_options_count": eth_options.get("count", 0),
        },
    }

    # Save snapshot
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    return output


# =============================================================================
# STANDALONE — pretty print summary
# =============================================================================

def _color(signal):
    """ANSI color for signal."""
    if signal == "BUY":
        return "\033[92m"  # green
    elif signal == "SELL":
        return "\033[91m"  # red
    return "\033[93m"  # yellow


RST = "\033[0m"


def print_summary(data):
    """Print a formatted summary table."""
    sigs = data.get("signals", {})
    composite = sigs.get("composite_signal", "NEUTRAL")

    print("\n" + "=" * 70)
    print("  DERIBIT OPTIONS & FUTURES SIGNALS")
    print("=" * 70)
    print(f"  Timestamp: {data['timestamp']}")
    print("-" * 70)

    # BTC section
    print(f"\n  {'BTC':>5}  Spot: ${data['btc_spot_price']:,.0f}")
    print(f"  {'':>5}  Put/Call Ratio:  {data['btc_put_call_ratio']:.4f}")
    print(f"  {'':>5}  DVOL:           {data['btc_dvol']:.1f}  (24h: {data['btc_dvol_change_24h']:+.1f})")
    print(f"  {'':>5}  Max Pain:       ${data['btc_max_pain']:,.0f}")
    print(f"  {'':>5}  IV Skew:        {data['btc_iv_skew']:+.2f}")
    print(f"  {'':>5}  Futures Basis:  {data['btc_futures_basis_annualized']:+.2f}% annualized")

    # ETH section
    print(f"\n  {'ETH':>5}  Spot: ${data['eth_spot_price']:,.0f}")
    print(f"  {'':>5}  Put/Call Ratio:  {data['eth_put_call_ratio']:.4f}")
    print(f"  {'':>5}  DVOL:           {data['eth_dvol']:.1f}  (24h: {data['eth_dvol_change_24h']:+.1f})")
    print(f"  {'':>5}  Max Pain:       ${data['eth_max_pain']:,.0f}")
    print(f"  {'':>5}  IV Skew:        {data['eth_iv_skew']:+.2f}")
    print(f"  {'':>5}  Futures Basis:  {data.get('eth_futures_basis_annualized', 0):+.2f}% annualized")

    # Signals
    print("\n" + "-" * 70)
    print("  SIGNALS (BTC-primary)")
    print("-" * 70)

    rows = [
        ("DVOL", sigs["dvol_signal"], sigs["dvol_strength"],
         f"DVOL={data['btc_dvol']:.0f} | >80=BUY, <40=SELL"),
        ("Put/Call", sigs["put_call_signal"], sigs["put_call_strength"],
         f"P/C={data['btc_put_call_ratio']:.2f} | >1.2=BUY, <0.5=SELL"),
        ("Basis", sigs["basis_signal"], sigs["basis_strength"],
         f"Basis={data['btc_futures_basis_annualized']:+.1f}% | >15%=SELL, <5%=BUY"),
    ]
    for label, sig, strength, detail in rows:
        c = _color(sig)
        print(f"  {label:<12} {c}{sig:>7}{RST}  str={strength:.2f}  | {detail}")

    c = _color(composite)
    print(f"\n  {'COMPOSITE':<12} {c}{composite:>7}{RST}  "
          f"strength={sigs['composite_strength']:+.3f}")

    # Futures detail
    btc_contracts = data.get("futures_detail", {}).get("btc", [])
    if btc_contracts:
        print("\n" + "-" * 70)
        print("  BTC FUTURES CONTRACTS")
        print(f"  {'Contract':<20} {'Price':>12} {'DTE':>6} {'Basis':>10}")
        for c in sorted(btc_contracts, key=lambda x: x["days_to_expiry"]):
            print(f"  {c['instrument']:<20} ${c['mark_price']:>10,.0f} "
                  f"{c['days_to_expiry']:>5.0f}d "
                  f"{c['annualized_basis_pct']:>+8.2f}%")

    print("\n" + "=" * 70)
    print(f"  Snapshot saved: {SNAPSHOT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("Fetching Deribit data (public API, no auth)...")
    data = generate_signals()
    print_summary(data)

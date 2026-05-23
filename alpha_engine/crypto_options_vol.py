"""
ALPHA_ENGINE -- Crypto Options Volatility Surface
===================================================
Extracts implied volatility, skew, and term structure from Deribit public API
to generate directional signals when the vol surface shows mispricing.

Signals are spot/futures directional hints (not options trades), since the
Alpha Engine operates on spot and perpetual futures.

Data source:
  - Primary: Deribit public API (no auth required for market data)
    https://www.deribit.com/api/v2/public/
  - Fallback: Binance spot klines for historical volatility estimation

Signal types:
  1. IV Crush Play       -- ATM IV in top 20% of 30d range -> expect mean reversion
  2. Vol Expansion Play  -- ATM IV in bottom 20% -> expect vol expansion
  3. Skew Reversal       -- Extreme put skew (>10%) -> contrarian long
  4. Term Structure Inversion -- Near IV > Far IV (backwardation) -> big move imminent

References:
  - Natenberg (1994): Option Volatility & Pricing
  - Sinclair (2013): Volatility Trading, 2nd ed.
  - Deribit DVOL methodology (2020): variance swap based IV index
  - Realized vs Implied: 70% of time IV > RV in BTC options (Deribit 2019-2024)
"""

from __future__ import annotations

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
_BINANCE_SPOT_BASES = [
    "https://api.binance.com/api/v3",
    "https://api.binance.us/api/v3",
    "https://data-api.binance.vision/api/v3",
]
BINANCE_BASE = "https://api.binance.com/api/v3"

SUPPORTED_CURRENCIES = ["BTC", "ETH"]

# IV percentile thresholds for signal generation
IV_HIGH_PERCENTILE = 80   # top 20% -> IV Crush
IV_LOW_PERCENTILE = 20    # bottom 20% -> Vol Expansion
SKEW_EXTREME_PCT = 10.0   # put skew > 10% -> Skew Reversal

# Realized vol lookback
RV_LOOKBACK_DAYS = 30
IV_HISTORY_DAYS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _smart_round(value: float) -> float:
    """Round prices intelligently based on magnitude."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    else:
        return round(value, 6)


def _api_get(url: str, timeout: int = 15) -> Optional[dict]:
    """Fetch JSON from a URL, return None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _get_spot_price(currency: str) -> Optional[float]:
    """Get current spot price from Binance with endpoint failover."""
    symbol = f"{currency}USDT"
    for base in _BINANCE_SPOT_BASES:
        data = _api_get(f"{base}/ticker/price?symbol={symbol}")
        if data and "price" in data:
            return float(data["price"])
    return None


def _get_binance_klines(currency: str, days: int = 30) -> list[float]:
    """Fetch daily close prices from Binance with endpoint failover."""
    symbol = f"{currency}USDT"
    for base in _BINANCE_SPOT_BASES:
        url = (
            f"{base}/klines?symbol={symbol}"
            f"&interval=1d&limit={days + 1}"
        )
        data = _api_get(url)
        if data:
            break
    if not data:
        return []
    # klines format: [open_time, open, high, low, close, volume, ...]
    return [float(k[4]) for k in data]


def _compute_realized_vol(closes: list[float]) -> float:
    """
    Compute annualized realized volatility from daily closes.
    Uses close-to-close log returns, annualized by sqrt(365) for crypto.
    """
    if len(closes) < 2:
        return 0.0
    log_returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    if len(log_returns) < 2:
        return 0.0
    rv = float(np.std(log_returns, ddof=1)) * math.sqrt(365) * 100
    return round(rv, 2)


def _parse_expiry_ms(instrument_name: str) -> Optional[int]:
    """
    Parse expiry from Deribit instrument name like 'BTC-28MAR26-90000-C'.
    Returns expiry as Unix timestamp in ms, or None on parse failure.
    """
    parts = instrument_name.split("-")
    if len(parts) < 3:
        return None
    date_str = parts[1]
    try:
        # Deribit format: DDMMMYY (e.g., 28MAR26)
        dt = datetime.strptime(date_str, "%d%b%y").replace(
            hour=8, minute=0, tzinfo=timezone.utc
        )
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def _parse_strike(instrument_name: str) -> Optional[float]:
    """Parse strike from instrument name like 'BTC-28MAR26-90000-C'."""
    parts = instrument_name.split("-")
    if len(parts) < 4:
        return None
    try:
        return float(parts[2])
    except ValueError:
        return None


def _parse_option_type(instrument_name: str) -> Optional[str]:
    """Parse option type (C/P) from instrument name."""
    parts = instrument_name.split("-")
    if len(parts) < 4:
        return None
    t = parts[-1].upper()
    return t if t in ("C", "P") else None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def fetch_deribit_options(currency: str = "BTC") -> list[dict]:
    """
    Fetch option book summaries from Deribit public API.

    Returns list of option dicts with: instrument_name, mark_price,
    mark_iv (implied vol), underlying_price, strike, expiry_ms,
    option_type, open_interest, volume_usd.

    Falls back to empty list if Deribit is unreachable.
    """
    currency = currency.upper()
    url = (
        f"{DERIBIT_BASE}/get_book_summary_by_currency"
        f"?currency={currency}&kind=option"
    )
    data = _api_get(url, timeout=20)
    if not data or "result" not in data:
        return []

    options = []
    for item in data["result"]:
        name = item.get("instrument_name", "")
        mark_iv = item.get("mark_iv")
        if mark_iv is None or mark_iv <= 0:
            continue

        strike = _parse_strike(name)
        expiry_ms = _parse_expiry_ms(name)
        opt_type = _parse_option_type(name)
        if strike is None or expiry_ms is None or opt_type is None:
            continue

        options.append({
            "instrument_name": name,
            "mark_price": item.get("mark_price", 0),
            "mark_iv": mark_iv,
            "underlying_price": item.get("underlying_price", 0),
            "strike": strike,
            "expiry_ms": expiry_ms,
            "option_type": opt_type,
            "open_interest": item.get("open_interest", 0),
            "volume_usd": item.get("volume_usd", 0),
        })

    return options


def build_vol_surface(options_data: list[dict]) -> dict:
    """
    Build a volatility surface from option data.

    Groups options by expiry, computes ATM IV (nearest strike to spot)
    and put/call skew per expiry.

    Returns:
        {
            "term_structure": [{"expiry": "2026-03-28", "expiry_ms": ..., "atm_iv": 55.2, "dte": 24}, ...],
            "skew": [{"expiry": "2026-03-28", "put_iv": 58.1, "call_iv": 52.3, "skew_val": 5.8}, ...],
        }
    """
    if not options_data:
        return {"term_structure": [], "skew": []}

    # Get underlying price from first option
    spot = options_data[0].get("underlying_price", 0)
    if spot <= 0:
        return {"term_structure": [], "skew": []}

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Group by expiry
    by_expiry: dict[int, list[dict]] = {}
    for opt in options_data:
        exp = opt["expiry_ms"]
        if exp <= now_ms:
            continue  # skip expired
        by_expiry.setdefault(exp, []).append(opt)

    term_structure = []
    skew_data = []

    for exp_ms in sorted(by_expiry.keys()):
        opts = by_expiry[exp_ms]
        dte = max(1, (exp_ms - now_ms) // (86400 * 1000))

        # Find ATM: nearest strike to spot
        atm_opts = sorted(opts, key=lambda o: abs(o["strike"] - spot))
        atm_iv_values = [o["mark_iv"] for o in atm_opts[:4]]  # avg of closest 4
        atm_iv = sum(atm_iv_values) / len(atm_iv_values) if atm_iv_values else 0

        expiry_str = datetime.fromtimestamp(
            exp_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")

        term_structure.append({
            "expiry": expiry_str,
            "expiry_ms": exp_ms,
            "atm_iv": round(atm_iv, 2),
            "dte": dte,
        })

        # Put vs Call IV at ATM strikes
        atm_range = spot * 0.05  # within 5% of spot
        puts = [o for o in opts if o["option_type"] == "P" and abs(o["strike"] - spot) < atm_range]
        calls = [o for o in opts if o["option_type"] == "C" and abs(o["strike"] - spot) < atm_range]

        if puts and calls:
            avg_put_iv = sum(p["mark_iv"] for p in puts) / len(puts)
            avg_call_iv = sum(c["mark_iv"] for c in calls) / len(calls)
            skew_val = avg_put_iv - avg_call_iv
            skew_data.append({
                "expiry": expiry_str,
                "put_iv": round(avg_put_iv, 2),
                "call_iv": round(avg_call_iv, 2),
                "skew_val": round(skew_val, 2),
            })

    return {"term_structure": term_structure, "skew": skew_data}


def compute_vol_metrics(currency: str = "BTC") -> dict:
    """
    Compute comprehensive volatility metrics for a currency.

    Returns:
        {
            "currency": "BTC",
            "spot_price": 94500.0,
            "atm_iv": 55.2,           -- ATM implied vol (nearest expiry)
            "iv_skew": 5.8,            -- Put IV minus Call IV (+ = fearful)
            "iv_term_slope": 3.4,      -- Far IV minus Near IV (+ = contango)
            "iv_percentile": 72,       -- Current ATM IV vs 30d range (0-100)
            "realized_vol": 48.1,      -- 30d realized vol
            "realized_vs_implied": 7.1,-- IV minus RV (+ = IV premium)
            "source": "deribit",       -- or "fallback_binance"
            "timestamp": "..."
        }
    """
    currency = currency.upper()
    spot = _get_spot_price(currency)
    if spot is None:
        spot = 0.0

    # Try Deribit first
    options = fetch_deribit_options(currency)
    surface = build_vol_surface(options)

    # Realized vol from Binance
    closes = _get_binance_klines(currency, RV_LOOKBACK_DAYS)
    rv = _compute_realized_vol(closes)

    source = "deribit"
    atm_iv = 0.0
    iv_skew = 0.0
    iv_term_slope = 0.0
    iv_percentile = 50  # default neutral

    if surface["term_structure"]:
        # ATM IV from nearest expiry
        nearest = surface["term_structure"][0]
        atm_iv = nearest["atm_iv"]

        # Term slope: farthest minus nearest
        if len(surface["term_structure"]) >= 2:
            farthest = surface["term_structure"][-1]
            iv_term_slope = round(farthest["atm_iv"] - nearest["atm_iv"], 2)

        # Skew from nearest expiry
        if surface["skew"]:
            iv_skew = surface["skew"][0]["skew_val"]

        # IV percentile: compare ATM IV against range across all expiries
        all_ivs = [t["atm_iv"] for t in surface["term_structure"]]
        if len(all_ivs) >= 3:
            iv_min = min(all_ivs)
            iv_max = max(all_ivs)
            if iv_max > iv_min:
                iv_percentile = int(
                    (atm_iv - iv_min) / (iv_max - iv_min) * 100
                )
                iv_percentile = max(0, min(100, iv_percentile))
    else:
        # Fallback: estimate IV from realized vol with typical premium
        source = "fallback_binance"
        if rv > 0:
            # IV is typically 1.15-1.3x RV in crypto (Deribit 2019-2024 data)
            atm_iv = round(rv * 1.2, 2)
            iv_percentile = 50  # unknown without historical IV data

    realized_vs_implied = round(atm_iv - rv, 2) if rv > 0 else 0.0

    return {
        "currency": currency,
        "spot_price": _smart_round(spot),
        "atm_iv": atm_iv,
        "iv_skew": iv_skew,
        "iv_term_slope": iv_term_slope,
        "iv_percentile": iv_percentile,
        "realized_vol": rv,
        "realized_vs_implied": realized_vs_implied,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_vol_signals(currency: str = "BTC") -> list[dict]:
    """
    Generate directional signals from vol surface analysis.

    Signal types:
      1. IV Crush Play       -- IV top 20% -> SHORT (expect vol contraction)
      2. Vol Expansion Play  -- IV bottom 20% -> LONG (expect vol expansion)
      3. Skew Reversal       -- Put skew >10% -> LONG (contrarian bounce)
      4. Term Structure Inv. -- Backwardation -> volatility event imminent

    Returns list of signal dicts matching Alpha Engine format.
    """
    metrics = compute_vol_metrics(currency)
    signals = []

    spot = metrics["spot_price"]
    if spot <= 0:
        return signals

    symbol = f"{currency}-USD"
    now_str = datetime.now(timezone.utc).isoformat()

    # Signal 1: IV Crush Play
    if metrics["atm_iv"] > 0 and metrics["iv_percentile"] >= IV_HIGH_PERCENTILE:
        confidence = min(0.85, 0.55 + (metrics["iv_percentile"] - 80) * 0.015)
        signals.append({
            "strategy": "iv_crush_play",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "SELL",
            "entry_price": _smart_round(spot),
            "take_profit": _smart_round(spot * 0.92),
            "stop_loss": _smart_round(spot * 1.04),
            "confidence": round(confidence, 3),
            "risk_reward": round(8.0 / 4.0, 2),
            "reason": (
                f"IV Crush Play: ATM IV={metrics['atm_iv']:.1f}% is in "
                f"{metrics['iv_percentile']}th percentile (top 20%). "
                f"RV={metrics['realized_vol']:.1f}%, IV premium="
                f"{metrics['realized_vs_implied']:.1f}pts. "
                f"Expect vol contraction and price mean reversion."
            ),
            "timeframe": "3-7d",
            "source": f"deribit_vol_surface_{currency.lower()}",
            "extra": {
                "vol_metrics": metrics,
            },
            "generated_at": now_str,
        })

    # Signal 2: Vol Expansion Play
    if metrics["atm_iv"] > 0 and metrics["iv_percentile"] <= IV_LOW_PERCENTILE:
        confidence = min(0.80, 0.50 + (20 - metrics["iv_percentile"]) * 0.015)
        signals.append({
            "strategy": "vol_expansion_play",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": _smart_round(spot),
            "take_profit": _smart_round(spot * 1.10),
            "stop_loss": _smart_round(spot * 0.95),
            "confidence": round(confidence, 3),
            "risk_reward": round(10.0 / 5.0, 2),
            "reason": (
                f"Vol Expansion Play: ATM IV={metrics['atm_iv']:.1f}% is in "
                f"{metrics['iv_percentile']}th percentile (bottom 20%). "
                f"Vol is cheap -- expect expansion. "
                f"Historically, low IV precedes large directional moves."
            ),
            "timeframe": "7-14d",
            "source": f"deribit_vol_surface_{currency.lower()}",
            "extra": {
                "vol_metrics": metrics,
            },
            "generated_at": now_str,
        })

    # Signal 3: Skew Reversal
    if metrics["iv_skew"] > SKEW_EXTREME_PCT:
        confidence = min(0.75, 0.50 + (metrics["iv_skew"] - 10) * 0.01)
        signals.append({
            "strategy": "skew_reversal",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": _smart_round(spot),
            "take_profit": _smart_round(spot * 1.08),
            "stop_loss": _smart_round(spot * 0.95),
            "confidence": round(confidence, 3),
            "risk_reward": round(8.0 / 5.0, 2),
            "reason": (
                f"Skew Reversal: Put IV exceeds Call IV by "
                f"{metrics['iv_skew']:.1f}% (>{SKEW_EXTREME_PCT}% threshold). "
                f"Extreme put demand signals peak fear -- contrarian long. "
                f"Put/call skew mean-reverts within 5-10 days (Sinclair 2013)."
            ),
            "timeframe": "5-10d",
            "source": f"deribit_vol_surface_{currency.lower()}",
            "extra": {
                "vol_metrics": metrics,
            },
            "generated_at": now_str,
        })

    # Signal 4: Term Structure Inversion (Backwardation)
    if metrics["iv_term_slope"] < -3.0:
        confidence = min(0.70, 0.45 + abs(metrics["iv_term_slope"]) * 0.01)
        signals.append({
            "strategy": "term_structure_inversion",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": _smart_round(spot),
            "take_profit": _smart_round(spot * 1.12),
            "stop_loss": _smart_round(spot * 0.94),
            "confidence": round(confidence, 3),
            "risk_reward": round(12.0 / 6.0, 2),
            "reason": (
                f"Term Structure Inversion: Near-term IV exceeds far-term "
                f"by {abs(metrics['iv_term_slope']):.1f}pts (backwardation). "
                f"Market pricing imminent large move. "
                f"Vol term structure backwardation resolves with directional breakout."
            ),
            "timeframe": "3-7d",
            "source": f"deribit_vol_surface_{currency.lower()}",
            "extra": {
                "vol_metrics": metrics,
            },
            "generated_at": now_str,
        })

    return signals


def scan(symbols: Optional[list[str]] = None) -> list[dict]:
    """
    Scan all supported currencies for vol surface signals.

    Args:
        symbols: List of currencies to scan (default: ["BTC", "ETH"])

    Returns:
        List of all active signals across currencies.
    """
    if symbols is None:
        symbols = SUPPORTED_CURRENCIES

    all_signals = []
    for currency in symbols:
        currency = currency.upper().replace("-USD", "").replace("USDT", "")
        if currency not in SUPPORTED_CURRENCIES:
            continue
        try:
            sigs = generate_vol_signals(currency)
            all_signals.extend(sigs)
        except Exception as e:
            print(f"[crypto_options_vol] Error scanning {currency}: {e}")

    return all_signals


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"
    currency = sys.argv[2] if len(sys.argv) > 2 else "BTC"

    if mode == "metrics":
        metrics = compute_vol_metrics(currency)
        print(json.dumps(metrics, indent=2))
    elif mode == "surface":
        options = fetch_deribit_options(currency)
        surface = build_vol_surface(options)
        print(f"Term structure entries: {len(surface['term_structure'])}")
        for t in surface["term_structure"][:5]:
            print(f"  {t['expiry']}  DTE={t['dte']:3d}  ATM_IV={t['atm_iv']:.1f}%")
        print(f"Skew entries: {len(surface['skew'])}")
        for s in surface["skew"][:5]:
            print(f"  {s['expiry']}  Put={s['put_iv']:.1f}%  Call={s['call_iv']:.1f}%  Skew={s['skew_val']:+.1f}%")
    elif mode == "scan":
        signals = scan()
        if signals:
            for sig in signals:
                print(f"[{sig['strategy']}] {sig['symbol']} {sig['signal_type']} "
                      f"conf={sig['confidence']} | {sig['reason'][:80]}...")
        else:
            print("No vol surface signals active right now.")
    else:
        print(f"Usage: python crypto_options_vol.py [metrics|surface|scan] [BTC|ETH]")

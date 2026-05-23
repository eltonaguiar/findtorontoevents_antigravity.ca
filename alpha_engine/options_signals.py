"""
Crypto Options-Derived Signals from Deribit API

Extracts contrarian trading signals from BTC/ETH options markets:
  1. risk_reversal_25delta  -- 25-delta call IV minus put IV (skew)
  2. max_pain_gravity       -- Price gravitates to max-pain strike before expiry
  3. put_call_ratio         -- Aggregate put OI / call OI as fear/greed gauge

Deribit public API (no key required):
  - Book summaries: GET /api/v2/public/get_book_summary_by_currency
  - Instruments:    GET /api/v2/public/get_instruments

References:
  - Ederington & Guan (2002) "Measuring Implied Volatility: Is an Average Better?"
  - Bollen & Whaley (2004) "Does Net Buying Pressure Affect the Shape of Implied Volatility?"
  - Goyal & Saretto (2009) "Cross-section of Option Returns and Volatility"

stdlib only: urllib.request, json, math, datetime
"""

import json
import logging
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
REQUEST_TIMEOUT = 15  # seconds

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Strategy registry (for scanner.py STRATEGY_COUNT)
OPTIONS_STRATEGIES = {
    "risk_reversal_25delta": {
        "name": "25-Delta Risk Reversal",
        "category": "crypto",
        "win_rate": "55-62%",
        "source": "Bollen & Whaley (2004)",
    },
    "max_pain_gravity": {
        "name": "Max Pain Gravity",
        "category": "crypto",
        "win_rate": "52-58%",
        "source": "Goyal & Saretto (2009)",
    },
    "put_call_ratio": {
        "name": "Put/Call Ratio Contrarian",
        "category": "crypto",
        "win_rate": "54-60%",
        "source": "Ederington & Guan (2002)",
    },
}

# Thresholds
SKEW_EXTREME_NEGATIVE = -5.0   # puts very expensive -> contrarian BULLISH
SKEW_EXTREME_POSITIVE = 5.0    # calls very expensive -> contrarian BEARISH
MAX_PAIN_DEVIATION_PCT = 5.0   # >5% from max pain triggers signal
PCR_BEARISH_THRESHOLD = 1.2    # excessive fear
PCR_BULLISH_THRESHOLD = 0.6    # excessive greed

# Symbols to scan
CURRENCIES = ["BTC", "ETH"]
SYMBOL_MAP = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}


# ---------------------------------------------------------------------------
# Deribit API helpers
# ---------------------------------------------------------------------------

def _api_get(endpoint, params=None):
    """GET request to Deribit public API. Returns parsed JSON or None."""
    url = f"{DERIBIT_BASE}/{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"

    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return data.get("result", data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Deribit API error (%s): %s", endpoint, exc)
        return None


def _get_book_summaries(currency, kind="option"):
    """Fetch option book summaries for a currency."""
    return _api_get("get_book_summary_by_currency", {
        "currency": currency,
        "kind": kind,
    })


def _get_instruments(currency, kind="option", expired=False):
    """Fetch active option instruments for a currency."""
    return _api_get("get_instruments", {
        "currency": currency,
        "kind": kind,
        "expired": str(expired).lower(),
    })


def _get_index_price(currency):
    """Fetch current index price for a currency."""
    result = _api_get("get_index_price", {"index_name": f"{currency.lower()}_usd"})
    if result and isinstance(result, dict):
        return result.get("index_price")
    return None


def _parse_instrument_name(name):
    """
    Parse Deribit instrument name like 'BTC-28MAR26-90000-C'.
    Returns dict with currency, expiry_str, strike, option_type or None.
    """
    parts = name.split("-")
    if len(parts) != 4:
        return None
    return {
        "currency": parts[0],
        "expiry_str": parts[1],
        "strike": float(parts[2]),
        "option_type": parts[3],  # 'C' or 'P'
    }


def _expiry_str_to_date(expiry_str):
    """Convert Deribit expiry like '28MAR26' to datetime."""
    try:
        return datetime.strptime(expiry_str, "%d%b%y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _days_to_expiry(expiry_str):
    """Days remaining until expiry."""
    exp_date = _expiry_str_to_date(expiry_str)
    if exp_date is None:
        return None
    delta = exp_date - datetime.now(timezone.utc)
    return max(delta.days, 0)


# ---------------------------------------------------------------------------
# Strategy 1: 25-Delta Risk Reversal (IV skew)
# ---------------------------------------------------------------------------

def risk_reversal_25delta(currency="BTC"):
    """
    Compute 25-delta risk reversal: call IV - put IV.

    Extreme negative skew (puts expensive) = contrarian BULLISH.
    Extreme positive skew (calls expensive) = contrarian BEARISH.

    Returns signal dict or None.
    """
    summaries = _get_book_summaries(currency)
    if not summaries:
        return None

    index_price = _get_index_price(currency)
    if not index_price or index_price <= 0:
        return None

    now = datetime.now(timezone.utc)

    # Group options by expiry bucket (7-day and 30-day windows)
    short_term = []  # 3-10 days
    medium_term = []  # 20-40 days

    for item in summaries:
        name = item.get("instrument_name", "")
        parsed = _parse_instrument_name(name)
        if parsed is None:
            continue

        dte = _days_to_expiry(parsed["expiry_str"])
        if dte is None:
            continue

        mark_iv = item.get("mark_iv")
        if mark_iv is None or mark_iv <= 0:
            continue

        # Approximate delta from moneyness (Black-Scholes shortcut)
        strike = parsed["strike"]
        moneyness = math.log(strike / index_price) if strike > 0 and index_price > 0 else 0
        # 25-delta options are ~0.2-0.35 log-moneyness away
        abs_moneyness = abs(moneyness)

        entry = {
            "strike": strike,
            "option_type": parsed["option_type"],
            "mark_iv": mark_iv,
            "moneyness": moneyness,
            "abs_moneyness": abs_moneyness,
            "dte": dte,
        }

        if 3 <= dte <= 10:
            short_term.append(entry)
        elif 20 <= dte <= 40:
            medium_term.append(entry)

    # For each bucket, find approximate 25-delta call and put
    def _compute_skew(options):
        if not options:
            return None
        # 25-delta calls: OTM calls with ~0.15-0.35 moneyness
        otm_calls = [o for o in options if o["option_type"] == "C" and 0.05 < o["moneyness"] < 0.40]
        otm_puts = [o for o in options if o["option_type"] == "P" and -0.40 < o["moneyness"] < -0.05]

        if not otm_calls or not otm_puts:
            return None

        # Pick the option closest to 25-delta (~0.22 moneyness)
        target_moneyness = 0.22
        best_call = min(otm_calls, key=lambda o: abs(o["abs_moneyness"] - target_moneyness))
        best_put = min(otm_puts, key=lambda o: abs(o["abs_moneyness"] - target_moneyness))

        return best_call["mark_iv"] - best_put["mark_iv"]

    short_skew = _compute_skew(short_term)
    medium_skew = _compute_skew(medium_term)

    # Use the best available
    skew = medium_skew if medium_skew is not None else short_skew
    skew_label = "30d" if medium_skew is not None else "7d"
    if skew is None:
        return None

    # Determine signal
    if skew < SKEW_EXTREME_NEGATIVE:
        signal = "BULLISH"
        confidence = min(0.85, 0.55 + abs(skew - SKEW_EXTREME_NEGATIVE) * 0.02)
        description = (
            f"{currency} {skew_label} 25-delta risk reversal at {skew:+.1f}% "
            f"(puts expensive). Contrarian bullish -- extreme fear in options market."
        )
    elif skew > SKEW_EXTREME_POSITIVE:
        signal = "BEARISH"
        confidence = min(0.85, 0.55 + abs(skew - SKEW_EXTREME_POSITIVE) * 0.02)
        description = (
            f"{currency} {skew_label} 25-delta risk reversal at {skew:+.1f}% "
            f"(calls expensive). Contrarian bearish -- excessive optimism."
        )
    else:
        signal = "NEUTRAL"
        confidence = 0.3
        description = (
            f"{currency} {skew_label} 25-delta risk reversal at {skew:+.1f}% "
            f"-- within normal range, no extreme skew detected."
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(skew, 2),
        "description": description,
        "source": "deribit_risk_reversal",
        "currency": currency,
        "skew_term": skew_label,
    }


# ---------------------------------------------------------------------------
# Strategy 2: Max Pain Gravity
# ---------------------------------------------------------------------------

def max_pain_gravity(currency="BTC"):
    """
    Compute max pain strike (where most options expire worthless).
    Price tends to gravitate toward max pain before expiry.

    Signal: if spot is >5% from max pain, trade toward max pain.
    Returns signal dict or None.
    """
    summaries = _get_book_summaries(currency)
    if not summaries:
        return None

    index_price = _get_index_price(currency)
    if not index_price or index_price <= 0:
        return None

    # Find the nearest expiry with enough OI
    # Group by expiry
    expiry_oi = {}  # expiry_str -> {strike -> {"call_oi": x, "put_oi": y}}

    for item in summaries:
        name = item.get("instrument_name", "")
        parsed = _parse_instrument_name(name)
        if parsed is None:
            continue

        dte = _days_to_expiry(parsed["expiry_str"])
        if dte is None or dte < 1 or dte > 14:
            continue  # Focus on near-term expiries

        oi = item.get("open_interest", 0)
        if oi <= 0:
            continue

        expiry = parsed["expiry_str"]
        strike = parsed["strike"]

        if expiry not in expiry_oi:
            expiry_oi[expiry] = {}
        if strike not in expiry_oi[expiry]:
            expiry_oi[expiry][strike] = {"call_oi": 0, "put_oi": 0}

        if parsed["option_type"] == "C":
            expiry_oi[expiry][strike]["call_oi"] += oi
        else:
            expiry_oi[expiry][strike]["put_oi"] += oi

    if not expiry_oi:
        return None

    # Pick expiry with most total OI
    best_expiry = max(expiry_oi, key=lambda e: sum(
        v["call_oi"] + v["put_oi"] for v in expiry_oi[e].values()
    ))
    strikes_data = expiry_oi[best_expiry]
    dte = _days_to_expiry(best_expiry)

    # Calculate max pain: the strike where total intrinsic loss is minimized
    all_strikes = sorted(strikes_data.keys())
    if not all_strikes:
        return None

    min_pain = float("inf")
    max_pain_strike = all_strikes[0]

    for settle_price in all_strikes:
        total_pain = 0.0
        for strike, oi_data in strikes_data.items():
            # Call holders lose if settle < strike
            call_loss = max(0, settle_price - strike) * oi_data["call_oi"]
            # Put holders lose if settle > strike
            put_loss = max(0, strike - settle_price) * oi_data["put_oi"]
            total_pain += call_loss + put_loss

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = settle_price

    # Deviation from max pain
    deviation_pct = ((index_price - max_pain_strike) / max_pain_strike) * 100

    if abs(deviation_pct) < MAX_PAIN_DEVIATION_PCT:
        signal = "NEUTRAL"
        confidence = 0.3
        description = (
            f"{currency} spot ${index_price:,.0f} is within {abs(deviation_pct):.1f}% "
            f"of max pain ${max_pain_strike:,.0f} ({best_expiry} expiry, {dte}d). "
            f"No significant gravity pull."
        )
    elif deviation_pct > 0:
        # Price above max pain -> expect pull down
        signal = "BEARISH"
        confidence = min(0.80, 0.50 + (abs(deviation_pct) - MAX_PAIN_DEVIATION_PCT) * 0.015)
        description = (
            f"{currency} spot ${index_price:,.0f} is {deviation_pct:.1f}% above "
            f"max pain ${max_pain_strike:,.0f} ({best_expiry} expiry, {dte}d). "
            f"Expect gravitational pull downward before expiry."
        )
    else:
        # Price below max pain -> expect pull up
        signal = "BULLISH"
        confidence = min(0.80, 0.50 + (abs(deviation_pct) - MAX_PAIN_DEVIATION_PCT) * 0.015)
        description = (
            f"{currency} spot ${index_price:,.0f} is {abs(deviation_pct):.1f}% below "
            f"max pain ${max_pain_strike:,.0f} ({best_expiry} expiry, {dte}d). "
            f"Expect gravitational pull upward before expiry."
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(deviation_pct, 2),
        "description": description,
        "source": "deribit_max_pain",
        "currency": currency,
        "max_pain_strike": max_pain_strike,
        "index_price": index_price,
        "expiry": best_expiry,
        "dte": dte,
    }


# ---------------------------------------------------------------------------
# Strategy 3: Put/Call Ratio
# ---------------------------------------------------------------------------

def put_call_ratio(currency="BTC"):
    """
    Compute aggregate put/call open interest ratio.

    PCR > 1.2 = excessive fear = contrarian BULLISH.
    PCR < 0.6 = excessive greed = contrarian BEARISH.

    Returns signal dict or None.
    """
    summaries = _get_book_summaries(currency)
    if not summaries:
        return None

    total_call_oi = 0.0
    total_put_oi = 0.0

    for item in summaries:
        name = item.get("instrument_name", "")
        parsed = _parse_instrument_name(name)
        if parsed is None:
            continue

        oi = item.get("open_interest", 0)
        if oi <= 0:
            continue

        if parsed["option_type"] == "C":
            total_call_oi += oi
        else:
            total_put_oi += oi

    if total_call_oi <= 0:
        return None

    pcr = total_put_oi / total_call_oi

    if pcr > PCR_BEARISH_THRESHOLD:
        signal = "BULLISH"
        confidence = min(0.80, 0.50 + (pcr - PCR_BEARISH_THRESHOLD) * 0.15)
        description = (
            f"{currency} put/call ratio = {pcr:.2f} (puts: {total_put_oi:,.0f}, "
            f"calls: {total_call_oi:,.0f}). Excessive fear -- contrarian bullish."
        )
    elif pcr < PCR_BULLISH_THRESHOLD:
        signal = "BEARISH"
        confidence = min(0.80, 0.50 + (PCR_BULLISH_THRESHOLD - pcr) * 0.25)
        description = (
            f"{currency} put/call ratio = {pcr:.2f} (puts: {total_put_oi:,.0f}, "
            f"calls: {total_call_oi:,.0f}). Excessive greed -- contrarian bearish."
        )
    else:
        signal = "NEUTRAL"
        confidence = 0.3
        description = (
            f"{currency} put/call ratio = {pcr:.2f} (puts: {total_put_oi:,.0f}, "
            f"calls: {total_call_oi:,.0f}). Normal range, no extreme sentiment."
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(pcr, 3),
        "description": description,
        "source": "deribit_put_call_ratio",
        "currency": currency,
        "total_put_oi": total_put_oi,
        "total_call_oi": total_call_oi,
    }


# ---------------------------------------------------------------------------
# Aggregator: get all options signals
# ---------------------------------------------------------------------------

def get_options_signals():
    """
    Run all three options strategies across BTC and ETH.
    Returns list of signal dicts (non-None results only).
    """
    signals = []

    for currency in CURRENCIES:
        for strategy_fn in (risk_reversal_25delta, max_pain_gravity, put_call_ratio):
            try:
                result = strategy_fn(currency)
                if result is not None:
                    signals.append(result)
            except Exception as exc:
                logger.warning(
                    "Options signal %s(%s) failed: %s",
                    strategy_fn.__name__, currency, exc,
                )

    logger.info("Options signals: %d results from %d strategies x %d currencies",
                len(signals), 3, len(CURRENCIES))
    return signals


# ---------------------------------------------------------------------------
# Pick generator: convert signals into scanner-compatible picks
# ---------------------------------------------------------------------------

def generate_options_picks():
    """
    Convert options signals into alpha_engine pick format.

    Only generates picks for non-NEUTRAL signals with confidence >= 0.5.
    Returns list of pick dicts compatible with scanner.py signals format.
    """
    signals = get_options_signals()
    now = datetime.now(timezone.utc)
    picks = []

    for sig in signals:
        if sig["signal"] == "NEUTRAL":
            continue
        if sig["confidence"] < 0.5:
            continue

        currency = sig["currency"]
        symbol = SYMBOL_MAP.get(currency, f"{currency}USDT")
        strategy = sig["source"]
        direction = sig["signal"]
        signal_type = "BUY" if direction == "BULLISH" else "SELL"

        pick_id = f"options_{strategy}_{symbol}_{now.strftime('%Y%m%d%H%M')}"

        # Avoid duplicate IDs
        existing_ids = {p["id"] for p in picks}
        base_id = pick_id
        suffix = 0
        while pick_id in existing_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"

        picks.append({
            "id": pick_id,
            "strategy": strategy,
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal_type,
            "entry_price": None,  # Signal-based, no specific entry
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": None,
            "stop_loss": None,
            "confidence": sig["confidence"],
            "ml_score": None,
            "status": "SIGNAL",
            "source_system": "deribit_options",
            "created_at": now.isoformat(),
            "options_data": {
                "signal_type": sig["source"],
                "value": sig["value"],
                "description": sig["description"],
                "currency": currency,
            },
        })

    logger.info("Generated %d options picks from %d signals", len(picks), len(signals))
    return picks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 70)
    print("Deribit Options Signals")
    print("=" * 70)

    sigs = get_options_signals()
    for s in sigs:
        emoji = {"BULLISH": "+", "BEARISH": "-", "NEUTRAL": "~"}
        print(f"\n[{emoji.get(s['signal'], '?')}] {s['source']} ({s['currency']})")
        print(f"    Signal:     {s['signal']}")
        print(f"    Confidence: {s['confidence']}")
        print(f"    Value:      {s['value']}")
        print(f"    {s['description']}")

    print(f"\n{'=' * 70}")
    picks = generate_options_picks()
    print(f"Generated {len(picks)} actionable pick(s)")
    for p in picks:
        print(f"  [{p['signal_type']}] {p['symbol']} via {p['strategy']} "
              f"(conf: {p['confidence']})")

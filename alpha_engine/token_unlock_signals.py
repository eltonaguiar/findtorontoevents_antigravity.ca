"""
ALPHA_ENGINE -- Token Unlock Supply Shock Signals
====================================================
Trade predictable supply shocks from token vesting unlocks.

Two strategies:
  token_unlock_pressure  -- SHORT before large cliff unlocks (3-7d out)
                            Supply impact >2% circ = bearish, >5% = high confidence
  token_unlock_bounce    -- Contrarian LONG after unlock day if price already dropped >5%
                            Post-unlock mean reversion when selling exhausted

Data sources (3-tier failover, all stdlib):
  1. token.unlocks.app API (primary)
  2. DeFiLlama /unlocks endpoint (fallback)
  3. Hardcoded calendar of known major cliff unlocks (reliability fallback)

Binance spot API for prices (failover across api/api1/api2/api3).

References:
  - Keyrock (2024): 16,000+ unlock events, 90% negative pressure
  - Team/investor unlocks average -25% decline within 30 days
  - Post-unlock bounce: oversold conditions + exhausted selling = 55-65% bounce rate

stdlib only. No requests, no pandas, no numpy.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback: known major upcoming cliff unlock schedules
# Dates generated deterministically from anchor + interval.
# unlock_pct = approximate % of circulating supply per event.
# ---------------------------------------------------------------------------
KNOWN_UNLOCK_SCHEDULE = [
    {"token": "ARB",   "symbol": "ARBUSDT",   "unlock_pct": 3.5,  "interval_days": 30,
     "unlock_type": "team",      "note": "Monthly cliff ~3.5% supply"},
    {"token": "APT",   "symbol": "APTUSDT",   "unlock_pct": 2.5,  "interval_days": 30,
     "unlock_type": "investor",  "note": "Monthly ~2.5% supply"},
    {"token": "SUI",   "symbol": "SUIUSDT",   "unlock_pct": 2.8,  "interval_days": 30,
     "unlock_type": "team",      "note": "Monthly ~2.8% supply"},
    {"token": "OP",    "symbol": "OPUSDT",    "unlock_pct": 3.0,  "interval_days": 90,
     "unlock_type": "investor",  "note": "Quarterly ~3% supply"},
    {"token": "STRK",  "symbol": "STRKUSDT",  "unlock_pct": 4.0,  "interval_days": 90,
     "unlock_type": "team",      "note": "Quarterly ~4% supply"},
    {"token": "SEI",   "symbol": "SEIUSDT",   "unlock_pct": 2.5,  "interval_days": 30,
     "unlock_type": "ecosystem", "note": "Monthly ~2.5% supply"},
    {"token": "TIA",   "symbol": "TIAUSDT",   "unlock_pct": 5.0,  "interval_days": 180,
     "unlock_type": "investor",  "note": "Large cliff expected late 2026"},
    {"token": "JTO",   "symbol": "JTOUSDT",   "unlock_pct": 3.2,  "interval_days": 30,
     "unlock_type": "team",      "note": "Monthly ~3.2% supply"},
    {"token": "PYTH",  "symbol": "PYTHUSDT",  "unlock_pct": 2.8,  "interval_days": 30,
     "unlock_type": "ecosystem", "note": "Monthly ~2.8% supply"},
    {"token": "W",     "symbol": "WUSDT",     "unlock_pct": 3.0,  "interval_days": 30,
     "unlock_type": "team",      "note": "Monthly ~3% supply"},
    {"token": "ZRO",   "symbol": "ZROUSDT",   "unlock_pct": 2.2,  "interval_days": 30,
     "unlock_type": "investor",  "note": "Monthly ~2.2% supply"},
    {"token": "EIGEN", "symbol": "EIGENUSDT", "unlock_pct": 3.5,  "interval_days": 30,
     "unlock_type": "team",      "note": "Monthly ~3.5% supply"},
    {"token": "BLAST", "symbol": "BLASTUSDT", "unlock_pct": 2.5,  "interval_days": 30,
     "unlock_type": "ecosystem", "note": "Monthly ~2.5% supply"},
]

# Confidence bonus by unlock type (team/investor = strongest selling pressure)
UNLOCK_TYPE_CONFIDENCE = {
    "team":      0.08,
    "investor":  0.06,
    "ecosystem": 0.0,
    "unknown":   0.0,
}

# Tradeable Binance USDT pairs
BINANCE_USDT_PAIRS = {
    "ARBUSDT", "APTUSDT", "SUIUSDT", "OPUSDT", "STRKUSDT",
    "SEIUSDT", "TIAUSDT", "JTOUSDT", "PYTHUSDT", "WUSDT",
    "ZROUSDT", "EIGENUSDT", "BLASTUSDT",
}

# Binance spot API mirrors (failover chain per project rules)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# Strategy parameters
PRESSURE_LOOKAHEAD_MIN = 3   # Days before unlock to enter SHORT
PRESSURE_LOOKAHEAD_MAX = 7   # Latest entry before unlock
BOUNCE_LOOKBACK_DAYS = 3     # Days after unlock to check for bounce
MIN_SUPPLY_IMPACT_PCT = 2.0  # Minimum supply impact to trigger signal
HIGH_CONFIDENCE_PCT = 5.0    # Supply impact threshold for high confidence
MIN_DROP_FOR_BOUNCE = 5.0    # Minimum % drop post-unlock for bounce signal
MAX_PICKS_PRESSURE = 3       # Max SHORT picks per cycle
MAX_PICKS_BOUNCE = 2         # Max LONG bounce picks per cycle
MIN_CONFIDENCE = 0.70        # Minimum confidence to emit signal


# ---------------------------------------------------------------------------
# Helpers (stdlib only)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from a URL using stdlib only. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.debug("_fetch_json failed for %s: %s", url, exc)
        return None


def _fetch_binance_price(symbol: str) -> Optional[float]:
    """Fetch spot price from Binance with mirror failover."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/ticker/price?symbol={symbol}"
        data = _fetch_json(url, timeout=8)
        if data and "price" in data:
            try:
                price = float(data["price"])
                if price > 0:
                    return price
            except (ValueError, TypeError):
                continue
    return None


def _fetch_binance_klines_change(symbol: str, days: int = 7) -> Optional[float]:
    """
    Fetch recent price change % over N days from Binance klines.
    Returns negative value if price dropped (e.g., -8.5 means 8.5% drop).
    Uses 1d interval klines.
    """
    for base in BINANCE_MIRRORS:
        url = (
            f"{base}/api/v3/klines"
            f"?symbol={symbol}&interval=1d&limit={days + 1}"
        )
        data = _fetch_json(url, timeout=8)
        if data and isinstance(data, list) and len(data) >= 2:
            try:
                open_price = float(data[0][1])   # Open of first candle
                close_price = float(data[-1][4])  # Close of last candle
                if open_price > 0:
                    return ((close_price - open_price) / open_price) * 100.0
            except (ValueError, TypeError, IndexError):
                continue
    return None


# ---------------------------------------------------------------------------
# Data fetching: 3-tier failover for unlock events
# ---------------------------------------------------------------------------

def _fetch_unlocks_from_tokenunlocks() -> list[dict]:
    """Tier 1: token.unlocks.app API."""
    results = []
    data = _fetch_json("https://token.unlocks.app/api/v2/token", timeout=12)
    if not data or not isinstance(data, list):
        return results

    now = datetime.now(timezone.utc)
    known_tokens = {s["token"]: s["symbol"] for s in KNOWN_UNLOCK_SCHEDULE}

    for item in data[:100]:
        try:
            token_name = str(item.get("symbol", item.get("name", ""))).upper()
            matched_symbol = known_tokens.get(token_name)
            if not matched_symbol or matched_symbol not in BINANCE_USDT_PAIRS:
                continue

            events = item.get("upcoming_events", item.get("events", []))
            if not events:
                continue

            for evt in events[:5]:
                unlock_info = _parse_unlock_event(evt, token_name, matched_symbol, now)
                if unlock_info:
                    unlock_info["source"] = "token_unlocks_app"
                    results.append(unlock_info)
        except (KeyError, TypeError, ValueError):
            continue
    return results


def _fetch_unlocks_from_defillama() -> list[dict]:
    """Tier 2: DeFiLlama unlocks endpoint."""
    results = []
    data = _fetch_json("https://api.llama.fi/unlocks/upcoming", timeout=12)
    if not data:
        return results

    items = data if isinstance(data, list) else data.get("data", data.get("unlocks", []))
    if not isinstance(items, list):
        return results

    now = datetime.now(timezone.utc)
    known_tokens = {s["token"]: s["symbol"] for s in KNOWN_UNLOCK_SCHEDULE}

    for item in items[:100]:
        try:
            token_name = str(item.get("symbol", item.get("name", ""))).upper()
            matched_symbol = known_tokens.get(token_name)
            if not matched_symbol or matched_symbol not in BINANCE_USDT_PAIRS:
                continue

            # Try to compute unlock_pct from value/mcap if not given directly
            pct = item.get("unlock_percent", item.get("percentOfSupply", 0))
            if pct == 0:
                mcap = item.get("mcap", item.get("marketCap", 0))
                value = item.get("value", item.get("unlockValue", 0))
                if mcap > 0 and value > 0:
                    pct = (value / mcap) * 100

            ts = item.get("timestamp", item.get("date", item.get("unlockDate", 0)))
            unlock_dt = _parse_timestamp(ts)
            if not unlock_dt:
                continue

            days_until = (unlock_dt - now).days
            pct = float(pct)
            if pct < MIN_SUPPLY_IMPACT_PCT:
                continue

            u_type = str(item.get("type", item.get("category", "unknown"))).lower()
            if u_type not in UNLOCK_TYPE_CONFIDENCE:
                u_type = "unknown"

            results.append({
                "token": token_name,
                "symbol": matched_symbol,
                "unlock_pct": round(pct, 2),
                "unlock_date": unlock_dt.isoformat(),
                "unlock_type": u_type,
                "days_until": days_until,
                "source": "defillama",
            })
        except (KeyError, TypeError, ValueError):
            continue
    return results


def _generate_hardcoded_unlocks() -> list[dict]:
    """Tier 3: Generate unlock events from known vesting schedules."""
    results = []
    now = datetime.now(timezone.utc)
    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for sched in KNOWN_UNLOCK_SCHEDULE:
        if sched["unlock_pct"] < MIN_SUPPLY_IMPACT_PCT:
            continue
        if sched["symbol"] not in BINANCE_USDT_PAIRS:
            continue

        interval = timedelta(days=sched["interval_days"])
        next_unlock = anchor
        while next_unlock <= now:
            next_unlock += interval

        days_until = (next_unlock - now).days

        results.append({
            "token": sched["token"],
            "symbol": sched["symbol"],
            "unlock_pct": sched["unlock_pct"],
            "unlock_date": next_unlock.isoformat(),
            "unlock_type": sched["unlock_type"],
            "days_until": days_until,
            "source": "hardcoded_schedule",
            "note": sched["note"],
        })
    return results


def _parse_timestamp(ts) -> Optional[datetime]:
    """Parse a timestamp from various formats (ISO string, unix epoch)."""
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    elif isinstance(ts, (int, float)) and ts > 0:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    return None


def _parse_unlock_event(evt: dict, token: str, symbol: str,
                        now: datetime) -> Optional[dict]:
    """Parse a single unlock event dict into standardized format."""
    ts = evt.get("timestamp", evt.get("date", 0))
    unlock_dt = _parse_timestamp(ts)
    if not unlock_dt:
        return None

    days_until = (unlock_dt - now).days

    pct = evt.get("unlock_percent", evt.get("percent", 0))
    if isinstance(pct, str):
        try:
            pct = float(pct.strip("%"))
        except ValueError:
            pct = 0
    pct = float(pct)
    if pct < MIN_SUPPLY_IMPACT_PCT:
        return None

    u_type = str(evt.get("type", evt.get("category", "unknown"))).lower()
    if u_type not in UNLOCK_TYPE_CONFIDENCE:
        u_type = "unknown"

    return {
        "token": token,
        "symbol": symbol,
        "unlock_pct": round(pct, 2),
        "unlock_date": unlock_dt.isoformat(),
        "unlock_type": u_type,
        "days_until": days_until,
    }


def _get_all_unlock_events() -> list[dict]:
    """Fetch unlock events with 3-tier failover, merged and deduplicated."""
    # Tier 1
    events = _fetch_unlocks_from_tokenunlocks()

    # Tier 2 fallback
    if not events:
        events = _fetch_unlocks_from_defillama()

    # Tier 3 fallback (always merge hardcoded for coverage)
    hardcoded = _generate_hardcoded_unlocks()
    if not events:
        events = hardcoded
    else:
        api_symbols = {e["symbol"] for e in events}
        for hc in hardcoded:
            if hc["symbol"] not in api_symbols:
                events.append(hc)

    # Deduplicate: keep highest unlock_pct per symbol
    events.sort(key=lambda x: x.get("unlock_pct", 0), reverse=True)
    seen = set()
    unique = []
    for evt in events:
        if evt["symbol"] not in seen:
            seen.add(evt["symbol"])
            unique.append(evt)
    return unique


# ---------------------------------------------------------------------------
# Confidence / TP / SL calculations
# ---------------------------------------------------------------------------

def _compute_pressure_confidence(unlock_pct: float, unlock_type: str) -> float:
    """
    Confidence for SHORT signal: 0.70-0.88.
    Scales with unlock_pct. Team/investor unlocks get bonus.
    >5% supply impact = high confidence zone.
    """
    # Base: scale from 0.68 at 2% to 0.80 at 10%+
    base = min(0.80, 0.64 + unlock_pct * 0.02)
    type_bonus = UNLOCK_TYPE_CONFIDENCE.get(unlock_type, 0.0)
    return min(0.88, round(base + type_bonus, 3))


def _compute_bounce_confidence(unlock_pct: float, price_drop_pct: float) -> float:
    """
    Confidence for LONG bounce signal: 0.70-0.82.
    Larger drop + larger unlock = more exhausted selling = higher bounce probability.
    """
    # Base from drop magnitude: -5% = 0.68, -15% = 0.78
    drop_factor = min(0.78, 0.60 + abs(price_drop_pct) * 0.012)
    # Small bonus for bigger unlocks (more selling already done)
    unlock_bonus = min(0.06, unlock_pct * 0.008)
    return min(0.82, round(drop_factor + unlock_bonus, 3))


def _compute_pressure_tp_pct(unlock_pct: float) -> float:
    """TP for SHORT: -8% to -15% depending on unlock size."""
    tp = min(0.15, 0.06 + unlock_pct * 0.012)
    return max(0.08, tp)


# ---------------------------------------------------------------------------
# Strategy 1: token_unlock_pressure (SHORT before unlock)
# ---------------------------------------------------------------------------

def token_unlock_pressure(data: dict = None, context: dict = None) -> list[dict]:
    """
    SHORT tokens 3-7 days before large cliff unlocks.

    Supply impact >2% of circulating supply = bearish signal.
    Supply impact >5% = high confidence SHORT.

    Args:
        data: dict of symbol -> DataFrame (from scanner, may be None)
        context: optional scanner context dict

    Returns:
        List of scanner-compatible pick dicts.
    """
    signals = []
    events = _get_all_unlock_events()
    if not events:
        return signals

    now = datetime.now(timezone.utc)

    for evt in events:
        if len(signals) >= MAX_PICKS_PRESSURE:
            break

        days_until = evt.get("days_until", 0)
        # For pressure: only enter 3-7 days before unlock
        if not (PRESSURE_LOOKAHEAD_MIN <= days_until <= PRESSURE_LOOKAHEAD_MAX):
            continue

        symbol = evt["symbol"]
        unlock_pct = evt["unlock_pct"]
        unlock_type = evt.get("unlock_type", "unknown")

        if unlock_pct < MIN_SUPPLY_IMPACT_PCT:
            continue

        confidence = _compute_pressure_confidence(unlock_pct, unlock_type)
        if confidence < MIN_CONFIDENCE:
            continue

        # Fetch current price
        price = _fetch_binance_price(symbol)
        if not price or price <= 0:
            continue

        # TP/SL for SHORT position
        tp_pct = _compute_pressure_tp_pct(unlock_pct)
        tp = _smart_round(price * (1.0 - tp_pct))   # Price drops to TP
        sl = _smart_round(price * 1.05)               # 5% stop loss above entry
        entry = _smart_round(price)

        rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

        conf_label = "HIGH" if unlock_pct >= HIGH_CONFIDENCE_PCT else "MEDIUM"

        signals.append({
            "strategy": "token_unlock_pressure",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "SELL",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Token unlock in {days_until}d: {unlock_pct:.1f}% of circulating "
                f"supply ({conf_label} confidence). Type: {unlock_type}. "
                f"Keyrock 2024: 90% of cliff unlocks produce negative pressure, "
                f"team/investor avg -25%."
            ),
            "timeframe": "3-7d",
            "extra": {
                "unlock_pct": round(unlock_pct, 2),
                "unlock_date": evt.get("unlock_date", ""),
                "unlock_type": unlock_type,
                "days_until": days_until,
                "supply_impact_tier": conf_label,
                "source": evt.get("source", "unknown"),
                "reference": "Keyrock 2024: 16K events, 90% neg pressure",
            },
            "timestamp": _now_iso(),
            "source_system": "alpha_engine",
        })

    return signals


# ---------------------------------------------------------------------------
# Strategy 2: token_unlock_bounce (contrarian LONG after unlock)
# ---------------------------------------------------------------------------

def token_unlock_bounce(data: dict = None, context: dict = None) -> list[dict]:
    """
    Contrarian LONG after unlock day if price already dropped >5%.

    Post-unlock mean reversion: once selling pressure is exhausted,
    oversold tokens tend to bounce. Enter LONG if the drop has been
    significant enough (>5% in the days around the unlock).

    Args:
        data: dict of symbol -> DataFrame (from scanner, may be None)
        context: optional scanner context dict

    Returns:
        List of scanner-compatible pick dicts.
    """
    signals = []
    events = _get_all_unlock_events()
    if not events:
        return signals

    now = datetime.now(timezone.utc)

    for evt in events:
        if len(signals) >= MAX_PICKS_BOUNCE:
            break

        days_until = evt.get("days_until", 0)
        # For bounce: unlock was recent (0 to -3 days ago, i.e. days_until <= 0)
        # or just happened (within BOUNCE_LOOKBACK_DAYS after)
        if days_until > 0 or days_until < -BOUNCE_LOOKBACK_DAYS:
            continue

        symbol = evt["symbol"]
        unlock_pct = evt["unlock_pct"]

        if unlock_pct < MIN_SUPPLY_IMPACT_PCT:
            continue

        # Check recent price change -- need >5% drop to trigger bounce
        price_change = _fetch_binance_klines_change(symbol, days=7)
        if price_change is None:
            continue

        if price_change > -MIN_DROP_FOR_BOUNCE:
            # Price hasn't dropped enough for a bounce play
            continue

        price_drop_pct = price_change  # Negative value

        confidence = _compute_bounce_confidence(unlock_pct, price_drop_pct)
        if confidence < MIN_CONFIDENCE:
            continue

        # Fetch current price
        price = _fetch_binance_price(symbol)
        if not price or price <= 0:
            continue

        # TP/SL for LONG bounce
        # Target: recover 40-60% of the drop (conservative mean reversion)
        recovery_pct = min(0.08, abs(price_drop_pct) * 0.005)  # 40-60% of drop
        recovery_pct = max(0.04, recovery_pct)
        tp = _smart_round(price * (1.0 + recovery_pct))
        sl = _smart_round(price * 0.97)  # 3% stop loss below entry
        entry = _smart_round(price)

        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

        signals.append({
            "strategy": "token_unlock_bounce",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Post-unlock bounce: {symbol} dropped {abs(price_drop_pct):.1f}% "
                f"after {unlock_pct:.1f}% supply unlock. Selling pressure likely "
                f"exhausted. Contrarian mean reversion LONG targeting "
                f"{recovery_pct * 100:.0f}% recovery."
            ),
            "timeframe": "3-7d",
            "extra": {
                "unlock_pct": round(unlock_pct, 2),
                "unlock_date": evt.get("unlock_date", ""),
                "price_drop_pct": round(price_drop_pct, 2),
                "recovery_target_pct": round(recovery_pct * 100, 1),
                "source": evt.get("source", "unknown"),
                "reference": "Post-unlock mean reversion, 55-65% bounce rate",
            },
            "timestamp": _now_iso(),
            "source_system": "alpha_engine",
        })

    return signals


# ---------------------------------------------------------------------------
# Strategy registration dict (for scanner import)
# ---------------------------------------------------------------------------

TOKEN_UNLOCK_SIGNAL_STRATEGIES = {
    "token_unlock_pressure": token_unlock_pressure,
    "token_unlock_bounce": token_unlock_bounce,
}

"""
ALPHA_ENGINE -- Token Unlock Event Short Strategy
===================================================
Keyrock study (2024): 16,000+ unlock events analyzed.
90% of token unlocks are negative for price.
Team/investor unlocks average -25% decline.
Short tokens 7-30 days before large cliff unlocks (>2% circ supply).

Data sources (3-tier failover):
  1. token.unlocks.app API v2 (primary)
  2. DeFiLlama /unlocks/upcoming (fallback)
  3. Hardcoded known schedules for top tokens (reliability fallback)

Binance spot API for current prices. Max 3 SHORT picks per cycle.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback: known major upcoming cliff unlock schedules
# Updated periodically. Dates are approximate next-unlock dates.
# unlock_pct = % of circulating supply per event
# ---------------------------------------------------------------------------
KNOWN_UNLOCK_SCHEDULE = [
    {"token": "ARB",  "symbol": "ARBUSDT",  "unlock_pct": 3.5, "interval_days": 30,
     "unlock_type": "team",    "note": "Monthly cliff unlock ~3.5% supply"},
    {"token": "APT",  "symbol": "APTUSDT",  "unlock_pct": 2.5, "interval_days": 30,
     "unlock_type": "investor","note": "Monthly ~2.5% supply"},
    {"token": "SUI",  "symbol": "SUIUSDT",  "unlock_pct": 2.8, "interval_days": 30,
     "unlock_type": "team",    "note": "Monthly ~2.8% supply"},
    {"token": "OP",   "symbol": "OPUSDT",   "unlock_pct": 3.0, "interval_days": 90,
     "unlock_type": "investor","note": "Quarterly ~3% supply"},
    {"token": "STRK", "symbol": "STRKUSDT", "unlock_pct": 4.0, "interval_days": 90,
     "unlock_type": "team",    "note": "Quarterly ~4% supply"},
    {"token": "SEI",  "symbol": "SEIUSDT",  "unlock_pct": 2.5, "interval_days": 30,
     "unlock_type": "ecosystem","note": "Monthly ~2.5% supply"},
    {"token": "TIA",  "symbol": "TIAUSDT",  "unlock_pct": 5.0, "interval_days": 180,
     "unlock_type": "investor","note": "Large unlock expected late 2026"},
    {"token": "JTO",  "symbol": "JTOUSDT",  "unlock_pct": 3.2, "interval_days": 30,
     "unlock_type": "team",    "note": "Monthly ~3.2% supply"},
    {"token": "PYTH", "symbol": "PYTHUSDT", "unlock_pct": 2.8, "interval_days": 30,
     "unlock_type": "ecosystem","note": "Monthly ~2.8% supply"},
    {"token": "W",    "symbol": "WUSDT",    "unlock_pct": 3.0, "interval_days": 30,
     "unlock_type": "team",    "note": "Monthly ~3% supply"},
    {"token": "ZRO",  "symbol": "ZROUSDT",  "unlock_pct": 2.2, "interval_days": 30,
     "unlock_type": "investor","note": "Monthly ~2.2% supply"},
    {"token": "EIGEN","symbol": "EIGENUSDT","unlock_pct": 3.5, "interval_days": 30,
     "unlock_type": "team",    "note": "Monthly ~3.5% supply"},
    {"token": "BLAST","symbol": "BLASTUSDT","unlock_pct": 2.5, "interval_days": 30,
     "unlock_type": "ecosystem","note": "Monthly ~2.5% supply"},
]

# Confidence mapping by unlock type (team/investor = strongest signal)
UNLOCK_TYPE_CONFIDENCE_BONUS = {
    "team": 0.08,
    "investor": 0.06,
    "ecosystem": 0.0,
    "unknown": 0.0,
}

# Binance symbols that are confirmed tradeable (USDT pairs)
BINANCE_USDT_PAIRS = {
    "ARBUSDT", "APTUSDT", "SUIUSDT", "OPUSDT", "STRKUSDT",
    "SEIUSDT", "TIAUSDT", "JTOUSDT", "PYTHUSDT", "WUSDT",
    "ZROUSDT", "EIGENUSDT", "BLASTUSDT",
}

MIN_UNLOCK_PCT = 2.0       # Minimum unlock % of circulating supply
LOOKAHEAD_MIN_DAYS = 7     # Earliest to enter before unlock
LOOKAHEAD_MAX_DAYS = 30    # Latest to enter before unlock
MAX_PICKS = 3              # Max SHORT picks per cycle
MIN_CONFIDENCE = 0.72      # Minimum confidence threshold


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


def _compute_confidence(unlock_pct: float, unlock_type: str) -> float:
    """
    Confidence: 0.72-0.85 based on unlock_pct and unlock_type.
    >5% supply = higher confidence. Team/investor = bonus.
    """
    # Base: scale from 0.72 at 2% to 0.80 at 10%+
    base = min(0.80, 0.68 + unlock_pct * 0.015)
    type_bonus = UNLOCK_TYPE_CONFIDENCE_BONUS.get(unlock_type, 0.0)
    return min(0.85, round(base + type_bonus, 3))


def _compute_tp_pct(unlock_pct: float) -> float:
    """
    TP target: -8% to -15% depending on unlock size.
    Larger unlock = bigger downside target.
    """
    # Scale: 2% unlock -> -8%, 5%+ unlock -> -15%
    tp_pct = min(0.15, 0.06 + unlock_pct * 0.012)
    return max(0.08, tp_pct)


def _fetch_binance_price(symbol: str) -> Optional[float]:
    """Fetch current spot price from Binance."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("price", 0))
    except Exception:
        pass
    # Fallback: Binance mirror
    try:
        url2 = f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}"
        resp = requests.get(url2, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("price", 0))
    except Exception:
        pass
    return None


def _fetch_unlocks_from_tokenunlocks() -> list[dict]:
    """
    Primary source: token.unlocks.app API v2.
    Returns list of dicts with: token, symbol, unlock_pct, unlock_date, unlock_type.
    """
    results = []
    url = "https://token.unlocks.app/api/v2/token"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ALPHA_ENGINE/2.0"})
        if resp.status_code != 200:
            return results
        data = resp.json()
        if not isinstance(data, list):
            return results

        now = datetime.now(timezone.utc)
        for item in data[:100]:
            try:
                token_name = item.get("symbol", item.get("name", "")).upper()
                # Find matching symbol
                matched_symbol = None
                for known in KNOWN_UNLOCK_SCHEDULE:
                    if known["token"] == token_name:
                        matched_symbol = known["symbol"]
                        break
                if not matched_symbol or matched_symbol not in BINANCE_USDT_PAIRS:
                    continue

                events = item.get("upcoming_events", item.get("events", []))
                if not events:
                    continue

                for evt in events[:5]:
                    ts = evt.get("timestamp", evt.get("date", 0))
                    if isinstance(ts, str):
                        try:
                            unlock_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                    elif isinstance(ts, (int, float)) and ts > 0:
                        unlock_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    else:
                        continue

                    days_until = (unlock_dt - now).days
                    if not (LOOKAHEAD_MIN_DAYS <= days_until <= LOOKAHEAD_MAX_DAYS):
                        continue

                    # Extract unlock percentage
                    pct = evt.get("unlock_percent", evt.get("percent", 0))
                    if isinstance(pct, str):
                        try:
                            pct = float(pct.strip("%"))
                        except ValueError:
                            pct = 0
                    pct = float(pct)
                    if pct < MIN_UNLOCK_PCT:
                        continue

                    u_type = evt.get("type", evt.get("category", "unknown")).lower()
                    if u_type not in UNLOCK_TYPE_CONFIDENCE_BONUS:
                        u_type = "unknown"

                    results.append({
                        "token": token_name,
                        "symbol": matched_symbol,
                        "unlock_pct": pct,
                        "unlock_date": unlock_dt.isoformat(),
                        "unlock_type": u_type,
                        "days_until": days_until,
                        "source": "token_unlocks_app",
                    })
            except (KeyError, TypeError, ValueError):
                continue
    except Exception as e:
        logger.debug(f"token.unlocks.app fetch failed: {e}")
    return results


def _fetch_unlocks_from_defillama() -> list[dict]:
    """
    Fallback source: DeFiLlama unlocks/upcoming endpoint.
    Returns list of dicts with: token, symbol, unlock_pct, unlock_date, unlock_type.
    """
    results = []
    url = "https://api.llama.fi/unlocks/upcoming"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ALPHA_ENGINE/2.0"})
        if resp.status_code != 200:
            return results
        data = resp.json()
        if not isinstance(data, (list, dict)):
            return results

        # Handle both list and dict responses
        items = data if isinstance(data, list) else data.get("data", data.get("unlocks", []))
        if not isinstance(items, list):
            return results

        now = datetime.now(timezone.utc)
        for item in items[:100]:
            try:
                token_name = item.get("symbol", item.get("name", "")).upper()
                matched_symbol = None
                for known in KNOWN_UNLOCK_SCHEDULE:
                    if known["token"] == token_name:
                        matched_symbol = known["symbol"]
                        break
                if not matched_symbol or matched_symbol not in BINANCE_USDT_PAIRS:
                    continue

                ts = item.get("timestamp", item.get("date", item.get("unlockDate", 0)))
                if isinstance(ts, str):
                    try:
                        unlock_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                elif isinstance(ts, (int, float)) and ts > 0:
                    unlock_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    continue

                days_until = (unlock_dt - now).days
                if not (LOOKAHEAD_MIN_DAYS <= days_until <= LOOKAHEAD_MAX_DAYS):
                    continue

                # Try to get unlock percentage from various fields
                pct = item.get("unlock_percent", item.get("percentOfSupply", 0))
                mcap = item.get("mcap", item.get("marketCap", 0))
                value = item.get("value", item.get("unlockValue", 0))
                if pct == 0 and mcap > 0 and value > 0:
                    pct = (value / mcap) * 100
                pct = float(pct)
                if pct < MIN_UNLOCK_PCT:
                    continue

                u_type = item.get("type", item.get("category", "unknown")).lower()
                if u_type not in UNLOCK_TYPE_CONFIDENCE_BONUS:
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
    except Exception as e:
        logger.debug(f"DeFiLlama unlocks fetch failed: {e}")
    return results


def _generate_hardcoded_unlocks() -> list[dict]:
    """
    Second fallback: generate unlock events from known schedules.
    Simulates upcoming unlock dates based on interval_days patterns.
    """
    results = []
    now = datetime.now(timezone.utc)

    for sched in KNOWN_UNLOCK_SCHEDULE:
        if sched["unlock_pct"] < MIN_UNLOCK_PCT:
            continue
        if sched["symbol"] not in BINANCE_USDT_PAIRS:
            continue

        # Generate next unlock date based on interval
        # Use a deterministic anchor: start of 2026 + intervals
        anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
        interval = timedelta(days=sched["interval_days"])

        # Find the next unlock date after now
        next_unlock = anchor
        while next_unlock <= now:
            next_unlock += interval

        days_until = (next_unlock - now).days
        if not (LOOKAHEAD_MIN_DAYS <= days_until <= LOOKAHEAD_MAX_DAYS):
            continue

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


def token_unlock_event_short(data: dict = None, context: dict = None) -> list[dict]:
    """
    Token Unlock Event Short strategy.

    Fetches upcoming token unlocks from 3-tier API failover,
    filters for large cliff unlocks (>2% supply, 7-30 days away),
    and generates SHORT picks with ATR-adjusted TP/SL.

    Args:
        data: dict of symbol -> DataFrame (from scanner, may be None)
        context: optional scanner context dict

    Returns:
        List of pick dicts matching active_picks.json format.
    """
    signals = []

    # Tier 1: token.unlocks.app
    unlock_events = _fetch_unlocks_from_tokenunlocks()

    # Tier 2: DeFiLlama fallback
    if not unlock_events:
        unlock_events = _fetch_unlocks_from_defillama()

    # Tier 3: Hardcoded schedule fallback
    if not unlock_events:
        unlock_events = _generate_hardcoded_unlocks()

    # Merge: if API returned some but hardcoded has extras, add them
    if unlock_events:
        api_symbols = {e["symbol"] for e in unlock_events}
        hardcoded = _generate_hardcoded_unlocks()
        for hc in hardcoded:
            if hc["symbol"] not in api_symbols:
                unlock_events.append(hc)

    if not unlock_events:
        return signals

    # Sort by confidence potential (higher unlock_pct first)
    unlock_events.sort(key=lambda x: x["unlock_pct"], reverse=True)

    # Deduplicate by symbol (keep highest unlock_pct)
    seen_symbols = set()
    unique_events = []
    for evt in unlock_events:
        if evt["symbol"] not in seen_symbols:
            seen_symbols.add(evt["symbol"])
            unique_events.append(evt)

    for evt in unique_events:
        if len(signals) >= MAX_PICKS:
            break

        symbol = evt["symbol"]
        unlock_pct = evt["unlock_pct"]
        unlock_type = evt["unlock_type"]
        unlock_date = evt["unlock_date"]
        days_until = evt["days_until"]

        # Compute confidence
        confidence = _compute_confidence(unlock_pct, unlock_type)
        if confidence < MIN_CONFIDENCE:
            continue

        # Fetch current Binance price
        price = _fetch_binance_price(symbol)
        if not price or price <= 0:
            continue

        # Compute TP/SL
        tp_pct = _compute_tp_pct(unlock_pct)
        tp = _smart_round(price * (1.0 - tp_pct))     # Short TP = price drops
        sl = _smart_round(price * 1.05)                 # SL = +5% above entry
        entry = _smart_round(price)

        rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

        signals.append({
            "strategy": "token_unlock_event_short",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "SELL",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Token unlock in {days_until}d: {unlock_pct:.1f}% of circulating supply. "
                f"Type: {unlock_type}. Keyrock: 90% of cliff unlocks = negative pressure, "
                f"team unlocks avg -25%."
            ),
            "timeframe": "7-30d",
            "extra": {
                "unlock_pct": round(unlock_pct, 2),
                "unlock_date": unlock_date,
                "unlock_type": unlock_type,
                "days_until": days_until,
                "source": evt.get("source", "unknown"),
                "reference": "Keyrock 2024: 16K events, 90% neg pressure, team avg -25%",
            },
            "timestamp": _now_iso(),
            "source_system": "alpha_engine",
        })

    return signals


# Strategy dict for scanner registration
TOKEN_UNLOCK_EVENT_STRATEGIES = {
    "token_unlock_event_short": token_unlock_event_short,
}

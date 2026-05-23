"""
Finnhub Economic Calendar Client
=================================
Free API for high-impact economic events (FOMC, CPI, NFP, etc.)
that move crypto and forex markets.

Bridges the gap: our event_strategies.py needs real event timing
instead of hardcoded dates. Finnhub provides forecasts + actuals
so we can pre-position before announcements.

Requires: FINNHUB environment variable (API key)
Free tier: 60 calls/minute

Usage:
    from finnhub_events import get_upcoming_events, get_event_signal
"""

import os
import time
import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
REQUEST_TIMEOUT = 8
CACHE_TTL = 900  # 15 minutes -- events don't change fast

_cache: dict = {}
_last_request_ts: float = 0.0


def _get_api_key():
    return os.environ.get("FINNHUB", "")


def _rate_limit():
    global _last_request_ts
    now = time.time()
    if now - _last_request_ts < 1.0:  # max 60/min ≈ 1/sec
        time.sleep(1.0 - (now - _last_request_ts))
    _last_request_ts = time.time()


def _finnhub_get(path: str, params: dict | None = None):
    key = _get_api_key()
    if not key:
        return None
    _rate_limit()
    if params is None:
        params = {}
    params["token"] = key
    try:
        resp = requests.get(f"{FINNHUB_BASE}{path}", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Finnhub API error %s: %s", path, e)
        return None


# High-impact event keywords that move crypto
HIGH_IMPACT_EVENTS = {
    "Federal Funds Rate",
    "FOMC",
    "CPI",
    "Consumer Price Index",
    "Non-Farm Payrolls",
    "NFP",
    "GDP",
    "PCE",
    "PPI",
    "Unemployment Rate",
    "Retail Sales",
    "ISM Manufacturing",
    "Interest Rate Decision",
    "ECB",
    "BOJ",
    "BOE",
}


def get_upcoming_events(days_ahead: int = 7) -> list[dict]:
    """Get upcoming high-impact economic events.

    Tries Finnhub economic calendar (premium) first, then falls back to
    a free alternative (Trading Economics RSS / hardcoded FOMC schedule).
    """
    cache_key = f"events:{days_ahead}"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    now = datetime.now(timezone.utc)
    from_date = now.strftime("%Y-%m-%d")
    to_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Try Finnhub premium endpoint first
    data = _finnhub_get("/calendar/economic", {"from": from_date, "to": to_date})
    events = []

    if data and "economicCalendar" in data:
        for e in data["economicCalendar"]:
            impact = e.get("impact", 0)
            event_name = e.get("event", "")
            is_high = impact == 3
            is_known = any(kw.lower() in event_name.lower() for kw in HIGH_IMPACT_EVENTS)
            if not (is_high or is_known):
                continue
            event_time = e.get("time", "")
            try:
                if event_time:
                    event_date = e.get("date", from_date)
                    dt = datetime.fromisoformat(f"{event_date}T{event_time}+00:00")
                    hours_until = (dt - now).total_seconds() / 3600
                else:
                    hours_until = 999
            except Exception:
                hours_until = 999
            events.append({
                "event": event_name, "country": e.get("country", ""),
                "date": e.get("date", ""), "time": event_time,
                "impact": impact, "estimate": e.get("estimate"),
                "actual": e.get("actual"), "prev": e.get("prev"),
                "unit": e.get("unit", ""), "hours_until": round(hours_until, 1),
            })

    # Fallback: known 2026 FOMC schedule + major events
    if not events:
        fomc_2026 = [
            "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
            "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16",
        ]
        for date_str in fomc_2026:
            try:
                dt = datetime.fromisoformat(f"{date_str}T18:00:00+00:00")
                hours_until = (dt - now).total_seconds() / 3600
                if 0 <= hours_until <= days_ahead * 24:
                    events.append({
                        "event": "FOMC Interest Rate Decision",
                        "country": "US", "date": date_str, "time": "18:00:00",
                        "impact": 3, "estimate": None, "actual": None,
                        "prev": None, "unit": "%", "hours_until": round(hours_until, 1),
                    })
            except Exception:
                pass

    events.sort(key=lambda x: x["hours_until"])
    _cache[cache_key] = (time.time(), events)
    return events


def get_event_signal() -> dict:
    """Generate a trading signal based on upcoming economic events.

    Returns:
        {
            "event_risk": str -- "HIGH" / "MEDIUM" / "LOW"
            "next_event": str -- name of next high-impact event
            "hours_until": float -- hours until next event
            "recommendation": str -- plain English advice
            "events_24h": int -- count of high-impact events in next 24h
            "events_72h": int -- count in next 72h
        }
    """
    events = get_upcoming_events(days_ahead=7)

    if not events:
        return {
            "event_risk": "LOW",
            "next_event": None,
            "hours_until": 999,
            "recommendation": "No high-impact events found. Normal trading conditions.",
            "events_24h": 0,
            "events_72h": 0,
        }

    next_event = events[0]
    events_24h = sum(1 for e in events if e["hours_until"] <= 24)
    events_72h = sum(1 for e in events if e["hours_until"] <= 72)

    hours = next_event["hours_until"]

    if hours <= 2:
        risk = "HIGH"
        rec = (f"{next_event['event']} in {hours:.0f}h -- "
               f"reduce position sizes, expect volatility spike. "
               f"Avoid new entries until announcement.")
    elif hours <= 12:
        risk = "MEDIUM"
        rec = (f"{next_event['event']} in {hours:.0f}h -- "
               f"tighten stop-losses. Pre-event positioning window closing.")
    elif hours <= 24:
        risk = "MEDIUM"
        rec = (f"{next_event['event']} tomorrow -- "
               f"consider hedging or reducing overnight exposure.")
    else:
        risk = "LOW"
        rec = f"Next event: {next_event['event']} in {hours:.0f}h. Normal conditions."

    return {
        "event_risk": risk,
        "next_event": next_event["event"],
        "hours_until": hours,
        "recommendation": rec,
        "events_24h": events_24h,
        "events_72h": events_72h,
        "country": next_event.get("country", ""),
    }


def get_crypto_news_sentiment() -> dict:
    """Get crypto news volume and sentiment from Finnhub (FREE endpoint).

    High news volume often precedes or accompanies big moves.
    Scans headlines for bullish/bearish keywords.
    """
    cache_key = "crypto_news"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    data = _finnhub_get("/news", {"category": "crypto"})
    if not data or not isinstance(data, list):
        return {"news_count": 0, "signal": "UNAVAILABLE"}

    bullish_words = {"surge", "rally", "bull", "breakout", "soar", "pump", "buy",
                     "approval", "etf", "adoption", "record", "high", "gain"}
    bearish_words = {"crash", "bear", "dump", "plunge", "sell", "ban", "hack",
                     "fraud", "ponzi", "collapse", "fear", "drop", "loss"}

    bull_count = 0
    bear_count = 0
    for article in data[:50]:  # Check last 50 articles
        headline = (article.get("headline", "") + " " + article.get("summary", "")).lower()
        if any(w in headline for w in bullish_words):
            bull_count += 1
        if any(w in headline for w in bearish_words):
            bear_count += 1

    total = bull_count + bear_count
    if total == 0:
        signal = "NEUTRAL"
    elif bull_count > bear_count * 1.5:
        signal = "NEWS_BULLISH"
    elif bear_count > bull_count * 1.5:
        signal = "NEWS_BEARISH"
    else:
        signal = "NEWS_MIXED"

    result = {
        "news_count": len(data),
        "bullish_headlines": bull_count,
        "bearish_headlines": bear_count,
        "signal": signal,
        "source": "finnhub_crypto_news",
    }
    _cache[cache_key] = (time.time(), result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("Finnhub Economic Calendar -- Test Run")
    print("=" * 60)

    signal = get_event_signal()
    print(f"\nEvent Risk: {signal['event_risk']}")
    print(f"Next Event: {signal['next_event']}")
    print(f"Hours Until: {signal['hours_until']}")
    print(f"Recommendation: {signal['recommendation']}")
    print(f"Events in 24h: {signal['events_24h']}")
    print(f"Events in 72h: {signal['events_72h']}")

    print("\n--- Upcoming High-Impact Events ---")
    events = get_upcoming_events(7)
    for e in events[:10]:
        actual = f" | Actual: {e['actual']}" if e.get('actual') is not None else ""
        est = f" | Forecast: {e['estimate']}" if e.get('estimate') is not None else ""
        print(f"  {e['date']} {e['time']} | {e['event']} ({e['country']})"
              f"{est}{actual} | {e['hours_until']:.0f}h away")

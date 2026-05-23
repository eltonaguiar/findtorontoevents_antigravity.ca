"""
Google Trends Sentiment Signal
===============================
100% FREE -- no API key, no registration needed.

Uses Google Trends search interest as a retail sentiment proxy.
Academically validated: Kristoufek 2013 (Scientific Reports) confirmed
Google Trends Granger-causes BTC price movements.

Key signals:
- "buy bitcoin" spikes >2x normal = retail FOMO = local top warning
- "bitcoin crash" spikes >2x normal = capitulation = potential bottom
- FOMO ratio (buy/crash) extreme values = contrarian signal

Uses urllib (no pytrends dependency) for maximum compatibility.
"""

import json
import time
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CACHE_TTL = 1800  # 30 min -- Google Trends updates slowly
_cache: dict = {}


def _get_trends_data(keywords: list[str], timeframe: str = "now 7-d") -> dict | None:
    """Fetch Google Trends interest data using the unofficial widget API.

    This approach doesn't need pytrends -- it hits the public explore endpoint
    that powers the Google Trends website.

    Returns dict mapping keyword -> latest interest value (0-100).
    """
    cache_key = f"gtrends:{','.join(keywords)}:{timeframe}"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    try:
        # Build the comparison URL parameters
        comparisonItem = []
        for kw in keywords:
            comparisonItem.append({
                "keyword": kw,
                "geo": "",
                "time": timeframe,
            })

        req_data = {
            "comparisonItem": comparisonItem,
            "category": 0,
            "property": "",
        }

        # Step 1: Get the widget token
        encoded = urllib.parse.quote(json.dumps(req_data))
        url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=0&req={encoded}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode("utf-8")

        # Response starts with ")]}\',\n" which we need to strip
        if raw.startswith(")]}'"):
            raw = raw[5:]

        widget_data = json.loads(raw)
        widgets = widget_data.get("widgets", [])

        # Find the multiline widget (time series data)
        timeline_widget = None
        for w in widgets:
            if w.get("id") == "TIMESERIES":
                timeline_widget = w
                break

        if not timeline_widget:
            return None

        # Step 2: Get the actual timeline data
        token = timeline_widget.get("token", "")
        widget_req = timeline_widget.get("request", {})
        encoded_req = urllib.parse.quote(json.dumps(widget_req))

        data_url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=0&req={encoded_req}&token={token}"
        req2 = urllib.request.Request(data_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        resp2 = urllib.request.urlopen(req2, timeout=10)
        raw2 = resp2.read().decode("utf-8")

        if raw2.startswith(")]}'"):
            raw2 = raw2[5:]

        timeline = json.loads(raw2)
        points = timeline.get("default", {}).get("timelineData", [])

        if not points:
            return None

        # Get the most recent data point for each keyword
        result = {}
        latest = points[-1]
        values = latest.get("value", [])
        for i, kw in enumerate(keywords):
            if i < len(values):
                result[kw] = values[i]
            else:
                result[kw] = 0

        # Also compute 7-day average for baseline
        if len(points) >= 7:
            for i, kw in enumerate(keywords):
                avg = sum(p["value"][i] for p in points[-7:] if i < len(p.get("value", []))) / 7
                result[f"{kw}_avg7d"] = round(avg, 1)

        _cache[cache_key] = (time.time(), result)
        return result

    except Exception as e:
        logger.warning("Google Trends fetch failed: %s", e)
        return None


def get_crypto_sentiment() -> dict:
    """Get crypto retail sentiment from Google Trends.

    Returns:
        {
            "fomo_score": int -- "buy bitcoin" interest (0-100)
            "fear_score": int -- "bitcoin crash" interest (0-100)
            "fomo_ratio": float -- buy/crash ratio (>3 = top warning, <0.5 = bottom signal)
            "signal": str -- "FOMO_TOP" / "CAPITULATION_BOTTOM" / "NEUTRAL"
            "recommendation": str -- plain English
            "source": "google_trends"
        }
    """
    data = _get_trends_data(["buy bitcoin", "bitcoin crash"])

    if not data:
        return {
            "fomo_score": 50,
            "fear_score": 50,
            "fomo_ratio": 1.0,
            "signal": "UNAVAILABLE",
            "recommendation": "Google Trends data unavailable. No retail sentiment signal.",
            "source": "google_trends",
        }

    buy_score = data.get("buy bitcoin", 50)
    crash_score = data.get("bitcoin crash", 50)
    buy_avg = data.get("buy bitcoin_avg7d", 50)
    crash_avg = data.get("bitcoin crash_avg7d", 50)

    # FOMO ratio: how much "buy" interest vs "crash" interest
    fomo_ratio = buy_score / max(crash_score, 1)

    # Spike detection: current vs 7-day average
    buy_spike = buy_score / max(buy_avg, 1)
    crash_spike = crash_score / max(crash_avg, 1)

    signal = "NEUTRAL"
    rec = "Normal retail sentiment. No extreme signals."

    if fomo_ratio > 3.0 or buy_spike > 2.0:
        signal = "FOMO_TOP"
        rec = (f"Retail FOMO detected: 'buy bitcoin' interest is {buy_score}/100 "
               f"({buy_spike:.1f}x normal). When retail rushes in, smart money exits. "
               f"Consider tightening take-profits or reducing long exposure.")
    elif fomo_ratio < 0.5 or crash_spike > 2.0:
        signal = "CAPITULATION_BOTTOM"
        rec = (f"Retail panic detected: 'bitcoin crash' interest is {crash_score}/100 "
               f"({crash_spike:.1f}x normal). Extreme fear often marks bottoms. "
               f"Consider accumulation or contrarian long entries.")
    elif buy_spike > 1.5:
        signal = "MILD_FOMO"
        rec = (f"Moderate retail interest rising: 'buy bitcoin' at {buy_score}/100 "
               f"({buy_spike:.1f}x normal). Not extreme yet but watch for acceleration.")
    elif crash_spike > 1.5:
        signal = "MILD_FEAR"
        rec = (f"Moderate fear rising: 'bitcoin crash' at {crash_score}/100 "
               f"({crash_spike:.1f}x normal). Getting closer to capitulation signal.")

    return {
        "fomo_score": buy_score,
        "fear_score": crash_score,
        "fomo_ratio": round(fomo_ratio, 2),
        "buy_spike": round(buy_spike, 2),
        "crash_spike": round(crash_spike, 2),
        "signal": signal,
        "recommendation": rec,
        "source": "google_trends",
    }


def get_altcoin_sentiment() -> dict:
    """Get altcoin-specific Google Trends signals.

    Tracks search interest for major altcoins -- rising interest in
    a specific altcoin often precedes price movement.
    """
    alts = ["solana crypto", "ethereum price", "xrp news"]
    data = _get_trends_data(alts)

    if not data:
        return {"available": False}

    result = {"available": True, "source": "google_trends"}
    for alt in alts:
        result[alt] = data.get(alt, 0)
        result[f"{alt}_avg"] = data.get(f"{alt}_avg7d", 0)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("Google Trends Crypto Sentiment -- Test Run")
    print("=" * 60)

    sentiment = get_crypto_sentiment()
    print(f"\nFOMO Score (buy bitcoin): {sentiment['fomo_score']}/100")
    print(f"Fear Score (bitcoin crash): {sentiment['fear_score']}/100")
    print(f"FOMO Ratio: {sentiment['fomo_ratio']}")
    print(f"Signal: {sentiment['signal']}")
    print(f"Recommendation: {sentiment['recommendation']}")

    print("\n--- Altcoin Sentiment ---")
    alt = get_altcoin_sentiment()
    if alt.get("available"):
        for k, v in alt.items():
            if k not in ("available", "source"):
                print(f"  {k}: {v}")

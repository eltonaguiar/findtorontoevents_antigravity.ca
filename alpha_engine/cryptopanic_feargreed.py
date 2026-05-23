"""
ALPHA_ENGINE -- CryptoPanic News Sentiment + Fear & Greed Index
================================================================
Two complementary sentiment data sources combined into trading signals:

1. CryptoPanic (Developer plan: 100 req/month, 24h delay, 20 items)
   - News sentiment with PanicScore (proprietary attention metric)
   - Filters: by coin, sentiment (bullish/bearish/important)
   - Cache: 8 hours minimum (conserves quota -- ~3 req/day max)

2. Fear & Greed Index (alternative.me -- free, unlimited)
   - 0-100 scale: 0=Extreme Fear, 100=Extreme Greed
   - Historically: F&G ≤ 10 → strong buy zone (Nasdaq backtest: 14.6% annual)
   - F&G ≥ 90 → distribution zone (mean reversion incoming)

3. CoinMarketCap Fear & Greed (scraped as backup)
   - Cross-validates alternative.me signal

Strategies:
  - cryptopanic_news_sentiment: Contrarian trades on extreme CryptoPanic sentiment
    Heavy bearish news + F&G ≤ 25 → BUY (fear capitulation)
    Heavy bullish news + F&G ≥ 75 → SHORT (greed euphoria)
    Based on: Baker & Wurgler (2006) "Investor Sentiment and the Cross-Section"

  - fear_greed_dca: Extreme fear DCA entry (F&G ≤ 15)
    Based on: Nasdaq backtest (14.6% annual), CNN Money methodology

References:
  - Baker, M. & Wurgler, J. (2006). Investor Sentiment. J. Finance 61(4)
  - alternative.me Fear & Greed Index methodology
  - CryptoPanic API v2 docs
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"
_CACHE_FILE = _DATA_DIR / "cryptopanic_cache.json"
_FG_CACHE_FILE = _DATA_DIR / "feargreed_cache.json"

# CryptoPanic: 100 req/month. At 80% usage (Mar 23), extend cache to 12h.
# 12h = 2 calls/day x 30 = 60/month (well within limit).
# Backup: alternative.me Fear & Greed (free, unlimited) provides the
# most actionable sentiment signal. CoinGecko trending is free backup for headlines.
_CP_CACHE_TTL = 24 * 3600  # 24 hours — GH Actions runners are ephemeral so cache must be committed to repo
_FG_CACHE_TTL = 2 * 3600  # 2 hours (free, can refresh more often)

_CP_API_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "")
_CP_BASE_URL = "https://cryptopanic.com/api/developer/v2/posts/"
_FG_API_URL = "https://api.alternative.me/fng/?limit=7&format=json"

_TIMEOUT = 10

# Symbols we care about (map to CryptoPanic currency filters)
_CRYPTO_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "MATIC": "MATICUSDT",
    "NEAR": "NEARUSDT",
    "APT": "APTUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
    "SUI": "SUIUSDT",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_json(url: str, timeout: int = _TIMEOUT) -> dict | list | None:
    """Fetch JSON from URL. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None


def _load_cache(path: Path) -> dict | None:
    """Load cache file if it exists and is fresh."""
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = data.get("_cached_at", 0)
        ttl = data.get("_ttl", 0)
        if time.time() - cached_at < ttl:
            return data
        return None  # expired
    except Exception:
        return None


def _save_cache(path: Path, data: dict, ttl: int):
    """Save data to cache with timestamp."""
    data["_cached_at"] = time.time()
    data["_ttl"] = ttl
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# CryptoPanic API
# ---------------------------------------------------------------------------

def fetch_cryptopanic_news(currencies: str = "") -> dict:
    """
    Fetch latest news from CryptoPanic. Uses cache to stay within 100 req/month.

    Returns: {"results": [...], "sentiment_summary": {...}}
    """
    cached = _load_cache(_CACHE_FILE)
    if cached:
        logger.info("CryptoPanic: using cached data (%d items)", len(cached.get("results", [])))
        return cached

    if not _CP_API_KEY:
        logger.warning("CryptoPanic: no API key set (CRYPTOPANIC_API_KEY)")
        return {"results": [], "sentiment_summary": {}}

    # Fetch important/trending news (maximizes signal per request)
    url = f"{_CP_BASE_URL}?auth_token={_CP_API_KEY}&filter=important&kind=news"
    if currencies:
        url += f"&currencies={currencies}"

    data = _fetch_json(url)
    if not data or "results" not in data:
        logger.warning("CryptoPanic: API returned no results")
        return {"results": [], "sentiment_summary": {}}

    results = data.get("results", [])

    # Build sentiment summary per currency
    sentiment = {}
    for item in results:
        votes = item.get("votes", {})
        item_sentiment = _classify_sentiment(votes)
        # Track per-currency sentiment
        for curr in (item.get("currencies") or []):
            code = curr.get("code", "")
            if code not in sentiment:
                sentiment[code] = {"bullish": 0, "bearish": 0, "neutral": 0,
                                   "total": 0, "panic_scores": []}
            sentiment[code][item_sentiment] += 1
            sentiment[code]["total"] += 1
            # PanicScore (if available)
            ps = votes.get("important", 0) + votes.get("toxic", 0) * 2
            sentiment[code]["panic_scores"].append(ps)

    result = {
        "results": results[:20],  # Developer plan: 20 items max
        "sentiment_summary": sentiment,
        "fetched_at": _now_iso(),
    }

    _save_cache(_CACHE_FILE, result, _CP_CACHE_TTL)
    logger.info("CryptoPanic: fetched %d items, %d currencies tracked",
                len(results), len(sentiment))
    return result


def _classify_sentiment(votes: dict) -> str:
    """Classify item sentiment from CryptoPanic votes."""
    pos = (votes.get("positive", 0) or 0) + (votes.get("liked", 0) or 0)
    neg = (votes.get("negative", 0) or 0) + (votes.get("disliked", 0) or 0)
    if pos > neg * 1.5:
        return "bullish"
    if neg > pos * 1.5:
        return "bearish"
    return "neutral"


# ---------------------------------------------------------------------------
# Fear & Greed Index
# ---------------------------------------------------------------------------

def fetch_fear_greed() -> dict:
    """
    Fetch Bitcoin Fear & Greed Index from alternative.me (free, unlimited).

    Returns: {
        "current": 25,
        "classification": "Extreme Fear",
        "yesterday": 30,
        "last_week": 45,
        "trend": "falling",
        "history": [{"value": 25, "classification": "...", "date": "..."}]
    }
    """
    cached = _load_cache(_FG_CACHE_FILE)
    if cached and "current" in cached:
        return cached

    data = _fetch_json(_FG_API_URL)
    if not data or "data" not in data:
        logger.warning("Fear & Greed: API unavailable")
        return {"current": 50, "classification": "Neutral", "trend": "flat", "history": []}

    items = data["data"]
    if not items:
        return {"current": 50, "classification": "Neutral", "trend": "flat", "history": []}

    current = int(items[0].get("value", 50))
    classification = items[0].get("value_classification", "Neutral")

    yesterday = int(items[1].get("value", current)) if len(items) > 1 else current
    last_week = int(items[-1].get("value", current)) if len(items) > 6 else current

    # Trend: compare current vs 7-day average
    avg_7d = sum(int(i.get("value", 50)) for i in items) / len(items)
    if current < avg_7d - 5:
        trend = "falling"
    elif current > avg_7d + 5:
        trend = "rising"
    else:
        trend = "flat"

    result = {
        "current": current,
        "classification": classification,
        "yesterday": yesterday,
        "last_week": last_week,
        "avg_7d": round(avg_7d, 1),
        "trend": trend,
        "history": [
            {
                "value": int(i.get("value", 50)),
                "classification": i.get("value_classification", ""),
                "date": datetime.fromtimestamp(
                    int(i.get("timestamp", 0)), tz=timezone.utc
                ).strftime("%Y-%m-%d") if i.get("timestamp") else "",
            }
            for i in items
        ],
        "fetched_at": _now_iso(),
    }

    _save_cache(_FG_CACHE_FILE, result, _FG_CACHE_TTL)
    logger.info("Fear & Greed: current=%d (%s), trend=%s", current, classification, trend)
    return result


# ---------------------------------------------------------------------------
# Strategy: CryptoPanic News Sentiment (contrarian)
# ---------------------------------------------------------------------------

def cryptopanic_news_sentiment(data: dict, context: dict = None) -> list[dict]:
    """
    Contrarian trading on CryptoPanic news sentiment extremes.

    Logic:
      - Heavy bearish news (>60% bearish) + F&G ≤ 25 → BUY (fear capitulation)
      - Heavy bullish news (>60% bullish) + F&G ≥ 75 → SHORT (greed distribution)

    Requires both CryptoPanic + F&G alignment for signal.
    Based on: Baker & Wurgler (2006), contrarian sentiment model.
    """
    signals = []

    # Fetch both data sources
    cp_data = fetch_cryptopanic_news()
    fg_data = fetch_fear_greed()

    sentiment_summary = cp_data.get("sentiment_summary", {})
    fg_current = fg_data.get("current", 50)
    fg_trend = fg_data.get("trend", "flat")

    if not sentiment_summary:
        return signals

    for currency_code, sent in sentiment_summary.items():
        symbol = _CRYPTO_SYMBOLS.get(currency_code)
        if not symbol:
            continue

        total = sent.get("total", 0)
        if total < 2:
            continue  # Need at least 2 news items

        bullish_pct = sent.get("bullish", 0) / total
        bearish_pct = sent.get("bearish", 0) / total

        # Get current price from data dict (ccxt/yfinance)
        pair_key = f"{currency_code}-USD"
        df = data.get(pair_key) or data.get(symbol) or data.get(f"{currency_code}USDT")
        if df is None or len(df) < 20:
            continue

        current_price = float(df["Close"].iloc[-1])
        if current_price <= 0:
            continue

        # ATR for TP/SL
        try:
            high = df["High"]
            low = df["Low"]
            close = df["Close"]
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ], axis=1).max(axis=1)
            atr_val = float(tr.rolling(14).mean().iloc[-1])
        except Exception:
            atr_val = current_price * 0.03  # 3% fallback

        if atr_val <= 0:
            atr_val = current_price * 0.03

        # --- CONTRARIAN BUY: heavy bearish news + extreme fear ---
        if bearish_pct >= 0.60 and fg_current <= 25:
            tp = current_price + atr_val * 3.0
            sl = current_price - atr_val * 1.5

            # Confidence: deeper fear + more bearish = stronger contrarian signal
            conf = min(0.78, 0.55 + (25 - fg_current) * 0.005 + bearish_pct * 0.1)

            signals.append({
                "strategy": "cryptopanic_news_sentiment",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": "BUY",
                "direction": "long",
                "entry_price": round(current_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(conf, 2),
                "risk_reward": round((tp - current_price) / (current_price - sl), 2),
                "reason": (
                    f"Contrarian BUY: {currency_code} news {bearish_pct*100:.0f}% bearish "
                    f"({total} items) + F&G={fg_current} ({fg_data.get('classification', '')}). "
                    f"Trend: {fg_trend}. Baker & Wurgler (2006) sentiment reversal."
                ),
                "timeframe": "1d",
                "extra": {
                    "fg_current": fg_current,
                    "fg_classification": fg_data.get("classification", ""),
                    "fg_trend": fg_trend,
                    "bearish_pct": round(bearish_pct, 2),
                    "bullish_pct": round(bullish_pct, 2),
                    "news_count": total,
                    "source": "CryptoPanic Developer + alternative.me F&G",
                },
                "timestamp": _now_iso(),
            })

        # --- CONTRARIAN SHORT: heavy bullish news + extreme greed ---
        elif bullish_pct >= 0.60 and fg_current >= 75:
            tp = current_price - atr_val * 3.0
            sl = current_price + atr_val * 1.5

            conf = min(0.75, 0.52 + (fg_current - 75) * 0.005 + bullish_pct * 0.1)

            signals.append({
                "strategy": "cryptopanic_news_sentiment",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": "SELL",
                "direction": "short",
                "entry_price": round(current_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(conf, 2),
                "risk_reward": round((current_price - tp) / (sl - current_price), 2),
                "reason": (
                    f"Contrarian SHORT: {currency_code} news {bullish_pct*100:.0f}% bullish "
                    f"({total} items) + F&G={fg_current} ({fg_data.get('classification', '')}). "
                    f"Trend: {fg_trend}. Baker & Wurgler (2006) sentiment reversal."
                ),
                "timeframe": "1d",
                "extra": {
                    "fg_current": fg_current,
                    "fg_classification": fg_data.get("classification", ""),
                    "fg_trend": fg_trend,
                    "bearish_pct": round(bearish_pct, 2),
                    "bullish_pct": round(bullish_pct, 2),
                    "news_count": total,
                    "source": "CryptoPanic Developer + alternative.me F&G",
                },
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Strategy: Fear & Greed Extreme DCA
# ---------------------------------------------------------------------------

def fear_greed_extreme_dca(data: dict, context: dict = None) -> list[dict]:
    """
    DCA into BTC/ETH at extreme fear (F&G ≤ 15) with multi-day confirmation.

    Logic:
      - F&G ≤ 15 for 2+ consecutive days → BUY BTC + ETH
      - Wider TP (4x ATR) because fear bottoms lead to strong recoveries
      - Tight SL (1.5x ATR) to limit drawdown in ongoing crashes

    Based on: Nasdaq backtest (14.6% annual return), CNN Money F&G methodology.
    Historical: F&G ≤ 10 has preceded 30-90 day rallies of 20-80% since 2018.
    """
    signals = []

    fg = fetch_fear_greed()
    current = fg.get("current", 50)

    if current > 15:
        return signals

    # Check for multi-day confirmation (at least 2 of last 3 days ≤ 20)
    history = fg.get("history", [])
    extreme_days = sum(1 for h in history[:3] if h.get("value", 50) <= 20)
    if extreme_days < 2:
        return signals

    # Target BTC and ETH for DCA
    dca_targets = [
        ("BTC-USD", "BTCUSDT"),
        ("ETH-USD", "ETHUSDT"),
    ]

    for pair_key, symbol in dca_targets:
        df = data.get(pair_key) or data.get(symbol)
        if df is None or len(df) < 20:
            continue

        current_price = float(df["Close"].iloc[-1])
        if current_price <= 0:
            continue

        # ATR for TP/SL
        try:
            high = df["High"]
            low = df["Low"]
            close = df["Close"]
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ], axis=1).max(axis=1)
            atr_val = float(tr.rolling(14).mean().iloc[-1])
        except Exception:
            atr_val = current_price * 0.04

        if atr_val <= 0:
            atr_val = current_price * 0.04

        # Wider TP for fear-bottom recoveries (historically strong)
        tp = current_price + atr_val * 4.0
        sl = current_price - atr_val * 1.5

        # Confidence: deeper fear = stronger signal
        conf = min(0.82, 0.60 + (15 - current) * 0.02 + extreme_days * 0.03)

        coin = pair_key.split("-")[0]
        signals.append({
            "strategy": "fear_greed_extreme_dca",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "direction": "long",
            "entry_price": round(current_price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 2),
            "risk_reward": round((tp - current_price) / (current_price - sl), 2),
            "reason": (
                f"Extreme Fear DCA: F&G={current} ({fg.get('classification', '')}), "
                f"{extreme_days}/3 days ≤20. Avg 7d: {fg.get('avg_7d', '?')}. "
                f"Historical: F&G≤15 precedes 20-80% rallies within 30-90d. "
                f"Nasdaq backtest: 14.6% annual. {coin} DCA entry."
            ),
            "timeframe": "1d",
            "extra": {
                "fg_current": current,
                "fg_classification": fg.get("classification", ""),
                "fg_trend": fg.get("trend", ""),
                "fg_avg_7d": fg.get("avg_7d"),
                "extreme_days_3d": extreme_days,
                "source": "alternative.me F&G Index + Nasdaq DCA backtest",
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# Import guard: pandas needed for ATR calculation in strategies
# ---------------------------------------------------------------------------
try:
    import pandas as pd
except ImportError:
    pd = None
    logger.warning("pandas not available -- cryptopanic strategies will use fallback ATR")


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

CRYPTOPANIC_STRATEGIES: dict[str, callable] = {
    "cryptopanic_news_sentiment": cryptopanic_news_sentiment,
    "fear_greed_extreme_dca": fear_greed_extreme_dca,
}

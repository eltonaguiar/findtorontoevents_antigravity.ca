"""
ALPHA_ENGINE -- Social Sentiment Signal (Galaxy Score)
=====================================================
Composite social sentiment scoring using FREE APIs:
  1. CoinGecko -- sentiment votes, trending rank, watchlist size
  2. Alternative.me -- Crypto Fear & Greed Index
  3. CoinGecko trending -- social buzz proxy

Produces a 0-100 "Galaxy Score" equivalent that combines:
  - CoinGecko sentiment_votes_up_percentage (crowd bullishness)
  - Fear & Greed Index (market-wide sentiment)
  - Trending rank (social buzz)
  - Watchlist portfolio users (attention proxy)

NOTE: LunarCrush v4 API requires paid subscription ($50+/mo).
      This module provides equivalent signals using free alternatives.

References:
  - Kristoufek (2013): Google Trends + social sentiment predicts BTC price.
  - Bouri et al. (2022): social media sentiment significantly affects crypto returns.
  - LunarCrush research: social volume leads price by 24-72h on average.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

try:
    from config import CRYPTO_SYMBOLS
except ImportError:
    CRYPTO_SYMBOLS = {}

# -- Configuration ----------------------------------------------------------

GALAXY_BULLISH_THRESHOLD = 70
GALAXY_BEARISH_THRESHOLD = 30
ALTRANK_STRONG = 50

# CoinGecko ID mapping (symbol -> coingecko id)
_CG_IDS: dict[str, str] = {
    "BTC-USD":  "bitcoin",
    "ETH-USD":  "ethereum",
    "SOL-USD":  "solana",
    "BNB-USD":  "binancecoin",
    "XRP-USD":  "ripple",
    "ADA-USD":  "cardano",
    "AVAX-USD": "avalanche-2",
    "LINK-USD": "chainlink",
    "DOGE-USD": "dogecoin",
    "DOT-USD":  "polkadot",
    "TAO-USD":  "bittensor",
    "NEAR-USD": "near",
    "TRX-USD":  "tron",
    "RNDR-USD": "render-token",
    "SUI-USD":  "sui",
    "PEPE-USD": "pepe",
    "WIF-USD":  "dogwifcoin",
    "BONK-USD": "bonk",
}

# Backward-compat alias used by scanner.py imports
_LC_SYMBOLS: dict[str, str] = {k: k.replace("-USD", "") for k in _CG_IDS}


# -- Helpers -----------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 12) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "ALPHA_ENGINE/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# -- Cache to avoid hammering free APIs ------------------------------------

_fear_greed_cache: dict[str, tuple[float, float]] = {}
_trending_cache: dict[str, tuple[float, set]] = {}
_cg_cache: dict[str, tuple[float, dict]] = {}

CACHE_TTL = 300  # 5 min


def _get_fear_greed() -> float:
    """Fetch Fear & Greed Index (0-100). Cached 5 min."""
    now = time.time()
    cached = _fear_greed_cache.get("value")
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    data = _fetch_json("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data and len(data["data"]) > 0:
        score = float(data["data"][0].get("value", 50))
        _fear_greed_cache["value"] = (now, score)
        return score
    return 50.0


def _get_trending_symbols() -> set[str]:
    """Fetch CoinGecko trending coins. Returns set of uppercase symbols. Cached 5 min."""
    now = time.time()
    cached = _trending_cache.get("trending")
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    data = _fetch_json("https://api.coingecko.com/api/v3/search/trending")
    symbols = set()
    if data and "coins" in data:
        for coin in data["coins"]:
            item = coin.get("item", {})
            sym = item.get("symbol", "").upper()
            if sym:
                symbols.add(sym)
    _trending_cache["trending"] = (now, symbols)
    return symbols


def _get_coingecko_sentiment(cg_id: str, symbol: str) -> Optional[dict]:
    """Fetch CoinGecko sentiment and community data for a coin. Cached 5 min."""
    now = time.time()
    cached = _cg_cache.get(symbol)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    url = (
        f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        f"?localization=false&tickers=false&market_data=false"
        f"&community_data=true&developer_data=false&sparkline=false"
    )
    data = _fetch_json(url)
    if data is None:
        return None

    result = {
        "sentiment_up": data.get("sentiment_votes_up_percentage", 50.0),
        "sentiment_down": data.get("sentiment_votes_down_percentage", 50.0),
        "watchlist_users": data.get("watchlist_portfolio_users", 0),
    }
    _cg_cache[symbol] = (now, result)
    return result


# -- Score Computation -------------------------------------------------------

def get_lunarcrush_score(symbol: str) -> Optional[dict]:
    """
    Compute composite social sentiment score for a symbol.

    Returns dict with same interface as original LunarCrush module:
      - galaxy_score: 0-100 composite social score
      - alt_rank: trending rank (lower = more buzz)
      - social_volume: watchlist users as social attention proxy
      - social_score: CoinGecko sentiment up %
      - sentiment: normalized 1-5 scale
      - signal: "BULLISH" | "BEARISH" | "NEUTRAL"
    """
    cg_id = _CG_IDS.get(symbol)
    if not cg_id:
        return None

    # 1. Fear & Greed (market-wide, 0-100)
    fg_score = _get_fear_greed()

    # 2. Trending (is this coin trending on CoinGecko?)
    trending = _get_trending_symbols()
    short_sym = symbol.replace("-USD", "")
    is_trending = short_sym in trending
    trending_bonus = 15.0 if is_trending else 0.0

    # 3. CoinGecko sentiment (per-coin)
    cg_data = _get_coingecko_sentiment(cg_id, symbol)
    if cg_data is None:
        sentiment_up = 50.0
        watchlist = 0
    else:
        sentiment_up = cg_data.get("sentiment_up", 50.0) or 50.0
        watchlist = cg_data.get("watchlist_users", 0) or 0

    # 4. Composite Galaxy Score (0-100)
    #    40% CoinGecko sentiment + 40% Fear & Greed + trending bonus
    galaxy_score = max(0, min(100, sentiment_up * 0.4 + fg_score * 0.4 + trending_bonus))

    # Alt rank: trending coins get low ranks, others scale inversely with score
    if is_trending:
        trending_list = sorted(trending)
        alt_rank = trending_list.index(short_sym) + 1 if short_sym in trending_list else 10
    else:
        alt_rank = 500 + int((100 - galaxy_score) * 5)

    # Sentiment on 1-5 scale
    sentiment_5 = 1.0 + (sentiment_up / 100.0) * 4.0

    # Signal classification
    if galaxy_score >= GALAXY_BULLISH_THRESHOLD:
        signal = "BULLISH"
    elif galaxy_score <= GALAXY_BEARISH_THRESHOLD:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    return {
        "symbol": symbol,
        "galaxy_score": round(galaxy_score, 1),
        "alt_rank": int(alt_rank),
        "social_volume": int(watchlist),
        "social_score": round(sentiment_up, 1),
        "sentiment": round(sentiment_5, 2),
        "signal": signal,
        "fear_greed": round(fg_score, 0),
        "is_trending": is_trending,
        "source": "CoinGecko+FearGreed (free)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_lunarcrush_scores_batch(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch social scores for multiple symbols.
    Returns dict of {symbol: score_dict}. Missing symbols omitted.
    CoinGecko free tier ~30 req/min, so we throttle.
    """
    results = {}
    for i, sym in enumerate(symbols):
        score = get_lunarcrush_score(sym)
        if score is not None:
            results[sym] = score
        if i < len(symbols) - 1:
            time.sleep(2.5)
    return results


# ---------------------------------------------------------------------------
# Strategy: Galaxy Score Momentum (uses composite social score)
# ---------------------------------------------------------------------------

def galaxy_score_momentum(data: dict, context: dict | None = None) -> list[dict]:
    """
    Social Sentiment Momentum Strategy.
    Fires on extreme social momentum shifts.
    """
    signals = []

    for symbol in list(_CG_IDS.keys()):
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 20:
                continue

            close = df["Close"]
            price = float(close.iloc[-1])

            lc_data = get_lunarcrush_score(symbol)
            if lc_data is None:
                continue

            galaxy = lc_data["galaxy_score"]
            alt_rank = lc_data["alt_rank"]
            sentiment = lc_data["sentiment"]

            cat_info = CRYPTO_SYMBOLS.get(symbol, {})
            cat = cat_info.get("cat", "crypto")

            # --- BULLISH: Galaxy > 70 + good AltRank = social momentum ---
            if galaxy >= GALAXY_BULLISH_THRESHOLD and alt_rank < ALTRANK_STRONG:
                conf = min(0.85, 0.50 + (galaxy - 50) / 200 + (50 - alt_rank) / 300)
                tp = round(price * 1.025, 2) if price > 1 else round(price * 1.025, 6)
                sl = round(price * 0.985, 2) if price > 1 else round(price * 0.985, 6)
                rr = abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 1.67

                signals.append({
                    "strategy": "galaxy_score_momentum",
                    "symbol": symbol,
                    "category": cat,
                    "signal_type": "BUY",
                    "direction": "LONG",
                    "entry_price": round(price, 2) if price > 1 else round(price, 6),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Social Score {galaxy:.0f} (BULLISH), "
                        f"F&G={lc_data['fear_greed']:.0f}, "
                        f"Trending={'YES' if lc_data['is_trending'] else 'no'}, "
                        f"sentiment {sentiment:.1f}/5 -- "
                        f"social momentum leads price by 24-72h"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": 50,
                    "volume_ratio": 1.0,
                    "extra": {
                        "galaxy_score": galaxy,
                        "alt_rank": alt_rank,
                        "social_volume": lc_data["social_volume"],
                        "sentiment": sentiment,
                        "fear_greed": lc_data["fear_greed"],
                        "source": lc_data["source"],
                        "reference": "Kristoufek (2013), Bouri et al. (2022)",
                    },
                    "research_basis": "Social sentiment leads price by 24-72h",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "galaxy_score": galaxy,
                })

            # --- BEARISH: Galaxy < 30 but as CONTRARIAN LONG ---
            elif galaxy <= GALAXY_BEARISH_THRESHOLD and sentiment < 2.5:
                conf = min(0.70, 0.45 + (30 - galaxy) / 100)
                tp = round(price * 1.03, 2) if price > 1 else round(price * 1.03, 6)
                sl = round(price * 0.975, 2) if price > 1 else round(price * 0.975, 6)
                rr = abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 1.2

                signals.append({
                    "strategy": "galaxy_score_momentum",
                    "symbol": symbol,
                    "category": cat,
                    "signal_type": "BUY",
                    "direction": "LONG",
                    "entry_price": round(price, 2) if price > 1 else round(price, 6),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Social Score {galaxy:.0f} (CAPITULATION), "
                        f"F&G={lc_data['fear_greed']:.0f}, "
                        f"sentiment {sentiment:.1f}/5 -- "
                        f"extreme fear = contrarian LONG opportunity"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": 50,
                    "volume_ratio": 1.0,
                    "extra": {
                        "galaxy_score": galaxy,
                        "alt_rank": alt_rank,
                        "social_volume": lc_data["social_volume"],
                        "sentiment": sentiment,
                        "mode": "contrarian",
                        "fear_greed": lc_data["fear_greed"],
                        "source": lc_data["source"],
                        "reference": "Contrarian sentiment reversal",
                    },
                    "research_basis": "Contrarian sentiment reversal -- extreme fear buys",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "galaxy_score": galaxy,
                })

        except Exception:
            continue

    return signals


# -- Strategy registry -------------------------------------------------------

LUNARCRUSH_STRATEGIES: dict[str, callable] = {
    "galaxy_score_momentum": galaxy_score_momentum,
}


# -- Self-test ---------------------------------------------------------------
if __name__ == "__main__":
    print("Social Sentiment Module -- Self-Test (CoinGecko + Fear & Greed)")
    print("=" * 65)
    fg = _get_fear_greed()
    print(f"  Fear & Greed Index: {fg:.0f}")
    trending = _get_trending_symbols()
    print(f"  Trending coins: {', '.join(sorted(trending)[:10])}")
    print()
    for sym in ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]:
        result = get_lunarcrush_score(sym)
        if result:
            t = "TRENDING" if result["is_trending"] else ""
            print(f"  {sym}: Galaxy={result['galaxy_score']:.0f} ({result['signal']}) "
                  f"F&G={result['fear_greed']:.0f} "
                  f"Sentiment={result['sentiment']:.1f} "
                  f"Watchlist={result['social_volume']:,} {t}")
        else:
            print(f"  {sym}: [UNAVAILABLE]")
        time.sleep(2.5)

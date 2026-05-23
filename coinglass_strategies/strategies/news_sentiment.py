"""S12: News-Sentiment Classifier — real-time parsing of crypto-related news
and social sentiment to generate directional trading signals.

Sources:
  - CryptoPanic API (free tier, no key required for basic feed)
  - CoinGecko trending (proxy for social momentum)
  - Alternative.me Fear & Greed Index

Logic:
  - Aggregates recent crypto news sentiment (bullish/bearish/neutral)
  - Weights by recency and source credibility
  - Combines with Fear & Greed index for macro context
  - If strong bullish sentiment + extreme fear → high-conviction LONG
  - If strong bearish sentiment + extreme greed → high-conviction SHORT
  - Pure sentiment extremes also generate signals (lower confidence)

This fills the "News-Sentiment & Regulatory Event" gap in the strategy
catalog. Distinct from ape_wisdom_social_momentum (Reddit-only) and
twitter_alpha_calls (Twitter-only).
"""
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .base import Signal

logger = logging.getLogger(__name__)

CRYPTOPANIC_API = "https://cryptopanic.com/api/free/v1/posts/"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"
COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"

# Sentiment history for smoothing
_sentiment_history: Dict[str, List[float]] = {}
_MAX_SENTIMENT_HISTORY = 12  # 3 hours at 15-min intervals

# Symbol to keywords mapping for news relevance
SYMBOL_KEYWORDS = {
    "BTCUSDT": ["bitcoin", "btc", "satoshi", "halving", "mining"],
    "ETHUSDT": ["ethereum", "eth", "vitalik", "merge", "layer 2", "l2", "defi"],
    "SOLUSDT": ["solana", "sol", "phantom", "raydium", "jupiter"],
    "BNBUSDT": ["binance", "bnb", "bsc", "cz"],
    "DOGEUSDT": ["dogecoin", "doge", "elon", "musk", "meme coin"],
}


def _fetch_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed index value with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get(FEAR_GREED_URL, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and len(data["data"]) > 0:
                    return int(data["data"][0]["value"])
        except Exception as e:
            if attempt == 2:
                logger.debug("Fear & Greed fetch failed after 3 attempts: %s", e)
            else:
                _time.sleep(2 * (attempt + 1))
    return None


def _fetch_cryptopanic_news(symbol: str) -> List[Dict]:
    """Fetch recent crypto news from CryptoPanic free API."""
    keywords = SYMBOL_KEYWORDS.get(symbol, [])
    if not keywords:
        return []

    # CryptoPanic free tier: filter by currency
    currency_map = {
        "BTCUSDT": "BTC",
        "ETHUSDT": "ETH",
        "SOLUSDT": "SOL",
        "BNBUSDT": "BNB",
        "DOGEUSDT": "DOGE",
    }
    currency = currency_map.get(symbol, symbol.replace("USDT", ""))

    try:
        resp = requests.get(
            CRYPTOPANIC_API,
            params={
                "currencies": currency,
                "kind": "news",
                "public": "true",
            },
            timeout=10,
            headers={"User-Agent": "CoinglassDNA/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            news_items = []
            for item in results[:20]:  # Last 20 news items
                votes = item.get("votes", {})
                # CryptoPanic provides sentiment votes
                positive = votes.get("positive", 0)
                negative = votes.get("negative", 0)
                important = votes.get("important", 0)
                lol = votes.get("lol", 0)  # Spam/joke indicator

                sentiment_score = 0
                total_votes = positive + negative + important + lol
                if total_votes > 0:
                    sentiment_score = (positive + important * 0.5 - negative - lol * 0.3) / total_votes

                news_items.append({
                    "title": item.get("title", ""),
                    "sentiment_score": sentiment_score,
                    "total_votes": total_votes,
                    "positive": positive,
                    "negative": negative,
                    "published_at": item.get("published_at", ""),
                    "source": item.get("source", {}).get("title", "unknown"),
                })
            return news_items
    except Exception as e:
        logger.debug("CryptoPanic fetch failed for %s: %s", symbol, e)

    return []


def _compute_aggregate_sentiment(news_items: List[Dict]) -> Dict:
    """Compute aggregate sentiment from news items."""
    if not news_items:
        return {"score": 0, "bullish_pct": 50, "bearish_pct": 50, "count": 0}

    weighted_sum = 0
    weight_total = 0
    bullish_count = 0
    bearish_count = 0

    for i, item in enumerate(news_items):
        # Weight by recency (most recent = highest weight)
        recency_weight = 1.0 / (1 + i * 0.15)
        # Weight by vote count (more votes = more trusted)
        vote_weight = math.log1p(item["total_votes"]) / 3.0 if item["total_votes"] > 0 else 0.3

        weight = recency_weight * max(vote_weight, 0.1)
        weighted_sum += item["sentiment_score"] * weight
        weight_total += weight

        if item["sentiment_score"] > 0.1:
            bullish_count += 1
        elif item["sentiment_score"] < -0.1:
            bearish_count += 1

    score = weighted_sum / weight_total if weight_total > 0 else 0
    total = len(news_items)

    return {
        "score": score,
        "bullish_pct": round(bullish_count / total * 100, 1) if total > 0 else 50,
        "bearish_pct": round(bearish_count / total * 100, 1) if total > 0 else 50,
        "count": total,
    }


def _smooth_sentiment(symbol: str, current_score: float) -> float:
    """Apply exponential smoothing to sentiment score."""
    if symbol not in _sentiment_history:
        _sentiment_history[symbol] = []

    history = _sentiment_history[symbol]
    history.append(current_score)

    if len(history) > _MAX_SENTIMENT_HISTORY:
        _sentiment_history[symbol] = history[-_MAX_SENTIMENT_HISTORY:]
        history = _sentiment_history[symbol]

    if len(history) < 2:
        return current_score

    # EMA with alpha=0.3 (recent data weighted more)
    alpha = 0.3
    ema = history[0]
    for val in history[1:]:
        ema = alpha * val + (1 - alpha) * ema
    return ema


def run(symbol: str, recent_rows: list, current_ratios: dict) -> Optional[Signal]:
    """News-sentiment classifier strategy.

    Combines crypto news sentiment with Fear & Greed index for
    directional trading signals.
    """
    # Fetch sentiment data
    news = _fetch_cryptopanic_news(symbol)
    sentiment = _compute_aggregate_sentiment(news)

    if sentiment["count"] < 3:
        return None  # Not enough news to form opinion

    smoothed_score = _smooth_sentiment(symbol, sentiment["score"])

    # Fear & Greed for macro context
    fg_value = _fetch_fear_greed()

    # Decision thresholds
    SENTIMENT_THRESHOLD = 0.25
    FG_EXTREME_FEAR = 25
    FG_EXTREME_GREED = 75

    direction = None
    reason_parts = []

    # Strong sentiment-only signals
    if abs(smoothed_score) < SENTIMENT_THRESHOLD:
        return None  # Sentiment not strong enough

    if smoothed_score > SENTIMENT_THRESHOLD:
        direction = "LONG"
        reason_parts.append(
            f"Bullish news sentiment: {smoothed_score:.3f} "
            f"(raw={sentiment['score']:.3f}, {sentiment['bullish_pct']:.0f}% bullish, "
            f"{sentiment['count']} articles)"
        )
    else:
        direction = "SHORT"
        reason_parts.append(
            f"Bearish news sentiment: {smoothed_score:.3f} "
            f"(raw={sentiment['score']:.3f}, {sentiment['bearish_pct']:.0f}% bearish, "
            f"{sentiment['count']} articles)"
        )

    # Fear & Greed confluence (boosts confidence)
    fg_confluence = False
    if fg_value is not None:
        if direction == "LONG" and fg_value <= FG_EXTREME_FEAR:
            fg_confluence = True
            reason_parts.append(
                f"Fear & Greed extreme fear ({fg_value}). "
                f"Bullish sentiment + fear = contrarian LONG."
            )
        elif direction == "SHORT" and fg_value >= FG_EXTREME_GREED:
            fg_confluence = True
            reason_parts.append(
                f"Fear & Greed extreme greed ({fg_value}). "
                f"Bearish sentiment + greed = contrarian SHORT."
            )
        elif fg_value is not None:
            reason_parts.append(f"Fear & Greed: {fg_value}")

    # Confidence calculation
    sentiment_strength = min(abs(smoothed_score) / 0.5, 1.0)
    article_count_score = min(sentiment["count"] / 15.0, 1.0)
    fg_boost = 0.10 if fg_confluence else 0

    conf = 0.45 + 0.15 * sentiment_strength + 0.10 * article_count_score + fg_boost
    conf = round(min(conf, 0.80), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_news_sentiment",
        confidence=conf,
        reason=" | ".join(reason_parts),
        ratios={
            "sentiment_score": round(smoothed_score, 4),
            "raw_sentiment": round(sentiment["score"], 4),
            "bullish_pct": sentiment["bullish_pct"],
            "bearish_pct": sentiment["bearish_pct"],
            "article_count": sentiment["count"],
            "fear_greed": fg_value,
            "fg_confluence": fg_confluence,
            **current_ratios,
        },
    )

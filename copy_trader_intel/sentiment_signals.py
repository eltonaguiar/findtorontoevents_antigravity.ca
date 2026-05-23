#!/usr/bin/env python3
"""
sentiment_signals.py - Multi-Source Crypto Sentiment Signal Generator
=====================================================================
Aggregates sentiment from multiple free/freemium APIs:

1. CryptoPanic  — Hot crypto news, bullish/bearish vote counts per coin
2. LunarCrush   — Galaxy Score + social volume for top coins
3. Alternative.me — Fear & Greed Index (always free, no auth)

Output: dict of signals per symbol:
  {symbol: {direction, confidence, source, reason}}

Environment variables (Windows User-level env vars supported):
  CRYPTOPANIC_API_KEY  — CryptoPanic API key
  LUNARCRUSH_API       — LunarCrush Bearer token

Usage:
  from copy_trader_intel.sentiment_signals import run, get_sentiment_signal
  signals = run()
  btc_signal = get_sentiment_signal("BTC")
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "sentiment_signals.json"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Top coins to track sentiment for
TOP_COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK",
             "DOT", "MATIC", "SHIB", "PEPE", "ARB", "OP", "SUI", "APT",
             "NEAR", "FIL", "INJ", "TIA", "SEI", "WIF", "BONK", "RENDER"]


# ---------------------------------------------------------------------------
# Env var helpers (Windows PowerShell fallback)
# ---------------------------------------------------------------------------

def _win_env(name: str) -> str:
    """Read a Windows User-level environment variable via PowerShell."""
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"[Environment]::GetEnvironmentVariable('{name}', 'User')"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _get_env(name: str, *alt_names: str) -> str:
    """
    Get env var by name (with optional alternates).
    Falls back to Windows User-level env vars via PowerShell.
    """
    # Try os.environ first
    for n in (name, *alt_names):
        val = os.environ.get(n, "")
        if val:
            return val

    # On Windows, try registry
    if sys.platform == "win32":
        for n in (name, *alt_names):
            val = _win_env(n)
            if val:
                return val

    return ""


def _get_cryptopanic_key() -> str:
    return _get_env("CRYPTOPANIC_API_KEY", "CRYPTOPANIC_KEY")


def _get_lunarcrush_key() -> str:
    return _get_env("LUNARCRUSH_API", "LUNARCRUSH_API_KEY", "LUNARCRUSH_KEY")


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: dict = None, timeout: int = 15) -> Optional[dict]:
    """Make GET request and return parsed JSON, or None on failure."""
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception) as e:
        logger.debug(f"HTTP GET failed: {url[:80]}... -> {e}")
        return None


# ---------------------------------------------------------------------------
# Source 1: CryptoPanic
# ---------------------------------------------------------------------------

def fetch_cryptopanic_sentiment() -> Dict[str, dict]:
    """
    Fetch hot/trending crypto news from CryptoPanic API.
    Count bullish vs bearish sentiment votes per coin.
    Returns: {symbol: {bullish_votes, bearish_votes, total_posts, headlines}}
    """
    api_key = _get_cryptopanic_key()
    if not api_key:
        logger.warning("No CRYPTOPANIC_API_KEY set - skipping CryptoPanic")
        return {}

    sentiment_by_coin: Dict[str, dict] = {}

    # Try multiple filter types for broader coverage
    filters = ["hot", "rising", "bullish", "bearish", "important"]
    posts_seen = set()

    for filt in filters:
        # Build URL with optional currency filter for major coins
        for currencies in ["BTC,ETH,SOL,XRP,DOGE,ADA,AVAX,LINK", ""]:
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&kind=news"
            if filt:
                url += f"&filter={filt}"
            if currencies:
                url += f"&currencies={currencies}"

            data = _http_get(url)
            if not data or "results" not in data:
                continue

            for post in data.get("results", []):
                post_id = post.get("id", "")
                if post_id in posts_seen:
                    continue
                posts_seen.add(post_id)

                # Extract vote counts
                votes = post.get("votes", {})
                positive = votes.get("positive", 0) or 0
                negative = votes.get("negative", 0) or 0
                important = votes.get("important", 0) or 0
                liked = votes.get("liked", 0) or 0

                # Map to coins mentioned
                currencies_list = post.get("currencies", [])
                if not currencies_list:
                    continue

                for curr in currencies_list:
                    code = curr.get("code", "").upper()
                    if not code:
                        continue

                    if code not in sentiment_by_coin:
                        sentiment_by_coin[code] = {
                            "bullish_votes": 0,
                            "bearish_votes": 0,
                            "important_votes": 0,
                            "total_posts": 0,
                            "headlines": [],
                        }

                    sentiment_by_coin[code]["bullish_votes"] += positive + liked
                    sentiment_by_coin[code]["bearish_votes"] += negative
                    sentiment_by_coin[code]["important_votes"] += important
                    sentiment_by_coin[code]["total_posts"] += 1
                    if len(sentiment_by_coin[code]["headlines"]) < 3:
                        sentiment_by_coin[code]["headlines"].append(
                            post.get("title", "")[:120]
                        )

            time.sleep(0.5)  # Rate limiting

        if posts_seen:
            break  # Got data from first successful filter combo

    logger.info(f"CryptoPanic: {len(sentiment_by_coin)} coins, {len(posts_seen)} posts")
    return sentiment_by_coin


def cryptopanic_to_signals(sentiment: Dict[str, dict]) -> Dict[str, dict]:
    """
    Convert CryptoPanic sentiment data into directional signals.
    Bullish if >60% positive votes, bearish if >60% negative.
    """
    signals = {}
    for symbol, data in sentiment.items():
        total_votes = data["bullish_votes"] + data["bearish_votes"]
        if total_votes < 2:
            continue  # Not enough votes

        bull_pct = data["bullish_votes"] / total_votes if total_votes > 0 else 0.5
        bear_pct = data["bearish_votes"] / total_votes if total_votes > 0 else 0.5

        if bull_pct > 0.60:
            direction = "bullish"
            confidence = round(min(0.90, 0.50 + bull_pct * 0.40), 3)
            reason = (f"CryptoPanic: {data['bullish_votes']} bullish vs "
                      f"{data['bearish_votes']} bearish votes across "
                      f"{data['total_posts']} posts ({bull_pct*100:.0f}% positive)")
        elif bear_pct > 0.60:
            direction = "bearish"
            confidence = round(min(0.90, 0.50 + bear_pct * 0.40), 3)
            reason = (f"CryptoPanic: {data['bearish_votes']} bearish vs "
                      f"{data['bullish_votes']} bullish votes across "
                      f"{data['total_posts']} posts ({bear_pct*100:.0f}% negative)")
        else:
            direction = "neutral"
            confidence = 0.40
            reason = (f"CryptoPanic: mixed sentiment "
                      f"({data['bullish_votes']} bull / {data['bearish_votes']} bear)")

        signals[symbol] = {
            "direction": direction,
            "confidence": confidence,
            "source": "cryptopanic",
            "reason": reason,
            "votes_bullish": data["bullish_votes"],
            "votes_bearish": data["bearish_votes"],
            "post_count": data["total_posts"],
            "headlines": data.get("headlines", []),
        }

    return signals


# ---------------------------------------------------------------------------
# Source 2: LunarCrush
# ---------------------------------------------------------------------------

def fetch_lunarcrush_sentiment() -> Dict[str, dict]:
    """
    Fetch Galaxy Score and social volume from LunarCrush API.
    Galaxy Score > 70 = bullish, < 30 = bearish.
    High social volume spike (>2x average) = momentum signal.

    Tries multiple API versions (v4, v3) with graceful fallback.
    Returns: {symbol: {galaxy_score, social_volume, ...}}
    """
    api_key = _get_lunarcrush_key()
    if not api_key:
        logger.warning("No LUNARCRUSH_API set - skipping LunarCrush")
        return {}

    coin_data: Dict[str, dict] = {}

    # Try API v4 (current) - requires Bearer token
    v4_headers = {"Authorization": f"Bearer {api_key}"}

    # Try per-coin endpoints for top coins
    for coin in TOP_COINS[:10]:  # Limit to top 10 to avoid rate limits
        coin_slug = coin.lower()
        # v4 public coin endpoint
        url = f"https://lunarcrush.com/api4/public/coins/{coin_slug}/v1"
        data = _http_get(url, headers=v4_headers)

        if data and "error" not in data:
            coin_info = data.get("data", data)
            if isinstance(coin_info, dict):
                coin_data[coin] = {
                    "galaxy_score": coin_info.get("galaxy_score",
                                   coin_info.get("galaxyScore", 0)),
                    "alt_rank": coin_info.get("alt_rank",
                               coin_info.get("altRank", 0)),
                    "social_volume": coin_info.get("social_volume",
                                    coin_info.get("socialVolume",
                                    coin_info.get("social_mentions", 0))),
                    "social_volume_24h": coin_info.get("social_volume_24h",
                                        coin_info.get("socialVolume24h", 0)),
                    "social_score": coin_info.get("social_score",
                                   coin_info.get("socialScore", 0)),
                    "sentiment": coin_info.get("sentiment",
                                coin_info.get("average_sentiment", 0)),
                    "market_dominance": coin_info.get("market_dominance",
                                       coin_info.get("marketDominance", 0)),
                    "price_change_24h": coin_info.get("percent_change_24h",
                                       coin_info.get("priceChange24h", 0)),
                }
                logger.debug(f"LunarCrush {coin}: galaxy={coin_data[coin]['galaxy_score']}")
        time.sleep(1.5)  # Generous rate limiting for LunarCrush

    # If v4 per-coin didn't work, try v4 list endpoint
    if not coin_data:
        url = "https://lunarcrush.com/api4/public/coins/list/v2"
        data = _http_get(url, headers=v4_headers)
        if data and "error" not in data:
            coins_list = data.get("data", [])
            if isinstance(coins_list, list):
                for coin_info in coins_list:
                    symbol = (coin_info.get("symbol", "") or
                              coin_info.get("s", "")).upper()
                    if symbol in TOP_COINS:
                        coin_data[symbol] = {
                            "galaxy_score": coin_info.get("galaxy_score",
                                           coin_info.get("gs", 0)),
                            "alt_rank": coin_info.get("alt_rank",
                                       coin_info.get("acr", 0)),
                            "social_volume": coin_info.get("social_volume",
                                            coin_info.get("sv", 0)),
                            "social_volume_24h": coin_info.get("social_volume_24h", 0),
                            "social_score": coin_info.get("social_score",
                                           coin_info.get("ss", 0)),
                            "sentiment": coin_info.get("sentiment",
                                        coin_info.get("as", 0)),
                            "market_dominance": coin_info.get("market_dominance", 0),
                            "price_change_24h": coin_info.get("percent_change_24h", 0),
                        }

    # Fallback: try v3 API (older, uses key= param)
    if not coin_data:
        symbols_str = ",".join(TOP_COINS[:10])
        url = (f"https://lunarcrush.com/api3/coins?"
               f"key={api_key}&sort=galaxy_score&limit=10&symbols={symbols_str}")
        data = _http_get(url)
        if data and isinstance(data.get("data"), list):
            for coin_info in data["data"]:
                symbol = coin_info.get("symbol", "").upper()
                if symbol:
                    coin_data[symbol] = {
                        "galaxy_score": coin_info.get("galaxy_score", 0),
                        "alt_rank": coin_info.get("alt_rank", 0),
                        "social_volume": coin_info.get("social_volume", 0),
                        "social_volume_24h": coin_info.get("social_volume_24h", 0),
                        "social_score": coin_info.get("social_score", 0),
                        "sentiment": coin_info.get("average_sentiment", 0),
                        "market_dominance": coin_info.get("market_dominance", 0),
                        "price_change_24h": coin_info.get("percent_change_24h", 0),
                    }

    logger.info(f"LunarCrush: {len(coin_data)} coins with data")
    return coin_data


def lunarcrush_to_signals(coin_data: Dict[str, dict]) -> Dict[str, dict]:
    """
    Convert LunarCrush data into directional signals.
    Galaxy Score > 70 = bullish, < 30 = bearish.
    Social volume spike detection via relative thresholds.
    """
    signals = {}

    # Calculate average social volume for spike detection
    volumes = [d.get("social_volume", 0) for d in coin_data.values() if d.get("social_volume")]
    avg_volume = sum(volumes) / len(volumes) if volumes else 1

    for symbol, data in coin_data.items():
        galaxy = data.get("galaxy_score", 50)
        social_vol = data.get("social_volume", 0)
        sentiment_val = data.get("sentiment", 0)

        reasons = []

        # Galaxy Score signal
        if galaxy > 70:
            gs_direction = "bullish"
            gs_confidence = round(min(0.85, 0.50 + (galaxy - 70) / 100), 3)
            reasons.append(f"Galaxy Score {galaxy}/100 (bullish)")
        elif galaxy < 30:
            gs_direction = "bearish"
            gs_confidence = round(min(0.85, 0.50 + (30 - galaxy) / 100), 3)
            reasons.append(f"Galaxy Score {galaxy}/100 (bearish)")
        else:
            gs_direction = "neutral"
            gs_confidence = 0.40
            reasons.append(f"Galaxy Score {galaxy}/100 (neutral)")

        # Social volume spike
        momentum = ""
        if avg_volume > 0 and social_vol > avg_volume * 2:
            spike_ratio = social_vol / avg_volume
            momentum = "high_momentum"
            reasons.append(f"Social volume spike {spike_ratio:.1f}x average")
        elif avg_volume > 0 and social_vol > avg_volume * 1.5:
            momentum = "rising_momentum"
            reasons.append(f"Social volume rising {social_vol / avg_volume:.1f}x average")

        # Sentiment override
        if sentiment_val > 0 and sentiment_val > 3.5:
            reasons.append(f"Sentiment score {sentiment_val:.1f}/5 (positive)")
            if gs_direction == "neutral":
                gs_direction = "bullish"
                gs_confidence = 0.55
        elif sentiment_val > 0 and sentiment_val < 2.0:
            reasons.append(f"Sentiment score {sentiment_val:.1f}/5 (negative)")
            if gs_direction == "neutral":
                gs_direction = "bearish"
                gs_confidence = 0.55

        # Boost confidence for momentum + direction alignment
        if momentum and gs_direction == "bullish":
            gs_confidence = min(0.90, gs_confidence + 0.10)

        signals[symbol] = {
            "direction": gs_direction,
            "confidence": gs_confidence,
            "source": "lunarcrush",
            "reason": " | ".join(reasons),
            "galaxy_score": galaxy,
            "social_volume": social_vol,
            "momentum": momentum,
            "alt_rank": data.get("alt_rank", 0),
        }

    return signals


# ---------------------------------------------------------------------------
# Source 3: Alternative.me Fear & Greed Index (always free)
# ---------------------------------------------------------------------------

def fetch_fear_greed() -> dict:
    """
    Fetch Bitcoin Fear & Greed Index from Alternative.me.
    Returns: {value: int, classification: str, history: [...]}
    """
    url = "https://api.alternative.me/fng/?limit=7"
    data = _http_get(url)
    if not data or "data" not in data:
        logger.warning("Failed to fetch Fear & Greed Index")
        return {}

    entries = data["data"]
    if not entries:
        return {}

    current = entries[0]
    value = int(current.get("value", 50))
    classification = current.get("value_classification", "Neutral")

    # Calculate trend (is fear increasing or decreasing?)
    values = [int(e.get("value", 50)) for e in entries]
    trend = "stable"
    if len(values) >= 3:
        recent_avg = sum(values[:3]) / 3
        older_avg = sum(values[3:]) / max(1, len(values[3:]))
        if recent_avg > older_avg + 5:
            trend = "improving"
        elif recent_avg < older_avg - 5:
            trend = "worsening"

    return {
        "value": value,
        "classification": classification,
        "trend": trend,
        "history": values,
    }


def fear_greed_to_signal(fg_data: dict) -> dict:
    """
    Convert Fear & Greed Index into a market-wide signal.
    Extreme Fear (<20) = contrarian bullish, Extreme Greed (>80) = contrarian bearish.
    """
    if not fg_data:
        return {}

    value = fg_data.get("value", 50)
    classification = fg_data.get("classification", "Neutral")
    trend = fg_data.get("trend", "stable")

    # Contrarian approach: extreme fear = buying opportunity
    if value <= 20:
        direction = "bullish"
        confidence = round(min(0.80, 0.55 + (20 - value) / 100), 3)
        reason = f"Extreme Fear ({value}/100) - contrarian bullish signal, trend {trend}"
    elif value <= 35:
        direction = "bullish"
        confidence = round(0.50 + (35 - value) / 100, 3)
        reason = f"Fear ({value}/100) - mild contrarian bullish, trend {trend}"
    elif value >= 80:
        direction = "bearish"
        confidence = round(min(0.80, 0.55 + (value - 80) / 100), 3)
        reason = f"Extreme Greed ({value}/100) - contrarian bearish signal, trend {trend}"
    elif value >= 65:
        direction = "bearish"
        confidence = round(0.50 + (value - 65) / 100, 3)
        reason = f"Greed ({value}/100) - mild contrarian bearish, trend {trend}"
    else:
        direction = "neutral"
        confidence = 0.40
        reason = f"Neutral sentiment ({value}/100 - {classification}), trend {trend}"

    # Trend modifier
    if trend == "worsening" and direction == "bearish":
        confidence = min(0.90, confidence + 0.05)
    elif trend == "improving" and direction == "bullish":
        confidence = min(0.90, confidence + 0.05)

    return {
        "direction": direction,
        "confidence": confidence,
        "source": "fear_greed_index",
        "reason": reason,
        "value": value,
        "classification": classification,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Signal Aggregation
# ---------------------------------------------------------------------------

def aggregate_signals(
    cryptopanic_signals: Dict[str, dict],
    lunarcrush_signals: Dict[str, dict],
    fear_greed_signal: dict,
) -> Dict[str, dict]:
    """
    Merge signals from all sources into a single dict per symbol.
    Consensus (2+ sources agree) gets higher confidence.
    """
    all_symbols = set(list(cryptopanic_signals.keys()) +
                      list(lunarcrush_signals.keys()) +
                      TOP_COINS[:10])  # Always include top 10

    aggregated = {}

    for symbol in all_symbols:
        sources = []
        directions = []
        total_confidence = 0
        reasons = []

        # CryptoPanic signal
        cp = cryptopanic_signals.get(symbol)
        if cp:
            sources.append("cryptopanic")
            directions.append(cp["direction"])
            total_confidence += cp["confidence"]
            reasons.append(cp["reason"])

        # LunarCrush signal
        lc = lunarcrush_signals.get(symbol)
        if lc:
            sources.append("lunarcrush")
            directions.append(lc["direction"])
            total_confidence += lc["confidence"]
            reasons.append(lc["reason"])

        # Fear & Greed applies to all crypto
        if fear_greed_signal:
            sources.append("fear_greed")
            directions.append(fear_greed_signal["direction"])
            total_confidence += fear_greed_signal["confidence"]
            reasons.append(fear_greed_signal["reason"])

        if not sources:
            continue

        # Determine consensus direction
        bull_count = directions.count("bullish")
        bear_count = directions.count("bearish")
        neutral_count = directions.count("neutral")

        if bull_count > bear_count and bull_count > neutral_count:
            direction = "bullish"
        elif bear_count > bull_count and bear_count > neutral_count:
            direction = "bearish"
        else:
            direction = "neutral"

        # Average confidence, boosted by consensus
        avg_confidence = total_confidence / len(sources) if sources else 0.40
        consensus_count = max(bull_count, bear_count)
        if consensus_count >= 2:
            avg_confidence = min(0.92, avg_confidence + 0.08)
        elif consensus_count >= 3:
            avg_confidence = min(0.95, avg_confidence + 0.12)

        aggregated[symbol] = {
            "direction": direction,
            "confidence": round(avg_confidence, 3),
            "source": "+".join(sources),
            "reason": " || ".join(reasons),
            "source_count": len(sources),
            "consensus": consensus_count,
            "bullish_sources": bull_count,
            "bearish_sources": bear_count,
            "neutral_sources": neutral_count,
            "individual_signals": {
                "cryptopanic": cp,
                "lunarcrush": lc,
                "fear_greed": fear_greed_signal,
            },
        }

    return aggregated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run() -> Dict[str, dict]:
    """
    Run full sentiment scan across all sources and save results.
    Returns aggregated signals dict: {symbol: {direction, confidence, source, reason}}
    """
    logger.info("Running sentiment signal scan...")
    start = time.time()

    # Fetch from all sources (graceful on failure)
    cp_sentiment = fetch_cryptopanic_sentiment()
    cp_signals = cryptopanic_to_signals(cp_sentiment)
    logger.info(f"CryptoPanic: {len(cp_signals)} signals")

    lc_data = fetch_lunarcrush_sentiment()
    lc_signals = lunarcrush_to_signals(lc_data)
    logger.info(f"LunarCrush: {len(lc_signals)} signals")

    fg_data = fetch_fear_greed()
    fg_signal = fear_greed_to_signal(fg_data)
    logger.info(f"Fear & Greed: {fg_data.get('classification', 'N/A')} ({fg_data.get('value', '?')})")

    # Aggregate
    aggregated = aggregate_signals(cp_signals, lc_signals, fg_signal)

    # Build output
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "sentiment_signals",
        "scan_duration_sec": round(time.time() - start, 1),
        "sources_active": {
            "cryptopanic": len(cp_signals) > 0,
            "lunarcrush": len(lc_signals) > 0,
            "fear_greed": bool(fg_data),
        },
        "fear_greed_index": fg_data,
        "signal_count": len(aggregated),
        "signals": aggregated,
    }

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Sentiment signals saved to {OUTPUT_FILE}")

    return aggregated


def get_sentiment_signal(symbol: str) -> Optional[Dict]:
    """
    Get sentiment signal for a specific symbol.
    Reads from cached output file. Returns None if not available.

    Args:
        symbol: e.g. "BTC", "BTCUSDT", "ETH-USD"

    Returns:
        dict with {direction, confidence, source, reason} or None
    """
    # Normalize symbol
    sym = symbol.upper()
    for suffix in ("USDT", "USD", "BUSD", "USDC", "-USD", "-USDT", "/USDT", "/USD"):
        sym = sym.replace(suffix, "")
    sym = sym.replace("-", "").replace("/", "")

    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            signals = data.get("signals", {})

            # Try exact match and common variations
            for try_sym in [sym, f"W{sym}", sym.replace("W", "")]:
                if try_sym in signals:
                    sig = signals[try_sym]
                    return {
                        "direction": sig["direction"],
                        "confidence": sig["confidence"],
                        "source": sig["source"],
                        "reason": sig["reason"],
                    }

            # If we have fear & greed data, return that as fallback for any crypto
            fg = data.get("fear_greed_index", {})
            if fg:
                fg_sig = fear_greed_to_signal(fg)
                if fg_sig:
                    fg_sig["reason"] = f"[{sym}] " + fg_sig["reason"]
                    return {
                        "direction": fg_sig["direction"],
                        "confidence": fg_sig["confidence"],
                        "source": fg_sig["source"],
                        "reason": fg_sig["reason"],
                    }
    except Exception as e:
        logger.debug(f"Sentiment signal lookup failed for {symbol}: {e}")

    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 70)
    print("  SENTIMENT SIGNAL SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Check API keys
    cp_key = _get_cryptopanic_key()
    lc_key = _get_lunarcrush_key()
    print(f"  CryptoPanic API key: {'OK (' + cp_key[:8] + '...)' if cp_key else 'NOT SET'}")
    print(f"  LunarCrush API key:  {'OK (' + lc_key[:8] + '...)' if lc_key else 'NOT SET'}")
    print(f"  Fear & Greed Index:  always available (no auth)")
    print()

    signals = run()

    print(f"\n{'=' * 70}")
    print(f"  SENTIMENT SIGNALS — {len(signals)} coins")
    print(f"{'=' * 70}")

    # Sort by confidence
    sorted_signals = sorted(signals.items(),
                            key=lambda x: x[1].get("confidence", 0),
                            reverse=True)

    for symbol, sig in sorted_signals[:20]:
        direction = sig["direction"].upper()
        conf = sig["confidence"]
        sources = sig.get("source_count", 0)
        tag = {"BULLISH": "BULL", "BEARISH": "BEAR", "NEUTRAL": "----"}.get(direction, "----")
        print(f"\n  [{tag}] {symbol:8s} conf={conf:.0%} sources={sources}")
        # Show individual source reasons
        for reason_part in sig.get("reason", "").split(" || "):
            print(f"    -> {reason_part[:100]}")

    # Fear & Greed summary
    print(f"\n{'=' * 70}")
    fg_sig = fear_greed_to_signal(fetch_fear_greed())
    if fg_sig:
        print(f"  MARKET FEAR & GREED: {fg_sig.get('classification', 'N/A')} "
              f"({fg_sig.get('value', '?')}/100) -> {fg_sig['direction'].upper()}")
    print(f"{'=' * 70}")

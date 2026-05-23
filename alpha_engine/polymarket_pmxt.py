"""
polymarket_pmxt.py - Alpha Engine: Polymarket Prediction Market Signal Source
=============================================================================
Fetches crypto-relevant prediction markets from Polymarket via the public
Gamma API (gamma-api.polymarket.com) and the CLOB API (clob.polymarket.com).

No API key required — all endpoints are public.

Data available:
  - Market odds (0-1 probability scale) for crypto events
  - Volume, liquidity, open interest
  - Orderbook depth via CLOB API
  - Historical trades and OHLCV via CLOB API

Strategy:
  - Search for crypto-related markets (BTC price targets, ETH milestones,
    crypto regulation, exchange events, DeFi protocols)
  - Convert market odds to directional confidence signals
  - e.g., "BTC above $100K by June" at 70% odds → +0.05 confidence boost for BTC LONG
  - "Ethereum ETF approved" at 80% odds → +0.04 confidence boost for ETH LONG
  - Markets below 30% odds with bearish keywords → negative confidence boost

Output: alpha_engine/data/polymarket_signals.json
Integration: get_polymarket_signal(symbol) → dict with odds, direction, confidence_boost

Environment:
  No keys needed — Polymarket Gamma API is fully public.

Archive (PMXT):
  https://archive.pmxt.dev/Polymarket — hourly parquet snapshots of orderbook/trade data
  Currently intermittent availability. We use the live Gamma API as primary source.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "polymarket_signals.json"

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

TIMEOUT = 10

# Search terms to find crypto-relevant markets
CRYPTO_SEARCH_TERMS = [
    "bitcoin", "BTC", "ethereum", "ETH", "solana", "SOL",
    "crypto", "XRP", "ripple", "cardano", "ADA", "dogecoin", "DOGE",
    "DeFi", "blockchain", "stablecoin", "USDT", "USDC",
    "binance", "coinbase", "SEC crypto", "bitcoin ETF",
    "altcoin", "memecoin", "NFT", "web3",
]

# Keywords that indicate bullish/bearish direction
BULLISH_KEYWORDS = [
    "above", "hit", "reach", "exceed", "surpass", "break",
    "new all-time high", "ATH", "rally", "bull", "adoption",
    "approved", "approval", "etf", "institutional",
    "100k", "150k", "200k", "1m", "million",
]

BEARISH_KEYWORDS = [
    "below", "crash", "drop", "fall", "decline", "ban",
    "regulation", "crackdown", "hack", "exploit", "collapse",
    "bear", "recession", "bankrupt", "insolvent",
]

# Symbol extraction patterns
SYMBOL_PATTERNS = {
    "BTC": re.compile(r"\b(bitcoin|btc)\b", re.IGNORECASE),
    "ETH": re.compile(r"\b(ethereum|eth)\b", re.IGNORECASE),
    "SOL": re.compile(r"\b(solana|sol)\b", re.IGNORECASE),
    "XRP": re.compile(r"\b(xrp|ripple)\b", re.IGNORECASE),
    "ADA": re.compile(r"\b(cardano|ada)\b", re.IGNORECASE),
    "DOGE": re.compile(r"\b(dogecoin|doge)\b", re.IGNORECASE),
    "BNB": re.compile(r"\b(binance coin|bnb)\b", re.IGNORECASE),
    "AVAX": re.compile(r"\b(avax|avalanche\s*(?:network|chain|token|coin|crypto|c-chain|x-chain))\b", re.IGNORECASE),
    "MATIC": re.compile(r"\b(polygon|matic)\b", re.IGNORECASE),
    "LINK": re.compile(r"\b(chainlink|link)\b", re.IGNORECASE),
    "DOT": re.compile(r"\b(polkadot|dot)\b", re.IGNORECASE),
}

# General crypto keywords (affect all crypto symbols if no specific match)
GENERAL_CRYPTO_RE = re.compile(
    r"\b(crypto|cryptocurrency|digital asset|blockchain|defi|web3)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _fetch_json(url: str) -> Optional[dict]:
    """Fetch JSON from URL with timeout and error handling."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AlphaEngine/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP {e.code} fetching {url}")
    except urllib.error.URLError as e:
        logger.warning(f"URL error fetching {url}: {e.reason}")
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
    return None


# ---------------------------------------------------------------------------
# Market fetching
# ---------------------------------------------------------------------------

def fetch_crypto_markets() -> List[Dict[str, Any]]:
    """
    Fetch all crypto-relevant prediction markets from Polymarket Gamma API.
    Searches multiple terms and deduplicates by market ID.
    """
    seen_ids = set()
    markets = []

    for term in CRYPTO_SEARCH_TERMS:
        url = f"{GAMMA_API}/markets?closed=false&limit=100&_q={urllib.request.quote(term)}"
        data = _fetch_json(url)

        if not data or not isinstance(data, list):
            continue

        for m in data:
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                # Check if actually crypto-relevant by inspecting question text
                question = (m.get("question", "") + " " + m.get("description", "")).lower()
                is_crypto = any(
                    kw.lower() in question
                    for kw in ["bitcoin", "btc", "ethereum", "eth", "crypto",
                               "solana", "xrp", "defi", "blockchain", "nft",
                               "altcoin", "memecoin", "web3", "binance",
                               "coinbase", "etf crypto", "stablecoin",
                               "dogecoin", "cardano"]
                )
                if is_crypto:
                    markets.append(m)

        # Rate limit: be polite to the API
        time.sleep(0.3)

    logger.info(f"Found {len(markets)} crypto-relevant Polymarket markets")
    return markets


def fetch_events_crypto() -> List[Dict[str, Any]]:
    """
    Fetch crypto-tagged events from the Gamma API events endpoint.
    """
    url = f"{GAMMA_API}/events?tag=crypto&closed=false&limit=50&order=volume&ascending=false"
    data = _fetch_json(url)
    if data and isinstance(data, list):
        return data
    return []


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def _extract_symbols(text: str) -> List[str]:
    """Extract crypto symbols mentioned in market text."""
    symbols = []
    for sym, pattern in SYMBOL_PATTERNS.items():
        if pattern.search(text):
            symbols.append(sym)
    return symbols


def _detect_direction(text: str) -> str:
    """Detect bullish/bearish direction from market text."""
    text_lower = text.lower()
    bull_score = sum(1 for kw in BULLISH_KEYWORDS if kw.lower() in text_lower)
    bear_score = sum(1 for kw in BEARISH_KEYWORDS if kw.lower() in text_lower)

    if bull_score > bear_score:
        return "bullish"
    elif bear_score > bull_score:
        return "bearish"
    return "neutral"


def _extract_price_target(text: str) -> Optional[float]:
    """Extract price target from market text (e.g., '$100K', '$1m', '$75,000')."""
    patterns = [
        (r"\$(\d+(?:,\d{3})*)\b", lambda m: float(m.group(1).replace(",", ""))),
        (r"\$(\d+(?:\.\d+)?)\s*[kK]", lambda m: float(m.group(1)) * 1_000),
        (r"\$(\d+(?:\.\d+)?)\s*[mM]", lambda m: float(m.group(1)) * 1_000_000),
        (r"(\d+(?:,\d{3})+)", lambda m: float(m.group(1).replace(",", ""))),
    ]
    for pat, converter in patterns:
        match = re.search(pat, text)
        if match:
            try:
                val = converter(match)
                # Sanity check — likely a price target if > $50
                if val > 50:
                    return val
            except (ValueError, IndexError):
                continue
    return None


def analyze_markets(markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze fetched markets and produce per-symbol signal data.
    Returns dict keyed by symbol with aggregated market signals.
    """
    symbol_signals: Dict[str, List[Dict]] = {}

    for m in markets:
        question = m.get("question", "")
        description = m.get("description", "")
        full_text = f"{question} {description}"

        # Extract outcome prices — Gamma API may return these as JSON strings
        outcomes = m.get("outcomes", [])
        outcome_prices_raw = m.get("outcomePrices", [])

        # Parse JSON strings if needed
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except (json.JSONDecodeError, TypeError):
                outcomes = []
        if isinstance(outcome_prices_raw, str):
            try:
                outcome_prices_raw = json.loads(outcome_prices_raw)
            except (json.JSONDecodeError, TypeError):
                outcome_prices_raw = []

        try:
            outcome_prices = [float(p) for p in outcome_prices_raw]
        except (ValueError, TypeError):
            outcome_prices = []

        if len(outcomes) < 2 or len(outcome_prices) < 2:
            continue

        # For Yes/No markets, "Yes" price = probability of the event
        try:
            yes_price = outcome_prices[0] if outcomes[0].lower() == "yes" else outcome_prices[1]
        except (IndexError, AttributeError):
            continue

        # Extract symbols
        symbols = _extract_symbols(full_text)
        if not symbols and GENERAL_CRYPTO_RE.search(full_text):
            # General crypto market — applies to BTC as market leader
            symbols = ["BTC"]

        direction = _detect_direction(full_text)
        price_target = _extract_price_target(full_text)
        volume = float(m.get("volume", 0) or 0)
        liquidity = float(m.get("liquidity", 0) or 0)

        signal = {
            "market_id": m.get("id"),
            "question": question,
            "yes_probability": round(yes_price, 4),
            "no_probability": round(1 - yes_price, 4),
            "direction": direction,
            "price_target": price_target,
            "volume_usd": round(volume, 2),
            "liquidity_usd": round(liquidity, 2),
            "end_date": m.get("endDate"),
            "slug": m.get("slug", ""),
        }

        for sym in symbols:
            if sym not in symbol_signals:
                symbol_signals[sym] = []
            symbol_signals[sym].append(signal)

    # Aggregate per-symbol
    result = {}
    for sym, signals in symbol_signals.items():
        # Weight by volume and liquidity
        total_volume = sum(s["volume_usd"] for s in signals)
        bullish_weight = 0.0
        bearish_weight = 0.0

        for s in signals:
            weight = max(s["volume_usd"], 1)  # min weight 1
            prob = s["yes_probability"]

            if s["direction"] == "bullish":
                bullish_weight += prob * weight
            elif s["direction"] == "bearish":
                bearish_weight += prob * weight
            else:
                # Neutral — split
                bullish_weight += prob * weight * 0.5
                bearish_weight += (1 - prob) * weight * 0.5

        total_weight = bullish_weight + bearish_weight
        if total_weight > 0:
            net_bullish = (bullish_weight - bearish_weight) / total_weight
        else:
            net_bullish = 0.0

        # Convert to confidence boost: range [-0.10, +0.10]
        # Scale: strong consensus (>0.7) = max boost
        confidence_boost = round(net_bullish * 0.10, 4)

        # Cap at +/- 0.10
        confidence_boost = max(-0.10, min(0.10, confidence_boost))

        if net_bullish > 0.1:
            overall_direction = "bullish"
        elif net_bullish < -0.1:
            overall_direction = "bearish"
        else:
            overall_direction = "neutral"

        # Find highest-volume market for this symbol
        top_market = max(signals, key=lambda s: s["volume_usd"])

        result[sym] = {
            "symbol": sym,
            "direction": overall_direction,
            "confidence_boost": confidence_boost,
            "net_bullish_score": round(net_bullish, 4),
            "market_count": len(signals),
            "total_volume_usd": round(total_volume, 2),
            "top_market": {
                "question": top_market["question"],
                "yes_probability": top_market["yes_probability"],
                "volume_usd": top_market["volume_usd"],
            },
            "all_markets": signals,
        }

    return result


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_polymarket() -> Dict[str, Any]:
    """
    Full scan: fetch crypto markets, analyze, and save results.
    Returns the complete analysis dict.
    """
    logger.info("Scanning Polymarket for crypto prediction markets...")

    markets = fetch_crypto_markets()
    events = fetch_events_crypto()

    # Extract markets from events too
    for event in events:
        event_markets = event.get("markets", [])
        if isinstance(event_markets, list):
            markets.extend(event_markets)

    # Deduplicate
    seen = set()
    unique = []
    for m in markets:
        mid = m.get("id") or m.get("condition_id")
        if mid and mid not in seen:
            seen.add(mid)
            unique.append(m)

    analysis = analyze_markets(unique)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Polymarket Gamma API (gamma-api.polymarket.com)",
        "archive_source": "PMXT (archive.pmxt.dev/Polymarket) — hourly parquet snapshots",
        "total_crypto_markets_found": len(unique),
        "symbols_with_signals": len(analysis),
        "signals": analysis,
    }

    # Save to disk
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info(f"Polymarket signals saved to {OUTPUT_FILE}")

    return result


# ---------------------------------------------------------------------------
# Integration helper for Alpha Engine
# ---------------------------------------------------------------------------

def get_polymarket_signal(symbol: str = "BTC") -> Optional[Dict[str, Any]]:
    """
    Get Polymarket prediction market signal for a specific crypto symbol.

    Returns dict with:
      - direction: "bullish" | "bearish" | "neutral"
      - confidence_boost: float in [-0.10, +0.10] to add to pick confidence
      - odds: highest-volume market yes_probability
      - market_count: number of relevant markets
      - top_question: the most-traded relevant market question
      - volume_usd: total volume across relevant markets

    Returns None if no data available.
    """
    sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "").replace("-PERP", "")

    # Try loading cached data first
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                data = json.load(f)

            signals = data.get("signals", {})
            if sym in signals:
                s = signals[sym]
                return {
                    "direction": s["direction"],
                    "confidence_boost": s["confidence_boost"],
                    "odds": s.get("top_market", {}).get("yes_probability", 0.5),
                    "market_count": s["market_count"],
                    "top_question": s.get("top_market", {}).get("question", ""),
                    "volume_usd": s["total_volume_usd"],
                    "source": "polymarket",
                }
    except Exception as e:
        logger.debug(f"Polymarket cached signal lookup failed: {e}")

    # If no cached data, try a quick live fetch for just this symbol
    try:
        search_terms = [sym]
        # Add full name for common symbols
        name_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin",
            "DOT": "polkadot", "LINK": "chainlink", "AVAX": "avalanche",
            "MATIC": "polygon", "BNB": "binance",
        }
        if sym in name_map:
            search_terms.append(name_map[sym])

        all_markets = []
        for term in search_terms:
            url = f"{GAMMA_API}/markets?closed=false&limit=50&_q={urllib.request.quote(term)}"
            data = _fetch_json(url)
            if data and isinstance(data, list):
                all_markets.extend(data)
            time.sleep(0.2)

        # Deduplicate and filter
        seen = set()
        unique = []
        for m in all_markets:
            mid = m.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                full_text = f"{m.get('question', '')} {m.get('description', '')}"
                if SYMBOL_PATTERNS.get(sym, re.compile(r"$^")).search(full_text) or \
                   GENERAL_CRYPTO_RE.search(full_text):
                    unique.append(m)

        if not unique:
            return None

        analysis = analyze_markets(unique)
        if sym in analysis:
            s = analysis[sym]
            return {
                "direction": s["direction"],
                "confidence_boost": s["confidence_boost"],
                "odds": s.get("top_market", {}).get("yes_probability", 0.5),
                "market_count": s["market_count"],
                "top_question": s.get("top_market", {}).get("question", ""),
                "volume_usd": s["total_volume_usd"],
                "source": "polymarket_live",
            }
    except Exception as e:
        logger.debug(f"Polymarket live signal lookup failed: {e}")

    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = scan_polymarket()
    print(f"\nPolymarket scan complete:")
    print(f"  Markets found: {result['total_crypto_markets_found']}")
    print(f"  Symbols with signals: {result['symbols_with_signals']}")
    for sym, sig in result.get("signals", {}).items():
        print(f"  {sym}: {sig['direction']} (boost={sig['confidence_boost']:+.4f}, "
              f"markets={sig['market_count']}, vol=${sig['total_volume_usd']:,.0f})")
        print(f"    Top: {sig['top_market']['question']} ({sig['top_market']['yes_probability']:.1%})")

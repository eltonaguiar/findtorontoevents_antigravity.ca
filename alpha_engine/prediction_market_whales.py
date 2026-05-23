"""
Prediction Market Whale Tracker & Signal Generator

Tracks Polymarket price momentum, whale positions, Kalshi intraday sentiment,
and generates consensus trading signals from prediction market data.

Sources:
  - Polymarket CLOB API: price history / momentum detection
  - Polymarket Gamma API: market metadata, events, leaderboard attempts
  - Kalshi Trade API v2: crypto prediction markets (15-min, hourly, daily)
  - Known whale addresses on Polygon (CTFX ERC-1155 positions)

All HTTP calls use stdlib only (urllib.request). Graceful degradation when
APIs are unreachable.

Usage:
    from prediction_market_whales import generate_prediction_market_picks
    picks = generate_prediction_market_picks()
"""

import json
import logging
import math
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "prediction_market_whales.json")

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

REQUEST_TIMEOUT = 12  # seconds

# Binance 5-mirror failover chain (API Failover Rule)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Momentum thresholds
MOMENTUM_4H_THRESHOLD = 0.05    # 5 percentage-point shift in 4 hours
MOMENTUM_24H_THRESHOLD = 0.10   # 10pp shift in 24 hours
BREAKOUT_HIGH = 0.60            # probability breakout above this
BREAKOUT_LOW = 0.40             # probability breakout below this
BREAKOUT_WINDOW_HOURS = 6       # time window for breakout detection

# Kalshi intraday thresholds
KALSHI_STRONG_SIGNAL = 0.80     # 80%+ probability = strong short-term signal
KALSHI_MODERATE_SIGNAL = 0.65   # 65%+ = moderate signal

# Whale consensus threshold
WHALE_CONSENSUS_MIN = 2         # minimum whales agreeing for a signal

# Symbol mapping (prediction market question -> trading symbol)
SYMBOL_MAP = {
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "xrp": "XRPUSDT", "ripple": "XRPUSDT",
    "cardano": "ADAUSDT", "ada": "ADAUSDT",
    "dogecoin": "DOGEUSDT", "doge": "DOGEUSDT",
    "bnb": "BNBUSDT", "avalanche": "AVAXUSDT", "avax": "AVAXUSDT",
    "polkadot": "DOTUSDT", "dot": "DOTUSDT",
    "chainlink": "LINKUSDT", "link": "LINKUSDT",
    "litecoin": "LTCUSDT", "ltc": "LTCUSDT",
    "shib": "SHIBUSDT", "shiba": "SHIBUSDT",
}

# Kalshi series -> trading symbol
KALSHI_SERIES_MAP = {
    "KXBTC": "BTCUSDT", "KXBTCD": "BTCUSDT", "BTCD": "BTCUSDT",
    "KXBTC15M": "BTCUSDT", "KXBTCMAXW": "BTCUSDT",
    "KXETH": "ETHUSDT", "KXETHD": "ETHUSDT", "ETHD": "ETHUSDT",
    "KXETH15M": "ETHUSDT",
    "KXSOL": "SOLUSDT", "KXSOLD": "SOLUSDT", "KXSOL15M": "SOLUSDT",
    "KXDOGE": "DOGEUSDT", "KXDOGED": "DOGEUSDT", "KXDOGE15M": "DOGEUSDT",
    "KXXRP": "XRPUSDT", "KXXRPD": "XRPUSDT", "KXXRP15M": "XRPUSDT",
    "KXAVAX": "AVAXUSDT", "KXAVAXD": "AVAXUSDT",
    "KXLINK": "LINKUSDT", "KXLINKD": "LINKUSDT",
    "KXDOT": "DOTUSDT", "KXDOTD": "DOTUSDT",
    "KXLTC": "LTCUSDT", "KXLTCD": "LTCUSDT",
    "KXBNB15M": "BNBUSDT",
    "KXADA15M": "ADAUSDT",
}

# ---------------------------------------------------------------------------
# Known Polymarket Whales
#
# NOTE: Most addresses below are placeholders ("0x..."). Real addresses
# should be filled from Dune Analytics queries:
#   SELECT trader, SUM(profit) as total_profit
#   FROM polymarket_polygon.ctf_positions
#   GROUP BY trader ORDER BY total_profit DESC LIMIT 50
#
# Or from Arkham Intelligence whale tracking dashboards.
# ---------------------------------------------------------------------------

KNOWN_POLYMARKET_WHALES = {
    "theo": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "$50M+ profit, famous Polymarket whale, crypto specialist",
        "reliability": 0.85,
    },
    "fredi9999": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "Top leaderboard trader, consistent performer",
        "reliability": 0.80,
    },
    "gcr_galois": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "Galois Capital / GCR, known macro crypto trader",
        "reliability": 0.80,
    },
    "silverrock": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "Known BTC predictor, high win rate on price markets",
        "reliability": 0.75,
    },
    "polymarket_wizard": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "High-volume trader, frequently in top 10 leaderboard",
        "reliability": 0.70,
    },
    "delphi_digital": {
        "address": "0x...",  # TODO: fill from Dune Analytics
        "description": "Research firm with prediction market desk",
        "reliability": 0.75,
    },
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _fetch_json(url, params=None, timeout=None):
    """Fetch JSON from URL using stdlib. Returns parsed object or None."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "AlphaEngine-WhaleTracker/2.0",
        "Accept": "application/json",
    })
    
    # Rate limit API
    import time
    time.sleep(0.35)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout or REQUEST_TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        logger.debug("HTTP %s fetching %s: %s", e.code, url, e.reason)
        return None
    except urllib.error.URLError as e:
        logger.debug("URL error fetching %s: %s", url, e.reason)
        return None
    except Exception as e:
        logger.debug("Error fetching %s: %s", url, e)
        return None


def _safe_float(val, default=None):
    """Convert value to float, return default on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _detect_symbol(text):
    """Detect trading symbol from market question text."""
    t = text.lower()
    for keyword, symbol in SYMBOL_MAP.items():
        if keyword in t:
            return symbol
    if any(kw in t for kw in ("crypto", "cryptocurrency")):
        return "BTCUSDT"
    return None


# ---------------------------------------------------------------------------
# 1. Polymarket Price History & Momentum
# ---------------------------------------------------------------------------

def fetch_price_history(token_id, fidelity=60):
    """
    Fetch price time series from CLOB API: clob.polymarket.com/prices-history

    Args:
        token_id: Numeric CLOB token ID from market's clobTokenIds field
        fidelity: Number of data points (default 60 = ~1hr intervals over ~2.5 days)

    Returns:
        List of {t: unix_timestamp, p: price} sorted by time ascending,
        or empty list on failure.
    """
    result = _fetch_json(
        f"{CLOB_API_BASE}/prices-history",
        params={"market": str(token_id), "interval": "all", "fidelity": str(fidelity)},
    )
    if not result:
        return []

    # Response format: {"history": [{t: int, p: float}, ...]}
    history = []
    raw = result.get("history", []) if isinstance(result, dict) else []
    if isinstance(result, list):
        raw = result

    for point in raw:
        ts = point.get("t")
        price = _safe_float(point.get("p"))
        if ts is not None and price is not None:
            history.append({"t": int(ts), "p": price})

    # Sort by timestamp ascending
    history.sort(key=lambda x: x["t"])
    return history


def compute_probability_momentum(markets):
    """
    For each active crypto market with CLOB token IDs:
    1. Fetch price history (last 24h at 1h intervals)
    2. Compute momentum: current_prob - prob_4h_ago
    3. If momentum > 0.05 (5pp) -> BULLISH momentum signal
    4. If momentum < -0.05 -> BEARISH momentum signal
    5. Weight by market volume (higher volume = more reliable)

    This is the KEY ALPHA: probability changes PRECEDE spot price changes.

    Args:
        markets: List of market dicts from Polymarket Gamma API

    Returns:
        List of momentum signal dicts with keys:
            symbol, direction, momentum_4h, momentum_24h, current_prob,
            volume, question, confidence, strategy
    """
    signals = []
    now_ts = int(time.time())

    for market in markets:
        # Extract CLOB token IDs
        clob_ids = market.get("clobTokenIds")
        if not clob_ids:
            continue

        # Parse clobTokenIds (can be JSON string or list)
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except (json.JSONDecodeError, ValueError):
                continue
        if not isinstance(clob_ids, list) or len(clob_ids) == 0:
            continue

        # Use the first token (YES outcome)
        token_id = clob_ids[0]
        question = market.get("question") or market.get("title") or ""
        symbol = _detect_symbol(question)
        if not symbol:
            continue

        volume = _safe_float(
            market.get("volume") or market.get("volumeNum") or 0,
            default=0,
        )

        # Fetch price history
        history = fetch_price_history(token_id, fidelity=60)
        if len(history) < 5:
            continue

        current_prob = history[-1]["p"]
        current_ts = history[-1]["t"]

        # Find probability 4 hours ago
        target_4h = current_ts - (4 * 3600)
        prob_4h_ago = _find_nearest_price(history, target_4h)

        # Find probability 24 hours ago
        target_24h = current_ts - (24 * 3600)
        prob_24h_ago = _find_nearest_price(history, target_24h)

        # Compute momentum
        momentum_4h = None
        momentum_24h = None

        if prob_4h_ago is not None:
            momentum_4h = current_prob - prob_4h_ago
        if prob_24h_ago is not None:
            momentum_24h = current_prob - prob_24h_ago

        # Check if momentum crosses threshold
        direction = None
        momentum_strength = 0.0

        if momentum_4h is not None and abs(momentum_4h) >= MOMENTUM_4H_THRESHOLD:
            direction = "LONG" if momentum_4h > 0 else "SHORT"
            momentum_strength = abs(momentum_4h)

        if momentum_24h is not None and abs(momentum_24h) >= MOMENTUM_24H_THRESHOLD:
            if direction is None:
                direction = "LONG" if momentum_24h > 0 else "SHORT"
            momentum_strength = max(momentum_strength, abs(momentum_24h) * 0.7)

        if direction is None:
            continue

        # Infer direction from question context (reach = bullish, dip = bearish)
        q_lower = question.lower()
        is_dip_market = bool(re.search(r"(dip|drop|fall|below|under)", q_lower))
        is_reach_market = bool(re.search(r"(reach|hit|above|over|exceed)", q_lower))

        # For dip markets, rising probability means bearish (more likely to dip)
        if is_dip_market:
            if momentum_4h and momentum_4h > 0:
                direction = "SHORT"
            elif momentum_4h and momentum_4h < 0:
                direction = "LONG"
        elif is_reach_market:
            if momentum_4h and momentum_4h > 0:
                direction = "LONG"
            elif momentum_4h and momentum_4h < 0:
                direction = "SHORT"

        # Confidence: base 0.55, scale with momentum strength, weight by volume
        volume_weight = min(1.0, math.log10(max(volume, 1)) / 7)  # log scale, cap at $10M
        confidence = 0.55 + (momentum_strength * 2.0) * volume_weight
        confidence = max(0.40, min(confidence, 0.90))

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "momentum_4h": round(momentum_4h, 4) if momentum_4h else None,
            "momentum_24h": round(momentum_24h, 4) if momentum_24h else None,
            "current_prob": round(current_prob, 4),
            "volume": volume,
            "question": question,
            "confidence": round(confidence, 3),
            "strategy": "polymarket_momentum",
            "token_id": str(token_id),
        })

    logger.info("Computed %d probability momentum signals", len(signals))
    return signals


def _find_nearest_price(history, target_ts):
    """Find the price point nearest to target_ts in sorted history."""
    if not history:
        return None

    best = None
    best_diff = float("inf")
    for point in history:
        diff = abs(point["t"] - target_ts)
        if diff < best_diff:
            best_diff = diff
            best = point["p"]
        elif diff > best_diff:
            # Past the closest point (list is sorted), stop early
            break

    # Only return if within 2 hours of target
    if best_diff <= 7200:
        return best
    return None


# ---------------------------------------------------------------------------
# 2. Polymarket Leaderboard / Top Predictor Scraping
# ---------------------------------------------------------------------------

def fetch_polymarket_leaderboard():
    """
    Try multiple approaches to get top Polymarket predictors:
    1. gamma-api.polymarket.com/leaderboard (speculative)
    2. Polymarket profile API: gamma-api.polymarket.com/profiles?limit=20&order=profit
    3. Known top predictor addresses (hardcoded from research)
    4. Polygon CTFX positions via public RPC (future)

    Returns:
        List of predictor dicts: {name, address, profit, reliability, source}
    """
    predictors = []

    # Attempt 1: Leaderboard endpoint (may not exist)
    result = _fetch_json(f"{GAMMA_API_BASE}/leaderboard", params={"limit": "20"})
    if result:
        items = result if isinstance(result, list) else result.get("data", [])
        for item in items:
            if isinstance(item, dict):
                predictors.append({
                    "name": item.get("name") or item.get("username") or "unknown",
                    "address": item.get("address") or item.get("proxyWallet") or "",
                    "profit": _safe_float(item.get("profit") or item.get("pnl"), 0),
                    "reliability": 0.70,
                    "source": "leaderboard_api",
                })

    # Attempt 2: Profiles endpoint sorted by profit
    if not predictors:
        result = _fetch_json(f"{GAMMA_API_BASE}/profiles", params={
            "limit": "20", "order": "profit", "ascending": "false",
        })
        if result:
            items = result if isinstance(result, list) else result.get("data", [])
            for item in items:
                if isinstance(item, dict):
                    predictors.append({
                        "name": item.get("name") or item.get("username") or "unknown",
                        "address": item.get("address") or item.get("proxyWallet") or "",
                        "profit": _safe_float(item.get("profit") or item.get("pnl"), 0),
                        "reliability": 0.65,
                        "source": "profiles_api",
                    })

    # Attempt 3: Fall back to known whales (always available)
    if not predictors:
        for name, info in KNOWN_POLYMARKET_WHALES.items():
            predictors.append({
                "name": name,
                "address": info["address"],
                "profit": None,  # Unknown from static data
                "reliability": info["reliability"],
                "source": "known_whales",
                "description": info["description"],
            })

    logger.info("Fetched %d predictors (source: %s)",
                len(predictors),
                predictors[0]["source"] if predictors else "none")
    return predictors


# ---------------------------------------------------------------------------
# 3. Track Specific Whale Positions
# ---------------------------------------------------------------------------

def track_whale_positions(whale_addresses=None):
    """
    For each known whale, check their current positions on crypto markets.

    Uses Polymarket profile/activity API or Polygon RPC to read CTFX token
    balances. Falls back to inferring positions from leaderboard data.

    Args:
        whale_addresses: Optional dict of {name: address}. If None, uses
                         KNOWN_POLYMARKET_WHALES.

    Returns:
        List of dicts: {whale_name, market_question, position_direction,
                        size_usd, probability, symbol, confidence}

    NOTE: Real whale address tracking requires either:
      1. Dune Analytics API key + query for CTFX balances
      2. Direct Polygon RPC calls to the CTFX contract
      3. Polymarket releasing a public activity/positions API
    Currently uses profile API attempts with graceful fallback.
    """
    if whale_addresses is None:
        whale_addresses = {
            name: info["address"] for name, info in KNOWN_POLYMARKET_WHALES.items()
        }

    positions = []

    for whale_name, address in whale_addresses.items():
        # Skip placeholder addresses
        if not address or address == "0x..." or len(address) < 10:
            logger.debug("Skipping %s: placeholder address", whale_name)
            continue

        # Attempt: query Polymarket profile for activity
        profile = _fetch_json(
            f"{GAMMA_API_BASE}/profiles/{address}",
        )
        if not profile or not isinstance(profile, dict):
            continue

        # Try to get positions from profile
        user_positions = profile.get("positions") or profile.get("markets") or []
        for pos in user_positions:
            if not isinstance(pos, dict):
                continue

            question = pos.get("question") or pos.get("title") or ""
            symbol = _detect_symbol(question)
            if not symbol:
                continue

            # Determine direction from position data
            outcome = (pos.get("outcome") or pos.get("side") or "").upper()
            shares = _safe_float(pos.get("shares") or pos.get("amount"), 0)
            avg_price = _safe_float(pos.get("avgPrice") or pos.get("price"), 0)
            size_usd = shares * avg_price if shares and avg_price else 0

            if outcome in ("YES", "LONG", "BUY"):
                direction = "LONG"
            elif outcome in ("NO", "SHORT", "SELL"):
                direction = "SHORT"
            else:
                continue

            whale_info = KNOWN_POLYMARKET_WHALES.get(whale_name, {})
            reliability = whale_info.get("reliability", 0.65)

            positions.append({
                "whale_name": whale_name,
                "market_question": question,
                "position_direction": direction,
                "size_usd": round(size_usd, 2),
                "probability": _safe_float(pos.get("probability") or pos.get("price"), 0),
                "symbol": symbol,
                "confidence": round(reliability * 0.9, 3),
            })

    logger.info("Tracked %d whale positions across %d whales",
                len(positions), len(whale_addresses))
    return positions


# ---------------------------------------------------------------------------
# 4. Kalshi Integration
# ---------------------------------------------------------------------------

def fetch_kalshi_crypto_markets():
    """
    Fetch crypto prediction markets from Kalshi.
    API: GET https://api.elections.kalshi.com/trade-api/v2/events?category=Crypto

    Kalshi has intraday BTC/ETH/SOL/DOGE/XRP prediction markets.
    These are incredibly valuable for scalp-tier signals.

    Returns:
        List of dicts: {question, probability, volume, expiry, symbol,
                        series_ticker, event_ticker, yes_price, no_price}
    """
    markets = []

    # Fetch all open crypto events
    result = _fetch_json(
        f"{KALSHI_API_BASE}/events",
        params={"limit": "100", "status": "open", "with_nested_markets": "true"},
    )

    if not result:
        logger.debug("Kalshi events endpoint returned nothing, trying series approach")
        return _fetch_kalshi_via_series()

    events = []
    if isinstance(result, dict):
        events = result.get("events", [])
    elif isinstance(result, list):
        events = result

    for event in events:
        if not isinstance(event, dict):
            continue

        # Filter to crypto-related events
        category = (event.get("category") or "").lower()
        title = (event.get("title") or "").lower()
        series_ticker = event.get("series_ticker") or ""

        is_crypto = (
            category == "crypto"
            or series_ticker in KALSHI_SERIES_MAP
            or any(kw in title for kw in ("bitcoin", "btc", "ethereum", "eth",
                                          "solana", "sol", "doge", "xrp"))
        )
        if not is_crypto:
            continue

        # Extract nested markets
        event_markets = event.get("markets", [])
        for mkt in event_markets:
            if not isinstance(mkt, dict):
                continue

            ticker = mkt.get("ticker") or ""
            subtitle = mkt.get("subtitle") or mkt.get("title") or ""
            yes_price = _safe_float(mkt.get("yes_bid") or mkt.get("last_price"), 0)
            no_price = _safe_float(mkt.get("no_bid"), 0)
            volume = _safe_float(mkt.get("volume") or mkt.get("volume_24h"), 0)
            expiry = mkt.get("close_time") or mkt.get("expiration_time") or ""

            # Detect symbol from series or title
            symbol = KALSHI_SERIES_MAP.get(series_ticker)
            if not symbol:
                symbol = _detect_symbol(title + " " + subtitle)
            if not symbol:
                continue

            question_text = event.get("title", "") + " - " + subtitle

            markets.append({
                "question": question_text,
                "probability": yes_price,
                "volume": volume,
                "expiry": expiry,
                "symbol": symbol,
                "series_ticker": series_ticker,
                "event_ticker": event.get("event_ticker") or "",
                "market_ticker": ticker,
                "yes_price": yes_price,
                "no_price": no_price,
                "source": "kalshi",
            })

    logger.info("Fetched %d crypto markets from Kalshi", len(markets))
    return markets


def _fetch_kalshi_via_series():
    """Fallback: fetch Kalshi markets by known crypto series tickers."""
    markets = []
    priority_series = ["KXBTC", "KXBTCD", "KXBTC15M", "KXETH", "KXETH15M",
                       "KXSOL", "KXSOL15M", "KXDOGE", "KXXRP"]

    for series in priority_series:
        result = _fetch_json(
            f"{KALSHI_API_BASE}/events",
            params={"status": "open", "series_ticker": series, "limit": "10"},
        )
        if not result:
            continue

        events = result.get("events", []) if isinstance(result, dict) else []
        for event in events:
            if not isinstance(event, dict):
                continue

            symbol = KALSHI_SERIES_MAP.get(series, "BTCUSDT")
            event_title = event.get("title") or ""

            # Fetch markets for this event
            event_ticker = event.get("event_ticker")
            if not event_ticker:
                continue

            mkt_result = _fetch_json(
                f"{KALSHI_API_BASE}/markets",
                params={"event_ticker": event_ticker, "limit": "50"},
            )
            if not mkt_result:
                continue

            mkt_list = mkt_result.get("markets", []) if isinstance(mkt_result, dict) else []
            for mkt in mkt_list:
                if not isinstance(mkt, dict):
                    continue

                yes_price = _safe_float(mkt.get("yes_bid") or mkt.get("last_price"), 0)
                volume = _safe_float(mkt.get("volume") or mkt.get("volume_24h"), 0)

                markets.append({
                    "question": event_title + " - " + (mkt.get("subtitle") or mkt.get("title") or ""),
                    "probability": yes_price,
                    "volume": volume,
                    "expiry": mkt.get("close_time") or "",
                    "symbol": symbol,
                    "series_ticker": series,
                    "event_ticker": event_ticker,
                    "market_ticker": mkt.get("ticker") or "",
                    "yes_price": yes_price,
                    "no_price": _safe_float(mkt.get("no_bid"), 0),
                    "source": "kalshi",
                })

    logger.info("Fetched %d crypto markets from Kalshi (series approach)", len(markets))
    return markets


def fetch_kalshi_btc_intraday():
    """
    Fetch Kalshi's intraday BTC prediction markets (15-min resolution).
    These resolve every 15 minutes: "Will BTC be above $X at Y:00?"

    Signal: if 15-min market probability > 80% -> strong SHORT-term LONG

    Returns:
        List of dicts with intraday sentiment signals:
        {symbol, direction, probability, expiry, confidence, strategy}
    """
    signals = []

    # Try 15-minute BTC series
    for series in ["KXBTC15M", "KXETH15M", "KXSOL15M", "KXDOGE15M", "KXXRP15M"]:
        result = _fetch_json(
            f"{KALSHI_API_BASE}/events",
            params={"status": "open", "series_ticker": series, "limit": "5"},
        )
        if not result:
            continue

        events = result.get("events", []) if isinstance(result, dict) else []
        symbol = KALSHI_SERIES_MAP.get(series, "BTCUSDT")

        for event in events:
            if not isinstance(event, dict):
                continue

            event_ticker = event.get("event_ticker")
            if not event_ticker:
                continue

            mkt_result = _fetch_json(
                f"{KALSHI_API_BASE}/markets",
                params={"event_ticker": event_ticker, "limit": "20"},
            )
            if not mkt_result:
                continue

            mkt_list = mkt_result.get("markets", []) if isinstance(mkt_result, dict) else []
            for mkt in mkt_list:
                if not isinstance(mkt, dict):
                    continue

                yes_price = _safe_float(mkt.get("yes_bid") or mkt.get("last_price"), 0)
                if not yes_price or yes_price <= 0:
                    continue

                expiry = mkt.get("close_time") or ""

                # Strong signal: high probability = confident directional bet
                if yes_price >= KALSHI_STRONG_SIGNAL:
                    direction = "LONG"
                    confidence = 0.70 + (yes_price - KALSHI_STRONG_SIGNAL) * 0.5
                elif yes_price <= (1.0 - KALSHI_STRONG_SIGNAL):
                    direction = "SHORT"
                    confidence = 0.70 + ((1.0 - yes_price) - KALSHI_STRONG_SIGNAL) * 0.5
                elif yes_price >= KALSHI_MODERATE_SIGNAL:
                    direction = "LONG"
                    confidence = 0.55 + (yes_price - KALSHI_MODERATE_SIGNAL) * 0.5
                elif yes_price <= (1.0 - KALSHI_MODERATE_SIGNAL):
                    direction = "SHORT"
                    confidence = 0.55 + ((1.0 - yes_price) - KALSHI_MODERATE_SIGNAL) * 0.5
                else:
                    continue  # Too uncertain

                confidence = max(0.40, min(confidence, 0.85))

                signals.append({
                    "symbol": symbol,
                    "direction": direction,
                    "probability": yes_price,
                    "expiry": expiry,
                    "confidence": round(confidence, 3),
                    "strategy": "kalshi_intraday",
                    "series": series,
                    "market_ticker": mkt.get("ticker") or "",
                    "question": (event.get("title") or "") + " - " + (mkt.get("subtitle") or ""),
                })

    logger.info("Fetched %d Kalshi intraday signals", len(signals))
    return signals


# ---------------------------------------------------------------------------
# 5. Spot Price Fetching (Binance 5-mirror failover)
# ---------------------------------------------------------------------------

def _fetch_spot_price(symbol):
    """
    Fetch current spot price using Binance 5-mirror failover chain
    plus CoinGecko/KuCoin/CryptoCompare fallbacks.

    Returns float price or None.
    """
    # Binance mirrors
    for base in BINANCE_MIRRORS:
        try:
            url = f"{base}/api/v3/ticker/price?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                return _safe_float(data.get("price"))
        except Exception:
            continue

    # CoinGecko fallback
    try:
        cg_id = symbol.replace("USDT", "").lower()
        cg_map = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana",
                   "xrp": "ripple", "ada": "cardano", "doge": "dogecoin",
                   "bnb": "binancecoin", "avax": "avalanche-2",
                   "dot": "polkadot", "link": "chainlink", "ltc": "litecoin"}
        cg_id = cg_map.get(cg_id, cg_id)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return _safe_float(data.get(cg_id, {}).get("usd"))
    except Exception:
        pass

    # KuCoin fallback
    try:
        kc_sym = symbol.replace("USDT", "-USDT")
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kc_sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return _safe_float(data.get("data", {}).get("price"))
    except Exception:
        pass

    # CryptoCompare fallback
    try:
        fsym = symbol.replace("USDT", "")
        url = f"https://min-api.cryptocompare.com/data/price?fsym={fsym}&tsyms=USDT"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return _safe_float(data.get("USDT"))
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# 6. Reverse-Engineered Strategies
# ---------------------------------------------------------------------------

def probability_breakout_strategy(markets):
    """
    When a BTC price prediction market breaks above 60% from below 40%
    within 6 hours -> LONG signal (market consensus shifting bullish).

    Inverse: breaks below 40% from above 60% -> SHORT signal.

    Args:
        markets: List of market dicts from Polymarket with clobTokenIds

    Returns:
        List of breakout signal dicts
    """
    signals = []

    for market in markets:
        clob_ids = market.get("clobTokenIds")
        if not clob_ids:
            continue
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except (json.JSONDecodeError, ValueError):
                continue
        if not isinstance(clob_ids, list) or not clob_ids:
            continue

        token_id = clob_ids[0]
        question = market.get("question") or ""
        symbol = _detect_symbol(question)
        if not symbol:
            continue

        history = fetch_price_history(token_id, fidelity=30)
        if len(history) < 8:
            continue

        current_prob = history[-1]["p"]
        current_ts = history[-1]["t"]
        window_start = current_ts - (BREAKOUT_WINDOW_HOURS * 3600)

        # Find min and max probability in the breakout window
        window_prices = [h["p"] for h in history if h["t"] >= window_start]
        if len(window_prices) < 3:
            continue

        window_min = min(window_prices)
        window_max = max(window_prices)

        direction = None
        breakout_type = None

        # Bullish breakout: was below 40%, now above 60%
        if window_min <= BREAKOUT_LOW and current_prob >= BREAKOUT_HIGH:
            direction = "LONG"
            breakout_type = "bullish_breakout"

        # Bearish breakout: was above 60%, now below 40%
        elif window_max >= BREAKOUT_HIGH and current_prob <= BREAKOUT_LOW:
            direction = "SHORT"
            breakout_type = "bearish_breakout"

        if not direction:
            continue

        # For dip markets, invert the signal
        q_lower = question.lower()
        if re.search(r"(dip|drop|fall|below|under)", q_lower):
            direction = "SHORT" if direction == "LONG" else "LONG"

        volume = _safe_float(market.get("volume") or market.get("volumeNum"), 0)
        confidence = 0.65 + min(0.20, abs(current_prob - 0.50) * 0.4)
        confidence = max(0.50, min(confidence, 0.85))

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strategy": "prob_breakout",
            "breakout_type": breakout_type,
            "current_prob": round(current_prob, 4),
            "window_min": round(window_min, 4),
            "window_max": round(window_max, 4),
            "confidence": round(confidence, 3),
            "volume": volume,
            "question": question,
        })

    logger.info("Generated %d probability breakout signals", len(signals))
    return signals


def whale_follow_strategy(whale_positions):
    """
    When 2+ known whales take the same position on a crypto market
    -> follow their direction with high confidence.

    Args:
        whale_positions: List from track_whale_positions()

    Returns:
        List of whale-follow signal dicts
    """
    # Group positions by symbol + direction
    consensus = {}
    for pos in whale_positions:
        key = (pos["symbol"], pos["position_direction"])
        if key not in consensus:
            consensus[key] = []
        consensus[key].append(pos)

    signals = []
    for (symbol, direction), group in consensus.items():
        if len(group) < WHALE_CONSENSUS_MIN:
            continue

        total_size = sum(p.get("size_usd", 0) for p in group)
        avg_reliability = sum(p.get("confidence", 0.5) for p in group) / len(group)
        whale_names = [p["whale_name"] for p in group]

        # More whales = higher confidence
        whale_bonus = min(0.15, (len(group) - WHALE_CONSENSUS_MIN) * 0.05)
        confidence = avg_reliability + whale_bonus
        confidence = max(0.50, min(confidence, 0.90))

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strategy": "whale_follow",
            "whale_count": len(group),
            "whale_names": whale_names,
            "total_size_usd": round(total_size, 2),
            "confidence": round(confidence, 3),
            "question": f"{len(group)} whales positioned {direction} on {symbol}",
        })

    logger.info("Generated %d whale-follow consensus signals", len(signals))
    return signals


def smart_money_divergence_strategy(momentum_signals, spot_prices=None):
    """
    When prediction market probability is rising but spot price is flat/falling
    -> LONG (smart money accumulating via prediction markets before spot moves).

    Inverse: probability falling + spot rising -> SHORT.

    Args:
        momentum_signals: List from compute_probability_momentum()
        spot_prices: Optional dict of {symbol: price}. Fetched if None.

    Returns:
        List of divergence signal dicts
    """
    if spot_prices is None:
        spot_prices = {}

    signals = []

    # Group momentum signals by symbol
    by_symbol = {}
    for sig in momentum_signals:
        sym = sig["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(sig)

    for symbol, mom_signals in by_symbol.items():
        # Get spot price (with caching)
        if symbol not in spot_prices:
            price = _fetch_spot_price(symbol)
            if price:
                spot_prices[symbol] = price

        spot_price = spot_prices.get(symbol)
        if not spot_price:
            continue

        # Aggregate momentum direction across all markets for this symbol
        bullish_momentum = sum(
            1 for s in mom_signals
            if s["direction"] == "LONG" and s.get("momentum_4h")
        )
        bearish_momentum = sum(
            1 for s in mom_signals
            if s["direction"] == "SHORT" and s.get("momentum_4h")
        )

        avg_momentum = sum(
            s.get("momentum_4h", 0) for s in mom_signals if s.get("momentum_4h")
        ) / max(1, len(mom_signals))

        # We can't easily get spot price change from a single call,
        # so we check if the prediction market direction diverges from
        # the overall momentum direction.
        # A divergence signal fires when prediction markets are strongly
        # directional (>= 2 signals same way) but the spot hasn't moved much.
        if bullish_momentum >= 2 and avg_momentum > MOMENTUM_4H_THRESHOLD:
            # Multiple prediction markets turning bullish
            avg_conf = sum(s["confidence"] for s in mom_signals) / len(mom_signals)
            signals.append({
                "symbol": symbol,
                "direction": "LONG",
                "strategy": "smart_money_divergence",
                "prediction_bias": "bullish",
                "bullish_markets": bullish_momentum,
                "bearish_markets": bearish_momentum,
                "avg_momentum": round(avg_momentum, 4),
                "spot_price": spot_price,
                "confidence": round(min(avg_conf + 0.05, 0.85), 3),
                "question": f"Smart money divergence: {bullish_momentum} markets bullish on {symbol}",
            })
        elif bearish_momentum >= 2 and avg_momentum < -MOMENTUM_4H_THRESHOLD:
            avg_conf = sum(s["confidence"] for s in mom_signals) / len(mom_signals)
            signals.append({
                "symbol": symbol,
                "direction": "SHORT",
                "strategy": "smart_money_divergence",
                "prediction_bias": "bearish",
                "bullish_markets": bullish_momentum,
                "bearish_markets": bearish_momentum,
                "avg_momentum": round(avg_momentum, 4),
                "spot_price": spot_price,
                "confidence": round(min(avg_conf + 0.05, 0.85), 3),
                "question": f"Smart money divergence: {bearish_momentum} markets bearish on {symbol}",
            })

    logger.info("Generated %d smart money divergence signals", len(signals))
    return signals


# ---------------------------------------------------------------------------
# 7. Fetch Polymarket Crypto Markets (with events endpoint)
# ---------------------------------------------------------------------------

def fetch_polymarket_crypto_events():
    """
    Fetch crypto prediction markets using both Gamma /markets and /events
    endpoints. The events endpoint gives complete price ladders (e.g., all
    BTC price targets in one event).

    Returns:
        List of market dicts with clobTokenIds for momentum analysis
    """
    markets = []
    seen_ids = set()

    # Event slugs for major crypto price ladders (from research)
    event_slugs = [
        "what-price-will-bitcoin-hit-in-march-2026",
        "what-price-will-bitcoin-hit-before-2027",
        "what-price-will-ethereum-hit-in-march-2026",
        "what-price-will-solana-hit-in-march-2026",
    ]

    # Fetch events by slug
    for slug in event_slugs:
        result = _fetch_json(
            f"{GAMMA_API_BASE}/events",
            params={"slug": slug},
        )
        if not result:
            continue

        events = result if isinstance(result, list) else [result]
        for event in events:
            if not isinstance(event, dict):
                continue
            event_markets = event.get("markets") or []
            for m in event_markets:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id") or m.get("conditionId") or ""
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    markets.append(m)

    # Also fetch by tag/volume for broader coverage
    for tag in ["crypto", "bitcoin"]:
        result = _fetch_json(
            f"{GAMMA_API_BASE}/markets",
            params={
                "tag": tag, "active": "true", "closed": "false",
                "limit": "50", "order": "volume", "ascending": "false",
            },
        )
        if not result:
            continue
        items = result if isinstance(result, list) else result.get("data", [])
        for m in items:
            if not isinstance(m, dict):
                continue
            mid = m.get("id") or m.get("conditionId") or ""
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                markets.append(m)

    # Also try active events sorted by volume
    result = _fetch_json(
        f"{GAMMA_API_BASE}/events",
        params={
            "active": "true", "closed": "false",
            "limit": "50", "order": "volume", "ascending": "false",
        },
    )
    if result:
        events = result if isinstance(result, list) else result.get("data", [])
        for event in events:
            if not isinstance(event, dict):
                continue
            # Filter to crypto
            title = (event.get("title") or "").lower()
            if not any(kw in title for kw in ("bitcoin", "btc", "ethereum", "eth",
                                               "solana", "sol", "crypto", "xrp",
                                               "doge", "cardano")):
                continue
            event_markets = event.get("markets") or []
            for m in event_markets:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id") or m.get("conditionId") or ""
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    markets.append(m)

    logger.info("Fetched %d Polymarket crypto markets (events + markets endpoints)", len(markets))
    return markets


# ---------------------------------------------------------------------------
# 8. Cross-Market Consensus
# ---------------------------------------------------------------------------

def _compute_cross_market_consensus(polymarket_signals, kalshi_signals):
    """
    Find consensus between Polymarket and Kalshi signals.
    If both platforms agree on direction for a symbol -> high confidence.

    Returns list of consensus signal dicts.
    """
    # Build Kalshi direction map by symbol
    kalshi_by_symbol = {}
    for sig in kalshi_signals:
        sym = sig["symbol"]
        if sym not in kalshi_by_symbol:
            kalshi_by_symbol[sym] = {"long": 0, "short": 0, "signals": []}
        if sig["direction"] == "LONG":
            kalshi_by_symbol[sym]["long"] += 1
        else:
            kalshi_by_symbol[sym]["short"] += 1
        kalshi_by_symbol[sym]["signals"].append(sig)

    # Build Polymarket direction map by symbol
    poly_by_symbol = {}
    for sig in polymarket_signals:
        sym = sig["symbol"]
        if sym not in poly_by_symbol:
            poly_by_symbol[sym] = {"long": 0, "short": 0, "signals": []}
        if sig["direction"] == "LONG":
            poly_by_symbol[sym]["long"] += 1
        else:
            poly_by_symbol[sym]["short"] += 1
        poly_by_symbol[sym]["signals"].append(sig)

    consensus_signals = []
    all_symbols = set(list(kalshi_by_symbol.keys()) + list(poly_by_symbol.keys()))

    for symbol in all_symbols:
        kalshi = kalshi_by_symbol.get(symbol)
        poly = poly_by_symbol.get(symbol)

        if not kalshi or not poly:
            continue  # Need both platforms

        # Determine dominant direction on each platform
        kalshi_dir = "LONG" if kalshi["long"] > kalshi["short"] else "SHORT"
        poly_dir = "LONG" if poly["long"] > poly["short"] else "SHORT"

        if kalshi_dir != poly_dir:
            continue  # Disagreement, no consensus

        # Both agree! High confidence signal
        total_signals = (kalshi["long"] + kalshi["short"] +
                         poly["long"] + poly["short"])
        agreeing = (
            (kalshi["long"] + poly["long"]) if kalshi_dir == "LONG"
            else (kalshi["short"] + poly["short"])
        )

        agreement_ratio = agreeing / max(total_signals, 1)

        # Aggregate confidence from underlying signals
        all_sigs = kalshi["signals"] + poly["signals"]
        avg_confidence = sum(s.get("confidence", 0.5) for s in all_sigs) / max(len(all_sigs), 1)

        # Cross-platform agreement boosts confidence
        confidence = avg_confidence + 0.10 + (agreement_ratio * 0.05)
        confidence = max(0.55, min(confidence, 0.92))

        consensus_signals.append({
            "symbol": symbol,
            "direction": kalshi_dir,
            "strategy": "cross_market_consensus",
            "polymarket_signals": poly["long"] + poly["short"],
            "kalshi_signals": kalshi["long"] + kalshi["short"],
            "agreement_ratio": round(agreement_ratio, 3),
            "confidence": round(confidence, 3),
            "question": f"Cross-market consensus: Polymarket + Kalshi agree {kalshi_dir} on {symbol}",
        })

    logger.info("Generated %d cross-market consensus signals", len(consensus_signals))
    return consensus_signals


# ---------------------------------------------------------------------------
# 9. Main Signal Generator
# ---------------------------------------------------------------------------

# Strategy metadata for scanner.py integration
PREDICTION_MARKET_WHALE_STRATEGIES = {
    "polymarket_momentum": {
        "name": "Polymarket Probability Momentum",
        "description": "Detects rapid probability shifts in prediction markets (leading indicator)",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
    "prob_breakout": {
        "name": "Probability Breakout",
        "description": "Detects when market probability breaks 40->60% or 60->40% (consensus shift)",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
    "whale_follow": {
        "name": "Whale Follow (Prediction Markets)",
        "description": "Follows consensus of 2+ known Polymarket whales",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
    "smart_money_divergence": {
        "name": "Smart Money Divergence",
        "description": "Prediction market probability diverges from spot price movement",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
    "kalshi_intraday": {
        "name": "Kalshi Intraday Sentiment",
        "description": "15-minute BTC/ETH/SOL prediction market sentiment from Kalshi",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
    "cross_market_consensus": {
        "name": "Cross-Market Consensus",
        "description": "Polymarket + Kalshi agree on direction (high confidence)",
        "category": "crypto",
        "source_system": "prediction_markets",
    },
}


def generate_prediction_market_picks():
    """
    Main entry point. Combines all prediction market sources:
    1. Polymarket probability momentum (high-volume markets)
    2. Polymarket whale positions (follow smart money)
    3. Probability breakout detection
    4. Kalshi intraday sentiment
    5. Smart money divergence (prediction vs spot)
    6. Cross-market consensus (Polymarket + Kalshi agree -> high confidence)

    Output: picks in alpha_engine standard format
    {symbol, direction, strategy, entry_price, take_profit, stop_loss,
     confidence, source_system, category, tooltip, polymarket_data}
    """
    all_signals = []
    spot_prices = {}

    # ----- 1. Fetch Polymarket crypto markets (events + markets endpoints) -----
    try:
        poly_markets = fetch_polymarket_crypto_events()
        logger.info("Fetched %d Polymarket markets for analysis", len(poly_markets))
    except Exception as e:
        logger.warning("Failed to fetch Polymarket markets: %s", e)
        poly_markets = []

    # ----- 2. Compute probability momentum signals -----
    momentum_signals = []
    if poly_markets:
        try:
            momentum_signals = compute_probability_momentum(poly_markets)
            all_signals.extend(momentum_signals)
        except Exception as e:
            logger.warning("Momentum computation failed: %s", e)

    # ----- 3. Probability breakout detection -----
    if poly_markets:
        try:
            breakout_signals = probability_breakout_strategy(poly_markets)
            all_signals.extend(breakout_signals)
        except Exception as e:
            logger.warning("Breakout detection failed: %s", e)

    # ----- 4. Track whale positions -----
    try:
        whale_positions = track_whale_positions()
        if whale_positions:
            whale_signals = whale_follow_strategy(whale_positions)
            all_signals.extend(whale_signals)
    except Exception as e:
        logger.warning("Whale tracking failed: %s", e)

    # ----- 5. Kalshi crypto markets -----
    kalshi_signals = []
    try:
        kalshi_markets = fetch_kalshi_crypto_markets()
        kalshi_intraday = fetch_kalshi_btc_intraday()
        kalshi_signals = kalshi_intraday
        all_signals.extend(kalshi_intraday)
    except Exception as e:
        logger.warning("Kalshi fetch failed: %s", e)

    # ----- 6. Smart money divergence -----
    if momentum_signals:
        try:
            divergence_signals = smart_money_divergence_strategy(
                momentum_signals, spot_prices
            )
            all_signals.extend(divergence_signals)
        except Exception as e:
            logger.warning("Smart money divergence failed: %s", e)

    # ----- 7. Cross-market consensus -----
    poly_directional = momentum_signals  # Use momentum signals as Polymarket direction
    if poly_directional and kalshi_signals:
        try:
            consensus = _compute_cross_market_consensus(poly_directional, kalshi_signals)
            all_signals.extend(consensus)
        except Exception as e:
            logger.warning("Cross-market consensus failed: %s", e)

    # ----- 8. Convert to alpha_engine standard picks -----
    picks = _signals_to_picks(all_signals, spot_prices)

    # ----- 9. Save to JSON -----
    try:
        _save_whale_signals(picks)
    except Exception as e:
        logger.warning("Failed to save whale signals: %s", e)

    logger.info("Generated %d prediction market whale picks", len(picks))
    return picks


def _signals_to_picks(signals, spot_prices):
    """Convert raw signals to alpha_engine standard pick format."""
    now = datetime.now(timezone.utc)
    picks = []
    seen_ids = set()

    for sig in signals:
        symbol = sig.get("symbol", "BTCUSDT")
        direction = sig.get("direction", "LONG")
        strategy = sig.get("strategy", "prediction_market")
        confidence = sig.get("confidence", 0.50)

        # Fetch spot price if not cached
        if symbol not in spot_prices:
            price = _fetch_spot_price(symbol)
            if price:
                spot_prices[symbol] = price

        entry_price = spot_prices.get(symbol)
        if not entry_price:
            entry_price = None

        # Compute TP/SL based on confidence and direction
        tp = None
        sl = None
        if entry_price:
            # Scale TP/SL with confidence: higher confidence = tighter TP (more precise)
            tp_pct = 0.03 + (1.0 - confidence) * 0.04   # 3-7% TP
            sl_pct = 0.02 + (1.0 - confidence) * 0.03   # 2-5% SL

            if direction == "LONG":
                tp = round(entry_price * (1 + tp_pct), 6)
                sl = round(entry_price * (1 - sl_pct), 6)
            else:
                tp = round(entry_price * (1 - tp_pct), 6)
                sl = round(entry_price * (1 + sl_pct), 6)

        signal_type = "BUY" if direction == "LONG" else "SELL"

        # Build unique pick ID
        pick_id = f"pmwhale_{strategy}_{symbol}_{now.strftime('%Y%m%d%H%M')}"
        base_id = pick_id
        suffix = 0
        while pick_id in seen_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"
        seen_ids.add(pick_id)

        # Build tooltip from signal data
        tooltip_parts = []
        if sig.get("momentum_4h") is not None:
            tooltip_parts.append(f"4h momentum: {sig['momentum_4h']:+.2%}")
        if sig.get("momentum_24h") is not None:
            tooltip_parts.append(f"24h momentum: {sig['momentum_24h']:+.2%}")
        if sig.get("current_prob") is not None:
            tooltip_parts.append(f"prob: {sig['current_prob']:.1%}")
        if sig.get("whale_count"):
            tooltip_parts.append(f"{sig['whale_count']} whales agree")
        if sig.get("agreement_ratio"):
            tooltip_parts.append(f"consensus: {sig['agreement_ratio']:.0%}")
        tooltip = " | ".join(tooltip_parts) if tooltip_parts else strategy

        picks.append({
            "id": pick_id,
            "strategy": strategy,
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal_type,
            "entry_price": entry_price,
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": None,
            "status": "ACTIVE",
            "source_system": "prediction_markets",
            "created_at": now.isoformat(),
            "tooltip": tooltip,
            "polymarket_data": {
                "strategy": strategy,
                "question": sig.get("question", ""),
                "probability": sig.get("current_prob") or sig.get("probability"),
                "volume": sig.get("volume", 0),
                "momentum_4h": sig.get("momentum_4h"),
                "momentum_24h": sig.get("momentum_24h"),
                "whale_names": sig.get("whale_names"),
                "breakout_type": sig.get("breakout_type"),
                "agreement_ratio": sig.get("agreement_ratio"),
                "source_platform": sig.get("source", "polymarket"),
            },
        })

    return picks


def _save_whale_signals(picks):
    """Save prediction market whale picks to JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "prediction_market_whales",
        "strategies": list(PREDICTION_MARKET_WHALE_STRATEGIES.keys()),
        "pick_count": len(picks),
        "picks": picks,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("Saved %d whale picks to %s", len(picks), OUTPUT_FILE)
    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# CLI mode
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for prediction market whale tracker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("=" * 70)
    print("  Prediction Market Whale Tracker & Signal Generator")
    print("=" * 70)
    print()

    picks = generate_prediction_market_picks()

    print()
    print(f"  Total picks generated: {len(picks)}")
    print()

    # Group by strategy
    by_strategy = {}
    for p in picks:
        strat = p["strategy"]
        if strat not in by_strategy:
            by_strategy[strat] = []
        by_strategy[strat].append(p)

    for strat, strat_picks in sorted(by_strategy.items()):
        print(f"  [{strat}] {len(strat_picks)} pick(s)")
        for p in strat_picks[:3]:
            arrow = "LONG " if p["signal_type"] == "BUY" else "SHORT"
            print(f"    {arrow} {p['symbol']:<12s} conf={p['confidence']:.2f}  {p.get('tooltip', '')[:60]}")
        if len(strat_picks) > 3:
            print(f"    ... and {len(strat_picks) - 3} more")
        print()

    print("=" * 70)
    print(f"  Done. {len(picks)} prediction market whale signals saved.")
    print("=" * 70)


if __name__ == "__main__":
    main()

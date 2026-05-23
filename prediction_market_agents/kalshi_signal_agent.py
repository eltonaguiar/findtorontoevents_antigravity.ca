#!/usr/bin/env python3
"""
Agent 3: Kalshi Multi-Timeframe Signal Agent
==============================================
Fetches crypto price predictions from Kalshi's regulated US prediction market
across multiple timeframes (15-min, hourly, daily, weekly, monthly, annual).
Builds a timeframe consensus and generates signals when multiple timeframes agree.

API: GET https://api.elections.kalshi.com/trade-api/v2/events
     GET https://api.elections.kalshi.com/trade-api/v2/markets

No API key required for market data.

FIXED: Changed from keyword-based filtering to series_ticker-based fetching
for reliable crypto event discovery (was returning 0 events before).
"""

import json
import logging
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "kalshi_signals.json"

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
TIMEOUT = 15

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# All known Kalshi crypto series with their symbols and timeframes
CRYPTO_SERIES = {
    # BTC
    "KXBTC": {"symbol": "BTCUSDT", "timeframe": "hourly", "asset": "BTC"},
    "KXBTCD": {"symbol": "BTCUSDT", "timeframe": "daily", "asset": "BTC"},
    "BTCD": {"symbol": "BTCUSDT", "timeframe": "daily", "asset": "BTC"},
    "KXBTC15M": {"symbol": "BTCUSDT", "timeframe": "15min", "asset": "BTC"},
    "KXBTCMAXW": {"symbol": "BTCUSDT", "timeframe": "weekly", "asset": "BTC"},
    "KXBTCMAXM": {"symbol": "BTCUSDT", "timeframe": "monthly", "asset": "BTC"},
    "BTCMAXM": {"symbol": "BTCUSDT", "timeframe": "monthly", "asset": "BTC"},
    "KXBTCMAXY": {"symbol": "BTCUSDT", "timeframe": "annual", "asset": "BTC"},
    "BTCMAXY": {"symbol": "BTCUSDT", "timeframe": "annual", "asset": "BTC"},
    "KXBTCMINY": {"symbol": "BTCUSDT", "timeframe": "annual", "asset": "BTC"},
    "BTCMINY": {"symbol": "BTCUSDT", "timeframe": "annual", "asset": "BTC"},
    # ETH
    "KXETH": {"symbol": "ETHUSDT", "timeframe": "hourly", "asset": "ETH"},
    "KXETHD": {"symbol": "ETHUSDT", "timeframe": "daily", "asset": "ETH"},
    "ETHD": {"symbol": "ETHUSDT", "timeframe": "daily", "asset": "ETH"},
    "KXETH15M": {"symbol": "ETHUSDT", "timeframe": "15min", "asset": "ETH"},
    # SOL
    "KXSOL": {"symbol": "SOLUSDT", "timeframe": "hourly", "asset": "SOL"},
    "KXSOLD": {"symbol": "SOLUSDT", "timeframe": "daily", "asset": "SOL"},
    "KXSOL15M": {"symbol": "SOLUSDT", "timeframe": "15min", "asset": "SOL"},
    # DOGE
    "KXDOGE": {"symbol": "DOGEUSDT", "timeframe": "hourly", "asset": "DOGE"},
    "KXDOGED": {"symbol": "DOGEUSDT", "timeframe": "daily", "asset": "DOGE"},
    "KXDOGE15M": {"symbol": "DOGEUSDT", "timeframe": "15min", "asset": "DOGE"},
    # XRP
    "KXXRP": {"symbol": "XRPUSDT", "timeframe": "hourly", "asset": "XRP"},
    "KXXRPD": {"symbol": "XRPUSDT", "timeframe": "daily", "asset": "XRP"},
    "KXXRP15M": {"symbol": "XRPUSDT", "timeframe": "15min", "asset": "XRP"},
    # Others
    "KXAVAX": {"symbol": "AVAXUSDT", "timeframe": "hourly", "asset": "AVAX"},
    "KXAVAXD": {"symbol": "AVAXUSDT", "timeframe": "daily", "asset": "AVAX"},
    "KXLINK": {"symbol": "LINKUSDT", "timeframe": "hourly", "asset": "LINK"},
    "KXLINKD": {"symbol": "LINKUSDT", "timeframe": "daily", "asset": "LINK"},
    "KXDOT": {"symbol": "DOTUSDT", "timeframe": "hourly", "asset": "DOT"},
    "KXDOTD": {"symbol": "DOTUSDT", "timeframe": "daily", "asset": "DOT"},
    "KXBNB15M": {"symbol": "BNBUSDT", "timeframe": "15min", "asset": "BNB"},
    "KXADA15M": {"symbol": "ADAUSDT", "timeframe": "15min", "asset": "ADA"},
}

# Narrative/event series
EVENT_SERIES = {
    "KXBTCATH": {"symbol": "BTCUSDT", "type": "event", "description": "BTC all-time high"},
    "BTCATH": {"symbol": "BTCUSDT", "type": "event", "description": "BTC all-time high"},
    "KXSOLANAATH": {"symbol": "SOLUSDT", "type": "event", "description": "SOL all-time high"},
    "KXBTCRESERVE": {"symbol": "BTCUSDT", "type": "event", "description": "US BTC reserve"},
}

# Timeframe weights for consensus scoring
TIMEFRAME_WEIGHTS = {
    "15min": 0.10,   # Noise-heavy, low weight
    "hourly": 0.15,
    "daily": 0.25,
    "weekly": 0.25,
    "monthly": 0.15,
    "annual": 0.10,
}


def _fetch(url: str, params: Optional[dict] = None) -> Optional[Any]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "PredictionMarketAgents/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug("Kalshi fetch error %s: %s", url[:80], e)
        return None


def fetch_events_for_series(series_ticker: str) -> List[Dict]:
    """Fetch all open events for a specific series ticker.
    
    FIXED: This replaces the broken keyword-based filtering approach.
    We now query directly by series_ticker which is reliable.
    """
    result = _fetch(f"{KALSHI_API}/events", params={
        "status": "open",
        "series_ticker": series_ticker,
        "limit": "20",
    })
    if result and isinstance(result, dict):
        return result.get("events", [])
    return []


def fetch_crypto_events() -> List[Dict]:
    """Fetch all open crypto events from Kalshi.
    
    FIXED: Instead of keyword filtering (which fails because titles don't
    contain obvious keywords), we query each known crypto series directly.
    """
    events = []
    
    # Query each crypto series directly
    all_series = list(CRYPTO_SERIES.keys()) + list(EVENT_SERIES.keys())
    
    for series_ticker in all_series:
        series_events = fetch_events_for_series(series_ticker)
        if series_events:
            logger.debug("Found %d events for series %s", len(series_events), series_ticker)
            for event in series_events:
                # Add series info to the event for later use
                event["_series_info"] = CRYPTO_SERIES.get(series_ticker) or EVENT_SERIES.get(series_ticker)
                event["_series_ticker"] = series_ticker
            events.extend(series_events)
        
        # Rate limiting — Kalshi enforces strict rate limits (429 errors)
        time.sleep(1.0)

    return events


def fetch_event_markets(event_ticker: str) -> List[Dict]:
    """Fetch all markets (strike prices) for a specific event."""
    time.sleep(1.0)  # Rate limit before each markets fetch
    result = _fetch(f"{KALSHI_API}/markets", params={
        "event_ticker": event_ticker,
        "limit": "200",
    })
    if result and isinstance(result, dict):
        markets = result.get("markets", [])
        if not markets:
            logger.warning("[KALSHI] 0 markets for event %s (API may have changed format)", event_ticker)
        return markets
    logger.warning("[KALSHI] No response for event %s markets", event_ticker)
    return []


def analyze_event_markets(markets: List[Dict], series_info: Dict) -> Dict:
    """
    Analyze a set of markets (price ranges) for a crypto event.
    Build an implied probability distribution and extract directional bias.
    """
    if not markets:
        return {}

    symbol = series_info.get("symbol", "BTCUSDT")
    timeframe = series_info.get("timeframe", "unknown")

    # Parse strike prices and probabilities
    # Kalshi API v2 (2026) changed field names:
    #   yes_ask -> yes_ask_dollars, volume -> volume_fp,
    #   new: floor_strike, strike_type, subtitle has strike info
    strikes = []
    for m in markets:
        try:
            # YES probability — try new dollar fields first, fall back to legacy
            yes_price = None
            for key in ("yes_ask_dollars", "yes_bid_dollars", "last_price_dollars"):
                raw = m.get(key)
                if raw is not None:
                    try:
                        yes_price = float(raw)  # Already 0-1 dollar range
                        break
                    except (TypeError, ValueError):
                        continue
            if yes_price is None:
                for key in ("yes_ask", "yes_bid", "last_price"):
                    raw = m.get(key)
                    if raw is not None:
                        try:
                            yes_price = float(raw) / 100.0
                            break
                        except (TypeError, ValueError):
                            continue
            if yes_price is None:
                yes_price = 0.5

            # Strike price — prefer structured floor_strike field
            strike_price = None
            fs = m.get("floor_strike")
            if fs is not None:
                try:
                    strike_price = float(fs)
                except (TypeError, ValueError):
                    pass
            if strike_price is None:
                text = m.get("subtitle", "") or m.get("title", "")
                price_match = re.search(r'\$?([\d,]+(?:\.\d+)?)\s*[kK]?', text)
                if price_match:
                    val = float(price_match.group(1).replace(",", ""))
                    if "k" in text.lower() and val < 1000:
                        val *= 1000
                    if val > 10:
                        strike_price = val

            # Direction — prefer strike_type field, fall back to text
            st = m.get("strike_type", "")
            if st == "greater":
                is_above, is_below = True, False
            elif st in ("less", "lesser"):
                is_above, is_below = False, True
            else:
                text = (m.get("subtitle", "") + " " + m.get("title", "")).lower()
                is_above = any(w in text for w in ["above", "between", "higher", "over", "reach"])
                is_below = any(w in text for w in ["below", "under", "lower", "floor"])

            # Volume — try volume_fp first
            vol_raw = m.get("volume_fp") or m.get("volume") or "0"
            try:
                volume = int(float(str(vol_raw)))
            except (TypeError, ValueError):
                volume = 0

            strikes.append({
                "ticker": m.get("ticker", ""),
                "title": m.get("subtitle", "") or m.get("title", ""),
                "yes_price": yes_price,
                "strike_price": strike_price,
                "is_above": is_above,
                "is_below": is_below,
                "volume": volume,
            })
        except Exception:
            continue

    if not strikes:
        return {}

    # Calculate directional bias
    # Weight by volume and probability
    bullish_weight = 0
    bearish_weight = 0
    total_volume = sum(s["volume"] for s in strikes) or 1

    for s in strikes:
        weight = max(s["volume"], 1)
        if s["is_above"]:
            bullish_weight += s["yes_price"] * weight
            bearish_weight += (1 - s["yes_price"]) * weight
        elif s["is_below"]:
            bearish_weight += s["yes_price"] * weight
            bullish_weight += (1 - s["yes_price"]) * weight
        else:
            # Neutral — split
            bullish_weight += s["yes_price"] * weight * 0.5
            bearish_weight += (1 - s["yes_price"]) * weight * 0.5

    total_weight = bullish_weight + bearish_weight
    if total_weight > 0:
        bullish_ratio = bullish_weight / total_weight
    else:
        bullish_ratio = 0.5

    # Direction
    if bullish_ratio > 0.55:
        direction = "LONG"
    elif bullish_ratio < 0.45:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "bullish_ratio": round(bullish_ratio, 4),
        "num_markets": len(strikes),
        "total_volume": total_volume,
        "strikes": strikes[:5],  # Top 5 for context
    }


def build_timeframe_consensus(analyses: List[Dict]) -> Dict[str, Dict]:
    """
    Build consensus across multiple timeframes for each symbol.
    Returns per-symbol consensus with weighted direction.
    """
    by_symbol = {}

    for a in analyses:
        sym = a["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = {"timeframes": {}, "symbol": sym}
        by_symbol[sym]["timeframes"][a["timeframe"]] = a

    consensus = {}
    for sym, data in by_symbol.items():
        tfs = data["timeframes"]
        if not tfs:
            continue

        weighted_score = 0  # Positive = bullish, negative = bearish
        total_weight = 0
        agreeing = 0
        total = len(tfs)

        majority_direction = None
        direction_votes = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}

        for tf_name, tf_data in tfs.items():
            weight = TIMEFRAME_WEIGHTS.get(tf_name, 0.10)
            ratio = tf_data["bullish_ratio"]
            direction = tf_data["direction"]

            # Convert to -1 to +1 scale
            score = (ratio - 0.5) * 2
            weighted_score += score * weight
            total_weight += weight

            direction_votes[direction] = direction_votes.get(direction, 0) + 1

        # Determine consensus direction
        net_score = weighted_score / total_weight if total_weight > 0 else 0

        if net_score > 0.10:
            consensus_dir = "LONG"
        elif net_score < -0.10:
            consensus_dir = "SHORT"
        else:
            consensus_dir = "NEUTRAL"

        # Agreement ratio
        if consensus_dir != "NEUTRAL":
            agreeing = direction_votes.get(consensus_dir, 0)
        else:
            agreeing = direction_votes.get("NEUTRAL", 0)

        agreement_pct = agreeing / total if total > 0 else 0

        # Confidence: higher when more timeframes agree
        base_conf = 0.60
        if agreement_pct >= 0.80:
            base_conf = 0.85
        elif agreement_pct >= 0.60:
            base_conf = 0.75
        elif agreement_pct >= 0.40:
            base_conf = 0.65

        # Boost for extreme net scores
        base_conf += min(0.10, abs(net_score) * 0.15)
        confidence = min(0.95, base_conf)

        consensus[sym] = {
            "symbol": sym,
            "direction": consensus_dir,
            "confidence": round(confidence, 3),
            "net_score": round(net_score, 4),
            "agreement_pct": round(agreement_pct, 2),
            "timeframes_analyzed": total,
            "timeframes_agreeing": agreeing,
            "direction_votes": direction_votes,
            "timeframe_details": {
                tf: {
                    "direction": d["direction"],
                    "bullish_ratio": d["bullish_ratio"],
                }
                for tf, d in tfs.items()
            },
        }

    return consensus


def scan_kalshi() -> Dict[str, Any]:
    """
    Full Kalshi scan:
    1. Fetch all crypto events
    2. Get markets for each event
    3. Analyze per-timeframe
    4. Build cross-timeframe consensus
    5. Generate signals
    """
    logger.info("=" * 60)
    logger.info("  Kalshi Multi-Timeframe Signal Agent — Scanning crypto markets")
    logger.info("=" * 60)

    now = datetime.now(timezone.utc)

    # Step 1: Fetch crypto events (FIXED: uses series_ticker filtering)
    events = fetch_crypto_events()
    logger.info("Found %d crypto events on Kalshi", len(events))

    # Step 2: Analyze each event
    all_analyses = []
    zero_market_events: list = []
    for event in events:
        event_ticker = event.get("event_ticker", "")
        series_info = event.get("_series_info", {})
        series_ticker = event.get("_series_ticker", "")

        if not series_info:
            continue

        markets = fetch_event_markets(event_ticker)
        if not markets:
            zero_market_events.append(event_ticker)
            logger.warning("No markets returned for event %s (series: %s)", event_ticker, series_ticker)
            continue

        analysis = analyze_event_markets(markets, series_info)
        if analysis:
            all_analyses.append(analysis)
            logger.info(
                "  %s %s: %s (bullish: %.0f%%, markets: %d)",
                analysis["symbol"], analysis["timeframe"],
                analysis["direction"],
                analysis["bullish_ratio"] * 100,
                analysis["num_markets"],
            )

        time.sleep(0.2)  # Rate limiting

    if zero_market_events:
        logger.warning(
            "Zero-market events (%d): %s",
            len(zero_market_events),
            ", ".join(zero_market_events),
        )
    logger.info(
        "Event analysis complete: %d analyzed, %d zero-market skipped",
        len(all_analyses), len(zero_market_events),
    )

    # Step 3: Build consensus
    consensus = build_timeframe_consensus(all_analyses)

    # Step 4: Generate signals
    signals = []
    for sym, cons in consensus.items():
        if cons["direction"] == "NEUTRAL":
            continue

        signal = {
            "symbol": sym,
            "direction": cons["direction"],
            "confidence": cons["confidence"],
            "strategy": "kalshi_mtf_consensus",
            "source_system": "kalshi_signal_agent",
            "category": "crypto",
            "signal_type": "BUY" if cons["direction"] == "LONG" else "SELL",
            "status": "OPEN",
            "entry_price": 0,
            "take_profit": 0,
            "stop_loss": 0,
            "kalshi_data": {
                "net_score": cons["net_score"],
                "agreement_pct": cons["agreement_pct"],
                "timeframes_analyzed": cons["timeframes_analyzed"],
                "timeframes_agreeing": cons["timeframes_agreeing"],
                "direction_votes": cons["direction_votes"],
                "timeframe_details": cons["timeframe_details"],
            },
            "reason": (
                f"Kalshi consensus: {cons['direction']} {sym} "
                f"({cons['timeframes_agreeing']}/{cons['timeframes_analyzed']} "
                f"timeframes agree, net score: {cons['net_score']:+.2f})"
            ),
            "timestamp": now.isoformat(),
            "entry_date": now.strftime("%Y-%m-%d"),
        }
        signals.append(signal)

    result = {
        "generated_at": now.isoformat(),
        "source": "kalshi_signal_agent",
        "events_analyzed": len(events),
        "analyses_completed": len(all_analyses),
        "consensus_symbols": len(consensus),
        "signals_generated": len(signals),
        "consensus": consensus,
        "signals": signals,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Saved %d Kalshi signals to %s", len(signals), OUTPUT_FILE)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = scan_kalshi()
    print(f"\nKalshi Signal Agent Complete:")
    print(f"  Events analyzed: {result.get('events_analyzed', 0)}")
    print(f"  Signals generated: {result.get('signals_generated', 0)}")
    for sig in result.get("signals", []):
        kd = sig.get("kalshi_data", {})
        print(f"  {sig['direction']:5s} {sig['symbol']:12s} conf={sig['confidence']:.2f} "
              f"agree={kd.get('agreement_pct', 0):.0%} net={kd.get('net_score', 0):+.2f}")

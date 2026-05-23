"""Polymarket scraper - extracts crypto prediction markets with outcome tracking.

Uses Polymarket's public Gamma API to fetch market data for crypto predictions.
Tracks Bitcoin Up/Down hourly markets and other crypto events with resolution dates.
Validates predictions against actual outcomes.
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

# Polymarket Gamma API
POLYMARKET_API = "https://gamma-api.polymarket.com"

# Crypto-related tags to search for
CRYPTO_TAGS = ['crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'solana', 'sol']

# Symbols we track
SYMBOLS_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT", 
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT",
    "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOT": "DOTUSDT",
    "SUI": "SUIUSDT",
    "MATIC": "MATICUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
}

DIRECTION_RE = re.compile(r'\b(above|below|higher|lower|up|down|bullish|bearish)\b', re.I)
PRICE_RE = re.compile(r'\$?([\d,]+\.?\d*)\s*[kK]?', re.I)


def fetch_polymarket_events() -> list[dict]:
    """Fetch active events from Polymarket."""
    events = []
    
    try:
        # Use events endpoint - more reliable
        url = f"{POLYMARKET_API}/events"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 100,
            "order": "volume",
            "ascending": "false"
        }
        
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        events = resp.json()
            
    except Exception as e:
        print(f"  Polymarket API error: {e}")
        
    return events


def fetch_closed_crypto_events() -> list[dict]:
    """Fetch recently closed crypto events for outcome validation."""
    events = []
    
    try:
        url = f"{POLYMARKET_API}/events"
        params = {
            "active": "false",
            "closed": "true",
            "limit": 50,
            "order": "endDate",
            "ascending": "false"
        }
        
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        all_closed = resp.json()
        
        # Filter for crypto-related closed events
        for event in all_closed:
            title = event.get("title", "").lower()
            description = event.get("description", "").lower()
            tags = [t.get("slug", "").lower() for t in event.get("tags", [])]
            
            is_crypto = any(tag in tags for tag in CRYPTO_TAGS)
            is_crypto = is_crypto or any(sym.lower() in title for sym in SYMBOLS_MAP.keys())
            is_crypto = is_crypto or "bitcoin" in title or "ethereum" in title
            
            if is_crypto:
                events.append(event)
                
    except Exception as e:
        print(f"  Closed events API error: {e}")
        
    return events


def is_crypto_event(event: dict) -> bool:
    """Check if an event is crypto-related using strict word boundary matching.

    Prevents false positives like 'Paris mayoral election' matching 'sol',
    or 'whether' matching 'eth'.
    """
    title = event.get("title", "").lower()
    description = event.get("description", "").lower()
    full_text = f"{title} {description}"

    # Check tags first (most reliable signal)
    tags = [t.get("slug", "").lower() for t in event.get("tags", [])]
    if any(tag in tags for tag in CRYPTO_TAGS):
        return True

    # Use word boundary regex for symbol matching to avoid false positives
    # e.g. "eth" should NOT match "whether", "sol" should NOT match "solution"
    for sym in SYMBOLS_MAP.keys():
        pattern = r'\b' + re.escape(sym.lower()) + r'\b'
        if re.search(pattern, full_text):
            return True

    # Check unambiguous crypto terms (these are long enough to avoid false matches)
    unambiguous_terms = ["bitcoin", "ethereum", "cryptocurrency", "blockchain",
                         "binance", "coinbase", "defi", "altcoin"]
    if any(term in full_text for term in unambiguous_terms):
        return True

    # Short terms like "btc", "eth", "crypto" need word boundary matching
    short_terms = ["btc", "eth", "crypto"]
    for term in short_terms:
        if re.search(r'\b' + term + r'\b', full_text):
            return True

    return False


def extract_symbol_from_event(event: dict) -> str | None:
    """Extract trading symbol from event title/description using word boundaries.

    Returns None if no crypto symbol can be confidently identified.
    Prevents mapping political/news events to random crypto symbols.
    """
    title = event.get("title", "").lower()
    description = event.get("description", "").lower()
    full_text = f"{title} {description}"

    # Check for specific symbols with word boundary matching
    for sym, pair in SYMBOLS_MAP.items():
        pattern = r'\b' + re.escape(sym.lower()) + r'\b'
        if re.search(pattern, full_text):
            return pair

    # Check unambiguous full names
    if "bitcoin" in full_text:
        return "BTCUSDT"
    if "ethereum" in full_text:
        return "ETHUSDT"

    # Do NOT default to any symbol — return None if we can't identify one
    return None


def parse_direction_from_event(event: dict) -> str | None:
    """Parse prediction direction (LONG/SHORT) from event."""
    title = event.get("title", "").lower()
    description = event.get("description", "").lower()
    full_text = f"{title} {description}"
    
    # Look for directional keywords
    if any(w in full_text for w in ["above", "higher", "up", "over", "bullish", "long"]):
        return "LONG"
    elif any(w in full_text for w in ["below", "lower", "down", "under", "bearish", "short"]):
        return "SHORT"
    
    # Check market outcomes for direction
    markets = event.get("markets", [])
    if markets:
        market = markets[0]
        outcomes = market.get("outcomes", [])
        outcome_str = " ".join(outcomes).lower()
        
        if any(w in outcome_str for w in ["yes", "up", "above", "higher"]):
            return "LONG"
        elif any(w in outcome_str for w in ["no", "down", "below", "lower"]):
            return "SHORT"
    
    return None


def extract_target_from_event(event: dict) -> float | None:
    """Extract target price from event."""
    title = event.get("title", "")
    
    # Look for price patterns
    price_matches = PRICE_RE.findall(title)
    for match in price_matches:
        if match:
            try:
                val = float(match.replace(",", ""))
                if "k" in title.lower() and val < 1000:
                    val *= 1000
                if val > 100:  # Reasonable crypto price
                    return val
            except:
                pass
    
    return None


def parse_event_to_prediction(event: dict) -> dict | None:
    """Parse a Polymarket event into our prediction format."""
    if not is_crypto_event(event):
        return None
    
    symbol = extract_symbol_from_event(event)
    if not symbol:
        return None
    
    direction = parse_direction_from_event(event)
    if not direction:
        return None
    
    target_price = extract_target_from_event(event)
    
    # Get resolution date
    end_date = event.get("endDate")
    resolution_date = None
    if end_date:
        try:
            resolution_date = end_date
        except:
            pass
    
    # Get current market probability (sentiment)
    sentiment = None
    markets = event.get("markets", [])
    if markets:
        market = markets[0]
        outcome_prices = market.get("outcomePrices", [])
        if outcome_prices and len(outcome_prices) >= 2:
            try:
                if isinstance(outcome_prices[0], str):
                    yes_prob = float(outcome_prices[0])
                else:
                    yes_prob = outcome_prices[0]
                sentiment = (yes_prob - 0.5) * 2  # Convert to -1 to 1 scale
            except:
                pass
    
    # Build prediction
    event_slug = event.get("slug", "")
    event_id = event.get("id", "")
    title = event.get("title", "")
    
    market_url = f"https://polymarket.com/event/{event_slug}" if event_slug else \
                 f"https://polymarket.com/event/{event_id}"
    
    return {
        "predictor_id": "polymarket:consensus",
        "platform": "polymarket",
        "display_name": "Polymarket Consensus",
        "symbol": symbol,
        "direction": direction,
        "entry_price": None,
        "take_profit": target_price,
        "stop_loss": None,
        "sentiment_score": sentiment,
        "resolution_date": resolution_date,
        "source_url": market_url,
        "source_text": title,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "is_known_analyst": 0,
        "analyst_category": "prediction_market",
        "event_id": str(event_id),
        "event_slug": event_slug,
    }


def validate_closed_prediction(event: dict, conn) -> bool:
    """Validate a closed Polymarket event against our predictions."""
    event_id = event.get("id")
    if not event_id:
        return False
    
    # Find our prediction for this event
    cursor = conn.execute(
        "SELECT id, direction, symbol FROM predictions WHERE event_id = ? AND platform = 'polymarket'",
        (str(event_id),)
    )
    pred = cursor.fetchone()
    
    if not pred:
        return False
    
    # Get the winning outcome
    markets = event.get("markets", [])
    if not markets:
        return False
    
    market = markets[0]
    winning_outcome = market.get("winningOutcome")
    outcomes = market.get("outcomes", [])
    
    if not winning_outcome or not outcomes:
        return False
    
    # Determine if prediction was correct
    pred_direction = pred["direction"]
    winning_str = str(winning_outcome).lower()
    
    # Simple validation: if direction was LONG and Yes/Up won, or SHORT and No/Down won
    won = False
    
    if pred_direction == "LONG":
        won = any(w in winning_str for w in ["yes", "up", "above", "higher", "long"])
    elif pred_direction == "SHORT":
        won = any(w in winning_str for w in ["no", "down", "below", "lower", "short"])
    
    # Calculate PnL (simplified - would need actual price data for full calculation)
    pnl = 10.0 if won else -10.0
    
    # Update prediction
    status = "RESOLVED_WIN" if won else "RESOLVED_LOSS"
    conn.execute(
        """UPDATE predictions 
           SET status = ?, outcome_pnl_pct = ?, resolved_at = ?
           WHERE id = ?""",
        (status, pnl, datetime.now(timezone.utc).isoformat(), pred["id"])
    )
    conn.commit()
    
    print(f"  Validated: {pred['symbol']} {pred_direction} -> {status}")
    return True


def scrape_polymarket() -> int:
    """Scrape Polymarket crypto prediction markets."""
    print("=" * 60)
    print("Polymarket Crypto Predictions Scraper")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    validated = 0
    
    # Phase 1: Fetch and validate closed events
    print("\n[Phase 1] Checking closed events for validation...")
    closed_events = fetch_closed_crypto_events()
    print(f"  Found {len(closed_events)} recently closed crypto events")
    
    for event in closed_events[:20]:  # Check last 20
        if validate_closed_prediction(event, conn):
            validated += 1
    
    print(f"  Validated {validated} predictions")
    
    # Phase 2: Fetch active events
    print("\n[Phase 2] Fetching active crypto markets...")
    events = fetch_polymarket_events()
    print(f"  Found {len(events)} total events")
    
    crypto_events = [e for e in events if is_crypto_event(e)]
    print(f"  Filtered to {len(crypto_events)} crypto events")
    
    for event in crypto_events:
        try:
            pred = parse_event_to_prediction(event)
            if pred:
                # Check for duplicates by event_id
                existing = conn.execute(
                    "SELECT id FROM predictions WHERE event_id = ? AND platform = 'polymarket'",
                    (pred.get("event_id"),)
                ).fetchone()
                
                if not existing:
                    conn.execute("""
                        INSERT INTO predictions
                        (predictor_id, platform, symbol, direction, entry_price, take_profit,
                         stop_loss, sentiment_score, source_url, source_text, scraped_at,
                         status, is_known_analyst, analyst_category, resolution_date, event_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)
                    """, (
                        pred["predictor_id"], pred["platform"], pred["symbol"],
                        pred["direction"], pred["entry_price"], pred["take_profit"],
                        pred["stop_loss"], pred["sentiment_score"], pred["source_url"],
                        pred["source_text"], pred["scraped_at"],
                        pred["is_known_analyst"], pred["analyst_category"],
                        pred.get("resolution_date"), pred.get("event_id")
                    ))
                    conn.commit()
                    total += 1
                    print(f"    + {pred['symbol']} {pred['direction']} (resolves: {pred.get('resolution_date', 'N/A')[:10]})")
                    
        except Exception as e:
            print(f"    Error parsing event: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('polymarket', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        len(crypto_events),
        total,
        None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"Polymarket: {total} new predictions, {validated} validated")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    scrape_polymarket()

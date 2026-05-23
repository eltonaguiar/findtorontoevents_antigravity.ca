"""
Limitless Scraper - Prediction market on Base chain
https://limitless.exchange
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from crawler_engine import CrawlerEngine
import asyncio

LIMITLESS_API = "https://api.limitless.exchange/markets"


def fetch_limitless_markets() -> list[dict]:
    """Fetch active markets from Limitless"""
    engine = CrawlerEngine(delay=1.0, timeout=30)
    html, method = asyncio.run(engine.fetch(LIMITLESS_API, use_js=False))
    
    if not html:
        print("[Limitless] Failed to fetch markets")
        return []
    
    try:
        data = json.loads(html)
        markets = data if isinstance(data, list) else data.get("markets", [])
        
        # Filter for crypto-related markets
        crypto_keywords = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", 
                          "crypto", "price", "market"]
        
        crypto_markets = []
        for market in markets:
            title = (market.get("title", "") + " " + market.get("description", "")).lower()
            if any(kw in title for kw in crypto_keywords):
                crypto_markets.append(market)
        
        return crypto_markets
    except json.JSONDecodeError as e:
        print(f"[Limitless] JSON error: {e}")
        return []


def parse_prediction(market: dict) -> Optional[dict]:
    """Convert Limitless market to prediction format"""
    title = market.get("title", "").lower()
    description = market.get("description", "").lower()
    
    # Determine direction
    direction = "LONG"
    if any(word in title + description for word in ["below", "down", "decrease", "lower", "fall"]):
        direction = "SHORT"
    
    # Extract symbol
    symbol = _detect_symbol(title + description)
    
    # Extract price target
    import re
    price_match = re.search(r'\$([\d,]+(?:\.\d+)?)k?', title + description)
    target_price = None
    if price_match:
        price_str = price_match.group(1).replace(",", "")
        target_price = float(price_str)
        if "k" in price_match.group(0).lower():
            target_price *= 1000
    
    # Get probability from market data
    probability = 0.5
    if "outcomePrices" in market:
        try:
            prices = json.loads(market["outcomePrices"])
            if isinstance(prices, list) and len(prices) >= 2:
                probability = float(prices[0]) / 100  # Yes price
        except:
            pass
    
    return {
        "predictor_id": "limitless:market",
        "platform": "limitless",
        "symbol": symbol,
        "direction": direction,
        "entry_price": None,
        "take_profit": target_price,
        "stop_loss": None,
        "confidence": probability,
        "source_url": f"https://limitless.exchange/markets/{market.get('address', '')}",
        "source_text": f"{market.get('title', '')}: {market.get('description', '')}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "resolution_date": market.get("expirationDate"),
        "event_id": market.get("address"),
    }


def _detect_symbol(text: str) -> str:
    """Detect trading symbol from text"""
    text = text.lower()
    if "bitcoin" in text or "btc" in text:
        return "BTCUSDT"
    elif "ethereum" in text or "eth" in text:
        return "ETHUSDT"
    elif "solana" in text or "sol" in text:
        return "SOLUSDT"
    return "CRYPTO"


def insert_prediction(conn: sqlite3.Connection, pred: dict) -> bool:
    """Insert prediction to database"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO predictions 
            (predictor_id, platform, symbol, direction, entry_price, take_profit,
             stop_loss, sentiment_score, source_url, source_text, scraped_at,
             status, resolution_date, event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(predictor_id, symbol, scraped_at) DO UPDATE SET
                source_text = excluded.source_text,
                sentiment_score = excluded.sentiment_score
            """,
            (
                pred["predictor_id"],
                pred["platform"],
                pred["symbol"],
                pred["direction"],
                pred["entry_price"],
                pred["take_profit"],
                pred["stop_loss"],
                pred.get("confidence"),
                pred["source_url"],
                pred["source_text"],
                pred["scraped_at"],
                pred.get("resolution_date"),
                pred.get("event_id"),
            )
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[Limitless] DB error: {e}")
        return False


def scrape_limitless() -> int:
    """Main scraper function"""
    print("[Limitless] Fetching crypto prediction markets...")
    
    markets = fetch_limitless_markets()
    if not markets:
        print("[Limitless] No crypto markets found")
        return 0
    
    print(f"[Limitless] Found {len(markets)} crypto markets")
    
    # Connect to DB
    db_path = Path(__file__).parent.parent / "data" / "predictions.db"
    conn = sqlite3.connect(db_path)
    
    inserted = 0
    for market in markets:
        pred = parse_prediction(market)
        if pred:
            if insert_prediction(conn, pred):
                inserted += 1
                print(f"  + {pred['symbol']} {pred['direction']} | {market.get('title', '')[:50]}...")
    
    conn.close()
    print(f"[Limitless] Inserted {inserted} predictions")
    return inserted


if __name__ == "__main__":
    scrape_limitless()

"""
Kalshi Scraper - US prediction market for crypto, politics, economics
https://kalshi.com
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from crawler_engine import CrawlerEngine
import asyncio

# Kalshi API endpoints
KALSHI_API_BASE = "https://trading-api.kalshi.com/trade-api/v2"
KALSHI_MARKETS_URL = f"{KALSHI_API_BASE}/markets"

# Crypto-related market series on Kalshi
CRYPTO_SERIES = [
    "KXBTC",  # Bitcoin
    "KXETH",  # Ethereum
    "KXSOL",  # Solana
]


def fetch_kalshi_markets() -> list[dict]:
    """Fetch active crypto markets from Kalshi"""
    markets = []
    engine = CrawlerEngine(delay=1.0, timeout=30)
    
    for series in CRYPTO_SERIES:
        url = f"{KALSHI_MARKETS_URL}?series_ticker={series}&status=open"
        html, method = asyncio.run(engine.fetch(url, use_js=False))
        
        if not html:
            print(f"[Kalshi] Failed to fetch {series}")
            continue
            
        try:
            data = json.loads(html)
            for market in data.get("markets", []):
                markets.append({
                    "ticker": market.get("ticker"),
                    "title": market.get("title"),
                    "description": market.get("description"),
                    "yes_ask": market.get("yes_ask"),
                    "yes_bid": market.get("yes_bid"),
                    "no_ask": market.get("no_ask"),
                    "no_bid": market.get("no_bid"),
                    "volume": market.get("volume"),
                    "liquidity": market.get("liquidity"),
                    "expiration": market.get("expiration_date"),
                    "series": series,
                })
        except json.JSONDecodeError:
            print(f"[Kalshi] Invalid JSON for {series}")
            continue
    
    return markets


def parse_prediction(market: dict) -> Optional[dict]:
    """Convert Kalshi market to prediction format"""
    title = market.get("title", "").lower()
    
    # Determine direction based on market title
    direction = "LONG"  # Default
    if any(word in title for word in ["below", "down", "decrease", "lower"]):
        direction = "SHORT"
    
    # Extract price levels from title (e.g., "Bitcoin to close above $65000")
    import re
    price_match = re.search(r'\$([\d,]+(?:\.\d+)?)', market.get("title", ""))
    target_price = None
    if price_match:
        target_price = float(price_match.group(1).replace(",", ""))
    
    # Current probability (yes price = probability %)
    yes_price = market.get("yes_ask", 50)
    if yes_price:
        probability = yes_price / 100.0
    else:
        probability = 0.5
    
    return {
        "predictor_id": "kalshi:market",
        "platform": "kalshi",
        "symbol": _map_to_symbol(market.get("series", "")),
        "direction": direction,
        "entry_price": None,  # Binary market, no entry price
        "take_profit": target_price,
        "stop_loss": None,
        "confidence": probability,
        "source_url": f"https://kalshi.com/markets/{market.get('ticker', '')}",
        "source_text": f"{market.get('title', '')}: {market.get('description', '')}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "resolution_date": market.get("expiration"),
        "market_data": {
            "yes_price": market.get("yes_ask"),
            "no_price": market.get("no_ask"),
            "volume": market.get("volume"),
            "liquidity": market.get("liquidity"),
        }
    }


def _map_to_symbol(series: str) -> str:
    """Map Kalshi series to trading symbol"""
    mapping = {
        "KXBTC": "BTCUSDT",
        "KXETH": "ETHUSDT",
        "KXSOL": "SOLUSDT",
    }
    return mapping.get(series, "UNKNOWN")


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
                pred.get("market_data", {}).get("volume"),
            )
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[Kalshi] DB error: {e}")
        return False


def scrape_kalshi() -> int:
    """Main scraper function"""
    print("[Kalshi] Fetching crypto prediction markets...")
    
    markets = fetch_kalshi_markets()
    if not markets:
        print("[Kalshi] No markets found")
        return 0
    
    print(f"[Kalshi] Found {len(markets)} markets")
    
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
    print(f"[Kalshi] Inserted {inserted} predictions")
    return inserted


if __name__ == "__main__":
    scrape_kalshi()

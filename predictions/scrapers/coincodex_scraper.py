"""CoinCodex scraper - extracts price predictions and signals.

Uses CrawlerEngine for reliable RSS and API fetching.
"""
import asyncio
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

try:
    from crawler_engine import CrawlerEngine
    HAS_CRAWLER = True
except ImportError:
    HAS_CRAWLER = False
    print("Warning: crawler_engine not available, using basic requests")

import requests

# CoinCodex API endpoints
COINCEX_API = "https://coincodex.com/api/coincodex"
COINCEX_COINS = f"{COINCEX_API}/coins"
COINCEX_PREDICTIONS = f"{COINCEX_API}/predictions"

# Top coins to track
TOP_COINS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "LINK", "AVAX", 
    "XRP", "ADA", "DOT", "SUI", "MATIC", "ARB", "OP"
]

SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOT": "DOTUSDT", "SUI": "SUIUSDT", "MATIC": "MATICUSDT",
    "ARB": "ARBUSDT", "OP": "OPUSDT",
}


async def fetch_coincodex_rss() -> tuple[list[dict], str]:
    """Fetch CoinCodex RSS using CrawlerEngine."""
    url = "https://coincodex.com/rss/"
    
    if HAS_CRAWLER:
        engine = CrawlerEngine(delay=1.0, timeout=20)
        html, method = await engine.fetch(url, use_js=False)
        
        if html:
            entries = []
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(html)
                channel = root.find("channel")
                if channel:
                    for item in channel.findall("item"):
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        desc = item.findtext("description", "")
                        pub_date = item.findtext("pubDate", "")
                        
                        entries.append({
                            "title": title,
                            "url": link,
                            "description": desc,
                            "published": pub_date
                        })
            except Exception as e:
                print(f"  RSS parse error: {e}")
            
            return entries, method
        return [], "failed"
    else:
        # Fallback
        try:
            resp = requests.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code == 200:
                entries = []
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel:
                    for item in channel.findall("item"):
                        entries.append({
                            "title": item.findtext("title", ""),
                            "url": item.findtext("link", ""),
                            "description": item.findtext("description", ""),
                            "published": item.findtext("pubDate", ""),
                        })
                return entries, "requests"
        except Exception as e:
            print(f"  Requests error: {e}")
        return [], "failed"


def extract_prediction_from_rss(entry: dict) -> dict | None:
    """Extract prediction from RSS entry."""
    text = f"{entry['title']} {entry['description']}".lower()
    
    # Find symbol
    symbol = None
    for sym, pair in SYMBOL_MAP.items():
        if sym.lower() in text or pair.lower() in text:
            symbol = pair
            break
    
    if not symbol:
        return None
    
    # Look for direction keywords
    direction = None
    bullish_words = ["bullish", "pump", "rally", "surge", "breakout", "moon", "upward"]
    bearish_words = ["bearish", "dump", "crash", "drop", "fall", "downward", "decline"]
    
    if any(w in text for w in bullish_words):
        direction = "LONG"
    elif any(w in text for w in bearish_words):
        direction = "SHORT"
    
    if not direction:
        return None
    
    # Extract price targets
    price_pattern = re.compile(r'\$?([\d,]+\.?\d*)\s*[kK]?')
    prices = []
    for match in price_pattern.finditer(entry['title']):
        try:
            val = float(match.group(1).replace(",", ""))
            if "k" in entry['title'].lower():
                val *= 1000
            if val > 100:
                prices.append(val)
        except:
            pass
    
    target = prices[0] if prices else None
    
    return {
        "predictor_id": "coincodex:analysis",
        "platform": "coincodex",
        "display_name": "CoinCodex Analysis",
        "symbol": symbol,
        "direction": direction,
        "entry_price": None,
        "take_profit": target,
        "stop_loss": None,
        "sentiment_score": 0.5 if direction == "LONG" else -0.5,
        "source_url": entry["url"],
        "source_text": entry["title"][:500],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "is_known_analyst": 0,
        "analyst_category": "aggregator",
    }


async def scrape_coincodex_async() -> int:
    """Scrape CoinCodex using CrawlerEngine."""
    print("=" * 60)
    print("CoinCodex Scraper (with CrawlerEngine)")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    
    # Fetch RSS feed
    print("\nFetching CoinCodex RSS feed...")
    rss_entries, method = await fetch_coincodex_rss()
    print(f"  [OK] Got {len(rss_entries)} RSS entries via {method}")
    
    for entry in rss_entries[:20]:  # Process last 20
        try:
            pred = extract_prediction_from_rss(entry)
            if pred:
                existing = conn.execute(
                    "SELECT id FROM predictions WHERE source_url = ?",
                    (pred["source_url"],)
                ).fetchone()
                
                if not existing:
                    conn.execute("""
                        INSERT INTO predictions
                        (predictor_id, platform, symbol, direction, entry_price, take_profit,
                         stop_loss, sentiment_score, source_url, source_text, scraped_at,
                         status, is_known_analyst, analyst_category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                    """, (
                        pred["predictor_id"], pred["platform"], pred["symbol"],
                        pred["direction"], pred["entry_price"], pred["take_profit"],
                        pred["stop_loss"], pred["sentiment_score"], pred["source_url"],
                        pred["source_text"], pred["scraped_at"],
                        pred["is_known_analyst"], pred["analyst_category"]
                    ))
                    conn.commit()
                    total += 1
                    print(f"    + {pred['symbol']} {pred['direction']}")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('coincodex', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        len(rss_entries),
        total,
        None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"CoinCodex total: {total} predictions")
    print(f"{'=' * 60}")
    return total


def scrape_coincodex() -> int:
    """Synchronous wrapper."""
    return asyncio.run(scrape_coincodex_async())


if __name__ == "__main__":
    scrape_coincodex()

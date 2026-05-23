"""CoinMarketCap scraper - extracts trending coins and fear/greed data.

Uses advanced crawling with Crawl4AI/Scrapling for JavaScript-rendered data.
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
    print("Warning: crawler_engine not available, using requests fallback")

import requests

# CoinMarketCap URLs
CMC_FEAR_GREED = "https://coinmarketcap.com/charts/fear-and-greed-index/"
CMC_TRENDING = "https://coinmarketcap.com/trending-cryptocurrencies/"
CMC_GAINERS = "https://coinmarketcap.com/gainers-losers/"

SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOT": "DOTUSDT", "SUI": "SUIUSDT", "MATIC": "MATICUSDT",
}


def fetch_fear_greed_index() -> dict | None:
    """Fetch Fear & Greed Index value from CoinMarketCap."""
    try:
        if HAS_CRAWLER:
            engine = CrawlerEngine()
            html, method = asyncio.run(engine.fetch(CMC_FEAR_GREED, use_js=True))
        else:
            resp = requests.get(CMC_FEAR_GREED, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            html = resp.text if resp.status_code == 200 else ""
        
        if not html:
            return None
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for fear/greed value
        # CMC displays it in various formats, try multiple selectors
        selectors = [
            "[data-module-name='FearGreedIndex']",
            ".fear-greed-index",
            "[class*='fear']",
            "[class*='greed']",
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text()
                # Extract number from text like "Fear: 45" or "Greed Index: 75"
                match = re.search(r'(\d+)', text)
                if match:
                    value = int(match.group(1))
                    sentiment = "neutral"
                    if value <= 25:
                        sentiment = "extreme_fear"
                    elif value <= 45:
                        sentiment = "fear"
                    elif value <= 55:
                        sentiment = "neutral"
                    elif value <= 75:
                        sentiment = "greed"
                    else:
                        sentiment = "extreme_greed"
                    
                    return {
                        "value": value,
                        "sentiment": sentiment,
                        "source": "coinmarketcap_fgi"
                    }
        
        return None
        
    except Exception as e:
        print(f"  Fear/Greed fetch error: {e}")
        return None


def fetch_trending_coins() -> list[dict]:
    """Fetch trending coins from CoinMarketCap."""
    coins = []
    
    try:
        if HAS_CRAWLER:
            engine = CrawlerEngine()
            html, method = asyncio.run(engine.fetch(CMC_TRENDING, use_js=True))
        else:
            resp = requests.get(CMC_TRENDING, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            html = resp.text if resp.status_code == 200 else ""
        
        if not html:
            return coins
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract coin symbols from trending table
        # CMC uses various class names, try to find coin symbols
        rows = soup.select("table tbody tr")
        
        for row in rows[:20]:  # Top 20 trending
            try:
                # Look for symbol in various formats
                symbol_elem = row.select_one("td:nth-child(3) p") or \
                             row.select_one("[class*='symbol']") or \
                             row.select_one("span[class*='coin-symbol']")
                
                if symbol_elem:
                    symbol_text = symbol_elem.get_text(strip=True).upper()
                    if symbol_text in SYMBOL_MAP:
                        coins.append({
                            "symbol": SYMBOL_MAP[symbol_text],
                            "direction": "LONG",  # Trending = bullish signal
                            "confidence": 0.6,
                            "source_url": CMC_TRENDING,
                            "reason": "trending_on_cmc"
                        })
            except:
                continue
        
    except Exception as e:
        print(f"  Trending fetch error: {e}")
    
    return coins


def fetch_top_gainers() -> list[dict]:
    """Fetch top gainers from CoinMarketCap."""
    gainers = []
    
    try:
        if HAS_CRAWLER:
            engine = CrawlerEngine()
            html, method = asyncio.run(engine.fetch(CMC_GAINERS, use_js=True))
        else:
            resp = requests.get(CMC_GAINERS, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            html = resp.text if resp.status_code == 200 else ""
        
        if not html:
            return gainers
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Find gainers section
        rows = soup.select("[class*='gainers'] table tbody tr") or \
               soup.select("table tbody tr")
        
        for row in rows[:10]:  # Top 10 gainers
            try:
                symbol_elem = row.select_one("td:nth-child(3) p") or \
                             row.select_one("[class*='symbol']")
                
                if symbol_elem:
                    symbol_text = symbol_elem.get_text(strip=True).upper()
                    if symbol_text in SYMBOL_MAP:
                        gainers.append({
                            "symbol": SYMBOL_MAP[symbol_text],
                            "direction": "LONG",
                            "confidence": 0.7,
                            "source_url": CMC_GAINERS,
                            "reason": "top_gainer"
                        })
            except:
                continue
        
    except Exception as e:
        print(f"  Gainers fetch error: {e}")
    
    return gainers


def scrape_coinmarketcap() -> int:
    """Scrape CoinMarketCap for sentiment and trending data."""
    print("=" * 60)
    print("CoinMarketCap Scraper")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    
    # Fetch Fear & Greed Index
    print("\n[Fear & Greed Index]")
    fgi = fetch_fear_greed_index()
    if fgi:
        print(f"  Value: {fgi['value']} ({fgi['sentiment']})")
        
        # Create a market sentiment prediction
        direction = "LONG" if fgi["value"] < 30 else "SHORT" if fgi["value"] > 70 else None
        
        if direction:
            for symbol in ["BTCUSDT", "ETHUSDT"]:
                pred = {
                    "predictor_id": "cmc:fear_greed",
                    "platform": "coinmarketcap",
                    "display_name": "CMC Fear & Greed",
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": None,
                    "take_profit": None,
                    "stop_loss": None,
                    "sentiment_score": (fgi["value"] - 50) / 50,  # -1 to 1
                    "source_url": CMC_FEAR_GREED,
                    "source_text": f"Fear & Greed Index: {fgi['value']} ({fgi['sentiment']})",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "is_known_analyst": 0,
                    "analyst_category": "sentiment_indicator",
                }
                
                try:
                    existing = conn.execute(
                        "SELECT id FROM predictions WHERE source_url = ? AND scraped_at > datetime('now', '-1 day')",
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
                        print(f"    + {symbol} {direction} (based on Fear & Greed)")
                except Exception as e:
                    print(f"    DB error: {e}")
    else:
        print("  Could not fetch Fear & Greed Index")
    
    # Fetch trending coins
    print("\n[Trending Coins]")
    trending = fetch_trending_coins()
    print(f"  Found {len(trending)} trending coins")
    
    for coin in trending[:5]:  # Top 5
        try:
            pred = {
                "predictor_id": "cmc:trending",
                "platform": "coinmarketcap",
                "display_name": "CMC Trending",
                "symbol": coin["symbol"],
                "direction": coin["direction"],
                "entry_price": None,
                "take_profit": None,
                "stop_loss": None,
                "sentiment_score": coin["confidence"],
                "source_url": coin["source_url"],
                "source_text": f"Trending on CoinMarketCap: {coin['reason']}",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "is_known_analyst": 0,
                "analyst_category": "trending",
            }
            
            existing = conn.execute(
                "SELECT id FROM predictions WHERE source_url = ? AND symbol = ? AND scraped_at > datetime('now', '-1 day')",
                (pred["source_url"], pred["symbol"])
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
                print(f"    + {coin['symbol']} {coin['direction']}")
        except Exception as e:
            print(f"    DB error: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('coinmarketcap', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        len(trending),
        total,
        None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"CoinMarketCap: {total} predictions")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    scrape_coinmarketcap()

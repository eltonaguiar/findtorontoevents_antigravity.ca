"""Crypto Community Scraper - aggregates signals from various crypto communities.

Targets:
- Bitcointalk.org (forum)
- CryptoCompare (community)
- CoinGecko community
- Various Discord/Telegram public channels via widget sites
"""
import asyncio
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

try:
    from crawler_engine import CrawlerEngine, fetch_page
    HAS_CRAWLER = True
except ImportError:
    HAS_CRAWLER = False

import requests

# Community sources
COMMUNITY_SOURCES = {
    "bitcointalk": {
        "url": "https://bitcointalk.org/index.php?board=5.0",  # Bitcoin speculation
        "type": "forum",
    },
    "cryptocompare": {
        "url": "https://www.cryptocompare.com/coins/btc/analysis/",
        "type": "analysis",
    },
    "coingecko": {
        "url": "https://www.coingecko.com/en/coins/bitcoin/social",
        "type": "social",
    },
}

SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOT": "DOTUSDT", "SUI": "SUIUSDT", "MATIC": "MATICUSDT",
}

DIRECTION_RE = re.compile(r'\b(bullish|bearish|long|short|buy|sell|up|down)\b', re.I)
PRICE_RE = re.compile(r'\$?([\d,]+\.?\d*)\s*[kK]?', re.I)


class CommunityScraper:
    """Scraper for crypto community sites."""
    
    def __init__(self):
        self.engine = CrawlerEngine() if HAS_CRAWLER else None
        self.predictions = []
    
    async def scrape_bitcointalk(self) -> list[dict]:
        """Scrape BitcoinTalk speculation forum."""
        predictions = []
        url = COMMUNITY_SOURCES["bitcointalk"]["url"]
        
        try:
            if self.engine:
                html, method = await self.engine.fetch(url, use_js=False)
            else:
                resp = requests.get(url, timeout=20, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                })
                html = resp.text if resp.status_code == 200 else ""
            
            if not html:
                return predictions
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Find topic rows
            topics = soup.select("td.subject")
            
            for topic in topics[:20]:  # Top 20 topics
                try:
                    link = topic.select_one("a")
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    topic_url = link.get("href", "")
                    
                    # Check for directional keywords
                    text_lower = title.lower()
                    direction = None
                    
                    if any(w in text_lower for w in ["bull", "long", "buy", "up", "moon"]):
                        direction = "LONG"
                    elif any(w in text_lower for w in ["bear", "short", "sell", "down", "dump"]):
                        direction = "SHORT"
                    
                    if not direction:
                        continue
                    
                    # Extract price targets
                    prices = []
                    for match in PRICE_RE.finditer(title):
                        try:
                            val = float(match.group(1).replace(",", ""))
                            if "k" in title.lower() and val < 1000:
                                val *= 1000
                            if val > 1000:
                                prices.append(val)
                        except:
                            pass
                    
                    predictions.append({
                        "symbol": "BTCUSDT",  # Bitcointalk is BTC-focused
                        "direction": direction,
                        "take_profit": prices[0] if prices else None,
                        "source_url": topic_url if topic_url.startswith("http") else f"https://bitcointalk.org{topic_url}",
                        "source_text": title,
                        "predictor_id": "bitcointalk:community",
                        "platform": "bitcointalk",
                    })
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"  BitcoinTalk error: {e}")
        
        return predictions
    
    async def scrape_cryptocompare(self) -> list[dict]:
        """Scrape CryptoCompare analysis."""
        predictions = []
        
        symbols = ["btc", "eth", "sol"]
        
        for sym in symbols:
            try:
                url = f"https://www.cryptocompare.com/coins/{sym}/analysis/"
                
                if self.engine:
                    html, method = await self.engine.fetch(url, use_js=True)
                else:
                    resp = requests.get(url, timeout=20, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    })
                    html = resp.text if resp.status_code == 200 else ""
                
                if not html:
                    continue
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for analysis content
                analysis = soup.select_one("[class*='analysis']") or \
                          soup.select_one("[class*='price-prediction']")
                
                if analysis:
                    text = analysis.get_text()
                    text_lower = text.lower()
                    
                    direction = None
                    if any(w in text_lower for w in ["bull", "buy", "up"]):
                        direction = "LONG"
                    elif any(w in text_lower for w in ["bear", "sell", "down"]):
                        direction = "SHORT"
                    
                    if direction:
                        predictions.append({
                            "symbol": SYMBOL_MAP.get(sym.upper(), f"{sym.upper()}USDT"),
                            "direction": direction,
                            "source_url": url,
                            "source_text": text[:500],
                            "predictor_id": f"cryptocompare:{sym}",
                            "platform": "cryptocompare",
                        })
                
            except Exception as e:
                print(f"  CryptoCompare {sym} error: {e}")
        
        return predictions
    
    def aggregate_predictions(self, all_predictions: list[list[dict]]) -> list[dict]:
        """Aggregate and deduplicate predictions."""
        seen = set()
        aggregated = []
        
        for pred_list in all_predictions:
            for pred in pred_list:
                key = f"{pred['symbol']}_{pred['direction']}_{pred.get('take_profit', 'none')}"
                if key not in seen:
                    seen.add(key)
                    aggregated.append(pred)
        
        return aggregated


def scrape_crypto_communities() -> int:
    """Main entry point for community scraping."""
    print("=" * 60)
    print("Crypto Community Scraper")
    print("=" * 60)
    
    scraper = CommunityScraper()
    conn = get_db()
    total = 0
    
    # Scrape all sources
    print("\n[1/3] Scraping BitcoinTalk...")
    bitcointalk_preds = asyncio.run(scraper.scrape_bitcointalk())
    print(f"  Found {len(bitcointalk_preds)} predictions")
    
    print("\n[2/3] Scraping CryptoCompare...")
    cc_preds = asyncio.run(scraper.scrape_cryptocompare())
    print(f"  Found {len(cc_preds)} predictions")
    
    # Aggregate
    print("\n[3/3] Aggregating predictions...")
    all_preds = scraper.aggregate_predictions([bitcointalk_preds, cc_preds])
    print(f"  Total unique: {len(all_preds)}")
    
    # Store in database
    for pred in all_preds:
        try:
            existing = conn.execute(
                "SELECT id FROM predictions WHERE source_url = ? AND scraped_at > datetime('now', '-7 days')",
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
                    pred["direction"], pred.get("entry_price"), pred.get("take_profit"),
                    pred.get("stop_loss"), pred.get("sentiment_score"), pred["source_url"],
                    pred["source_text"], datetime.now(timezone.utc).isoformat(),
                    0, "community"
                ))
                conn.commit()
                total += 1
                print(f"  + {pred['symbol']} {pred['direction']} from {pred['platform']}")
        except Exception as e:
            print(f"  DB error: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('crypto_communities', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        len(all_preds),
        total,
        None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"Crypto Communities: {total} predictions")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    scrape_crypto_communities()

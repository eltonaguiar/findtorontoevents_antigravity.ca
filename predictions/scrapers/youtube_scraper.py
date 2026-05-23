"""YouTube scraper - extracts crypto predictions from video descriptions and comments.

Uses RSS feeds and advanced crawling for crypto YouTube channels.
Targets: Coin Bureau, Lark Davis, Benjamin Cowen, Altcoin Daily, etc.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

# Top crypto YouTube channels (via RSS feeds from rss.app or similar)
YOUTUBE_CHANNELS = {
    "CoinBureau": {
        "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw",
        "rss_feed": None,  # To be filled with rss.app feed
        "focus": "research",
    },
    "LarkDavis": {
        "channel_id": "UCl2bmC0Rp2ywQCf0ENd3MJw",
        "rss_feed": None,
        "focus": "daily_news",
    },
    "BenjaminCowen": {
        "channel_id": "UCRvqjQPSeaWn-uEx-w8XkGA",
        "rss_feed": None,
        "focus": "technical_analysis",
    },
    "AltcoinDaily": {
        "channel_id": "UCbLhGKVY-bJPcawebgtNfbw",
        "rss_feed": None,
        "focus": "altcoin_news",
    },
}

# YouTube RSS feed format (requires rss.app or similar service)
# https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}
YOUTUBE_RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOT": "DOTUSDT", "SUI": "SUIUSDT", "MATIC": "MATICUSDT",
}

DIRECTION_RE = re.compile(r'\b(bullish|bearish|long|short|buy|sell|accumulate|dip)\b', re.I)
PRICE_RE = re.compile(r'\$?([\d,]+\.?\d*)\s*[kK]?', re.I)
TIMEFRAME_RE = re.compile(r'\b(\d+)\s*(day|week|month|year)s?\b', re.I)


def fetch_youtube_rss(channel_id: str) -> list[dict]:
    """Fetch recent videos from YouTube channel via RSS."""
    entries = []
    
    try:
        url = YOUTUBE_RSS_TEMPLATE.format(channel_id)
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            
            # YouTube RSS uses Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
            root = ET.fromstring(resp.content)
            
            for entry in root.findall("atom:entry", ns):
                try:
                    title = entry.findtext("atom:title", "", ns)
                    video_id = entry.find("atom:id", ns).text.split(":")[-1]
                    link = f"https://www.youtube.com/watch?v={video_id}"
                    published = entry.findtext("atom:published", "", ns)
                    
                    # Get description from media:group
                    media_group = entry.find("media:group", ns)
                    description = ""
                    if media_group is not None:
                        desc_elem = media_group.find("media:description", ns)
                        if desc_elem is not None:
                            description = desc_elem.text or ""
                    
                    entries.append({
                        "title": title,
                        "url": link,
                        "video_id": video_id,
                        "published": published,
                        "description": description,
                    })
                except:
                    continue
                    
    except Exception as e:
        print(f"  YouTube RSS error: {e}")
    
    return entries


def extract_prediction_from_video(video: dict, channel_name: str) -> dict | None:
    """Extract prediction from YouTube video title and description."""
    title = video.get("title", "")
    description = video.get("description", "")
    full_text = f"{title} {description}".lower()
    
    # Find mentioned symbols
    symbol = None
    for sym, pair in SYMBOL_MAP.items():
        if sym.lower() in full_text or pair.lower() in full_text:
            symbol = pair
            break
    
    # Default symbols based on video content
    if not symbol:
        if "bitcoin" in full_text or "btc" in full_text:
            symbol = "BTCUSDT"
        elif "ethereum" in full_text or "eth" in full_text:
            symbol = "ETHUSDT"
        elif "solana" in full_text or "sol" in full_text:
            symbol = "SOLUSDT"
    
    if not symbol:
        return None
    
    # Find direction
    direction = None
    if any(w in full_text for w in ["bullish", "long", "buy", "accumulate", "moon", "pump"]):
        direction = "LONG"
    elif any(w in full_text for w in ["bearish", "short", "sell", "dump", "crash"]):
        direction = "SHORT"
    
    if not direction:
        return None
    
    # Extract price targets
    prices = []
    for match in PRICE_RE.finditer(title + " " + description[:500]):
        try:
            val = float(match.group(1).replace(",", ""))
            if "k" in full_text and val < 1000:
                val *= 1000
            if val > 100:  # Reasonable crypto price
                prices.append(val)
        except:
            pass
    
    # Extract timeframe
    timeframe = None
    tf_match = TIMEFRAME_RE.search(title)
    if tf_match:
        timeframe = f"{tf_match.group(1)} {tf_match.group(2)}"
    
    return {
        "predictor_id": f"youtube:{channel_name}",
        "platform": "youtube",
        "display_name": f"{channel_name} (YouTube)",
        "symbol": symbol,
        "direction": direction,
        "entry_price": None,
        "take_profit": prices[0] if prices else None,
        "stop_loss": None,
        "sentiment_score": 0.6 if direction == "LONG" else -0.6,
        "source_url": video["url"],
        "source_text": f"{title}\n\n{description[:500]}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "is_known_analyst": 1,
        "analyst_category": "youtube",
        "timeframe": timeframe,
    }


def scrape_youtube_crypto() -> int:
    """Scrape YouTube crypto channels for predictions."""
    print("=" * 60)
    print("YouTube Crypto Scraper")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    
    for channel_name, channel_info in YOUTUBE_CHANNELS.items():
        print(f"\nScraping {channel_name}...")
        
        # Check if RSS feed is configured
        rss_feed = channel_info.get("rss_feed")
        if not rss_feed:
            print(f"  Skipped: No RSS feed configured")
            print(f"  (Set up via rss.app and add to YOUTUBE_CHANNELS)")
            continue
        
        try:
            # Fetch via RSS
            videos = fetch_youtube_rss(channel_info["channel_id"])
            print(f"  Found {len(videos)} recent videos")
            
            extracted = 0
            for video in videos[:10]:  # Check last 10 videos
                try:
                    pred = extract_prediction_from_video(video, channel_name)
                    if pred:
                        # Check for duplicates
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
                            extracted += 1
                            print(f"    + {pred['symbol']} {pred['direction']}")
                            
                except Exception as e:
                    print(f"    Error: {e}")
            
            print(f"  Extracted {extracted} predictions")
            
        except Exception as e:
            print(f"  Error scraping {channel_name}: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('youtube', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        0,
        total,
        None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"YouTube total: {total} predictions")
    print(f"{'=' * 60}")
    return total


def setup_youtube_rss_instructions():
    """Print instructions for setting up YouTube RSS feeds."""
    print("""
=== YouTube RSS Setup Instructions ===

To scrape YouTube channels, you need to set up RSS feeds:

1. Go to https://rss.app
2. Create a new RSS feed
3. Enter YouTube channel URL (e.g., https://www.youtube.com/@CoinBureau)
4. Copy the generated RSS feed URL
5. Update YOUTUBE_CHANNELS in youtube_scraper.py:

   YOUTUBE_CHANNELS = {
       "CoinBureau": {
           "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw",
           "rss_feed": "https://rss.app/feeds/YOUR_FEED_ID.xml",
           "focus": "research",
       },
       ...
   }

Channels to add:
- Coin Bureau (@CoinBureau)
- Lark Davis (@TheCryptoLark)
- Benjamin Cowen (@IntoTheCryptoverse)
- Altcoin Daily (@AltcoinDaily)
- BitBoy Crypto (@BitBoyCrypto)

Note: YouTube's native RSS feeds (https://www.youtube.com/feeds/videos.xml?channel_id=...)
may be rate-limited or blocked. rss.app provides a more reliable alternative.
""")


if __name__ == "__main__":
    # Check if we have any RSS feeds configured
    has_feeds = any(ch.get("rss_feed") for ch in YOUTUBE_CHANNELS.values())
    
    if not has_feeds:
        setup_youtube_rss_instructions()
    else:
        scrape_youtube_crypto()

"""4chan /biz/ scraper - extracts crypto predictions from business & finance board.

Uses 4chan's public API to fetch threads from /biz/.
Filters for crypto-related discussions with price targets.
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

# 4chan API
FOURCHAN_API = "https://a.4cdn.org"
BIZ_BOARD = "biz"

# Crypto symbols to track
SYMBOLS = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "SHIB": "SHIBUSDT",
    "LINK": "LINKUSDT", "SUI": "SUIUSDT", "DOT": "DOTUSDT",
    "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "XRP": "XRPUSDT",
    "MATIC": "MATICUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT",
    "PEPE": "PEPEUSDT", "FLOKI": "FLOKIUSDT", "BONK": "BONKUSDT",
}

# Regex patterns
DIRECTION_RE = re.compile(r'\b(long|short|buy|sell|bullish|bearish|pump|dump|moon|rug)\b', re.I)
PRICE_RE = re.compile(r'\$?([\d,]+\.?\d*)\s*[kK]?', re.I)
ENTRY_RE = re.compile(r'(?:entry|buy)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp|target|take profit)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop loss)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)


def fetch_biz_catalog() -> list[dict]:
    """Fetch the current catalog of /biz/ threads."""
    try:
        url = f"{FOURCHAN_API}/{BIZ_BOARD}/catalog.json"
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (PredictionTracker/1.0)"
        })
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  4chan API error: {e}")
    return []


def fetch_thread_posts(thread_id: int) -> list[dict]:
    """Fetch all posts from a specific thread."""
    try:
        url = f"{FOURCHAN_API}/{BIZ_BOARD}/thread/{thread_id}.json"
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (PredictionTracker/1.0)"
        })
        if resp.status_code == 200:
            data = resp.json()
            return data.get("posts", [])
    except Exception as e:
        print(f"  Thread fetch error: {e}")
    return []


def clean_4chan_text(text: str) -> str:
    """Clean 4chan post text (remove HTML, format)."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove quote links
    text = re.sub(r'>>\d+', '', text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_prediction_from_post(post: dict, thread_id: int) -> dict | None:
    """Extract a prediction from a 4chan post."""
    raw_text = post.get("com", "")
    if not raw_text:
        return None
    
    text = clean_4chan_text(raw_text).lower()
    if len(text) < 30:
        return None
    
    # Find mentioned symbols
    mentioned = [(t, p) for t, p in SYMBOLS.items() if re.search(rf'\b{t}\b', text, re.I)]
    if not mentioned:
        return None
    
    # Find direction
    direction = None
    if any(w in text for w in ["long", "buy", "bullish", "pump", "moon", "accumulate"]):
        direction = "LONG"
    elif any(w in text for w in ["short", "sell", "bearish", "dump", "crash", "rug"]):
        direction = "SHORT"
    
    if not direction:
        return None
    
    # Extract price levels
    entry_m = ENTRY_RE.search(text)
    tp_m = TP_RE.search(text)
    sl_m = SL_RE.search(text)
    
    entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
    tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
    sl = float(sl_m.group(1).replace(",", "")) if sl_m else None
    
    # If no structured prices, try to extract any dollar amounts
    if not (entry or tp or sl):
        prices = []
        for m in PRICE_RE.finditer(text):
            try:
                val = float(m.group(1).replace(",", ""))
                if "k" in text:
                    val *= 1000
                if val > 100:
                    prices.append(val)
            except:
                pass
        if prices:
            tp = prices[0]
    
    # Need at least one price level
    if not (entry or tp or sl):
        return None
    
    post_id = post.get("no", 0)
    symbol = mentioned[0][1]  # Use first mentioned symbol
    
    return {
        "predictor_id": f"4chan:anon_{post_id}",
        "platform": "4chan",
        "display_name": f"/biz/ anon",
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "sentiment_score": 0.6 if direction == "LONG" else -0.6,
        "source_url": f"https://boards.4channel.org/biz/thread/{thread_id}#p{post_id}",
        "source_text": clean_4chan_text(raw_text)[:500],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "is_known_analyst": 0,
        "analyst_category": "4chan_biz",
    }


def scrape_4chan_biz() -> int:
    """Scrape 4chan /biz/ for crypto predictions."""
    print("=" * 60)
    print("4chan /biz/ Scraper")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    errors = []
    
    # Fetch catalog
    print("\nFetching /biz/ catalog...")
    catalog = fetch_biz_catalog()
    if not catalog:
        print("  Failed to fetch catalog")
        return 0
    
    print(f"  Got {len(catalog)} pages")
    
    # Process first 3 pages
    threads_processed = 0
    for page in catalog[:3]:
        for thread in page.get("threads", [])[:10]:  # Top 10 threads per page
            thread_id = thread.get("no")
            if not thread_id:
                continue
            
            # Check thread subject for crypto keywords
            subject = thread.get("sub", "").lower()
            com = thread.get("com", "").lower()
            thread_text = f"{subject} {com}"
            
            # Skip if no crypto symbols mentioned
            if not any(sym.lower() in thread_text for sym in SYMBOLS.keys()):
                continue
            
            print(f"  Processing thread {thread_id}...")
            
            # Fetch thread posts
            posts = fetch_thread_posts(thread_id)
            if not posts:
                continue
            
            extracted = 0
            for post in posts:
                try:
                    pred = extract_prediction_from_post(post, thread_id)
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
                    errors.append(str(e))
            
            print(f"    Extracted {extracted} predictions")
            threads_processed += 1
            
            # Rate limit
            time.sleep(1)
    
    print(f"\n  Processed {threads_processed} threads")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('4chan', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        threads_processed,
        total,
        "; ".join(errors[:5]) if errors else None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"4chan /biz/ total: {total} predictions")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    scrape_4chan_biz()

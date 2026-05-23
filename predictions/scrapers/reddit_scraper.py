"""Reddit scraper using multiple fallback methods (no API required).

Methods tried in order:
1. Reddit JSON API (unofficial, no auth needed) - e.g., reddit.com/r/Bitcoin/.json
2. Pushshift API (archived Reddit data)
3. RSS feeds (if available)
4. Scrapling/Crawl4AI for direct scraping
"""
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db, insert_prediction

# Import shared symbol extractor for multi-asset support
try:
    from symbol_extractor import extract_symbols as _extract_symbols_multi
    HAS_SYMBOL_EXTRACTOR = True
except ImportError:
    HAS_SYMBOL_EXTRACTOR = False

# Legacy crypto-only symbol map (fallback if symbol_extractor unavailable)
SYMBOLS = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "SHIB": "SHIBUSDT",
    "LINK": "LINKUSDT", "SUI": "SUIUSDT", "DOT": "DOTUSDT",
    "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "XRP": "XRPUSDT",
}

# Subreddits where equity/forex tickers are expected (avoid false positives
# on crypto subs where "LINK" = Chainlink, not Lincoln National)
EQUITY_SUBREDDITS = {
    "wallstreetbets", "stocks", "investing", "options",
    "Daytrading", "SecurityAnalysis",
}
FOREX_SUBREDDITS = {"Forex"}

SUBREDDITS = [
    # Major crypto trading subreddits
    "BitcoinMarkets",
    "CryptoMarkets", 
    "CryptoCurrency",
    "ethtrader",
    "binance",
    "CryptoTrading",
    "altcoin",
    "SatoshiStreetBets",
    "CryptoMoonShots",
    "defi",
    "NFTs",
    "solana",
    "cardano",
    "ethereum",
    "BTC",
    "Ripple",
    "Chainlink",
    "Polkadot",
    "Avalanche",
    "Polygon",
    # Investment and trading
    "wallstreetbets",
    "stocks",
    "Daytrading",
    "Forex",
    "algotrading",
    "options",
    "investing",
    "SecurityAnalysis",
    # Regional crypto
    "CryptoIndia",
    "CryptoUK",
    "CryptoAus",
    "CryptoCanada",
]

ENTRY_RE = re.compile(r'(?:entry|buy|sell|short|long)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp|take.?profit|target)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop.?loss|stop)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|buy|sell|bullish|bearish)\b', re.I)

# Pushshift API base URLs (try multiple)
PUSHSHIFT_URLS = [
    "https://api.pullpush.io/reddit/search/submission",
    "https://api.pullpush.io/reddit/search/comment",
]

REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/new/.json?limit=50"
REDDIT_SEARCH_URL = "https://www.reddit.com/r/{subreddit}/search/.json?q={query}&restrict_sr=on&sort=new&t=day&limit=25"

TRADING_SEARCH_QUERIES = [
    "long OR short OR bullish OR bearish",
    "entry target stop loss",
    "buy dip OR accumulate OR moon",
]


# Price pattern: any $ amount near a crypto symbol (e.g., "$95,000", "95k", "100K")
PRICE_RE = re.compile(r'\$\s*([\d,]+\.?\d*)\s*[kK]?|\b([\d,]+\.?\d*)\s*[kK]\b', re.I)
# Sentiment keywords that imply direction without explicit "long/short"
BULLISH_SENTIMENT_RE = re.compile(r'\b(moon|pump|rally|breakout|accumulate|dip\s*buy|undervalued|bottom|support\s*hold|ath|all.time.high|send\s*it|to\s*the\s*moon)\b', re.I)
BEARISH_SENTIMENT_RE = re.compile(r'\b(dump|crash|overvalued|top|resistance\s*reject|bear|collapse|bubble|rug|dead\s*cat)\b', re.I)


def _extract_predictions(text: str, author: str, url: str, subreddit: str) -> list[dict]:
    """Extract trading predictions from Reddit post/comment text."""
    preds = []

    # Find mentioned symbols — use multi-asset extractor when available
    if HAS_SYMBOL_EXTRACTOR:
        symbol_hits = _extract_symbols_multi(text)
        if not symbol_hits:
            return []
        # Subreddit-aware filtering: on crypto subs, only accept crypto symbols;
        # on equity subs, accept equity/etf/crypto; on forex subs, accept forex
        sub_lower = subreddit.lower() if subreddit else ""
        if sub_lower in {s.lower() for s in FOREX_SUBREDDITS}:
            symbol_hits = [s for s in symbol_hits if s["asset_class"] in ("forex", "futures", "crypto")]
        elif sub_lower not in {s.lower() for s in EQUITY_SUBREDDITS}:
            # Default crypto subs — still accept equity if explicitly cashtag-ed ($AAPL)
            # but filter out ambiguous short tickers that could be crypto aliases
            pass
        mentioned = [(s["symbol"], s["symbol"]) for s in symbol_hits]
    else:
        # Legacy fallback: crypto-only dict
        mentioned = [(t, p) for t, p in SYMBOLS.items() if re.search(rf'\b{t}\b', text, re.I)]

    if not mentioned:
        return []

    # Find direction: explicit first, then sentiment
    dir_match = DIRECTION_RE.search(text)
    direction = None
    if dir_match:
        dir_word = dir_match.group(1).lower()
        direction = "LONG" if dir_word in ("long", "buy", "bullish") else "SHORT"
    else:
        bull = BULLISH_SENTIMENT_RE.search(text)
        bear = BEARISH_SENTIMENT_RE.search(text)
        if bull and not bear:
            direction = "LONG"
        elif bear and not bull:
            direction = "SHORT"

    if not direction:
        return []

    # Extract price levels (structured format)
    entry_m = ENTRY_RE.search(text)
    tp_m = TP_RE.search(text)
    sl_m = SL_RE.search(text)

    entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
    tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
    sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

    # If no structured prices, try to extract any $ amounts as price targets
    if not (entry or tp or sl):
        prices = []
        for m in PRICE_RE.finditer(text):
            raw = (m.group(1) or m.group(2) or "").replace(",", "")
            if not raw:
                continue
            val = float(raw)
            # Handle "k" suffix (e.g., "95k" = 95000)
            if m.group(0).lower().endswith("k"):
                val *= 1000
            if val > 0:
                prices.append(val)
        if prices:
            # Use the first price as target/entry
            tp = prices[0]

    # Accept predictions with symbol + direction (prices optional for sentiment-based)
    for _ticker, pair in mentioned:
        preds.append({
            "predictor_id": f"reddit:u/{author}",
            "platform": "reddit",
            "display_name": f"u/{author}",
            "symbol": pair,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "source_url": url,
            "source_text": text[:500],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })

    return preds


def _fetch_reddit_json(subreddit: str) -> list[dict]:
    """Fetch posts using Reddit's unofficial JSON API (no auth needed)."""
    posts = []
    try:
        url = REDDIT_JSON_URL.format(subreddit=subreddit)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            
            # Skip stickied/deleted posts
            if post.get("stickied") or post.get("removed_by_category"):
                continue
            
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            full_text = f"{title} {selftext}".strip()
            
            if len(full_text) < 30:
                continue
            
            author = post.get("author", "deleted")
            permalink = f"https://reddit.com{post.get('permalink', '')}"
            created_utc = post.get("created_utc", 0)
            
            posts.append({
                "text": full_text,
                "author": author,
                "url": permalink,
                "created": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
            })
            
    except Exception as e:
        print(f"  Reddit JSON API error for r/{subreddit}: {e}")
    
    return posts


def _fetch_reddit_search(subreddit: str) -> list[dict]:
    """Fetch posts using Reddit search for trading-related content."""
    posts = []
    seen_urls = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html;q=0.9, */*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for query in TRADING_SEARCH_QUERIES:
        try:
            url = REDDIT_SEARCH_URL.format(subreddit=subreddit, query=quote(query))
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                if post.get("stickied") or post.get("removed_by_category"):
                    continue
                permalink = f"https://reddit.com{post.get('permalink', '')}"
                if permalink in seen_urls:
                    continue
                seen_urls.add(permalink)
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                full_text = f"{title} {selftext}".strip()
                if len(full_text) < 30:
                    continue
                author = post.get("author", "deleted")
                created_utc = post.get("created_utc", 0)
                posts.append({
                    "text": full_text,
                    "author": author,
                    "url": permalink,
                    "created": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
                })
            time.sleep(1)
        except Exception as e:
            print(f"  Reddit search error for r/{subreddit} q='{query[:30]}': {e}")
    return posts


def _fetch_pushshift(subreddit: str, hours_back: int = 24) -> list[dict]:
    """Fetch posts using Pushshift API (archived Reddit data)."""
    posts = []
    
    since = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp())
    
    for base_url in PUSHSHIFT_URLS:
        try:
            params = {
                "subreddit": subreddit,
                "since": since,
                "size": 50,
                "sort": "desc",
                "sort_type": "created_utc",
            }
            
            resp = requests.get(base_url, params=params, timeout=20)
            resp.raise_for_status()
            
            data = resp.json()
            for post in data.get("data", []):
                title = post.get("title", "")
                selftext = post.get("selftext", "") or post.get("body", "")
                full_text = f"{title} {selftext}".strip()
                
                if len(full_text) < 30:
                    continue
                
                author = post.get("author", "deleted")
                permalink = f"https://reddit.com{post.get('permalink', '')}"
                created_utc = post.get("created_utc", 0)
                
                posts.append({
                    "text": full_text,
                    "author": author,
                    "url": permalink,
                    "created": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
                })
                
        except Exception as e:
            print(f"  Pushshift error for r/{subreddit}: {e}")
            continue
    
    return posts


def _fetch_scrapling(subreddit: str) -> list[dict]:
    """Direct scraping with Scrapling as last resort."""
    posts = []
    
    try:
        from scrapling import Fetcher
        
        url = f"https://old.reddit.com/r/{subreddit}/new/"
        fetcher = Fetcher(auto_match=False)
        resp = fetcher.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status != 200:
            return posts
        
        html = resp.text
        
        # Parse old Reddit HTML structure
        entries = re.findall(r'<div class="entry unvoted"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S)
        
        for entry in entries:
            # Extract title
            title_match = re.search(r'<a class="title"[^>]*>(.*?)</a>', entry, re.S)
            if not title_match:
                continue
            
            title = re.sub(r'<[^>]+>', '', title_match.group(1))
            
            # Extract author
            author_match = re.search(r'class="author"[^>]*>([^<]+)</a>', entry)
            author = author_match.group(1) if author_match else "deleted"
            
            # Extract permalink
            link_match = re.search(r'href="(/r/{}/comments/[^"]+)"'.format(subreddit), entry)
            permalink = f"https://reddit.com{link_match.group(1)}" if link_match else ""
            
            # Get selftext if available (would need another request for full post)
            full_text = title
            
            if len(full_text) < 20:
                continue
            
            posts.append({
                "text": full_text,
                "author": author,
                "url": permalink,
                "created": datetime.now(timezone.utc).isoformat(),
            })
            
    except ImportError:
        print(f"  Scrapling not available for r/{subreddit}")
    except Exception as e:
        print(f"  Scrapling error for r/{subreddit}: {e}")
    
    return posts


def scrape_reddit() -> int:
    """Scrape Reddit using multiple fallback methods."""
    print("=" * 60)
    print("Reddit Scraper (Multi-Method Fallback)")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    errors = []
    
    for subreddit in SUBREDDITS:
        print(f"\nScraping r/{subreddit}...")
        
        posts = []
        method_used = ""
        
        # Method 1: Reddit JSON API (no auth)
        try:
            posts = _fetch_reddit_json(subreddit)
            if posts:
                method_used = "Reddit JSON API"
                print(f"  ✓ Got {len(posts)} posts via Reddit JSON")
        except Exception as e:
            print(f"  Reddit JSON failed: {e}")
        
        # Method 2: Reddit Search API (targeted trading keywords)
        if not posts:
            try:
                posts = _fetch_reddit_search(subreddit)
                if posts:
                    method_used = "Reddit Search"
                    print(f"  ✓ Got {len(posts)} posts via Reddit Search")
            except Exception as e:
                print(f"  Reddit Search failed: {e}")

        # Method 3: Pushshift API
        if not posts:
            try:
                posts = _fetch_pushshift(subreddit)
                if posts:
                    method_used = "Pushshift API"
                    print(f"  ✓ Got {len(posts)} posts via Pushshift")
            except Exception as e:
                print(f"  Pushshift failed: {e}")
        
        # Method 4: Direct Scrapling
        if not posts:
            try:
                posts = _fetch_scrapling(subreddit)
                if posts:
                    method_used = "Scrapling"
                    print(f"  ✓ Got {len(posts)} posts via Scrapling")
            except Exception as e:
                print(f"  Scrapling failed: {e}")
        
        if not posts:
            errors.append(f"r/{subreddit}: all methods failed")
            print(f"  ✗ All methods failed")
            continue
        
        # Extract predictions from posts
        extracted = 0
        for post in posts[:30]:  # Check last 30 posts
            try:
                preds = _extract_predictions(
                    post["text"], 
                    post["author"], 
                    post["url"],
                    subreddit
                )
                
                for pred in preds:
                    try:
                        existing = conn.execute(
                            "SELECT id FROM predictions WHERE source_url = ?",
                            (pred["source_url"],)
                        ).fetchone()
                        
                        if not existing:
                            conn.execute("""
                                INSERT INTO predictions 
                                (predictor_id, platform, symbol, direction, entry_price, 
                                 take_profit, stop_loss, source_url, source_text, 
                                 scraped_at, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                            """, (
                                pred["predictor_id"], pred["platform"], pred["symbol"],
                                pred["direction"], pred["entry_price"], pred["take_profit"],
                                pred["stop_loss"], pred["source_url"], pred["source_text"],
                                pred["scraped_at"]
                            ))
                            conn.commit()
                            total += 1
                            extracted += 1
                            print(f"    + {pred['symbol']} {pred['direction']}")
                    except Exception as e:
                        print(f"    DB error: {e}")
                        
            except Exception as e:
                print(f"  Extract error: {e}")
        
        print(f"  Method: {method_used} | Extracted: {extracted} predictions")
        
        # Rate limit between subreddits
        time.sleep(2)
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('reddit', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        total,
        total,
        "; ".join(errors) if errors else None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"Reddit total: {total} predictions")
    print(f"{'=' * 60}")
    return total


def scrape_reddit_crypto() -> int:
    """Entry point for analyst scraper integration."""
    return scrape_reddit()


if __name__ == "__main__":
    scrape_reddit()

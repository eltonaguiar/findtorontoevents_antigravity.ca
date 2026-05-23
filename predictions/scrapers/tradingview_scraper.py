"""TradingView Ideas scraper using CrawlerEngine for JS-rendered pages.

Uses unified crawler with automatic fallback:
1. Crawl4AI (JavaScript rendering)
2. Scrapling (anti-bot)
3. Playwright (browser automation)
4. Requests (static fallback)
"""
import asyncio
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db, insert_prediction

# Import shared symbol extractor for multi-asset text analysis
try:
    from symbol_extractor import extract_symbols as _extract_symbols_multi
    HAS_SYMBOL_EXTRACTOR = True
except ImportError:
    HAS_SYMBOL_EXTRACTOR = False

# Import crawler engine
try:
    from crawler_engine import CrawlerEngine
    HAS_CRAWLER = True
except ImportError:
    HAS_CRAWLER = False
    print("Warning: crawler_engine not available, using basic requests")

TV_SYMBOLS = [
    # Crypto
    ("BTCUSD", "BTCUSDT"),
    ("ETHUSD", "ETHUSDT"),
    ("SOLUSD", "SOLUSDT"),
    ("BNBUSD", "BNBUSDT"),
    ("DOGEUSD", "DOGEUSDT"),
    ("LINKUSD", "LINKUSDT"),
    ("AVAXUSD", "AVAXUSDT"),
    ("XRPUSD", "XRPUSDT"),
    ("ADAUSD", "ADAUSDT"),
    ("DOTUSD", "DOTUSDT"),
    ("SUIUSD", "SUIUSDT"),
    # Major Equities/ETFs (TradingView uses NASDAQ:AAPL style, ideas page uses plain)
    ("SPY", "SPY"),
    ("QQQ", "QQQ"),
    ("AAPL", "AAPL"),
    ("NVDA", "NVDA"),
    ("TSLA", "TSLA"),
    ("MSFT", "MSFT"),
    ("AMD", "AMD"),
    ("META", "META"),
    # Forex (TradingView uses FX:EURUSD)
    ("EURUSD", "EURUSD=X"),
    ("GBPUSD", "GBPUSD=X"),
    ("USDJPY", "USDJPY=X"),
    # Futures (TradingView uses CME_MINI:ES1!)
    ("ES1!", "ES=F"),
    ("NQ1!", "NQ=F"),
    ("GC1!", "GC=F"),
]

# Regex patterns for extracting trade ideas
ENTRY_RE = re.compile(r'(?:entry|buy|sell|open|position)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp\d?|target|take\.?profit)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|buy|sell|bullish|bearish)\b', re.I)

DELAY = 2.0  # Rate limit between requests


async def fetch_tradingview_page(tv_sym: str) -> tuple[str | None, str]:
    """Fetch TradingView ideas page using CrawlerEngine."""
    url = f"https://www.tradingview.com/symbols/{tv_sym}/ideas/"
    
    if HAS_CRAWLER:
        engine = CrawlerEngine(delay=DELAY, timeout=30)
        html, method = await engine.fetch(url, use_js=True)
        return html, method
    else:
        # Fallback to basic requests
        import requests
        try:
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }, timeout=20)
            if resp.status_code == 200:
                return resp.text, "requests"
        except Exception as e:
            print(f"  Requests error: {e}")
        return None, "failed"


def _parse_ideas(html: str, tv_sym: str, binance_sym: str) -> list[dict]:
    """Parse TradingView ideas from rendered HTML."""
    ideas = []
    
    if not html or len(html) < 1000:
        return ideas
    
    # Try to find idea cards in rendered HTML
    # Multiple patterns for different TradingView layouts
    
    # Pattern 1: Data widget idea articles (new layout)
    idea_blocks = re.findall(
        r'<article[^>]*class="[^"]*tv-widget-idea[^"]*"[^>]*>(.*?)</article>',
        html, re.S
    )
    
    # Pattern 2: Legacy widget layout
    if not idea_blocks:
        idea_blocks = re.findall(
            r'<div[^>]*class="[^"]*tv-widget-idea__description[^"]*"[^>]*>(.*?)</div>',
            html, re.S
        )
    
    # Pattern 3: Generic content blocks with author info
    if not idea_blocks:
        idea_blocks = re.findall(
            r'<div[^>]*data-widget-name="idea"[^>]*>(.*?)</div>(?=</div>\s*</div>)',
            html, re.S
        )
    
    # Pattern 4: Any div with idea-related classes
    if not idea_blocks:
        idea_blocks = re.split(
            r'(?=<div[^>]*class="[^"]*(?:tv-widget-idea|idea-card|tv-idea)[^"]*")',
            html
        )
        idea_blocks = idea_blocks[1:]  # Skip first split
    
    for block in idea_blocks:
        if len(block) < 200:
            continue
        
        # Strip HTML tags for text analysis
        text = re.sub(r'<[^>]+>', ' ', block)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) < 50:
            continue
        
        # Extract author
        author_match = re.search(r'by\s+(\w+)', text, re.I) or \
                       re.search(r'@(\w+)', text) or \
                       re.search(r'class="[^"]*author[^"]*"[^>]*>(\w+)', block, re.I)
        author = author_match.group(1) if author_match else "traders"
        
        # Extract direction
        dir_match = DIRECTION_RE.search(text)
        if not dir_match:
            continue
        
        dir_word = dir_match.group(1).lower()
        direction = "LONG" if dir_word in ("long", "buy", "bullish") else "SHORT"
        
        # Extract price levels
        entry_m = ENTRY_RE.search(text)
        tp_m = TP_RE.search(text)
        sl_m = SL_RE.search(text)
        
        entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
        tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
        sl = float(sl_m.group(1).replace(",", "")) if sl_m else None
        
        # Skip if no actionable levels
        if not (entry or tp or sl):
            continue
        
        # Extract idea URL
        url_match = re.search(r'href="(/chart/[^"]+)"', block) or \
                    re.search(r'href="(/u/[^"]+/ideas/[^"]+)"', block)
        idea_url = f"https://www.tradingview.com{url_match.group(1)}" if url_match else \
                   f"https://www.tradingview.com/symbols/{tv_sym}/ideas/"
        
        ideas.append({
            "predictor_id": f"tv:{author}",
            "platform": "tradingview",
            "display_name": author,
            "symbol": binance_sym,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "source_url": idea_url,
            "source_text": text[:500],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    
    return ideas


async def scrape_tradingview_async() -> int:
    """Async version of TradingView scraper using CrawlerEngine."""
    print("=" * 60)
    print("TradingView Scraper (with CrawlerEngine)")
    print("=" * 60)
    
    conn = get_db()
    total = 0
    errors = []
    
    for tv_sym, binance_sym in TV_SYMBOLS:
        print(f"\nScraping {tv_sym}...")
        
        try:
            html, method_used = await fetch_tradingview_page(tv_sym)
            
            if not html:
                errors.append(f"{tv_sym}: all fetch methods failed")
                print(f"  [X] All methods failed")
                continue
            
            print(f"  [OK] Got page via {method_used}")
            
            # Parse ideas
            ideas = _parse_ideas(html, tv_sym, binance_sym)
            
            for idea in ideas:
                try:
                    insert_prediction(conn, idea)
                    total += 1
                    print(f"    + {idea['direction']} {idea['symbol']} by {idea['display_name']}")
                except Exception as e:
                    print(f"    DB error: {e}")
            
            print(f"  Found: {len(ideas)} ideas")
            
        except Exception as e:
            errors.append(f"{tv_sym}: {e}")
            print(f"  Error: {e}")
        
        await asyncio.sleep(DELAY)
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('tradingview', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        total,
        total,
        "; ".join(errors) if errors else None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"TradingView total: {total} predictions")
    print(f"{'=' * 60}")
    return total


def scrape_tradingview() -> int:
    """Synchronous wrapper for TradingView scraper."""
    return asyncio.run(scrape_tradingview_async())


if __name__ == "__main__":
    scrape_tradingview()

"""
Web KOL Scraper -- scrapes KOL blogs and analysis sites using CrawlerEngine.

Uses the existing CrawlerEngine (Crawl4AI -> Scrapling -> Playwright -> requests/BS4
fallback chain) to fetch blog posts, substacks, and analysis pages from known
crypto Key Opinion Leaders.
"""

import os
import re
import sys
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Import CrawlerEngine with fallback
# ---------------------------------------------------------------------------
try:
    from crawler_engine import CrawlerEngine
    HAS_CRAWLER_ENGINE = True
except ImportError:
    HAS_CRAWLER_ENGINE = False

# ---------------------------------------------------------------------------
# Import KOL registry and symbol extractor
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
from kol_registry import get_active_kols
from symbol_extractor import extract_symbols

# ---------------------------------------------------------------------------
# Import DB helpers
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db, insert_prediction

# ---------------------------------------------------------------------------
# Fallback: simple requests + BeautifulSoup if CrawlerEngine unavailable
# ---------------------------------------------------------------------------
if not HAS_CRAWLER_ENGINE:
    import requests
    from bs4 import BeautifulSoup

    _FALLBACK_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    class _FallbackEngine:
        """Minimal stand-in when CrawlerEngine is not importable."""

        def __init__(self, delay: float = 1.0, timeout: int = 30):
            self.delay = delay
            self.timeout = timeout

        async def fetch(self, url: str, use_js: bool = False) -> tuple:
            try:
                resp = requests.get(
                    url, headers=_FALLBACK_HEADERS, timeout=self.timeout
                )
                if resp.status_code == 200:
                    return resp.text, "requests-fallback"
            except Exception as exc:
                print(f"  Fallback fetch failed for {url}: {exc}")
            return "", "failed"


# ---------------------------------------------------------------------------
# Default KOL blog/analysis URLs (used when registry lacks specific URLs)
# ---------------------------------------------------------------------------
DEFAULT_KOL_URLS = [
    # Arthur Hayes blog
    {"url": "https://cryptohayes.substack.com", "handle": "CryptoHayes", "use_js": False},
    # Willy Woo
    {"url": "https://woobull.com", "handle": "woonomic", "use_js": False},
]

# ---------------------------------------------------------------------------
# Regex patterns for price extraction
# ---------------------------------------------------------------------------
ENTRY_RE = re.compile(
    r"(?:entry|buy|sell|open|position)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
TP_RE = re.compile(
    r"(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
SL_RE = re.compile(
    r"(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
DIRECTION_RE = re.compile(
    r"\b(long|short|buy|sell|bullish|bearish)\b", re.I
)

# ---------------------------------------------------------------------------
# Sentiment keyword lists
# ---------------------------------------------------------------------------
BULLISH_KEYWORDS = [
    "bullish", "long", "buy", "accumulate", "moon", "pump", "rally",
    "breakout", "upside", "higher", "support", "bottom", "reversal",
    "undervalued", "oversold", "opportunity",
]
BEARISH_KEYWORDS = [
    "bearish", "short", "sell", "dump", "crash", "downside", "lower",
    "resistance", "top", "overvalued", "overbought", "breakdown",
    "correction", "decline", "capitulation", "rug",
]

# Maximum URLs to scrape per run (time budget guard)
MAX_URLS_PER_RUN = 10

# Rate-limit delay between fetches (seconds)
FETCH_DELAY = 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace to plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_price(regex, text: str):
    """Extract first price match from text, return float or None."""
    m = regex.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except (ValueError, IndexError):
            pass
    return None


def _detect_direction(text: str) -> str:
    """Detect trade direction from text content."""
    match = DIRECTION_RE.search(text)
    if match:
        word = match.group(1).lower()
        if word in ("long", "buy", "bullish"):
            return "LONG"
        if word in ("short", "sell", "bearish"):
            return "SHORT"
    return "LONG"  # default


def _compute_sentiment(text: str) -> float:
    """Compute simple sentiment score from -1.0 to 1.0."""
    text_lower = text.lower()
    bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
    total = bull_count + bear_count
    if total == 0:
        return 0.0
    return round((bull_count - bear_count) / total, 3)


def _collect_urls_from_registry() -> list[dict]:
    """Build URL list from KOL registry entries that have web URLs."""
    urls = []
    seen_handles = set()
    for kol in get_active_kols():
        handle = kol["handle"]

        # Substack URL
        if kol.get("substack_url"):
            urls.append({
                "url": kol["substack_url"],
                "handle": handle,
                "use_js": False,
                "display_name": kol.get("display_name", handle),
                "category": kol.get("category", ""),
            })
            seen_handles.add(handle)

        # RSS URL (some KOLs have blog RSS feeds)
        if kol.get("rss_url"):
            urls.append({
                "url": kol["rss_url"],
                "handle": handle,
                "use_js": False,
                "display_name": kol.get("display_name", handle),
                "category": kol.get("category", ""),
            })
            seen_handles.add(handle)

    # Merge DEFAULT_KOL_URLS for handles not already covered
    for entry in DEFAULT_KOL_URLS:
        if entry["handle"] not in seen_handles:
            urls.append({
                **entry,
                "display_name": entry.get("display_name", entry["handle"]),
                "category": entry.get("category", ""),
            })
            seen_handles.add(entry["handle"])

    return urls


# ---------------------------------------------------------------------------
# Main async scraper
# ---------------------------------------------------------------------------

async def scrape_kol_web_pages() -> list[dict]:
    """Scrape KOL blogs/analysis sites and extract predictions.

    Returns list of prediction dicts ready for insert_prediction().
    """
    # Initialize engine
    if HAS_CRAWLER_ENGINE:
        engine = CrawlerEngine(delay=FETCH_DELAY)
    else:
        print("[web_kol_scraper] CrawlerEngine unavailable, using requests fallback")
        engine = _FallbackEngine(delay=FETCH_DELAY)

    # Collect URLs
    all_urls = _collect_urls_from_registry()
    # Limit to MAX_URLS_PER_RUN
    urls_to_scrape = all_urls[:MAX_URLS_PER_RUN]

    print(f"[web_kol_scraper] Scraping {len(urls_to_scrape)} KOL web pages "
          f"(of {len(all_urls)} total)")

    predictions = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for i, entry in enumerate(urls_to_scrape):
        url = entry["url"]
        handle = entry["handle"]
        use_js = entry.get("use_js", False)
        display_name = entry.get("display_name", handle)
        category = entry.get("category", "")

        print(f"\n[{i + 1}/{len(urls_to_scrape)}] Fetching {handle}: {url}")

        try:
            html, method = await engine.fetch(url, use_js=use_js)
        except Exception as exc:
            print(f"  ERROR fetching {url}: {exc}")
            html, method = "", "failed"

        if not html or method == "failed":
            print(f"  SKIP - no content retrieved")
            # Rate limit even on failure
            if i < len(urls_to_scrape) - 1:
                await asyncio.sleep(FETCH_DELAY)
            continue

        # Strip HTML to plain text
        text = _strip_html(html)
        if len(text) < 100:
            print(f"  SKIP - content too short ({len(text)} chars)")
            if i < len(urls_to_scrape) - 1:
                await asyncio.sleep(FETCH_DELAY)
            continue

        print(f"  Fetched {len(text)} chars via {method}")

        # Extract symbols
        symbols_found = extract_symbols(text)
        if not symbols_found:
            print(f"  No symbols detected in content")
            if i < len(urls_to_scrape) - 1:
                await asyncio.sleep(FETCH_DELAY)
            continue

        # Detect direction and prices from overall text
        direction = _detect_direction(text)
        entry_price = _parse_price(ENTRY_RE, text)
        take_profit = _parse_price(TP_RE, text)
        stop_loss = _parse_price(SL_RE, text)
        sentiment = _compute_sentiment(text)

        # Truncate source text for DB storage
        source_text_snippet = text[:500] if len(text) > 500 else text

        # Build a prediction for each detected symbol
        for sym_info in symbols_found:
            symbol = sym_info["symbol"]
            pred = {
                "predictor_id": f"web:{handle}",
                "platform": "web",
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "sentiment_score": sentiment,
                "source_url": url,
                "source_text": source_text_snippet,
                "scraped_at": now_iso,
                "is_known_analyst": 1,
                "analyst_category": category or None,
            }
            predictions.append(pred)

        print(f"  Extracted {len(symbols_found)} symbol(s): "
              f"{[s['symbol'] for s in symbols_found[:5]]}"
              f"{'...' if len(symbols_found) > 5 else ''}")

        # Rate limit between fetches
        if i < len(urls_to_scrape) - 1:
            await asyncio.sleep(FETCH_DELAY)

    return predictions


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    """Run the web KOL scraper and insert predictions into DB."""
    print("=" * 60)
    print("Web KOL Scraper - Starting")
    print("=" * 60)

    start = time.time()

    try:
        predictions = asyncio.run(scrape_kol_web_pages())
    except Exception as exc:
        print(f"FATAL: scraper crashed: {exc}")
        predictions = []

    if not predictions:
        print("\nNo predictions extracted.")
        elapsed = round(time.time() - start, 1)
        print(f"Completed in {elapsed}s")
        return

    # Insert into database
    conn = get_db()
    inserted = 0
    for pred in predictions:
        try:
            insert_prediction(conn, pred)
            inserted += 1
        except Exception as exc:
            print(f"  DB insert error for {pred['symbol']}: {exc}")
    conn.close()

    elapsed = round(time.time() - start, 1)
    print(f"\n{'=' * 60}")
    print(f"Web KOL Scraper - Complete")
    print(f"  Pages scraped: {MAX_URLS_PER_RUN}")
    print(f"  Predictions found: {len(predictions)}")
    print(f"  Inserted to DB: {inserted}")
    print(f"  Duration: {elapsed}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

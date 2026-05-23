"""
TheNewsAPI KOL Scraper
======================
Finds KOL mentions in news articles via TheNewsAPI.com and extracts
directional signals (price targets, sentiment, direction).

Free-tier friendly: caps total requests at 8 per run (100/day limit).
"""

import os
import re
import sys
import json
import ssl
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Import KOL registry and symbol extractor
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
from kol_registry import get_active_kols

sys.path.insert(0, str(Path(__file__).parent))
from symbol_extractor import extract_symbols

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db, insert_prediction

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
THENEWSAPI_KEY = os.getenv("THENEWSAPI", "")
BASE = "https://api.thenewsapi.com/v1/news/all"

# ---------------------------------------------------------------------------
# Sentiment word lists
# ---------------------------------------------------------------------------
POSITIVE_WORDS = [
    "surge", "rally", "bullish", "gain", "soar", "rise", "boom",
    "breakout", "record", "high", "buy", "long", "accumulate",
]
NEGATIVE_WORDS = [
    "crash", "plunge", "bearish", "fear", "drop", "fall", "collapse",
    "recession", "sell", "risk", "warning", "short", "dump",
]

# ---------------------------------------------------------------------------
# Regex patterns for price extraction & direction
# ---------------------------------------------------------------------------
ENTRY_RE = re.compile(
    r"(?:entry|buy|short|long|target\s*1?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
TP_RE = re.compile(
    r"(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
SL_RE = re.compile(
    r"(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)", re.I
)
DIRECTION_RE = re.compile(r"\b(long|short|bullish|bearish)\b", re.I)

# ---------------------------------------------------------------------------
# Topic queries for prediction-related news
# ---------------------------------------------------------------------------
TOPIC_QUERIES = [
    "bitcoin prediction",
    "cryptocurrency forecast",
    "stock market prediction",
    "forex outlook",
]


# ===================================================================
#  Fetch helpers
# ===================================================================

def _fetch_news(query: str, limit: int = 10) -> dict | None:
    """Fetch articles from TheNewsAPI /v1/news/all endpoint.

    Reuses the SSL context + urllib pattern from the other scrapers.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    params = urllib.parse.urlencode({
        "api_token": THENEWSAPI_KEY,
        "search": query,
        "language": "en",
        "limit": limit,
    })
    url = f"{BASE}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  API error for \"{query}\": {e}")
        return None


# ===================================================================
#  KOL query builder
# ===================================================================

def _build_kol_queries(kols: list[dict], batch_size: int = 5) -> list[str]:
    """Group KOL display names into batched queries for TheNewsAPI.

    TheNewsAPI uses +OR+ as the OR separator in search queries.
    Returns queries like: '"Arthur Hayes"+OR+"Raoul Pal"+OR+"Willy Woo"'
    """
    names = [k["display_name"] for k in kols if k.get("display_name")]
    queries: list[str] = []
    for i in range(0, len(names), batch_size):
        batch = names[i : i + batch_size]
        query = "+OR+".join(f'"{name}"' for name in batch)
        queries.append(query)
    return queries


# ===================================================================
#  Sentiment scoring
# ===================================================================

def _score_sentiment(title: str, description: str) -> float:
    """Score sentiment of title + description. Returns 0-1, 0.5 = neutral."""
    text = (title + " " + (description or "")).lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    total = pos + neg
    if total == 0:
        return 0.5
    # Map to 0-1 range: all positive = 1.0, all negative = 0.0
    return round(pos / total, 3)


# ===================================================================
#  Prediction extraction
# ===================================================================

def _build_kol_name_set(kols: list[dict]) -> set[str]:
    """Build a lowercase set of KOL display names for quick lookup."""
    return {k["display_name"].lower() for k in kols if k.get("display_name")}


def extract_predictions_from_articles(
    articles: list[dict],
    source_query: str,
    kol_names_lower: set[str] | None = None,
) -> list[dict]:
    """Extract directional predictions from a list of TheNewsAPI articles.

    Parameters
    ----------
    articles : list[dict]
        Article objects from the TheNewsAPI response.
    source_query : str
        The query that produced these articles (for logging).
    kol_names_lower : set[str] | None
        Lowercase KOL display names for is_known_analyst tagging.

    Returns a list of prediction dicts ready for insert_prediction().
    """
    if kol_names_lower is None:
        kol_names_lower = set()

    predictions: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for article in articles:
        title = article.get("title") or ""
        description = article.get("description") or ""
        snippet = article.get("snippet") or ""
        combined = f"{title} {description} {snippet}"

        if len(combined.strip()) < 10:
            continue

        # Extract symbols via shared extractor
        symbol_hits = extract_symbols(combined)
        if not symbol_hits:
            continue

        # Direction from regex
        dir_match = DIRECTION_RE.search(combined)
        sentiment = _score_sentiment(title, description)

        if dir_match:
            dir_word = dir_match.group(1).lower()
            direction = "LONG" if dir_word in ("long", "bullish") else "SHORT"
        elif sentiment > 0.6:
            direction = "LONG"
        elif sentiment < 0.4:
            direction = "SHORT"
        else:
            # No clear signal -- skip
            continue

        # Extract price levels
        entry_m = ENTRY_RE.search(combined)
        tp_m = TP_RE.search(combined)
        sl_m = SL_RE.search(combined)

        entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
        tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
        sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

        # Source info
        source_name = article.get("source", "unknown")
        article_url = article.get("url", "")

        # Check if any KOL name appears in the article text.
        # IMPORTANT: An article *about* a KOL is NOT the same as a first-person
        # call. Tag these as weak signals (is_known_analyst=0) so they do NOT
        # inflate consensus engine vote counts. Only the KOL's own platforms
        # (Twitter, YouTube, Substack, Telegram) produce is_known_analyst=1.
        combined_lower = combined.lower()
        mentions_kol = any(n in combined_lower for n in kol_names_lower)

        # Lower sentiment_score for news-inferred signals vs first-person calls
        adjusted_sentiment = sentiment * 0.7 if mentions_kol else sentiment * 0.5

        for sym_info in symbol_hits:
            symbol = sym_info.get("symbol", "")
            if not symbol:
                continue

            predictions.append({
                "predictor_id": f"thenewsapi:{source_name}",
                "platform": "thenewsapi",
                "display_name": source_name,
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "source_url": article_url,
                "source_text": combined[:500],
                "scraped_at": now_iso,
                "is_known_analyst": 0,  # News articles are NOT first-person KOL calls
                "analyst_category": "news_inferred",
                "sentiment_score": adjusted_sentiment,
            })

    return predictions


# ===================================================================
#  Main
# ===================================================================

def main():
    if not THENEWSAPI_KEY:
        print("[thenewsapi_kol_scraper] No THENEWSAPI key set - skipping.")
        return

    print("=" * 60)
    print("TheNewsAPI KOL Scraper")
    print("=" * 60)

    # Get active KOLs and build queries
    kols = get_active_kols()
    kol_queries = _build_kol_queries(kols, batch_size=5)
    kol_names_lower = _build_kol_name_set(kols)

    # Free tier: 100 requests/day -- cap total requests at 8
    MAX_REQUESTS = 8
    request_count = 0

    all_predictions: list[dict] = []

    # --- KOL name queries (max 4 to stay within budget) ---
    kol_query_limit = min(4, len(kol_queries))
    print(f"\nFetching KOL mention queries ({kol_query_limit} of {len(kol_queries)})...")

    for query in kol_queries[:kol_query_limit]:
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  Query: {query[:80]}...")
        data = _fetch_news(query, limit=10)
        request_count += 1

        if data and "data" in data:
            articles = data.get("data", [])
            print(f"    Got {len(articles)} articles")
            preds = extract_predictions_from_articles(articles, query, kol_names_lower)
            all_predictions.extend(preds)
            print(f"    Extracted {len(preds)} predictions")
        else:
            print("    Failed or rate limited")

        time.sleep(1)  # Rate limit between calls

    # --- Topic queries (max 4) ---
    topic_limit = min(4, len(TOPIC_QUERIES))
    print(f"\nFetching topic queries ({topic_limit})...")

    for query in TOPIC_QUERIES[:topic_limit]:
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  Query: {query[:80]}...")
        data = _fetch_news(query, limit=10)
        request_count += 1

        if data and "data" in data:
            articles = data.get("data", [])
            print(f"    Got {len(articles)} articles")
            preds = extract_predictions_from_articles(articles, query, kol_names_lower)
            all_predictions.extend(preds)
            print(f"    Extracted {len(preds)} predictions")
        else:
            print("    Failed or rate limited")

        time.sleep(1)  # Rate limit between calls

    # --- Insert into DB ---
    if all_predictions:
        print(f"\nInserting {len(all_predictions)} predictions into DB...")
        conn = get_db()
        inserted = 0
        for pred in all_predictions:
            try:
                pid = insert_prediction(conn, pred)
                if pid:
                    inserted += 1
            except Exception as e:
                print(f"  Insert error: {e}")

        # Log scrape
        try:
            conn.execute(
                """INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
                   VALUES ('thenewsapi', ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    request_count * 10,  # approximate articles fetched
                    inserted,
                    "",
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"  Scrape log error: {e}")

        print(f"  Inserted {inserted}/{len(all_predictions)} predictions")
    else:
        print("\nNo predictions extracted.")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"Summary: {request_count} API requests, {len(all_predictions)} predictions extracted")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

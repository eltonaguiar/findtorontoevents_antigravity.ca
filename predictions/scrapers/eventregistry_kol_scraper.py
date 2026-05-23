"""
Event Registry (newsapi.ai) KOL Scraper
========================================
Finds KOL mentions and prediction signals via Event Registry's advanced
news intelligence API. Leverages built-in sentiment and entity extraction.

Free-tier friendly: ~2000 tokens — caps at 6 requests per run.
"""

import os
import re
import sys
import json
import ssl
import time
import urllib.request
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
ER_API_KEY = os.getenv("NEWSAPIDOTAI", "")
ENDPOINT = "http://eventregistry.org/api/v1/article/getArticles"

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
    "bitcoin prediction OR crypto forecast",
    "stock market outlook OR equity forecast",
    "forex prediction OR currency forecast",
]


# ===================================================================
#  HTTP helper (POST with JSON body)
# ===================================================================

def _post_json(url: str, body: dict, timeout: int = 15) -> dict | None:
    """Send a POST request with JSON body and return parsed response."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  API error: {e}")
        return None


def _fetch_articles(query: str, count: int = 15) -> dict | None:
    """Fetch articles from Event Registry for the given keyword query."""
    body = {
        "action": "getArticles",
        "keyword": query,
        "keywordLoc": "title",
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": count,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "dataType": ["news"],
        "apiKey": ER_API_KEY,
    }
    return _post_json(ENDPOINT, body)


# ===================================================================
#  KOL query builder
# ===================================================================

def _build_kol_queries(kols: list[dict], batch_size: int = 3) -> list[str]:
    """Group KOL display names into batched OR queries.

    Returns queries like: '"Arthur Hayes" OR "Raoul Pal" OR "Willy Woo"'
    """
    names = [k["display_name"] for k in kols if k.get("display_name")]
    queries: list[str] = []
    for i in range(0, len(names), batch_size):
        batch = names[i : i + batch_size]
        query = " OR ".join(f'"{name}"' for name in batch)
        queries.append(query)
    return queries


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
    """Extract directional predictions from Event Registry articles.

    Uses the built-in sentiment field from Event Registry instead of
    local keyword-based scoring. Skips duplicate articles.

    Parameters
    ----------
    articles : list[dict]
        Article objects from the Event Registry response.
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
        # Skip duplicates flagged by Event Registry
        if article.get("isDuplicate", False):
            continue

        title = article.get("title") or ""
        body_text = article.get("body") or ""
        # Truncate body to first 1000 chars to avoid noise
        body_truncated = body_text[:1000]
        combined = f"{title} {body_truncated}"

        if len(combined.strip()) < 10:
            continue

        # Extract symbols via shared extractor
        symbol_hits = extract_symbols(combined)
        if not symbol_hits:
            continue

        # --- Sentiment from Event Registry (built-in, -1 to 1) ---
        er_sentiment = article.get("sentiment", 0)
        # Convert ER sentiment (-1 to 1) to our 0-1 scale
        sentiment_01 = (er_sentiment + 1) / 2  # -1->0, 0->0.5, 1->1

        # Direction from regex first, fall back to ER sentiment
        dir_match = DIRECTION_RE.search(combined)

        if dir_match:
            dir_word = dir_match.group(1).lower()
            direction = "LONG" if dir_word in ("long", "bullish") else "SHORT"
        elif er_sentiment > 0.15:
            direction = "LONG"
        elif er_sentiment < -0.15:
            direction = "SHORT"
        else:
            # Weak/neutral sentiment — still capture with neutral direction
            # based on keyword fallback
            text_lower = combined.lower()
            bull_kw = sum(1 for w in ("rally", "surge", "bullish", "gain", "rise", "breakout", "buy", "accumulate") if w in text_lower)
            bear_kw = sum(1 for w in ("crash", "drop", "bearish", "fear", "sell", "dump", "plunge", "collapse") if w in text_lower)
            if bull_kw > bear_kw:
                direction = "LONG"
            elif bear_kw > bull_kw:
                direction = "SHORT"
            else:
                continue  # Truly neutral — skip

        # Extract price levels
        entry_m = ENTRY_RE.search(combined)
        tp_m = TP_RE.search(combined)
        sl_m = SL_RE.search(combined)

        entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
        tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
        sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

        # Source info
        source_obj = article.get("source") or {}
        source_name = source_obj.get("name", "unknown") if isinstance(source_obj, dict) else "unknown"
        article_url = article.get("url", "")

        # Check if any KOL name appears in the article text
        combined_lower = combined.lower()
        mentions_kol = any(n in combined_lower for n in kol_names_lower)

        # Lower sentiment_score for news-inferred signals vs first-person calls
        # ER sentiment * 0.7 for KOL mentions, * 0.5 for generic news
        adjusted_sentiment = round(sentiment_01 * 0.7 if mentions_kol else sentiment_01 * 0.5, 3)

        for sym_info in symbol_hits:
            symbol = sym_info.get("symbol", "")
            if not symbol:
                continue

            predictions.append({
                "predictor_id": f"eventregistry:{source_name}",
                "platform": "eventregistry",
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
    if not ER_API_KEY:
        print("[eventregistry_kol_scraper] No NEWSAPIDOTAI key set - skipping.")
        return

    print("=" * 60)
    print("Event Registry (newsapi.ai) KOL Scraper")
    print("=" * 60)

    # Get active KOLs and build queries
    kols = get_active_kols()
    kol_queries = _build_kol_queries(kols, batch_size=3)
    kol_names_lower = _build_kol_name_set(kols)

    # Free tier: ~2000 tokens — cap total requests at 6
    MAX_REQUESTS = 6
    request_count = 0

    all_predictions: list[dict] = []

    # --- KOL name queries (max 3 to stay within token budget) ---
    kol_query_limit = min(3, len(kol_queries))
    print(f"\nFetching KOL mention queries ({kol_query_limit} of {len(kol_queries)})...")

    for query in kol_queries[:kol_query_limit]:
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  Query: {query[:80]}...")
        data = _fetch_articles(query, count=15)
        request_count += 1

        if data and "articles" in data:
            results = data["articles"].get("results", [])
            print(f"    Got {len(results)} articles")
            preds = extract_predictions_from_articles(results, query, kol_names_lower)
            all_predictions.extend(preds)
            print(f"    Extracted {len(preds)} predictions")
        else:
            print("    Failed or rate limited")

        time.sleep(2)  # Be gentle on token budget

    # --- Topic queries (max 3) ---
    topic_limit = min(3, len(TOPIC_QUERIES))
    print(f"\nFetching topic queries ({topic_limit})...")

    for query in TOPIC_QUERIES[:topic_limit]:
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  Query: {query[:80]}...")
        data = _fetch_articles(query, count=15)
        request_count += 1

        if data and "articles" in data:
            results = data["articles"].get("results", [])
            print(f"    Got {len(results)} articles")
            preds = extract_predictions_from_articles(results, query, kol_names_lower)
            all_predictions.extend(preds)
            print(f"    Extracted {len(preds)} predictions")
        else:
            print("    Failed or rate limited")

        time.sleep(2)  # Be gentle on token budget

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
                   VALUES ('eventregistry', ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    request_count * 15,  # approximate articles fetched
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

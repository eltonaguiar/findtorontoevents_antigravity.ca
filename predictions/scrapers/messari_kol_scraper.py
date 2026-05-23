"""
Messari KOL Scraper
===================
Fetches crypto asset news, governance proposals, and fundamental data
from the Messari API to extract directional bias signals.

Free-tier friendly: 20 req/min -- caps at 10 requests per run.
"""

import os
import re
import sys
import json
import ssl
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
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
MESSARI_KEY = os.getenv("MESSARI_API_KEY", "")
BASE_URL = "https://data.messari.io/api"

# Top assets for metric signals
TOP_ASSETS = ["bitcoin", "ethereum", "solana", "binance-coin", "dogecoin"]

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

# Messari tag-to-symbol mapping for common tags
TAG_SYMBOL_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "bnb": "BNBUSDT",
    "binance": "BNBUSDT",
    "dogecoin": "DOGEUSDT",
    "cardano": "ADAUSDT",
    "xrp": "XRPUSDT",
    "ripple": "XRPUSDT",
    "polkadot": "DOTUSDT",
    "avalanche": "AVAXUSDT",
    "chainlink": "LINKUSDT",
    "sui": "SUIUSDT",
    "near": "NEARUSDT",
    "arbitrum": "ARBUSDT",
    "optimism": "OPUSDT",
    "aptos": "APTUSDT",
    "sei": "SEIUSDT",
    "injective": "INJUSDT",
    "filecoin": "FILUSDT",
    "celestia": "TIAUSDT",
    "toncoin": "TONUSDT",
    "cosmos": "ATOMUSDT",
    "fantom": "FTMUSDT",
    "polygon": "MATICUSDT",
    "render": "RENDERUSDT",
    "pepe": "PEPEUSDT",
    "shiba-inu": "SHIBUSDT",
}

# Messari asset key to symbol mapping for metrics
ASSET_KEY_SYMBOL_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "binance-coin": "BNBUSDT",
    "dogecoin": "DOGEUSDT",
}


# ===================================================================
#  Fetch helper
# ===================================================================

def _fetch_messari(endpoint: str) -> dict | None:
    """Fetch from Messari API with auth header and relaxed SSL."""
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("x-messari-api-key", MESSARI_KEY)
    req.add_header("User-Agent", "Mozilla/5.0")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  Messari API error: {e}")
        return None


# ===================================================================
#  Sentiment scoring
# ===================================================================

def _score_sentiment(text: str) -> float:
    """Score sentiment of text. Returns 0-1, 0.5 = neutral."""
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.5
    return round(pos / total, 3)


# ===================================================================
#  Symbol extraction from Messari tags
# ===================================================================

def _symbols_from_tags(tags: list) -> list[dict]:
    """Map Messari tags to normalized symbols."""
    results = []
    seen = set()
    for tag in tags:
        tag_lower = tag.lower().strip()
        if tag_lower in TAG_SYMBOL_MAP:
            sym = TAG_SYMBOL_MAP[tag_lower]
            if sym not in seen:
                seen.add(sym)
                results.append({"symbol": sym, "asset_class": "crypto", "raw": tag})
    return results


# ===================================================================
#  News extraction
# ===================================================================

def extract_predictions_from_news(articles: list[dict]) -> list[dict]:
    """Extract directional predictions from Messari news articles.

    Parameters
    ----------
    articles : list[dict]
        Article objects from the Messari /v1/news response.

    Returns a list of prediction dicts ready for insert_prediction().
    """
    predictions: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    for article in articles:
        title = article.get("title") or ""
        content = article.get("content") or ""
        published_at = article.get("published_at") or ""
        tags = article.get("tags") or []
        author_obj = article.get("author") or {}
        author_name = author_obj.get("name") or "Messari Research"
        article_url = article.get("url") or ""

        # Freshness check: skip articles older than 48h
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except (ValueError, TypeError):
                pass  # If parse fails, include the article

        combined = f"{title} {content[:500]}"
        if len(combined.strip()) < 10:
            continue

        # Extract symbols from tags first, then from text
        symbol_hits = _symbols_from_tags(tags)
        text_symbols = extract_symbols(combined)
        # Merge, avoiding duplicates
        seen_syms = {s["symbol"] for s in symbol_hits}
        for ts in text_symbols:
            if ts["symbol"] not in seen_syms:
                seen_syms.add(ts["symbol"])
                symbol_hits.append(ts)

        if not symbol_hits:
            continue

        # Direction from regex
        dir_match = DIRECTION_RE.search(combined)
        sentiment = _score_sentiment(combined)

        if dir_match:
            dir_word = dir_match.group(1).lower()
            direction = "LONG" if dir_word in ("long", "bullish") else "SHORT"
        elif sentiment > 0.55:
            direction = "LONG"
        elif sentiment < 0.45:
            direction = "SHORT"
        else:
            # Keyword fallback for neutral sentiment
            text_lower = combined.lower()
            bull_kw = sum(1 for w in ("rally", "surge", "bullish", "gain", "rise", "breakout", "buy") if w in text_lower)
            bear_kw = sum(1 for w in ("crash", "drop", "bearish", "fear", "sell", "dump", "plunge") if w in text_lower)
            if bull_kw > bear_kw:
                direction = "LONG"
            elif bear_kw > bull_kw:
                direction = "SHORT"
            else:
                continue

        # Extract price levels
        entry_m = ENTRY_RE.search(combined)
        tp_m = TP_RE.search(combined)
        sl_m = SL_RE.search(combined)

        entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
        tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
        sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

        # News-inferred: reduce sentiment by 0.7
        adjusted_sentiment = round(sentiment * 0.7, 3)

        for sym_info in symbol_hits:
            symbol = sym_info.get("symbol", "")
            if not symbol:
                continue

            predictions.append({
                "predictor_id": f"messari:{author_name}",
                "platform": "messari",
                "display_name": author_name,
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "source_url": article_url,
                "source_text": combined[:500],
                "scraped_at": now_iso,
                "is_known_analyst": 0,
                "analyst_category": "news_inferred",
                "sentiment_score": adjusted_sentiment,
            })

    return predictions


# ===================================================================
#  Asset metric signals
# ===================================================================

def extract_metric_signals(asset_key: str, data: dict) -> list[dict]:
    """Extract momentum signals from Messari asset metrics.

    If 24h percent change exceeds +/-5%, generate a directional signal.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    predictions = []

    symbol = ASSET_KEY_SYMBOL_MAP.get(asset_key)
    if not symbol:
        return predictions

    try:
        market_data = data.get("data", {}).get("market_data", {})
        pct_change_24h = market_data.get("percent_change_usd_last_24_hours")
        if pct_change_24h is None:
            return predictions

        pct_change_24h = float(pct_change_24h)

        # Only generate signal if >5% move in either direction
        if abs(pct_change_24h) < 5.0:
            return predictions

        direction = "LONG" if pct_change_24h > 0 else "SHORT"

        # Sentiment based on magnitude: 5% = 0.6, 10% = 0.7, 20%+ = 0.85
        magnitude = min(abs(pct_change_24h), 25.0)
        raw_sentiment = 0.5 + (magnitude / 100.0)
        # Reduce by 0.7 for metric-inferred signals
        adjusted_sentiment = round(raw_sentiment * 0.7, 3)

        price_usd = market_data.get("price_usd")

        predictions.append({
            "predictor_id": f"messari:metrics_{asset_key}",
            "platform": "messari",
            "display_name": f"Messari Metrics ({asset_key})",
            "symbol": symbol,
            "direction": direction,
            "entry_price": float(price_usd) if price_usd else None,
            "take_profit": None,
            "stop_loss": None,
            "source_url": f"https://messari.io/asset/{asset_key}",
            "source_text": f"24h change: {pct_change_24h:+.2f}%",
            "scraped_at": now_iso,
            "is_known_analyst": 0,
            "analyst_category": "messari_metrics",
            "sentiment_score": adjusted_sentiment,
        })
    except (KeyError, TypeError, ValueError) as e:
        print(f"  Metric parse error for {asset_key}: {e}")

    return predictions


# ===================================================================
#  Main
# ===================================================================

def main():
    if not MESSARI_KEY:
        print("[messari_kol_scraper] No MESSARI_API_KEY set - skipping.")
        return

    print("=" * 60)
    print("Messari KOL Scraper")
    print("=" * 60)

    # Free tier: 20 req/min -- cap total requests at 10
    MAX_REQUESTS = 10
    request_count = 0

    all_predictions: list[dict] = []

    # --- Source 1: News feed (up to 3 pages) ---
    news_pages = 3
    print(f"\nFetching Messari news ({news_pages} pages)...")

    for page in range(1, news_pages + 1):
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  Page {page}...")
        data = _fetch_messari(f"/v1/news?page={page}&as-markdown=false")
        request_count += 1

        if data and "data" in data:
            articles = data.get("data", [])
            print(f"    Got {len(articles)} articles")
            preds = extract_predictions_from_news(articles)
            all_predictions.extend(preds)
            print(f"    Extracted {len(preds)} predictions")
        else:
            print("    Failed or no data")

        time.sleep(1)  # Rate limit between calls

    # --- Source 2: Asset metric signals (top 5 assets) ---
    print(f"\nFetching asset metrics for {len(TOP_ASSETS)} assets...")

    for asset_key in TOP_ASSETS:
        if request_count >= MAX_REQUESTS:
            print("  Request cap reached, stopping.")
            break

        print(f"  {asset_key}...")
        data = _fetch_messari(f"/v1/assets/{asset_key}/metrics")
        request_count += 1

        if data:
            preds = extract_metric_signals(asset_key, data)
            all_predictions.extend(preds)
            if preds:
                print(f"    Momentum signal detected: {preds[0]['direction']}")
            else:
                print(f"    No significant momentum (< 5% 24h change)")
        else:
            print("    Failed or no data")

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
                   VALUES ('messari', ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    request_count * 10,  # approximate items fetched
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

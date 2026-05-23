"""Substack KOL scraper - extracts crypto predictions from KOL newsletters via RSS.

Fetches recent Substack posts for registered KOLs, extracts trading signals
(direction, entry, TP, SL) and inserts them as predictions.
"""
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# --- project imports ---
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db, insert_prediction

sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
from kol_registry import get_kols_by_platform
from symbol_extractor import extract_symbols

# ---------------------------------------------------------------------------
# Regex patterns (shared with twitter / analyst scrapers)
# ---------------------------------------------------------------------------
ENTRY_RE = re.compile(r'(?:entry|buy|short|long|target\s*1?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|bullish|bearish|buy|sell)\b', re.I)

HTML_TAG_RE = re.compile(r'<[^>]+>')

# ---------------------------------------------------------------------------
# Sentiment keyword lists
# ---------------------------------------------------------------------------
BULLISH_KEYWORDS = [
    "long", "bullish", "buy", "accumulate", "breakout", "moon", "pump",
    "upside", "higher", "rally", "support", "bounce", "dip buy",
    "oversold", "reversal up", "golden cross",
]

BEARISH_KEYWORDS = [
    "short", "bearish", "sell", "dump", "crash", "downside", "lower",
    "resistance", "breakdown", "death cross", "overbought",
    "reversal down", "capitulation", "flush",
]


# ---------------------------------------------------------------------------
# RSS fetching
# ---------------------------------------------------------------------------

def fetch_substack_rss(substack_handle: str, max_age_hours: int = 48) -> list[dict]:
    """Fetch recent posts from a Substack newsletter RSS feed.

    Parameters
    ----------
    substack_handle : str
        The Substack subdomain (e.g. ``willywoo`` for willywoo.substack.com).
    max_age_hours : int
        Only return items published within the last *max_age_hours*.

    Returns
    -------
    list[dict]
        Each dict contains ``title``, ``link``, ``description``, ``published``.
    """
    url = f"https://{substack_handle}.substack.com/feed"
    items: list[dict] = []

    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            print(f"  [WARN] No <channel> in RSS for {substack_handle}")
            return items

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for item_el in channel.findall("item"):
            try:
                title = (item_el.findtext("title") or "").strip()
                link = (item_el.findtext("link") or "").strip()
                pub_date_str = (item_el.findtext("pubDate") or "").strip()

                # Parse publish date (RFC 2822)
                published_dt = None
                if pub_date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_dt = parsedate_to_datetime(pub_date_str)
                        if published_dt.tzinfo is None:
                            published_dt = published_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        published_dt = None

                # Filter by age
                if published_dt and published_dt < cutoff:
                    continue

                # Description — strip HTML tags
                raw_desc = (item_el.findtext("description") or "").strip()
                # Also check content:encoded
                content_encoded = item_el.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
                description = HTML_TAG_RE.sub(" ", raw_desc + " " + content_encoded).strip()

                if not title and not description:
                    continue

                items.append({
                    "title": title,
                    "link": link,
                    "description": description,
                    "published": pub_date_str,
                })
            except Exception as e:
                print(f"  [WARN] Skipping RSS item: {e}")
                continue

    except requests.RequestException as e:
        print(f"  [ERR] RSS fetch failed for {substack_handle}: {e}")
    except ET.ParseError as e:
        print(f"  [ERR] XML parse failed for {substack_handle}: {e}")
    except Exception as e:
        print(f"  [ERR] Unexpected error fetching {substack_handle}: {e}")

    return items


# ---------------------------------------------------------------------------
# Prediction extraction
# ---------------------------------------------------------------------------

def extract_predictions_from_post(
    title: str,
    content: str,
    kol: dict,
    source_url: str,
) -> list[dict]:
    """Extract trading predictions from a single Substack post.

    Parameters
    ----------
    title : str
        Post title.
    content : str
        Post body (HTML-stripped).
    kol : dict
        KOL registry entry.
    source_url : str
        Permalink to the post.

    Returns
    -------
    list[dict]
        Standard prediction dicts ready for ``insert_prediction``.
    """
    preds: list[dict] = []
    full_text = f"{title} {content}".strip()
    if len(full_text) < 30:
        return preds

    # --- symbols ---
    symbols = extract_symbols(full_text)
    if not symbols:
        return preds

    # --- direction via keyword counting ---
    text_lower = full_text.lower()
    bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

    # Also check the explicit regex
    dir_match = DIRECTION_RE.search(full_text)
    if dir_match:
        dw = dir_match.group(1).lower()
        if dw in ("long", "bullish", "buy"):
            bull_count += 2
        elif dw in ("short", "bearish", "sell"):
            bear_count += 2

    if bull_count == 0 and bear_count == 0:
        return preds

    direction = "LONG" if bull_count >= bear_count else "SHORT"

    # Sentiment score: range roughly -1 .. +1
    total_kw = bull_count + bear_count
    sentiment = round((bull_count - bear_count) / max(total_kw, 1), 2)

    # --- price levels ---
    entry_m = ENTRY_RE.search(full_text)
    tp_m = TP_RE.search(full_text)
    sl_m = SL_RE.search(full_text)

    entry_price = float(entry_m.group(1).replace(",", "")) if entry_m else None
    take_profit = float(tp_m.group(1).replace(",", "")) if tp_m else None
    stop_loss = float(sl_m.group(1).replace(",", "")) if sl_m else None

    now_iso = datetime.now(timezone.utc).isoformat()

    for sym in symbols:
        preds.append({
            "predictor_id": f"substack:{kol['handle']}",
            "platform": "substack",
            "display_name": kol.get("display_name", kol["handle"]),
            "symbol": sym,
            "direction": direction,
            "entry_price": entry_price,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "sentiment_score": sentiment,
            "source_url": source_url,
            "source_text": full_text[:500],
            "scraped_at": now_iso,
            "is_known_analyst": 1,
            "analyst_category": kol.get("category", "macro"),
        })

    return preds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Scrape Substack newsletters for KOL predictions."""
    print("=" * 60)
    print("Substack KOL Scraper")
    print("=" * 60)

    kols = get_kols_by_platform("substack")
    if not kols:
        print("[INFO] No KOLs registered on substack platform.")
        return 0

    print(f"[INFO] Found {len(kols)} KOLs with Substack presence")

    conn = get_db()
    total_inserted = 0
    total_posts = 0
    errors: list[str] = []

    for kol in kols:
        substack_url = kol.get("substack_url")
        if not substack_url:
            print(f"  Skipping {kol['handle']}: no substack_url configured")
            continue

        # Derive handle from URL: https://willywoo.substack.com -> willywoo
        try:
            substack_handle = substack_url.split("//")[1].split(".substack.com")[0]
        except (IndexError, AttributeError):
            print(f"  [WARN] Cannot parse substack_url for {kol['handle']}: {substack_url}")
            errors.append(f"{kol['handle']}: bad substack_url")
            continue

        print(f"\n  Fetching {kol['display_name']} ({substack_handle}.substack.com) ...")

        try:
            posts = fetch_substack_rss(substack_handle)
            print(f"    Got {len(posts)} recent posts")
            total_posts += len(posts)

            extracted = 0
            for post in posts:
                try:
                    preds = extract_predictions_from_post(
                        title=post["title"],
                        content=post["description"],
                        kol=kol,
                        source_url=post["link"],
                    )
                    for pred in preds:
                        try:
                            insert_prediction(conn, pred)
                            conn.commit()
                            total_inserted += 1
                            extracted += 1
                            print(f"      + {pred['symbol']} {pred['direction']}")
                        except Exception as db_err:
                            print(f"      [DB ERR] {db_err}")
                except Exception as post_err:
                    print(f"    [WARN] Post extraction error: {post_err}")

            print(f"    Extracted: {extracted} predictions")

        except Exception as feed_err:
            print(f"    [ERR] Feed error for {kol['handle']}: {feed_err}")
            errors.append(f"{kol['handle']}: {feed_err}")

        # Rate limit between feeds
        time.sleep(1.5)

    # Log scrape run
    try:
        conn.execute("""
            INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
            VALUES ('substack', ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            total_posts,
            total_inserted,
            "; ".join(errors) if errors else None,
        ))
        conn.commit()
    except Exception as log_err:
        print(f"[WARN] Could not write scrape_log: {log_err}")

    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Substack total: {total_inserted} predictions from {total_posts} posts")
    if errors:
        print(f"Errors: {len(errors)}")
    print(f"{'=' * 60}")

    return total_inserted


if __name__ == "__main__":
    main()

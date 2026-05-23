"""YouTube KOL scraper - extracts crypto predictions from YouTube transcripts and RSS feeds.

Uses the KOL registry for channel discovery. Tries transcript extraction first,
falls back to title-only analysis when youtube-transcript-api is unavailable.
"""
import logging
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Path setup - standard project pattern
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db, insert_prediction

sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
from kol_registry import get_kols_by_platform

# Optional: symbol_extractor (may not exist yet)
try:
    from symbol_extractor import extract_symbols
    HAS_SYMBOL_EXTRACTOR = True
except ImportError:
    HAS_SYMBOL_EXTRACTOR = False

# Optional: youtube-transcript-api
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("youtube_kol_scraper")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

BULLISH_KEYWORDS = [
    "bullish", "long", "buy", "accumulate", "moon",
    "breakout", "pump", "rally", "surge", "upside",
]
BEARISH_KEYWORDS = [
    "bearish", "short", "sell", "dump", "crash",
    "breakdown", "plunge", "downside", "collapse", "correction",
]

# Price extraction regex (consistent with twitter_scraper.py)
ENTRY_RE = re.compile(
    r'(?:entry|buy|short|long|target\s*1?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I,
)
TP_RE = re.compile(
    r'(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I,
)
SL_RE = re.compile(
    r'(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I,
)
DIRECTION_RE = re.compile(r'\b(long|short|bullish|bearish)\b', re.I)

# Fallback symbol regex when symbol_extractor is unavailable
SYMBOL_RE = re.compile(
    r'\$?(BTC|ETH|SOL|BNB|DOGE|LINK|AVAX|XRP|ADA|DOT|SUI|MATIC|OP|ARB|APT|SEI|TIA|INJ)\b',
    re.I,
)

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


# ---------------------------------------------------------------------------
# RSS feed fetching
# ---------------------------------------------------------------------------

def fetch_recent_videos(channel_id: str, max_age_hours: int = 48) -> list[dict]:
    """Fetch recent videos from a YouTube channel via its Atom RSS feed.

    Returns list of {"video_id": str, "title": str, "published": str}
    filtered to videos published within *max_age_hours*.
    """
    url = YOUTUBE_RSS.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("RSS fetch failed for channel %s: %s", channel_id, exc)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        log.warning("XML parse error for channel %s: %s", channel_id, exc)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    videos: list[dict] = []

    for entry in root.findall("atom:entry", ATOM_NS):
        try:
            title = entry.findtext("atom:title", "", ATOM_NS)
            raw_id = entry.findtext("atom:id", "", ATOM_NS)
            video_id = raw_id.split(":")[-1] if raw_id else ""
            published_str = entry.findtext("atom:published", "", ATOM_NS)

            if not video_id or not published_str:
                continue

            # Parse ISO-8601 published date
            pub_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            if pub_dt < cutoff:
                continue

            videos.append({
                "video_id": video_id,
                "title": title,
                "published": published_str,
            })
        except Exception as exc:
            log.debug("Skipping entry: %s", exc)

    return videos


# ---------------------------------------------------------------------------
# Transcript extraction
# ---------------------------------------------------------------------------

def extract_transcript_text(video_id: str) -> str | None:
    """Retrieve the full transcript text for a YouTube video.

    Returns None when the youtube-transcript-api package is not installed
    or the transcript is unavailable.
    """
    if not HAS_TRANSCRIPT_API:
        return None

    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(seg["text"] for seg in segments)
    except Exception as exc:
        log.debug("Transcript unavailable for %s: %s", video_id, exc)
        return None


# ---------------------------------------------------------------------------
# Prediction extraction
# ---------------------------------------------------------------------------

def _fallback_extract_symbols(text: str) -> list[dict]:
    """Simple regex symbol extraction when symbol_extractor is missing."""
    found = SYMBOL_RE.findall(text)
    seen: set[str] = set()
    results: list[dict] = []
    for sym in found:
        sym_upper = sym.upper()
        if sym_upper not in seen:
            seen.add(sym_upper)
            results.append({"symbol": sym_upper + "USDT", "raw": sym})
    return results


def _compute_sentiment(text: str) -> tuple[str | None, float]:
    """Determine direction and sentiment score from keyword counts.

    Returns (direction, sentiment_score) where sentiment_score is 0-1
    (0 = maximally bearish, 1 = maximally bullish, 0.5 = neutral).
    """
    text_lower = text.lower()
    bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

    total = bull_count + bear_count
    if total == 0:
        return None, 0.5

    sentiment = bull_count / total  # 0..1

    if bull_count > bear_count:
        direction = "LONG"
    elif bear_count > bull_count:
        direction = "SHORT"
    else:
        direction = None

    return direction, round(sentiment, 3)


def extract_predictions_from_text(
    text: str,
    kol_handle: str,
    source_url: str,
    kol: dict | None = None,
) -> list[dict]:
    """Extract trading predictions from transcript or title text.

    Uses symbol_extractor if available, otherwise falls back to regex.
    """
    if kol is None:
        kol = {}

    # --- Symbol detection ---
    if HAS_SYMBOL_EXTRACTOR:
        symbols = extract_symbols(text)
    else:
        symbols = _fallback_extract_symbols(text)

    if not symbols:
        return []

    # --- Direction / sentiment ---
    dir_match = DIRECTION_RE.search(text)
    keyword_dir, sentiment = _compute_sentiment(text)

    if dir_match:
        word = dir_match.group(1).lower()
        direction = "LONG" if word in ("long", "bullish") else "SHORT"
    elif keyword_dir:
        direction = keyword_dir
    else:
        return []

    # --- Price levels ---
    entry_m = ENTRY_RE.search(text)
    tp_m = TP_RE.search(text)
    sl_m = SL_RE.search(text)

    entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
    tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
    sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

    # --- Build prediction dicts ---
    preds: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for symbol_info in symbols:
        sym = symbol_info["symbol"] if isinstance(symbol_info, dict) else str(symbol_info)
        preds.append({
            "predictor_id": f"youtube:{kol_handle}",
            "platform": "youtube",
            "display_name": kol.get("display_name", kol_handle),
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "sentiment_score": sentiment,
            "source_url": source_url,
            "source_text": text[:500],
            "scraped_at": now_iso,
            "is_known_analyst": 1,
            "analyst_category": kol.get("category", "narrative"),
        })

    return preds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Scrape YouTube KOL channels for crypto predictions."""
    youtube_kols = get_kols_by_platform("youtube")
    if not youtube_kols:
        log.info("No YouTube KOLs found in registry")
        return

    conn = get_db()
    total_inserted = 0
    total_videos = 0
    total_skipped = 0

    for kol in youtube_kols:
        channel_id = kol.get("youtube_channel_id")
        handle = kol["handle"]

        if not channel_id:
            log.debug("Skipping %s - no youtube_channel_id", handle)
            continue

        log.info("Fetching videos for %s (%s)", kol["display_name"], handle)
        videos = fetch_recent_videos(channel_id)

        if not videos:
            log.info("  No recent videos for %s", handle)
            continue

        for video in videos:
            vid = video["video_id"]
            title = video["title"]
            url = f"https://www.youtube.com/watch?v={vid}"
            total_videos += 1

            # Try transcript first, fall back to title-only
            transcript = extract_transcript_text(vid)
            if transcript:
                text = f"{title}\n\n{transcript}"
            else:
                text = title

            preds = extract_predictions_from_text(text, handle, url, kol)

            for pred in preds:
                try:
                    insert_prediction(conn, pred)
                    total_inserted += 1
                except Exception as exc:
                    log.warning("Failed to insert prediction: %s", exc)
                    total_skipped += 1

            # Rate-limit between transcript fetches
            time.sleep(1)

    conn.commit()
    conn.close()

    log.info(
        "YouTube KOL scrape complete: %d videos scanned, %d predictions inserted, %d skipped",
        total_videos,
        total_inserted,
        total_skipped,
    )


if __name__ == "__main__":
    main()

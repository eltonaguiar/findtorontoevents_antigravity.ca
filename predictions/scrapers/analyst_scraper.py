"""
Analyst Scraper — tracks 20 top crypto analysts from KIMI research.

Scrapes TradingView Ideas pages for analysts who cross-post there,
and marks all predictions with is_known_analyst=1 + analyst_category.

Uses scrapling (TLS-fingerprinted HTTP) with requests fallback.
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scrapling import Fetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

import requests

from db import get_db, insert_prediction

# ────────────────────────────────────────────────────────────
# Analyst Registry — unified via predictions/kol/kol_registry.py
# Falls back to inline dict if registry not available
# ────────────────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
    from kol_registry import get_analysts_dict, CATEGORY_LABELS
    ANALYSTS = get_analysts_dict()
except ImportError:
    ANALYSTS = {
        "woonomic": {"display_name": "Willy Woo", "category": "on_chain", "platform": "twitter", "tradingview_handle": None, "specialty": "On-chain analytics"},
        "intocryptoverse": {"display_name": "Benjamin Cowen", "category": "on_chain", "platform": "youtube", "tradingview_handle": "intocryptoverse", "specialty": "Cycle analysis"},
        "CryptoMichNL": {"display_name": "Michael van de Poppe", "category": "ta_daily", "platform": "twitter", "tradingview_handle": "CryptoMichNL", "specialty": "Altcoin TA"},
        "CryptoDonAlt": {"display_name": "DonAlt", "category": "ta_daily", "platform": "twitter", "tradingview_handle": "CryptoDonAlt", "specialty": "TA contrarian"},
        "CredibleCrypto": {"display_name": "Credible Crypto", "category": "ta_daily", "platform": "twitter", "tradingview_handle": "CredibleCrypto", "specialty": "Elliott Wave"},
        "davthewave": {"display_name": "Dave the Wave", "category": "ta_daily", "platform": "twitter", "tradingview_handle": "davthewave", "specialty": "LGC model"},
        "scottmelker": {"display_name": "Scott Melker", "category": "ta_daily", "platform": "twitter", "tradingview_handle": "scottmelker", "specialty": "TA + macro"},
        "RaoulGMI": {"display_name": "Raoul Pal", "category": "macro", "platform": "twitter", "tradingview_handle": None, "specialty": "Macro/institutional"},
        "CryptoHayes": {"display_name": "Arthur Hayes", "category": "macro", "platform": "twitter", "tradingview_handle": None, "specialty": "Macro narrative"},
        "coinbureau": {"display_name": "Coin Bureau", "category": "narrative", "platform": "youtube", "tradingview_handle": None, "specialty": "Deep-dive research"},
    }
    CATEGORY_LABELS = {"on_chain": "On-Chain", "macro": "Macro", "ta_daily": "TA Daily", "narrative": "Narrative"}

# Symbols to scan on TradingView for each analyst
TV_SYMBOLS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "DOGEUSD",
    "LINKUSD", "AVAXUSD", "XRPUSD", "ADAUSD", "DOTUSD",
    "SUIUSD", "NEARUSD", "MATICUSD", "ARBUSD", "OPUSD",
]
TV_TO_BINANCE = {s: s.replace("USD", "USDT") for s in TV_SYMBOLS}

# Regex patterns (reused from tradingview_scraper.py)
ENTRY_RE = re.compile(r'(?:entry|buy|sell|open|position)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp\d?|take.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|buy|sell|bullish|bearish)\b', re.I)

# Rate limit between requests
DELAY = 1.5


def _fetch_page(url: str) -> str | None:
    """Fetch a page using scrapling (TLS fingerprinting) or fallback to requests."""
    if HAS_SCRAPLING:
        try:
            fetcher = Fetcher(auto_match=False)
            resp = fetcher.get(url, timeout=20)
            if resp.status == 200:
                return resp.text
            print(f"  Scrapling status {resp.status} for {url}")
        except Exception as e:
            print(f"  Scrapling error: {e}, falling back to requests")

    # Fallback to requests
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.text
        print(f"  requests status {resp.status_code} for {url}")
    except Exception as e:
        print(f"  requests error: {e}")

    return None


def get_tv_analysts() -> list[tuple[str, dict]]:
    """Return analysts who have TradingView handles."""
    return [
        (handle, info) for handle, info in ANALYSTS.items()
        if info.get("tradingview_handle")
    ]


def get_manual_tracking_analysts() -> list[tuple[str, dict]]:
    """Return analysts who need manual tracking (no TradingView handle)."""
    return [
        (handle, info) for handle, info in ANALYSTS.items()
        if not info.get("tradingview_handle")
    ]


def _parse_analyst_ideas(html: str, tv_handle: str, analyst_handle: str,
                          analyst_info: dict) -> list[dict]:
    """Parse HTML content for a specific analyst's trading ideas."""
    ideas = []
    # Split by idea containers
    sections = re.split(r'(?=<(?:div|article|section)[^>]*class="[^"]*idea)', html, flags=re.I)
    if len(sections) < 2:
        sections = re.split(r'(?=<h[1-4])', html)

    for section in sections:
        if len(section) < 100:
            continue

        # Strip HTML tags for text analysis
        text = re.sub(r'<[^>]+>', ' ', section)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 50:
            continue

        # Look for the analyst's handle in the section
        author_match = re.search(r'by\s+(\w+)', text, re.I)
        if not author_match:
            continue
        found_author = author_match.group(1).lower()

        # Only include ideas from the specific analyst
        if found_author != tv_handle.lower():
            continue

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

        # Try to detect symbol from section content
        detected_symbol = None
        for tv_sym in TV_SYMBOLS:
            base = tv_sym.replace("USD", "")
            if re.search(rf'\b{base}\b', text, re.I):
                detected_symbol = TV_TO_BINANCE[tv_sym]
                break

        if not detected_symbol:
            continue

        if not (entry or tp or sl):
            continue

        ideas.append({
            "predictor_id": f"analyst:{analyst_handle}",
            "platform": analyst_info["platform"],
            "display_name": analyst_info["display_name"],
            "symbol": detected_symbol,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "source_url": f"https://www.tradingview.com/u/{tv_handle}/",
            "source_text": text[:500],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "is_known_analyst": 1,
            "analyst_category": analyst_info["category"],
        })

    return ideas


def scrape_analyst_tradingview_profiles() -> int:
    """Scrape TradingView profiles for analysts who have TV handles."""
    tv_analysts = get_tv_analysts()
    if not tv_analysts:
        print("[analyst_scraper] No analysts with TradingView handles.")
        return 0

    conn = get_db()
    total = 0
    errors = []

    for handle, info in tv_analysts:
        tv_handle = info["tradingview_handle"]
        url = f"https://www.tradingview.com/u/{tv_handle}/#published-charts"
        print(f"  Scraping TradingView profile: {info['display_name']} (@{tv_handle})")

        try:
            html = _fetch_page(url)
            if not html:
                errors.append(f"{tv_handle}: fetch failed")
                print(f"    FAILED: fetch unsuccessful")
                continue

            ideas = _parse_analyst_ideas(html, tv_handle, handle, info)

            for idea in ideas:
                _insert_analyst_prediction(conn, idea)
                total += 1

            print(f"    Found {len(ideas)} predictions")

        except Exception as e:
            errors.append(f"{tv_handle}: {e}")
            print(f"    ERROR: {e}")

        time.sleep(DELAY)

    # Also scan TradingView ideas pages for symbols, looking for known analyst names
    total += _scrape_ideas_for_analysts(conn, errors)

    # Log the scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('analyst_tracker', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        total, total,
        "; ".join(errors) if errors else None,
    ))
    conn.commit()
    conn.close()
    print(f"\n[analyst_scraper] Total: {total} analyst predictions extracted")
    return total


def _scrape_ideas_for_analysts(conn, errors: list) -> int:
    """Scan TradingView symbol ideas pages looking for posts by known analysts."""
    # Build a set of all TV handles to look for (case-insensitive)
    tv_handles = {}
    for handle, info in ANALYSTS.items():
        tv_h = info.get("tradingview_handle")
        if tv_h:
            tv_handles[tv_h.lower()] = (handle, info)

    total = 0
    for tv_sym in TV_SYMBOLS[:6]:  # Top 6 symbols to limit runtime
        url = f"https://www.tradingview.com/symbols/{tv_sym}/ideas/"
        binance_sym = TV_TO_BINANCE[tv_sym]
        print(f"  Scanning {tv_sym} ideas for known analysts...")

        try:
            html = _fetch_page(url)
            if not html:
                continue

            # Strip HTML for text analysis
            text_content = re.sub(r'<[^>]+>', ' ', html)
            sections = re.split(r'(?=\bby\s+\w+)', text_content)

            for section in sections:
                if len(section) < 50:
                    continue

                author_match = re.search(r'by\s+(\w+)', section, re.I)
                if not author_match:
                    continue

                found_author = author_match.group(1).lower()
                if found_author not in tv_handles:
                    continue

                analyst_handle, analyst_info = tv_handles[found_author]

                dir_match = DIRECTION_RE.search(section)
                if not dir_match:
                    continue
                dir_word = dir_match.group(1).lower()
                direction = "LONG" if dir_word in ("long", "buy", "bullish") else "SHORT"

                entry_m = ENTRY_RE.search(section)
                tp_m = TP_RE.search(section)
                sl_m = SL_RE.search(section)
                entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
                tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
                sl = float(sl_m.group(1).replace(",", "")) if sl_m else None

                if not (entry or tp or sl):
                    continue

                idea = {
                    "predictor_id": f"analyst:{analyst_handle}",
                    "platform": analyst_info["platform"],
                    "display_name": analyst_info["display_name"],
                    "symbol": binance_sym,
                    "direction": direction,
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "source_url": f"https://www.tradingview.com/symbols/{tv_sym}/ideas/",
                    "source_text": section[:500],
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "is_known_analyst": 1,
                    "analyst_category": analyst_info["category"],
                }
                _insert_analyst_prediction(conn, idea)
                total += 1
                print(f"    FOUND: {analyst_info['display_name']} on {binance_sym} ({direction})")

        except Exception as e:
            errors.append(f"{tv_sym} ideas scan: {e}")

        time.sleep(DELAY)

    return total


def _insert_analyst_prediction(conn, pred: dict) -> int:
    """Insert a prediction with analyst fields."""
    # De-dup by source_url
    if pred.get("source_url"):
        existing = conn.execute(
            "SELECT id FROM predictions WHERE source_url = ? AND predictor_id = ?",
            (pred["source_url"], pred["predictor_id"])
        ).fetchone()
        if existing:
            return existing["id"]

    cur = conn.execute("""
        INSERT INTO predictions
            (predictor_id, platform, symbol, direction, entry_price,
             take_profit, stop_loss, sentiment_score, source_url,
             source_text, scraped_at, status, is_known_analyst, analyst_category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
    """, (
        pred["predictor_id"], pred["platform"], pred["symbol"],
        pred["direction"], pred.get("entry_price"),
        pred.get("take_profit"), pred.get("stop_loss"),
        pred.get("sentiment_score"), pred.get("source_url"),
        pred.get("source_text"),
        pred.get("scraped_at", datetime.now(timezone.utc).isoformat()),
        pred.get("is_known_analyst", 1),
        pred.get("analyst_category"),
    ))
    conn.commit()

    # Upsert predictor with analyst fields
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO predictors
            (predictor_id, platform, display_name, first_seen, last_active,
             total_predictions, is_known_analyst, analyst_category)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(predictor_id) DO UPDATE SET
            last_active = ?, total_predictions = total_predictions + 1,
            is_known_analyst = ?, analyst_category = ?
    """, (
        pred["predictor_id"], pred["platform"],
        pred.get("display_name", pred["predictor_id"]),
        now, now,
        pred.get("is_known_analyst", 1),
        pred.get("analyst_category"),
        now,
        pred.get("is_known_analyst", 1),
        pred.get("analyst_category"),
    ))
    conn.commit()
    return cur.lastrowid


def seed_analysts() -> None:
    """Seed all 20 analysts into the predictors table so they appear on the dashboard
    even before any predictions are scraped."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    for handle, info in ANALYSTS.items():
        predictor_id = f"analyst:{handle}"
        conn.execute("""
            INSERT INTO predictors
                (predictor_id, platform, display_name, first_seen, last_active,
                 total_predictions, is_known_analyst, analyst_category)
            VALUES (?, ?, ?, ?, ?, 0, 1, ?)
            ON CONFLICT(predictor_id) DO UPDATE SET
                display_name = ?,
                is_known_analyst = 1,
                analyst_category = ?
        """, (
            predictor_id, info["platform"], info["display_name"],
            now, now, info["category"],
            info["display_name"], info["category"],
        ))

    conn.commit()
    conn.close()
    print(f"[analyst_scraper] Seeded {len(ANALYSTS)} analysts into database")


def get_analyst_registry() -> dict:
    """Return the full analyst registry for use by other modules."""
    return ANALYSTS.copy()


def run() -> int:
    """Main entry point for the analyst scraper."""
    print("=" * 60)
    print("Analyst Scraper — Tracking 20 Top Crypto Analysts")
    print("=" * 60)

    # Seed analysts first
    seed_analysts()

    # Report on tracking status
    tv_analysts = get_tv_analysts()
    manual_analysts = get_manual_tracking_analysts()
    print(f"\nTradingView-scrape-able: {len(tv_analysts)}")
    for h, info in tv_analysts:
        print(f"  - {info['display_name']} (@{info['tradingview_handle']})")

    print(f"\nManual tracking needed (Twitter/YouTube only): {len(manual_analysts)}")
    for h, info in manual_analysts:
        print(f"  - {info['display_name']} (@{h}) [{info['platform']}]")

    total = 0
    twitter_count = 0
    reddit_count = 0
    
    # Scrape TradingView
    print("\n[1/3] Scraping TradingView...")
    tv_count = scrape_analyst_tradingview_profiles()
    total += tv_count
    print(f"  -> TradingView: {tv_count} predictions")
    
    # Scrape Twitter/X for analysts (run in separate process to avoid async issues)
    print("\n[2/3] Scraping Twitter/X...")
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-c", "from scrapers.twitter_scraper import run; run()"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=120
        )
        print(result.stdout)
        if result.stderr:
            print(f"  stderr: {result.stderr[:200]}")
        # Count is embedded in output, parse it
        for line in result.stdout.split('\n'):
            if 'Twitter total:' in line:
                try:
                    twitter_count = int(line.split(':')[1].strip().split()[0])
                    total += twitter_count
                except:
                    pass
        if twitter_count == 0:
            print("  -> Twitter/X: 0 predictions (check output above)")
        else:
            print(f"  -> Twitter/X: {twitter_count} predictions")
    except Exception as e:
        print(f"  -> Twitter/X: ERROR - {e}")
    
    # Scrape Reddit
    print("\n[3/3] Scraping Reddit...")
    try:
        from scrapers.reddit_scraper import scrape_reddit_crypto
        reddit_count = scrape_reddit_crypto()
        total += reddit_count
        print(f"  -> Reddit: {reddit_count} predictions")
    except Exception as e:
        print(f"  -> Reddit: ERROR - {e}")

    print(f"\n{'=' * 60}")
    print(f"Scrape complete: {total} total predictions extracted")
    print(f"  - TradingView: {tv_count}")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    run()

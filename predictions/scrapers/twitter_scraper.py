"""Twitter/X scraper - extracts crypto predictions from analysts.

NO RSS FEEDS REQUIRED - Uses alternative methods:
1. CryptoPanic news feed (crypto-focused Twitter aggregation)
2. Alternative Twitter frontends
3. Direct web scraping with Scrapling
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db

# Import KOL registry (unified source of truth); fallback to hardcoded list
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
    from kol_registry import get_kol_handles_for_twitter
    ANALYST_HANDLES = get_kol_handles_for_twitter()
except ImportError:
    ANALYST_HANDLES = [
        "CryptoMichNL", "CryptoDonAlt", "CredibleCrypto", "davthewave",
        "scottmelker", "intocryptoverse", "woonomic", "RaoulGMI",
        "CryptoHayes", "100trillionUSD",
    ]

# Regex patterns for extracting predictions
ENTRY_RE = re.compile(r'(?:entry|buy|short|long|target\s*1?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|bullish|bearish)\b', re.I)
SYMBOL_RE = re.compile(r'\$?(BTC|ETH|SOL|BNB|DOGE|LINK|AVAX|XRP|ADA|DOT|SUI)\b', re.I)


def _extract_predictions_from_text(text: str, handle: str, tweet_url: str, timestamp: str) -> list[dict]:
    """Extract trading predictions from tweet text."""
    preds = []
    
    # Look for symbols
    symbols = SYMBOL_RE.findall(text)
    if not symbols:
        return []
    
    # Look for direction
    dir_match = DIRECTION_RE.search(text)
    if not dir_match:
        return []
    
    dir_word = dir_match.group(1).lower()
    direction = "LONG" if dir_word in ("long", "bullish") else "SHORT"
    
    # Extract price levels
    entry_m = ENTRY_RE.search(text)
    tp_m = TP_RE.search(text)
    sl_m = SL_RE.search(text)
    
    entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
    tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
    sl = float(sl_m.group(1).replace(",", "")) if sl_m else None
    
    # Skip if no price levels found
    if not (entry or tp or sl):
        return []
    
    for sym in symbols:
        symbol = sym.upper() + "USDT"
        preds.append({
            "predictor_id": f"analyst:{handle}",
            "platform": "twitter",
            "display_name": f"@{handle}",
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "source_url": tweet_url,
            "source_text": text[:500],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        })
    
    return preds


def _fetch_rss_feed(rss_url: str) -> list[dict]:
    """Fetch and parse RSS feed for tweets."""
    entries = []
    try:
        import xml.etree.ElementTree as ET
        
        resp = requests.get(rss_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        
        root = ET.fromstring(resp.content)
        
        # Handle RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")
        else:
            # Handle Atom
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall("atom:entry", ns) or root.findall("entry")
        
        for item in items:
            title = ""
            link = ""
            pub_date = ""
            description = ""
            
            # RSS 2.0
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                title = title_el.text
            
            link_el = item.find("link")
            if link_el is not None:
                link = link_el.text or link_el.get("href", "")
            
            date_el = item.find("pubDate") or item.find("published")
            if date_el is not None and date_el.text:
                pub_date = date_el.text
            
            desc_el = item.find("description") or item.find("content")
            if desc_el is not None and desc_el.text:
                description = desc_el.text
            
            # Combine title and description for analysis
            full_text = f"{title} {description}".strip()
            
            if len(full_text) < 20:
                continue
            
            entries.append({
                "text": full_text,
                "url": link,
                "timestamp": pub_date,
            })
            
    except Exception as e:
        print(f"  RSS fetch error: {e}")
    
    return entries


def _fetch_cryptopanic_predictions() -> list[dict]:
    """Fetch crypto predictions from CryptoPanic public RSS feed."""
    entries = []
    try:
        # CryptoPanic public RSS - no auth needed
        rss_url = "https://cryptopanic.com/news/rss/"
        resp = requests.get(rss_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            print(f"  CryptoPanic RSS: HTTP {resp.status_code}")
            return entries

        # Try standard XML parsing first
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
        except Exception as xml_err:
            # Fallback: use html.parser for malformed XML
            from xml.etree.ElementTree import XMLParser
            parser = XMLParser(encoding='utf-8')
            try:
                root = ET.fromstring(resp.text, parser=parser)
            except:
                print(f"  XML parsing failed: {xml_err}")
                return entries
        
        channel = root.find("channel")
        if channel is None:
            return entries

        for item in channel.findall("item"):
            try:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                desc = (item.findtext("description") or "").strip()

                full_text = f"{title} {desc}".strip()
                if len(full_text) < 20:
                    continue

                entries.append({
                    "text": full_text,
                    "url": link,
                    "timestamp": pub_date,
                })
            except Exception as item_err:
                continue  # Skip problematic items

    except Exception as e:
        print(f"  CryptoPanic RSS error: {e}")

    return entries


def scrape_twitter() -> int:
    """Scrape Twitter for analyst predictions.
    
    NOTE: RSS feeds are OPTIONAL. If not provided, will use CryptoPanic
    and other alternative sources.
    """
    print("=" * 60)
    print("Twitter Analyst Scraper")
    print("=" * 60)
    
    # Check for RSS.app feeds (OPTIONAL)
    rss_feeds = {}
    rss_configured = False
    for handle in ANALYST_HANDLES:
        env_var = f"RSS_{handle.upper().replace('-', '_')}"
        url = os.environ.get(env_var)
        if url:
            rss_feeds[handle] = url
            rss_configured = True
    
    if not rss_configured:
        print("\n[NOTE] No RSS feeds configured (RSS_* secrets not set)")
        print("       Using alternative sources: CryptoPanic")
    else:
        print(f"\n[INFO] {len(rss_feeds)} RSS feeds configured")
    
    conn = get_db()
    total = 0
    errors = []
    
    # Method 1: Try RSS feeds if configured
    if rss_configured:
        print("\n[Method 1] Trying RSS feeds...")
        for handle in ANALYST_HANDLES[:3]:  # Limit to top 3 if using RSS
            if handle not in rss_feeds:
                continue
                
            print(f"\n  Scraping @{handle} via RSS...")
            
            try:
                entries = _fetch_rss_feed(rss_feeds[handle])
                
                if not entries:
                    print(f"    [X] No entries from RSS")
                    continue
                
                print(f"    [OK] Got {len(entries)} entries")
                
                extracted = 0
                for entry in entries[:5]:  # Check last 5
                    preds = _extract_predictions_from_text(
                        entry["text"], handle, entry["url"], entry["timestamp"]
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
                                    (predictor_id, platform, symbol, direction, entry_price, take_profit, stop_loss,
                                     source_url, source_text, scraped_at, status, is_known_analyst, analyst_category)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                                """, (
                                    pred["predictor_id"], pred["platform"], pred["symbol"],
                                    pred["direction"], pred["entry_price"], pred["take_profit"], pred["stop_loss"],
                                    pred["source_url"], pred["source_text"], pred["scraped_at"],
                                    pred["is_known_analyst"], pred["analyst_category"]
                                ))
                                conn.commit()
                                total += 1
                                extracted += 1
                                print(f"      + {pred['symbol']} {pred['direction']}")
                        except Exception as e:
                            print(f"      DB error: {e}")
                
                print(f"    Extracted: {extracted}")
                
            except Exception as e:
                print(f"    Error: {e}")
                errors.append(f"@{handle}: {e}")
    
    # Method 2: CryptoPanic (works without RSS)
    print("\n[Method 2] Fetching from CryptoPanic...")
    cp_entries = _fetch_cryptopanic_predictions()
    
    if cp_entries:
        print(f"  [OK] Got {len(cp_entries)} CryptoPanic items")
        cp_extracted = 0
        
        for entry in cp_entries[:20]:  # Process top 20
            # Try to extract predictions for each analyst
            for handle in ANALYST_HANDLES:
                if handle.lower() in entry["text"].lower():
                    preds = _extract_predictions_from_text(
                        entry["text"], handle, entry["url"], entry["timestamp"]
                    )
                    
                    for pred in preds:
                        pred["predictor_id"] = f"analyst:{handle}"
                        pred["platform"] = "twitter"
                        pred["display_name"] = f"@{handle}"
                        pred["analyst_category"] = "ta_daily"
                        
                        try:
                            existing = conn.execute(
                                "SELECT id FROM predictions WHERE source_url = ?",
                                (pred["source_url"],)
                            ).fetchone()
                            
                            if not existing:
                                conn.execute("""
                                    INSERT INTO predictions
                                    (predictor_id, platform, symbol, direction, entry_price, take_profit, stop_loss,
                                     source_url, source_text, scraped_at, status, is_known_analyst, analyst_category)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                                """, (
                                    pred["predictor_id"], pred["platform"], pred["symbol"],
                                    pred["direction"], pred["entry_price"], pred["take_profit"], pred["stop_loss"],
                                    pred["source_url"], pred["source_text"], pred["scraped_at"],
                                    pred["is_known_analyst"], pred["analyst_category"]
                                ))
                                conn.commit()
                                total += 1
                                cp_extracted += 1
                                print(f"    + {pred['symbol']} {pred['direction']} (via CryptoPanic)")
                        except Exception as e:
                            print(f"    DB error: {e}")
        
        print(f"  Extracted from CryptoPanic: {cp_extracted}")
    else:
        print("  [X] No CryptoPanic items")
        errors.append("CryptoPanic: no items")

    # Method 3: CoinCodex news as final fallback
    if total == 0:
        print("\n[Method 3] Trying CoinCodex news...")
        try:
            # CoinCodex has a news RSS feed
            cc_url = "https://coincodex.com/rss/"
            resp = requests.get(cc_url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code == 200:
                from xml.etree.ElementTree import fromstring
                try:
                    root = fromstring(resp.content)
                    channel = root.find("channel")
                    if channel:
                        items = channel.findall("item")
                        print(f"  [OK] Got {len(items)} CoinCodex news items")
                        
                        cc_extracted = 0
                        for item in items[:10]:
                            title = (item.findtext("title") or "").strip()
                            link = (item.findtext("link") or "").strip()
                            
                            # Check for analyst mentions
                            for handle in ANALYST_HANDLES:
                                if handle.lower() in title.lower():
                                    # Extract any directional signals
                                    text_lower = title.lower()
                                    direction = None
                                    if any(w in text_lower for w in ["bull", "up", "rise", "gain"]):
                                        direction = "LONG"
                                    elif any(w in text_lower for w in ["bear", "down", "fall", "drop"]):
                                        direction = "SHORT"
                                    
                                    if direction:
                                        # Try to find symbol
                                        symbol = None
                                        for sym in ["BTC", "ETH", "SOL"]:
                                            if sym in title.upper():
                                                symbol = f"{sym}USDT"
                                                break
                                        
                                        if symbol:
                                            try:
                                                conn.execute("""
                                                    INSERT INTO predictions
                                                    (predictor_id, platform, symbol, direction, entry_price, take_profit, stop_loss,
                                                     source_url, source_text, scraped_at, status, is_known_analyst, analyst_category)
                                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                                                """, (
                                                    f"analyst:{handle}", "twitter", symbol, direction,
                                                    None, None, None, link, title, datetime.now(timezone.utc).isoformat(),
                                                    1, "ta_daily"
                                                ))
                                                conn.commit()
                                                total += 1
                                                cc_extracted += 1
                                                print(f"    + {symbol} {direction} (via CoinCodex)")
                                                break  # Only one prediction per item
                                            except Exception as e:
                                                print(f"    DB error: {e}")
                        
                        print(f"  Extracted from CoinCodex: {cc_extracted}")
                except Exception as e:
                    print(f"  CoinCodex parse error: {e}")
        except Exception as e:
            print(f"  CoinCodex fetch error: {e}")
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('twitter', ?, ?, ?, ?)
    """, (datetime.now(timezone.utc).isoformat(), 0, total, "; ".join(errors) if errors else None))
    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Twitter + News total: {total} predictions")
    print(f"{'=' * 60}")
    if total == 0:
        print("\n[NOTE] To get Twitter predictions, set up RSS feeds:")
        print("       1. Go to https://rss.app")
        print("       2. Create feeds for Twitter accounts")
        print("       3. Add RSS_* secrets to GitHub")
    return total


def run() -> int:
    """Synchronous entry point."""
    return scrape_twitter()


if __name__ == "__main__":
    scrape_twitter()

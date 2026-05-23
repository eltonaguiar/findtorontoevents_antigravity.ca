#!/usr/bin/env python3
"""
stealth_copytrader_scraper.py
===============================
Uses scrapling's StealthyFetcher to scrape copy trading leaderboards from
platforms with anti-bot protection (Bitget, Bybit, ZuluTrade, eToro, Myfxbook).

Scrapling's StealthyFetcher uses real browser fingerprints and stealth techniques
to bypass CloudFlare, DataDome, and similar protections.

Run: python copy_trader_intel/stealth_copytrader_scraper.py
"""

import json, sys, os, time, re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

try:
    from scrapling import Fetcher, StealthyFetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False
    print("[WARN] scrapling not installed. pip install scrapling")

import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def stealth_get(url, timeout=30):
    """Fetch a page using scrapling's stealth mode, with requests fallback."""
    if HAS_SCRAPLING:
        try:
            # StealthyFetcher uses real browser fingerprints
            fetcher = StealthyFetcher()
            response = fetcher.fetch(url, headless=True, timeout=timeout * 1000)
            return response
        except Exception as e:
            print(f"    [WARN] StealthyFetcher failed: {e}")
            # Fallback to regular Fetcher
            try:
                fetcher = Fetcher()
                response = fetcher.get(url, timeout=timeout)
                return response
            except Exception as e2:
                print(f"    [WARN] Fetcher fallback failed: {e2}")

    # Final fallback: plain requests
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        return r
    except Exception as e:
        print(f"    [ERROR] All fetch methods failed: {e}")
        return None


def get_text(response):
    """Extract text from either scrapling response or requests response."""
    if response is None:
        return ""
    if hasattr(response, 'text'):
        return response.text
    if hasattr(response, 'body'):
        return response.body if isinstance(response.body, str) else response.body.decode('utf-8', errors='replace')
    return str(response)


def get_status(response):
    """Get status code from response."""
    if response is None:
        return 0
    if hasattr(response, 'status_code'):
        return response.status_code
    if hasattr(response, 'status'):
        return response.status
    return 200  # If we got a response object, assume OK


# ============================================================
# SCRAPE: Bitget Copy Trading Leaderboard
# ============================================================

def scrape_bitget_leaderboard():
    """Scrape Bitget copy trading leaderboard with stealth."""
    print("\n  [CRYPTO] Scraping Bitget Copy Trading...")
    traders = []

    # Try multiple pages
    urls = [
        "https://www.bitget.com/copy-trading/futures",
        "https://www.bitget.com/copy-trading/ranking",
    ]

    for url in urls:
        print(f"    Fetching {url}...")
        resp = stealth_get(url)
        text = get_text(resp)
        status = get_status(resp)
        print(f"    Status: {status}, Length: {len(text)} chars")

        if len(text) < 500:
            continue

        # Parse trader data from HTML/JSON embedded in page
        # Look for __NEXT_DATA__ or similar React/Vue state
        next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                # Navigate the Next.js data structure
                page_props = next_data.get("props", {}).get("pageProps", {})
                trader_list = page_props.get("traderList", page_props.get("rankList", []))
                if isinstance(trader_list, list):
                    print(f"    Found {len(trader_list)} traders in __NEXT_DATA__")
                    for t in trader_list:
                        tid = t.get("traderUid", t.get("uid", t.get("encryptedUid", "")))
                        if tid:
                            traders.append({
                                "platform": "Bitget",
                                "asset_class": "CRYPTO",
                                "trader_id": str(tid),
                                "name": t.get("nickName", t.get("traderName", f"BG-{str(tid)[:8]}")),
                                "roi_pct": float(t.get("roiRate", t.get("roi", 0))) * 100 if t.get("roiRate") or t.get("roi") else None,
                                "win_rate": float(t.get("winRate", 0)) * 100 if t.get("winRate") else None,
                                "copiers": int(t.get("followerCount", t.get("copyCount", 0))),
                                "max_drawdown_pct": float(t.get("maxDrawdown", 0)) * 100 if t.get("maxDrawdown") else None,
                                "profile_url": f"https://www.bitget.com/copy-trading/trader/{tid}/futures",
                                "data_quality": "good",
                                "source": "stealth_scrape",
                            })
            except json.JSONDecodeError:
                pass

        # Also try parsing visible HTML trader cards
        # Common pattern: trader name + ROI in structured HTML
        trader_blocks = re.findall(
            r'(?:trader|traderName|nickName)["\s:]+([^"<]{2,30}).*?(?:roi|ROI|return)["\s:]+([+-]?\d+\.?\d*)',
            text, re.IGNORECASE | re.DOTALL
        )
        if trader_blocks and not traders:
            print(f"    Found {len(trader_blocks)} traders from HTML regex")
            for name, roi in trader_blocks[:50]:
                traders.append({
                    "platform": "Bitget",
                    "asset_class": "CRYPTO",
                    "trader_id": name.strip().replace(" ", "_")[:16],
                    "name": name.strip(),
                    "roi_pct": float(roi),
                    "data_quality": "medium",
                    "source": "html_regex",
                })

        if traders:
            break
        time.sleep(2)

    print(f"    [OK] Bitget: {len(traders)} traders scraped")
    return traders


# ============================================================
# SCRAPE: Bybit Copy Trading
# ============================================================

def scrape_bybit_leaderboard():
    """Scrape Bybit copy trading master traders."""
    print("\n  [CRYPTO] Scraping Bybit Copy Trading...")
    traders = []

    url = "https://www.bybit.com/copyTrade/trade-center/leader-board"
    resp = stealth_get(url)
    text = get_text(resp)
    status = get_status(resp)
    print(f"    Status: {status}, Length: {len(text)} chars")

    if len(text) > 500:
        # Look for embedded data
        next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
        if next_data:
            try:
                data = json.loads(next_data.group(1))
                # Try to find trader data in the structure
                props = data.get("props", {}).get("pageProps", {})
                for key in ["leaders", "traders", "masterTraders", "traderList"]:
                    items = props.get(key, [])
                    if isinstance(items, list) and items:
                        print(f"    Found {len(items)} in props.{key}")
                        for t in items:
                            tid = t.get("leaderId", t.get("uid", ""))
                            if tid:
                                traders.append({
                                    "platform": "Bybit",
                                    "asset_class": "CRYPTO",
                                    "trader_id": str(tid),
                                    "name": t.get("name", t.get("nickName", f"BY-{str(tid)[:8]}")),
                                    "roi_pct": float(t.get("roi", 0)) * 100 if t.get("roi") else None,
                                    "copiers": int(t.get("followerNum", 0)),
                                    "profile_url": f"https://www.bybit.com/copyTrade/trade-center/leader-detail?uid={tid}",
                                    "data_quality": "good",
                                    "source": "stealth_scrape",
                                })
                        break
            except json.JSONDecodeError:
                pass

        # Regex fallback for visible content
        if not traders:
            # Look for data-* attributes or structured text
            trader_names = re.findall(r'leader-name["\s>]+([^<]{2,30})', text, re.IGNORECASE)
            trader_rois = re.findall(r'roi-value["\s>]+([+-]?\d+\.?\d*)', text, re.IGNORECASE)
            if trader_names:
                print(f"    Found {len(trader_names)} via HTML regex")
                for i, name in enumerate(trader_names[:50]):
                    roi = float(trader_rois[i]) if i < len(trader_rois) else None
                    traders.append({
                        "platform": "Bybit",
                        "asset_class": "CRYPTO",
                        "trader_id": name.strip()[:16],
                        "name": name.strip(),
                        "roi_pct": roi,
                        "data_quality": "medium",
                        "source": "html_regex",
                    })

    print(f"    [OK] Bybit: {len(traders)} traders")
    return traders


# ============================================================
# SCRAPE: ZuluTrade Leaders (Forex)
# ============================================================

def scrape_zulutrade_leaders():
    """Scrape ZuluTrade forex leaders with stealth."""
    print("\n  [FOREX] Scraping ZuluTrade Leaders...")
    traders = []

    url = "https://www.zulutrade.com/traders"
    resp = stealth_get(url)
    text = get_text(resp)
    status = get_status(resp)
    print(f"    Status: {status}, Length: {len(text)} chars")

    if len(text) > 500:
        # Look for trader IDs and profiles
        trader_ids = re.findall(r'/trader/(\d+)', text)
        unique_ids = list(set(trader_ids))
        print(f"    Found {len(unique_ids)} unique trader IDs")

        # Try to parse trader names and stats too
        for tid in unique_ids[:100]:
            traders.append({
                "platform": "ZuluTrade",
                "asset_class": "FOREX",
                "trader_id": tid,
                "name": f"ZT-Leader-{tid}",
                "profile_url": f"https://www.zulutrade.com/trader/{tid}",
                "has_trade_history": True,
                "data_quality": "good",
                "source": "stealth_scrape",
            })

        # Try embedded JSON data
        next_data = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', text, re.DOTALL)
        if next_data:
            try:
                state = json.loads(next_data.group(1))
                leader_data = state.get("leaders", state.get("traders", []))
                if isinstance(leader_data, list):
                    for t in leader_data:
                        tid = str(t.get("id", t.get("providerId", "")))
                        if tid and tid not in [tr["trader_id"] for tr in traders]:
                            traders.append({
                                "platform": "ZuluTrade",
                                "asset_class": "FOREX",
                                "trader_id": tid,
                                "name": t.get("name", t.get("nickName", f"ZT-{tid}")),
                                "roi_pct": float(t.get("performance", t.get("pnl", 0))),
                                "copiers": int(t.get("followers", 0)),
                                "profile_url": f"https://www.zulutrade.com/trader/{tid}",
                                "data_quality": "excellent",
                                "source": "stealth_json",
                            })
            except json.JSONDecodeError:
                pass

    print(f"    [OK] ZuluTrade: {len(traders)} forex leaders")
    return traders


# ============================================================
# SCRAPE: eToro Popular Investors (Forex + Multi-asset)
# ============================================================

def scrape_etoro_investors():
    """Scrape eToro Popular Investors with stealth."""
    print("\n  [FOREX] Scraping eToro Popular Investors...")
    traders = []

    url = "https://www.etoro.com/discover/people"
    resp = stealth_get(url)
    text = get_text(resp)
    status = get_status(resp)
    print(f"    Status: {status}, Length: {len(text)} chars")

    if len(text) > 500:
        # eToro often uses Angular/React with embedded state
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', text, re.DOTALL)
        if state_match:
            try:
                state = json.loads(state_match.group(1))
                investors = state.get("popularInvestors", state.get("users", []))
                if isinstance(investors, list):
                    for inv in investors:
                        username = inv.get("userName", inv.get("username", ""))
                        if username:
                            traders.append({
                                "platform": "eToro",
                                "asset_class": "FOREX",
                                "trader_id": username,
                                "name": inv.get("fullName", inv.get("displayName", username)),
                                "gain_pct": float(inv.get("gain", 0)),
                                "risk_score": inv.get("riskScore"),
                                "copiers": int(inv.get("copiers", 0)),
                                "profile_url": f"https://www.etoro.com/people/{username}",
                                "data_quality": "excellent",
                                "source": "stealth_json",
                            })
            except json.JSONDecodeError:
                pass

        # Regex fallback: find usernames in the page
        if not traders:
            usernames = re.findall(r'/people/([a-zA-Z0-9_-]{3,30})', text)
            unique_users = list(set(usernames))
            print(f"    Found {len(unique_users)} unique usernames from HTML")
            for username in unique_users[:100]:
                if username not in ("discover", "markets", "portfolio", "settings", "about"):
                    traders.append({
                        "platform": "eToro",
                        "asset_class": "FOREX",
                        "trader_id": username,
                        "name": username,
                        "profile_url": f"https://www.etoro.com/people/{username}",
                        "data_quality": "medium",
                        "source": "html_regex",
                    })

    print(f"    [OK] eToro: {len(traders)} investors")
    return traders


# ============================================================
# SCRAPE: Myfxbook Top Trading Systems
# ============================================================

def scrape_myfxbook_systems():
    """Scrape Myfxbook verified trading systems (forex)."""
    print("\n  [FOREX] Scraping Myfxbook Trading Systems...")
    traders = []

    # Multiple pages for more coverage
    for page in range(1, 6):  # 5 pages
        url = f"https://www.myfxbook.com/systems?page={page}"
        print(f"    Page {page}...")
        resp = stealth_get(url)
        text = get_text(resp)
        status = get_status(resp)

        if len(text) < 500:
            continue

        # Parse system IDs & names
        system_ids = re.findall(r'/system/(\d+)', text)
        system_names = re.findall(r'class="col-name[^"]*"[^>]*>[\s]*<a[^>]*>([^<]+)</a>', text)
        if not system_names:
            system_names = re.findall(r'system/\d+[^"]*"[^>]*>([^<]{2,40})<', text)

        unique_ids = list(set(system_ids))
        print(f"    Found {len(unique_ids)} system IDs")

        for i, sid in enumerate(unique_ids):
            name = system_names[i] if i < len(system_names) else f"MFX-System-{sid}"
            traders.append({
                "platform": "Myfxbook",
                "asset_class": "FOREX",
                "trader_id": sid,
                "name": name.strip(),
                "profile_url": f"https://www.myfxbook.com/system/{sid}",
                "has_trade_history": True,
                "data_quality": "excellent",
                "verified_by": "Myfxbook",
                "source": "stealth_scrape",
            })

        time.sleep(1)

    # Deduplicate
    seen = set()
    unique_traders = []
    for t in traders:
        if t["trader_id"] not in seen:
            seen.add(t["trader_id"])
            unique_traders.append(t)

    print(f"    [OK] Myfxbook: {len(unique_traders)} verified systems")
    return unique_traders


# ============================================================
# Main
# ============================================================

def run_stealth_scrape():
    """Run all stealth scrapers."""
    print("=" * 70)
    print("  STEALTH COPYTRADER SCRAPER (scrapling)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Scrapling available: {HAS_SCRAPLING}")
    print("=" * 70)

    all_traders = []

    # CRYPTO
    crypto_scrapers = [
        ("Bitget", scrape_bitget_leaderboard),
        ("Bybit", scrape_bybit_leaderboard),
    ]
    for name, fn in crypto_scrapers:
        try:
            traders = fn()
            all_traders.extend(traders)
        except Exception as e:
            print(f"    [ERROR] {name}: {e}")

    # FOREX
    forex_scrapers = [
        ("ZuluTrade", scrape_zulutrade_leaders),
        ("eToro", scrape_etoro_investors),
        ("Myfxbook", scrape_myfxbook_systems),
    ]
    for name, fn in forex_scrapers:
        try:
            traders = fn()
            all_traders.extend(traders)
        except Exception as e:
            print(f"    [ERROR] {name}: {e}")

    # Merge with existing database
    existing_path = DATA_DIR / "copytrader_database.json"
    existing_data = {}
    if existing_path.exists():
        with open(existing_path) as f:
            existing_data = json.load(f)

    existing_traders = existing_data.get("crypto_traders", []) + existing_data.get("forex_traders", [])
    existing_keys = {(t.get("platform", ""), t.get("trader_id", "")) for t in existing_traders}

    new_traders = []
    for t in all_traders:
        key = (t.get("platform", ""), t.get("trader_id", ""))
        if key not in existing_keys:
            new_traders.append(t)
            existing_keys.add(key)

    all_combined = existing_traders + new_traders

    crypto = [t for t in all_combined if t.get("asset_class") == "CRYPTO"]
    forex = [t for t in all_combined if t.get("asset_class") == "FOREX"]

    by_platform = defaultdict(lambda: {"count": 0, "crypto": 0, "forex": 0})
    for t in all_combined:
        p = t.get("platform", "Unknown")
        by_platform[p]["count"] += 1
        if t.get("asset_class") == "CRYPTO":
            by_platform[p]["crypto"] += 1
        elif t.get("asset_class") == "FOREX":
            by_platform[p]["forex"] += 1

    # Save updated database
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_unique": len(all_combined),
        "crypto_total": len(crypto),
        "forex_total": len(forex),
        "new_from_stealth": len(new_traders),
        "by_platform": {k: v for k, v in sorted(by_platform.items(), key=lambda x: x[1]["count"], reverse=True)},
        "crypto_traders": crypto,
        "forex_traders": forex,
    }

    with open(existing_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 70)
    print("  STEALTH SCRAPE SUMMARY")
    print("=" * 70)
    print(f"  New traders found: {len(new_traders)}")
    print(f"  Total database: {len(all_combined)}")
    print(f"    Crypto: {len(crypto)}")
    print(f"    Forex: {len(forex)}")
    print()
    print(f"  {'Platform':25s} {'Total':>6s} {'Crypto':>7s} {'Forex':>6s}")
    print("  " + "-" * 50)
    for p, stats in sorted(by_platform.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"  {p:25s} {stats['count']:6d} {stats['crypto']:7d} {stats['forex']:6d}")

    print(f"\n  [OK] Updated database -> {existing_path}")
    print("=" * 70)

    return output


if __name__ == "__main__":
    run_stealth_scrape()

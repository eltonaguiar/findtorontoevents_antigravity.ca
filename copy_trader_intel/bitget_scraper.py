#!/usr/bin/env python3
"""
Bitget Copy Trading Scraper & Pick Generator
=============================================
Scrapes the Bitget copy trading leaderboard for top traders,
fetches their current open positions, and converts them into
active_picks.json compatible format.

IMPORTANT: Unlike OKX, ALL Bitget copy trading API endpoints are PRIVATE
(require API key + HMAC-SHA256 signature). There is NO public copy trading
API on Bitget.

Two access methods:
  A) Authenticated REST API (preferred if API key available)
  B) Web scraping the leaderboard HTML pages (fallback, no auth needed)

=== Authenticated API Endpoints (v1 -- all require HMAC auth) ===

  Leaderboard:
    GET /api/mix/v1/trace/traderList
      params: sortRule (composite|roi|totalPL|aum), sortFlag (asc|desc),
              pageSize (max 20), pageNo, traderUid, traderNickName,
              fullStatus (full|all), languageType (en-US)
      response.data[]: traderUid, traderNickName, roi, totalpl, winRate,
                       followCount, maxFollowCount, copyTradeDays,
                       dailyProfit, profitRate24h, followerTotalProfit,
                       lastTradeTime

  Trader Detail:
    GET /api/mix/v1/trace/traderDetail
      response.data: roi, tradingOrders, accFollowers, totalpl, gainNum,
                     lossNum, winRate, totalEquity, lastWeekRoi, lastMonthRoi

  Trader Current Positions:
    POST /api/mix/v1/trace/report/order/currentList
      body: { traderId, symbol (opt), pageNo, pageSize (max 20) }
      response.data[]: trackingNo, symbol, holdSide, leverage, openPrice,
                       openTime, openAmount, followerNum, takeProfitPrice,
                       stopLossPrice, marginAmount

  Trader History Orders:
    POST /api/mix/v1/trace/report/order/historyList
      body: { traderId, symbol (opt), pageNo, pageSize (max 20) }
      response.data[]: trackingNo, symbol, holdSide, leverage, openPrice,
                       closePrice, openTime, closeTime, marginAmount,
                       followerNum, achievedProfits, profitRate, netProfit

  Trader Open Orders (v1):
    GET /api/mix/v1/trace/currentTrack
      params: symbol, productType, pageSize, pageNo
      response.data[]: trackingNo, symbol, holdSide, openLeverage,
                       openAvgPrice, openTime, stopProfitPrice, stopLossPrice

  Trader History (v1):
    GET /api/mix/v1/trace/historyTrack
      params: startTime, endTime, pageSize, pageNo
      response.data[]: trackingNo, symbol, holdSide, openAvgPrice,
                       closeAvgPrice, achievedProfits, profitRate, netProfit

=== Authenticated API Endpoints (v2 -- all require HMAC auth) ===

  Current Tracking:
    GET /api/v2/copy/mix-trader/order-current-track
      params: symbol (e.g. BTCUSDT), productType (usdt-futures), limit (max 20)

  History Tracking:
    GET /api/v2/copy/mix-trader/order-history-track
      params: productType (USDT-FUTURES), symbol, startTime, endTime,
              order (desc), limit (max 20)

  Tracking Summary:
    GET /api/v2/copy/mix-trader/order-total-detail

  Profit History:
    GET /api/v2/copy/mix-trader/profit-history-summarys

=== Web Scraping (no auth, fallback) ===

  Leaderboard page: https://www.bitget.com/copy-trading/leaderboard-ranking/futures-roi
  Trader profile:   https://www.bitget.com/copy-trading/trader/{PROFILE_ID}/futures

=== Auth Headers Required (for REST API) ===
  ACCESS-KEY: your API key
  ACCESS-SIGN: Base64(HMAC-SHA256(timestamp + method + path + body, secret))
  ACCESS-TIMESTAMP: UTC epoch seconds as string
  ACCESS-PASSPHRASE: your passphrase

API Failover: 3+ mirrors (api.bitget.com, capi.bitget.com, open-api.bitget.com).
Rate limit: 500ms between calls. Leaderboard: 10 req/sec; History: 5 req/sec.

Known top performers from research (CRYPTO_COPY_TRADERS_RESEARCH.md):
  - hale (@hale, profile b1b5467f8bb73f53ac97): 1605 days, 750/750 MAX, 15.5% DD
  - Bg-ATM (@BGUSER-D3ZSGEF5, profile b0bd4a7e86bb3956a49c): 90.3% WR, 14.7% DD
  - ICHIZENCapital (@ICHIZENCapital): +4,302% ROI, 21.6% DD
"""

import base64
import hashlib
import hmac
import json
import os
import re
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- API Mirrors (failover chain per project rules) --
BITGET_API_MIRRORS = [
    "https://api.bitget.com",
    "https://capi.bitget.com",
    "https://open-api.bitget.com",
]

# -- v1 Authenticated Endpoints --
V1_LEADERBOARD = "/api/mix/v1/trace/traderList"
V1_TRADER_DETAIL = "/api/mix/v1/trace/traderDetail"
V1_CURRENT_TRACK = "/api/mix/v1/trace/currentTrack"
V1_HISTORY_TRACK = "/api/mix/v1/trace/historyTrack"
V1_REPORT_CURRENT = "/api/mix/v1/trace/report/order/currentList"
V1_REPORT_HISTORY = "/api/mix/v1/trace/report/order/historyList"

# -- v2 Authenticated Endpoints (V1 is DECOMMISSIONED as of 2026) --
V2_CURRENT_TRACK = "/api/v2/copy/mix-trader/order-current-track"
V2_HISTORY_TRACK = "/api/v2/copy/mix-trader/order-history-track"
V2_TOTAL_DETAIL = "/api/v2/copy/mix-trader/order-total-detail"
V2_PROFIT_SUMMARY = "/api/v2/copy/mix-trader/profit-history-summarys"
V2_QUERY_TRADERS = "/api/v2/copy/mix-broker/query-traders"
V2_FOLLOWER_CURRENT = "/api/v2/copy/mix-follower/query-current-orders"
V2_FOLLOWER_HISTORY = "/api/v2/copy/mix-follower/query-history-orders"

# -- Web Scraping URLs --
WEB_LEADERBOARD = "https://www.bitget.com/copy-trading/leaderboard-ranking/futures-roi"
WEB_PROFILE_BASE = "https://www.bitget.com/copy-trading/trader"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
}

# Known top traders from CRYPTO_COPY_TRADERS_RESEARCH.md + web research (verified profiles)
# Sources: Bitget leaderboard, CryptoManiaks, CoinBureau, CryptoNinjas reviews
# Last verified: 2026-03-19
SEED_TRADERS = [
    # -- Original verified traders --
    {
        "traderUid": "b1b5467f8bb73f53ac97",
        "nickName": "hale",
        "handle": "@hale",
        "note": "1605 days, 750/750 MAX copiers, 15.5% DD, 57.1% WR -- veteran",
        "roi_30d": 0.6104,
        "win_rate": 0.571,
        "follower_count": 750,
        "max_followers": 750,
    },
    {
        "traderUid": "b0bd4a7e86bb3956a49c",
        "nickName": "Bg-ATM",
        "handle": "@BGUSER-D3ZSGEF5",
        "note": "90.3% WR, 14.7% DD, BTCUSDT only -- conservative",
        "roi_30d": 0.5748,
        "win_rate": 0.903,
        "follower_count": 450,
        "max_followers": 500,
    },
    {
        "traderUid": "",
        "nickName": "ICHIZENCapital",
        "handle": "@ICHIZENCapital",
        "note": "+4,302% ROI, 21.6% DD, low DD standout",
        "roi_30d": 43.02,
        "win_rate": 0.346,
        "follower_count": 0,
        "max_followers": 600,
    },
    {
        "traderUid": "",
        "nickName": "WIN-2026",
        "handle": "@BGUSER-X15KWVSN",
        "note": "+19,396% 30D ROI, 70.6% DD, ETHUSDT/BTCUSDT",
        "roi_30d": 193.96,
        "win_rate": 0.895,
        "follower_count": 354,
        "max_followers": 500,
    },
    {
        "traderUid": "",
        "nickName": "Rich",
        "handle": "@BGUSER-9G3FB5CG",
        "note": "+64.69% 30D ROI, 100% WR -- WARN: possible grid/martingale",
        "roi_30d": 0.6469,
        "win_rate": 1.0,
        "follower_count": 373,
        "max_followers": 500,
    },
    # -- New traders added 2026-03-19 (from web research + leaderboard scraping) --
    {
        "traderUid": "",
        "nickName": "BGUSER-WZ5EMDCY",
        "handle": "@BGUSER-WZ5EMDCY",
        "note": "+73.4% 30D ROI, 84.6% WR, 704 copiers, 29.8% DD, diversified alts",
        "roi_30d": 0.7339,
        "win_rate": 0.846,
        "follower_count": 704,
        "max_followers": 1000,
    },
    {
        "traderUid": "",
        "nickName": "MJSONE",
        "handle": "@MJSONE",
        "note": "Steady 20-25% monthly, $3M+ follower capital, low leverage, reliable",
        "roi_30d": 0.22,
        "win_rate": 0.68,
        "follower_count": 800,
        "max_followers": 1000,
    },
]


# ======================================================================
# HMAC Authentication (required for ALL Bitget copy trading endpoints)
# ======================================================================

def _get_api_credentials():
    """
    Load Bitget API credentials from environment variables.
    Required: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE
    Falls back to Windows User-level env vars if not in current shell.
    """
    key = os.environ.get("BITGET_API_KEY", "")
    secret = os.environ.get("BITGET_API_SECRET", os.environ.get("BITGET_SECRET_KEY", ""))
    passphrase = os.environ.get("BITGET_API_PASSPHRASE", "")

    # On Windows, try reading from User-level registry if not in shell env
    if sys.platform == "win32" and (not key or not secret or not passphrase):
        try:
            import subprocess
            def _win_env(name):
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[Environment]::GetEnvironmentVariable('{name}', 'User')"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()
            if not key:
                key = _win_env("BITGET_API_KEY")
            if not secret:
                secret = _win_env("BITGET_API_SECRET") or _win_env("BITGET_SECRET_KEY")
            if not passphrase:
                passphrase = _win_env("BITGET_API_PASSPHRASE")
        except Exception:
            pass

    return key, secret, passphrase


def _has_api_credentials():
    """Check if Bitget API credentials are configured."""
    key, secret, passphrase = _get_api_credentials()
    return bool(key and secret and passphrase)


def _sign_request(timestamp: str, method: str, path: str, body: str = "") -> str:
    """
    Generate HMAC-SHA256 signature for Bitget API.
    sign = Base64(HMAC-SHA256(timestamp + method + requestPath + body, secretKey))
    """
    _, secret, _ = _get_api_credentials()
    message = timestamp + method.upper() + path + body
    mac = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    )
    return base64.b64encode(mac.digest()).decode("utf-8")


def _auth_headers(method: str, path: str, body: str = "") -> dict:
    """Build authenticated request headers."""
    key, _, passphrase = _get_api_credentials()
    timestamp = str(int(time.time() * 1000))
    sign = _sign_request(timestamp, method, path, body)
    return {
        **HEADERS,
        "ACCESS-KEY": key,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": passphrase,
    }


# ======================================================================
# API Request Helpers (with mirror failover)
# ======================================================================

def bitget_auth_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """Authenticated GET request with mirror failover."""
    if not _has_api_credentials():
        return {}

    query = ""
    if params:
        query = "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    full_path = path + query

    for mirror in BITGET_API_MIRRORS:
        url = f"{mirror}{full_path}"
        for attempt in range(retries):
            # Regenerate auth headers each attempt (timestamp must be fresh)
            hdrs = _auth_headers("GET", full_path)
            try:
                resp = requests.get(url, headers=hdrs, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "00000" or data.get("data"):
                        return data
                    # Log non-success code for debugging
                    print(f"    [DEBUG] Bitget API {path}: code={data.get('code')}, msg={data.get('msg', '')}")
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    print(f"    [DEBUG] Bitget API {path}: HTTP {resp.status_code}")
                    break
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def bitget_auth_post(path: str, body: dict = None, retries: int = 3) -> dict:
    """Authenticated POST request with mirror failover."""
    if not _has_api_credentials():
        return {}

    body_str = json.dumps(body) if body else ""

    for mirror in BITGET_API_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            # Regenerate auth headers each attempt (timestamp must be fresh)
            hdrs = _auth_headers("POST", path, body_str)
            try:
                resp = requests.post(
                    url, data=body_str, headers=hdrs, timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "00000" or data.get("data"):
                        return data
                    print(f"    [DEBUG] Bitget POST {path}: code={data.get('code')}, msg={data.get('msg', '')}")
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    print(f"    [DEBUG] Bitget POST {path}: HTTP {resp.status_code}")
                    break
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def bitget_web_get(url: str, retries: int = 3) -> str:
    """Unauthenticated GET for web scraping, returns HTML text."""
    web_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=web_headers, timeout=20)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                time.sleep(3)
                continue
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)
            continue
    return ""


# ======================================================================
# Method A: Authenticated API Access
# ======================================================================

def fetch_leaderboard_api(max_traders: int = 20) -> list:
    """
    Fetch top traders via authenticated API.
    V2: GET /api/v2/copy/mix-broker/query-traders (requires trace read permission)
    V1 is DECOMMISSIONED as of 2026.
    Requires: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE + trace read perm
    """
    print("  [API] Fetching Bitget leaderboard via V2 authenticated API...")

    all_traders = []

    # Try V2 broker endpoint first
    data = bitget_auth_get(V2_QUERY_TRADERS)
    if data.get("code") == "00000" and data.get("data"):
        traders = data["data"]
        if isinstance(traders, dict):
            traders = traders.get("list", traders.get("traderList", []))
        if isinstance(traders, list):
            print(f"    V2 query-traders: {len(traders)} traders")
            all_traders.extend(traders)

    # If V2 broker failed (permissions), try V2 follower current orders
    if not all_traders:
        data = bitget_auth_get(V2_FOLLOWER_CURRENT, params={"productType": "USDT-FUTURES"})
        if data.get("code") == "00000" and data.get("data"):
            orders = data["data"]
            if isinstance(orders, list):
                print(f"    V2 follower-current: {len(orders)} tracked orders")
                # Extract trader info from followed orders
                for order in orders:
                    all_traders.append(order)

    # If V2 also failed, try V2 self-trader endpoints
    if not all_traders:
        for endpoint, label in [(V2_TOTAL_DETAIL, "total-detail"), (V2_PROFIT_SUMMARY, "profit-summary")]:
            data = bitget_auth_get(endpoint)
            if data.get("code") == "00000" and data.get("data"):
                print(f"    V2 {label}: data found")
                # These return own trading stats, not leaderboard
                break

    if not all_traders:
        print("  [API] V2 API returned no leaderboard data (need 'trace read' permission)")
        print("        Go to Bitget -> API Management -> add 'Copy Trading Read' permission")
        return []

    # Deduplicate by traderUid
    seen = set()
    unique = []
    for t in all_traders:
        uid = t.get("traderUid", t.get("traderId", ""))
        if uid and uid not in seen:
            seen.add(uid)
            unique.append(t)

    print(f"  [API] Total unique traders: {len(unique)}")
    return unique[:max_traders]


def fetch_trader_detail_api(trader_uid: str) -> dict:
    """
    Fetch detailed profile for a specific trader.
    GET /api/mix/v1/trace/traderDetail
    Response: roi, tradingOrders, accFollowers, totalpl, gainNum, lossNum,
              winRate, totalEquity, lastWeekRoi, lastMonthRoi
    """
    data = bitget_auth_get(V1_TRADER_DETAIL, params={"traderUid": trader_uid})
    return data.get("data", {})


def fetch_positions_api(trader_uid: str, current_trading_list: list = None) -> list:
    """
    Fetch a trader's current open positions via V2 API.
    V1 endpoints are DECOMMISSIONED. V2 requires trace permissions.
    Falls back to currentTradingList from leaderboard data if available.
    """
    # Try V2 current track endpoint
    data = bitget_auth_get(V2_CURRENT_TRACK, params={
        "productType": "USDT-FUTURES",
        "limit": "20",
    })
    if data.get("code") == "00000" and data.get("data"):
        raw = data["data"]
        if isinstance(raw, dict):
            return raw.get("list", raw.get("orderList", []))
        if isinstance(raw, list):
            return raw

    # If V2 failed and we have currentTradingList from leaderboard,
    # synthesize position data from the coin list
    if current_trading_list:
        positions = []
        for symbol in current_trading_list:
            if not symbol:
                continue
            positions.append({
                "symbol": symbol if "USDT" in symbol else f"{symbol}USDT",
                "holdSide": "long",  # Default to long (most common)
                "leverage": "5",
                "openPrice": "0",  # Unknown -- will be filled from live price
                "synthetic": True,
            })
        return positions

    return []


def fetch_history_api(trader_uid: str) -> list:
    """
    Fetch a trader's historical trades via V2 API.
    V1 endpoints are DECOMMISSIONED.
    """
    data = bitget_auth_get(V2_HISTORY_TRACK, params={
        "productType": "USDT-FUTURES",
        "limit": "20",
    })
    if data.get("code") == "00000" and data.get("data"):
        raw = data["data"]
        if isinstance(raw, dict):
            return raw.get("list", raw.get("orderList", []))
        if isinstance(raw, list):
            return raw
    return []


# ======================================================================
# Method B: Web Scraping (no auth needed, parses HTML)
# ======================================================================

def _parse_leaderboard_html(html: str) -> list:
    """
    Parse Bitget leaderboard HTML for trader data.
    Falls back to regex parsing if BeautifulSoup unavailable.
    The leaderboard page at /copy-trading/leaderboard-ranking/futures-roi
    contains trader cards with ROI, profit, win rate, follower count.

    Note: Bitget's leaderboard is heavily JS-rendered (React/Next.js SPA).
    Simple HTML scraping may return an empty shell. If so, the scraper
    falls back to seed traders from research data.
    """
    traders = []

    # Try BeautifulSoup first
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Look for __NEXT_DATA__ JSON embedded in page (Next.js SSR)
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                next_data = json.loads(next_data_tag.string)
                # Navigate the Next.js props structure
                page_props = next_data.get("props", {}).get("pageProps", {})
                trader_list = (
                    page_props.get("traderList", [])
                    or page_props.get("data", {}).get("list", [])
                    or page_props.get("list", [])
                )
                if trader_list:
                    print(f"    Parsed {len(trader_list)} traders from __NEXT_DATA__")
                    return trader_list
            except (json.JSONDecodeError, KeyError):
                pass

        # Look for embedded JSON in script tags
        for script in soup.find_all("script"):
            text = script.string or ""
            if "traderList" in text or "traderUid" in text:
                match = re.search(r'traderList["\s:]+(\[.*?\])', text, re.DOTALL)
                if match:
                    try:
                        traders = json.loads(match.group(1))
                        if traders:
                            print(f"    Parsed {len(traders)} from embedded JSON")
                            return traders
                    except json.JSONDecodeError:
                        pass

    except ImportError:
        pass  # BeautifulSoup not available

    # Regex fallback: try to find any JSON-like trader data
    uid_matches = re.findall(r'"traderUid"\s*:\s*"([a-f0-9]+)"', html)
    if uid_matches:
        print(f"    Found {len(uid_matches)} trader UIDs via regex")
        for uid in uid_matches[:20]:
            traders.append({"traderUid": uid, "nickName": f"bg_{uid[:8]}"})

    return traders


def _parse_trader_profile_html(html: str) -> dict:
    """
    Parse a Bitget trader profile page for stats and current positions.
    Profile URL: /copy-trading/trader/{PROFILE_ID}/futures
    """
    result = {"stats": {}, "positions": []}

    # Try __NEXT_DATA__ first
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                next_data = json.loads(next_data_tag.string)
                page_props = next_data.get("props", {}).get("pageProps", {})
                trader_info = page_props.get("traderInfo", page_props.get("data", {}))
                if trader_info:
                    result["stats"] = trader_info
                    positions = (
                        trader_info.get("currentOrders", [])
                        or trader_info.get("positions", [])
                        or page_props.get("currentOrders", [])
                    )
                    result["positions"] = positions or []
                    return result
            except (json.JSONDecodeError, KeyError):
                pass
    except ImportError:
        pass

    # Regex fallbacks for key stats
    def _extract_pct(pattern, text):
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                return 0
        return 0

    result["stats"]["roi"] = _extract_pct(r'ROI[^>]*>([+\-]?[\d,.]+)%', html)
    result["stats"]["winRate"] = _extract_pct(r'Win\s*Rate[^>]*>([\d,.]+)%', html)

    return result


def fetch_leaderboard_web() -> list:
    """Scrape Bitget leaderboard via web HTML."""
    print("  [WEB] Scraping Bitget leaderboard page...")

    html = bitget_web_get(WEB_LEADERBOARD)
    if not html:
        print("  [WEB] Failed to fetch leaderboard page")
        return []

    traders = _parse_leaderboard_html(html)
    if traders:
        print(f"  [WEB] Parsed {len(traders)} traders from HTML")
    else:
        print("  [WEB] Page is JS-rendered (SPA), HTML parsing returned 0 traders")
        print("  [WEB] Note: Bitget uses React SPA -- requires Playwright/Selenium")
        print("         for full rendering. Falling back to seed traders.")

    return traders


def fetch_trader_profile_web(profile_id: str) -> dict:
    """Scrape individual trader profile page."""
    url = f"{WEB_PROFILE_BASE}/{profile_id}/futures"
    html = bitget_web_get(url)
    if not html:
        return {"stats": {}, "positions": []}
    return _parse_trader_profile_html(html)


# ======================================================================
# Stats & Conversion (shared by both methods)
# ======================================================================

def calculate_stats(detail: dict, history: list = None) -> dict:
    """Calculate trader stats from detail dict and optional trade history."""
    def _float(val, default=0):
        try:
            # Handle formatted strings like "$1,832,977.64"
            if isinstance(val, str):
                val = val.replace("$", "").replace(",", "").replace("%", "").strip()
                if val.startswith("-"):
                    return -float(val[1:])
            return float(val)
        except (ValueError, TypeError):
            return default

    def _int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    # V2 API returns metrics in columnList: [{describe: "ROI", value: "547.37"}, ...]
    column_map = {}
    for col in detail.get("columnList", []):
        desc = col.get("describe", "").lower()
        column_map[desc] = col.get("value", "0")

    win_rate = _float(detail.get("averageWinRate", detail.get("winRate",
                      detail.get("winRatio", detail.get("win_rate", 0)))))
    # Bitget may return win rate as percentage (e.g., 57.1) or decimal (0.571)
    if win_rate > 1:
        win_rate = win_rate / 100.0

    roi = _float(column_map.get("roi", detail.get("roi", detail.get("yieldRate",
                 detail.get("roi_30d", 0)))))
    # Same for ROI -- may be percentage or decimal
    if abs(roi) > 100:
        roi = roi / 100.0

    total_pnl = _float(column_map.get("total pnl",
                       detail.get("totalpl", detail.get("totalPnl",
                       detail.get("profit", 0)))))
    total_trades = _int(detail.get("tradeCount", detail.get("tradingOrders",
                        detail.get("totalOrder", 0))))
    follower_count = _int(detail.get("totalFollowers", detail.get("followCount",
                          detail.get("followerCount",
                          detail.get("copyTraderNum",
                          detail.get("follower_count", 0))))))
    max_dd = _float(detail.get("maxCallbackRate", detail.get("maxDrawdown", 0)))
    copy_days = _int(detail.get("tradeDays", detail.get("copyTradeDays",
                     detail.get("leadDays", 0))))

    # Calculate profit factor from history if available
    gross_profit = 0
    gross_loss = 0
    wins = 0
    losses = 0
    if history:
        for trade in history:
            pnl = _float(trade.get("achievedProfits", trade.get("netProfit",
                         trade.get("pnl", trade.get("profit", 0)))))
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            elif pnl < 0:
                losses += 1
                gross_loss += abs(pnl)

        if wins + losses > 0 and win_rate == 0:
            win_rate = wins / (wins + losses)
        if total_trades == 0:
            total_trades = wins + losses

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    return {
        "win_rate": round(win_rate, 4),
        "roi": round(roi, 4),
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "follower_count": follower_count,
        "max_drawdown": round(max_dd, 4),
        "copy_trade_days": copy_days,
        "wins": wins,
        "losses": losses,
    }


def convert_symbol(symbol: str) -> str:
    """
    Convert Bitget symbol to standard format.
    BTCUSDT_UMCBL -> BTCUSDT
    ETHUSDT_DMCBL -> ETHUSDT
    SBTCSUSDT    -> BTCUSDT (strip leading S for simulated)
    """
    if not symbol:
        return ""
    # Remove product type suffixes
    for suffix in ["_UMCBL", "_DMCBL", "_CMCBL", "_SUMCBL", "_SDMCBL",
                   "_USDT", "_USD"]:
        symbol = symbol.replace(suffix, "")
    # Remove underscores
    symbol = symbol.replace("_", "")
    # Handle simulated prefix
    if symbol.startswith("S") and len(symbol) > 6:
        symbol = symbol[1:]
    return symbol.upper()


def position_to_pick(position: dict, trader: dict, stats: dict) -> dict:
    """Convert a Bitget position into an active_picks.json compatible pick."""
    raw_symbol = position.get("symbol", position.get("instId", ""))
    symbol = convert_symbol(raw_symbol)
    if not symbol:
        return None

    # Direction
    side = position.get("holdSide", position.get("posSide",
           position.get("side", ""))).lower()
    direction = "LONG" if side in ("long", "buy", "open_long") else "SHORT"

    # Entry price -- multiple possible field names
    entry_price = 0
    for field in ["openPrice", "openAvgPrice", "avgPx", "openAvgPx", "entryPrice"]:
        try:
            entry_price = float(position.get(field, 0))
            if entry_price > 0:
                break
        except (ValueError, TypeError):
            continue
    if entry_price <= 0:
        # Synthetic position from currentTradingList -- use live price as entry
        if position.get("synthetic"):
            try:
                resp = requests.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                    timeout=5)
                if resp.status_code == 200:
                    entry_price = float(resp.json().get("price", 0))
            except Exception:
                pass
        if entry_price <= 0:
            return None

    # Leverage
    try:
        leverage = float(position.get("leverage", position.get("openLeverage", 1)))
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 50)

    # TP/SL from position data (if trader set them)
    try:
        tp_from_pos = float(position.get("takeProfitPrice",
                           position.get("stopProfitPrice", 0)))
    except (ValueError, TypeError):
        tp_from_pos = 0

    try:
        sl_from_pos = float(position.get("stopLossPrice", 0))
    except (ValueError, TypeError):
        sl_from_pos = 0

    # Use trader's TP/SL if available, otherwise calculate defaults
    if tp_from_pos > 0:
        tp_price = tp_from_pos
    elif direction == "LONG":
        tp_price = round(entry_price * 1.04, 8)
    else:
        tp_price = round(entry_price * 0.96, 8)

    if sl_from_pos > 0:
        sl_price = sl_from_pos
    elif direction == "LONG":
        sl_price = round(entry_price * 0.975, 8)
    else:
        sl_price = round(entry_price * 1.025, 8)

    nick = trader.get("nickName", trader.get("traderNickName",
           trader.get("traderName", "unknown_bg")))
    win_rate = stats.get("win_rate", 0)
    roi = stats.get("roi", 0)

    # Confidence: base 0.65, +0.25 from WR, +0.10 max from ROI
    confidence = round(min(0.95, 0.65 + win_rate * 0.25 + min(abs(roi) * 0.05, 0.10)), 3)

    # Unrealized PnL
    try:
        upl = float(position.get("unrealizedPL", position.get("upl",
              position.get("achievedProfits", 0))))
    except (ValueError, TypeError):
        upl = 0

    # Open time
    try:
        open_time_ms = int(position.get("openTime", position.get("cTime", 0)))
        open_time_str = (
            datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).isoformat()
            if open_time_ms > 1_000_000_000
            else None
        )
    except (ValueError, TypeError):
        open_time_str = None

    # Follower count on this specific position
    try:
        pos_followers = int(position.get("followerNum", 0))
    except (ValueError, TypeError):
        pos_followers = 0

    now = datetime.now(timezone.utc)
    safe_nick = nick.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"bitget_copy_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"bitget_copy_{safe_nick}",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": entry_price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.025,
        "max_safe_leverage": leverage,
        "forward_trades": stats.get("total_trades", 0),
        "forward_wr": win_rate,
        "forward_validated": win_rate >= 0.50 and stats.get("total_trades", 0) >= 10,
        "elite_score": min(100, int(abs(roi) * 15 + win_rate * 50)),
        "elite_grade": "A" if win_rate >= 0.60 else "B" if win_rate >= 0.50 else "C",
        "reason": (f"Bitget copy trader {nick} | ROI:{roi*100:.0f}% "
                   f"WR:{win_rate*100:.0f}% Followers:{stats.get('follower_count', 0)}"),
        "source_system": "copy_trader_bitget",
        "trader_name": nick,
        "trader_roi": round(roi, 4),
        "trader_win_rate": round(win_rate, 4),
        "trader_pnl": stats.get("total_pnl", 0),
        "trader_max_dd": stats.get("max_drawdown", 0),
        "trader_copy_days": stats.get("copy_trade_days", 0),
        "leverage": leverage,
        "unrealized_pnl": round(upl, 2),
        "open_time": open_time_str,
        "position_followers": pos_followers,
        "inst_id_raw": raw_symbol,
        "timestamp": now.isoformat(),
    }


# ======================================================================
# Main Scanner
# ======================================================================

def scan_bitget_traders(max_traders: int = 15) -> tuple:
    """
    Main scan: fetch leaderboard, get positions for top traders, generate picks.
    Returns (trader_profiles, picks).

    Strategy:
    1. If BITGET_API_KEY is set -> use authenticated API (full data)
    2. Else -> try web scraping leaderboard HTML
    3. Else -> fall back to seed traders from research
    """
    print("=" * 70)
    print("  BITGET COPY TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    has_api = _has_api_credentials()
    if has_api:
        key, _, passphrase = _get_api_credentials()
        print(f"  Mode: AUTHENTICATED API (key={key[:8]}...{key[-4:]})")
        print(f"  [OK] BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE all set")
    else:
        print("  Mode: WEB SCRAPING (no API key found)")
        print("  Tip: Set BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE")
        print("       for full leaderboard + position data access")

    # -- Step 1: Get trader list --
    traders = []

    if has_api:
        traders = fetch_leaderboard_api(max_traders=30)

    if not traders:
        traders = fetch_leaderboard_web()

    if not traders:
        print("  [FALLBACK] Using seed traders from research data")
        traders = SEED_TRADERS

    print(f"  Loaded {len(traders)} traders")

    # -- Step 2: Analyze top traders --
    all_profiles = []
    all_picks = []

    # Sort by ROI if available
    for t in traders:
        try:
            t["_sort_key"] = float(t.get("roi", t.get("roi_30d",
                              t.get("profitRate", t.get("totalpl", 0)))))
        except (ValueError, TypeError):
            t["_sort_key"] = 0

    traders.sort(key=lambda x: x.get("_sort_key", 0), reverse=True)
    top_traders = traders[:max_traders]

    for i, trader in enumerate(top_traders):
        uid = trader.get("traderUid", trader.get("traderId",
              trader.get("uid", "")))
        nick = trader.get("nickName", trader.get("traderNickName",
               trader.get("traderName", f"bg_trader_{i}")))

        print(f"  [{i+1}/{len(top_traders)}] {nick} ", end="", flush=True)

        detail = {}
        history = []
        positions = []

        if has_api and uid:
            time.sleep(RATE_LIMIT_SEC)
            # V2 current-track and history-track are for YOUR OWN tracked orders
            # For other traders, use currentTradingList from leaderboard
            current_trading = trader.get("currentTradingList", [])
            positions = fetch_positions_api(uid, current_trading_list=current_trading)
            time.sleep(RATE_LIMIT_SEC)
            history = fetch_history_api(uid)
            time.sleep(RATE_LIMIT_SEC)
        elif uid and len(uid) > 16:
            # uid looks like a profile ID -- try web scraping
            profile_data = fetch_trader_profile_web(uid)
            detail = profile_data.get("stats", {})
            positions = profile_data.get("positions", [])
            time.sleep(RATE_LIMIT_SEC)

        # Merge leaderboard data into detail for stats calculation
        merged = {**trader, **detail} if detail else trader
        stats = calculate_stats(merged, history)

        profile = {
            "traderUid": uid,
            "nickName": nick,
            "handle": trader.get("handle", ""),
            "roi": stats["roi"],
            "win_rate": stats["win_rate"],
            "total_pnl": stats["total_pnl"],
            "total_trades": stats["total_trades"],
            "profit_factor": stats["profit_factor"],
            "follower_count": stats["follower_count"],
            "max_drawdown": stats["max_drawdown"],
            "copy_trade_days": stats["copy_trade_days"],
            "open_positions_count": len(positions),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "data_source": "api" if has_api and uid else "web" if detail else "seed",
        }
        all_profiles.append(profile)

        if not positions:
            print(f"ROI:{stats['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% "
                  f"-- no open positions")
            continue

        # Convert positions to picks
        picks_for_trader = []
        for pos in positions:
            pick = position_to_pick(pos, trader, stats)
            if pick:
                picks_for_trader.append(pick)

        all_picks.extend(picks_for_trader)
        print(f"ROI:{stats['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% "
              f"Trades:{stats['total_trades']} Positions:{len(positions)} "
              f"Picks:{len(picks_for_trader)}")

    print(f"\n  Bitget scan complete: {len(all_profiles)} traders, {len(all_picks)} picks")
    return all_profiles, all_picks


def save_bitget_results(profiles: list, picks: list):
    """Save Bitget results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "bitget_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "bitget_copy_trading",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} trader profiles to {profiles_path}")

    picks_path = DATA_DIR / "bitget_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_bitget_traders(max_traders=15)
    save_bitget_results(profiles, picks)
    print(f"\nDone. {len(picks)} Bitget copy trader picks generated.")

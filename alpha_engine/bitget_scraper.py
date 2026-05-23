"""
bitget_scraper.py - Bitget Copy Trading Leaderboard Scraper
============================================================
Scrapes Bitget's copy-trading leaderboard for top trader positions and
generates trading signals from high-performing traders.

IMPORTANT FINDINGS FROM RESEARCH:
  - Bitget's official copy trading API (v1 & v2) ALL require authentication
    (ACCESS-KEY, ACCESS-SIGN, ACCESS-PASSPHRASE, ACCESS-TIMESTAMP).
  - There are NO public/unauthenticated REST endpoints for trader lists,
    positions, or trade history (unlike OKX which has public endpoints).
  - The web leaderboard pages are JS-rendered (React/Next.js SSR) and
    return 403 to plain requests.

APPROACH (3-tier fallback chain):
  1. PRIMARY: Bitget's undocumented web-facing API endpoints that the
     frontend calls (discovered via browser network inspection). These
     use different base URLs and don't require API key auth.
  2. SECONDARY: Direct HTML scraping of trader profile pages using
     server-side rendered content.
  3. TERTIARY: Hardcoded known top traders from our research database
     with cached profile IDs for targeted scraping.

KNOWN BITGET API ENDPOINTS (from ccxt + browser inspection):
  Official (auth required):
    GET  /api/mix/v1/trace/traderList
    GET  /api/mix/v1/trace/currentTrack
    GET  /api/mix/v1/trace/historyTrack
    GET  /api/mix/v1/trace/traderDetail
    POST /api/v2/copy/mix-trader/order-current-track
    POST /api/v2/copy/mix-trader/order-history-track
    GET  /api/v2/copy/mix-follower/query-traders

  Web-facing (undocumented, no API key):
    POST https://www.bitget.com/v1/copy/mix-trader/traderRankList
    POST https://www.bitget.com/v1/copy/trace/traderDetailSimpleInfo
    POST https://www.bitget.com/v1/copy/trace/traderSymbolList

Output: list of pick dicts compatible with alpha_engine scanner format.
"""

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = DATA_DIR / "bitget_trader_cache.json"

# Web-facing base (undocumented endpoints the frontend uses)
BITGET_WEB_BASE = "https://www.bitget.com"

# Official API base (for authenticated endpoints if API keys available)
BITGET_API_BASE = "https://api.bitget.com"

# Leaderboard web pages (for HTML scraping fallback)
LEADERBOARD_URLS = {
    "futures_roi": "/copy-trading/leaderboard-ranking/futures-roi",
    "futures_followers": "/copy-trading/leaderboard-ranking/futures-follwers",
    "futures_elite": "/copy-trading/leaderboard-ranking/futures-new-elite-traders",
    "spot_roi": "/copy-trading/leaderboard-ranking/spot-roi",
}

# Trader profile URL pattern
TRADER_PROFILE_URL = "/copy-trading/trader/{profile_id}/futures"

# Rate limiting
RATE_LIMIT_DELAY = 1.0  # seconds between requests
REQUEST_TIMEOUT = 20

# Quality thresholds
MIN_WIN_RATE = 0.50
MIN_ROI_30D = 20.0  # percent
MAX_DRAWDOWN = 50.0  # percent
MIN_COPIERS = 10
MIN_DAYS_ACTIVE = 30

# Known top traders from research (verified data from CRYPTO_COPY_TRADERS_RESEARCH.md)
KNOWN_TOP_TRADERS = [
    {
        "name": "hale",
        "handle": "@hale",
        "profile_id": "b1b5467f8bb73f53ac97",
        "roi_30d": 61.04,
        "profit_30d": 160605,
        "max_dd": 15.5,
        "win_rate": 0.571,
        "copiers": 750,
        "max_copiers": 750,
        "days_active": 1605,
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "tier": "gold",
    },
    {
        "name": "Bg-ATM",
        "handle": "@BGUSER-D3ZSGEF5",
        "profile_id": "b0bd4a7e86bb3956a49c",
        "roi_30d": 57.48,
        "profit_30d": 117938,
        "max_dd": 14.7,
        "win_rate": 0.903,
        "copiers": 450,
        "max_copiers": 500,
        "days_active": 86,
        "symbols": ["BTCUSDT"],
        "tier": "gold",
    },
    {
        "name": "ICHIZENCapital",
        "handle": "@ICHIZENCapital",
        "profile_id": None,  # Need to discover
        "roi_30d": 4302.0,
        "profit_30d": 14928,
        "max_dd": 21.6,
        "win_rate": 0.346,
        "copiers": 0,
        "max_copiers": 600,
        "days_active": 90,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "tier": "silver",
    },
    {
        "name": "小小的躺赢",
        "handle": "@btctangying",
        "profile_id": None,
        "roi_30d": 3.1,
        "profit_30d": 74407,
        "max_dd": 9.6,
        "win_rate": 1.0,
        "copiers": 13,
        "max_copiers": 500,
        "days_active": 60,
        "symbols": ["BTCUSDT"],
        "tier": "silver",
    },
    {
        "name": "Rich",
        "handle": "@BGUSER-9G3FB5CG",
        "profile_id": None,
        "roi_30d": 64.69,
        "profit_30d": 115939,
        "max_dd": 36.9,
        "win_rate": 1.0,
        "copiers": 373,
        "max_copiers": 500,
        "days_active": 60,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "tier": "silver",
    },
]

# Common headers to mimic browser
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Origin": "https://www.bitget.com",
    "Referer": "https://www.bitget.com/copy-trading/futures",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _create_ssl_context() -> ssl.SSLContext:
    """Create a permissive SSL context."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, headers: Optional[dict] = None,
              retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """GET request returning raw response text, or None on failure."""
    hdrs = {**_HEADERS, **(headers or {})}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s from %s (attempt %d)", exc.code, url, attempt + 1)
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("Request error for %s: %s (attempt %d)", url, exc, attempt + 1)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def _http_post_json(url: str, payload: dict, headers: Optional[dict] = None,
                    retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """POST JSON request returning parsed dict, or None on failure."""
    hdrs = {**_HEADERS, "Content-Type": "application/json", **(headers or {})}
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s from POST %s (attempt %d)", exc.code, url, attempt + 1)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            logger.warning("POST error for %s: %s (attempt %d)", url, exc, attempt + 1)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def _to_float(val: Any) -> float:
    """Safely cast to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Bitget Web API (undocumented frontend endpoints)
# ---------------------------------------------------------------------------

def _fetch_leaderboard_web_api(sort_type: str = "ROI",
                                page: int = 1, page_size: int = 20) -> Optional[dict]:
    """
    Try Bitget's undocumented web-facing leaderboard API.

    These endpoints are what the React frontend calls. They may change
    without notice but don't require API key authentication.

    Discovered endpoints (from browser network inspection patterns):
      POST /v1/copy/mix-trader/traderRankList
      POST /v1/copy/trace/traderDetailSimpleInfo
      POST /v1/trigger/copy/mix-trader/traderList
    """
    # Attempt 1: /v1/copy/mix-trader/traderRankList
    endpoints = [
        f"{BITGET_WEB_BASE}/v1/copy/mix-trader/traderRankList",
        f"{BITGET_WEB_BASE}/v1/trigger/copy/mix-trader/traderList",
        f"{BITGET_WEB_BASE}/api/mix/v1/copy/traderRankList",
    ]

    payload = {
        "pageNo": page,
        "pageSize": page_size,
        "sortRule": sort_type,  # ROI, PROFIT, FOLLOWERS
        "sortFlag": "DESC",
        "productType": "USDT-FUTURES",
    }

    for endpoint in endpoints:
        logger.info("Trying Bitget web API: %s", endpoint)
        result = _http_post_json(endpoint, payload)
        if result and result.get("code") in ("00000", "0", 0, "200"):
            logger.info("Success from %s", endpoint)
            return result
        elif result:
            logger.debug("Got code=%s from %s", result.get("code"), endpoint)

    return None


def _fetch_trader_detail_web_api(trader_id: str) -> Optional[dict]:
    """
    Try to fetch trader detail via undocumented web API.
    """
    endpoints = [
        f"{BITGET_WEB_BASE}/v1/copy/trace/traderDetailSimpleInfo",
        f"{BITGET_WEB_BASE}/v1/copy/mix-trader/traderDetail",
    ]

    payload = {"traderId": trader_id}

    for endpoint in endpoints:
        result = _http_post_json(endpoint, payload)
        if result and result.get("code") in ("00000", "0", 0):
            return result
        time.sleep(0.5)

    return None


def _fetch_trader_positions_web_api(trader_id: str) -> Optional[dict]:
    """
    Try to fetch trader's current positions via undocumented web API.
    """
    endpoints = [
        f"{BITGET_WEB_BASE}/v1/copy/mix-trader/currentPositions",
        f"{BITGET_WEB_BASE}/v1/copy/trace/currentTrack",
    ]

    payload = {
        "traderId": trader_id,
        "pageNo": 1,
        "pageSize": 50,
        "productType": "USDT-FUTURES",
    }

    for endpoint in endpoints:
        result = _http_post_json(endpoint, payload)
        if result and result.get("code") in ("00000", "0", 0):
            return result
        time.sleep(0.5)

    return None


# ---------------------------------------------------------------------------
# HTML scraping fallback
# ---------------------------------------------------------------------------

def _scrape_trader_profile_html(profile_id: str) -> Dict[str, Any]:
    """
    Scrape a Bitget trader profile page for embedded data.

    URL: https://www.bitget.com/copy-trading/trader/{profile_id}/futures

    The page may contain server-side rendered HTML with trader stats
    or __NEXT_DATA__ JSON with pre-loaded data.
    """
    url = f"{BITGET_WEB_BASE}/copy-trading/trader/{profile_id}/futures"
    html = _http_get(url)

    if not html:
        logger.warning("Failed to fetch profile HTML for %s", profile_id)
        return {}

    result: Dict[str, Any] = {"profile_id": profile_id, "url": url}

    # Try to extract __NEXT_DATA__ (Next.js SSR payload)
    next_data_match = re.search(
        r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
        html, re.DOTALL
    )
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Extract trader info from pageProps
            trader_info = page_props.get("traderInfo", page_props.get("traderDetail", {}))
            if trader_info:
                result["trader_info"] = trader_info
                result["name"] = trader_info.get("nickName", trader_info.get("traderName", ""))
                result["roi_30d"] = _to_float(trader_info.get("roi30d", trader_info.get("roiRate", 0)))
                result["win_rate"] = _to_float(trader_info.get("winRate", 0))
                result["copiers"] = int(_to_float(trader_info.get("followerCount", 0)))
                result["max_dd"] = _to_float(trader_info.get("maxDrawdown", 0))
                result["profit_30d"] = _to_float(trader_info.get("profit30d", 0))
                result["trader_id"] = trader_info.get("traderId", "")

            # Extract positions if available
            positions = page_props.get("currentPositions", page_props.get("positionList", []))
            if positions:
                result["positions"] = positions

            logger.info("Extracted __NEXT_DATA__ for profile %s: name=%s",
                       profile_id, result.get("name", "?"))
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse __NEXT_DATA__ for profile %s", profile_id)

    # Fallback: regex-based HTML extraction
    # Look for ROI values
    roi_match = re.search(r'(?:roi|ROI|return)["\s:]+([+-]?\d+\.?\d*)\s*%', html)
    if roi_match:
        result["roi_30d"] = float(roi_match.group(1))

    # Look for win rate
    wr_match = re.search(r'(?:win\s*rate|winRate)["\s:]+(\d+\.?\d*)\s*%', html, re.IGNORECASE)
    if wr_match:
        result["win_rate"] = float(wr_match.group(1)) / 100.0

    # Look for copier count
    copier_match = re.search(r'(?:copier|follower)s?["\s:]+(\d+)', html, re.IGNORECASE)
    if copier_match:
        result["copiers"] = int(copier_match.group(1))

    # Look for trader name
    name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    if name_match:
        result["name"] = name_match.group(1).strip()

    return result


def _scrape_leaderboard_html() -> List[Dict[str, Any]]:
    """
    Scrape the Bitget leaderboard page for trader cards.

    The page is heavily JS-rendered so this may only get SSR content.
    """
    url = f"{BITGET_WEB_BASE}/copy-trading/leaderboard-ranking/futures-roi"
    html = _http_get(url)

    if not html:
        logger.warning("Failed to fetch leaderboard HTML")
        return []

    traders = []

    # Try __NEXT_DATA__ extraction
    next_data_match = re.search(
        r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
        html, re.DOTALL
    )
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Look for trader list in various possible keys
            for key in ("traderList", "leaderboard", "rankList", "list", "traders", "data"):
                trader_list = page_props.get(key, [])
                if isinstance(trader_list, list) and len(trader_list) > 0:
                    for t in trader_list:
                        if isinstance(t, dict):
                            traders.append({
                                "name": t.get("nickName", t.get("traderName", "Unknown")),
                                "trader_id": str(t.get("traderId", t.get("uid", ""))),
                                "profile_id": t.get("profileId", t.get("encryptUid", "")),
                                "roi_30d": _to_float(t.get("roi30d", t.get("roiRate", 0))),
                                "win_rate": _to_float(t.get("winRate", 0)),
                                "copiers": int(_to_float(t.get("followerCount", 0))),
                                "max_dd": _to_float(t.get("maxDrawdown", 0)),
                                "profit_30d": _to_float(t.get("profit30d", t.get("totalProfit", 0))),
                                "symbols": t.get("symbols", t.get("tradeSymbols", [])),
                                "days_active": int(_to_float(t.get("runningDays", t.get("leadDays", 0)))),
                                "_source": "bitget_html_ssr",
                            })
                    if traders:
                        logger.info("Extracted %d traders from __NEXT_DATA__", len(traders))
                        break
        except json.JSONDecodeError:
            pass

    # If __NEXT_DATA__ failed, try regex on rendered HTML
    if not traders:
        # Look for trader card patterns in HTML
        card_pattern = re.compile(
            r'trader/([a-f0-9]+)/futures.*?'
            r'(?:roi|ROI)["\s:]*([+-]?\d+\.?\d*)%',
            re.DOTALL | re.IGNORECASE
        )
        for match in card_pattern.finditer(html):
            traders.append({
                "profile_id": match.group(1),
                "roi_30d": float(match.group(2)),
                "_source": "bitget_html_regex",
            })

    return traders


# ---------------------------------------------------------------------------
# BitgetScraper class
# ---------------------------------------------------------------------------

class BitgetScraper:
    """
    Scrapes Bitget copy trading leaderboard for top trader signals.

    Three-tier fallback:
      1. Undocumented web API (POST endpoints the frontend uses)
      2. HTML scraping of leaderboard / profile pages
      3. Known top traders from research database

    Output format per pick:
      {
        "symbol": "BTCUSDT",
        "direction": "BUY" or "SELL",
        "confidence": 0.6-0.95,
        "source": "bitget_copy_trader",
        "trader_id": "...",
        "trader_name": "...",
        "trader_roi": ...,
        "trader_win_rate": ...,
        "entry_price": ...,
        "strategy": "bitget_copy_trader",
      }
    """

    def __init__(self):
        self.traders: List[Dict[str, Any]] = []
        self.positions: Dict[str, List[Dict]] = {}  # trader_id -> positions
        self.picks: List[Dict[str, Any]] = []
        self.data_source: str = "none"
        self._last_request_time: float = 0.0

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    # ------------------------------------------------------------------
    # Step 1: Fetch top traders (3-tier fallback)
    # ------------------------------------------------------------------

    def fetch_top_traders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch top traders from Bitget leaderboard.

        Tries in order:
          1. Undocumented web API endpoints
          2. HTML scraping of leaderboard page
          3. Known top traders from research database
        """
        traders = []

        # --- Tier 1: Web API ---
        logger.info("[BitgetScraper] Tier 1: Trying undocumented web API...")
        self._rate_limit()
        api_result = _fetch_leaderboard_web_api("ROI", page=1, page_size=limit)

        if api_result:
            raw_data = api_result.get("data", api_result.get("result", {}))
            raw_list = []
            if isinstance(raw_data, list):
                raw_list = raw_data
            elif isinstance(raw_data, dict):
                raw_list = (
                    raw_data.get("list", [])
                    or raw_data.get("traderList", [])
                    or raw_data.get("data", [])
                )

            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                traders.append(self._normalize_trader(item, source="bitget_web_api"))

            if traders:
                logger.info("[BitgetScraper] Tier 1 success: %d traders from web API", len(traders))
                self.data_source = "bitget_web_api"

        # --- Tier 2: HTML scraping ---
        if not traders:
            logger.info("[BitgetScraper] Tier 2: Trying HTML scraping...")
            self._rate_limit()
            traders = _scrape_leaderboard_html()
            if traders:
                logger.info("[BitgetScraper] Tier 2 success: %d traders from HTML", len(traders))
                self.data_source = "bitget_html_scrape"

        # --- Tier 3: Known traders from research ---
        if not traders:
            logger.info("[BitgetScraper] Tier 3: Using known top traders from research DB")
            traders = [
                {
                    "name": t["name"],
                    "handle": t["handle"],
                    "trader_id": t.get("profile_id", t["handle"]),
                    "profile_id": t.get("profile_id"),
                    "roi_30d": t["roi_30d"],
                    "profit_30d": t["profit_30d"],
                    "max_dd": t["max_dd"],
                    "win_rate": t["win_rate"],
                    "copiers": t["copiers"],
                    "max_copiers": t["max_copiers"],
                    "days_active": t["days_active"],
                    "symbols": t["symbols"],
                    "tier": t["tier"],
                    "_source": "bitget_research_db",
                }
                for t in KNOWN_TOP_TRADERS
            ]
            self.data_source = "bitget_research_db"
            logger.info("[BitgetScraper] Tier 3: Loaded %d known traders", len(traders))

        # Always enrich with known traders if they're not already in the list
        existing_names = {t.get("name", "").lower() for t in traders}
        for known in KNOWN_TOP_TRADERS:
            if known["name"].lower() not in existing_names:
                traders.append({
                    "name": known["name"],
                    "handle": known["handle"],
                    "trader_id": known.get("profile_id", known["handle"]),
                    "profile_id": known.get("profile_id"),
                    "roi_30d": known["roi_30d"],
                    "profit_30d": known["profit_30d"],
                    "max_dd": known["max_dd"],
                    "win_rate": known["win_rate"],
                    "copiers": known["copiers"],
                    "days_active": known["days_active"],
                    "symbols": known["symbols"],
                    "tier": known.get("tier", "research"),
                    "_source": "bitget_research_db",
                })

        self.traders = traders
        return traders

    def _normalize_trader(self, raw: dict, source: str = "unknown") -> Dict[str, Any]:
        """Normalize a raw trader dict from any source to standard format."""
        # Handle different field name conventions
        win_rate = _to_float(
            raw.get("winRate", raw.get("winRatio", raw.get("win_rate", 0)))
        )
        # If win_rate > 1, it's a percentage
        if win_rate > 1.0:
            win_rate = win_rate / 100.0

        roi = _to_float(
            raw.get("roi30d", raw.get("roiRate", raw.get("roi_30d",
                raw.get("totalRoi", raw.get("pnlRatio", 0)))))
        )

        return {
            "name": str(raw.get("nickName", raw.get("traderName",
                        raw.get("name", "Unknown")))),
            "trader_id": str(raw.get("traderId", raw.get("uid",
                            raw.get("trader_id", "")))),
            "profile_id": raw.get("profileId", raw.get("encryptUid",
                           raw.get("profile_id", ""))),
            "handle": raw.get("handle", ""),
            "roi_30d": roi,
            "profit_30d": _to_float(raw.get("profit30d",
                           raw.get("totalProfit", raw.get("profit_30d", 0)))),
            "max_dd": _to_float(raw.get("maxDrawdown",
                       raw.get("max_dd", raw.get("maxDrawDown", 0)))),
            "win_rate": win_rate,
            "copiers": int(_to_float(raw.get("followerCount",
                          raw.get("copyTraderNum", raw.get("copiers", 0))))),
            "days_active": int(_to_float(raw.get("runningDays",
                              raw.get("leadDays", raw.get("days_active", 0))))),
            "symbols": raw.get("symbols", raw.get("tradeSymbols", [])),
            "_source": source,
        }

    # ------------------------------------------------------------------
    # Step 2: Filter traders by quality
    # ------------------------------------------------------------------

    def filter_traders(self) -> List[Dict[str, Any]]:
        """
        Filter traders by quality thresholds:
          - Win rate >= 50%
          - 30D ROI >= 20%
          - Max drawdown <= 50%
          - Active >= 30 days
        """
        qualified = []
        for t in self.traders:
            wr = t.get("win_rate", 0)
            roi = t.get("roi_30d", 0)
            dd = t.get("max_dd", 100)
            days = t.get("days_active", 0)
            copiers = t.get("copiers", 0)

            # Gold tier traders from research DB always pass
            if t.get("tier") == "gold":
                qualified.append(t)
                continue

            # Block Bitget traders that game stats (PF > 10 = grid-trading scam)
            # They close only winners, leave losers open → PF artificially inflated
            pf = t.get("profit_factor", 1.0)
            closed_trades = t.get("closed_trades", t.get("total_trades", 0))
            if pf > 10:
                logger.info(
                    "[BitgetScraper] Blocking %s: profit_factor %.1f > 10 (gamed stats)",
                    t.get("name", t.get("trader_id", "?")), pf
                )
                continue
            if closed_trades < 10:
                logger.info(
                    "[BitgetScraper] Blocking %s: only %d closed trades (need 10+)",
                    t.get("name", t.get("trader_id", "?")), closed_trades
                )
                continue
            if days < 7:
                logger.info(
                    "[BitgetScraper] Blocking %s: only %d days active (need 7+)",
                    t.get("name", t.get("trader_id", "?")), days
                )
                continue

            if (wr >= MIN_WIN_RATE and roi >= MIN_ROI_30D
                    and dd <= MAX_DRAWDOWN and days >= MIN_DAYS_ACTIVE):
                qualified.append(t)
            elif copiers >= 100 and wr >= 0.45:
                # High-copier traders get softer filter
                qualified.append(t)

        qualified.sort(key=lambda x: x.get("roi_30d", 0), reverse=True)
        logger.info("[BitgetScraper] Filtered %d -> %d qualifying traders",
                    len(self.traders), len(qualified))
        self.traders = qualified
        return qualified

    # ------------------------------------------------------------------
    # Step 3: Fetch current positions for each trader
    # ------------------------------------------------------------------

    def fetch_positions(self) -> Dict[str, List[Dict]]:
        """
        Fetch current open positions for qualifying traders.

        Tries:
          1. Web API for position data
          2. HTML scraping of individual profile pages
          3. Use known symbols from research data as proxy
        """
        positions_by_trader: Dict[str, List[Dict]] = {}

        for trader in self.traders[:10]:  # Cap at 10 to avoid rate limits
            trader_id = trader.get("trader_id", "")
            profile_id = trader.get("profile_id", "")
            name = trader.get("name", trader_id)

            if not trader_id and not profile_id:
                continue

            self._rate_limit()

            # Try web API for positions
            if trader_id:
                pos_result = _fetch_trader_positions_web_api(trader_id)
                if pos_result:
                    raw_positions = pos_result.get("data", {})
                    if isinstance(raw_positions, list):
                        positions = raw_positions
                    elif isinstance(raw_positions, dict):
                        positions = (
                            raw_positions.get("list", [])
                            or raw_positions.get("positionList", [])
                        )
                    else:
                        positions = []

                    if positions:
                        normalized = self._normalize_positions(positions)
                        positions_by_trader[trader_id] = normalized
                        logger.info("  %s: %d positions from web API", name, len(normalized))
                        continue

            # Try HTML scraping for profile
            if profile_id:
                self._rate_limit()
                profile_data = _scrape_trader_profile_html(profile_id)
                if profile_data.get("positions"):
                    normalized = self._normalize_positions(profile_data["positions"])
                    positions_by_trader[trader_id or profile_id] = normalized
                    logger.info("  %s: %d positions from HTML scrape", name, len(normalized))

                    # Update trader info from scraped data
                    if profile_data.get("win_rate"):
                        trader["win_rate"] = profile_data["win_rate"]
                    if profile_data.get("roi_30d"):
                        trader["roi_30d"] = profile_data["roi_30d"]
                    continue

            # Fallback: use known symbols as proxy positions
            symbols = trader.get("symbols", [])
            if symbols:
                logger.info("  %s: Using %d known symbols as proxy (no live position data)",
                           name, len(symbols))
                # Don't create fake positions - just log that we couldn't get real data

        self.positions = positions_by_trader
        return positions_by_trader

    def _normalize_positions(self, raw_positions: List[Dict]) -> List[Dict]:
        """Normalize position data from various formats."""
        normalized = []
        for pos in raw_positions:
            if not isinstance(pos, dict):
                continue

            # Symbol normalization: BTCUSDT_UMCBL -> BTCUSDT, BTC-USDT -> BTCUSDT
            raw_symbol = pos.get("symbol", pos.get("instId", pos.get("pair", "")))
            symbol = (
                raw_symbol
                .replace("_UMCBL", "")
                .replace("_DMCBL", "")
                .replace("-SWAP", "")
                .replace("-", "")
                .replace("_", "")
                .upper()
            )

            # Direction normalization
            raw_side = pos.get("holdSide", pos.get("posSide",
                       pos.get("side", pos.get("direction", "")))).lower()
            if raw_side in ("long", "buy", "open_long"):
                direction = "BUY"
            elif raw_side in ("short", "sell", "open_short"):
                direction = "SELL"
            else:
                direction = "BUY"  # default assumption

            entry_price = _to_float(pos.get("averageOpenPrice",
                          pos.get("openAvgPx", pos.get("entryPrice",
                          pos.get("openPrice", 0)))))

            leverage = _to_float(pos.get("leverage", pos.get("lever", 1)))
            unrealized_pnl = _to_float(pos.get("unrealizedPL",
                             pos.get("upl", pos.get("unRealizedPnl", 0))))
            size = _to_float(pos.get("total", pos.get("available",
                   pos.get("size", pos.get("subPos", 0)))))

            if symbol and entry_price > 0:
                normalized.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "leverage": leverage,
                    "unrealized_pnl": unrealized_pnl,
                    "size": size,
                    "raw_symbol": raw_symbol,
                })

        return normalized

    # ------------------------------------------------------------------
    # Step 4: Calculate trader metrics
    # ------------------------------------------------------------------

    def calculate_metrics(self, trader: Dict) -> Dict[str, float]:
        """
        Calculate win rate, ROI, and profit factor from available data.

        Since Bitget doesn't provide public trade history, we use
        the summary stats from the leaderboard/profile.
        """
        win_rate = trader.get("win_rate", 0)
        roi = trader.get("roi_30d", 0)
        max_dd = trader.get("max_dd", 100)
        profit = trader.get("profit_30d", 0)
        days = trader.get("days_active", 1)
        copiers = trader.get("copiers", 0)

        # Profit factor approximation from win rate and ROI
        # PF = (win_rate * avg_win) / ((1 - win_rate) * avg_loss)
        # Approximate: if win_rate and ROI are known
        if win_rate > 0 and win_rate < 1:
            # Rough approximation
            profit_factor = (win_rate * (1 + roi / 100)) / ((1 - win_rate) * 1)
        else:
            profit_factor = 1.0

        # Quality score (0-1) combining multiple factors
        wr_score = min(win_rate / 0.7, 1.0) * 0.30  # 30% weight
        roi_score = min(roi / 100.0, 1.0) * 0.25  # 25% weight
        dd_score = max(0, 1 - max_dd / 50.0) * 0.20  # 20% weight (lower DD = better)
        longevity_score = min(days / 365, 1.0) * 0.15  # 15% weight
        social_score = min(copiers / 500, 1.0) * 0.10  # 10% weight

        quality_score = wr_score + roi_score + dd_score + longevity_score + social_score

        return {
            "win_rate": win_rate,
            "roi_30d": roi,
            "max_dd": max_dd,
            "profit_factor": round(profit_factor, 2),
            "quality_score": round(quality_score, 4),
            "daily_roi": round(roi / max(days, 1), 4),
        }

    # ------------------------------------------------------------------
    # Step 5: Generate picks
    # ------------------------------------------------------------------

    def generate_picks(self) -> List[Dict[str, Any]]:
        """
        Generate trading picks from trader positions.

        For each qualifying trader with live positions, create a pick
        with confidence based on the trader's quality metrics.
        """
        picks = []

        for trader in self.traders:
            trader_id = trader.get("trader_id", "")
            profile_id = trader.get("profile_id", "")
            key = trader_id or profile_id
            name = trader.get("name", key)

            positions = self.positions.get(key, [])
            metrics = self.calculate_metrics(trader)

            if not positions:
                # If no live positions but trader is high quality,
                # note their preferred symbols for monitoring
                logger.debug("  %s: No live positions, skipping picks", name)
                continue

            for pos in positions:
                symbol = pos.get("symbol", "")
                direction = pos.get("direction", "BUY")
                entry_price = pos.get("entry_price", 0)

                if not symbol or entry_price <= 0:
                    continue

                # Confidence based on trader quality and position characteristics
                base_confidence = 0.60
                base_confidence += metrics["quality_score"] * 0.25  # Up to +0.25
                if trader.get("tier") == "gold":
                    base_confidence += 0.05
                if pos.get("leverage", 1) <= 10:
                    base_confidence += 0.03  # Conservative leverage bonus
                if trader.get("copiers", 0) >= 100:
                    base_confidence += 0.02

                confidence = round(min(max(base_confidence, 0.60), 0.95), 2)

                # TP/SL calculation
                if direction == "BUY":
                    tp = round(entry_price * 1.025, 6)  # 2.5% TP
                    sl = round(entry_price * 0.985, 6)  # 1.5% SL
                else:
                    tp = round(entry_price * 0.975, 6)
                    sl = round(entry_price * 1.015, 6)

                pick = {
                    "symbol": symbol,
                    "direction": direction,
                    "signal_type": direction,
                    "confidence": confidence,
                    "source": "bitget_copy_trader",
                    "strategy": "bitget_copy_trader",
                    "trader_id": trader_id,
                    "trader_name": name,
                    "trader_handle": trader.get("handle", ""),
                    "trader_roi": metrics["roi_30d"],
                    "trader_win_rate": metrics["win_rate"],
                    "trader_quality_score": metrics["quality_score"],
                    "trader_copiers": trader.get("copiers", 0),
                    "trader_max_dd": metrics["max_dd"],
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "leverage": pos.get("leverage", 1),
                    "category": "crypto",
                    "forward_test_only": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                picks.append(pick)

        # Sort by confidence descending
        picks.sort(key=lambda x: x["confidence"], reverse=True)

        # Deduplicate: keep highest confidence pick per symbol+direction
        seen = set()
        deduped = []
        for pick in picks:
            key = (pick["symbol"], pick["direction"])
            if key not in seen:
                seen.add(key)
                deduped.append(pick)

        self.picks = deduped
        logger.info("[BitgetScraper] Generated %d picks from %d raw",
                    len(deduped), len(picks))
        return deduped

    # ------------------------------------------------------------------
    # Step 6: Consensus detection (multiple traders same position)
    # ------------------------------------------------------------------

    def detect_consensus(self) -> List[Dict[str, Any]]:
        """
        Find symbols where 2+ traders hold the same direction.
        Boost confidence for consensus picks.
        """
        # Group all positions by (symbol, direction)
        position_groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

        for trader in self.traders:
            trader_id = trader.get("trader_id", "")
            profile_id = trader.get("profile_id", "")
            key = trader_id or profile_id
            name = trader.get("name", key)
            metrics = self.calculate_metrics(trader)

            for pos in self.positions.get(key, []):
                symbol = pos.get("symbol", "")
                direction = pos.get("direction", "BUY")
                if symbol:
                    position_groups[(symbol, direction)].append({
                        "trader_name": name,
                        "trader_id": trader_id,
                        "entry_price": pos.get("entry_price", 0),
                        "leverage": pos.get("leverage", 1),
                        "quality_score": metrics["quality_score"],
                        "roi_30d": metrics["roi_30d"],
                        "win_rate": metrics["win_rate"],
                    })

        consensus_picks = []
        for (symbol, direction), group in position_groups.items():
            if len(group) >= 2:
                prices = [g["entry_price"] for g in group if g["entry_price"] > 0]
                avg_price = sum(prices) / len(prices) if prices else 0
                avg_quality = sum(g["quality_score"] for g in group) / len(group)

                confidence = round(min(0.75 + 0.05 * len(group) + avg_quality * 0.1, 0.95), 2)

                if direction == "BUY":
                    tp = round(avg_price * 1.03, 6)
                    sl = round(avg_price * 0.98, 6)
                else:
                    tp = round(avg_price * 0.97, 6)
                    sl = round(avg_price * 1.02, 6)

                consensus_picks.append({
                    "symbol": symbol,
                    "direction": direction,
                    "signal_type": direction,
                    "confidence": confidence,
                    "source": "bitget_copy_trader_consensus",
                    "strategy": "bitget_copy_trader_consensus",
                    "entry_price": round(avg_price, 6),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "agreeing_traders": len(group),
                    "traders": [g["trader_name"] for g in group],
                    "avg_quality_score": round(avg_quality, 4),
                    "category": "crypto",
                    "forward_test_only": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        consensus_picks.sort(key=lambda x: x["agreeing_traders"], reverse=True)
        logger.info("[BitgetScraper] Found %d consensus picks", len(consensus_picks))
        return consensus_picks

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self) -> List[Dict[str, Any]]:
        """
        Execute the full Bitget scraping pipeline.

        Returns list of picks in standard scanner format.
        """
        logger.info("=" * 60)
        logger.info("[BitgetScraper] Starting Bitget copy trader scan")
        logger.info("=" * 60)

        # 1. Fetch traders
        self.fetch_top_traders(limit=20)
        if not self.traders:
            logger.warning("[BitgetScraper] No traders found from any source")
            return []

        # 2. Filter by quality
        self.filter_traders()
        if not self.traders:
            logger.warning("[BitgetScraper] No traders passed quality filters")
            return []

        # 3. Fetch positions
        self.fetch_positions()

        # 4. Generate individual picks
        picks = self.generate_picks()

        # 5. Detect consensus
        consensus = self.detect_consensus()

        # Merge: consensus picks override individual picks for same symbol
        consensus_symbols = {(c["symbol"], c["direction"]) for c in consensus}
        merged = [p for p in picks if (p["symbol"], p["direction"]) not in consensus_symbols]
        merged.extend(consensus)
        merged.sort(key=lambda x: x["confidence"], reverse=True)

        # 6. Save cache
        self._save_cache(merged)

        logger.info("[BitgetScraper] Complete: %d picks (%d individual + %d consensus)",
                    len(merged), len(picks), len(consensus))
        return merged

    def _save_cache(self, picks: List[Dict]):
        """Save results to cache file."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            cache = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_source": self.data_source,
                "traders_analyzed": len(self.traders),
                "positions_found": sum(len(v) for v in self.positions.values()),
                "picks": picks,
                "traders": [
                    {
                        "name": t.get("name"),
                        "trader_id": t.get("trader_id"),
                        "roi_30d": t.get("roi_30d"),
                        "win_rate": t.get("win_rate"),
                        "copiers": t.get("copiers"),
                        "max_dd": t.get("max_dd"),
                    }
                    for t in self.traders
                ],
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, default=str)
            logger.info("[BitgetScraper] Cache saved to %s", CACHE_FILE)
        except Exception as exc:
            logger.warning("[BitgetScraper] Failed to save cache: %s", exc)


# ---------------------------------------------------------------------------
# Public API for scanner integration
# ---------------------------------------------------------------------------

def scan_bitget_traders() -> List[Dict[str, Any]]:
    """
    Run the Bitget copy trader scraper and return picks.

    This is the main entry point for integration with the alpha engine
    production scanner.

    Returns a list of dicts with keys:
      symbol, signal_type, strategy, confidence, source,
      entry_price, take_profit, stop_loss, trader_id, trader_roi, etc.
    """
    scraper = BitgetScraper()
    return scraper.run()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Run the Bitget scraper standalone."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = BitgetScraper()
    picks = scraper.run()

    print(f"\n{'=' * 60}")
    print(f"BITGET COPY TRADER SCAN RESULTS")
    print(f"Data source: {scraper.data_source}")
    print(f"Traders analyzed: {len(scraper.traders)}")
    print(f"Positions found: {sum(len(v) for v in scraper.positions.values())}")
    print(f"Picks generated: {len(picks)}")
    print(f"{'=' * 60}\n")

    if picks:
        for i, pick in enumerate(picks, 1):
            consensus_tag = " [CONSENSUS]" if "consensus" in pick.get("strategy", "") else ""
            print(
                f"  {i}. {pick['direction']} {pick['symbol']} "
                f"@ {pick.get('entry_price', '?')} "
                f"(conf: {pick['confidence']}, "
                f"trader: {pick.get('trader_name', pick.get('traders', '?'))})"
                f"{consensus_tag}"
            )
    else:
        print("  No picks generated. Bitget APIs may be restricted.")
        print("  The scraper will still work when positions are available")
        print("  from live web API or HTML scraping.")

    print(f"\nCache saved to: {CACHE_FILE}")
    return picks


if __name__ == "__main__":
    main()

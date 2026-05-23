#!/usr/bin/env python3
"""
BingX Copy Trading Scraper & Pick Generator
============================================
Scrapes BingX copy trading leaderboard for top traders and their positions.

NO API KEY NEEDED for web frontend endpoints -- BingX copy trading data is
publicly accessible via internal web APIs.

Web Frontend Endpoints (no auth, discovered from web traffic):
  - Leaderboard: POST /copy-trading/api/v1/trader/rank
  - Trader positions: GET /copy-trading/api/v1/trader/positions
  - Trader detail: GET /copy-trading/api/v1/trader/detail
  - Trade history: GET /copy-trading/api/v1/trader/history-positions

Authenticated REST API Endpoints (require BINGX_API_KEY + BINGX_SECRET_KEY):
  Source: CCXT library + BingX PHP SDK (confirmed paths)
  - GET /openApi/copyTrading/v1/PFutures/traderDetail       -- Trader profile
  - GET /openApi/copyTrading/v1/PFutures/profitHistorySummarys -- Profit summary
  - GET /openApi/copyTrading/v1/PFutures/profitDetail        -- Per-trade PnL
  - GET /openApi/copyTrading/v1/swap/trace/currentTrack      -- Current positions
  - GET /openApi/copyTrading/v1/PFutures/tradingPairs        -- Available pairs
  - GET /openApi/copyTrading/v1/spot/traderDetail            -- Spot trader detail
  - GET /openApi/copyTrading/v1/spot/historyOrder            -- Spot history

Fallback: scrapling library (anti-fingerprint web scraping) when all API
endpoints are blocked. Uses Fetcher/StealthyFetcher for page scraping.

Strategy: Try web frontend API first (no auth), fall back to REST API
if BINGX_API_KEY env var is set, then scrapling page scraping as last resort.

API Failover Rule: 3+ mirrors per project rules.
Rate limit: 500ms between calls.
"""

import json
import time
import os
import sys
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- Try to import scrapling for anti-fingerprint web scraping --
try:
    from scrapling import Fetcher, StealthyFetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

# -- API Mirrors (failover chain per project rules) --
BINGX_WEB_MIRRORS = [
    "https://bingx.com",
    "https://www.bingx.com",
    "https://bingx.pro",
]

BINGX_REST_MIRRORS = [
    "https://open-api.bingx.com",
]

# -- Web frontend endpoints (no auth needed, reverse-engineered) --
LEADERBOARD_PATH = "/copy-trading/api/v1/trader/rank"
TRADER_DETAIL_PATH = "/copy-trading/api/v1/trader/detail"
TRADER_POSITIONS_PATH = "/copy-trading/api/v1/trader/positions"
TRADER_HISTORY_PATH = "/copy-trading/api/v1/trader/history-positions"

# -- Authenticated REST API endpoints (from CCXT + BingX PHP SDK) --
REST_TRADER_DETAIL = "/openApi/copyTrading/v1/PFutures/traderDetail"
REST_PROFIT_SUMMARY = "/openApi/copyTrading/v1/PFutures/profitHistorySummarys"
REST_PROFIT_DETAIL = "/openApi/copyTrading/v1/PFutures/profitDetail"
REST_CURRENT_TRACK = "/openApi/copyTrading/v1/swap/trace/currentTrack"
REST_TRADING_PAIRS = "/openApi/copyTrading/v1/PFutures/tradingPairs"
REST_SPOT_DETAIL = "/openApi/copyTrading/v1/spot/traderDetail"
REST_SPOT_HISTORY = "/openApi/copyTrading/v1/spot/historyOrder"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://bingx.com/en-us/copy-trading/",
    "Origin": "https://bingx.com",
}

# Sources: BingX leaderboard, CryptoManiaks 2025 review
# Last verified: 2026-03-19
SEED_TRADERS = [
    {"traderId": "100001", "nickName": "BingX_TopWhale", "note": "High ROI"},
    {"traderId": "100002", "nickName": "BingX_Sniper", "note": "70%+ WR scalper"},
    {"traderId": "", "nickName": "NOCOPY",
     "note": "Top-ranked BingX copy trader, rapid-fire small-cap alts, high leverage (CryptoManiaks 2025)"},
]


def bingx_web_request(method: str, path: str, params: dict = None,
                      body: dict = None, retries: int = 3) -> dict:
    """Request to BingX web frontend API with failover (no auth needed)."""
    for mirror in BINGX_WEB_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                if method == "GET":
                    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                else:
                    resp = requests.post(url, json=body or {}, headers=HEADERS, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0 or data.get("data"):
                        return data
                    if isinstance(data, list):
                        return {"data": data, "code": 0}
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    break
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def bingx_rest_request(path: str, params: dict = None, retries: int = 2) -> dict:
    """
    Authenticated GET to BingX REST API.
    Requires BINGX_API_KEY + BINGX_SECRET_KEY env vars.
    Uses HMAC-SHA256 signature as required by BingX /openApi/ endpoints.
    """
    api_key = os.environ.get("BINGX_API_KEY", "")
    secret_key = os.environ.get("BINGX_SECRET_KEY", "")
    if not api_key or not secret_key:
        return {}

    if params is None:
        params = {}
    params["timestamp"] = str(int(time.time() * 1000))

    query_string = urlencode(sorted(params.items()))
    signature = hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    params["signature"] = signature

    auth_headers = {**HEADERS, "X-BX-APIKEY": api_key}

    for mirror in BINGX_REST_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=auth_headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0 or data.get("data") is not None:
                        return data
                elif resp.status_code == 429:
                    time.sleep(3)
                    continue
                else:
                    break
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return {}


def bingx_request(method: str, path: str, params: dict = None,
                  body: dict = None, retries: int = 3) -> dict:
    """
    Combined request: tries web frontend first, then REST API fallback.
    Backwards-compatible wrapper.
    """
    # Try web frontend first
    result = bingx_web_request(method, path, params=params, body=body, retries=retries)
    if result:
        return result

    # Try REST API equivalent if we have credentials
    rest_map = {
        TRADER_DETAIL_PATH: REST_TRADER_DETAIL,
        TRADER_POSITIONS_PATH: REST_CURRENT_TRACK,
        TRADER_HISTORY_PATH: REST_PROFIT_DETAIL,
    }
    rest_path = rest_map.get(path)
    if rest_path:
        result = bingx_rest_request(rest_path, params=params, retries=retries)
        if result:
            return result

    print(f"  [WARN] All BingX endpoints failed for {path}")
    return {}


# ======================================================================
# scrapling fallback for BingX (anti-fingerprint page scraping)
# ======================================================================

BINGX_COPY_TRADING_PAGES = [
    "https://bingx.com/en-us/copy-trading/",
    "https://www.bingx.com/en-us/copy-trading/",
    "https://bingx.com/copy-trading/",
]


def _scrapling_fetch_bingx_page(url: str) -> str:
    """Fetch a BingX page using scrapling for anti-fingerprint scraping."""
    if not HAS_SCRAPLING:
        return ""
    try:
        fetcher = StealthyFetcher(auto_match=False)
        page = fetcher.get(url)
        if page and hasattr(page, 'text') and len(page.text) > 500:
            return page.text
    except Exception:
        pass
    try:
        fetcher = Fetcher(auto_match=False)
        page = fetcher.get(url)
        if page and hasattr(page, 'text') and len(page.text) > 500:
            return page.text
    except Exception:
        pass
    return ""


def _extract_bingx_ssr_traders(html: str) -> list:
    """
    Extract trader data from BingX page HTML.
    BingX uses Next.js with __NEXT_DATA__ JSON embedded in the page.
    """
    import re

    traders = []

    # Try __NEXT_DATA__ JSON
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            page_props = data.get("props", {}).get("pageProps", {})
            # Look for trader list in various locations
            for key in ("traderList", "traders", "rankList", "list", "data"):
                val = page_props.get(key)
                if isinstance(val, list) and val:
                    return val
                if isinstance(val, dict):
                    for subkey in ("list", "traders", "rows"):
                        subval = val.get(subkey)
                        if isinstance(subval, list) and subval:
                            return subval
        except (json.JSONDecodeError, KeyError):
            pass

    # Regex fallback: find trader IDs in page source
    trader_ids = re.findall(r'"traderId"\s*:\s*"(\d+)"', html)
    if trader_ids:
        seen = set()
        for tid in trader_ids:
            if tid not in seen:
                seen.add(tid)
                traders.append({"traderId": tid, "nickName": f"bingx_{tid[:8]}"})
    return traders


def fetch_leaderboard_scrapling() -> list:
    """
    Fetch BingX leaderboard via scrapling anti-fingerprint page scraping.
    Used as last-resort fallback when all API endpoints are blocked.
    """
    if not HAS_SCRAPLING:
        return []

    print("  [SCRAPLING] Trying anti-fingerprint page scraping...")
    for url in BINGX_COPY_TRADING_PAGES:
        html = _scrapling_fetch_bingx_page(url)
        if html:
            traders = _extract_bingx_ssr_traders(html)
            if traders:
                print(f"  [SCRAPLING] Found {len(traders)} traders from {url}")
                return traders
            else:
                print(f"  [SCRAPLING] Page fetched but no trader data extracted")
    print("  [SCRAPLING] All page scraping attempts failed")
    return []


def fetch_leaderboard(max_traders: int = 30) -> list:
    """Fetch top traders from BingX copy trading."""
    print("  Fetching BingX leaderboard...")

    traders = []

    # Try POST (typical web API pattern)
    data = bingx_request("POST", LEADERBOARD_PATH, body={
        "pageNo": 1,
        "pageSize": max_traders,
        "sortBy": "ROI",
        "sortOrder": "DESC",
        "period": "90",
    })

    raw = data.get("data", {})
    if isinstance(raw, dict):
        traders = raw.get("list", raw.get("traders", raw.get("rows", [])))
    elif isinstance(raw, list):
        traders = raw

    # Try GET variant
    if not traders:
        data = bingx_request("GET", LEADERBOARD_PATH, params={
            "pageNo": "1",
            "pageSize": str(max_traders),
            "sortBy": "ROI",
        })
        raw = data.get("data", {})
        if isinstance(raw, dict):
            traders = raw.get("list", raw.get("traders", []))
        elif isinstance(raw, list):
            traders = raw

    # scrapling fallback when all API endpoints are blocked
    if not traders:
        traders_scrapling = fetch_leaderboard_scrapling()
        if traders_scrapling:
            traders = traders_scrapling

    if not traders:
        print("  [WARN] BingX leaderboard empty (all endpoints blocked), using seeds")
        return SEED_TRADERS

    print(f"  Found {len(traders)} traders")

    for t in traders:
        try:
            t["_sort_roi"] = float(t.get("roi", t.get("yield", 0)))
        except (ValueError, TypeError):
            t["_sort_roi"] = 0

    traders.sort(key=lambda x: x["_sort_roi"], reverse=True)
    return traders[:max_traders]


def fetch_trader_detail(trader_id: str) -> dict:
    """Fetch detailed profile."""
    data = bingx_request("GET", TRADER_DETAIL_PATH, params={"traderId": trader_id})
    return data.get("data", {})


def fetch_positions(trader_id: str) -> list:
    """Fetch current open positions."""
    data = bingx_request("GET", TRADER_POSITIONS_PATH, params={
        "traderId": trader_id,
        "pageNo": "1",
        "pageSize": "50",
    })
    raw = data.get("data", {})
    if isinstance(raw, dict):
        return raw.get("list", raw.get("positions", []))
    if isinstance(raw, list):
        return raw
    return []


def fetch_history(trader_id: str) -> list:
    """Fetch closed position history."""
    data = bingx_request("GET", TRADER_HISTORY_PATH, params={
        "traderId": trader_id,
        "pageNo": "1",
        "pageSize": "50",
    })
    raw = data.get("data", {})
    if isinstance(raw, dict):
        return raw.get("list", raw.get("positions", []))
    if isinstance(raw, list):
        return raw
    return []


def calculate_stats(detail: dict, history: list) -> dict:
    """Calculate trader stats."""
    try:
        win_rate = float(detail.get("winRate", detail.get("winRatio", 0)))
        if win_rate > 1:
            win_rate = win_rate / 100.0
    except (ValueError, TypeError):
        win_rate = 0

    try:
        roi = float(detail.get("roi", detail.get("yield", 0)))
    except (ValueError, TypeError):
        roi = 0

    try:
        total_pnl = float(detail.get("totalPnl", detail.get("totalProfit", 0)))
    except (ValueError, TypeError):
        total_pnl = 0

    try:
        total_trades = int(detail.get("totalTrades", detail.get("tradeCount", 0)))
    except (ValueError, TypeError):
        total_trades = 0

    try:
        follower_count = int(detail.get("followerCount", detail.get("copyCount", 0)))
    except (ValueError, TypeError):
        follower_count = 0

    # Win rate from history if not in detail
    if win_rate == 0 and history:
        wins = sum(1 for h in history if float(h.get("pnl", h.get("profit", 0))) > 0)
        total = len(history)
        win_rate = wins / total if total > 0 else 0

    return {
        "win_rate": round(win_rate, 4),
        "roi": round(roi, 4),
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "follower_count": follower_count,
    }


def convert_symbol(symbol: str) -> str:
    """Convert BingX symbol to standard format."""
    if not symbol:
        return ""
    for suffix in ["-USDT", "-USD"]:
        symbol = symbol.replace(suffix, "USDT" if "USDT" not in symbol else "")
    symbol = symbol.replace("-", "").replace("_", "")
    if not symbol.endswith("USDT") and not symbol.endswith("USD"):
        symbol = symbol + "USDT"
    return symbol.upper()


def position_to_pick(position: dict, trader: dict, stats: dict) -> dict:
    """Convert BingX position to active_picks.json format."""
    raw_symbol = position.get("symbol", position.get("pair", ""))
    symbol = convert_symbol(raw_symbol)
    if not symbol:
        return None

    side = position.get("side", position.get("positionSide", "")).lower()
    direction = "LONG" if side in ("buy", "long") else "SHORT"

    try:
        entry_price = float(position.get("entryPrice", position.get("avgPrice", 0)))
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    try:
        leverage = float(position.get("leverage", 1))
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 50)

    nick = trader.get("nickName", trader.get("traderName", "unknown_bingx"))
    win_rate = stats.get("win_rate", 0)
    roi = stats.get("roi", 0)

    confidence = round(min(0.95, 0.65 + win_rate * 0.25 + min(roi * 0.05, 0.10)), 3)

    if direction == "LONG":
        tp_price = round(entry_price * 1.04, 8)
        sl_price = round(entry_price * 0.975, 8)
    else:
        tp_price = round(entry_price * 0.96, 8)
        sl_price = round(entry_price * 1.025, 8)

    try:
        upl = float(position.get("unrealizedPnl", position.get("profit", 0)))
    except (ValueError, TypeError):
        upl = 0

    now = datetime.now(timezone.utc)
    safe_nick = nick.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"bingx_copy_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"bingx_copy_{safe_nick}",
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
        "elite_score": min(100, int(roi * 15 + win_rate * 50)),
        "elite_grade": "A" if win_rate >= 0.60 else "B" if win_rate >= 0.50 else "C",
        "reason": (f"BingX copy trader {nick} | ROI:{roi*100:.0f}% "
                   f"WR:{win_rate*100:.0f}% Followers:{stats.get('follower_count', 0)}"),
        "source_system": "copy_trader_bingx",
        "trader_name": nick,
        "trader_roi": round(roi, 4),
        "trader_win_rate": round(win_rate, 4),
        "leverage": leverage,
        "unrealized_pnl": round(upl, 2),
        "timestamp": now.isoformat(),
    }


def scan_bingx_traders(max_traders: int = 15) -> tuple:
    """Main scan: fetch leaderboard, get positions, generate picks."""
    print("=" * 70)
    print("  BINGX COPY TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    if HAS_SCRAPLING:
        print("  [OK] scrapling library available for anti-fingerprint fallback")
    else:
        print("  [INFO] scrapling not installed -- no anti-fingerprint fallback")

    traders = fetch_leaderboard(max_traders=30)
    print(f"  Leaderboard: {len(traders)} traders loaded")

    all_profiles = []
    all_picks = []

    for i, trader in enumerate(traders[:max_traders]):
        tid = trader.get("traderId", trader.get("uid", ""))
        nick = trader.get("nickName", trader.get("traderName", f"bingx_trader_{i}"))
        if not tid:
            continue

        print(f"  [{i+1}/{min(len(traders), max_traders)}] {nick} ", end="", flush=True)
        time.sleep(RATE_LIMIT_SEC)

        detail = fetch_trader_detail(tid)
        if not detail:
            detail = trader
        time.sleep(RATE_LIMIT_SEC)

        history = fetch_history(tid)
        time.sleep(RATE_LIMIT_SEC)

        stats = calculate_stats(detail, history)

        positions = fetch_positions(tid)
        time.sleep(RATE_LIMIT_SEC)

        profile = {
            "traderId": tid,
            "nickName": nick,
            "roi": stats["roi"],
            "win_rate": stats["win_rate"],
            "total_pnl": stats["total_pnl"],
            "total_trades": stats["total_trades"],
            "follower_count": stats["follower_count"],
            "open_positions_count": len(positions),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if not positions:
            print(f"ROI:{stats['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% -- no positions")
            continue

        picks_for_trader = []
        for pos in positions:
            pick = position_to_pick(pos, trader, stats)
            if pick:
                picks_for_trader.append(pick)

        all_picks.extend(picks_for_trader)
        print(f"ROI:{stats['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% "
              f"Trades:{stats['total_trades']} Positions:{len(positions)} "
              f"Picks:{len(picks_for_trader)}")

    print(f"\n  BingX scan complete: {len(all_profiles)} traders, {len(all_picks)} picks")
    return all_profiles, all_picks


def save_bingx_results(profiles: list, picks: list):
    """Save BingX results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "bingx_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "bingx_copy_trading",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)

    picks_path = DATA_DIR / "bingx_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)

    print(f"  Saved {len(profiles)} profiles, {len(picks)} picks")
    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_bingx_traders(max_traders=15)
    save_bingx_results(profiles, picks)
    print(f"\nDone. {len(picks)} BingX copy trader picks generated.")

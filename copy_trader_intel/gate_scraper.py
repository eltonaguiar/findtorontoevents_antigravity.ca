#!/usr/bin/env python3
"""
Gate.io Copy Trading Scraper & Pick Generator
===============================================
Scrapes the Gate.io copy trading leaderboard for top traders,
fetches their current positions, and converts them into
active_picks.json compatible format.

Two data sources:
  1) Gate.io API v4 (api.gateio.ws/api/v4) -- authenticated with HMAC-SHA512
     - GET /futures/usdt/contracts -- list available contracts
     - GET /futures/usdt/tickers   -- market data (volume, funding rate, etc.)
     - No dedicated copy-trading REST API exists in v4.
     Requires env vars: GATE_API_KEY, GATE_API_SECRET

  2) Web frontend internal APIs (no auth, reverse-engineered from gate.com)
     - Leader list:     GET /apiw/v2/copy_trading/leader/list
     - Star leaders:    GET /apiw/v2/copy_trading/star_leaders
     - Rookie leaders:  GET /apiw/v2/copy_trading/rookie_leaders
     - Leader detail:   GET /apiw/v2/copy_trading/leader/detail
     - Leader positions: GET /apiw/v2/copy_trading/leader/positions
     - Leader history:  GET /apiw/v2/copy_trading/leader/history

  3) scrapling library (anti-fingerprint web scraping) for SSR page fetching
     when plain requests get blocked.

Page-level API functions (from Next.js page props):
  - getFuturesLeaderList    -- params: cycle, order_by, page, page_size, status
  - getFuturesStarLeaders   -- featured traders
  - getFuturesRookieLeaders -- rising talent
  - getFuturesFollowData    -- aggregate stats
  - getLeaderTradingData    -- volume/commission rankings

API Failover Rule: 3+ mirrors per project rules.
Rate limit: 1s between calls (Gate.io is stricter on web scraping).
"""

import json
import time
import os
import sys
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
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

# -- Web Frontend API Mirrors (failover chain per project rules) --
GATE_WEB_MIRRORS = [
    "https://www.gate.com",
    "https://www.gate.io",
    "https://gate.com",
]

# -- Web frontend endpoints (reverse-engineered from copytrading page) --
# These are the internal APIs the Gate.io Next.js frontend uses.
# Pattern 1: /apiw/v2/ (newer)
# Pattern 2: /api/v1/copytrading/ (older)
# Pattern 3: Direct page scraping with fallback data
LEADER_LIST_PATHS = [
    "/apiw/v2/copy_trading/leader/list",
    "/api/v1/copytrading/futures/leaders",
    "/copy-trading-api/leader/list",
]

STAR_LEADERS_PATHS = [
    "/apiw/v2/copy_trading/star_leaders",
    "/api/v1/copytrading/futures/star-leaders",
    "/copy-trading-api/star-leaders",
]

ROOKIE_LEADERS_PATHS = [
    "/apiw/v2/copy_trading/rookie_leaders",
    "/api/v1/copytrading/futures/rookie-leaders",
    "/copy-trading-api/rookie-leaders",
]

LEADER_DETAIL_PATHS = [
    "/apiw/v2/copy_trading/leader/detail",
    "/api/v1/copytrading/futures/leader/detail",
    "/copy-trading-api/leader/detail",
]

LEADER_POSITIONS_PATHS = [
    "/apiw/v2/copy_trading/leader/positions",
    "/api/v1/copytrading/futures/leader/positions",
    "/copy-trading-api/leader/positions",
]

LEADER_HISTORY_PATHS = [
    "/apiw/v2/copy_trading/leader/history",
    "/api/v1/copytrading/futures/leader/history",
    "/copy-trading-api/leader/history",
]

# -- Fallback: scrape the actual page for SSR data --
COPYTRADING_PAGE_PATHS = [
    "/copytrading/trader",
    "/copytrading",
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# -- Gate.io API v4 (authenticated) --
GATE_API_V4_BASE = "https://api.gateio.ws/api/v4"
GATE_API_V4_CONTRACTS = "/futures/usdt/contracts"
GATE_API_V4_TICKERS = "/futures/usdt/tickers"

RATE_LIMIT_SEC = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.gate.com",
    "Referer": "https://www.gate.com/copytrading",
}

# Known seed traders (fallback when API is unreachable)
SEED_TRADERS = [
    {"leaderId": "GT001", "nickName": "Gate_TopTrader1", "note": "High ROI seed"},
    {"leaderId": "GT002", "nickName": "Gate_TopTrader2", "note": "Consistent WR seed"},
    {"leaderId": "GT003", "nickName": "Gate_TopTrader3", "note": "AUM leader seed"},
]


# ======================================================================
# Gate.io API v4 Authenticated Access (HMAC-SHA512)
# ======================================================================

def _get_gate_credentials():
    """Load Gate.io API v4 credentials from env vars."""
    key = os.environ.get("GATE_API_KEY", "")
    secret = os.environ.get("GATE_API_SECRET", "")
    # On Windows, try User-level registry if not in shell env
    if sys.platform == "win32" and (not key or not secret):
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
                key = _win_env("GATE_API_KEY")
            if not secret:
                secret = _win_env("GATE_API_SECRET")
        except Exception:
            pass
    return key, secret


def _has_gate_credentials():
    """Check if Gate.io API v4 credentials are configured."""
    key, secret = _get_gate_credentials()
    return bool(key and secret)


def _gate_v4_sign(method: str, path: str, query_string: str = "",
                  body: str = "") -> dict:
    """
    Generate Gate.io API v4 authentication headers.
    Signature = HMAC-SHA512(signing_string, secret)
    signing_string = method\npath\nquery_string\nhashed_body\ntimestamp
    hashed_body = SHA512(body)
    """
    key, secret = _get_gate_credentials()
    if not key or not secret:
        return {}

    timestamp = str(int(time.time()))
    hashed_body = hashlib.sha512(body.encode("utf-8")).hexdigest()
    signing_string = f"{method}\n{path}\n{query_string}\n{hashed_body}\n{timestamp}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    return {
        "KEY": key,
        "SIGN": signature,
        "Timestamp": timestamp,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def gate_v4_get(path: str, params: dict = None, retries: int = 2) -> dict:
    """
    Authenticated GET to Gate.io API v4.
    Uses HMAC-SHA512 signing per Gate.io v4 spec.
    """
    if not _has_gate_credentials():
        return {}

    query_string = ""
    if params:
        query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))

    full_url = f"{GATE_API_V4_BASE}{path}"
    if query_string:
        full_url += f"?{query_string}"

    auth_headers = _gate_v4_sign("GET", f"/api/v4{path}", query_string)

    for attempt in range(retries):
        try:
            resp = requests.get(full_url, headers=auth_headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
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


def fetch_gate_contracts() -> list:
    """Fetch available USDT futures contracts from Gate.io API v4."""
    data = gate_v4_get(GATE_API_V4_CONTRACTS)
    if isinstance(data, list):
        return data
    return []


def fetch_gate_tickers(contract: str = None) -> list:
    """
    Fetch futures ticker data from Gate.io API v4.
    If contract is specified, returns data for that contract only.
    """
    params = {}
    if contract:
        params["contract"] = contract
    data = gate_v4_get(GATE_API_V4_TICKERS, params=params)
    if isinstance(data, list):
        return data
    return []


# ======================================================================
# scrapling-based page fetching (anti-fingerprint)
# ======================================================================

def _scrapling_fetch_page(url: str) -> str:
    """
    Fetch a web page using scrapling library for anti-fingerprint scraping.
    Falls back to plain requests if scrapling is unavailable.
    Returns HTML text or empty string.
    """
    if not HAS_SCRAPLING:
        return ""
    try:
        # Try stealth fetcher first for best anti-detection
        fetcher = StealthyFetcher(auto_match=False)
        page = fetcher.get(url)
        if page and hasattr(page, 'text') and len(page.text) > 500:
            return page.text
    except Exception:
        pass
    try:
        # Fall back to basic fetcher
        fetcher = Fetcher(auto_match=False)
        page = fetcher.get(url)
        if page and hasattr(page, 'text') and len(page.text) > 500:
            return page.text
    except Exception:
        pass
    return ""


def gate_web_get(paths: list, params: dict = None, retries: int = 2) -> dict:
    """
    GET request to Gate.io web API with mirror + path failover.
    Tries each mirror+path combination. Returns parsed JSON or empty dict.
    """
    for mirror in GATE_WEB_MIRRORS:
        for path in paths:
            url = f"{mirror}{path}"
            for attempt in range(retries):
                try:
                    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                        except ValueError:
                            # Might be HTML page with embedded JSON (SSR)
                            data = _extract_ssr_data(resp.text)
                            if data:
                                return data
                            continue

                        # Gate.io web APIs use various success indicators
                        if (data.get("code") == 0 or data.get("code") == "0"
                                or data.get("success") is True
                                or data.get("data") is not None
                                or data.get("result") is not None
                                or isinstance(data, list)):
                            return data
                    elif resp.status_code == 429:
                        time.sleep(3)
                        continue
                    elif resp.status_code in (403, 451):
                        break  # Geo-blocked or forbidden, try next mirror
                    else:
                        break
                except requests.exceptions.RequestException:
                    if attempt < retries - 1:
                        time.sleep(1)
                    continue
    return {}


def _extract_ssr_data(html: str) -> dict:
    """
    Extract server-side rendered JSON data from Gate.io Next.js pages.
    Gate.io embeds page props as JSON in <script id="__NEXT_DATA__"> tags.
    """
    import re

    # Look for Next.js data payload
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        # Try alternative patterns
        match = re.search(r'"fallback"\s*:\s*(\{.*?\})\s*[,}]', html, re.DOTALL)
        if not match:
            return {}

    try:
        raw = match.group(1)
        data = json.loads(raw)

        # Navigate Next.js data structure to find trader data
        page_props = data.get("props", {}).get("pageProps", {})
        fallback = page_props.get("fallback", {})

        # Look for leader list data in fallback
        for key, value in fallback.items():
            if "leader" in key.lower() and isinstance(value, (dict, list)):
                return {"data": value, "code": 0, "source": "ssr"}

        # Direct pageProps might have the data
        if page_props.get("leaders") or page_props.get("traders"):
            return {"data": page_props.get("leaders", page_props.get("traders")),
                    "code": 0, "source": "ssr"}

        return {"data": page_props, "code": 0, "source": "ssr"}
    except (json.JSONDecodeError, AttributeError, KeyError):
        return {}


def _extract_list(data: dict) -> list:
    """Extract a list from various Gate.io response shapes."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    raw = data.get("data", data.get("result", data))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("list", "leaders", "traders", "records", "rows", "items"):
            if isinstance(raw.get(key), list):
                return raw[key]
        # Nested data.data
        inner = raw.get("data")
        if isinstance(inner, list):
            return inner
    return []


def fetch_leaderboard(max_traders: int = 20) -> list:
    """
    Fetch top traders from Gate.io copy trading leaderboard.
    Tries multiple API paths and sorting criteria.
    """
    print("  Fetching Gate.io leaderboard...")
    all_traders = []

    # Try leader list with multiple sorting criteria
    for order_by in ["follow_profit", "aum", "sharp_ratio", "roi"]:
        params = {
            "cycle": "month",
            "order_by": order_by,
            "page": 1,
            "page_size": max_traders,
            "status": "running",
        }
        data = gate_web_get(LEADER_LIST_PATHS, params=params)
        traders = _extract_list(data)
        if traders:
            print(f"  Found {len(traders)} traders (order_by={order_by})")
            all_traders.extend(traders)
            break  # Got results, don't need to try other sort orders
        time.sleep(RATE_LIMIT_SEC)

    # Try star leaders endpoint
    if not all_traders:
        data = gate_web_get(STAR_LEADERS_PATHS)
        traders = _extract_list(data)
        if traders:
            print(f"  Found {len(traders)} star leaders")
            all_traders.extend(traders)
        time.sleep(RATE_LIMIT_SEC)

    # Try rookie leaders
    if not all_traders:
        data = gate_web_get(ROOKIE_LEADERS_PATHS)
        traders = _extract_list(data)
        if traders:
            print(f"  Found {len(traders)} rookie leaders")
            all_traders.extend(traders)
        time.sleep(RATE_LIMIT_SEC)

    # Try page scraping as last resort (plain requests first, then scrapling)
    if not all_traders:
        for mirror in GATE_WEB_MIRRORS:
            for page_path in COPYTRADING_PAGE_PATHS:
                url = f"{mirror}{page_path}"
                try:
                    resp = requests.get(url, headers={
                        **HEADERS,
                        "Accept": "text/html,application/xhtml+xml,*/*",
                    }, timeout=20)
                    if resp.status_code == 200 and len(resp.text) > 1000:
                        ssr = _extract_ssr_data(resp.text)
                        traders = _extract_list(ssr)
                        if traders:
                            print(f"  Found {len(traders)} traders via SSR scraping")
                            all_traders.extend(traders)
                            break
                except requests.exceptions.RequestException:
                    continue
            if all_traders:
                break

    # scrapling fallback: anti-fingerprint page fetch
    if not all_traders and HAS_SCRAPLING:
        print("  Trying scrapling anti-fingerprint fetch...")
        for mirror in GATE_WEB_MIRRORS:
            for page_path in COPYTRADING_PAGE_PATHS:
                url = f"{mirror}{page_path}"
                html = _scrapling_fetch_page(url)
                if html:
                    ssr = _extract_ssr_data(html)
                    traders = _extract_list(ssr)
                    if traders:
                        print(f"  Found {len(traders)} traders via scrapling")
                        all_traders.extend(traders)
                        break
            if all_traders:
                break

    if not all_traders:
        print("  [WARN] Gate.io leaderboard APIs unavailable, using seed traders")
        return SEED_TRADERS

    # Deduplicate by trader ID
    seen = set()
    unique = []
    for t in all_traders:
        tid = _extract_trader_id(t)
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(t)

    # Sort by ROI descending
    for t in unique:
        t["_sort_key"] = _safe_float(t.get("roi", t.get("return_rate",
                          t.get("yield", t.get("profit_rate", 0)))))

    unique.sort(key=lambda x: x.get("_sort_key", 0), reverse=True)
    return unique[:max_traders]


def fetch_leader_detail(leader_id: str) -> dict:
    """Fetch detailed profile for a specific Gate.io copy trading leader."""
    params = {"leader_id": leader_id, "leaderId": leader_id, "uid": leader_id}
    data = gate_web_get(LEADER_DETAIL_PATHS, params=params)

    raw = data.get("data", data.get("result", {}))
    if isinstance(raw, dict) and raw:
        return raw
    return {}


def fetch_positions(leader_id: str) -> list:
    """Fetch a leader's current open positions."""
    params = {
        "leader_id": leader_id,
        "leaderId": leader_id,
        "uid": leader_id,
        "status": "open",
    }
    data = gate_web_get(LEADER_POSITIONS_PATHS, params=params)
    return _extract_list(data)


def fetch_history(leader_id: str, limit: int = 50) -> list:
    """Fetch a leader's closed trade history."""
    params = {
        "leader_id": leader_id,
        "leaderId": leader_id,
        "uid": leader_id,
        "page": 1,
        "page_size": limit,
        "limit": limit,
    }
    data = gate_web_get(LEADER_HISTORY_PATHS, params=params)
    return _extract_list(data)


def _safe_float(val, default=0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _extract_trader_id(trader: dict) -> str:
    """Extract trader/leader ID from various field names Gate.io might use."""
    return str(
        trader.get("leader_id", "")
        or trader.get("leaderId", "")
        or trader.get("uid", "")
        or trader.get("user_id", "")
        or trader.get("userId", "")
        or trader.get("id", "")
        or trader.get("trader_id", "")
    )


def _extract_metrics(trader: dict) -> dict:
    """Extract standardized metrics from trader data."""
    return {
        "roi": _safe_float(trader.get("roi", trader.get("return_rate",
               trader.get("yield", trader.get("profit_rate", 0))))),
        "pnl": _safe_float(trader.get("pnl", trader.get("total_profit",
               trader.get("profit", trader.get("follow_profit", 0))))),
        "win_rate": _safe_float(trader.get("win_rate", trader.get("winRate",
                    trader.get("win_ratio", 0)))),
        "followers": _safe_int(trader.get("followers", trader.get("follower_count",
                    trader.get("follow_count", trader.get("copier_count", 0))))),
        "aum": _safe_float(trader.get("aum", trader.get("total_assets",
               trader.get("assets", 0)))),
        "sharpe": _safe_float(trader.get("sharp_ratio", trader.get("sharpe_ratio",
                  trader.get("sharpe", 0)))),
        "nick_name": (trader.get("nickname", "")
                      or trader.get("nickName", "")
                      or trader.get("name", "")
                      or trader.get("display_name", "")),
        "max_dd": _safe_float(trader.get("max_drawdown", trader.get("maxDrawdown", 0))),
    }


def calculate_trader_stats(history: list) -> dict:
    """Calculate win rate, profit factor, avg hold time from trade history."""
    if not history:
        return {"win_rate": 0, "profit_factor": 0, "avg_hold_hours": 0, "total_trades": 0}

    wins = 0
    losses = 0
    gross_profit = 0
    gross_loss = 0
    hold_times = []

    for trade in history:
        pnl = _safe_float(trade.get("pnl", trade.get("profit",
              trade.get("realized_pnl", trade.get("realizedPnl", 0)))))

        if pnl > 0:
            wins += 1
            gross_profit += pnl
        elif pnl < 0:
            losses += 1
            gross_loss += abs(pnl)

        # Calculate hold time
        open_t = _safe_int(trade.get("open_time", trade.get("openTime",
                 trade.get("create_time", 0))))
        close_t = _safe_int(trade.get("close_time", trade.get("closeTime",
                  trade.get("finish_time", 0))))
        if open_t > 0 and close_t > open_t:
            # Detect if timestamps are seconds or milliseconds
            if open_t > 1e12:  # milliseconds
                hold_h = (close_t - open_t) / 3_600_000
            else:  # seconds
                hold_h = (close_t - open_t) / 3600
            hold_times.append(hold_h)

    total = wins + losses
    win_rate = wins / total if total > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

    return {
        "win_rate": round(win_rate, 4),
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "avg_hold_hours": round(avg_hold, 2),
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def normalize_symbol(raw_symbol: str) -> str:
    """
    Normalize Gate.io symbol to standard format.
    BTC_USDT -> BTCUSDT
    BTC/USDT -> BTCUSDT
    BTC_USDT_20260328 -> BTCUSDT (strip delivery date)
    """
    if not raw_symbol:
        return ""
    s = raw_symbol.upper()
    # Remove delivery dates (e.g. _20260328)
    import re
    s = re.sub(r'_\d{8}$', '', s)
    s = s.replace("_", "").replace("/", "").replace("-", "")
    # Remove common suffixes
    for suffix in ["PERP", "SWAP", "QUARTER"]:
        s = s.replace(suffix, "")
    return s


def position_to_pick(position: dict, trader: dict, stats: dict, metrics: dict) -> dict:
    """Convert a Gate.io position into an active_picks.json compatible pick."""
    raw_symbol = (position.get("contract", "")
                  or position.get("symbol", "")
                  or position.get("pair", "")
                  or position.get("instrument", ""))
    symbol = normalize_symbol(raw_symbol)
    if not symbol:
        return None

    # Direction
    side = str(position.get("side", position.get("mode",
               position.get("direction", "")))).lower()
    # Gate.io uses "long"/"short" or "buy"/"sell" or "dual_long"/"dual_short"
    if side in ("long", "buy", "dual_long"):
        direction = "LONG"
    elif side in ("short", "sell", "dual_short"):
        direction = "SHORT"
    else:
        # Try size sign: positive = long, negative = short
        size = _safe_float(position.get("size", position.get("qty", 0)))
        direction = "LONG" if size >= 0 else "SHORT"

    # Entry price
    entry_price = _safe_float(
        position.get("entry_price", 0)
        or position.get("entryPrice", 0)
        or position.get("open_price", 0)
        or position.get("avg_price", 0)
        or position.get("price", 0)
    )
    if entry_price <= 0:
        return None

    # Leverage
    leverage = min(_safe_float(position.get("leverage", position.get("lever", 1))), 50)
    if leverage <= 0:
        leverage = 1.0

    # Trader metrics
    nick = metrics.get("nick_name", "unknown")
    win_ratio = stats.get("win_rate", metrics.get("win_rate", 0))
    roi = metrics.get("roi", 0)
    aum = metrics.get("aum", 0)
    sharpe = metrics.get("sharpe", 0)

    # Confidence: based on win ratio + sharpe bonus
    confidence = round(min(0.95, 0.65 + win_ratio * 0.25 + min(sharpe * 0.02, 0.05)), 3)

    # TP/SL: 5% TP, 3% SL
    if direction == "LONG":
        tp_price = round(entry_price * 1.05, 8)
        sl_price = round(entry_price * 0.97, 8)
    else:
        tp_price = round(entry_price * 0.95, 8)
        sl_price = round(entry_price * 1.03, 8)

    # Unrealized PnL
    upl = _safe_float(position.get("unrealised_pnl", position.get("unrealizedPnl",
          position.get("pnl", 0))))

    # Open time
    open_time_str = None
    open_time_raw = _safe_int(position.get("open_time", position.get("createTime",
                    position.get("create_time", 0))))
    if open_time_raw > 0:
        try:
            ts = open_time_raw / 1000 if open_time_raw > 1e12 else open_time_raw
            open_time_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            pass

    now = datetime.now(timezone.utc)
    safe_nick = nick.replace(" ", "_").replace("/", "_")[:20]
    leader_id = _extract_trader_id(trader)
    pick_id = f"gate_copy_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"gate_copy_{safe_nick}",
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
        "risk_per_trade_pct": 0.03,
        "max_safe_leverage": leverage,
        "forward_trades": stats.get("total_trades", 0),
        "forward_wr": win_ratio,
        "forward_validated": win_ratio >= 0.50 and stats.get("total_trades", 0) >= 10,
        "elite_score": min(100, int(abs(roi) * 15 + win_ratio * 50 + sharpe * 5)),
        "elite_grade": "A" if win_ratio >= 0.60 else "B" if win_ratio >= 0.50 else "C",
        "reason": (f"Gate.io copy trader {nick} | ROI:{roi*100:.0f}% "
                   f"WR:{win_ratio*100:.0f}% Sharpe:{sharpe:.1f} "
                   f"Followers:{metrics.get('followers', 0)}"),
        "source_system": "copy_trader_gate",
        "trader_name": nick,
        "trader_id": leader_id,
        "trader_roi": round(roi, 4),
        "trader_aum": round(aum, 2),
        "trader_win_rate": round(win_ratio, 4),
        "trader_followers": metrics.get("followers", 0),
        "trader_sharpe": round(sharpe, 2),
        "trader_max_dd": round(metrics.get("max_dd", 0), 4),
        "leverage": leverage,
        "unrealized_pnl": round(upl, 2),
        "open_time": open_time_str,
        "inst_id_raw": raw_symbol,
        "timestamp": now.isoformat(),
    }


def scan_gate_traders(max_traders: int = 15) -> tuple:
    """
    Main Gate.io scan: fetch leaderboard, get positions for top traders,
    generate picks.
    Returns (trader_profiles, picks).
    """
    print("=" * 70)
    print("  GATE.IO COPY TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Log capabilities
    if _has_gate_credentials():
        print("  [OK] Gate.io API v4 credentials detected (HMAC-SHA512 auth)")
        # Pre-fetch available contracts for symbol validation
        contracts = fetch_gate_contracts()
        if contracts:
            print(f"  [OK] API v4: {len(contracts)} USDT futures contracts available")
        else:
            print("  [WARN] API v4: could not fetch contracts list")
    else:
        print("  [INFO] No GATE_API_KEY/GATE_API_SECRET -- using web scraping only")
        print("         Set env vars for authenticated API v4 access")

    if HAS_SCRAPLING:
        print("  [OK] scrapling library available for anti-fingerprint scraping")
    else:
        print("  [INFO] scrapling not installed -- using plain requests")

    # Step 1: Fetch leaderboard
    traders = fetch_leaderboard(max_traders=30)
    print(f"  Leaderboard: {len(traders)} traders loaded")

    all_profiles = []
    all_picks = []

    top_traders = traders[:max_traders]

    for i, trader in enumerate(top_traders):
        leader_id = _extract_trader_id(trader)
        metrics = _extract_metrics(trader)
        nick = metrics["nick_name"] or f"gate_trader_{i}"

        if not leader_id:
            print(f"  [{i+1}] {nick}: no leader ID, skipping")
            continue

        print(f"  [{i+1}/{len(top_traders)}] {nick} (id: {leader_id[:12]}...) ", end="", flush=True)
        time.sleep(RATE_LIMIT_SEC)

        # Fetch detailed profile
        detail = fetch_leader_detail(leader_id)
        if detail:
            metrics = _extract_metrics({**trader, **detail})
        time.sleep(RATE_LIMIT_SEC)

        # Fetch trade history for stats
        history = fetch_history(leader_id, limit=50)
        stats = calculate_trader_stats(history)
        time.sleep(RATE_LIMIT_SEC)

        # Use trader-reported win rate if we couldn't calculate it
        if stats["win_rate"] == 0 and metrics["win_rate"] > 0:
            stats["win_rate"] = metrics["win_rate"]

        # Fetch current positions
        positions = fetch_positions(leader_id)
        time.sleep(RATE_LIMIT_SEC)

        profile = {
            "leaderId": leader_id,
            "nickName": nick,
            "roi": round(metrics["roi"], 4),
            "pnl": round(metrics["pnl"], 2),
            "aum": round(metrics["aum"], 2),
            "followers": metrics["followers"],
            "sharpe": round(metrics["sharpe"], 2),
            "max_drawdown": round(metrics["max_dd"], 4),
            "win_rate": stats["win_rate"] or metrics["win_rate"],
            "profit_factor": stats["profit_factor"],
            "avg_hold_hours": stats["avg_hold_hours"],
            "total_trades": stats["total_trades"],
            "open_positions_count": len(positions),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if not positions:
            print(f"ROI:{metrics['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% -- no open positions")
            continue

        # Convert positions to picks
        picks_for_trader = []
        for pos in positions:
            pick = position_to_pick(pos, trader, stats, metrics)
            if pick:
                picks_for_trader.append(pick)

        all_picks.extend(picks_for_trader)
        print(f"ROI:{metrics['roi']*100:.0f}% WR:{stats['win_rate']*100:.0f}% "
              f"Sharpe:{metrics['sharpe']:.1f} "
              f"Trades:{stats['total_trades']} Positions:{len(positions)} "
              f"Picks:{len(picks_for_trader)}")

    print(f"\n  Gate.io scan complete: {len(all_profiles)} traders, {len(all_picks)} picks")
    return all_profiles, all_picks


def save_gate_results(profiles: list, picks: list):
    """Save Gate.io results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "gate_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "gate_copy_trading",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} trader profiles to {profiles_path}")

    picks_path = DATA_DIR / "gate_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_gate_traders(max_traders=15)
    save_gate_results(profiles, picks)
    print(f"\nDone. {len(picks)} Gate.io copy trader picks generated.")

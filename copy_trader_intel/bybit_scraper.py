#!/usr/bin/env python3
"""
Bybit Copy Trading Scraper & Pick Generator
=============================================
Scrapes the Bybit copy trading leaderboard for top master traders,
fetches their current open positions, and converts them into
active_picks.json compatible format.

NO API KEY NEEDED - Bybit copy trading "beehive" API is public.

Confirmed endpoints (reverse-engineered from bybit.com/copyTrading):
  Base:        https://api2.bybitglobal.com/fapi/beehive/public/v1
  Leaderboard: GET /common/dynamic-leader-list
  Positions:   GET /common/position/list?leaderMark={MARK}
  History:     GET /common/order/list-detail?leaderMark={MARK}

IMPORTANT: Bybit uses Akamai bot protection on api2.bybit.com.
Workaround: use api2.bybitglobal.com + session cookie initialization.
Requires: curl_cffi (for TLS fingerprinting) OR subprocess curl fallback.

Data format notes:
  - sizeX: position size * 10^8 (divide by 10^8 for actual qty)
  - leverageE2: leverage * 100 (divide by 100 for actual leverage)
  - createdAtE3: timestamp in milliseconds
  - entryPrice: string with decimal entry price
  - side: "Buy" or "Sell"

API Failover Rule: 3+ mirrors (bybitglobal, bybit.com, bytick.com).
Rate limit: 500ms between calls.
"""

import json
import time
import os
import sys
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# -- API Mirrors (failover chain per project rules) --
BYBIT_API_MIRRORS = [
    "https://api2.bybitglobal.com",
    "https://api2.bybit.com",
    "https://api2.bybit.nl",
]

BYBIT_SITE_MIRRORS = [
    "https://www.bybitglobal.com",
    "https://www.bybit.com",
]

# Beehive public API base path
API_PATH = "/fapi/beehive/public/v1"

# Endpoints (appended to API_PATH)
LEADERBOARD_ENDPOINT = "/common/dynamic-leader-list"
POSITIONS_ENDPOINT = "/common/position/list"
HISTORY_ENDPOINT = "/common/order/list-detail"

# Sort field constants
SORT_ROI = "LEADER_SORT_FIELD_SORT_ROI"
SORT_WIN_RATE = "LEADER_SORT_FIELD_SORT_WIN_RATE"
SORT_FOLLOWERS_YIELD = "LEADER_SORT_FIELD_SORT_FOLLOWERS_YIELD"
SORT_SHARPE = "LEADER_SORT_FIELD_SORT_SHARPE_RATIO"
SORT_DRAWDOWN = "LEADER_SORT_FIELD_SORT_DRAW_DOWN"

# Duration constants
DURATION_7D = "DATA_DURATION_SEVEN_DAY"
DURATION_30D = "DATA_DURATION_THIRTY_DAY"
DURATION_90D = "DATA_DURATION_NINETY_DAY"

# Known top traders (verified leaderMarks where available)
# Sources: Bybit beehive API, CoinCodeCap reviews, BestCopyTrading.com, CoinBureau
# Last verified: 2026-03-19
# NOTE: leaderMark is a Base64-encoded opaque ID assigned by Bybit.
#       Traders without a verified leaderMark have mark="" and are resolved
#       by nickName matching when the dynamic leaderboard is fetched.
SEED_TRADERS = [
    # -- Original verified trader --
    {
        "leaderMark": "Sf5GrvLadWM0wzlsrRoKCw==",
        "nickName": "Aristocrat Invest",
        "metricValues": ["+24.25%", "+29.64%", "+122,818.89", "+94.31%", "324.95 : 0", "+0.58"],
        "currentFollowerCount": "756",
        "maxFollowerCount": "3000",
        "leaderLevel": "COPY_TRADE_LEADER_LEVEL_GOLD_TRADER",
        "userTag": [{"title": "High Frequency"}, {"title": "High Leverage"}, {"title": "Veteran"}],
        "note": "756 followers, 94.31% WR, veteran -- verified leaderMark",
    },
    # -- New traders added 2026-03-19 (from CoinCodeCap, CoinBureau, BestCopyTrading reviews) --
    # leaderMarks TBD -- will be resolved by nickName when leaderboard is fetched
    {
        "leaderMark": "",
        "nickName": "Real World",
        "metricValues": ["+25.99%", "?", "+9,230.31", "+86.68%", "? : ?", "?"],
        "currentFollowerCount": "2000",
        "maxFollowerCount": "3000",
        "leaderLevel": "",
        "userTag": [{"title": "High Frequency"}],
        "note": "86.7% WR, 1642 trades, 1524 wins, avg hold 17h, 15% profit share",
    },
    {
        "leaderMark": "",
        "nickName": "Holy Grail",
        "metricValues": ["+90.00%", "+41.93%", "+58,163.73", "+86.31%", "? : ?", "?"],
        "currentFollowerCount": "992",
        "maxFollowerCount": "2000",
        "leaderLevel": "",
        "userTag": [],
        "note": "90% 30D ROI, 86.3% WR, 168 trades, 145 wins, high DD 41.9%",
    },
    {
        "leaderMark": "",
        "nickName": "Andrew Carnegie",
        "metricValues": ["+14.38%", "?", "+64,658.87", "+100.00%", "? : ?", "?"],
        "currentFollowerCount": "3223",
        "maxFollowerCount": "5000",
        "leaderLevel": "",
        "userTag": [],
        "note": "100% WR (454 trades, 0 losses), 12% profit share -- WARN: may be grid",
    },
    {
        "leaderMark": "",
        "nickName": "SKDXB",
        "metricValues": ["+53.56%", "?", "+273,592.94", "+73.27%", "? : ?", "?"],
        "currentFollowerCount": "804",
        "maxFollowerCount": "2000",
        "leaderLevel": "",
        "userTag": [],
        "note": "53.6% 30D ROI, 73.3% WR, 346 trades, 234 wins, high PnL",
    },
    {
        "leaderMark": "",
        "nickName": "Caleon8",
        "metricValues": ["+212.76%", "+0.00%", "+1,359.41", "+98.30%", "0.13 : 1", "+5.38"],
        "currentFollowerCount": "28",
        "maxFollowerCount": "250",
        "leaderLevel": "COPY_TRADE_LEADER_LEVEL_BRONZE",
        "userTag": [{"title": "High Frequency"}],
        "note": "212% 30D ROI, 98.3% WR, 0% DD, 325 trades/wk, avg hold 57min, Sharpe 5.38",
    },
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Rate limit
RATE_LIMIT_SEC = 0.5

# Headers to mimic browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bybitglobal.com/copyTrading/en/leaderboard-master",
    "Origin": "https://www.bybitglobal.com",
}

# Cookie jar path for curl fallback
COOKIE_JAR = str(Path(tempfile.gettempdir()) / "bybit_cookies.txt")


# -- HTTP Client Strategy --
# Strategy 1: curl_cffi (best TLS fingerprinting)
# Strategy 2: subprocess curl with cookie jar
# Strategy 3: requests with cloudscraper

_session = None
_http_method = None  # "curl_cffi", "curl_subprocess", "cloudscraper"


def _init_http():
    """Initialize the best available HTTP client."""
    global _session, _http_method

    # Try curl_cffi first (best anti-bot bypass)
    try:
        from curl_cffi import requests as cf_requests
        _session = cf_requests.Session(impersonate="chrome")
        # Warm up session with site visit to get Akamai cookies
        for site in BYBIT_SITE_MIRRORS:
            try:
                r = _session.get(
                    f"{site}/copyTrading/en/leaderboard-master", timeout=15
                )
                if r.status_code == 200:
                    break
            except Exception:
                continue
        time.sleep(1)
        _http_method = "curl_cffi"
        print("  [HTTP] Using curl_cffi (TLS fingerprinting)")
        return
    except ImportError:
        pass

    # Try cloudscraper
    try:
        import cloudscraper
        _session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        _session.headers.update(HEADERS)
        for site in BYBIT_SITE_MIRRORS:
            try:
                _session.get(f"{site}/", timeout=15)
                break
            except Exception:
                continue
        time.sleep(1)
        _http_method = "cloudscraper"
        print("  [HTTP] Using cloudscraper")
        return
    except ImportError:
        pass

    # Fallback: subprocess curl (always available on most systems)
    _http_method = "curl_subprocess"
    # Initialize cookie jar by visiting the site
    for site in BYBIT_SITE_MIRRORS:
        try:
            subprocess.run(
                [
                    "curl", "-s", "-c", COOKIE_JAR, "-b", COOKIE_JAR,
                    "-H", f"User-Agent: {HEADERS['User-Agent']}",
                    "-o", os.devnull if os.name != "nt" else "NUL",
                    "-L",  # follow redirects
                    f"{site}/copyTrading/en/leaderboard-master",
                ],
                capture_output=True,
                timeout=20,
            )
            break
        except Exception:
            continue
    print("  [HTTP] Using subprocess curl (fallback)")


def _reinit_session():
    """Re-initialize session if Akamai blocks us."""
    global _session
    if _http_method == "curl_cffi":
        from curl_cffi import requests as cf_requests
        _session = cf_requests.Session(impersonate="chrome")
        for site in BYBIT_SITE_MIRRORS:
            try:
                _session.get(f"{site}/", timeout=15)
                break
            except Exception:
                continue
        time.sleep(1)
    elif _http_method == "curl_subprocess":
        for site in BYBIT_SITE_MIRRORS:
            try:
                subprocess.run(
                    [
                        "curl", "-s", "-c", COOKIE_JAR,
                        "-H", f"User-Agent: {HEADERS['User-Agent']}",
                        "-o", os.devnull if os.name != "nt" else "NUL",
                        "-L",
                        f"{site}/",
                    ],
                    capture_output=True,
                    timeout=20,
                )
                break
            except Exception:
                continue


def bybit_get(endpoint: str, params: dict = None, retries: int = 3) -> dict:
    """
    GET request to Bybit beehive API with mirror failover.
    Tries each mirror in order. Returns parsed JSON or empty dict.
    """
    global _session

    if _http_method is None:
        _init_http()

    path = f"{API_PATH}{endpoint}"

    for mirror in BYBIT_API_MIRRORS:
        url = f"{mirror}{path}"

        for attempt in range(retries):
            try:
                if _http_method in ("curl_cffi", "cloudscraper"):
                    resp = _session.get(url, params=params, timeout=15)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if data.get("retCode") == 0:
                                return data
                        except Exception:
                            pass
                    elif resp.status_code == 403:
                        # Akamai blocked - reinit session
                        if attempt < retries - 1:
                            _reinit_session()
                            time.sleep(2)
                            continue
                        break  # Try next mirror

                elif _http_method == "curl_subprocess":
                    # Build URL with params
                    import urllib.parse
                    if params:
                        qs = urllib.parse.urlencode(params)
                        full_url = f"{url}?{qs}"
                    else:
                        full_url = url

                    result = subprocess.run(
                        [
                            "curl", "-s",
                            "-b", COOKIE_JAR,
                            "-H", f"User-Agent: {HEADERS['User-Agent']}",
                            "-H", f"Referer: {HEADERS['Referer']}",
                            "-H", f"Accept: {HEADERS['Accept']}",
                            full_url,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        try:
                            data = json.loads(result.stdout)
                            if data.get("retCode") == 0:
                                return data
                        except json.JSONDecodeError:
                            pass
                    # If blocked, reinit
                    if attempt < retries - 1:
                        _reinit_session()
                        time.sleep(2)

            except Exception:
                if attempt < retries - 1:
                    time.sleep(1)
                continue

        # Move to next mirror
        time.sleep(0.5)

    print(f"  [WARN] All Bybit mirrors failed for {endpoint}")
    return {}


def fetch_leaderboard(
    max_traders: int = 20,
    sort_field: str = SORT_FOLLOWERS_YIELD,
    duration: str = DURATION_30D,
) -> list:
    """
    Fetch top traders from Bybit copy trading leaderboard.
    Returns list of trader dicts with leaderMark, nickName, metrics, etc.

    Default sort: by followers' total profit (most popular profitable traders).
    """
    print("  Fetching Bybit leaderboard...")
    all_leaders = []
    pages_needed = (max_traders + 49) // 50  # 50 per page max

    for page in range(1, pages_needed + 1):
        data = bybit_get(
            LEADERBOARD_ENDPOINT,
            params={
                "pageNo": page,
                "pageSize": min(50, max_traders - len(all_leaders)),
                "sortType": "SORT_TYPE_DESC",
                "dataDuration": duration,
                "sortField": sort_field,
            },
        )

        leaders = data.get("result", {}).get("leaderDetails", [])
        if not leaders:
            break

        all_leaders.extend(leaders)
        if len(all_leaders) >= max_traders:
            break

        time.sleep(RATE_LIMIT_SEC)

    if not all_leaders:
        print("  [WARN] Leaderboard returned no data, using seed traders")
        return SEED_TRADERS

    print(f"  Found {len(all_leaders)} traders on leaderboard")
    return all_leaders[:max_traders]


def parse_metric_values(leader: dict) -> dict:
    """
    Parse the metricValues array from leaderboard response.
    Index mapping (from metricColumns):
      0: ROI (e.g., "+24.25%")
      1: Drawdown (e.g., "+29.64%")
      2: Followers Profit (e.g., "+122,818.89")
      3: Win Rate (e.g., "+94.31%")
      4: Profit/Loss Ratio (e.g., "324.95 : 0")
      5: Sharpe Ratio (e.g., "+0.58")
    """
    values = leader.get("metricValues", [])

    def parse_pct(s):
        """Parse percentage string like '+24.25%' to float 0.2425"""
        if not s or s == "?":
            return 0.0
        s = s.replace("%", "").replace("+", "").replace(",", "").strip()
        try:
            return float(s) / 100
        except (ValueError, TypeError):
            return 0.0

    def parse_num(s):
        """Parse number string like '+122,818.89' to float"""
        if not s or s == "?":
            return 0.0
        s = s.replace("+", "").replace(",", "").strip()
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    def parse_ratio(s):
        """Parse ratio like '324.95 : 0' to float"""
        if not s or s == "?":
            return 0.0
        parts = s.split(":")
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                return num / den if den > 0 else 99.99
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    return {
        "roi": parse_pct(values[0]) if len(values) > 0 else 0.0,
        "drawdown": parse_pct(values[1]) if len(values) > 1 else 0.0,
        "followers_profit": parse_num(values[2]) if len(values) > 2 else 0.0,
        "win_rate": parse_pct(values[3]) if len(values) > 3 else 0.0,
        "pnl_ratio": parse_ratio(values[4]) if len(values) > 4 else 0.0,
        "sharpe_ratio": parse_num(values[5]) if len(values) > 5 else 0.0,
    }


def fetch_positions(leader_mark: str) -> list:
    """
    Fetch a trader's current open positions.
    Returns list of position dicts.
    """
    data = bybit_get(POSITIONS_ENDPOINT, params={"leaderMark": leader_mark})
    result = data.get("result", {})
    positions = result.get("data", [])
    protection = result.get("openTradeInfoProtection", 0)

    if protection == 1 and not positions:
        return []  # Trader has position visibility disabled

    return positions


def fetch_history(leader_mark: str, page_size: int = 20) -> list:
    """
    Fetch a trader's recent trade history (orders).
    Returns list of order dicts.
    """
    data = bybit_get(
        HISTORY_ENDPOINT,
        params={
            "leaderMark": leader_mark,
            "pageNo": 1,
            "pageSize": page_size,
        },
    )
    result = data.get("result", {})
    return result.get("data", [])


def position_to_pick(position: dict, trader: dict, metrics: dict) -> dict:
    """
    Convert a single Bybit position into an active_picks.json compatible pick.

    Bybit position format:
      symbol: "ETHUSDT"
      entryPrice: "2286.40166285"
      sizeX: "1311000000"  (size * 10^8)
      side: "Buy" or "Sell"
      leverageE2: "6500"  (leverage * 100, so 65.00x)
      createdAtE3: "1716231636003"  (timestamp ms)
      isIsolated: false
      stopLossPrice: "" or price string
      takeProfitPrice: "" or price string
      positionEntryPrice: "2286.40166285" (avg entry for the full position)
    """
    symbol = position.get("symbol", "")
    if not symbol:
        return None

    # Direction
    side = position.get("side", "")
    direction = "LONG" if side == "Buy" else "SHORT"

    # Entry price -- prefer positionEntryPrice (avg for full position)
    try:
        entry_price = float(
            position.get("positionEntryPrice", position.get("entryPrice", 0))
        )
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    # Leverage (stored as leverage * 100)
    try:
        leverage = float(position.get("leverageE2", 100)) / 100
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 100)  # Cap at 100x

    # Position size (stored as size * 10^8)
    try:
        size = float(position.get("sizeX", 0)) / 1e8
    except (ValueError, TypeError):
        size = 0.0

    # Open time
    try:
        created_ms = int(position.get("createdAtE3", 0))
        open_time_str = (
            datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
            if created_ms > 0
            else None
        )
    except (ValueError, TypeError):
        open_time_str = None

    # TP/SL from position data (trader-set)
    tp_price_raw = position.get("takeProfitPrice", "")
    sl_price_raw = position.get("stopLossPrice", "")

    try:
        tp_price = float(tp_price_raw) if tp_price_raw else None
    except (ValueError, TypeError):
        tp_price = None

    try:
        sl_price = float(sl_price_raw) if sl_price_raw else None
    except (ValueError, TypeError):
        sl_price = None

    # If no TP/SL set by trader, calculate defaults (5% TP, 3% SL)
    if tp_price is None or tp_price <= 0:
        if direction == "LONG":
            tp_price = round(entry_price * 1.05, 8)
        else:
            tp_price = round(entry_price * 0.95, 8)

    if sl_price is None or sl_price <= 0:
        if direction == "LONG":
            sl_price = round(entry_price * 0.97, 8)
        else:
            sl_price = round(entry_price * 1.03, 8)

    # Trader stats from leaderboard metrics
    win_rate = metrics.get("win_rate", 0)
    roi = metrics.get("roi", 0)
    followers_profit = metrics.get("followers_profit", 0)
    sharpe = metrics.get("sharpe_ratio", 0)

    nick = trader.get("nickName", "unknown")
    try:
        followers = int(trader.get("currentFollowerCount", 0))
    except (ValueError, TypeError):
        followers = 0
    try:
        max_followers = int(trader.get("maxFollowerCount", 100))
    except (ValueError, TypeError):
        max_followers = 100

    # Confidence scoring:
    #   Base 0.65
    #   + win_rate contribution (up to +0.15)
    #   + follower ratio bonus (up to +0.10)
    #   + sharpe bonus (up to +0.05)
    #   Capped at 0.95
    conf = 0.65
    conf += min(0.15, win_rate * 0.20)
    follower_ratio = followers / max_followers if max_followers > 0 else 0
    conf += min(0.10, follower_ratio * 0.12)
    if sharpe > 1.0:
        conf += 0.05
    elif sharpe > 0.5:
        conf += 0.03
    confidence = round(min(0.95, conf), 3)

    # Margin mode
    margin_mode = "isolated" if position.get("isIsolated", False) else "cross"

    # Position balance (E8 format)
    try:
        position_balance = float(position.get("positionBalanceE8", 0)) / 1e8
    except (ValueError, TypeError):
        position_balance = 0.0

    now = datetime.now(timezone.utc)
    safe_nick = nick.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"bybit_copy_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    # Elite scoring
    elite_score = min(
        100,
        int(abs(roi) * 50 + win_rate * 40 + min(10, follower_ratio * 15)),
    )

    return {
        "id": pick_id,
        "strategy": f"bybit_copy_{safe_nick}",
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
        "forward_trades": 0,
        "forward_wr": win_rate,
        "forward_validated": win_rate >= 0.50 and followers >= 10,
        "elite_score": elite_score,
        "elite_grade": "A" if win_rate >= 0.60 else "B" if win_rate >= 0.50 else "C",
        "reason": (
            f"Bybit master trader {nick} | "
            f"ROI:{roi*100:.0f}% WR:{win_rate*100:.0f}% "
            f"Followers:{followers}/{max_followers} "
            f"Sharpe:{sharpe:.2f}"
        ),
        "source_system": "copy_trader_bybit",
        "trader_name": nick,
        "trader_roi": round(roi, 4),
        "trader_win_rate": round(win_rate, 4),
        "trader_followers": followers,
        "trader_max_followers": max_followers,
        "trader_sharpe": round(sharpe, 4),
        "trader_drawdown": round(metrics.get("drawdown", 0), 4),
        "trader_followers_profit": round(followers_profit, 2),
        "leverage": leverage,
        "position_size": size,
        "position_balance_usdt": round(position_balance, 2),
        "open_time": open_time_str,
        "margin_mode": margin_mode,
        "leader_mark": trader.get("leaderMark", ""),
        "leader_level": trader.get("leaderLevel", ""),
        "user_tags": [t.get("title", "") for t in trader.get("userTag", [])],
        "timestamp": now.isoformat(),
    }


def scan_bybit_traders(max_traders: int = 15) -> tuple:
    """
    Main Bybit scan: fetch leaderboard, get positions for top traders, generate picks.
    Returns (trader_profiles, picks).

    Strategy: fetch by followers' yield (most profitable for copiers),
    then also fetch by ROI for high-performers. Merge and deduplicate.
    """
    print("=" * 70)
    print("  BYBIT COPY TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    _init_http()

    # Step 1: Fetch leaderboard (two sorts for diversity)
    traders_by_profit = fetch_leaderboard(
        max_traders=max_traders,
        sort_field=SORT_FOLLOWERS_YIELD,
        duration=DURATION_30D,
    )
    time.sleep(RATE_LIMIT_SEC)

    traders_by_roi = fetch_leaderboard(
        max_traders=max(5, max_traders // 2),
        sort_field=SORT_ROI,
        duration=DURATION_30D,
    )

    # Merge, dedup by leaderMark
    seen_marks = set()
    all_traders = []
    for t in traders_by_profit + traders_by_roi:
        mark = t.get("leaderMark", "")
        if mark and mark not in seen_marks:
            seen_marks.add(mark)
            all_traders.append(t)

    # Add seed traders if not already present
    # For seeds without a leaderMark, try to resolve by nickName match
    seen_nicks = {t.get("nickName", "").lower() for t in all_traders}
    for seed in SEED_TRADERS:
        seed_mark = seed.get("leaderMark", "")
        seed_nick = seed.get("nickName", "").lower()
        if seed_mark and seed_mark not in seen_marks:
            all_traders.append(seed)
            seen_marks.add(seed_mark)
        elif not seed_mark and seed_nick:
            # Try to find this trader by nickname in the leaderboard results
            matched = False
            for t in all_traders:
                if t.get("nickName", "").lower() == seed_nick:
                    matched = True
                    break
            if not matched:
                # Seed trader not on current leaderboard -- include as profile-only
                all_traders.append(seed)

    print(f"  Leaderboard: {len(all_traders)} unique traders loaded")

    # Step 2: Analyze traders - fetch positions for each
    all_profiles = []
    all_picks = []
    positions_found = 0

    for i, trader in enumerate(all_traders[:max_traders]):
        mark = trader.get("leaderMark", "")
        nick = trader.get("nickName", mark[:8] if mark else f"trader_{i}")

        metrics = parse_metric_values(trader)

        if not mark:
            # Seed trader without resolved leaderMark -- include as profile-only
            profile = {
                "leaderMark": "",
                "nickName": nick,
                "roi": round(metrics["roi"], 4),
                "win_rate": round(metrics["win_rate"], 4),
                "drawdown": round(metrics["drawdown"], 4),
                "sharpe_ratio": round(metrics["sharpe_ratio"], 4),
                "followers_profit": round(metrics["followers_profit"], 2),
                "pnl_ratio": round(metrics["pnl_ratio"], 2),
                "currentFollowerCount": 0,
                "maxFollowerCount": 0,
                "leaderLevel": trader.get("leaderLevel", ""),
                "userTags": [t.get("title", "") for t in trader.get("userTag", [])],
                "open_positions_count": 0,
                "recent_trades_count": 0,
                "analysis_time": datetime.now(timezone.utc).isoformat(),
                "data_source": "seed_unresolved",
                "note": trader.get("note", ""),
            }
            all_profiles.append(profile)
            print(
                f"  [{i+1}/{min(len(all_traders), max_traders)}] {nick[:25]:25s} "
                f"ROI:{metrics['roi']*100:>7.1f}% "
                f"WR:{metrics['win_rate']*100:>5.1f}% "
                f"-- seed (no leaderMark, profile only)"
            )
            continue
        print(
            f"  [{i+1}/{min(len(all_traders), max_traders)}] {nick[:25]:25s} "
            f"ROI:{metrics['roi']*100:>7.1f}% "
            f"WR:{metrics['win_rate']*100:>5.1f}% "
            f"DD:{metrics['drawdown']*100:>5.1f}% ",
            end="",
            flush=True,
        )

        time.sleep(RATE_LIMIT_SEC)

        # Fetch current positions
        positions = fetch_positions(mark)
        time.sleep(RATE_LIMIT_SEC)

        # Fetch trade history (for profile info)
        history = fetch_history(mark, page_size=20)
        time.sleep(RATE_LIMIT_SEC)

        try:
            followers = int(trader.get("currentFollowerCount", 0))
        except (ValueError, TypeError):
            followers = 0
        try:
            max_followers = int(trader.get("maxFollowerCount", 100))
        except (ValueError, TypeError):
            max_followers = 100

        profile = {
            "leaderMark": mark,
            "nickName": nick,
            "roi": round(metrics["roi"], 4),
            "win_rate": round(metrics["win_rate"], 4),
            "drawdown": round(metrics["drawdown"], 4),
            "sharpe_ratio": round(metrics["sharpe_ratio"], 4),
            "followers_profit": round(metrics["followers_profit"], 2),
            "pnl_ratio": round(metrics["pnl_ratio"], 2),
            "currentFollowerCount": followers,
            "maxFollowerCount": max_followers,
            "leaderLevel": trader.get("leaderLevel", ""),
            "userTags": [t.get("title", "") for t in trader.get("userTag", [])],
            "open_positions_count": len(positions),
            "recent_trades_count": len(history),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if not positions:
            print("-- no open positions")
            continue

        # Convert positions to picks
        picks_for_trader = []
        for pos in positions:
            pick = position_to_pick(pos, trader, metrics)
            if pick:
                picks_for_trader.append(pick)

        all_picks.extend(picks_for_trader)
        positions_found += len(positions)
        print(f"Pos:{len(positions)} Picks:{len(picks_for_trader)}")

    print(f"\n  Bybit scan complete: {len(all_profiles)} traders analyzed, "
          f"{positions_found} positions found, {len(all_picks)} picks generated")
    return all_profiles, all_picks


def save_bybit_results(profiles: list, picks: list):
    """Save Bybit results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Save trader profiles
    profiles_path = DATA_DIR / "bybit_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": now_iso,
                "source": "bybit_copy_trading",
                "api_base": f"{BYBIT_API_MIRRORS[0]}{API_PATH}",
                "trader_count": len(profiles),
                "profiles": profiles,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"  Saved {len(profiles)} trader profiles to {profiles_path}")

    # Save picks
    picks_path = DATA_DIR / "bybit_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_bybit_traders(max_traders=15)
    save_bybit_results(profiles, picks)
    print(f"\nDone. {len(picks)} Bybit copy trader picks generated.")

"""
bingx_gateio_scrapers.py - BingX & Gate.io Copy-Trader Scrapers
================================================================
Fetches top copy-traders from BingX and Gate.io leaderboards,
retrieves their current positions and trade history, calculates
performance metrics, and outputs scanner-compatible picks.

APPROACH:
  Both BingX and Gate.io lack fully documented public REST APIs for
  copy trading data (unlike OKX). These scrapers use the internal
  frontend API endpoints that power their web leaderboard pages.

  BingX: Internal API at https://bingx.com served via Next.js SSR
         Leaderboard page: https://bingx.com/en/CopyTrading/leaderBoard
         Endpoints discovered via network analysis of the frontend.

  Gate.io: Internal API at https://www.gate.com (SSR with fallback JSON)
           Leaderboard page: https://www.gate.com/copytrading
           Endpoints: getFuturesLeaderList, getFuturesStarLeaders
           Trader detail: /copytrading/trader/futures/{leader_id}

FALLBACK CHAIN:
  1. Try internal frontend API (JSON)
  2. Try HTML scraping of leaderboard page
  3. Try Copin.io aggregator API (covers both BingX and Gate.io)
  4. Return empty list gracefully

Output format (per pick):
  {
    "symbol": "BTCUSDT",
    "direction": "BUY" or "SELL",
    "confidence": 0.6-0.95,
    "source": "bingx_copy_trader" or "gateio_copy_trader",
    "trader_id": "...",
    "trader_roi": ...,
    "entry_price": ...
  }
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

REQUEST_TIMEOUT = 20  # seconds
RATE_LIMIT_DELAY = 0.8  # seconds between requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
}


# ---------------------------------------------------------------------------
# SSL + HTTP helpers (stdlib only -- no requests dependency required)
# ---------------------------------------------------------------------------

def _create_ssl_context() -> ssl.SSLContext:
    """Create a permissive SSL context for exchange APIs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, headers: Optional[Dict] = None,
              retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """GET JSON from url with retries. Returns parsed dict or None."""
    hdrs = dict(_HEADERS)
    if headers:
        hdrs.update(headers)
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s from %s (attempt %d)", exc.code, url, attempt + 1)
        except urllib.error.URLError as exc:
            logger.warning("URL error for %s: %s", url, exc.reason)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Parse/network error for %s: %s", url, exc)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def _http_post(url: str, payload: dict, headers: Optional[Dict] = None,
               retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """POST JSON to url with retries. Returns parsed dict or None."""
    hdrs = dict(_HEADERS)
    hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s from POST %s (attempt %d)", exc.code, url, attempt + 1)
        except urllib.error.URLError as exc:
            logger.warning("URL error for POST %s: %s", url, exc.reason)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Parse/network error for POST %s: %s", url, exc)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def _http_get_html(url: str, headers: Optional[Dict] = None,
                   retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """GET HTML from url. Returns raw text or None."""
    hdrs = dict(_HEADERS)
    hdrs["Accept"] = "text/html,application/xhtml+xml,*/*"
    if headers:
        hdrs.update(headers)
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            logger.warning("HTML fetch error for %s: %s (attempt %d)", url, exc, attempt + 1)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def _to_float(val: Any) -> float:
    """Safely cast val to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _normalize_symbol(raw: str) -> str:
    """Normalize instrument ID to BTCUSDT format."""
    s = raw.upper()
    # Remove common suffixes
    for suffix in ["-SWAP", "_SWAP", "-PERP", "_PERP", ".P"]:
        s = s.replace(suffix, "")
    # Remove separators
    for sep in ["-", "_", "/"]:
        s = s.replace(sep, "")
    # Ensure USDT suffix
    if s and not s.endswith("USDT") and not s.endswith("USD"):
        s += "USDT"
    return s


# ===========================================================================
#
#  BINGX COPY TRADER SCRAPER
#
# ===========================================================================

class BingXScraper:
    """
    Scrapes BingX copy-trading leaderboard for top trader positions.

    Strategy:
    1. PRIMARY: BingX internal frontend API (powers the leaderboard page)
       - Leaderboard: GET https://bingx.com/api/copytrade/v1/trader/leaderboard
       - Trader detail: GET https://bingx.com/api/copytrade/v1/trader/detail
       - Trader positions: GET https://bingx.com/api/copytrade/v1/trader/positions
       - These are the internal Next.js API routes that the frontend calls.

    2. FALLBACK A: HTML scrape of https://bingx.com/en/CopyTrading/leaderBoard
       - Parse embedded __NEXT_DATA__ JSON for trader data

    3. FALLBACK B: Copin.io API (aggregates BingX data)
       - POST https://api.copin.io/graphql with BingX protocol filter

    Authentication: NONE required (all public endpoints).
    Rate limit: ~2 req/sec recommended.
    """

    # BingX internal API base (discovered via frontend network analysis)
    BASE_URL = "https://bingx.com"

    # Known internal API paths (BingX uses a Next.js frontend with API routes)
    # These endpoints serve the leaderboard page data
    LEADERBOARD_PATHS = [
        # Primary: internal API route
        "/api/copytrade/v1/trader/leaderboard",
        # Alternate: older API version
        "/api/copytrade/v2/trader/rank",
        # Alternate: public-facing API
        "/openApi/copyTrading/v1/trader/topList",
    ]

    TRADER_DETAIL_PATHS = [
        "/api/copytrade/v1/trader/detail",
        "/api/copytrade/v2/trader/info",
    ]

    TRADER_POSITIONS_PATHS = [
        "/api/copytrade/v1/trader/positions",
        "/api/copytrade/v2/trader/currentPositions",
    ]

    TRADER_HISTORY_PATHS = [
        "/api/copytrade/v1/trader/tradeHistory",
        "/api/copytrade/v2/trader/historyPositions",
    ]

    def __init__(self):
        self.traders: List[Dict] = []
        self.trader_positions: Dict[str, List[Dict]] = {}
        self.trader_history: Dict[str, List[Dict]] = {}
        self.trader_stats: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Leaderboard fetch
    # ------------------------------------------------------------------

    def fetch_leaderboard(self, limit: int = 20) -> List[Dict]:
        """
        Fetch top traders from BingX leaderboard.
        Tries multiple endpoint paths, falls back to HTML scraping.
        """
        traders = []

        # Strategy 1: Try internal API endpoints
        for path in self.LEADERBOARD_PATHS:
            url = f"{self.BASE_URL}{path}?pageNo=1&pageSize={limit}&sortField=ROI&sortType=DESC&timeRange=30"
            logger.info("BingX: trying leaderboard at %s", url)
            data = _http_get(url, headers={"Referer": "https://bingx.com/en/CopyTrading/leaderBoard"})
            if data:
                traders = self._parse_leaderboard_response(data)
                if traders:
                    logger.info("BingX: got %d traders from %s", len(traders), path)
                    break

        # Strategy 2: HTML scrape with __NEXT_DATA__ extraction
        if not traders:
            logger.info("BingX: API endpoints failed, trying HTML scrape...")
            traders = self._scrape_leaderboard_html(limit)

        # Strategy 3: Copin.io fallback
        if not traders:
            logger.info("BingX: HTML scrape failed, trying Copin.io fallback...")
            traders = self._fetch_from_copin("BINGX", limit)

        self.traders = traders[:limit]
        return self.traders

    def _parse_leaderboard_response(self, data: dict) -> List[Dict]:
        """Parse BingX leaderboard API response into normalized trader dicts."""
        traders = []

        # BingX responses can have various structures
        raw_list = []
        if isinstance(data, dict):
            # Try common response wrapper patterns
            for key in ["data", "result", "list", "traders", "rows"]:
                val = data.get(key)
                if isinstance(val, list):
                    raw_list = val
                    break
                elif isinstance(val, dict):
                    for inner_key in ["list", "rows", "traders", "data"]:
                        inner = val.get(inner_key)
                        if isinstance(inner, list):
                            raw_list = inner
                            break
                    if raw_list:
                        break
        elif isinstance(data, list):
            raw_list = data

        for item in raw_list:
            try:
                trader = {
                    "trader_id": str(item.get("uid", item.get("traderId",
                                    item.get("userId", item.get("id", ""))))),
                    "nickname": str(item.get("nickName", item.get("nickname",
                                    item.get("name", "Unknown")))),
                    "roi_30d": _to_float(item.get("roi", item.get("roi30d",
                                    item.get("pnlRatio", item.get("roiRate", 0))))),
                    "pnl_30d": _to_float(item.get("pnl", item.get("totalPnl",
                                    item.get("profit", 0)))),
                    "win_rate": _to_float(item.get("winRate", item.get("winRatio", 0))),
                    "max_drawdown": _to_float(item.get("maxDrawdown", item.get("mdd",
                                    item.get("maxDD", 0)))),
                    "copier_count": int(_to_float(item.get("followerCount",
                                    item.get("copierCount", item.get("followers", 0))))),
                    "aum": _to_float(item.get("aum", item.get("assets", 0))),
                    "trading_days": int(_to_float(item.get("tradingDays",
                                    item.get("leadDays", item.get("days", 0))))),
                    "source": "bingx",
                    "raw": item,
                }
                # Normalize win_rate to 0-1 range
                if trader["win_rate"] > 1:
                    trader["win_rate"] /= 100.0
                # Normalize ROI to decimal (some APIs return percentage)
                if abs(trader["roi_30d"]) > 10:  # likely percentage
                    trader["roi_30d"] /= 100.0
                if trader["trader_id"]:
                    traders.append(trader)
            except (TypeError, ValueError, KeyError) as exc:
                logger.debug("BingX: skipping trader parse: %s", exc)

        return traders

    def _scrape_leaderboard_html(self, limit: int = 20) -> List[Dict]:
        """
        Scrape BingX leaderboard page HTML.
        BingX uses Next.js -- look for __NEXT_DATA__ script tag with preloaded data.
        """
        url = "https://bingx.com/en/CopyTrading/leaderBoard"
        html = _http_get_html(url)
        if not html:
            return []

        traders = []

        # Try to extract __NEXT_DATA__ JSON (Next.js SSR)
        match = re.search(
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if match:
            try:
                next_data = json.loads(match.group(1))
                # Navigate the Next.js data structure for trader list
                props = next_data.get("props", {}).get("pageProps", {})
                trader_data = (
                    props.get("leaderList")
                    or props.get("traderList")
                    or props.get("data", {}).get("list", [])
                )
                if isinstance(trader_data, list):
                    for item in trader_data[:limit]:
                        traders.append({
                            "trader_id": str(item.get("uid", item.get("traderId", ""))),
                            "nickname": str(item.get("nickName", item.get("nickname", "Unknown"))),
                            "roi_30d": _to_float(item.get("roi", item.get("roiRate", 0))),
                            "pnl_30d": _to_float(item.get("pnl", item.get("totalPnl", 0))),
                            "win_rate": _to_float(item.get("winRate", 0)),
                            "max_drawdown": _to_float(item.get("maxDrawdown", 0)),
                            "copier_count": int(_to_float(item.get("followerCount", 0))),
                            "aum": _to_float(item.get("aum", 0)),
                            "trading_days": int(_to_float(item.get("tradingDays", 0))),
                            "source": "bingx_html",
                        })
                    if traders:
                        logger.info("BingX: extracted %d traders from __NEXT_DATA__", len(traders))
                        return traders
            except (json.JSONDecodeError, KeyError) as exc:
                logger.debug("BingX: __NEXT_DATA__ parse failed: %s", exc)

        # Fallback: regex scrape for trader cards in HTML
        # Look for trader profile links and ROI values
        trader_links = re.findall(
            r'/(?:en|zh-cn)/CopyTrading/(\d+)', html
        )
        roi_values = re.findall(
            r'(?:roi|ROI)["\s:]*["\s]*([+-]?\d+\.?\d*)%?', html
        )

        for i, tid in enumerate(set(trader_links)):
            roi = _to_float(roi_values[i]) / 100.0 if i < len(roi_values) else 0
            traders.append({
                "trader_id": tid,
                "nickname": f"BingX_Trader_{tid[:8]}",
                "roi_30d": roi,
                "pnl_30d": 0,
                "win_rate": 0,
                "max_drawdown": 0,
                "copier_count": 0,
                "aum": 0,
                "trading_days": 0,
                "source": "bingx_html_regex",
            })

        return traders[:limit]

    # ------------------------------------------------------------------
    # Trader positions
    # ------------------------------------------------------------------

    def fetch_trader_positions(self, trader_id: str) -> List[Dict]:
        """Fetch current open positions for a BingX trader."""
        positions = []

        for path in self.TRADER_POSITIONS_PATHS:
            url = f"{self.BASE_URL}{path}?uid={trader_id}&traderId={trader_id}"
            data = _http_get(url, headers={
                "Referer": f"https://bingx.com/en/CopyTrading/{trader_id}"
            })
            if data:
                positions = self._parse_positions(data)
                if positions:
                    break

        # Fallback: try trader detail page HTML
        if not positions:
            positions = self._scrape_trader_positions_html(trader_id)

        self.trader_positions[trader_id] = positions
        return positions

    def _parse_positions(self, data: dict) -> List[Dict]:
        """Parse position data from BingX API response."""
        positions = []
        raw_list = self._extract_list(data)

        for item in raw_list:
            try:
                symbol_raw = str(item.get("symbol", item.get("pair",
                                item.get("contractName", item.get("instId", "")))))
                symbol = _normalize_symbol(symbol_raw)
                if not symbol:
                    continue

                pos_side = str(item.get("positionSide", item.get("side",
                                item.get("posSide", "")))).upper()
                direction = "BUY" if pos_side in ("LONG", "BUY", "OPEN_LONG") else "SELL"

                positions.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": _to_float(item.get("avgPrice", item.get("entryPrice",
                                    item.get("openAvgPx", item.get("price", 0))))),
                    "leverage": _to_float(item.get("leverage", item.get("lever", 1))),
                    "unrealized_pnl": _to_float(item.get("unrealizedPnl",
                                    item.get("upl", item.get("profit", 0)))),
                    "margin_mode": str(item.get("marginMode", item.get("mgnMode", "cross"))),
                    "size": _to_float(item.get("positionAmt", item.get("size",
                                    item.get("amount", 0)))),
                    "raw": item,
                })
            except (TypeError, ValueError) as exc:
                logger.debug("BingX: position parse error: %s", exc)

        return positions

    def _scrape_trader_positions_html(self, trader_id: str) -> List[Dict]:
        """Scrape trader profile page for position data."""
        url = f"https://bingx.com/en/CopyTrading/{trader_id}"
        html = _http_get_html(url)
        if not html:
            return []

        positions = []
        # Try __NEXT_DATA__
        match = re.search(
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if match:
            try:
                next_data = json.loads(match.group(1))
                props = next_data.get("props", {}).get("pageProps", {})
                pos_data = (
                    props.get("positions")
                    or props.get("currentPositions")
                    or props.get("openPositions")
                    or props.get("data", {}).get("positions", [])
                )
                if isinstance(pos_data, list):
                    return self._parse_positions({"data": pos_data})
            except (json.JSONDecodeError, KeyError):
                pass

        return positions

    # ------------------------------------------------------------------
    # Trade history
    # ------------------------------------------------------------------

    def fetch_trade_history(self, trader_id: str, limit: int = 100) -> List[Dict]:
        """Fetch closed trade history for a BingX trader."""
        trades = []

        for path in self.TRADER_HISTORY_PATHS:
            url = (
                f"{self.BASE_URL}{path}"
                f"?uid={trader_id}&traderId={trader_id}"
                f"&pageNo=1&pageSize={limit}"
            )
            data = _http_get(url, headers={
                "Referer": f"https://bingx.com/en/CopyTrading/{trader_id}"
            })
            if data:
                trades = self._parse_trade_history(data)
                if trades:
                    break

        self.trader_history[trader_id] = trades
        return trades

    def _parse_trade_history(self, data: dict) -> List[Dict]:
        """Parse trade history from BingX API response."""
        trades = []
        raw_list = self._extract_list(data)

        for item in raw_list:
            try:
                symbol_raw = str(item.get("symbol", item.get("pair",
                                item.get("contractName", ""))))
                symbol = _normalize_symbol(symbol_raw)
                if not symbol:
                    continue

                pos_side = str(item.get("positionSide", item.get("side",
                                item.get("posSide", "")))).upper()
                direction = "BUY" if pos_side in ("LONG", "BUY", "OPEN_LONG") else "SELL"

                pnl = _to_float(item.get("pnl", item.get("profit",
                                item.get("realizedPnl", 0))))
                pnl_ratio = _to_float(item.get("pnlRatio", item.get("roiRate",
                                item.get("profitRate", 0))))

                open_time = _to_float(item.get("openTime", item.get("createTime", 0)))
                close_time = _to_float(item.get("closeTime", item.get("updateTime", 0)))
                hold_hours = 0
                if open_time > 0 and close_time > open_time:
                    hold_hours = (close_time - open_time) / 3_600_000.0

                trades.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": _to_float(item.get("openAvgPx",
                                    item.get("entryPrice", item.get("avgPrice", 0)))),
                    "exit_price": _to_float(item.get("closeAvgPx",
                                    item.get("closePrice", item.get("exitPrice", 0)))),
                    "leverage": _to_float(item.get("leverage", item.get("lever", 1))),
                    "pnl": pnl,
                    "pnl_ratio": pnl_ratio,
                    "hold_hours": round(hold_hours, 1),
                    "is_win": pnl > 0,
                })
            except (TypeError, ValueError) as exc:
                logger.debug("BingX: trade history parse error: %s", exc)

        return trades

    # ------------------------------------------------------------------
    # Performance stats
    # ------------------------------------------------------------------

    def calculate_stats(self, trader_id: str) -> Dict[str, Any]:
        """Calculate win rate, ROI, profit factor from trade history."""
        trades = self.trader_history.get(trader_id, [])
        trader_info = next(
            (t for t in self.traders if t.get("trader_id") == trader_id), {}
        )

        if not trades:
            # Use leaderboard stats if no history available
            return {
                "trader_id": trader_id,
                "nickname": trader_info.get("nickname", "Unknown"),
                "win_rate": trader_info.get("win_rate", 0),
                "roi_30d": trader_info.get("roi_30d", 0),
                "total_trades": 0,
                "profit_factor": 0,
                "avg_hold_hours": 0,
                "source": "bingx_leaderboard_stats",
            }

        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        total_wins_pnl = sum(t["pnl"] for t in wins)
        total_losses_pnl = abs(sum(t["pnl"] for t in losses))

        stats = {
            "trader_id": trader_id,
            "nickname": trader_info.get("nickname", "Unknown"),
            "win_rate": len(wins) / len(trades) if trades else 0,
            "roi_30d": trader_info.get("roi_30d", 0),
            "total_trades": len(trades),
            "profit_factor": (
                total_wins_pnl / total_losses_pnl
                if total_losses_pnl > 0 else float("inf") if total_wins_pnl > 0 else 0
            ),
            "avg_hold_hours": (
                sum(t["hold_hours"] for t in trades) / len(trades) if trades else 0
            ),
            "avg_leverage": (
                sum(t["leverage"] for t in trades) / len(trades) if trades else 0
            ),
            "source": "bingx_trade_history",
        }

        self.trader_stats[trader_id] = stats
        return stats

    # ------------------------------------------------------------------
    # Generate picks
    # ------------------------------------------------------------------

    def generate_picks(self, min_win_rate: float = 0.50,
                       min_roi: float = 0.30) -> List[Dict]:
        """
        Generate scanner-compatible picks from top BingX traders'
        current open positions.

        Filters traders by win_rate and ROI, then returns their
        current positions as picks with confidence scoring.
        """
        picks = []

        for trader in self.traders:
            tid = trader.get("trader_id", "")
            if not tid:
                continue

            wr = trader.get("win_rate", 0)
            roi = trader.get("roi_30d", 0)

            # Skip low-quality traders
            if wr < min_win_rate and roi < min_roi:
                continue

            positions = self.trader_positions.get(tid, [])
            stats = self.trader_stats.get(tid, {})

            for pos in positions:
                symbol = pos.get("symbol", "")
                if not symbol:
                    continue

                # Confidence based on trader quality metrics
                confidence = self._compute_confidence(trader, stats)

                picks.append({
                    "symbol": symbol,
                    "direction": pos.get("direction", "BUY"),
                    "confidence": round(confidence, 2),
                    "source": "bingx_copy_trader",
                    "strategy": "bingx_copy_trader",
                    "trader_id": tid,
                    "trader_name": trader.get("nickname", "Unknown"),
                    "trader_roi": round(roi, 4),
                    "trader_win_rate": round(wr, 4),
                    "entry_price": pos.get("entry_price", 0),
                    "leverage": pos.get("leverage", 1),
                    "take_profit": round(
                        pos["entry_price"] * (1.025 if pos["direction"] == "BUY" else 0.975), 6
                    ) if pos.get("entry_price", 0) > 0 else 0,
                    "stop_loss": round(
                        pos["entry_price"] * (0.985 if pos["direction"] == "BUY" else 1.015), 6
                    ) if pos.get("entry_price", 0) > 0 else 0,
                    "signal_type": pos.get("direction", "BUY"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return picks

    def _compute_confidence(self, trader: Dict, stats: Dict) -> float:
        """Compute confidence score (0.60-0.95) based on trader quality."""
        confidence = 0.60

        wr = trader.get("win_rate", 0)
        roi = trader.get("roi_30d", 0)
        pf = stats.get("profit_factor", 0)
        copiers = trader.get("copier_count", 0)

        # Win rate bonus
        if wr >= 0.70:
            confidence += 0.10
        elif wr >= 0.55:
            confidence += 0.05

        # ROI bonus
        if roi >= 1.0:
            confidence += 0.10
        elif roi >= 0.50:
            confidence += 0.05

        # Profit factor bonus
        if pf >= 2.0:
            confidence += 0.05
        elif pf >= 1.5:
            confidence += 0.02

        # Copier social proof
        if copiers >= 200:
            confidence += 0.05
        elif copiers >= 50:
            confidence += 0.02

        return min(confidence, 0.95)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self, limit: int = 15) -> List[Dict]:
        """
        Execute the full BingX scraping pipeline.
        Returns list of scanner-compatible picks.
        """
        logger.info("=== BingX Copy Trader Scraper - Starting ===")

        # 1. Fetch leaderboard
        self.fetch_leaderboard(limit=limit)
        if not self.traders:
            logger.warning("BingX: no traders found")
            return []
        logger.info("BingX: %d traders on leaderboard", len(self.traders))

        # 2. For each top trader, fetch positions and history
        for trader in self.traders[:10]:  # Cap at 10 to be polite
            tid = trader.get("trader_id", "")
            if not tid:
                continue

            self.fetch_trader_positions(tid)
            time.sleep(RATE_LIMIT_DELAY)

            self.fetch_trade_history(tid)
            time.sleep(RATE_LIMIT_DELAY)

            self.calculate_stats(tid)

        # 3. Generate picks
        picks = self.generate_picks()
        logger.info("BingX: generated %d picks from %d traders",
                     len(picks), len(self.traders))

        return picks

    # ------------------------------------------------------------------
    # Copin.io fallback
    # ------------------------------------------------------------------

    def _fetch_from_copin(self, protocol: str = "BINGX",
                          limit: int = 20) -> List[Dict]:
        """
        Fetch trader data from Copin.io aggregator as ultimate fallback.
        Copin.io aggregates BingX, Gate.io, and other exchange leaderboards.
        """
        url = "https://api.copin.io/graphql"
        # Copin.io GraphQL query for top traders
        query = {
            "query": """
                query GetTraders($protocol: String!, $limit: Int!) {
                    traders(
                        protocol: $protocol
                        sortBy: "pnl30d"
                        sortOrder: "desc"
                        limit: $limit
                    ) {
                        id
                        account
                        pnl30d
                        roi30d
                        winRate
                        maxDrawdown
                        totalTrades
                    }
                }
            """,
            "variables": {"protocol": protocol, "limit": limit}
        }

        data = _http_post(url, query)
        if not data:
            # Try REST API fallback
            rest_url = (
                f"https://api.copin.io/{protocol.lower()}/top-traders"
                f"?sortBy=pnl30d&limit={limit}"
            )
            data = _http_get(rest_url)

        if not data:
            return []

        traders = []
        raw_list = self._extract_list(data)
        for item in raw_list:
            traders.append({
                "trader_id": str(item.get("id", item.get("account", ""))),
                "nickname": str(item.get("account", "Unknown"))[:16],
                "roi_30d": _to_float(item.get("roi30d", 0)),
                "pnl_30d": _to_float(item.get("pnl30d", 0)),
                "win_rate": _to_float(item.get("winRate", 0)),
                "max_drawdown": _to_float(item.get("maxDrawdown", 0)),
                "copier_count": 0,
                "aum": 0,
                "trading_days": 0,
                "source": f"copin_{protocol.lower()}",
            })

        return traders

    @staticmethod
    def _extract_list(data: Any) -> list:
        """Extract list from nested API response."""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ["data", "result", "list", "traders", "rows",
                     "items", "positions", "records"]:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for inner_key in ["list", "rows", "data", "items", "records"]:
                    inner = val.get(inner_key)
                    if isinstance(inner, list):
                        return inner
        return []


# ===========================================================================
#
#  GATE.IO COPY TRADER SCRAPER
#
# ===========================================================================

class GateIOScraper:
    """
    Scrapes Gate.io copy-trading leaderboard for top trader positions.

    Strategy:
    1. PRIMARY: Gate.io internal frontend API (SSR data from /copytrading page)
       - Star leaders: /api/v1/copytrade/getFuturesStarLeaders
       - Leader list:  /api/v1/copytrade/getFuturesLeaderList
       - Leader detail: /api/v1/copytrade/getFuturesLeaderDetail
       - Trader profile: /copytrading/trader/futures/{leader_id}
       These endpoints power the Gate.io copy trading page and are
       pre-rendered as JSON in the page's SSR fallback data.

    2. FALLBACK A: HTML scrape of https://www.gate.com/copytrading
       - Parse embedded props/fallback JSON for trader data

    3. FALLBACK B: Copin.io API (aggregates Gate.io data)

    Authentication: NONE required (all public pages/endpoints).
    Rate limit: ~1 req/sec recommended.

    Confirmed data fields per trader (from SSR analysis):
      leader_id, nickname, profit_rate, win_rate, max_drawdown,
      aum, sharp_ratio, follower_count, tier_level, trading_tags
    """

    BASE_URL = "https://www.gate.com"

    # Internal API paths (discovered from SSR fallback data)
    LEADER_LIST_PATHS = [
        "/api/v1/copytrade/getFuturesLeaderList",
        "/api/copytrade/futures/leader/list",
    ]

    STAR_LEADERS_PATHS = [
        "/api/v1/copytrade/getFuturesStarLeaders",
        "/api/copytrade/futures/star/leaders",
    ]

    LEADER_DETAIL_PATHS = [
        "/api/v1/copytrade/getFuturesLeaderDetail",
        "/api/copytrade/futures/leader/detail",
    ]

    LEADER_POSITIONS_PATHS = [
        "/api/v1/copytrade/getFuturesLeaderPositions",
        "/api/copytrade/futures/leader/positions",
    ]

    LEADER_HISTORY_PATHS = [
        "/api/v1/copytrade/getFuturesLeaderHistory",
        "/api/copytrade/futures/leader/history",
    ]

    def __init__(self):
        self.traders: List[Dict] = []
        self.trader_positions: Dict[str, List[Dict]] = {}
        self.trader_history: Dict[str, List[Dict]] = {}
        self.trader_stats: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Leaderboard fetch
    # ------------------------------------------------------------------

    def fetch_leaderboard(self, limit: int = 20,
                          sort_by: str = "follow_profit") -> List[Dict]:
        """
        Fetch top traders from Gate.io copy trading leaderboard.

        sort_by options: "follow_profit", "aum", "sharp_ratio"
        """
        traders = []

        # Strategy 1: Try internal API endpoints
        for path in self.LEADER_LIST_PATHS:
            url = (
                f"{self.BASE_URL}{path}"
                f"?cycle=month&order_by={sort_by}"
                f"&page=1&page_size={limit}&status=running"
            )
            logger.info("Gate.io: trying leaderboard at %s", url)
            data = _http_get(url, headers={
                "Referer": "https://www.gate.com/copytrading",
            })
            if data:
                traders = self._parse_leader_list(data)
                if traders:
                    logger.info("Gate.io: got %d traders from API", len(traders))
                    break

        # Strategy 1b: Try star leaders endpoint
        if not traders:
            for path in self.STAR_LEADERS_PATHS:
                url = f"{self.BASE_URL}{path}?lang=en"
                data = _http_get(url, headers={
                    "Referer": "https://www.gate.com/copytrading",
                })
                if data:
                    traders = self._parse_leader_list(data)
                    if traders:
                        logger.info("Gate.io: got %d star traders", len(traders))
                        break

        # Strategy 2: HTML scrape with SSR data extraction
        if not traders:
            logger.info("Gate.io: API failed, trying HTML scrape...")
            traders = self._scrape_leaderboard_html(limit)

        # Strategy 3: Copin.io fallback
        if not traders:
            logger.info("Gate.io: HTML failed, trying Copin.io...")
            traders = self._fetch_from_copin("GATE", limit)

        self.traders = traders[:limit]
        return self.traders

    def _parse_leader_list(self, data: dict) -> List[Dict]:
        """Parse Gate.io leader list API response."""
        traders = []
        raw_list = self._extract_list(data)

        for item in raw_list:
            try:
                leader_id = str(item.get("leader_id", item.get("leaderId",
                                item.get("id", item.get("uid", "")))))
                if not leader_id:
                    continue

                # Gate.io returns profit_rate as decimal (e.g., 1.5 = 150%)
                profit_rate = _to_float(item.get("profit_rate",
                                item.get("profitRate", item.get("roi", 0))))
                win_rate = _to_float(item.get("win_rate",
                                item.get("winRate", item.get("winRatio", 0))))
                max_dd = _to_float(item.get("max_drawdown",
                                item.get("maxDrawdown", item.get("mdd", 0))))
                aum = _to_float(item.get("aum", item.get("assets", 0)))
                sharpe = _to_float(item.get("sharp_ratio",
                                item.get("sharpeRatio", item.get("sharpe", 0))))
                followers = int(_to_float(item.get("follower_count",
                                item.get("followerCount",
                                item.get("copier_count", item.get("followers", 0))))))
                nickname = str(item.get("nickname", item.get("nickName",
                                item.get("name", f"Gate_Trader_{leader_id}"))))

                trader = {
                    "trader_id": leader_id,
                    "nickname": nickname,
                    "roi_30d": profit_rate,
                    "pnl_30d": _to_float(item.get("pnl", item.get("totalProfit", 0))),
                    "win_rate": win_rate if win_rate <= 1 else win_rate / 100.0,
                    "max_drawdown": max_dd if max_dd <= 1 else max_dd / 100.0,
                    "aum": aum,
                    "sharpe_ratio": sharpe,
                    "copier_count": followers,
                    "trading_days": int(_to_float(item.get("trading_days",
                                    item.get("tradingDays", item.get("days", 0))))),
                    "source": "gateio",
                    "profile_url": f"https://www.gate.com/copytrading/trader/futures/{leader_id}",
                    "raw": item,
                }
                traders.append(trader)

            except (TypeError, ValueError, KeyError) as exc:
                logger.debug("Gate.io: skipping trader parse: %s", exc)

        return traders

    def _scrape_leaderboard_html(self, limit: int = 20) -> List[Dict]:
        """
        Scrape Gate.io copy trading page HTML for embedded SSR data.
        Gate.io uses Next.js/Nuxt with preloaded fallback JSON in the page.
        """
        url = "https://www.gate.com/copytrading"
        html = _http_get_html(url)
        if not html:
            return []

        traders = []

        # Gate.io embeds data in a props/fallback JSON structure
        # Look for patterns like: "getFuturesLeaderList|..." or __NEXT_DATA__
        patterns = [
            # Next.js data
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            # Nuxt data
            r'<script[^>]*>window\.__NUXT__\s*=\s*(.*?)</script>',
            # Generic JSON state
            r'"fallback"\s*:\s*(\{[^}]{100,})',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                continue

            try:
                json_str = match.group(1)
                # Clean up if needed
                if json_str.startswith("(") and json_str.endswith(")"):
                    json_str = json_str[1:-1]

                data = json.loads(json_str)

                # Navigate structure for trader data
                leader_data = self._find_leader_data_in_json(data)
                if leader_data:
                    traders = self._parse_leader_list({"data": leader_data})
                    if traders:
                        logger.info("Gate.io: extracted %d traders from SSR HTML",
                                     len(traders))
                        return traders[:limit]
            except (json.JSONDecodeError, KeyError) as exc:
                logger.debug("Gate.io: SSR parse failed for pattern: %s", exc)

        # Fallback: extract leader_ids from HTML links
        leader_ids = re.findall(
            r'/copytrading/trader/futures/(\d+)', html
        )
        for lid in set(leader_ids):
            traders.append({
                "trader_id": lid,
                "nickname": f"Gate_Trader_{lid}",
                "roi_30d": 0,
                "pnl_30d": 0,
                "win_rate": 0,
                "max_drawdown": 0,
                "aum": 0,
                "sharpe_ratio": 0,
                "copier_count": 0,
                "trading_days": 0,
                "source": "gateio_html_regex",
                "profile_url": f"https://www.gate.com/copytrading/trader/futures/{lid}",
            })

        return traders[:limit]

    def _find_leader_data_in_json(self, data: Any, depth: int = 0) -> Optional[list]:
        """Recursively search JSON structure for leader data arrays."""
        if depth > 5:
            return None
        if isinstance(data, list) and len(data) > 0:
            # Check if items look like trader data
            if isinstance(data[0], dict):
                if any(k in data[0] for k in
                       ["leader_id", "leaderId", "profit_rate", "profitRate",
                        "win_rate", "winRate"]):
                    return data
        if isinstance(data, dict):
            # Check known keys first
            for key in ["getFuturesStarLeaders", "getFuturesLeaderList",
                        "leaderList", "starLeaders", "leaders", "traders"]:
                # Gate.io uses pipe-delimited keys like "getFuturesLeaderList|cycle=month..."
                for dkey in data:
                    if key in str(dkey):
                        val = data[dkey]
                        if isinstance(val, list):
                            return val
                        if isinstance(val, dict):
                            result = self._find_leader_data_in_json(val, depth + 1)
                            if result:
                                return result
            # Generic search
            for val in data.values():
                if isinstance(val, (dict, list)):
                    result = self._find_leader_data_in_json(val, depth + 1)
                    if result:
                        return result
        return None

    # ------------------------------------------------------------------
    # Trader positions
    # ------------------------------------------------------------------

    def fetch_trader_positions(self, leader_id: str) -> List[Dict]:
        """Fetch current open positions for a Gate.io lead trader."""
        positions = []

        # Try API endpoints
        for path in self.LEADER_POSITIONS_PATHS:
            url = f"{self.BASE_URL}{path}?leader_id={leader_id}&leaderId={leader_id}"
            data = _http_get(url, headers={
                "Referer": f"https://www.gate.com/copytrading/trader/futures/{leader_id}",
            })
            if data:
                positions = self._parse_positions(data)
                if positions:
                    break

        # Fallback: scrape trader profile page
        if not positions:
            positions = self._scrape_trader_page(leader_id)

        self.trader_positions[leader_id] = positions
        return positions

    def _parse_positions(self, data: dict) -> List[Dict]:
        """Parse position data from Gate.io API response."""
        positions = []
        raw_list = self._extract_list(data)

        for item in raw_list:
            try:
                symbol_raw = str(item.get("contract", item.get("symbol",
                                item.get("pair", item.get("instrument", "")))))
                symbol = _normalize_symbol(symbol_raw)
                if not symbol:
                    continue

                # Gate.io uses "long"/"short" or "buy"/"sell"
                side = str(item.get("side", item.get("direction",
                                item.get("posSide", "")))).upper()
                direction = "BUY" if side in ("LONG", "BUY") else "SELL"

                positions.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": _to_float(item.get("entry_price",
                                    item.get("entryPrice", item.get("avgPrice",
                                    item.get("openPrice", 0))))),
                    "leverage": _to_float(item.get("leverage", item.get("lever", 1))),
                    "unrealized_pnl": _to_float(item.get("unrealised_pnl",
                                    item.get("unrealizedPnl", item.get("upl", 0)))),
                    "size": _to_float(item.get("size", item.get("amount",
                                    item.get("quantity", 0)))),
                    "margin_mode": str(item.get("mode", item.get("marginMode", "cross"))),
                    "raw": item,
                })
            except (TypeError, ValueError) as exc:
                logger.debug("Gate.io: position parse error: %s", exc)

        return positions

    def _scrape_trader_page(self, leader_id: str) -> List[Dict]:
        """Scrape a Gate.io trader profile page for position data."""
        url = f"https://www.gate.com/copytrading/trader/futures/{leader_id}"
        html = _http_get_html(url)
        if not html:
            return []

        # Try to find embedded JSON with position data
        for pattern in [
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r'"positions"\s*:\s*(\[[^\]]*\])',
            r'"currentPositions"\s*:\s*(\[[^\]]*\])',
        ]:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    raw = match.group(1)
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        # Navigate Next.js structure
                        props = data.get("props", {}).get("pageProps", {})
                        pos_data = (
                            props.get("positions")
                            or props.get("currentPositions")
                            or props.get("leaderPositions")
                        )
                        if isinstance(pos_data, list):
                            return self._parse_positions({"data": pos_data})
                    elif isinstance(data, list):
                        return self._parse_positions({"data": data})
                except (json.JSONDecodeError, KeyError):
                    pass

        return []

    # ------------------------------------------------------------------
    # Trade history
    # ------------------------------------------------------------------

    def fetch_trade_history(self, leader_id: str, limit: int = 100) -> List[Dict]:
        """Fetch closed trade history for a Gate.io lead trader."""
        trades = []

        for path in self.LEADER_HISTORY_PATHS:
            url = (
                f"{self.BASE_URL}{path}"
                f"?leader_id={leader_id}&leaderId={leader_id}"
                f"&page=1&page_size={limit}"
            )
            data = _http_get(url, headers={
                "Referer": f"https://www.gate.com/copytrading/trader/futures/{leader_id}",
            })
            if data:
                trades = self._parse_trade_history(data)
                if trades:
                    break

        self.trader_history[leader_id] = trades
        return trades

    def _parse_trade_history(self, data: dict) -> List[Dict]:
        """Parse trade history from Gate.io API response."""
        trades = []
        raw_list = self._extract_list(data)

        for item in raw_list:
            try:
                symbol_raw = str(item.get("contract", item.get("symbol",
                                item.get("pair", ""))))
                symbol = _normalize_symbol(symbol_raw)
                if not symbol:
                    continue

                side = str(item.get("side", item.get("direction",
                                item.get("posSide", "")))).upper()
                direction = "BUY" if side in ("LONG", "BUY") else "SELL"

                pnl = _to_float(item.get("pnl", item.get("profit",
                                item.get("realizedPnl", 0))))
                pnl_ratio = _to_float(item.get("pnl_ratio",
                                item.get("profitRate", item.get("roiRate", 0))))

                open_time = _to_float(item.get("open_time",
                                item.get("openTime", item.get("createTime", 0))))
                close_time = _to_float(item.get("close_time",
                                item.get("closeTime", item.get("updateTime", 0))))
                hold_hours = 0
                if open_time > 0 and close_time > open_time:
                    # Gate.io may use seconds or milliseconds
                    divisor = 3_600.0 if open_time < 1e12 else 3_600_000.0
                    hold_hours = (close_time - open_time) / divisor

                trades.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": _to_float(item.get("entry_price",
                                    item.get("openPrice", item.get("avgPrice", 0)))),
                    "exit_price": _to_float(item.get("close_price",
                                    item.get("closePrice", item.get("exitPrice", 0)))),
                    "leverage": _to_float(item.get("leverage", item.get("lever", 1))),
                    "pnl": pnl,
                    "pnl_ratio": pnl_ratio,
                    "hold_hours": round(hold_hours, 1),
                    "is_win": pnl > 0,
                })
            except (TypeError, ValueError) as exc:
                logger.debug("Gate.io: trade history parse error: %s", exc)

        return trades

    # ------------------------------------------------------------------
    # Performance stats
    # ------------------------------------------------------------------

    def calculate_stats(self, leader_id: str) -> Dict[str, Any]:
        """Calculate win rate, ROI, profit factor from trade history."""
        trades = self.trader_history.get(leader_id, [])
        trader_info = next(
            (t for t in self.traders if t.get("trader_id") == leader_id), {}
        )

        if not trades:
            return {
                "trader_id": leader_id,
                "nickname": trader_info.get("nickname", "Unknown"),
                "win_rate": trader_info.get("win_rate", 0),
                "roi_30d": trader_info.get("roi_30d", 0),
                "sharpe_ratio": trader_info.get("sharpe_ratio", 0),
                "total_trades": 0,
                "profit_factor": 0,
                "avg_hold_hours": 0,
                "source": "gateio_leaderboard_stats",
            }

        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]
        total_wins_pnl = sum(t["pnl"] for t in wins)
        total_losses_pnl = abs(sum(t["pnl"] for t in losses))

        stats = {
            "trader_id": leader_id,
            "nickname": trader_info.get("nickname", "Unknown"),
            "win_rate": len(wins) / len(trades) if trades else 0,
            "roi_30d": trader_info.get("roi_30d", 0),
            "sharpe_ratio": trader_info.get("sharpe_ratio", 0),
            "total_trades": len(trades),
            "profit_factor": (
                total_wins_pnl / total_losses_pnl
                if total_losses_pnl > 0 else float("inf") if total_wins_pnl > 0 else 0
            ),
            "avg_hold_hours": (
                sum(t["hold_hours"] for t in trades) / len(trades) if trades else 0
            ),
            "avg_leverage": (
                sum(t["leverage"] for t in trades) / len(trades) if trades else 0
            ),
            "source": "gateio_trade_history",
        }

        self.trader_stats[leader_id] = stats
        return stats

    # ------------------------------------------------------------------
    # Generate picks
    # ------------------------------------------------------------------

    def generate_picks(self, min_win_rate: float = 0.50,
                       min_roi: float = 0.30) -> List[Dict]:
        """
        Generate scanner-compatible picks from top Gate.io traders'
        current open positions.
        """
        picks = []

        for trader in self.traders:
            tid = trader.get("trader_id", "")
            if not tid:
                continue

            wr = trader.get("win_rate", 0)
            roi = trader.get("roi_30d", 0)
            sharpe = trader.get("sharpe_ratio", 0)

            # Skip low-quality traders (relax if Sharpe is good)
            if wr < min_win_rate and roi < min_roi and sharpe < 1.0:
                continue

            positions = self.trader_positions.get(tid, [])
            stats = self.trader_stats.get(tid, {})

            for pos in positions:
                symbol = pos.get("symbol", "")
                if not symbol:
                    continue

                confidence = self._compute_confidence(trader, stats)

                picks.append({
                    "symbol": symbol,
                    "direction": pos.get("direction", "BUY"),
                    "confidence": round(confidence, 2),
                    "source": "gateio_copy_trader",
                    "strategy": "gateio_copy_trader",
                    "trader_id": tid,
                    "trader_name": trader.get("nickname", "Unknown"),
                    "trader_roi": round(roi, 4),
                    "trader_win_rate": round(wr, 4),
                    "trader_sharpe": round(sharpe, 2),
                    "entry_price": pos.get("entry_price", 0),
                    "leverage": pos.get("leverage", 1),
                    "take_profit": round(
                        pos["entry_price"] * (1.025 if pos["direction"] == "BUY" else 0.975), 6
                    ) if pos.get("entry_price", 0) > 0 else 0,
                    "stop_loss": round(
                        pos["entry_price"] * (0.985 if pos["direction"] == "BUY" else 1.015), 6
                    ) if pos.get("entry_price", 0) > 0 else 0,
                    "signal_type": pos.get("direction", "BUY"),
                    "profile_url": trader.get("profile_url", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return picks

    def _compute_confidence(self, trader: Dict, stats: Dict) -> float:
        """Compute confidence score (0.60-0.95) based on trader quality."""
        confidence = 0.60

        wr = trader.get("win_rate", 0)
        roi = trader.get("roi_30d", 0)
        sharpe = trader.get("sharpe_ratio", 0)
        pf = stats.get("profit_factor", 0)
        copiers = trader.get("copier_count", 0)

        # Win rate bonus
        if wr >= 0.70:
            confidence += 0.10
        elif wr >= 0.55:
            confidence += 0.05

        # ROI bonus
        if roi >= 1.0:
            confidence += 0.08
        elif roi >= 0.50:
            confidence += 0.04

        # Sharpe ratio bonus (Gate.io provides this)
        if sharpe >= 3.0:
            confidence += 0.07
        elif sharpe >= 2.0:
            confidence += 0.04
        elif sharpe >= 1.0:
            confidence += 0.02

        # Profit factor bonus
        if pf >= 2.0:
            confidence += 0.05
        elif pf >= 1.5:
            confidence += 0.02

        # Copier social proof
        if copiers >= 200:
            confidence += 0.05
        elif copiers >= 50:
            confidence += 0.02

        return min(confidence, 0.95)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self, limit: int = 15) -> List[Dict]:
        """
        Execute the full Gate.io scraping pipeline.
        Returns list of scanner-compatible picks.
        """
        logger.info("=== Gate.io Copy Trader Scraper - Starting ===")

        # 1. Fetch leaderboard
        self.fetch_leaderboard(limit=limit)
        if not self.traders:
            logger.warning("Gate.io: no traders found")
            return []
        logger.info("Gate.io: %d traders on leaderboard", len(self.traders))

        # 2. For each top trader, fetch positions and history
        for trader in self.traders[:10]:
            tid = trader.get("trader_id", "")
            if not tid:
                continue

            self.fetch_trader_positions(tid)
            time.sleep(RATE_LIMIT_DELAY)

            self.fetch_trade_history(tid)
            time.sleep(RATE_LIMIT_DELAY)

            self.calculate_stats(tid)

        # 3. Generate picks
        picks = self.generate_picks()
        logger.info("Gate.io: generated %d picks from %d traders",
                     len(picks), len(self.traders))

        return picks

    # ------------------------------------------------------------------
    # Copin.io fallback (shared approach)
    # ------------------------------------------------------------------

    def _fetch_from_copin(self, protocol: str = "GATE",
                          limit: int = 20) -> List[Dict]:
        """Fetch from Copin.io aggregator as ultimate fallback."""
        url = "https://api.copin.io/graphql"
        query = {
            "query": """
                query GetTraders($protocol: String!, $limit: Int!) {
                    traders(
                        protocol: $protocol
                        sortBy: "pnl30d"
                        sortOrder: "desc"
                        limit: $limit
                    ) {
                        id
                        account
                        pnl30d
                        roi30d
                        winRate
                        maxDrawdown
                        totalTrades
                    }
                }
            """,
            "variables": {"protocol": protocol, "limit": limit}
        }

        data = _http_post(url, query)
        if not data:
            rest_url = (
                f"https://api.copin.io/{protocol.lower()}/top-traders"
                f"?sortBy=pnl30d&limit={limit}"
            )
            data = _http_get(rest_url)

        if not data:
            return []

        traders = []
        raw_list = self._extract_list(data)
        for item in raw_list:
            traders.append({
                "trader_id": str(item.get("id", item.get("account", ""))),
                "nickname": str(item.get("account", "Unknown"))[:16],
                "roi_30d": _to_float(item.get("roi30d", 0)),
                "pnl_30d": _to_float(item.get("pnl30d", 0)),
                "win_rate": _to_float(item.get("winRate", 0)),
                "max_drawdown": _to_float(item.get("maxDrawdown", 0)),
                "sharpe_ratio": 0,
                "copier_count": 0,
                "aum": 0,
                "trading_days": 0,
                "source": f"copin_{protocol.lower()}",
            })

        return traders

    @staticmethod
    def _extract_list(data: Any) -> list:
        """Extract list from nested API response."""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ["data", "result", "list", "leaders", "traders",
                     "rows", "items", "positions", "records"]:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for inner_key in ["list", "rows", "data", "items",
                                  "leaders", "records"]:
                    inner = val.get(inner_key)
                    if isinstance(inner, list):
                        return inner
        return []


# ===========================================================================
#
#  PUBLIC API -- Scanner integration
#
# ===========================================================================

def scan_bingx_traders() -> List[Dict]:
    """
    Run the BingX copy trader scraper and return picks.
    Safe to call from production_scanner.py.
    """
    try:
        scraper = BingXScraper()
        picks = scraper.run(limit=15)
        logger.info("BingX scraper returned %d picks", len(picks))
        return picks
    except Exception as exc:
        logger.error("BingX scraper failed: %s", exc, exc_info=True)
        return []


def scan_gateio_traders() -> List[Dict]:
    """
    Run the Gate.io copy trader scraper and return picks.
    Safe to call from production_scanner.py.
    """
    try:
        scraper = GateIOScraper()
        picks = scraper.run(limit=15)
        logger.info("Gate.io scraper returned %d picks", len(picks))
        return picks
    except Exception as exc:
        logger.error("Gate.io scraper failed: %s", exc, exc_info=True)
        return []


def scan_all_copy_traders() -> List[Dict]:
    """
    Run both BingX and Gate.io scrapers and merge picks.
    Deduplicates by symbol+direction.
    """
    all_picks = []

    bingx_picks = scan_bingx_traders()
    all_picks.extend(bingx_picks)

    gateio_picks = scan_gateio_traders()
    all_picks.extend(gateio_picks)

    # Deduplicate: if same symbol+direction from both, keep higher confidence
    seen = {}
    for pick in all_picks:
        key = (pick["symbol"], pick["direction"])
        if key not in seen or pick["confidence"] > seen[key]["confidence"]:
            seen[key] = pick

    deduped = list(seen.values())
    deduped.sort(key=lambda x: x["confidence"], reverse=True)

    logger.info(
        "Combined copy trader picks: %d (BingX: %d, Gate.io: %d, deduped: %d)",
        len(all_picks), len(bingx_picks), len(gateio_picks), len(deduped)
    )

    return deduped


# ===========================================================================
# CLI entry point
# ===========================================================================

def main() -> None:
    """Run both scrapers as a standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 70)
    print("  BingX + Gate.io Copy Trader Scrapers")
    print("=" * 70)

    picks = scan_all_copy_traders()

    if picks:
        print(f"\n=== {len(picks)} PICKS ===\n")
        for i, p in enumerate(picks, 1):
            print(
                f"  {i}. {p['signal_type']} {p['symbol']} "
                f"@ {p.get('entry_price', '?')} "
                f"(conf: {p['confidence']}, src: {p['source']}, "
                f"trader: {p.get('trader_name', p.get('trader_id', '?'))})"
            )
    else:
        print("\nNo picks generated. APIs may be blocked or no qualifying traders.")

    # Save results
    output_file = DATA_DIR / "bingx_gateio_picks.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "picks": picks,
            "total": len(picks),
        }, f, indent=2, default=str)
    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()

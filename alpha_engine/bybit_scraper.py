"""
bybit_scraper.py - Bybit Copy Trading Leaderboard Scraper
==========================================================
Fetches top copy-traders from Bybit's internal beehive API,
retrieves their current open positions, and generates trading signals.

Confirmed API endpoints (reverse-engineered from Bybit's web frontend):
  BASE: https://api2.bybit.com/fapi/beehive/public/v1
  - GET /common/dynamic-leader-list   (leaderboard -- top traders by ROI)
  - GET /common/position/list         (trader's current open positions)
  - GET /common/leader/detail         (trader profile + stats)
  - GET /common/order/list            (trader's trade history)

These are PUBLIC endpoints (no API key required) but are behind Akamai CDN
protection. They require:
  1. A valid browser User-Agent header
  2. A session that first hits the Bybit website to collect cookies
  3. Proper Origin/Referer headers

If the beehive API is blocked (403/geo-restricted), the scraper falls back
to the Bybit V5 public market API for price validation only.

Output format: list of dicts with keys:
  symbol, direction, confidence, source, trader_id, trader_roi, entry_price

Author: Alpha Engine
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BYBIT_BEEHIVE_BASE = "https://api2.bybit.com/fapi/beehive/public/v1"
BYBIT_V5_BASE = "https://api.bybit.com/v5"
BYBIT_WEB_URL = "https://www.bybit.com/copyTrading/en/leader-board"

# Duration filters for leaderboard
DURATION_7D = "DATA_DURATION_SEVEN_DAY"
DURATION_30D = "DATA_DURATION_THIRTY_DAY"
DURATION_90D = "DATA_DURATION_NINETY_DAY"

# Sort fields
SORT_BY_ROI = "LEADER_SORT_FIELD_SORT_ROI"
SORT_BY_PNL = "LEADER_SORT_FIELD_SORT_PNL"
SORT_BY_WIN_RATE = "LEADER_SORT_FIELD_SORT_WIN_RATE"
SORT_BY_FOLLOWERS = "LEADER_SORT_FIELD_SORT_FOLLOWERS"

# Quality thresholds
MIN_ROI_PCT = 20.0         # Minimum 20% ROI in selected period
MIN_WIN_RATE = 0.50        # 50%+ win rate
MIN_FOLLOWERS = 10         # At least 10 followers (social proof)
MAX_DRAWDOWN_PCT = 50.0    # Skip traders with >50% max drawdown

# Rate limiting
REQUEST_DELAY = 0.6        # seconds between API requests
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

# Browser-like headers (required for beehive API)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://www.bybit.com",
    "Referer": "https://www.bybit.com/",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _normalize_symbol(symbol: str) -> str:
    """Normalize Bybit symbol to standard format (e.g., BTCUSDT)."""
    # Bybit uses BTCUSDT format already, but clean up any edge cases
    symbol = symbol.upper().strip()
    # Remove trailing PERP suffix if present
    if symbol.endswith("PERP"):
        symbol = symbol[:-4]
    return symbol


# ---------------------------------------------------------------------------
# BybitScraper class
# ---------------------------------------------------------------------------

class BybitScraper:
    """
    Scrapes Bybit copy trading leaderboard for top trader positions.

    Flow:
    1. Initialize session (hit Bybit website first to get cookies)
    2. Fetch leaderboard (top traders sorted by ROI)
    3. For each qualifying trader, fetch their open positions
    4. Optionally fetch trade history for win rate / profit factor calc
    5. Generate consensus picks in standardized format

    Usage:
        scraper = BybitScraper()
        picks = scraper.run()
        # picks = [{"symbol": "BTCUSDT", "direction": "BUY", ...}, ...]
    """

    def __init__(
        self,
        duration: str = DURATION_30D,
        max_traders: int = 50,
        min_roi: float = MIN_ROI_PCT,
        min_win_rate: float = MIN_WIN_RATE,
    ):
        self.duration = duration
        self.max_traders = max_traders
        self.min_roi = min_roi
        self.min_win_rate = min_win_rate

        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

        self._api_available = False
        self._traders_raw: List[Dict] = []
        self._trader_details: Dict[str, Dict] = {}
        self._trader_positions: Dict[str, List[Dict]] = {}
        self._trader_history: Dict[str, List[Dict]] = {}

    # ------------------------------------------------------------------
    # Session initialization
    # ------------------------------------------------------------------

    def _init_session(self) -> bool:
        """
        Hit the Bybit website first to collect cookies/session tokens.
        The beehive API requires a valid browser session.
        """
        try:
            resp = self.session.get(
                BYBIT_WEB_URL,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                logger.info("Bybit session initialized (cookies acquired)")
                self._api_available = True
                return True
            else:
                logger.warning(
                    "Bybit session init returned %d", resp.status_code
                )
        except requests.RequestException as exc:
            logger.warning("Bybit session init failed: %s", exc)

        self._api_available = False
        return False

    # ------------------------------------------------------------------
    # HTTP helper with retries and rate limiting
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        GET JSON from Bybit beehive API with retries and rate limiting.
        Returns parsed JSON dict or None on failure.
        """
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(REQUEST_DELAY)
                resp = self.session.get(
                    url, params=params, timeout=REQUEST_TIMEOUT
                )

                if resp.status_code == 403:
                    logger.warning(
                        "Bybit API returned 403 (CDN block) for %s "
                        "(attempt %d/%d)",
                        url.split("/")[-1], attempt + 1, MAX_RETRIES,
                    )
                    # Try re-initializing session
                    if attempt == 0:
                        self._init_session()
                    time.sleep(2.0 * (attempt + 1))
                    continue

                if resp.status_code == 429:
                    wait = 5.0 * (attempt + 1)
                    logger.warning(
                        "Rate limited by Bybit, waiting %.1fs", wait
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    logger.warning(
                        "Bybit API returned %d for %s",
                        resp.status_code, url.split("/")[-1],
                    )
                    continue

                data = resp.json()

                # Bybit beehive API uses retCode/retMsg pattern
                ret_code = data.get("retCode") or data.get("ret_code", 0)
                if ret_code != 0:
                    logger.warning(
                        "Bybit API error: code=%s msg=%s",
                        ret_code, data.get("retMsg", data.get("ret_msg", "")),
                    )
                    return None

                return data

            except requests.exceptions.Timeout:
                logger.warning(
                    "Bybit API timeout for %s (attempt %d/%d)",
                    url.split("/")[-1], attempt + 1, MAX_RETRIES,
                )
            except requests.exceptions.ConnectionError as exc:
                logger.warning("Bybit connection error: %s", exc)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Bybit JSON parse error: %s", exc)

            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))

        return None

    # ------------------------------------------------------------------
    # 1. Fetch leaderboard (top traders)
    # ------------------------------------------------------------------

    def fetch_leaderboard(
        self,
        sort_field: str = SORT_BY_ROI,
        page_size: int = 50,
    ) -> List[Dict]:
        """
        Fetch the copy trading leaderboard from Bybit.

        Endpoint: GET /common/dynamic-leader-list
        Params:
          - pageNo: page number (1-indexed)
          - pageSize: traders per page (max 50)
          - sortType: SORT_TYPE_DESC
          - dataDuration: DATA_DURATION_THIRTY_DAY etc.
          - sortField: LEADER_SORT_FIELD_SORT_ROI etc.

        Returns list of trader dicts with fields:
          leaderMark, nickName, roi, totalPnl, winRate, followerCount,
          maxDrawdown, etc.
        """
        all_traders = []
        page = 1
        pages_needed = (self.max_traders + page_size - 1) // page_size

        for page in range(1, pages_needed + 1):
            url = f"{BYBIT_BEEHIVE_BASE}/common/dynamic-leader-list"
            params = {
                "pageNo": page,
                "pageSize": min(page_size, 50),
                "sortType": "SORT_TYPE_DESC",
                "dataDuration": self.duration,
                "sortField": sort_field,
            }

            data = self._get(url, params)
            if not data:
                logger.warning(
                    "Leaderboard page %d failed, stopping pagination", page
                )
                break

            result = data.get("result", {})
            leaders = result.get("leaderDetails", [])

            if not leaders:
                break

            all_traders.extend(leaders)
            logger.info(
                "Leaderboard page %d: %d traders", page, len(leaders)
            )

            if len(leaders) < page_size:
                break  # Last page

        self._traders_raw = all_traders[:self.max_traders]
        logger.info(
            "Fetched %d traders from Bybit leaderboard", len(self._traders_raw)
        )
        return self._traders_raw

    # ------------------------------------------------------------------
    # 2. Get trader detail / profile
    # ------------------------------------------------------------------

    def fetch_trader_detail(self, leader_mark: str) -> Optional[Dict]:
        """
        Fetch detailed profile for a specific trader.

        Endpoint: GET /common/leader/detail
        Params: leaderMark

        Returns dict with roi, pnl, winRate, followerCount, drawdown, etc.
        """
        url = f"{BYBIT_BEEHIVE_BASE}/common/leader/detail"
        data = self._get(url, {"leaderMark": leader_mark})
        if not data:
            return None

        detail = data.get("result", {})
        self._trader_details[leader_mark] = detail
        return detail

    # ------------------------------------------------------------------
    # 3. Get trader's current open positions
    # ------------------------------------------------------------------

    def fetch_trader_positions(self, leader_mark: str) -> List[Dict]:
        """
        Fetch current open positions for a specific trader.

        Endpoint: GET /common/position/list
        Params: leaderMark

        Returns list of position dicts with fields:
          symbol, side (Buy/Sell), entryPrice, sizeX, leverageE2,
          markPrice, unrealisedPnl, etc.

        Note: sizeX is multiplied by 10^8, leverageE2 is multiplied by 100.
        """
        url = f"{BYBIT_BEEHIVE_BASE}/common/position/list"
        data = self._get(url, {"leaderMark": leader_mark})
        if not data:
            return []

        result = data.get("result", {})
        positions_raw = result.get("data", [])

        # Normalize position data
        positions = []
        for p in positions_raw:
            try:
                entry_price = _safe_float(p.get("entryPrice", 0))
                # sizeX is position size * 10^8
                size = _safe_float(p.get("sizeX", 0)) / 1e8
                # leverageE2 is leverage * 100
                leverage = _safe_float(p.get("leverageE2", 0)) / 100.0
                mark_price = _safe_float(p.get("markPrice", 0))
                unrealised_pnl = _safe_float(p.get("unrealisedPnl", 0))

                positions.append({
                    "symbol": _normalize_symbol(p.get("symbol", "")),
                    "side": p.get("side", ""),  # "Buy" or "Sell"
                    "entry_price": entry_price,
                    "size": size,
                    "leverage": leverage,
                    "mark_price": mark_price,
                    "unrealised_pnl": unrealised_pnl,
                    "created_at": p.get("createdAtE3", ""),
                    "updated_at": p.get("updatedAtE3", ""),
                    "leader_mark": leader_mark,
                })
            except (TypeError, ValueError, KeyError) as exc:
                logger.debug("Skipping position: %s", exc)
                continue

        self._trader_positions[leader_mark] = positions
        return positions

    # ------------------------------------------------------------------
    # 4. Get trader's trade history
    # ------------------------------------------------------------------

    def fetch_trade_history(
        self,
        leader_mark: str,
        page_size: int = 50,
        max_pages: int = 2,
    ) -> List[Dict]:
        """
        Fetch closed trade history for a trader.

        Endpoint: GET /common/order/list
        Params: leaderMark, pageNo, pageSize

        Returns list of closed trade dicts.
        """
        all_trades = []

        for page in range(1, max_pages + 1):
            url = f"{BYBIT_BEEHIVE_BASE}/common/order/list"
            params = {
                "leaderMark": leader_mark,
                "pageNo": page,
                "pageSize": page_size,
            }

            data = self._get(url, params)
            if not data:
                break

            result = data.get("result", {})
            trades = result.get("data", [])

            if not trades:
                break

            all_trades.extend(trades)

            if len(trades) < page_size:
                break

        self._trader_history[leader_mark] = all_trades
        return all_trades

    # ------------------------------------------------------------------
    # 5. Calculate trader statistics from history
    # ------------------------------------------------------------------

    def calculate_trader_stats(self, leader_mark: str) -> Dict[str, Any]:
        """
        Calculate win rate, ROI, profit factor, and other stats from
        a trader's closed trade history.
        """
        trades = self._trader_history.get(leader_mark, [])
        if not trades:
            # Try to extract stats from trader detail/leaderboard entry
            detail = self._trader_details.get(leader_mark, {})
            return {
                "win_rate": _safe_float(detail.get("winRate", 0)),
                "roi": _safe_float(detail.get("roi", 0)),
                "total_pnl": _safe_float(detail.get("totalPnl", 0)),
                "profit_factor": 0,
                "total_trades": 0,
                "avg_hold_hours": 0,
                "source": "profile",
            }

        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0
        hold_times = []

        for trade in trades:
            pnl = _safe_float(trade.get("closedPnl", trade.get("pnl", 0)))

            if pnl > 0:
                wins += 1
                gross_profit += pnl
            elif pnl < 0:
                losses += 1
                gross_loss += abs(pnl)

            # Calculate hold time if timestamps available
            open_time = _safe_float(trade.get("createdAtE3", 0))
            close_time = _safe_float(trade.get("closedAtE3", trade.get("updatedAtE3", 0)))
            if open_time > 0 and close_time > open_time:
                hold_hours = (close_time - open_time) / 3_600_000.0
                hold_times.append(hold_hours)

        total_trades = wins + losses
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else float("inf")
        )
        avg_hold = (
            sum(hold_times) / len(hold_times) if hold_times else 0.0
        )

        return {
            "win_rate": round(win_rate, 4),
            "roi": _safe_float(
                self._trader_details.get(leader_mark, {}).get("roi", 0)
            ),
            "total_pnl": round(gross_profit - gross_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_hold_hours": round(avg_hold, 1),
            "source": "history",
        }

    # ------------------------------------------------------------------
    # 6. Filter qualifying traders
    # ------------------------------------------------------------------

    def filter_qualifying_traders(self) -> List[Dict]:
        """
        Filter leaderboard traders by quality thresholds.
        Returns list of qualifying trader dicts with leaderMark.
        """
        qualified = []

        for trader in self._traders_raw:
            try:
                # Extract ROI -- Bybit returns it in different formats
                roi = _safe_float(trader.get("roi", 0))
                # Some entries have it as a decimal (0.25 = 25%), others as %
                if -1 < roi < 1 and roi != 0:
                    roi *= 100  # Convert to percentage

                win_rate = _safe_float(trader.get("winRate", 0))
                if win_rate > 1:
                    win_rate /= 100  # Normalize to 0-1

                follower_count = _safe_float(
                    trader.get("followerCount", trader.get("followCount", 0))
                )
                max_dd = _safe_float(trader.get("maxDrawdown", 100))
                if max_dd > 1:
                    max_dd_pct = max_dd  # Already a percentage
                else:
                    max_dd_pct = max_dd * 100

                leader_mark = trader.get("leaderMark", "")
                nickname = trader.get("nickName", trader.get("nickname", "Unknown"))

                # Apply filters
                if roi < self.min_roi:
                    continue
                if win_rate < self.min_win_rate:
                    continue
                if follower_count < MIN_FOLLOWERS:
                    continue
                if max_dd_pct > MAX_DRAWDOWN_PCT:
                    continue
                if not leader_mark:
                    continue

                qualified.append({
                    "leaderMark": leader_mark,
                    "nickName": nickname,
                    "roi": roi,
                    "winRate": win_rate,
                    "followerCount": follower_count,
                    "maxDrawdown": max_dd_pct,
                    "totalPnl": _safe_float(trader.get("totalPnl", 0)),
                })

            except (TypeError, ValueError, KeyError) as exc:
                logger.debug("Skipping trader in filter: %s", exc)
                continue

        # Sort by ROI descending
        qualified.sort(key=lambda x: x["roi"], reverse=True)
        logger.info(
            "Filtered %d -> %d qualifying traders "
            "(ROI>%.0f%%, WR>%.0f%%, followers>%d, DD<%.0f%%)",
            len(self._traders_raw), len(qualified),
            self.min_roi, self.min_win_rate * 100,
            MIN_FOLLOWERS, MAX_DRAWDOWN_PCT,
        )
        return qualified

    # ------------------------------------------------------------------
    # 7. Get current price from V5 API (always works, for validation)
    # ------------------------------------------------------------------

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price from Bybit V5 public market API.
        This endpoint always works (no auth, no CDN issues).
        """
        try:
            url = f"{BYBIT_V5_BASE}/market/tickers"
            resp = self.session.get(
                url,
                params={"category": "linear", "symbol": symbol},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    return _safe_float(tickers[0].get("lastPrice", 0))
        except Exception as exc:
            logger.debug("Price fetch failed for %s: %s", symbol, exc)
        return None

    # ------------------------------------------------------------------
    # 8. Generate picks from trader positions
    # ------------------------------------------------------------------

    def generate_picks(
        self,
        qualified_traders: List[Dict],
    ) -> List[Dict]:
        """
        For each qualifying trader, fetch their open positions and generate
        standardized trading picks.

        Output format per pick:
        {
            "symbol": "BTCUSDT",
            "direction": "BUY" or "SELL",
            "confidence": 0.60 - 0.95,
            "source": "bybit_copy_trader",
            "trader_id": "...",
            "trader_name": "...",
            "trader_roi": 125.5,
            "trader_win_rate": 0.65,
            "entry_price": 69500.0,
            "leverage": 10.0,
            "position_size": 0.5,
        }
        """
        all_picks = []

        for trader in qualified_traders[:20]:  # Cap at 20 to respect rate limits
            leader_mark = trader["leaderMark"]
            nickname = trader["nickName"]
            roi = trader["roi"]
            win_rate = trader["winRate"]

            logger.info(
                "  Fetching positions for %s (ROI=%.1f%%, WR=%.1f%%)",
                nickname, roi, win_rate * 100,
            )

            # Fetch current positions
            positions = self.fetch_trader_positions(leader_mark)

            if not positions:
                logger.info("    -> No open positions")
                continue

            logger.info("    -> %d open positions", len(positions))

            for pos in positions:
                symbol = pos["symbol"]
                side = pos["side"]

                # Map Bybit side to direction
                if side == "Buy":
                    direction = "BUY"
                elif side == "Sell":
                    direction = "SELL"
                else:
                    continue

                # Calculate confidence based on trader quality
                # Base: 0.60, boosted by ROI and win rate
                confidence = 0.60
                if roi > 100:
                    confidence += 0.10
                elif roi > 50:
                    confidence += 0.05
                if win_rate > 0.65:
                    confidence += 0.10
                elif win_rate > 0.55:
                    confidence += 0.05
                if trader["followerCount"] > 200:
                    confidence += 0.05
                confidence = min(confidence, 0.95)

                entry_price = pos["entry_price"]
                if entry_price <= 0:
                    # Try to get current price as fallback
                    entry_price = self.get_current_price(symbol) or 0

                pick = {
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": round(confidence, 2),
                    "source": "bybit_copy_trader",
                    "trader_id": leader_mark,
                    "trader_name": nickname,
                    "trader_roi": round(roi, 2),
                    "trader_win_rate": round(win_rate, 4),
                    "trader_followers": trader["followerCount"],
                    "entry_price": entry_price,
                    "leverage": pos["leverage"],
                    "position_size": pos["size"],
                    "unrealised_pnl": pos["unrealised_pnl"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                all_picks.append(pick)

        logger.info("Generated %d raw picks from Bybit traders", len(all_picks))
        return all_picks

    # ------------------------------------------------------------------
    # 9. Aggregate consensus picks
    # ------------------------------------------------------------------

    def aggregate_consensus(
        self,
        picks: List[Dict],
        min_agreement: int = 2,
    ) -> List[Dict]:
        """
        Find symbols where multiple top traders agree on direction.
        These get higher confidence scores.
        """
        from collections import defaultdict

        # Group by (symbol, direction)
        groups: Dict[tuple, List[Dict]] = defaultdict(list)
        for pick in picks:
            key = (pick["symbol"], pick["direction"])
            groups[key].append(pick)

        consensus = []
        for (symbol, direction), group in groups.items():
            if len(group) >= min_agreement:
                # Average the entry prices and boost confidence
                prices = [p["entry_price"] for p in group if p["entry_price"] > 0]
                avg_price = sum(prices) / len(prices) if prices else 0
                avg_roi = sum(p["trader_roi"] for p in group) / len(group)
                avg_wr = sum(p["trader_win_rate"] for p in group) / len(group)
                avg_lev = sum(p["leverage"] for p in group) / len(group)

                # Consensus confidence: base + agreement bonus
                conf = min(0.70 + 0.05 * len(group), 0.95)

                consensus.append({
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": conf,
                    "source": "bybit_copy_trader_consensus",
                    "agreeing_traders": len(group),
                    "traders": [
                        {
                            "id": p["trader_id"],
                            "name": p["trader_name"],
                            "roi": p["trader_roi"],
                        }
                        for p in group
                    ],
                    "avg_entry_price": round(avg_price, 6),
                    "avg_trader_roi": round(avg_roi, 2),
                    "avg_win_rate": round(avg_wr, 4),
                    "avg_leverage": round(avg_lev, 1),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        consensus.sort(key=lambda x: x["agreeing_traders"], reverse=True)
        logger.info(
            "Found %d consensus picks (>=%d traders agree)",
            len(consensus), min_agreement,
        )
        return consensus

    # ------------------------------------------------------------------
    # 10. Save results
    # ------------------------------------------------------------------

    def save_results(
        self,
        picks: List[Dict],
        consensus: List[Dict],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Save scraper results to JSON."""
        if output_path is None:
            output_path = DATA_DIR / "bybit_copy_trader_picks.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "bybit_copy_trading",
            "api_available": self._api_available,
            "total_traders_scanned": len(self._traders_raw),
            "traders_with_positions": len(self._trader_positions),
            "total_picks": len(picks),
            "consensus_picks": consensus,
            "all_picks": picks,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)

        logger.info("Saved Bybit picks to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self) -> List[Dict]:
        """
        Execute the full Bybit copy trading scraper pipeline.

        Returns list of picks in standardized format:
        [
            {
                "symbol": "BTCUSDT",
                "direction": "BUY",
                "confidence": 0.75,
                "source": "bybit_copy_trader",
                "trader_id": "abc123",
                "trader_name": "TopTrader",
                "trader_roi": 125.5,
                "trader_win_rate": 0.65,
                "entry_price": 69500.0,
                ...
            },
            ...
        ]
        """
        logger.info("=== Bybit Copy Trader Scraper - Starting ===")

        # Step 1: Initialize session (get cookies)
        self._init_session()

        # Step 2: Fetch leaderboard
        self.fetch_leaderboard()

        if not self._traders_raw:
            logger.warning(
                "No traders fetched from Bybit leaderboard. "
                "API may be geo-blocked or rate-limited."
            )
            return []

        # Step 3: Filter by quality thresholds
        qualified = self.filter_qualifying_traders()

        if not qualified:
            logger.warning(
                "No traders passed quality filters. "
                "Relaxing ROI threshold to 10%%..."
            )
            self.min_roi = 10.0
            self.min_win_rate = 0.40
            qualified = self.filter_qualifying_traders()

        if not qualified:
            logger.warning("Still no qualifying traders after relaxed filters.")
            return []

        # Step 4: Generate picks from open positions
        picks = self.generate_picks(qualified)

        # Step 5: Find consensus (multiple traders same position)
        consensus = self.aggregate_consensus(picks)

        # Step 6: Save results
        self.save_results(picks, consensus)

        # Step 7: Return all picks (individual + consensus)
        all_signals = []

        # Add consensus picks first (higher priority)
        for c in consensus:
            all_signals.append({
                "symbol": c["symbol"],
                "direction": c["direction"],
                "confidence": c["confidence"],
                "source": "bybit_copy_trader_consensus",
                "trader_id": "consensus",
                "trader_name": f"{c['agreeing_traders']} traders agree",
                "trader_roi": c["avg_trader_roi"],
                "trader_win_rate": c["avg_win_rate"],
                "entry_price": c["avg_entry_price"],
                "leverage": c["avg_leverage"],
            })

        # Add individual picks (lower priority, skip duplicates)
        seen = {(s["symbol"], s["direction"]) for s in all_signals}
        for pick in picks:
            key = (pick["symbol"], pick["direction"])
            if key not in seen:
                all_signals.append(pick)
                seen.add(key)

        logger.info(
            "=== Bybit Scraper Done: %d signals (%d consensus, %d individual) ===",
            len(all_signals), len(consensus), len(all_signals) - len(consensus),
        )
        return all_signals


# ---------------------------------------------------------------------------
# Public API for scanner integration
# ---------------------------------------------------------------------------

def scan_bybit_traders() -> List[Dict[str, Any]]:
    """
    Run the Bybit copy trader scraper and return picks in
    scanner-compatible format.

    This is the entry point for integration with production_scanner.py.
    """
    try:
        scraper = BybitScraper(
            duration=DURATION_30D,
            max_traders=50,
            min_roi=MIN_ROI_PCT,
            min_win_rate=MIN_WIN_RATE,
        )
        picks = scraper.run()

        # Convert to scanner signal format
        signals = []
        for pick in picks:
            direction = pick.get("direction", "BUY")
            signal_type = direction  # Already BUY/SELL

            sig = {
                "symbol": pick["symbol"],
                "signal_type": signal_type,
                "strategy": "bybit_copy_trader",
                "confidence": pick.get("confidence", 0.60),
                "source": pick.get("source", "bybit_copy_trader"),
                "rationale": (
                    f"Bybit top trader {pick.get('trader_name', '?')} "
                    f"(ROI={pick.get('trader_roi', 0):.1f}%, "
                    f"WR={pick.get('trader_win_rate', 0) * 100:.0f}%) "
                    f"has {direction.lower()} position"
                ),
                "entry_price": pick.get("entry_price", 0),
                "trader_id": pick.get("trader_id", ""),
                "trader_roi": pick.get("trader_roi", 0),
                "forward_test_only": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            signals.append(sig)

        return signals

    except Exception as exc:
        logger.error("Bybit scraper failed: %s", exc, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the Bybit scraper as a standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = BybitScraper()
    picks = scraper.run()

    if picks:
        print(f"\n=== {len(picks)} BYBIT COPY TRADER PICKS ===")
        for i, p in enumerate(picks, 1):
            print(
                f"  {i}. {p['direction']} {p['symbol']} "
                f"@ {p.get('entry_price', '?')} "
                f"(conf={p['confidence']}, "
                f"trader={p.get('trader_name', '?')}, "
                f"ROI={p.get('trader_roi', 0):.1f}%)"
            )
    else:
        print("\nNo picks generated. API may be blocked from this location.")
        print("The Bybit beehive API requires browser-like access.")
        print("Consider running from a residential IP or using a proxy.")


if __name__ == "__main__":
    main()

"""
copy_trader_analyzer.py - Alpha Engine: Copy-Trader Consensus Scanner
=====================================================================
PRIMARY: OKX Copy-Trading public REST API (NO auth required).
FALLBACK: Bybit leaderboard API.

Fetches top copy-traders, filters by performance, analyzes their trades,
and generates consensus picks when 2+ top traders hold the same position.

OKX Endpoints (confirmed public, no auth):
  GET /api/v5/copytrading/public-lead-traders
  GET /api/v5/copytrading/public-current-subpositions?uniqueCode={CODE}
  GET /api/v5/copytrading/public-subpositions-history?uniqueCode={CODE}&limit=100

Output: alpha_engine/data/copy_trader_patterns.json
"""

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "copy_trader_patterns.json"

OKX_BASE = "https://www.okx.com"
BYBIT_BASE = "https://api2.bybit.com"
BYBIT_BEEHIVE_BASE = "https://api2.bybit.com/fapi/beehive/public/v1"

# Filter thresholds for qualifying traders
MIN_PNL_RATIO = 1.0       # 100%+ ROI
MIN_WIN_RATIO = 0.50       # 50%+ win rate
MIN_LEAD_DAYS = 30         # At least 30 days leading

MIN_AUM_USD = 100000.0
MIN_RECENCY_WR = 0.60
MIN_RECENT_TRADES = 5
CONSENSUS_MIN_TRADERS = 3

# Known top traders from research (will be fetched even if they don't appear in leaderboard)
KNOWN_TRADER_CODES = [
    "Expert-Ethash-Camel",   # +1,053% in 90 days
    "CrowleyZhou",           # +215%, $439K AUM
]

# Consensus threshold
CONSENSUS_MIN_TRADERS = 2
CONSENSUS_CONFIDENCE = 0.85

REQUEST_TIMEOUT = 15  # seconds
RATE_LIMIT_DELAY = 0.5  # seconds between requests

# Common headers
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# SSL + HTTP helper (stdlib only)
# ---------------------------------------------------------------------------

def _create_ssl_context() -> ssl.SSLContext:
    """Create a permissive SSL context for exchange APIs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, retries: int = 2, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """GET JSON from url with retries. Returns parsed dict or None on failure."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            ctx = _create_ssl_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s from %s", exc.code, url)
        except urllib.error.URLError as exc:
            logger.warning("URL error for %s: %s", url, exc.reason)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Parse/network error for %s: %s", url, exc)
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


# ---------------------------------------------------------------------------
# OKX API - PRIMARY data source (fully public, no auth)
# ---------------------------------------------------------------------------

def okx_fetch_lead_traders(limit: int = 20) -> List[Dict]:
    """Fetch top lead traders from OKX copy-trading leaderboard."""
    url = f"{OKX_BASE}/api/v5/copytrading/public-lead-traders?limit={limit}"
    data = _http_get(url)
    if not data or data.get("code") != "0":
        code_val = data.get("code") if data else "None"
        logger.warning("OKX lead-traders returned code: %s", code_val)
        return []
    return data.get("data", [])


def okx_fetch_current_positions(unique_code: str) -> List[Dict]:
    """Fetch current open positions for a specific OKX trader."""
    url = (
        f"{OKX_BASE}/api/v5/copytrading/public-current-subpositions"
        f"?uniqueCode={unique_code}"
    )
    data = _http_get(url)
    if not data or data.get("code") != "0":
        return []
    return data.get("data", [])


def okx_fetch_trade_history(unique_code: str, limit: int = 100) -> List[Dict]:
    """Fetch historical closed trades for a specific OKX trader."""
    url = (
        f"{OKX_BASE}/api/v5/copytrading/public-subpositions-history"
        f"?uniqueCode={unique_code}&limit={limit}"
    )
    data = _http_get(url)
    if not data or data.get("code") != "0":
        return []
    return data.get("data", [])


# ---------------------------------------------------------------------------
# Bybit API - FALLBACK
# ---------------------------------------------------------------------------

def bybit_fetch_lead_traders(limit: int = 20) -> List[Dict]:
    """Fetch leaderboard from Bybit beehive API as fallback. Returns OKX-normalised dicts."""
    url = (
        f"{BYBIT_BEEHIVE_BASE}/common/dynamic-leader-list"
        f"?pageNo=1&pageSize={limit}"
        f"&sortField=LEADER_SORT_FIELD_SORT_ROI&sortType=SORT_TYPE_DESC"
        f"&dataDuration=DATA_DURATION_THIRTY_DAY"
    )
    data = _http_get(url)
    if not data:
        logger.warning("Bybit leaderboard returned no data")
        return []

    result = data.get("result") or data.get("data") or {}
    raw_list = []
    if isinstance(result, list):
        raw_list = result
    elif isinstance(result, dict):
        # Beehive API uses leaderDetails, older API uses list/data
        raw_list = result.get("leaderDetails") or result.get("list") or result.get("data") or []

    traders = []
    for item in raw_list:
        try:
            roi_raw = _to_float(item.get("roi", item.get("totalRoi", 0)))
            wr_raw = _to_float(item.get("winRate", item.get("winRatio", 0)))
            traders.append({
                "uniqueCode": str(item.get("leaderMark", item.get("leaderId", item.get("traderUid", "")))),
                "nickName": str(item.get("nickName", item.get("nickname", "Unknown"))),
                "pnl": str(item.get("totalPnl", item.get("pnl", "0"))),
                "pnlRatio": str(roi_raw if roi_raw >= 1.0 else roi_raw * 100),
                "winRatio": str(wr_raw if wr_raw <= 1.0 else wr_raw / 100),
                "aum": str(item.get("aum", "0")),
                "copyTraderNum": str(item.get("followerCount", item.get("followers", "0"))),
                "leadDays": str(item.get("leadDays", "30")),
                "_source": "bybit",
            })
        except (TypeError, ValueError) as exc:
            logger.debug("Skipping Bybit trader: %s", exc)

    return traders


# ---------------------------------------------------------------------------
# Trader filtering
# ---------------------------------------------------------------------------

def filter_qualifying_traders(traders: List[Dict]) -> List[Dict]:
    """Filter traders by ROI, win rate, and lead days thresholds."""
    qualified = []
    for t in traders:
        try:
            pnl_ratio = _to_float(t.get("pnlRatio", 0))
            win_ratio = _to_float(t.get("winRatio", 0))
            lead_days = int(_to_float(t.get("leadDays", 0)))
            aum = _to_float(t.get("aum", 0))
        except (ValueError, TypeError):
            continue

        if pnl_ratio >= MIN_PNL_RATIO and win_ratio >= MIN_WIN_RATIO and lead_days >= MIN_LEAD_DAYS and aum >= MIN_AUM_USD:
            qualified.append(t)

    # Sort by PnL ratio descending
    qualified.sort(key=lambda x: _to_float(x.get("pnlRatio", 0)), reverse=True)
    return qualified


# ---------------------------------------------------------------------------
# Trade pattern analysis
# ---------------------------------------------------------------------------

def analyze_trade_history(trades: List[Dict]) -> Dict[str, Any]:
    """Compute trading patterns from OKX historical trades."""
    if not trades:
        return {}

    hold_hours_list: List[float] = []
    symbol_counts: Dict[str, int] = defaultdict(int)
    long_count = 0
    short_count = 0
    leverage_list: List[float] = []
    wins_by_symbol: Dict[str, List[bool]] = defaultdict(list)
    entry_hours: List[int] = []
    tp_pcts: List[float] = []
    sl_pcts: List[float] = []

    for trade in trades:
        inst_id = trade.get("instId", "")
        symbol_counts[inst_id] += 1

        pos_side = trade.get("posSide", "").lower()
        if pos_side == "long":
            long_count += 1
        elif pos_side == "short":
            short_count += 1

        lev = _to_float(trade.get("lever", 0))
        if lev > 0:
            leverage_list.append(lev)

        open_ts = _to_float(trade.get("openTime", 0))
        close_ts = _to_float(trade.get("closeTime", 0))
        if open_ts > 0 and close_ts > open_ts:
            hold_h = (close_ts - open_ts) / 3_600_000.0
            hold_hours_list.append(hold_h)

        if open_ts > 0:
            try:
                dt = datetime.fromtimestamp(open_ts / 1000.0, tz=timezone.utc)
                entry_hours.append(dt.hour)
            except (OSError, ValueError):
                pass

        pnl = _to_float(trade.get("pnl", 0))
        pnl_ratio = _to_float(trade.get("pnlRatio", 0))
        wins_by_symbol[inst_id].append(pnl > 0)
        if pnl > 0:
            tp_pcts.append(abs(pnl_ratio) * 100)
        elif pnl < 0:
            sl_pcts.append(abs(pnl_ratio) * 100)

    # Win rate by symbol
    wr_by_symbol = {}
    for sym, results in wins_by_symbol.items():
        if results:
            wr_by_symbol[sym] = round(sum(results) / len(results), 4)

    # Most traded symbols (top 5)
    top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Entry hour distribution (4-hour buckets)
    hour_buckets: Dict[str, int] = defaultdict(int)
    for h in entry_hours:
        start = (h // 4) * 4
        end = (start + 4) % 24
        bucket = f"{start:02d}-{end:02d} UTC"
        hour_buckets[bucket] += 1

    total_dir = long_count + short_count

    return {
        "total_trades": len(trades),
        "avg_hold_hours": round(sum(hold_hours_list) / len(hold_hours_list), 1) if hold_hours_list else 0,
        "median_hold_hours": round(sorted(hold_hours_list)[len(hold_hours_list) // 2], 1) if hold_hours_list else 0,
        "most_traded_symbols": [{"symbol": s, "count": c} for s, c in top_symbols],
        "long_ratio": round(long_count / total_dir, 4) if total_dir > 0 else 0,
        "short_ratio": round(short_count / total_dir, 4) if total_dir > 0 else 0,
        "avg_leverage": round(sum(leverage_list) / len(leverage_list), 1) if leverage_list else 0,
        "win_rate_by_symbol": wr_by_symbol,
        "entry_hour_distribution": dict(hour_buckets),
        "avg_tp_pct": round(sum(tp_pcts) / len(tp_pcts), 2) if tp_pcts else 0,
        "avg_sl_pct": round(sum(sl_pcts) / len(sl_pcts), 2) if sl_pcts else 0,
    }


# ---------------------------------------------------------------------------
# Consensus pick generation
# ---------------------------------------------------------------------------

def generate_consensus_picks(
    open_positions_by_trader: Dict[str, List[Dict]],
    trader_info: Dict[str, Dict],
    min_agreement: int = CONSENSUS_MIN_TRADERS,
) -> List[Dict]:
    """
    Generate consensus picks when min_agreement+ top traders hold the same
    symbol in the same direction (from their CURRENT OPEN positions).
    """
    position_groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

    for trader_code, positions in open_positions_by_trader.items():
        for pos in positions:
            inst_id = pos.get("instId", "")
            direction = pos.get("posSide", "").upper()
            if not inst_id or not direction:
                continue

            # Normalize symbol: BTC-USDT-SWAP -> BTCUSDT
            normalized = inst_id.replace("-SWAP", "").replace("-", "")

            position_groups[(normalized, direction)].append({
                "trader": trader_code,
                "nickName": trader_info.get(trader_code, {}).get("nickName", trader_code),
                "instId": inst_id,
                "lever": pos.get("lever", "1"),
                "openAvgPx": pos.get("openAvgPx", "0"),
                "upl": pos.get("upl", "0"),
                "uplRatio": pos.get("uplRatio", "0"),
                "openTime": pos.get("openTime", ""),
            })

    consensus = []
    for (symbol, direction), group in position_groups.items():
        if len(group) >= min_agreement:
            prices = [_to_float(g["openAvgPx"]) for g in group if _to_float(g["openAvgPx"]) > 0]
            leverages = [_to_float(g["lever"]) for g in group if _to_float(g["lever"]) > 0]

            avg_price = sum(prices) / len(prices) if prices else 0
            avg_lever = sum(leverages) / len(leverages) if leverages else 1

            signal_type = "BUY" if direction == "LONG" else "SELL"

            # Conservative TP/SL
            tp_mult = 1.025 if signal_type == "BUY" else 0.975
            sl_mult = 0.985 if signal_type == "BUY" else 1.015

            consensus.append({
                "strategy": "copy_trader_consensus",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": round(avg_price, 6),
                "take_profit": round(avg_price * tp_mult, 6),
                "stop_loss": round(avg_price * sl_mult, 6),
                "confidence": round(min(0.60 + 0.10 * len(group), 0.95), 2),
                "avg_leverage": round(avg_lever, 1),
                "agreeing_traders": len(group),
                "traders": [g["nickName"] for g in group],
                "direction": direction,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "okx_copy_trading",
            })

    consensus.sort(key=lambda x: x["agreeing_traders"], reverse=True)
    return consensus


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class CopyTraderAnalyzer:
    """
    Fetches top traders from OKX (primary) / Bybit (fallback),
    analyses their recent trades + current positions,
    and distills patterns + consensus picks.
    """

    def __init__(self, output_path: Optional[Path] = None):
        self.output_path = output_path or OUTPUT_FILE
        self.traders: List[Dict[str, Any]] = []
        self.trader_patterns: List[Dict[str, Any]] = []
        self.open_positions_by_trader: Dict[str, List[Dict]] = {}
        self.trader_info: Dict[str, Dict] = {}
        self.trader_source: str = "unknown"

    # ------------------------------------------------------------------
    # Step 1: Fetch leaderboard (OKX primary, Bybit fallback)
    # ------------------------------------------------------------------

    def fetch_leaderboard(self) -> List[Dict[str, Any]]:
        """Fetch top traders. OKX first, Bybit fallback."""
        logger.info("Fetching OKX copy-trading leaderboard...")
        traders = okx_fetch_lead_traders(limit=20)
        self.trader_source = "okx"

        if not traders:
            logger.info("OKX failed, falling back to Bybit...")
            traders = bybit_fetch_lead_traders(limit=20)
            self.trader_source = "bybit"

        if not traders:
            logger.warning("Both OKX and Bybit failed. No data.")
            self.traders = []
            return []

        logger.info("Fetched %d traders from %s", len(traders), self.trader_source)
        self.traders = traders
        return traders

    # ------------------------------------------------------------------
    # Step 2: Filter traders by quality thresholds
    # ------------------------------------------------------------------

    def filter_traders(self) -> List[Dict[str, Any]]:
        """Keep only traders meeting ROI / WR / lead days thresholds."""
        qualified = filter_qualifying_traders(self.traders)
        logger.info(
            "Filtered %d -> %d qualifying traders (ROI>%.0f%%, WR>%.0f%%, days>%d)",
            len(self.traders), len(qualified),
            MIN_PNL_RATIO * 100, MIN_WIN_RATIO * 100, MIN_LEAD_DAYS,
        )

        # Also include known top traders
        known_codes_in_list = {t.get("uniqueCode") for t in qualified}
        for code in KNOWN_TRADER_CODES:
            if code not in known_codes_in_list:
                qualified.append({
                    "uniqueCode": code,
                    "nickName": code,
                    "pnlRatio": "0",
                    "winRatio": "0",
                    "leadDays": "0",
                    "_known": True,
                })

        self.traders = qualified
        return qualified

    # ------------------------------------------------------------------
    # Step 3: Fetch trades + current positions for each trader
    # ------------------------------------------------------------------

    def fetch_trader_data(self) -> None:
        """For each qualifying trader, fetch history and current positions."""
        for trader in self.traders[:10]:  # Cap at 10 to avoid rate limits
            code = trader.get("uniqueCode", "")
            nick = trader.get("nickName", code)
            if not code:
                continue

            self.trader_info[code] = trader
            logger.info("  Analyzing: %s (code=%s)", nick, code)

            # Fetch trade history
            history = okx_fetch_trade_history(code, limit=100)
            patterns = analyze_trade_history(history)

            # Fetch current open positions
            positions = okx_fetch_current_positions(code)
            if positions:
                self.open_positions_by_trader[code] = positions
                logger.info("    -> %d open positions, %d historical trades", len(positions), len(history))
            else:
                logger.info("    -> 0 open positions, %d historical trades", len(history))

            self.trader_patterns.append({
                "uniqueCode": code,
                "nickName": nick,
                "pnlRatio": trader.get("pnlRatio", "0"),
                "winRatio": trader.get("winRatio", "0"),
                "aum": trader.get("aum", "0"),
                "copyTraderNum": trader.get("copyTraderNum", "0"),
                "leadDays": trader.get("leadDays", "0"),
                "patterns": patterns,
                "current_positions": [
                    {
                        "instId": p.get("instId", ""),
                        "posSide": p.get("posSide", ""),
                        "lever": p.get("lever", ""),
                        "openAvgPx": p.get("openAvgPx", ""),
                        "upl": p.get("upl", ""),
                        "uplRatio": p.get("uplRatio", ""),
                    }
                    for p in positions
                ],
            })

            time.sleep(RATE_LIMIT_DELAY)

    # ------------------------------------------------------------------
    # Step 4: Save results
    # ------------------------------------------------------------------

    def save_results(self, consensus: List[Dict]) -> Path:
        """Write analysis results to JSON."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.trader_source,
            "total_traders_fetched": len(self.traders),
            "qualifying_traders": len(self.traders),
            "traders_analyzed": len(self.trader_patterns),
            "trader_patterns": self.trader_patterns,
            "consensus_picks": consensus,
            "all_open_positions": {
                code: [
                    {
                        "instId": p.get("instId", ""),
                        "posSide": p.get("posSide", ""),
                        "lever": p.get("lever", ""),
                        "openAvgPx": p.get("openAvgPx", ""),
                        "upl": p.get("upl", ""),
                    }
                    for p in positions
                ]
                for code, positions in self.open_positions_by_trader.items()
            },
        }

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)

        logger.info("Saved copy trader analysis to %s", self.output_path)
        return self.output_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute the full copy-trader analysis pipeline."""
        logger.info("=== Copy Trader Analyzer (OKX primary) - Starting ===")

        # 1. Fetch leaderboard
        self.fetch_leaderboard()

        if not self.traders:
            return {"status": "error", "message": "No traders fetched"}

        # 2. Filter
        self.filter_traders()

        # 3. Fetch trades + positions for each trader
        self.fetch_trader_data()

        # 4. Generate consensus picks from current open positions
        consensus = generate_consensus_picks(
            self.open_positions_by_trader, self.trader_info
        )
        logger.info("Consensus picks: %d", len(consensus))

        # 5. Save
        output_path = self.save_results(consensus)

        summary = {
            "status": "ok",
            "source": self.trader_source,
            "traders_analyzed": len(self.trader_patterns),
            "open_positions_total": sum(
                len(v) for v in self.open_positions_by_trader.values()
            ),
            "consensus_picks": len(consensus),
            "output_file": str(output_path),
        }
        logger.info("=== Copy Trader Analyzer - Done: %s ===", summary)
        return summary


# ---------------------------------------------------------------------------
# Public API for scanner integration
# ---------------------------------------------------------------------------

def analyze_top_traders() -> List[Dict[str, Any]]:
    """
    Run the copy trader analyzer and return consensus picks as
    scanner-compatible signals.

    Returns a list of dicts with keys: symbol, signal_type, strategy,
    confidence, entry_price, take_profit, stop_loss, etc.
    """
    analyzer = CopyTraderAnalyzer()
    analyzer.run()

    # Load consensus picks from saved output
    consensus = []
    try:
        if analyzer.output_path.exists():
            with open(analyzer.output_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            consensus = saved.get("consensus_picks", [])
    except Exception:
        pass

    # Convert to scanner signal format
    signals = []
    for pick in consensus:
        direction = pick.get("direction", "LONG").upper()
        signal_type = "BUY" if direction == "LONG" else "SELL"
        symbol = pick.get("symbol", "")

        sig = {
            "symbol": symbol,
            "signal_type": signal_type,
            "strategy": "copy_trader_consensus",
            "confidence": pick.get("confidence", CONSENSUS_CONFIDENCE),
            "source": "OKX top copy-traders (100%+ ROI, 50%+ WR)",
            "rationale": (
                f"{pick.get('agreeing_traders', 0)} top traders agree on "
                f"{direction.lower()} {symbol}"
            ),
            "entry_price": pick.get("entry_price", 0),
            "take_profit": pick.get("take_profit", 0),
            "stop_loss": pick.get("stop_loss", 0),
            "avg_leverage": pick.get("avg_leverage", 1),
            "traders": pick.get("traders", []),
            "forward_test_only": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        signals.append(sig)

    return signals


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the copy trader analyzer as a standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    analyzer = CopyTraderAnalyzer()
    result = analyzer.run()
    print(json.dumps(result, indent=2))

    # Print consensus picks
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        picks = saved.get("consensus_picks", [])
        if picks:
            print(f"\n=== {len(picks)} CONSENSUS PICKS ===")
            for i, p in enumerate(picks, 1):
                print(
                    f"  {i}. {p['signal_type']} {p['symbol']} @ {p['entry_price']} "
                    f"(TP: {p['take_profit']}, SL: {p['stop_loss']}) "
                    f"-- {p['agreeing_traders']} traders, conf {p['confidence']}"
                )
        else:
            print("\nNo consensus picks at this time.")

        # Print all open positions
        all_pos = saved.get("all_open_positions", {})
        if all_pos:
            total = sum(len(v) for v in all_pos.values())
            print(f"\n=== {total} OPEN POSITIONS across {len(all_pos)} traders ===")
            for code, positions in all_pos.items():
                for pos in positions:
                    print(
                        f"  {code}: {pos['posSide']} {pos['instId']} "
                        f"@ {pos.get('openAvgPx', '?')} "
                        f"lever={pos.get('lever', '?')}x"
                    )
    except Exception as exc:
        print(f"Could not read output: {exc}")


if __name__ == "__main__":
    main()

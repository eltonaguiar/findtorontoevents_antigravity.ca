"""
ALPHA ENGINE -- A/B Test Portfolios
====================================
Runs 8 portfolio variants side-by-side, each starting with $500,
to prove which pick strategy actually works best.

Portfolios:
  A: Golden Filter     -- top 5 traders, score>=70, MTF gate, 3%/2% TP/SL
  B: Golden + RSI Gate -- A + RSI overbought/oversold block
  C: Golden + Wide     -- A but 5%/3% TP/SL
  D: Golden + Tight    -- A but 2%/1.5% TP/SL
  E: SHORT Only        -- A but only SHORT picks
  F: All Copy Traders  -- broader baseline, score>=50, no MTF
  G: Smart Picks       -- current system control
  H: Rocket Scanner    -- backtested rockets

State persists in alpha_engine/data/ab_test_state.json.
History appended to alpha_engine/data/ab_test_results.json (cap 200).

Stdlib only.  Binance 5-mirror failover.
"""

from __future__ import annotations

import json
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_DIR, "data")
_STATE_FILE = os.path.join(_DATA_DIR, "ab_test_state.json")
_RESULTS_FILE = os.path.join(_DATA_DIR, "ab_test_results.json")
_COPY_PICKS = os.path.join(_DIR, "..", "copy_trader_intel", "data", "active_picks.json")
_SMART_PICKS = os.path.join(_DATA_DIR, "smart_picks.json")
_ROCKET_PICKS = os.path.join(_DATA_DIR, "rocket_picks.json")
_TOP_TRADERS = os.path.join(_DATA_DIR, "top_trader_analysis.json")

# ---------------------------------------------------------------------------
# Top 5 golden traders
# ---------------------------------------------------------------------------
GOLDEN_TRADERS = [
    "whale_20.7M",
    "NMTD_25M",
    "whale_123M_87roi",
    "whale_58M_287roi",
    "lb_NMTD",
]

# Match against strategy field patterns like copy_hl_whale_20.7M, copy_hl_NMTD_25M, etc.
def _is_golden_trader(strategy: str) -> bool:
    """Check if a strategy string belongs to one of the top-5 golden traders."""
    s = strategy.lower().replace("copy_hl_", "").replace("copy_", "")
    for t in GOLDEN_TRADERS:
        if t.lower() in s.lower() or s.lower() in t.lower():
            return True
    return False


def _is_copy_trader(strategy: str) -> bool:
    """Any copy trader strategy."""
    sl = strategy.lower()
    return "copy_hl_" in sl or "copy_" in sl


# ---------------------------------------------------------------------------
# Binance 5-mirror failover
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_ssl_ctx: Optional[ssl.SSLContext] = None


def _get_ssl_ctx() -> ssl.SSLContext:
    global _ssl_ctx
    if _ssl_ctx is None:
        try:
            _ssl_ctx = ssl.create_default_context()
            _ssl_ctx.check_hostname = True
            _ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        except Exception:
            _ssl_ctx = ssl._create_unverified_context()
    return _ssl_ctx


def _http_get(url: str, timeout: int = 10) -> Optional[bytes]:
    """HTTP GET with SSL context."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AB-Test/1.0"})
        with urllib.request.urlopen(req, context=_get_ssl_ctx(), timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def _binance_api(path: str, params: str = "") -> Optional[Any]:
    """Try all 5 Binance mirrors, return parsed JSON or None."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{path}"
        if params:
            url += f"?{params}"
        data = _http_get(url)
        if data:
            try:
                return json.loads(data)
            except Exception:
                continue
    return None


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------
_price_cache: Dict[str, Tuple[float, float]] = {}  # symbol -> (timestamp, price)
_PRICE_CACHE_TTL = 30  # seconds


def fetch_price(symbol: str) -> Optional[float]:
    """Fetch current price for a symbol from Binance with 5-mirror failover."""
    now = time.time()
    cached = _price_cache.get(symbol)
    if cached and (now - cached[0]) < _PRICE_CACHE_TTL:
        return cached[1]

    data = _binance_api("/api/v3/ticker/price", f"symbol={symbol}")
    if data and "price" in data:
        price = float(data["price"])
        _price_cache[symbol] = (now, price)
        return price
    return None


def fetch_prices_batch(symbols: List[str]) -> Dict[str, float]:
    """Fetch prices for multiple symbols."""
    results: Dict[str, float] = {}
    # Try batch endpoint first
    data = _binance_api("/api/v3/ticker/price")
    if data and isinstance(data, list):
        lookup = {item["symbol"]: float(item["price"]) for item in data if "symbol" in item}
        for sym in symbols:
            if sym in lookup:
                results[sym] = lookup[sym]
                _price_cache[sym] = (time.time(), lookup[sym])
    # Fallback: fetch individually for missing
    for sym in symbols:
        if sym not in results:
            p = fetch_price(sym)
            if p is not None:
                results[sym] = p
    return results


# ---------------------------------------------------------------------------
# RSI calculation (14-period from 1H klines)
# ---------------------------------------------------------------------------
def _fetch_klines_1h(symbol: str, limit: int = 50) -> Optional[List[float]]:
    """Fetch 1H close prices from Binance."""
    data = _binance_api("/api/v3/klines", f"symbol={symbol}&interval=1h&limit={limit}")
    if data and isinstance(data, list) and len(data) > 1:
        return [float(k[4]) for k in data]  # close price is index 4
    return None


def compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI from a list of close prices."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def get_rsi(symbol: str) -> Optional[float]:
    """Get current RSI(14) for a symbol."""
    closes = _fetch_klines_1h(symbol, limit=50)
    if closes is None:
        return None
    return compute_rsi(closes, 14)


# ---------------------------------------------------------------------------
# MTF gate (import with fallback)
# ---------------------------------------------------------------------------
def check_mtf(symbol: str, direction: str) -> dict:
    """Check multi-timeframe alignment. Returns dict with 'aligned' and 'score_adjustment'."""
    try:
        sys.path.insert(0, _DIR)
        from mtf_gate import check_mtf_alignment
        result = check_mtf_alignment(symbol, direction)
        return result
    except Exception:
        # Fallback: assume aligned (don't block if MTF module unavailable)
        return {"aligned": True, "score_adjustment": 0, "details": "mtf_gate unavailable"}


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------
def _load_json(path: str) -> Any:
    """Load JSON file, return None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: str, data: Any) -> None:
    """Save JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Portfolio configuration
# ---------------------------------------------------------------------------
STARTING_CAPITAL = 500.0

PORTFOLIO_CONFIGS = {
    "A": {
        "name": "Golden Filter",
        "description": "Top 5 traders, score>=70, MTF gate, 3%/2% TP/SL",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 70,
        "require_mtf": True,
        "require_golden": True,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "copy_traders",
    },
    "B": {
        "name": "Golden + RSI Gate",
        "description": "Golden Filter + RSI overbought/oversold block",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 70,
        "require_mtf": True,
        "require_golden": True,
        "direction_filter": None,
        "require_rsi_gate": True,
        "source": "copy_traders",
    },
    "C": {
        "name": "Golden + Wide Stops",
        "description": "Golden Filter with 5%/3% TP/SL (wider to avoid shakeouts)",
        "tp_pct": 5.0,
        "sl_pct": 3.0,
        "min_score": 70,
        "require_mtf": True,
        "require_golden": True,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "copy_traders",
    },
    "D": {
        "name": "Golden + Tight Stops",
        "description": "Golden Filter with 2%/1.5% TP/SL (tighter for faster resolution)",
        "tp_pct": 2.0,
        "sl_pct": 1.5,
        "min_score": 70,
        "require_mtf": True,
        "require_golden": True,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "copy_traders",
    },
    "E": {
        "name": "SHORT Only",
        "description": "Golden Filter but only SHORT direction picks",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 70,
        "require_mtf": True,
        "require_golden": True,
        "direction_filter": "SHORT",
        "require_rsi_gate": False,
        "source": "copy_traders",
    },
    "F": {
        "name": "All Copy Traders",
        "description": "ALL copy trader picks, score>=50, no MTF gate",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 50,
        "require_mtf": False,
        "require_golden": False,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "copy_traders",
    },
    "G": {
        "name": "Current Smart Picks",
        "description": "Control: whatever the current system selects",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 0,
        "require_mtf": False,
        "require_golden": False,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "smart_picks",
    },
    "H": {
        "name": "Rocket Scanner",
        "description": "Backtested 50-62% WR rockets",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "min_score": 0,
        "require_mtf": False,
        "require_golden": False,
        "direction_filter": None,
        "require_rsi_gate": False,
        "source": "rocket_picks",
    },
}


# ---------------------------------------------------------------------------
# Pick loading & filtering
# ---------------------------------------------------------------------------
def _load_copy_trader_picks() -> List[dict]:
    """Load copy trader active picks."""
    data = _load_json(os.path.normpath(_COPY_PICKS))
    if isinstance(data, list):
        return data
    return []


def _load_smart_picks() -> List[dict]:
    """Load smart picks, flattening tiers."""
    data = _load_json(os.path.normpath(_SMART_PICKS))
    if not isinstance(data, dict):
        return []
    picks = []
    for tier_key in ["scalp_picks", "swing_picks", "core_picks"]:
        tier = data.get(tier_key, [])
        if isinstance(tier, list):
            picks.extend(tier)
    return picks


def _load_rocket_picks() -> List[dict]:
    """Load rocket scanner picks."""
    data = _load_json(os.path.normpath(_ROCKET_PICKS))
    if isinstance(data, dict):
        return data.get("picks", [])
    if isinstance(data, list):
        return data
    return []


def _normalize_pick(pick: dict, source: str) -> dict:
    """Normalize a pick to a common format."""
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", pick.get("signal_type", "LONG")).upper()
    if direction in ("SELL",):
        direction = "SHORT"
    if direction in ("BUY",):
        direction = "LONG"

    # Score: try multiple field names
    score = pick.get("smart_score",
            pick.get("elite_score",
            pick.get("ml_score",
            pick.get("confidence",
            pick.get("signal_score", 50)))))
    if isinstance(score, float) and score <= 1.0:
        score = int(score * 100)

    strategy = pick.get("strategy", source)
    entry = pick.get("entry_price", pick.get("entry", 0))

    return {
        "symbol": symbol,
        "direction": direction,
        "score": int(score) if score else 50,
        "strategy": strategy,
        "entry_price": float(entry) if entry else 0,
        "source": source,
        "id": pick.get("id", f"{strategy}::{symbol}"),
    }


def _get_candidate_picks(config: dict) -> List[dict]:
    """Load and filter picks for a given portfolio config."""
    source = config["source"]

    if source == "copy_traders":
        raw = _load_copy_trader_picks()
        picks = [_normalize_pick(p, "copy_traders") for p in raw]
    elif source == "smart_picks":
        raw = _load_smart_picks()
        picks = [_normalize_pick(p, "smart_picks") for p in raw]
    elif source == "rocket_picks":
        raw = _load_rocket_picks()
        picks = [_normalize_pick(p, "rocket_picks") for p in raw]
    else:
        picks = []

    # Apply filters
    filtered = []
    for p in picks:
        if not p["symbol"]:
            continue

        # Score filter
        if p["score"] < config["min_score"]:
            continue

        # Golden trader filter
        if config["require_golden"] and not _is_golden_trader(p["strategy"]):
            continue

        # Copy trader filter (for source=copy_traders with golden=False)
        if source == "copy_traders" and not config["require_golden"]:
            if not _is_copy_trader(p["strategy"]):
                continue

        # Direction filter
        if config["direction_filter"] and p["direction"] != config["direction_filter"]:
            continue

        filtered.append(p)

    return filtered


# ---------------------------------------------------------------------------
# Quarter Kelly position sizing
# ---------------------------------------------------------------------------
def quarter_kelly_size(equity: float, win_rate: float = 0.55, rr: float = 1.5) -> float:
    """Quarter Kelly position size in dollars."""
    if win_rate <= 0 or rr <= 0:
        return equity * 0.02  # 2% fallback
    b = rr
    q = 1.0 - win_rate
    kelly = (win_rate * b - q) / b
    if kelly <= 0:
        return equity * 0.01  # Minimum 1%
    quarter_k = kelly / 4.0
    # Cap at 5% of equity
    size_pct = min(quarter_k, 0.05)
    return equity * size_pct


# ---------------------------------------------------------------------------
# Portfolio state management
# ---------------------------------------------------------------------------
def _empty_portfolio(portfolio_id: str, config: dict) -> dict:
    """Create an empty portfolio state."""
    return {
        "id": portfolio_id,
        "name": config["name"],
        "description": config["description"],
        "starting_capital": STARTING_CAPITAL,
        "equity": STARTING_CAPITAL,
        "peak_equity": STARTING_CAPITAL,
        "max_drawdown_pct": 0.0,
        "open_positions": {},  # symbol -> position dict
        "closed_trades": [],
        "total_wins": 0,
        "total_losses": 0,
        "total_pnl": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "daily_equity_snapshots": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def load_state() -> dict:
    """Load all portfolio states."""
    data = _load_json(_STATE_FILE)
    if isinstance(data, dict) and "portfolios" in data:
        return data
    # Initialize fresh state
    state = {"portfolios": {}, "run_count": 0, "created_at": datetime.now(timezone.utc).isoformat()}
    for pid, cfg in PORTFOLIO_CONFIGS.items():
        state["portfolios"][pid] = _empty_portfolio(pid, cfg)
    return state


def save_state(state: dict) -> None:
    """Save portfolio states."""
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_json(_STATE_FILE, state)


# ---------------------------------------------------------------------------
# Core portfolio logic
# ---------------------------------------------------------------------------
def _add_position(portfolio: dict, pick: dict, live_price: float, config: dict) -> None:
    """Add a new position to the portfolio."""
    symbol = pick["symbol"]
    direction = pick["direction"]
    tp_pct = config["tp_pct"]
    sl_pct = config["sl_pct"]

    # Calculate TP/SL levels
    if direction == "LONG":
        tp_price = live_price * (1.0 + tp_pct / 100.0)
        sl_price = live_price * (1.0 - sl_pct / 100.0)
    else:  # SHORT
        tp_price = live_price * (1.0 - tp_pct / 100.0)
        sl_price = live_price * (1.0 + sl_pct / 100.0)

    # Quarter Kelly sizing — conservative default when insufficient history
    closed = portfolio.get("total_wins", 0) + portfolio.get("total_losses", 0)
    if closed >= 10:
        win_rate = portfolio["total_wins"] / closed
    else:
        # No assumed edge with <10 trades — use coin-flip (50%) instead of fake 55%
        win_rate = 0.50
        print(f"[POSITION SIZING] Using conservative 50% WR — insufficient trade history ({closed} < 10 closed)")
    allocation = quarter_kelly_size(portfolio["equity"], win_rate, tp_pct / sl_pct)
    allocation = max(allocation, 5.0)  # Minimum $5
    allocation = min(allocation, portfolio["equity"] * 0.10)  # Max 10% per position

    position = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": live_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "allocation": round(allocation, 2),
        "score": pick.get("score", 50),
        "strategy": pick.get("strategy", ""),
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    portfolio["open_positions"][symbol] = position


def _check_position(position: dict, live_price: float) -> Optional[dict]:
    """Check if position hit TP or SL. Returns closed trade dict or None."""
    direction = position["direction"]
    entry = position["entry_price"]
    tp = position["tp_price"]
    sl = position["sl_price"]

    if direction == "LONG":
        pnl_pct = ((live_price - entry) / entry) * 100.0
        hit_tp = live_price >= tp
        hit_sl = live_price <= sl
    else:  # SHORT
        pnl_pct = ((entry - live_price) / entry) * 100.0
        hit_tp = live_price <= tp
        hit_sl = live_price >= sl

    if hit_tp or hit_sl:
        exit_reason = "TP_HIT" if hit_tp else "SL_HIT"
        realized_pnl_pct = position["tp_pct"] if hit_tp else -position["sl_pct"]
        realized_pnl_dollar = position["allocation"] * (realized_pnl_pct / 100.0)

        return {
            "symbol": position["symbol"],
            "direction": direction,
            "entry_price": entry,
            "exit_price": live_price,
            "tp_price": tp,
            "sl_price": sl,
            "allocation": position["allocation"],
            "pnl_pct": round(realized_pnl_pct, 4),
            "pnl_dollar": round(realized_pnl_dollar, 4),
            "exit_reason": exit_reason,
            "won": hit_tp,
            "strategy": position.get("strategy", ""),
            "score": position.get("score", 0),
            "opened_at": position.get("opened_at", ""),
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }

    return None


def _compute_unrealized_pnl(position: dict, live_price: float) -> float:
    """Compute unrealized PnL percentage for open position."""
    entry = position["entry_price"]
    if entry == 0:
        return 0.0
    if position["direction"] == "LONG":
        return ((live_price - entry) / entry) * 100.0
    else:
        return ((entry - live_price) / entry) * 100.0


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------
def compute_metrics(portfolio: dict) -> dict:
    """Compute all metrics for a portfolio."""
    closed = portfolio.get("closed_trades", [])
    wins = portfolio.get("total_wins", 0)
    losses = portfolio.get("total_losses", 0)
    total = wins + losses

    win_rate = (wins / total * 100.0) if total > 0 else 0.0

    # Average win/loss
    win_pnls = [t["pnl_pct"] for t in closed if t.get("won")]
    loss_pnls = [t["pnl_pct"] for t in closed if not t.get("won")]
    avg_win = (sum(win_pnls) / len(win_pnls)) if win_pnls else 0.0
    avg_loss = (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0

    # Profit factor
    gross_profit = portfolio.get("gross_profit", 0.0)
    gross_loss = abs(portfolio.get("gross_loss", 0.0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    # Max drawdown
    max_dd = portfolio.get("max_drawdown_pct", 0.0)

    # Sharpe ratio (daily returns from equity snapshots)
    sharpe = 0.0
    snapshots = portfolio.get("daily_equity_snapshots", [])
    if len(snapshots) >= 5:
        returns = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1].get("equity", STARTING_CAPITAL)
            curr = snapshots[i].get("equity", STARTING_CAPITAL)
            if prev > 0:
                returns.append((curr - prev) / prev)
        if returns:
            mean_r = sum(returns) / len(returns)
            var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            std_r = math.sqrt(var_r) if var_r > 0 else 0.0001
            sharpe = (mean_r / std_r) * math.sqrt(365) if std_r > 0 else 0.0

    # Time in market (proportion of time with open positions)
    open_count = len(portfolio.get("open_positions", {}))

    # Total return
    equity = portfolio.get("equity", STARTING_CAPITAL)
    total_return_pct = ((equity - STARTING_CAPITAL) / STARTING_CAPITAL) * 100.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe_ratio": round(sharpe, 4),
        "equity": round(equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "total_pnl_dollar": round(portfolio.get("total_pnl", 0.0), 2),
        "open_positions": open_count,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


# ---------------------------------------------------------------------------
# Main run logic
# ---------------------------------------------------------------------------
def _process_portfolio(portfolio_id: str, portfolio: dict, config: dict,
                       prices: Dict[str, float], rsi_cache: Dict[str, Optional[float]],
                       mtf_cache: Dict[str, dict]) -> None:
    """Process one portfolio: check existing positions, add new picks."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Check existing positions for TP/SL hits
    to_close = []
    for symbol, pos in list(portfolio["open_positions"].items()):
        if symbol not in prices:
            continue
        live_price = prices[symbol]
        result = _check_position(pos, live_price)
        if result:
            to_close.append((symbol, result))

    # Close positions
    for symbol, trade in to_close:
        del portfolio["open_positions"][symbol]
        portfolio["closed_trades"].append(trade)
        if trade["won"]:
            portfolio["total_wins"] += 1
            portfolio["gross_profit"] += trade["pnl_dollar"]
        else:
            portfolio["total_losses"] += 1
            portfolio["gross_loss"] += trade["pnl_dollar"]
        portfolio["equity"] += trade["pnl_dollar"]
        portfolio["total_pnl"] += trade["pnl_dollar"]

    # Cap closed trades history to 200
    if len(portfolio["closed_trades"]) > 200:
        portfolio["closed_trades"] = portfolio["closed_trades"][-200:]

    # 2. Update unrealized PnL for open positions
    unrealized_total = 0.0
    for symbol, pos in portfolio["open_positions"].items():
        if symbol in prices:
            unrealized_total += _compute_unrealized_pnl(pos, prices[symbol]) * pos["allocation"] / 100.0

    # 3. Update equity tracking (mark-to-market)
    mark_equity = portfolio["equity"] + unrealized_total
    if mark_equity > portfolio["peak_equity"]:
        portfolio["peak_equity"] = mark_equity
    if portfolio["peak_equity"] > 0:
        dd = ((portfolio["peak_equity"] - mark_equity) / portfolio["peak_equity"]) * 100.0
        if dd > portfolio["max_drawdown_pct"]:
            portfolio["max_drawdown_pct"] = round(dd, 4)

    # 4. Add equity snapshot (one per run, keep last 200)
    portfolio["daily_equity_snapshots"].append({
        "timestamp": now_iso,
        "equity": round(mark_equity, 2),
        "open_positions": len(portfolio["open_positions"]),
    })
    if len(portfolio["daily_equity_snapshots"]) > 200:
        portfolio["daily_equity_snapshots"] = portfolio["daily_equity_snapshots"][-200:]

    # 5. Get candidate picks and add new positions
    candidates = _get_candidate_picks(config)

    # Don't add if we have too many open positions (max 10) or equity is too low
    max_positions = 10
    if len(portfolio["open_positions"]) >= max_positions:
        portfolio["last_updated"] = now_iso
        return
    if portfolio["equity"] <= 10.0:
        portfolio["last_updated"] = now_iso
        return

    for pick in candidates:
        symbol = pick["symbol"]

        # Skip if already have position in this symbol
        if symbol in portfolio["open_positions"]:
            continue

        # Skip if no price data
        if symbol not in prices:
            continue

        live_price = prices[symbol]
        if live_price <= 0:
            continue

        # MTF gate check
        if config["require_mtf"]:
            direction_for_mtf = "BULL" if pick["direction"] == "LONG" else "BEAR"
            mtf_key = f"{symbol}_{direction_for_mtf}"
            if mtf_key not in mtf_cache:
                mtf_cache[mtf_key] = check_mtf(symbol, direction_for_mtf)
            mtf_result = mtf_cache[mtf_key]
            if not mtf_result.get("aligned", True):
                # At least 2/3 timeframes must agree
                score_adj = mtf_result.get("score_adjustment", 0)
                if score_adj < -10:
                    continue

        # RSI gate check
        if config["require_rsi_gate"]:
            if symbol not in rsi_cache:
                rsi_cache[symbol] = get_rsi(symbol)
            rsi = rsi_cache[symbol]
            if rsi is not None:
                if pick["direction"] == "LONG" and rsi > 70:
                    continue  # Block LONG when RSI overbought
                if pick["direction"] == "SHORT" and rsi < 30:
                    continue  # Block SHORT when RSI oversold

        # Passed all filters -- add position
        _add_position(portfolio, pick, live_price, config)

        # Check position limit
        if len(portfolio["open_positions"]) >= max_positions:
            break

    portfolio["last_updated"] = now_iso


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------
def _format_comparison_table(all_metrics: Dict[str, dict]) -> str:
    """Format a comparison table of all portfolios."""
    lines = []
    lines.append("=" * 120)
    lines.append("A/B TEST PORTFOLIO COMPARISON")
    lines.append("=" * 120)
    lines.append("")

    header = (
        f"{'ID':<3} {'Portfolio':<24} {'Equity':>9} {'Return':>8} {'Trades':>7} "
        f"{'WR%':>6} {'AvgWin':>8} {'AvgLoss':>8} {'PF':>7} {'MaxDD':>7} "
        f"{'Sharpe':>7} {'Open':>5}"
    )
    lines.append(header)
    lines.append("-" * 120)

    sorted_ids = sorted(all_metrics.keys())
    for pid in sorted_ids:
        m = all_metrics[pid]
        cfg = PORTFOLIO_CONFIGS[pid]
        pf_str = str(m["profit_factor"]) if m["profit_factor"] != "inf" else "INF"
        line = (
            f"{pid:<3} {cfg['name']:<24} "
            f"${m['equity']:>7.2f} "
            f"{m['total_return_pct']:>7.2f}% "
            f"{m['total_trades']:>6d}  "
            f"{m['win_rate_pct']:>5.1f} "
            f"{m['avg_win_pct']:>7.3f}% "
            f"{m['avg_loss_pct']:>7.3f}% "
            f"{pf_str:>7} "
            f"{m['max_drawdown_pct']:>6.2f}% "
            f"{m['sharpe_ratio']:>7.3f} "
            f"{m['open_positions']:>4d}"
        )
        lines.append(line)

    lines.append("-" * 120)

    # Find best portfolio
    best_id = None
    best_return = -999999.0
    for pid, m in all_metrics.items():
        # Composite score: return% * (1 - maxDD/100) * (WR/100 + 0.5)
        wr = m["win_rate_pct"]
        ret = m["total_return_pct"]
        dd = m["max_drawdown_pct"]
        total = m["total_trades"]
        if total == 0:
            composite = -1000
        else:
            composite = ret * (1.0 - dd / 100.0) * (wr / 100.0 + 0.5)
        if composite > best_return:
            best_return = composite
            best_id = pid

    if best_id:
        bm = all_metrics[best_id]
        bc = PORTFOLIO_CONFIGS[best_id]
        lines.append("")
        lines.append(f"BEST PORTFOLIO: [{best_id}] {bc['name']}")
        reasons = []
        if bm["total_trades"] > 0:
            reasons.append(f"{bm['win_rate_pct']:.1f}% win rate across {bm['total_trades']} trades")
            reasons.append(f"{bm['total_return_pct']:.2f}% total return (${bm['equity']:.2f})")
            if bm["max_drawdown_pct"] > 0:
                reasons.append(f"Max drawdown only {bm['max_drawdown_pct']:.2f}%")
            if bm["profit_factor"] != "inf" and bm["profit_factor"] > 0:
                reasons.append(f"Profit factor {bm['profit_factor']:.2f}")
        else:
            reasons.append("No trades yet -- waiting for data")
        lines.append("  WHY: " + " | ".join(reasons))

    lines.append("")
    lines.append(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("=" * 120)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------
def run() -> dict:
    """
    Run one iteration of the A/B test across all 8 portfolios.

    Returns dict with metrics for all portfolios.
    """
    print("[AB Test] Loading state...")
    state = load_state()
    state["run_count"] = state.get("run_count", 0) + 1

    # Ensure all portfolios exist in state
    for pid, cfg in PORTFOLIO_CONFIGS.items():
        if pid not in state["portfolios"]:
            state["portfolios"][pid] = _empty_portfolio(pid, cfg)

    # Collect all unique symbols across all portfolios
    all_symbols = set()

    # From existing open positions
    for pid, pf in state["portfolios"].items():
        for sym in pf.get("open_positions", {}):
            all_symbols.add(sym)

    # From candidate picks (pre-load to know what symbols we need prices for)
    candidate_cache = {}
    for pid, cfg in PORTFOLIO_CONFIGS.items():
        candidates = _get_candidate_picks(cfg)
        candidate_cache[pid] = candidates
        for p in candidates:
            if p["symbol"]:
                all_symbols.add(p["symbol"])

    print(f"[AB Test] Fetching prices for {len(all_symbols)} symbols...")
    prices = fetch_prices_batch(list(all_symbols))
    print(f"[AB Test] Got {len(prices)} prices")

    # Shared caches for RSI and MTF (avoid redundant API calls)
    rsi_cache: Dict[str, Optional[float]] = {}
    mtf_cache: Dict[str, dict] = {}

    # Process each portfolio
    all_metrics = {}
    for pid in sorted(PORTFOLIO_CONFIGS.keys()):
        cfg = PORTFOLIO_CONFIGS[pid]
        pf = state["portfolios"][pid]
        print(f"[AB Test] Processing portfolio {pid}: {cfg['name']}...")
        _process_portfolio(pid, pf, cfg, prices, rsi_cache, mtf_cache)
        metrics = compute_metrics(pf)
        all_metrics[pid] = metrics

    # Print comparison table
    table = _format_comparison_table(all_metrics)
    print(table)

    # Save state
    save_state(state)

    # Append to results history (cap at 200 entries)
    results_history = _load_json(_RESULTS_FILE)
    if not isinstance(results_history, list):
        results_history = []

    results_entry = {
        "run_number": state["run_count"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": all_metrics,
        "best_portfolio": None,
    }

    # Find best
    best_id = None
    best_composite = -999999.0
    for pid, m in all_metrics.items():
        total = m["total_trades"]
        if total == 0:
            composite = -1000
        else:
            wr = m["win_rate_pct"]
            ret = m["total_return_pct"]
            dd = m["max_drawdown_pct"]
            composite = ret * (1.0 - dd / 100.0) * (wr / 100.0 + 0.5)
        if composite > best_composite:
            best_composite = composite
            best_id = pid
    if best_id:
        results_entry["best_portfolio"] = {
            "id": best_id,
            "name": PORTFOLIO_CONFIGS[best_id]["name"],
            "composite_score": round(best_composite, 4),
        }

    results_history.append(results_entry)
    if len(results_history) > 200:
        results_history = results_history[-200:]
    _save_json(_RESULTS_FILE, results_history)

    print(f"\n[AB Test] State saved to {_STATE_FILE}")
    print(f"[AB Test] Results appended to {_RESULTS_FILE} ({len(results_history)} entries)")
    print(f"[AB Test] Run #{state['run_count']} complete.")

    return all_metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()

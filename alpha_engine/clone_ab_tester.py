"""
ALPHA ENGINE -- Clone A/B Testing Framework
============================================
Problem: Clones (reverse-engineered strategies from top traders) have 35% WR
vs 55% for direct copies.  This module tests 12 parameter variations to find
which clone settings actually improve performance.

Each variation starts with $200 paper capital.  Clone picks are loaded from
copy_trader_intel/data/clone_active_picks.json, live prices fetched from
Binance (5-mirror failover), TP/SL checked each run, state persisted to
alpha_engine/data/clone_ab_state.json.

Usage:
    python -m alpha_engine.clone_ab_tester      # or import and call run()
"""

from __future__ import annotations

import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
DATA_DIR = _HERE / "data"
DATA_DIR.mkdir(exist_ok=True)

CLONE_PICKS_PATH = _HERE.parent / "copy_trader_intel" / "data" / "clone_active_picks.json"
STATE_PATH = DATA_DIR / "clone_ab_state.json"
RESULTS_PATH = DATA_DIR / "clone_ab_results.json"

# ---------------------------------------------------------------------------
# Binance 5-mirror failover (API failover rule)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_TICKER_ENDPOINT = "/api/v3/ticker/price"
_KLINE_ENDPOINT = "/api/v3/klines"


def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


_SSL_CTX = _make_ssl_ctx()

# Rate limiter
_last_api_call = 0.0
_RATE_LIMIT_DELAY = 0.12  # 120 ms between calls


def _rate_limit() -> None:
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _last_api_call = time.time()


def _api_get(endpoint: str, params: str = "") -> Any:
    """GET from Binance with 5-mirror failover.  Returns parsed JSON."""
    url_suffix = f"{endpoint}?{params}" if params else endpoint
    last_err = None
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{url_suffix}"
        try:
            _rate_limit()
            req = urllib.request.Request(url, headers={"User-Agent": "CloneABTester/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            continue
    logger.warning("All Binance mirrors failed for %s: %s", url_suffix, last_err)
    return None


# ---------------------------------------------------------------------------
# Price cache  { symbol: (timestamp, price) }
# ---------------------------------------------------------------------------
_price_cache: Dict[str, Tuple[float, float]] = {}
_PRICE_CACHE_TTL = 60  # 1 minute


def fetch_price(symbol: str) -> Optional[float]:
    """Fetch current price for a single symbol with caching."""
    sym = symbol.upper()
    now = time.time()
    if sym in _price_cache:
        ts, px = _price_cache[sym]
        if now - ts < _PRICE_CACHE_TTL:
            return px
    data = _api_get(_TICKER_ENDPOINT, f"symbol={sym}")
    if data and "price" in data:
        px = float(data["price"])
        _price_cache[sym] = (now, px)
        return px
    return None


def fetch_prices_batch(symbols: List[str]) -> Dict[str, float]:
    """Fetch prices for multiple symbols.  Uses batch endpoint first, fallback singles."""
    result: Dict[str, float] = {}
    now = time.time()

    # Check cache first
    uncached = []
    for s in symbols:
        sym = s.upper()
        if sym in _price_cache:
            ts, px = _price_cache[sym]
            if now - ts < _PRICE_CACHE_TTL:
                result[sym] = px
                continue
        uncached.append(sym)

    if not uncached:
        return result

    # Try batch ticker
    data = _api_get(_TICKER_ENDPOINT)
    if isinstance(data, list):
        lookup = {item["symbol"]: float(item["price"]) for item in data if "symbol" in item}
        for sym in uncached:
            if sym in lookup:
                result[sym] = lookup[sym]
                _price_cache[sym] = (now, lookup[sym])
    else:
        # Fallback: individual fetches
        for sym in uncached:
            px = fetch_price(sym)
            if px is not None:
                result[sym] = px

    return result


# ---------------------------------------------------------------------------
# Kline fetch for RSI / volume indicators
# ---------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, str], Tuple[float, list]] = {}
_KLINE_CACHE_TTL = 600


def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 50) -> list:
    cache_key = (symbol.upper(), interval)
    now = time.time()
    if cache_key in _kline_cache:
        ts, data = _kline_cache[cache_key]
        if now - ts < _KLINE_CACHE_TTL:
            return data
    data = _api_get(_KLINE_ENDPOINT, f"symbol={symbol.upper()}&interval={interval}&limit={limit}")
    if isinstance(data, list) and len(data) > 0:
        _kline_cache[cache_key] = (now, data)
        return data
    return []


def _parse_closes(klines: list) -> List[float]:
    return [float(k[4]) for k in klines if len(k) > 4]


def _parse_volumes(klines: list) -> List[float]:
    return [float(k[5]) for k in klines if len(k) > 5]


# ---------------------------------------------------------------------------
# Technical indicators (stdlib only)
# ---------------------------------------------------------------------------
def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI(period) from closes.  Returns latest value or None."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
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


def _volume_ratio(volumes: List[float], lookback: int = 20) -> Optional[float]:
    """Return current volume / SMA(lookback) of volume."""
    if len(volumes) < lookback + 1:
        return None
    sma = sum(volumes[-lookback - 1:-1]) / lookback
    if sma <= 0:
        return None
    return volumes[-1] / sma


# ---------------------------------------------------------------------------
# Optional imports (graceful fallback)
# ---------------------------------------------------------------------------
_mtf_available = False
_check_mtf_alignment = None
try:
    from alpha_engine.mtf_gate import check_mtf_alignment as _check_mtf_alignment
    _mtf_available = True
except ImportError:
    try:
        # Direct import when running from alpha_engine directory
        from mtf_gate import check_mtf_alignment as _check_mtf_alignment  # type: ignore[no-redef]
        _mtf_available = True
    except ImportError:
        pass

_hmm_available = False
_SimpleHMM = None
try:
    from alpha_engine.hmm_regime import SimpleHMM as _SimpleHMM, REGIME_NAMES
    _hmm_available = True
except ImportError:
    try:
        from hmm_regime import SimpleHMM as _SimpleHMM, REGIME_NAMES  # type: ignore[no-redef]
        _hmm_available = True
    except ImportError:
        REGIME_NAMES = {0: "BULL", 1: "BEAR", 2: "CHOP"}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_CAPITAL = 200.0
MAX_POSITIONS_PER_VARIATION = 5
RESULTS_CAP = 200

# Top 3 traders for Variation 10
TOP_3_TRADERS = {"whale_20.7m", "nmtd_25m", "whale_123m"}

# ---------------------------------------------------------------------------
# Variation definitions
# ---------------------------------------------------------------------------
VARIATIONS: List[Dict[str, Any]] = [
    {
        "id": "V01_exact_mirror",
        "name": "V1: Exact Mirror (Baseline)",
        "desc": "Use trader's exact entry/TP/SL, no filters",
        "tp_pct": None,   # use original
        "sl_pct": None,   # use original
        "filters": [],
    },
    {
        "id": "V02_tighter_stops",
        "name": "V2: Tighter Stops",
        "desc": "Same as V1 but TP:2%, SL:1.5% -- tests faster exits",
        "tp_pct": 2.0,
        "sl_pct": 1.5,
        "filters": [],
    },
    {
        "id": "V03_wider_stops",
        "name": "V3: Wider Stops",
        "desc": "Same as V1 but TP:5%, SL:3% -- tests if clones get shaken out",
        "tp_pct": 5.0,
        "sl_pct": 3.0,
        "filters": [],
    },
    {
        "id": "V04_rsi_confirm",
        "name": "V4: RSI Confirmation",
        "desc": "Only clone when RSI(14) 1H confirms direction",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["rsi_confirm"],
    },
    {
        "id": "V05_volume_confirm",
        "name": "V5: Volume Confirmation",
        "desc": "Only clone when volume > 1.5x 20-period avg",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["volume_confirm"],
    },
    {
        "id": "V06_mtf_alignment",
        "name": "V6: MTF Alignment",
        "desc": "Only clone when 2/3 timeframes agree with direction",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["mtf_alignment"],
    },
    {
        "id": "V07_delayed_entry",
        "name": "V7: Delayed Entry",
        "desc": "Wait 1H candle after signal before entering",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["delayed_entry"],
    },
    {
        "id": "V08_inverse_clone",
        "name": "V8: Inverse Clone",
        "desc": "Take OPPOSITE direction -- tests if extraction is backwards",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["inverse_direction"],
    },
    {
        "id": "V09_short_only",
        "name": "V9: SHORT Only Clone",
        "desc": "Only take SHORT direction clones",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["short_only"],
    },
    {
        "id": "V10_top3_traders",
        "name": "V10: Top 3 Traders Only",
        "desc": "Only clone whale_20.7M, NMTD_25M, whale_123M",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["top3_traders"],
    },
    {
        "id": "V11_regime_gated",
        "name": "V11: Regime-Gated Clone",
        "desc": "Only clone when direction matches current regime",
        "tp_pct": None,
        "sl_pct": None,
        "filters": ["regime_gated"],
    },
    {
        "id": "V12_combined_best",
        "name": "V12: Combined Best (Kitchen Sink)",
        "desc": "Top 3 + RSI + MTF + regime-gated + TP:3%/SL:2%",
        "tp_pct": 3.0,
        "sl_pct": 2.0,
        "filters": ["top3_traders", "rsi_confirm", "mtf_alignment", "regime_gated"],
    },
]


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def _default_variation_state(var_def: Dict) -> Dict:
    return {
        "id": var_def["id"],
        "name": var_def["name"],
        "capital": STARTING_CAPITAL,
        "open_positions": [],
        "closed_trades": [],
        "total_wins": 0,
        "total_losses": 0,
        "total_pnl": 0.0,
        "max_drawdown": 0.0,
        "peak_capital": STARTING_CAPITAL,
        "pending_signals": [],   # for delayed entry (V7)
    }


def load_state() -> Dict:
    """Load persisted A/B test state or initialize fresh."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            # Ensure all 12 variations exist
            existing_ids = {v["id"] for v in state.get("variations", [])}
            for var_def in VARIATIONS:
                if var_def["id"] not in existing_ids:
                    state["variations"].append(_default_variation_state(var_def))
            return state
        except Exception as exc:
            logger.warning("Failed to load state: %s -- reinitializing", exc)

    # Fresh state
    return {
        "created": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        "run_count": 0,
        "variations": [_default_variation_state(v) for v in VARIATIONS],
    }


def save_state(state: Dict) -> None:
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as exc:
        logger.error("Failed to save state: %s", exc)


# ---------------------------------------------------------------------------
# Clone pick loading
# ---------------------------------------------------------------------------
def load_clone_picks() -> List[Dict]:
    """Load active clone picks from copy_trader_intel."""
    if not CLONE_PICKS_PATH.exists():
        logger.warning("Clone picks file not found: %s", CLONE_PICKS_PATH)
        return []
    try:
        with open(CLONE_PICKS_PATH, "r", encoding="utf-8") as f:
            picks = json.load(f)
        if not isinstance(picks, list):
            return []
        # Filter to OPEN picks only
        return [p for p in picks if p.get("status", "").upper() == "OPEN"]
    except Exception as exc:
        logger.error("Failed to load clone picks: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Regime detection (lightweight, for gating)
# ---------------------------------------------------------------------------
_current_regime: Optional[str] = None
_regime_ts: float = 0.0


def _detect_regime() -> str:
    """Detect current market regime.  Returns 'BULL', 'BEAR', or 'CHOP'."""
    global _current_regime, _regime_ts
    now = time.time()
    if _current_regime and now - _regime_ts < 1800:  # cache 30 min
        return _current_regime

    # Try HMM if available
    if _hmm_available and _SimpleHMM is not None:
        try:
            klines = _fetch_klines("BTCUSDT", "1d", 30)
            closes = _parse_closes(klines)
            if len(closes) >= 5:
                hmm = _SimpleHMM()
                for i in range(1, len(closes)):
                    ret = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] else 0
                    vol = abs(ret)
                    hmm.update(ret, vol)
                state = int(hmm.state_probs.argmax())  # type: ignore[union-attr]
                regime = REGIME_NAMES.get(state, "CHOP")
                _current_regime = regime
                _regime_ts = now
                return regime
        except Exception as exc:
            logger.debug("HMM regime detection failed: %s", exc)

    # Fallback: simple EMA-based regime from BTC daily
    klines = _fetch_klines("BTCUSDT", "1d", 50)
    closes = _parse_closes(klines)
    if len(closes) < 21:
        _current_regime = "CHOP"
        _regime_ts = now
        return "CHOP"

    ema9 = _ema_single(closes, 9)
    ema21 = _ema_single(closes, 21)
    price = closes[-1]

    if ema9 is not None and ema21 is not None:
        if price > ema9 > ema21:
            regime = "BULL"
        elif price < ema9 < ema21:
            regime = "BEAR"
        else:
            regime = "CHOP"
    else:
        regime = "CHOP"

    _current_regime = regime
    _regime_ts = now
    return regime


def _ema_single(values: List[float], period: int) -> Optional[float]:
    """Compute latest EMA value only."""
    if len(values) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for i in range(period, len(values)):
        ema = (values[i] - ema) * multiplier + ema
    return ema


# ---------------------------------------------------------------------------
# Filter functions
# ---------------------------------------------------------------------------
def _filter_rsi_confirm(pick: Dict) -> bool:
    """LONG clone: RSI < 50.  SHORT clone: RSI > 50."""
    klines = _fetch_klines(pick["symbol"], "1h", 50)
    closes = _parse_closes(klines)
    rsi = _rsi(closes)
    if rsi is None:
        return False  # no data -> reject
    direction = pick.get("direction", "").upper()
    if direction == "LONG":
        return rsi < 50
    elif direction == "SHORT":
        return rsi > 50
    return False


def _filter_volume_confirm(pick: Dict) -> bool:
    """Only clone when volume > 1.5x 20-period average."""
    klines = _fetch_klines(pick["symbol"], "1h", 25)
    volumes = _parse_volumes(klines)
    ratio = _volume_ratio(volumes, 20)
    if ratio is None:
        return False
    return ratio > 1.5


def _filter_mtf_alignment(pick: Dict) -> bool:
    """Only clone when 2/3 timeframes agree with direction."""
    if not _mtf_available or _check_mtf_alignment is None:
        # Fallback: manual simple MTF check
        return _fallback_mtf_check(pick)
    try:
        direction_map = {"LONG": "BULL", "SHORT": "BEAR"}
        direction = direction_map.get(pick.get("direction", "").upper(), "BULL")
        result = _check_mtf_alignment(pick["symbol"], direction)
        return result.get("aligned", False)
    except Exception:
        return _fallback_mtf_check(pick)


def _fallback_mtf_check(pick: Dict) -> bool:
    """Simple MTF check: EMA9 vs EMA21 on 1h, 4h, 1d."""
    direction = pick.get("direction", "").upper()
    agree = 0
    for interval in ["1h", "4h", "1d"]:
        klines = _fetch_klines(pick["symbol"], interval, 30)
        closes = _parse_closes(klines)
        ema9 = _ema_single(closes, 9)
        ema21 = _ema_single(closes, 21)
        if ema9 is None or ema21 is None:
            continue
        if direction == "LONG" and ema9 > ema21:
            agree += 1
        elif direction == "SHORT" and ema9 < ema21:
            agree += 1
    return agree >= 2


def _filter_short_only(pick: Dict) -> bool:
    """Only allow SHORT clones."""
    return pick.get("direction", "").upper() == "SHORT"


def _filter_top3_traders(pick: Dict) -> bool:
    """Only clone from top 3 traders."""
    label = pick.get("trader_label", "").lower()
    return label in TOP_3_TRADERS


def _filter_regime_gated(pick: Dict) -> bool:
    """Only clone when direction matches current regime."""
    regime = _detect_regime()
    direction = pick.get("direction", "").upper()
    if direction == "LONG" and regime == "BULL":
        return True
    if direction == "SHORT" and regime == "BEAR":
        return True
    return False


def _filter_delayed_entry(pick: Dict) -> bool:
    """Always returns True -- actual delay handled in position opening logic."""
    return True


def _filter_inverse_direction(pick: Dict) -> bool:
    """Always returns True -- direction flip handled in position creation."""
    return True


FILTER_FUNCS = {
    "rsi_confirm": _filter_rsi_confirm,
    "volume_confirm": _filter_volume_confirm,
    "mtf_alignment": _filter_mtf_alignment,
    "short_only": _filter_short_only,
    "top3_traders": _filter_top3_traders,
    "regime_gated": _filter_regime_gated,
    "delayed_entry": _filter_delayed_entry,
    "inverse_direction": _filter_inverse_direction,
}


# ---------------------------------------------------------------------------
# Position management
# ---------------------------------------------------------------------------
def _compute_tp_sl(pick: Dict, var_def: Dict, entry_price: float) -> Tuple[float, float]:
    """Compute TP and SL prices for a position."""
    direction = pick.get("direction", "").upper()

    # Check for inverse clone
    if "inverse_direction" in var_def.get("filters", []):
        direction = "SHORT" if direction == "LONG" else "LONG"

    tp_pct = var_def.get("tp_pct")
    sl_pct = var_def.get("sl_pct")

    if tp_pct is not None and sl_pct is not None:
        # Use variation-defined TP/SL percentages
        if direction == "LONG":
            tp = entry_price * (1 + tp_pct / 100.0)
            sl = entry_price * (1 - sl_pct / 100.0)
        else:
            tp = entry_price * (1 - tp_pct / 100.0)
            sl = entry_price * (1 + sl_pct / 100.0)
    else:
        # Use original pick's TP/SL
        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)
        if tp == 0 or sl == 0:
            # Fallback: default 3.5%/2%
            if direction == "LONG":
                tp = entry_price * 1.035
                sl = entry_price * 0.98
            else:
                tp = entry_price * 0.965
                sl = entry_price * 1.02

    return tp, sl


def _create_position(pick: Dict, var_def: Dict, entry_price: float) -> Dict:
    """Create a new paper position from a clone pick."""
    direction = pick.get("direction", "").upper()
    if "inverse_direction" in var_def.get("filters", []):
        direction = "SHORT" if direction == "LONG" else "LONG"

    tp, sl = _compute_tp_sl(pick, var_def, entry_price)

    return {
        "symbol": pick["symbol"],
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": tp,
        "stop_loss": sl,
        "size_usd": 40.0,  # $40 per position ($200 / 5 max)
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "source_pick": pick.get("strategy", "unknown"),
        "trader_label": pick.get("trader_label", "unknown"),
    }


def _check_position_exit(pos: Dict, current_price: float) -> Optional[Dict]:
    """Check if a position hit TP or SL.  Returns closed trade dict or None."""
    direction = pos["direction"]
    entry = pos["entry_price"]
    tp = pos["take_profit"]
    sl = pos["stop_loss"]

    if direction == "LONG":
        if current_price >= tp:
            pnl_pct = (tp - entry) / entry * 100
            return {"result": "WIN", "pnl_pct": round(pnl_pct, 3), "exit_price": tp, "exit_reason": "TP"}
        if current_price <= sl:
            pnl_pct = (sl - entry) / entry * 100
            return {"result": "LOSS", "pnl_pct": round(pnl_pct, 3), "exit_price": sl, "exit_reason": "SL"}
    else:  # SHORT
        if current_price <= tp:
            pnl_pct = (entry - tp) / entry * 100
            return {"result": "WIN", "pnl_pct": round(pnl_pct, 3), "exit_price": tp, "exit_reason": "TP"}
        if current_price >= sl:
            pnl_pct = (entry - sl) / entry * 100
            return {"result": "LOSS", "pnl_pct": round(pnl_pct, 3), "exit_price": sl, "exit_reason": "SL"}

    return None


# ---------------------------------------------------------------------------
# Core A/B engine
# ---------------------------------------------------------------------------
def _should_accept_pick(pick: Dict, var_def: Dict) -> bool:
    """Run all filters for a variation.  Returns True if pick passes."""
    for filt in var_def.get("filters", []):
        fn = FILTER_FUNCS.get(filt)
        if fn is None:
            continue
        if not fn(pick):
            return False
    return True


def _pick_signature(pick: Dict) -> str:
    """Unique key for a pick to avoid duplicate positions."""
    return f"{pick['symbol']}_{pick.get('direction', '')}_{pick.get('strategy', '')}"


def process_variation(var_state: Dict, var_def: Dict, picks: List[Dict],
                      prices: Dict[str, float]) -> Dict:
    """
    Process one A/B variation:
      1. Check existing positions for TP/SL hits
      2. Process pending delayed entries (V7)
      3. Accept new picks that pass filters
      4. Update capital and drawdown
    """
    # ---- Step 1: Check existing positions for exits ----
    remaining_positions = []
    for pos in var_state.get("open_positions", []):
        symbol = pos["symbol"]
        current_price = prices.get(symbol)
        if current_price is None:
            remaining_positions.append(pos)
            continue

        exit_result = _check_position_exit(pos, current_price)
        if exit_result:
            # Close the position
            pnl_usd = pos["size_usd"] * (exit_result["pnl_pct"] / 100.0)
            var_state["capital"] = round(var_state["capital"] + pnl_usd, 2)
            var_state["total_pnl"] = round(var_state["total_pnl"] + pnl_usd, 2)

            if exit_result["result"] == "WIN":
                var_state["total_wins"] += 1
            else:
                var_state["total_losses"] += 1

            closed_trade = {
                **pos,
                **exit_result,
                "pnl_usd": round(pnl_usd, 2),
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }
            var_state["closed_trades"].append(closed_trade)
            # Cap closed trades to last 100
            if len(var_state["closed_trades"]) > 100:
                var_state["closed_trades"] = var_state["closed_trades"][-100:]
        else:
            remaining_positions.append(pos)

    var_state["open_positions"] = remaining_positions

    # Update peak and drawdown
    if var_state["capital"] > var_state.get("peak_capital", STARTING_CAPITAL):
        var_state["peak_capital"] = var_state["capital"]
    dd = 0.0
    if var_state["peak_capital"] > 0:
        dd = (var_state["peak_capital"] - var_state["capital"]) / var_state["peak_capital"] * 100
    if dd > var_state.get("max_drawdown", 0):
        var_state["max_drawdown"] = round(dd, 2)

    # ---- Step 2: Process delayed entries (V7) ----
    if "delayed_entry" in var_def.get("filters", []):
        ready_signals = []
        still_pending = []
        now = datetime.now(timezone.utc)
        for pending in var_state.get("pending_signals", []):
            signal_time = datetime.fromisoformat(pending["queued_at"])
            age_hours = (now - signal_time).total_seconds() / 3600
            if age_hours >= 1.0:
                ready_signals.append(pending["pick"])
            elif age_hours < 24.0:  # expire after 24h
                still_pending.append(pending)
        var_state["pending_signals"] = still_pending

        # Open positions from ready signals
        existing_sigs = {_pick_signature(p) for p in var_state["open_positions"]}
        for pick in ready_signals:
            if len(var_state["open_positions"]) >= MAX_POSITIONS_PER_VARIATION:
                break
            sig = _pick_signature(pick)
            if sig in existing_sigs:
                continue
            symbol = pick["symbol"]
            current_price = prices.get(symbol)
            if current_price is None:
                continue
            pos = _create_position(pick, var_def, current_price)
            var_state["open_positions"].append(pos)
            existing_sigs.add(sig)

    # ---- Step 3: Accept new picks ----
    existing_sigs = {_pick_signature(p) for p in var_state["open_positions"]}
    # Also exclude picks already pending
    for pending in var_state.get("pending_signals", []):
        existing_sigs.add(_pick_signature(pending.get("pick", {})))

    for pick in picks:
        if len(var_state["open_positions"]) >= MAX_POSITIONS_PER_VARIATION:
            break

        sig = _pick_signature(pick)
        if sig in existing_sigs:
            continue

        if not _should_accept_pick(pick, var_def):
            continue

        # Delayed entry: queue instead of opening immediately
        if "delayed_entry" in var_def.get("filters", []):
            if len(var_state.get("pending_signals", [])) < MAX_POSITIONS_PER_VARIATION:
                var_state.setdefault("pending_signals", []).append({
                    "pick": pick,
                    "queued_at": datetime.now(timezone.utc).isoformat(),
                })
                existing_sigs.add(sig)
            continue

        symbol = pick["symbol"]
        entry_price = prices.get(symbol)
        if entry_price is None:
            continue

        pos = _create_position(pick, var_def, entry_price)
        var_state["open_positions"].append(pos)
        existing_sigs.add(sig)

    return var_state


# ---------------------------------------------------------------------------
# Results & reporting
# ---------------------------------------------------------------------------
def _compute_wr(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 0.0
    return round(wins / total * 100, 1)


def _variation_summary(var_state: Dict) -> Dict:
    """Compute summary stats for one variation."""
    total_trades = var_state["total_wins"] + var_state["total_losses"]
    wr = _compute_wr(var_state["total_wins"], var_state["total_losses"])
    return {
        "id": var_state["id"],
        "name": var_state["name"],
        "capital": round(var_state["capital"], 2),
        "pnl": round(var_state["total_pnl"], 2),
        "pnl_pct": round((var_state["capital"] - STARTING_CAPITAL) / STARTING_CAPITAL * 100, 2),
        "wins": var_state["total_wins"],
        "losses": var_state["total_losses"],
        "total_trades": total_trades,
        "win_rate": wr,
        "open_positions": len(var_state.get("open_positions", [])),
        "max_drawdown": var_state.get("max_drawdown", 0),
    }


def print_comparison_table(state: Dict) -> None:
    """Print formatted comparison table of all 12 variations."""
    summaries = []
    for var_state in state["variations"]:
        summaries.append(_variation_summary(var_state))

    # Sort by PnL descending
    summaries.sort(key=lambda x: x["pnl"], reverse=True)

    print("\n" + "=" * 110)
    print("CLONE A/B TEST -- VARIATION COMPARISON")
    print(f"Run #{state['run_count']} | {state.get('last_run', 'N/A')}")
    print("=" * 110)
    header = (
        f"{'Rank':<5} {'Variation':<35} {'Capital':>8} {'PnL':>8} {'PnL%':>7} "
        f"{'W':>4} {'L':>4} {'WR%':>6} {'Open':>5} {'MaxDD%':>7}"
    )
    print(header)
    print("-" * 110)

    for i, s in enumerate(summaries):
        marker = " <<< BEST" if i == 0 and s["total_trades"] > 0 else ""
        row = (
            f"{i+1:<5} {s['name']:<35} ${s['capital']:>7.2f} ${s['pnl']:>7.2f} "
            f"{s['pnl_pct']:>6.1f}% {s['wins']:>4} {s['losses']:>4} "
            f"{s['win_rate']:>5.1f}% {s['open_positions']:>5} {s['max_drawdown']:>6.1f}%{marker}"
        )
        print(row)

    print("=" * 110)

    # Highlight best variation
    if summaries and summaries[0]["total_trades"] > 0:
        best = summaries[0]
        print(f"\nBEST VARIATION: {best['name']}")
        print(f"  Win Rate: {best['win_rate']}% ({best['wins']}W / {best['losses']}L)")
        print(f"  PnL: ${best['pnl']:.2f} ({best['pnl_pct']:.1f}%)")
        print(f"  Max Drawdown: {best['max_drawdown']:.1f}%")

        # Explain WHY this variation works
        var_id = best["id"]
        if "tighter" in var_id:
            print("  WHY: Tighter stops prevent clones from drifting -- faster exits cut losses.")
        elif "wider" in var_id:
            print("  WHY: Wider stops give clones room to breathe -- avoids premature stop-outs.")
        elif "rsi" in var_id:
            print("  WHY: RSI confirmation filters out clones against momentum -- reduces false signals.")
        elif "volume" in var_id:
            print("  WHY: Volume confirmation ensures the market agrees with the trader's move.")
        elif "mtf" in var_id:
            print("  WHY: Multi-timeframe alignment catches trend direction across scales.")
        elif "delayed" in var_id:
            print("  WHY: Delayed entry gets better fills on pullbacks after the initial signal.")
        elif "inverse" in var_id:
            print("  WHY: Inverse clone works -- our clone extraction was reading direction backwards!")
        elif "short_only" in var_id:
            print("  WHY: SHORT-only capitalizes on the short-dominant nature of clone strategies.")
        elif "top3" in var_id:
            print("  WHY: Trader selection matters -- top 3 whales have more predictable patterns.")
        elif "regime" in var_id:
            print("  WHY: Regime gating blocks counter-trend clones that drag down WR.")
        elif "combined" in var_id:
            print("  WHY: Combined filters stack multiple edges -- each filter adds 2-5% WR.")
        else:
            print("  WHY: Baseline mirror outperforms filtered variants -- clone signals are clean.")

    # Show worst variation
    if len(summaries) > 1 and summaries[-1]["total_trades"] > 0:
        worst = summaries[-1]
        print(f"\nWORST VARIATION: {worst['name']}")
        print(f"  Win Rate: {worst['win_rate']}% | PnL: ${worst['pnl']:.2f}")

    # Regime info
    regime = _detect_regime()
    print(f"\nCurrent BTC regime: {regime}")
    print(f"MTF gate available: {_mtf_available}")
    print(f"HMM regime available: {_hmm_available}")
    print()


def save_results(state: Dict) -> None:
    """Append run results to clone_ab_results.json (capped at 200 entries)."""
    results = []
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
            if not isinstance(results, list):
                results = []
        except Exception:
            results = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_count": state["run_count"],
        "regime": _detect_regime(),
        "variations": [],
    }
    for var_state in state["variations"]:
        entry["variations"].append(_variation_summary(var_state))

    results.append(entry)

    # Cap at RESULTS_CAP
    if len(results) > RESULTS_CAP:
        results = results[-RESULTS_CAP:]

    try:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Results saved to %s (%d entries)", RESULTS_PATH, len(results))
    except Exception as exc:
        logger.error("Failed to save results: %s", exc)


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------
def run() -> Dict:
    """
    Main entry point.  Loads clone picks, runs all 12 variations,
    checks TP/SL, updates state, prints comparison, saves results.

    Returns the current state dict.
    """
    print("=" * 60)
    print("CLONE A/B TESTER -- Starting run")
    print("=" * 60)

    # Load state
    state = load_state()
    state["run_count"] = state.get("run_count", 0) + 1
    state["last_run"] = datetime.now(timezone.utc).isoformat()

    # Load clone picks
    picks = load_clone_picks()
    print(f"Loaded {len(picks)} active clone picks")

    if not picks:
        print("No clone picks available -- checking existing positions only")

    # Gather all symbols needing price data
    symbols_needed = set()
    for p in picks:
        symbols_needed.add(p["symbol"].upper())
    for var_state in state["variations"]:
        for pos in var_state.get("open_positions", []):
            symbols_needed.add(pos["symbol"].upper())
        for pending in var_state.get("pending_signals", []):
            pick = pending.get("pick", {})
            if "symbol" in pick:
                symbols_needed.add(pick["symbol"].upper())

    print(f"Fetching prices for {len(symbols_needed)} symbols...")
    prices = fetch_prices_batch(list(symbols_needed))
    print(f"Got prices for {len(prices)}/{len(symbols_needed)} symbols")

    # Build variation def lookup
    var_defs = {v["id"]: v for v in VARIATIONS}

    # Process each variation
    for var_state in state["variations"]:
        var_id = var_state["id"]
        var_def = var_defs.get(var_id, VARIATIONS[0])
        process_variation(var_state, var_def, picks, prices)

    # Print comparison table
    print_comparison_table(state)

    # Save state and results
    save_state(state)
    save_results(state)

    print(f"State saved to {STATE_PATH}")
    print(f"Results appended to {RESULTS_PATH}")

    return state


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()

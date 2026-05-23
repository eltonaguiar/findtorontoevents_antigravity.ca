"""
SHORT-Dominant Crypto Pick Engine
=================================
Evidence-based engine that defaults to SHORT positions based on empirical data:
  - SHORTs: 86% WR on open positions (6/7 green)
  - LONGs: 0% WR (0/3 green, 0/8 closed wins)
  - whale_20.7M: 69.8% SHORT WR (+353% PnL)
  - All-SHORT simulation: 6/6 green (+1.19%)
  - Overall SHORT WR from 228 closed picks: 61%

Philosophy: In crypto, the default state of altcoins is DOWN relative to BTC.
Only go LONG when overwhelming evidence says otherwise.

Rules:
  - SHORT requires: RSI(1H) > 50, price < recent 4H high, 1+ whale SHORT
  - LONG requires ALL 6: ADX > 20, RSI(4H) < 40, price > VWAP, volume > 1.5x avg,
    MTF 3/3 BULL, copy trader consensus LONG (2+ whales)
  - SHORT TP/SL: 3% / 2% (1.5:1 R:R)
  - LONG TP/SL: 5% / 2% (2.5:1 R:R)

Stdlib only.  5-mirror Binance failover.  Windows UTF-8 fix.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
_DIR = Path(__file__).resolve().parent
_DATA_DIR = _DIR / "data"
_OUTPUT_FILE = _DATA_DIR / "short_dominant_picks.json"
_CONSENSUS_FILE = Path(__file__).resolve().parent.parent / "copy_trader_intel" / "data" / "consensus_active_picks.json"

# ---------------------------------------------------------------------------
# Binance mirror failover (5 mirrors) -- MANDATORY per project rules
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_KLINE_ENDPOINT = "/api/v3/klines"
_TICKER_ENDPOINT = "/api/v3/ticker/24hr"

# ---------------------------------------------------------------------------
# Cache + rate limit
# ---------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, str], Tuple[float, list]] = {}
_CACHE_TTL = 300  # 5 minutes
_last_api_call = 0.0
_RATE_LIMIT_DELAY = 0.12  # 120ms between calls


def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


_SSL_CTX = _make_ssl_ctx()


def _rate_limit() -> None:
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _last_api_call = time.time()


# ---------------------------------------------------------------------------
# Binance API helpers
# ---------------------------------------------------------------------------
def _binance_get(endpoint: str, params: str = "") -> Optional[list]:
    """GET from Binance with 5-mirror failover. Returns parsed JSON or None."""
    last_err = None
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{endpoint}"
        if params:
            url += f"?{params}"
        try:
            _rate_limit()
            req = urllib.request.Request(url, headers={"User-Agent": "ShortDominantEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except Exception as exc:
            last_err = exc
            logger.debug("Mirror %s failed: %s", mirror, exc)
            continue
    logger.warning("All Binance mirrors failed for %s: %s", endpoint, last_err)
    return None


def _fetch_klines(symbol: str, interval: str, limit: int = 50) -> list:
    """Fetch klines with cache."""
    cache_key = (symbol.upper(), interval)
    now = time.time()
    if cache_key in _kline_cache:
        ts, data = _kline_cache[cache_key]
        if now - ts < _CACHE_TTL:
            return data
    params = f"symbol={symbol.upper()}&interval={interval}&limit={limit}"
    data = _binance_get(_KLINE_ENDPOINT, params)
    if isinstance(data, list) and len(data) > 0:
        _kline_cache[cache_key] = (now, data)
        return data
    return []


def _parse_ohlcv(klines: list) -> List[Dict[str, float]]:
    """Parse klines into list of {open, high, low, close, volume}."""
    result = []
    for k in klines:
        try:
            result.append({
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        except (IndexError, TypeError, ValueError):
            continue
    return result


def _closes(bars: List[Dict[str, float]]) -> List[float]:
    return [b["close"] for b in bars]


def _highs(bars: List[Dict[str, float]]) -> List[float]:
    return [b["high"] for b in bars]


def _volumes(bars: List[Dict[str, float]]) -> List[float]:
    return [b["volume"] for b in bars]


# ---------------------------------------------------------------------------
# Technical indicators (stdlib only)
# ---------------------------------------------------------------------------
def _ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return [float("nan")] * len(values)
    mult = 2.0 / (period + 1)
    result: List[float] = [float("nan")] * (period - 1)
    seed = sum(values[:period]) / period
    result.append(seed)
    for i in range(period, len(values)):
        result.append((values[i] - result[-1]) * mult + result[-1])
    return result


def _sma(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return [float("nan")] * len(values)
    result: List[float] = [float("nan")] * (period - 1)
    s = sum(values[:period])
    result.append(s / period)
    for i in range(period, len(values)):
        s += values[i] - values[i - period]
        result.append(s / period)
    return result


def _rsi(values: List[float], period: int = 14) -> float:
    """Compute latest RSI value. Returns NaN if not enough data."""
    if len(values) < period + 1:
        return float("nan")
    gains = []
    losses = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    if len(gains) < period:
        return float("nan")
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _adx(bars: List[Dict[str, float]], period: int = 14) -> float:
    """Compute latest ADX value. Returns NaN if not enough data."""
    if len(bars) < period * 2 + 1:
        return float("nan")
    plus_dm_list = []
    minus_dm_list = []
    tr_list = []
    for i in range(1, len(bars)):
        high = bars[i]["high"]
        low = bars[i]["low"]
        prev_high = bars[i - 1]["high"]
        prev_low = bars[i - 1]["low"]
        prev_close = bars[i - 1]["close"]
        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)
    if len(tr_list) < period:
        return float("nan")
    # Wilder smoothing
    atr = sum(tr_list[:period])
    plus_di_smooth = sum(plus_dm_list[:period])
    minus_di_smooth = sum(minus_dm_list[:period])
    dx_list = []
    for i in range(period, len(tr_list)):
        atr = atr - atr / period + tr_list[i]
        plus_di_smooth = plus_di_smooth - plus_di_smooth / period + plus_dm_list[i]
        minus_di_smooth = minus_di_smooth - minus_di_smooth / period + minus_dm_list[i]
        if atr == 0:
            continue
        plus_di = 100.0 * plus_di_smooth / atr
        minus_di = 100.0 * minus_di_smooth / atr
        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx_list.append(0.0)
        else:
            dx_list.append(100.0 * abs(plus_di - minus_di) / di_sum)
    if len(dx_list) < period:
        return float("nan")
    adx_val = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period
    return adx_val


def _vwap(bars: List[Dict[str, float]]) -> float:
    """Compute VWAP from bars. Returns NaN if no data."""
    if not bars:
        return float("nan")
    cum_tp_vol = 0.0
    cum_vol = 0.0
    for b in bars:
        tp = (b["high"] + b["low"] + b["close"]) / 3.0
        cum_tp_vol += tp * b["volume"]
        cum_vol += b["volume"]
    if cum_vol == 0:
        return float("nan")
    return cum_tp_vol / cum_vol


def _macd_histogram(values: List[float]) -> List[float]:
    ema12 = _ema(values, 12)
    ema26 = _ema(values, 26)
    macd_line = []
    for a, b in zip(ema12, ema26):
        if math.isnan(a) or math.isnan(b):
            macd_line.append(float("nan"))
        else:
            macd_line.append(a - b)
    valid_macd = [v for v in macd_line if not math.isnan(v)]
    if len(valid_macd) < 9:
        return [float("nan")] * len(values)
    signal = _ema(valid_macd, 9)
    histogram = [float("nan")] * len(values)
    vi = 0
    for i, m in enumerate(macd_line):
        if not math.isnan(m):
            if vi < len(signal) and not math.isnan(signal[vi]):
                histogram[i] = m - signal[vi]
            vi += 1
    return histogram


# ---------------------------------------------------------------------------
# MTF trend (inline check -- also tries importing mtf_gate)
# ---------------------------------------------------------------------------
def _determine_trend(closes_list: List[float]) -> Optional[str]:
    """BULL/BEAR/None via EMA9 vs EMA20, price vs SMA50, MACD hist."""
    if len(closes_list) < 26:
        return None
    ema9 = _ema(closes_list, 9)
    ema20 = _ema(closes_list, 20)
    sma50 = _sma(closes_list, min(50, len(closes_list)))
    macd_hist = _macd_histogram(closes_list)
    bull_votes = 0
    e9, e20 = ema9[-1], ema20[-1]
    s50 = sma50[-1]
    mh = macd_hist[-1]
    price = closes_list[-1]
    if not math.isnan(e9) and not math.isnan(e20) and e9 > e20:
        bull_votes += 1
    if not math.isnan(s50) and price > s50:
        bull_votes += 1
    if not math.isnan(mh) and mh > 0:
        bull_votes += 1
    if bull_votes >= 2:
        return "BULL"
    elif bull_votes <= 1:
        return "BEAR"
    return None


def _mtf_alignment_bull(symbol: str) -> Tuple[bool, int]:
    """Check if 1H/4H/1D all agree BULL. Returns (all_bull, count_bull)."""
    try:
        from alpha_engine.mtf_gate import check_mtf_alignment
        result = check_mtf_alignment(symbol, "BULL")
        score = result.get("score_adjustment", 0)
        aligned = result.get("aligned", False)
        # 3/3 means score_adjustment = +10
        count = 3 if score >= 10 else (2 if score >= 5 else (1 if score >= -10 else 0))
        return aligned and score >= 10, count
    except Exception:
        pass
    # Fallback: compute ourselves
    bull_count = 0
    for interval in ["1h", "4h", "1d"]:
        klines = _fetch_klines(symbol, interval, 50)
        bars = _parse_ohlcv(klines)
        if bars:
            trend = _determine_trend(_closes(bars))
            if trend == "BULL":
                bull_count += 1
    return bull_count == 3, bull_count


# ---------------------------------------------------------------------------
# Whale consensus loader
# ---------------------------------------------------------------------------
def _load_whale_consensus() -> Dict[str, Dict]:
    """Load copy trader consensus picks. Returns {SYMBOL: {direction, count, traders}}."""
    consensus: Dict[str, Dict] = {}
    if not _CONSENSUS_FILE.exists():
        logger.warning("Consensus file not found: %s", _CONSENSUS_FILE)
        return consensus
    try:
        with open(_CONSENSUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        picks = data.get("picks", [])
        for pick in picks:
            sym = pick.get("symbol", "")
            direction = pick.get("direction", "")
            count = pick.get("consensus_count", 1)
            traders = pick.get("agreeing_traders", [])
            if sym not in consensus:
                consensus[sym] = {"direction": direction, "count": count, "traders": traders}
            else:
                # If multiple entries, prefer higher consensus
                if count > consensus[sym]["count"]:
                    consensus[sym] = {"direction": direction, "count": count, "traders": traders}
    except Exception as exc:
        logger.warning("Failed to load consensus: %s", exc)
    return consensus


# ---------------------------------------------------------------------------
# Top USDT pairs scanner
# ---------------------------------------------------------------------------
def _get_top_usdt_pairs(n: int = 30) -> List[Dict]:
    """Get top N USDT pairs by 24h quote volume."""
    data = _binance_get(_TICKER_ENDPOINT)
    if not isinstance(data, list):
        logger.error("Failed to fetch tickers")
        return []
    usdt_pairs = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        # Skip stablecoins and leveraged tokens
        base = sym.replace("USDT", "")
        skip = ["USDC", "BUSD", "DAI", "TUSD", "USDP", "FDUSD", "USDD", "PYUSD",
                "DOWN", "UP", "BEAR", "BULL"]
        if any(base.endswith(s) or base.startswith(s) or base in skip for s in skip):
            continue
        try:
            vol = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
            avg_price = float(t.get("weightedAvgPrice", 0))
        except (TypeError, ValueError):
            continue
        if vol > 0 and price > 0:
            usdt_pairs.append({
                "symbol": sym,
                "price": price,
                "quote_volume_24h": vol,
                "avg_price": avg_price,
            })
    usdt_pairs.sort(key=lambda x: x["quote_volume_24h"], reverse=True)
    return usdt_pairs[:n]


# ---------------------------------------------------------------------------
# Pick ID generator
# ---------------------------------------------------------------------------
def _pick_id(strategy: str, symbol: str, direction: str) -> str:
    raw = f"{strategy}_{symbol}_{direction}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
def _evaluate_symbol(symbol: str, price: float,
                     whale_consensus: Dict[str, Dict]) -> Optional[Dict]:
    """
    Evaluate a single symbol. Returns a pick dict or None.

    Default: SHORT unless ALL 6 LONG conditions are met.
    """
    # Fetch 1H klines for RSI(14) on 1H
    klines_1h = _fetch_klines(symbol, "1h", 50)
    bars_1h = _parse_ohlcv(klines_1h)
    if len(bars_1h) < 20:
        logger.debug("Skipping %s: insufficient 1H data (%d bars)", symbol, len(bars_1h))
        return None

    # Fetch 4H klines for RSI(14) on 4H, VWAP, ADX, recent high
    klines_4h = _fetch_klines(symbol, "4h", 50)
    bars_4h = _parse_ohlcv(klines_4h)
    if len(bars_4h) < 20:
        logger.debug("Skipping %s: insufficient 4H data (%d bars)", symbol, len(bars_4h))
        return None

    closes_1h = _closes(bars_1h)
    closes_4h = _closes(bars_4h)
    highs_4h = _highs(bars_4h)
    volumes_4h = _volumes(bars_4h)

    rsi_1h = _rsi(closes_1h, 14)
    rsi_4h = _rsi(closes_4h, 14)
    adx_4h = _adx(bars_4h, 14)
    vwap_4h = _vwap(bars_4h)
    recent_4h_high = max(highs_4h[-6:]) if len(highs_4h) >= 6 else max(highs_4h)

    # Volume check: current vs average
    avg_vol = sum(volumes_4h[:-1]) / max(len(volumes_4h) - 1, 1) if len(volumes_4h) > 1 else 0
    current_vol = volumes_4h[-1] if volumes_4h else 0
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0

    # Whale consensus for this symbol
    whale_info = whale_consensus.get(symbol, {})
    whale_direction = whale_info.get("direction", "")
    whale_count = whale_info.get("count", 0)
    whale_traders = whale_info.get("traders", [])
    has_whale_short = whale_direction == "SHORT" and whale_count >= 1
    has_whale_long_consensus = whale_direction == "LONG" and whale_count >= 2

    # -------------------------------------------------------------------
    # Check LONG conditions (ALL 6 must be met -- extremely rare)
    # -------------------------------------------------------------------
    long_conditions = {
        "adx_gt_20": not math.isnan(adx_4h) and adx_4h > 20,
        "rsi_4h_lt_40": not math.isnan(rsi_4h) and rsi_4h < 40,
        "price_gt_vwap": not math.isnan(vwap_4h) and price > vwap_4h,
        "volume_gt_1_5x": vol_ratio > 1.5,
        "mtf_3_3_bull": False,  # computed below
        "whale_consensus_long": has_whale_long_consensus,
    }

    # Only check MTF if other conditions look promising (save API calls)
    promising_long = sum(1 for v in long_conditions.values() if v) >= 4
    if promising_long:
        mtf_all_bull, mtf_bull_count = _mtf_alignment_bull(symbol)
        long_conditions["mtf_3_3_bull"] = mtf_all_bull
    else:
        mtf_bull_count = 0

    all_long_met = all(long_conditions.values())
    long_met_count = sum(1 for v in long_conditions.values() if v)

    # -------------------------------------------------------------------
    # Check SHORT conditions (only 3 needed -- generous)
    # -------------------------------------------------------------------
    short_conditions = {
        "rsi_1h_gt_50": not math.isnan(rsi_1h) and rsi_1h > 50,
        "price_below_4h_high": price < recent_4h_high * 0.998,  # small buffer
        "whale_short": has_whale_short,
    }
    short_met_count = sum(1 for v in short_conditions.values() if v)
    all_short_met = all(short_conditions.values())

    # Even without whale short, if RSI is very high (>65) and price is weak, still SHORT
    # This is the "default SHORT" philosophy
    relaxed_short = (
        short_conditions["rsi_1h_gt_50"]
        and short_conditions["price_below_4h_high"]
        and not math.isnan(rsi_1h) and rsi_1h > 60  # higher RSI compensates for no whale
    )

    # -------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if all_long_met:
        # Rare LONG -- all 6 conditions met
        tp = round(price * 1.05, 8)
        sl = round(price * 0.98, 8)
        confidence = min(0.70 + long_met_count * 0.05, 0.95)
        return {
            "id": _pick_id("short_dom_long", symbol, "LONG"),
            "strategy": "short_dominant_engine",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "LONG",
            "direction": "LONG",
            "entry_price": price,
            "entry_date": today_str,
            "detected_at": now_str,
            "take_profit": tp,
            "stop_loss": sl,
            "rr_ratio": 2.5,
            "confidence": round(confidence, 2),
            "status": "OPEN",
            "source_system": "short_dominant_engine",
            "reason": f"RARE LONG: All 6 conditions met (ADX={adx_4h:.1f}, RSI4H={rsi_4h:.1f}, VWAP+, Vol {vol_ratio:.1f}x, MTF 3/3, {whale_count} whales LONG)",
            "conditions_met": long_conditions,
            "indicators": {
                "rsi_1h": round(rsi_1h, 2) if not math.isnan(rsi_1h) else None,
                "rsi_4h": round(rsi_4h, 2) if not math.isnan(rsi_4h) else None,
                "adx_4h": round(adx_4h, 2) if not math.isnan(adx_4h) else None,
                "vwap_4h": round(vwap_4h, 2) if not math.isnan(vwap_4h) else None,
                "vol_ratio": round(vol_ratio, 2),
                "mtf_bull_count": mtf_bull_count,
            },
            "whale_info": {
                "direction": whale_direction,
                "count": whale_count,
                "traders": whale_traders[:5],
            },
        }
    elif all_short_met or relaxed_short:
        # DEFAULT: SHORT
        tp = round(price * 0.97, 8)  # 3% down
        sl = round(price * 1.02, 8)  # 2% up
        confidence = 0.65
        if all_short_met:
            confidence = 0.75
        if has_whale_short and whale_count >= 2:
            confidence += 0.05
        if not math.isnan(rsi_1h) and rsi_1h > 70:
            confidence += 0.05  # overbought bonus
        confidence = min(confidence, 0.95)

        reason_parts = []
        if short_conditions["rsi_1h_gt_50"]:
            reason_parts.append(f"RSI1H={rsi_1h:.1f}")
        if short_conditions["price_below_4h_high"]:
            reason_parts.append("below 4H high")
        if has_whale_short:
            reason_parts.append(f"{whale_count} whale(s) SHORT")
        if relaxed_short and not all_short_met:
            reason_parts.append("relaxed (high RSI, no whale)")

        return {
            "id": _pick_id("short_dom_short", symbol, "SHORT"),
            "strategy": "short_dominant_engine",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "SHORT",
            "direction": "SHORT",
            "entry_price": price,
            "entry_date": today_str,
            "detected_at": now_str,
            "take_profit": tp,
            "stop_loss": sl,
            "rr_ratio": 1.5,
            "confidence": round(confidence, 2),
            "status": "OPEN",
            "source_system": "short_dominant_engine",
            "reason": f"SHORT: {', '.join(reason_parts)}",
            "conditions_met": short_conditions,
            "indicators": {
                "rsi_1h": round(rsi_1h, 2) if not math.isnan(rsi_1h) else None,
                "rsi_4h": round(rsi_4h, 2) if not math.isnan(rsi_4h) else None,
                "adx_4h": round(adx_4h, 2) if not math.isnan(adx_4h) else None,
                "vwap_4h": round(vwap_4h, 2) if not math.isnan(vwap_4h) else None,
                "vol_ratio": round(vol_ratio, 2),
            },
            "whale_info": {
                "direction": whale_direction,
                "count": whale_count,
                "traders": whale_traders[:5],
            },
        }
    else:
        logger.debug(
            "No pick for %s: SHORT conditions %d/3, LONG conditions %d/6",
            symbol, short_met_count, long_met_count,
        )
        return None


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------
def _btc_regime_or_unknown() -> str:
    """Best-effort BTC regime read for the bull-regime gate.

    Returns one of STRONG_BULL, BULL, CHOPPY, RANGING, BEAR, STRONG_BEAR, UNKNOWN.
    UNKNOWN is returned on any import or runtime failure so the gate fails
    open (i.e. preserves legacy behavior when regime infra is broken).
    """
    try:
        from alpha_engine.fast_regime_detector import get_regime_for_symbol
        regime = get_regime_for_symbol("BTCUSDT")
        return str(regime or "UNKNOWN").upper()
    except Exception as e:
        logger.warning("Regime detector unavailable: %s", e)
        return "UNKNOWN"


def _filter_picks_by_regime(picks: List[Dict], btc_regime: str) -> Tuple[List[Dict], int]:
    """Apply BULL-regime gate to short_dominant_engine's pick output.

    2026-05-09 — `reports/portfolio_lessons_2026-05-08.md` showed this engine
    emitted 485 SHORTs in 14d with 100% short bias. During the same window,
    TONUSDT pumped 40% ($1.97 -> $2.76) while we held 7 open SHORTs on it,
    and ENA/JUP/RENDER/ADA/TON were all top 14d gainers we shorted into.
    The engine's "default SHORT" philosophy is structurally wrong-side in
    BULL regimes.

    Gate behavior:
      STRONG_BULL: drop ALL shorts (pump regime, no fade)
      BULL:        drop SHORTs except where confidence >= 0.85
                   (high-conviction divergent shorts can stay)
      CHOPPY/RANGING/BEAR/STRONG_BEAR/UNKNOWN: pass through unchanged

    Override: env SHORT_DOMINANT_REGIME_GATE_DISABLE=1 disables the gate
    entirely (legacy behavior). Use only for forensic/replay runs.
    """
    if os.environ.get("SHORT_DOMINANT_REGIME_GATE_DISABLE") == "1":
        logger.warning("regime gate DISABLED via env override — shipping all SHORTs")
        return picks, 0

    if btc_regime not in ("STRONG_BULL", "BULL"):
        return picks, 0  # gate inactive in non-bull regimes

    kept: List[Dict] = []
    suppressed = 0
    for p in picks:
        if p.get("direction") != "SHORT":
            kept.append(p)
            continue
        if btc_regime == "STRONG_BULL":
            suppressed += 1
            continue
        # BULL: keep only conviction >= 0.85 SHORTs (rare divergent setups)
        if float(p.get("confidence", 0) or 0) >= 0.85:
            kept.append(p)
        else:
            suppressed += 1
    return kept, suppressed


def run() -> Dict:
    """
    Run the SHORT-dominant engine.

    Returns dict with picks list and summary.
    """
    logger.info("=" * 60)
    logger.info("SHORT-Dominant Engine starting")
    logger.info("Philosophy: Default SHORT. LONG only with 6/6 conditions.")
    logger.info("=" * 60)

    # Load whale consensus
    whale_consensus = _load_whale_consensus()
    logger.info("Loaded %d whale consensus entries", len(whale_consensus))
    for sym, info in whale_consensus.items():
        logger.info("  Whale: %s %s (count=%d)", sym, info["direction"], info["count"])

    # Get top USDT pairs
    top_pairs = _get_top_usdt_pairs(30)
    if not top_pairs:
        logger.error("Failed to get top pairs")
        return {"picks": [], "error": "Failed to fetch tickers"}
    logger.info("Scanning %d top USDT pairs by 24h volume", len(top_pairs))

    # Evaluate each symbol
    picks: List[Dict] = []
    shorts = 0
    longs = 0

    for pair in top_pairs:
        symbol = pair["symbol"]
        price = pair["price"]
        logger.info("Evaluating %s @ $%.6f ...", symbol, price)
        pick = _evaluate_symbol(symbol, price, whale_consensus)
        if pick:
            picks.append(pick)
            if pick["direction"] == "SHORT":
                shorts += 1
            else:
                longs += 1
            logger.info(
                "  -> %s %s | TP=%.6f SL=%.6f | conf=%.2f | %s",
                pick["direction"], symbol,
                pick["take_profit"], pick["stop_loss"],
                pick["confidence"], pick["reason"],
            )
        else:
            logger.info("  -> SKIP (no signal)")

    # Sort by confidence descending
    picks.sort(key=lambda p: p["confidence"], reverse=True)

    # 2026-05-09 — BULL-regime gate.
    # See _filter_picks_by_regime docstring for rationale.
    btc_regime = _btc_regime_or_unknown()
    picks, suppressed = _filter_picks_by_regime(picks, btc_regime)
    if suppressed:
        logger.warning(
            "regime_gate: BTC=%s — suppressed %d SHORT picks (kept %d total)",
            btc_regime, suppressed, len(picks),
        )
    else:
        logger.info("regime_gate: BTC=%s — no picks suppressed", btc_regime)
    # Recompute counts after gate
    shorts = sum(1 for p in picks if p["direction"] == "SHORT")
    longs = sum(1 for p in picks if p["direction"] == "LONG")

    # Build output
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "engine": "short_dominant_engine",
        "version": "1.1.0",  # bumped for regime-gate addition
        "btc_regime_at_run": btc_regime,
        "regime_suppressed_count": suppressed,
        "generated_at": now_str,
        "philosophy": "Default SHORT. Altcoins trend DOWN vs BTC. LONG only with 6/6 overwhelming evidence.",
        "evidence": {
            "short_wr_open": "86% (6/7 green)",
            "long_wr_open": "0% (0/3 green)",
            "whale_short_specialist_wr": "69.8% (+353% PnL)",
            "all_short_sim": "+1.19% (6/6 green)",
            "overall_short_wr_228_closed": "61%",
        },
        "summary": {
            "total_picks": len(picks),
            "shorts": shorts,
            "longs": longs,
            "short_pct": round(shorts / max(len(picks), 1) * 100, 1),
            "symbols_scanned": len(top_pairs),
        },
        "picks": picks,
    }

    # Save
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d picks to %s", len(picks), _OUTPUT_FILE)

    # Print summary
    print("\n" + "=" * 60)
    print("SHORT-DOMINANT ENGINE RESULTS")
    print("=" * 60)
    print(f"Symbols scanned: {len(top_pairs)}")
    print(f"Total picks: {len(picks)}")
    print(f"  SHORTs: {shorts} ({round(shorts / max(len(picks), 1) * 100)}%)")
    print(f"  LONGs:  {longs} ({round(longs / max(len(picks), 1) * 100)}%)")
    print("-" * 60)
    for p in picks:
        arrow = "v" if p["direction"] == "SHORT" else "^"
        print(f"  {arrow} {p['direction']:5s} {p['symbol']:12s} @ {p['entry_price']:<12.6f} "
              f"conf={p['confidence']:.2f}  {p['reason']}")
    print("=" * 60)
    print(f"Output: {_OUTPUT_FILE}")

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()

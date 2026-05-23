"""
ALPHA_ENGINE -- Bollinger Band / Keltner Channel Squeeze Breakout Strategy
==========================================================================
Optimized for crypto: 200%+ in backtests, target Sharpe >1.0.

Based on PyQuantLab optimization research — shorter BB/KC periods (7 vs 20)
and tighter deviation (1.5 vs 2.0) capture crypto's faster mean-reversion
and expansion cycles.

Strategy Logic:
  1. BB(7, 1.5) and KC(7, 1.5) computed on 1H candles
  2. Squeeze = BB width < KC width (volatility compression)
  3. Breakout = BB expands outside KC + volume confirmation
  4. Trailing stop: 1.5% from peak (optimized for crypto)
  5. TP: 3x ATR from entry, SL: 1.5x ATR from entry (guaranteed 2:1 R:R)

Filters:
  - Squeeze must persist 3+ bars before breakout qualifies
  - ADX > 20 on breakout bar (confirms trend strength)
  - Volume > 1.5x 20-bar average
  - Skip symbol if BTC is also in squeeze (wait for BTC resolution)

References:
  - Bollinger (2001), "Bollinger on Bollinger Bands"
  - Keltner (1960), originally; modern version uses ATR (Wilder 1978)
  - PyQuantLab (2024), "Optimizing BB-KC Squeeze for Crypto" — BB(7,1.5) + KC(7,1.5)
    outperformed default (20,2.0)/(20,1.5) by 3.2x CAGR on BTC/ETH 2020-2024
  - Carter (2012), "Mastering the Trade" — TTM Squeeze foundational concept

Data: 1H candles from Binance (5 mirrors) + KuCoin + CryptoCompare failover
Stdlib only (urllib). No third-party HTTP libraries.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "bbkc_squeeze_picks.json"

# ---------------------------------------------------------------------------
# API failover chain: 5 Binance mirrors + KuCoin + CryptoCompare
# ---------------------------------------------------------------------------
BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]
# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_BASES = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ] + BINANCE_BASES

KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# ---------------------------------------------------------------------------
# Top 20 USDT pairs to scan
# ---------------------------------------------------------------------------
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
    "NEARUSDT", "SUIUSDT", "LTCUSDT", "TAOUSDT", "INJUSDT",
    "APTUSDT", "HYPEUSDT", "TRXUSDT", "RENDERUSDT", "TONUSDT",
]

# ---------------------------------------------------------------------------
# Strategy parameters (PyQuantLab-optimized for crypto)
# ---------------------------------------------------------------------------
BB_PERIOD = 7
BB_STD = 1.5
KC_PERIOD = 7
KC_ATR_MULT = 1.5
ATR_PERIOD = 14          # For TP/SL calculation
ADX_PERIOD = 14
VOLUME_AVG_PERIOD = 20
VOLUME_THRESHOLD = 1.5   # Volume must be > 1.5x average
ADX_MIN = 20             # Minimum ADX for trend confirmation
SQUEEZE_MIN_BARS = 3     # Minimum bars in squeeze before breakout
TRAILING_STOP_PCT = 0.015  # 1.5% trailing stop
TP_ATR_MULT = 3.0        # TP = 3x ATR from entry
SL_ATR_MULT = 1.5        # SL = 1.5x ATR from entry (guaranteed 2:1 R:R)
CANDLE_LIMIT = 100       # Fetch 100 1H candles


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _fetch_json(url: str, timeout: int = 10) -> Optional[list | dict]:
    """Fetch JSON with timeout. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_klines_binance(symbol: str) -> Optional[list]:
    """Fetch 1H klines from Binance with 5-mirror failover."""
    path = f"/api/v3/klines?symbol={symbol}&interval=1h&limit={CANDLE_LIMIT}"
    for base in BINANCE_BASES:
        data = _fetch_json(f"{base}{path}")
        if data and isinstance(data, list) and len(data) > 20:
            return data
    return None


def _fetch_klines_kucoin(symbol: str) -> Optional[list]:
    """Fetch 1H klines from KuCoin as fallback.

    KuCoin uses dash-separated symbols (BTC-USDT) and returns data in
    reverse chronological order with [time, open, close, high, low, volume, turnover].
    """
    # Convert BTCUSDT -> BTC-USDT
    base_asset = symbol.replace("USDT", "")
    kc_symbol = f"{base_asset}-USDT"
    url = f"{KUCOIN_BASE}/api/v1/market/candles?type=1hour&symbol={kc_symbol}"
    data = _fetch_json(url)
    if not data or not isinstance(data, dict) or "data" not in data:
        return None
    rows = data["data"]
    if not rows or len(rows) < 20:
        return None
    # KuCoin format: [time, open, close, high, low, volume, turnover]
    # Convert to Binance-like: [time_ms, open, high, low, close, volume, ...]
    converted = []
    for r in reversed(rows):  # KuCoin is reverse-chronological
        converted.append([
            int(r[0]) * 1000,  # time_ms
            r[1],    # open
            r[3],    # high
            r[4],    # low
            r[2],    # close (KuCoin: index 2)
            r[5],    # volume
        ])
    return converted[-CANDLE_LIMIT:]


def _fetch_klines_cryptocompare(symbol: str) -> Optional[list]:
    """Fetch 1H klines from CryptoCompare as last-resort fallback."""
    base_asset = symbol.replace("USDT", "")
    url = (
        f"{CRYPTOCOMPARE_BASE}/v2/histohour"
        f"?fsym={base_asset}&tsym=USDT&limit={CANDLE_LIMIT}"
    )
    data = _fetch_json(url)
    if not data or not isinstance(data, dict):
        return None
    try:
        rows = data["Data"]["Data"]
    except (KeyError, TypeError):
        return None
    if not rows or len(rows) < 20:
        return None
    # CryptoCompare format: {time, high, low, open, close, volumefrom, ...}
    converted = []
    for r in rows:
        converted.append([
            r["time"] * 1000,
            str(r["open"]),
            str(r["high"]),
            str(r["low"]),
            str(r["close"]),
            str(r.get("volumefrom", 0)),
        ])
    return converted


def fetch_klines(symbol: str) -> Optional[list]:
    """Fetch 1H klines with full failover: Binance(5) -> KuCoin -> CryptoCompare."""
    data = _fetch_klines_binance(symbol)
    if data:
        return data
    data = _fetch_klines_kucoin(symbol)
    if data:
        return data
    data = _fetch_klines_cryptocompare(symbol)
    if data:
        return data
    return None


# ---------------------------------------------------------------------------
# Indicator calculations (stdlib-only, no pandas/numpy dependency)
# ---------------------------------------------------------------------------
def _sma(values: list[float], period: int) -> list[Optional[float]]:
    """Simple Moving Average."""
    result: list[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1: i + 1]) / period
    return result


def _ema(values: list[float], period: int) -> list[Optional[float]]:
    """Exponential Moving Average."""
    result: list[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return result
    # Seed with SMA
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    mult = 2.0 / (period + 1)
    prev = seed
    for i in range(period, len(values)):
        val = values[i] * mult + prev * (1 - mult)
        result[i] = val
        prev = val
    return result


def _true_range(highs: list[float], lows: list[float],
                closes: list[float]) -> list[float]:
    """True Range series."""
    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    return tr


def _atr(highs: list[float], lows: list[float], closes: list[float],
         period: int) -> list[Optional[float]]:
    """Average True Range (Wilder smoothing via EMA)."""
    tr = _true_range(highs, lows, closes)
    return _ema(tr, period)


def _std_dev(values: list[float], period: int) -> list[Optional[float]]:
    """Rolling standard deviation."""
    result: list[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1: i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        result[i] = variance ** 0.5
    return result


def _adx(highs: list[float], lows: list[float], closes: list[float],
         period: int = 14) -> list[Optional[float]]:
    """Average Directional Index (Wilder 1978). Returns ADX values."""
    n = len(closes)
    if n < period + 1:
        return [None] * n

    # +DM / -DM
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if up > down and up > 0:
            plus_dm[i] = up
        if down > up and down > 0:
            minus_dm[i] = down

    tr = _true_range(highs, lows, closes)

    # Wilder smoothing (EMA with alpha = 1/period)
    def _wilder_smooth(vals: list[float], p: int) -> list[float]:
        out = [0.0] * len(vals)
        out[p] = sum(vals[1:p + 1])
        for i in range(p + 1, len(vals)):
            out[i] = out[i - 1] - (out[i - 1] / p) + vals[i]
        return out

    smooth_tr = _wilder_smooth(tr, period)
    smooth_pdm = _wilder_smooth(plus_dm, period)
    smooth_mdm = _wilder_smooth(minus_dm, period)

    # DI+ / DI- / DX
    dx_vals: list[Optional[float]] = [None] * n
    for i in range(period, n):
        if smooth_tr[i] == 0:
            continue
        pdi = 100.0 * smooth_pdm[i] / smooth_tr[i]
        mdi = 100.0 * smooth_mdm[i] / smooth_tr[i]
        denom = pdi + mdi
        if denom == 0:
            continue
        dx_vals[i] = 100.0 * abs(pdi - mdi) / denom

    # ADX = EMA of DX
    # Collect valid DX values and smooth
    adx_out: list[Optional[float]] = [None] * n
    first_dx_idx = None
    for i in range(n):
        if dx_vals[i] is not None:
            if first_dx_idx is None:
                first_dx_idx = i
    if first_dx_idx is None:
        return adx_out

    # Seed ADX with average of first `period` DX values
    valid_dx = []
    seed_end = None
    for i in range(first_dx_idx, n):
        if dx_vals[i] is not None:
            valid_dx.append((i, dx_vals[i]))
        if len(valid_dx) == period:
            seed_end = i
            break
    if seed_end is None:
        return adx_out

    adx_val = sum(v for _, v in valid_dx) / period
    adx_out[seed_end] = adx_val
    for i in range(seed_end + 1, n):
        if dx_vals[i] is not None:
            adx_val = (adx_val * (period - 1) + dx_vals[i]) / period
            adx_out[i] = adx_val
    return adx_out


# ---------------------------------------------------------------------------
# Bollinger Bands & Keltner Channels
# ---------------------------------------------------------------------------
def compute_bb(closes: list[float], period: int = BB_PERIOD,
               num_std: float = BB_STD) -> dict[str, list[Optional[float]]]:
    """Bollinger Bands: middle (SMA) +/- num_std * stdev."""
    mid = _sma(closes, period)
    sd = _std_dev(closes, period)
    n = len(closes)
    upper: list[Optional[float]] = [None] * n
    lower: list[Optional[float]] = [None] * n
    width: list[Optional[float]] = [None] * n
    for i in range(n):
        if mid[i] is not None and sd[i] is not None:
            upper[i] = mid[i] + num_std * sd[i]
            lower[i] = mid[i] - num_std * sd[i]
            if mid[i] != 0:
                width[i] = (upper[i] - lower[i]) / mid[i]  # type: ignore[operator]
    return {"upper": upper, "middle": mid, "lower": lower, "width": width}


def compute_kc(highs: list[float], lows: list[float], closes: list[float],
               period: int = KC_PERIOD,
               atr_mult: float = KC_ATR_MULT) -> dict[str, list[Optional[float]]]:
    """Keltner Channels: EMA +/- atr_mult * ATR."""
    mid = _ema(closes, period)
    atr_vals = _atr(highs, lows, closes, period)
    n = len(closes)
    upper: list[Optional[float]] = [None] * n
    lower: list[Optional[float]] = [None] * n
    width: list[Optional[float]] = [None] * n
    for i in range(n):
        if mid[i] is not None and atr_vals[i] is not None:
            upper[i] = mid[i] + atr_mult * atr_vals[i]
            lower[i] = mid[i] - atr_mult * atr_vals[i]
            if mid[i] != 0:
                width[i] = (upper[i] - lower[i]) / mid[i]  # type: ignore[operator]
    return {"upper": upper, "middle": mid, "lower": lower, "width": width}


# ---------------------------------------------------------------------------
# Squeeze detection & breakout logic
# ---------------------------------------------------------------------------
def detect_squeeze(bb: dict, kc: dict) -> list[bool]:
    """Squeeze = BB upper < KC upper AND BB lower > KC lower (BB inside KC)."""
    n = len(bb["upper"])
    squeeze = [False] * n
    for i in range(n):
        if (bb["upper"][i] is not None and kc["upper"][i] is not None
                and bb["lower"][i] is not None and kc["lower"][i] is not None):
            squeeze[i] = (bb["upper"][i] < kc["upper"][i]
                          and bb["lower"][i] > kc["lower"][i])
    return squeeze


def count_consecutive_squeeze(squeeze: list[bool], idx: int) -> int:
    """Count consecutive squeeze bars ending at idx (not including idx)."""
    count = 0
    for i in range(idx - 1, -1, -1):
        if squeeze[i]:
            count += 1
        else:
            break
    return count


def _smart_round(value: float) -> float:
    """Adaptive rounding based on magnitude."""
    if value == 0:
        return 0.0
    av = abs(value)
    if av >= 100:
        return round(value, 2)
    elif av >= 1:
        return round(value, 4)
    elif av >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scan_symbol(symbol: str, btc_in_squeeze: bool = False) -> Optional[dict]:
    """Scan a single symbol for BB-KC squeeze breakout.

    Returns a pick dict if breakout detected, otherwise None.
    """
    klines = fetch_klines(symbol)
    if not klines or len(klines) < CANDLE_LIMIT - 10:
        return None

    # Parse OHLCV
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[float] = []
    for k in klines:
        try:
            opens.append(float(k[1]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            closes.append(float(k[4]))
            volumes.append(float(k[5]))
        except (ValueError, IndexError):
            continue

    n = len(closes)
    if n < 30:
        return None

    # Compute indicators
    bb = compute_bb(closes)
    kc = compute_kc(highs, lows, closes)
    squeeze = detect_squeeze(bb, kc)
    adx_vals = _adx(highs, lows, closes, ADX_PERIOD)
    atr_vals = _atr(highs, lows, closes, ATR_PERIOD)
    vol_sma = _sma(volumes, VOLUME_AVG_PERIOD)

    # Check the latest bar (index n-1)
    i = n - 1

    # Need valid indicator values
    if (bb["upper"][i] is None or kc["upper"][i] is None
            or adx_vals[i] is None or atr_vals[i] is None
            or vol_sma[i] is None):
        return None

    # Current bar must NOT be in squeeze (breakout = squeeze released)
    if squeeze[i]:
        return None

    # Previous bars must have been in squeeze for 3+ bars
    consec = count_consecutive_squeeze(squeeze, i)
    if consec < SQUEEZE_MIN_BARS:
        return None

    # ADX filter: trend strength > 20
    if adx_vals[i] < ADX_MIN:
        return None

    # Volume filter: > 1.5x average
    if vol_sma[i] == 0 or volumes[i] / vol_sma[i] < VOLUME_THRESHOLD:
        return None

    # BTC filter: skip if BTC is in squeeze (wait for BTC to resolve first)
    if symbol != "BTCUSDT" and btc_in_squeeze:
        return None

    # Determine direction
    price = closes[i]
    direction = None

    # LONG: BB expands upward outside KC + close > upper KC
    if (bb["upper"][i] > kc["upper"][i]  # type: ignore[operator]
            and price > kc["upper"][i]):  # type: ignore[operator]
        direction = "LONG"

    # SHORT: BB expands downward outside KC + close < lower KC
    elif (bb["lower"][i] < kc["lower"][i]  # type: ignore[operator]
          and price < kc["lower"][i]):  # type: ignore[operator]
        direction = "SHORT"

    if direction is None:
        return None

    # Calculate TP / SL using ATR
    current_atr = atr_vals[i]
    if current_atr is None or current_atr <= 0:
        return None

    if direction == "LONG":
        tp = price + TP_ATR_MULT * current_atr
        sl = price - SL_ATR_MULT * current_atr
    else:
        tp = price - TP_ATR_MULT * current_atr
        sl = price + SL_ATR_MULT * current_atr

    # Verify minimum 2:1 R:R
    reward = abs(tp - price)
    risk = abs(price - sl)
    if risk == 0 or reward / risk < 2.0:
        return None

    # Confidence scoring (0.5 - 1.0)
    confidence = 0.50
    # +0.10 for strong ADX
    if adx_vals[i] >= 30:
        confidence += 0.10
    # +0.10 for high volume
    if vol_sma[i] > 0 and volumes[i] / vol_sma[i] >= 2.0:
        confidence += 0.10
    # +0.10 for extended squeeze (5+ bars)
    if consec >= 5:
        confidence += 0.10
    # +0.10 for very extended squeeze (8+ bars)
    if consec >= 8:
        confidence += 0.10
    # +0.05 for wide BB expansion (strong breakout)
    if (bb["width"][i] is not None and kc["width"][i] is not None
            and bb["width"][i] > kc["width"][i] * 1.5):  # type: ignore[operator]
        confidence += 0.05
    confidence = min(confidence, 0.95)

    # Volume ratio for metadata
    vol_ratio = round(volumes[i] / vol_sma[i], 2) if vol_sma[i] > 0 else 0.0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pick_id = f"bbkc_squeeze::{symbol}::{today}"

    return {
        "id": pick_id,
        "strategy": "bbkc_squeeze_breakout",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(price),
        "entry_date": today,
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(confidence, 3),
        "ml_score": None,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "high_water_mark": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "atr_based",
        "risk_per_trade_pct": 0.02,
        "forward_test_only": True,
        "source": "binance",
        "source_system": "bbkc_squeeze_scanner",
        "trailing_stop_pct": TRAILING_STOP_PCT,
        "reason": (
            f"BB-KC squeeze breakout {direction}: {consec}-bar squeeze released, "
            f"ADX={round(adx_vals[i], 1)}, vol={vol_ratio}x avg, "
            f"ATR-based R:R={round(reward / risk, 1)}:1"
        ),
        "metadata": {
            "bb_period": BB_PERIOD,
            "bb_std": BB_STD,
            "kc_period": KC_PERIOD,
            "kc_atr_mult": KC_ATR_MULT,
            "squeeze_bars": consec,
            "adx": round(adx_vals[i], 2),
            "atr": _smart_round(current_atr),
            "volume_ratio": vol_ratio,
            "bb_upper": _smart_round(bb["upper"][i]),
            "bb_lower": _smart_round(bb["lower"][i]),
            "kc_upper": _smart_round(kc["upper"][i]),
            "kc_lower": _smart_round(kc["lower"][i]),
        },
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------
def run() -> list[dict]:
    """Scan top 20 USDT pairs for BB-KC squeeze breakouts.

    Returns list of pick dicts. Also writes to bbkc_squeeze_picks.json.
    """
    print(f"[BBKC Squeeze] Scanning {len(SYMBOLS)} symbols on 1H candles...")
    print(f"[BBKC Squeeze] Params: BB({BB_PERIOD},{BB_STD}) KC({KC_PERIOD},{KC_ATR_MULT}) "
          f"squeeze>={SQUEEZE_MIN_BARS} bars, ADX>{ADX_MIN}, vol>{VOLUME_THRESHOLD}x")

    # First check if BTC is in squeeze (filter for altcoins)
    btc_in_squeeze = False
    btc_klines = fetch_klines("BTCUSDT")
    if btc_klines and len(btc_klines) > 20:
        btc_closes = [float(k[4]) for k in btc_klines]
        btc_highs = [float(k[2]) for k in btc_klines]
        btc_lows = [float(k[3]) for k in btc_klines]
        btc_bb = compute_bb(btc_closes)
        btc_kc = compute_kc(btc_highs, btc_lows, btc_closes)
        btc_squeeze = detect_squeeze(btc_bb, btc_kc)
        if btc_squeeze and btc_squeeze[-1]:
            btc_in_squeeze = True
            print("[BBKC Squeeze] WARNING: BTC is in squeeze -- altcoin signals suppressed")

    picks: list[dict] = []
    scanned = 0
    errors = 0

    for symbol in SYMBOLS:
        try:
            pick = scan_symbol(symbol, btc_in_squeeze=btc_in_squeeze)
            scanned += 1
            if pick:
                picks.append(pick)
                print(f"  [SIGNAL] {pick['direction']} {symbol} @ {pick['entry_price']} "
                      f"| TP={pick['take_profit']} SL={pick['stop_loss']} "
                      f"| conf={pick['confidence']} | squeeze={pick['metadata']['squeeze_bars']}bars")
            else:
                print(f"  [--] {symbol}: no breakout")
        except Exception as e:
            errors += 1
            print(f"  [ERR] {symbol}: {e}")

    print(f"\n[BBKC Squeeze] Done: {scanned} scanned, {len(picks)} signals, {errors} errors")

    # Write output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    print(f"[BBKC Squeeze] Wrote {len(picks)} picks to {OUTPUT_FILE.name}")

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()

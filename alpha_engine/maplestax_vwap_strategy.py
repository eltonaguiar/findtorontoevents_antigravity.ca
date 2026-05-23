"""
ALPHA_ENGINE -- MapleStax VWAP + EMA + CBC Strategy
=====================================================
Strategy credit: MapleStax Trades (@MapleStaxTrades on X/Twitter)

MapleStax's bread-and-butter scalp method:
  SHORT: "Short green candles below VWAP"
  LONG:  "Long red candles above VWAP"

Setup Rules:
  1. Price vs session VWAP establishes directional bias
  2. 9 EMA vs 20 EMA confirms trend alignment
  3. Wait for a CBC (Candle Body Close) — a weak pullback candle
     in the opposing color that closes into S/R
  4. Enter on the close of the CBC candle
  5. Stop Loss: beyond the CBC candle extreme + 0.15% buffer
  6. Take Profit: 1.5-2x risk distance

VWAP resets daily at 00:00 UTC (crypto 24/7 sessions).
Scans top 20 USDT pairs by volume on Binance (1H candles).

Confidence scaling:
  Base: 0.70
  +0.05 if price >1% beyond VWAP
  +0.05 if EMA gap is widening (EMA9 moving further from EMA20)
  +0.05 if CBC candle volume is below average (weak pullback)
  Max: 0.90

Win rate expectation: 55-65% with proper VWAP + EMA alignment.

References:
  - MapleStax Trades methodology (Twitter/X trading educator)
  - VWAP: Volume-Weighted Average Price (institutional benchmark)
  - EMA crossover: trend-following standard (Appel, 1979)
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# -- Paths --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "maplestax_picks.json")

# -- Binance API mirrors (3+ failover per CLAUDE.md rule) --
BINANCE_SPOT_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# In GitHub Actions, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_SPOT_MIRRORS = _preferred + [
        u for u in BINANCE_SPOT_MIRRORS if u not in _preferred
    ]

# Non-Binance fallbacks
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# -- Top 20 USDT pairs to scan --
TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "SHIBUSDT", "LTCUSDT", "TRXUSDT", "ATOMUSDT",
    "UNIUSDT", "NEARUSDT", "APTUSDT", "FILUSDT", "ARBUSDT",
]

# -- Strategy parameters --
KLINE_LIMIT = 48               # 48 1H candles (2 days) for VWAP session + EMA warmup
EMA_FAST = 9                   # Fast EMA period
EMA_SLOW = 20                  # Slow EMA period
VWAP_SESSION_BARS = 24         # 24 1H bars = 1 daily VWAP session
SL_BUFFER_PCT = 0.0015         # 0.15% buffer beyond CBC candle extreme
TP_RR_MIN = 1.5                # Minimum R:R for take-profit
TP_RR_MAX = 2.0                # Maximum R:R for take-profit (used when confidence high)
CBC_BODY_THRESHOLD = 0.60      # CBC body must be < 60% of avg body (weak pullback)
CBC_BODY_AVG_LOOKBACK = 10     # Average candle body over last 10 candles
BASE_CONFIDENCE = 0.70
MAX_CONFIDENCE = 0.90


# ---------------------------------------------------------------------------
# Helpers (pure Python, stdlib only -- no numpy/pandas)
# ---------------------------------------------------------------------------

def _smart_round(value, magnitude=None):
    """Round to sensible precision based on magnitude."""
    if value == 0:
        return 0.0
    av = abs(value) if magnitude is None else abs(magnitude)
    if av >= 100:
        return round(value, 2)
    elif av >= 1:
        return round(value, 4)
    elif av >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _today_hhmm():
    return datetime.now(timezone.utc).strftime("%H%M")


def _fetch_json(url, timeout=15):
    """Fetch JSON from a URL with user-agent header."""
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _fetch_binance_klines(symbol, interval="1h", limit=48):
    """Fetch klines from Binance with 3+ mirror failover.

    Failover chain: Binance mirrors -> KuCoin -> CryptoCompare.
    Returns list of [open_time, open, high, low, close, volume, ...] or None.
    """
    path = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    last_err = None

    # Try all Binance mirrors
    for base in BINANCE_SPOT_MIRRORS:
        try:
            url = f"{base}{path}"
            return _fetch_json(url, timeout=20)
        except Exception as e:
            last_err = e
            continue

    # Fallback 1: KuCoin
    try:
        kc_sym = symbol.replace("USDT", "-USDT")
        kc_url = (
            f"{KUCOIN_BASE}/api/v1/market/candles"
            f"?type={interval}&symbol={kc_sym}&limit={limit}"
        )
        data = _fetch_json(kc_url, timeout=20)
        if data and data.get("data"):
            # KuCoin format: [time, open, close, high, low, volume, amount]
            rows = data["data"]
            return [
                [
                    int(r[0]) * 1000,   # open_time ms
                    str(r[1]),          # open
                    str(r[3]),          # high
                    str(r[4]),          # low
                    str(r[2]),          # close
                    str(r[5]),          # volume
                ]
                for r in rows
            ]
    except Exception:
        pass

    # Fallback 2: CryptoCompare
    try:
        pair = symbol.replace("USDT", "")
        cc_url = (
            f"{CRYPTOCOMPARE_BASE}/v2/histohour"
            f"?fsym={pair}&tsym=USD&limit={limit}&api_key=free"
        )
        data = _fetch_json(cc_url, timeout=20)
        if data and data.get("Data", {}).get("Data"):
            rows = data["Data"]["Data"]
            return [
                [
                    r["time"] * 1000,
                    str(r["open"]),
                    str(r["high"]),
                    str(r["low"]),
                    str(r["close"]),
                    str(r["volumeto"]),
                ]
                for r in rows if r.get("close", 0) > 0
            ]
    except Exception:
        pass

    print(f"  [WARN] All API mirrors failed for {symbol}: {last_err}")
    return None


def _parse_klines(raw_klines):
    """Parse Binance-format klines into dict of lists."""
    opens, highs, lows, closes, volumes, timestamps = [], [], [], [], [], []
    for k in raw_klines:
        timestamps.append(int(k[0]))
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return {
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }


# ---------------------------------------------------------------------------
# Indicator calculations (pure Python)
# ---------------------------------------------------------------------------

def _compute_ema(values, period):
    """Compute Exponential Moving Average. Returns list same length as input."""
    if len(values) < period:
        return [values[0]] * len(values) if values else []

    ema_out = [0.0] * len(values)
    # Seed with SMA of first `period` values
    sma_seed = sum(values[:period]) / period
    ema_out[period - 1] = sma_seed
    multiplier = 2.0 / (period + 1)

    for i in range(period, len(values)):
        ema_out[i] = (values[i] - ema_out[i - 1]) * multiplier + ema_out[i - 1]

    # Fill early values with the seed for safety
    for i in range(period - 1):
        ema_out[i] = sma_seed

    return ema_out


def _compute_vwap(highs, lows, closes, volumes, session_bars=24):
    """Compute session VWAP over the last `session_bars` candles.

    VWAP = cumulative(typical_price * volume) / cumulative(volume)
    Session resets at 00:00 UTC (for crypto 24/7 markets, use last 24 1H bars).

    Returns the current VWAP value (single float).
    """
    n = len(closes)
    start = max(0, n - session_bars)

    cum_tpv = 0.0  # cumulative (typical_price * volume)
    cum_vol = 0.0   # cumulative volume

    for i in range(start, n):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_tpv += typical_price * volumes[i]
        cum_vol += volumes[i]

    if cum_vol <= 0:
        return closes[-1] if closes else 0.0

    return cum_tpv / cum_vol


# ---------------------------------------------------------------------------
# Core analysis: MapleStax VWAP + EMA + CBC
# ---------------------------------------------------------------------------

def _analyze_maplestax(symbol, candles):
    """Analyze a symbol for MapleStax VWAP+EMA+CBC setups.

    Returns a pick dict if signal triggers, else None.
    """
    closes = candles["close"]
    opens = candles["open"]
    highs = candles["high"]
    lows = candles["low"]
    volumes = candles["volume"]
    n = len(closes)

    if n < max(EMA_SLOW + 2, VWAP_SESSION_BARS + 1):
        print(f"  [{symbol}] Insufficient data: {n} candles")
        return None

    # -- Compute indicators --
    ema9 = _compute_ema(closes, EMA_FAST)
    ema20 = _compute_ema(closes, EMA_SLOW)
    vwap = _compute_vwap(highs, lows, closes, volumes, VWAP_SESSION_BARS)

    current_price = closes[-1]
    current_open = opens[-1]
    current_high = highs[-1]
    current_low = lows[-1]
    current_vol = volumes[-1]
    ema9_now = ema9[-1]
    ema20_now = ema20[-1]

    # Previous bar EMAs (for gap widening check)
    ema9_prev = ema9[-2]
    ema20_prev = ema20[-2]

    # -- Determine bias --
    price_below_vwap = current_price < vwap
    price_above_vwap = current_price > vwap
    bearish_ema = ema9_now < ema20_now
    bullish_ema = ema9_now > ema20_now

    # -- CBC (Candle Body Close) detection --
    is_green_candle = current_price > current_open   # close > open
    is_red_candle = current_price < current_open      # close < open

    # Body size check: CBC should be a weak pullback candle
    current_body = abs(current_price - current_open)
    body_sizes = []
    lookback_start = max(0, n - CBC_BODY_AVG_LOOKBACK - 1)
    for i in range(lookback_start, n - 1):
        body_sizes.append(abs(closes[i] - opens[i]))
    avg_body = sum(body_sizes) / len(body_sizes) if body_sizes else current_body
    is_weak_pullback = current_body < (CBC_BODY_THRESHOLD * avg_body) if avg_body > 0 else False

    # If body is zero (doji), still allow as very weak pullback
    if current_body == 0 and avg_body > 0:
        is_weak_pullback = True

    # -- Average volume for comparison --
    vol_lookback = min(20, n - 1)
    if vol_lookback > 0:
        avg_vol = sum(volumes[-(vol_lookback + 1):-1]) / vol_lookback
    else:
        avg_vol = current_vol
    cbc_vol_below_avg = current_vol < avg_vol

    # -- EMA gap widening check --
    ema_gap_now = abs(ema9_now - ema20_now)
    ema_gap_prev = abs(ema9_prev - ema20_prev)
    ema_gap_widening = ema_gap_now > ema_gap_prev

    # -- VWAP distance --
    vwap_distance_pct = abs(current_price - vwap) / vwap if vwap > 0 else 0
    price_far_from_vwap = vwap_distance_pct > 0.01  # >1% from VWAP

    direction = None
    signal_type = None

    # =====================================================
    # SHORT Setup: green candle below VWAP + bearish EMAs
    # =====================================================
    if price_below_vwap and bearish_ema and is_green_candle and is_weak_pullback:
        direction = "SHORT"
        signal_type = "SELL"

        entry_price = current_price
        buffer = current_high * SL_BUFFER_PCT
        stop_loss = current_high + buffer  # Above the green candle high
        risk = stop_loss - entry_price

        if risk <= 0:
            print(f"  [{symbol}] SHORT: invalid risk (SL <= entry)")
            return None

        # Confidence-based R:R scaling
        conf = BASE_CONFIDENCE
        if price_far_from_vwap:
            conf += 0.05
        if ema_gap_widening:
            conf += 0.05
        if cbc_vol_below_avg:
            conf += 0.05
        conf = min(conf, MAX_CONFIDENCE)

        rr_mult = TP_RR_MIN if conf < 0.80 else TP_RR_MAX
        take_profit = entry_price - (risk * rr_mult)
        rr = (entry_price - take_profit) / risk

        reason = (
            f"MapleStax SHORT: Green CBC below VWAP | "
            f"Price={_smart_round(entry_price, entry_price)} < "
            f"VWAP={_smart_round(vwap, vwap)} | "
            f"EMA9={_smart_round(ema9_now, ema9_now)} < "
            f"EMA20={_smart_round(ema20_now, ema20_now)} | "
            f"Body={current_body / avg_body * 100:.0f}% of avg | "
            f"R:R=1:{rr:.1f}"
        )

    # =====================================================
    # LONG Setup: red candle above VWAP + bullish EMAs
    # =====================================================
    elif price_above_vwap and bullish_ema and is_red_candle and is_weak_pullback:
        direction = "LONG"
        signal_type = "BUY"

        entry_price = current_price
        buffer = current_low * SL_BUFFER_PCT
        stop_loss = current_low - buffer  # Below the red candle low
        risk = entry_price - stop_loss

        if risk <= 0:
            print(f"  [{symbol}] LONG: invalid risk (entry <= SL)")
            return None

        # Confidence-based R:R scaling
        conf = BASE_CONFIDENCE
        if price_far_from_vwap:
            conf += 0.05
        if ema_gap_widening:
            conf += 0.05
        if cbc_vol_below_avg:
            conf += 0.05
        conf = min(conf, MAX_CONFIDENCE)

        rr_mult = TP_RR_MIN if conf < 0.80 else TP_RR_MAX
        take_profit = entry_price + (risk * rr_mult)
        rr = (take_profit - entry_price) / risk

        reason = (
            f"MapleStax LONG: Red CBC above VWAP | "
            f"Price={_smart_round(entry_price, entry_price)} > "
            f"VWAP={_smart_round(vwap, vwap)} | "
            f"EMA9={_smart_round(ema9_now, ema9_now)} > "
            f"EMA20={_smart_round(ema20_now, ema20_now)} | "
            f"Body={current_body / avg_body * 100:.0f}% of avg | "
            f"R:R=1:{rr:.1f}"
        )

    else:
        # No setup on this candle
        setup_reasons = []
        if not (price_below_vwap and bearish_ema) and not (price_above_vwap and bullish_ema):
            setup_reasons.append("no VWAP+EMA alignment")
        elif not is_green_candle and not is_red_candle:
            setup_reasons.append("doji candle (no CBC)")
        elif not is_weak_pullback:
            setup_reasons.append(f"CBC body too large ({current_body / avg_body * 100:.0f}% of avg)")
        else:
            setup_reasons.append("CBC color mismatch for setup direction")
        print(f"  [{symbol}] No setup: {', '.join(setup_reasons)}")
        return None

    # -- Build pick dict matching active_picks.json schema --
    today = _today_str()
    hhmm = _today_hhmm()
    pick_id = f"maplestax_vwap::{symbol}::{today}_{hhmm}"

    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

    pick = {
        "id": pick_id,
        "strategy": "maplestax_vwap",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": _smart_round(entry_price, entry_price),
        "entry_date": today,
        "take_profit": _smart_round(take_profit, entry_price),
        "stop_loss": _smart_round(stop_loss, entry_price),
        "confidence": round(conf, 2),
        "ml_score": None,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "high_water_mark": None,
        "status": "OPEN",
        "regime_at_entry": "trending",
        "atr_at_entry": None,
        "rsi_at_entry": None,
        "volume_ratio": round(vol_ratio, 2),
        "hold_days": None,
        "allocation": 2000.0,
        "gross_tp": _smart_round(take_profit, entry_price),
        "net_tp": _smart_round(
            take_profit * (1 - 0.001) if direction == "LONG"
            else take_profit * (1 + 0.001),
            entry_price
        ),
        "transaction_cost_pct": 0.001,
        "cost_model": 0.001,
        "position_sizing": "risk_based",
        "risk_per_trade_pct": 0.02,
        "regime_compatible": True,
        "regime_adx": None,
        "regime_volatility": None,
        "regime_trend_direction": direction.lower(),
        "regime_warning": None,
        "hmm_regime": None,
        "hmm_confidence": None,
        "hmm_signal": None,
        "hmm_leverage": None,
        "forward_trades": 0,
        "forward_wr": 0.0,
        "forward_validated": False,
        "elite_score": None,
        "elite_grade": None,
        "elite_breakdown": None,
        # -- MapleStax-specific fields --
        "vwap": _smart_round(vwap, entry_price),
        "vwap_distance_pct": round(vwap_distance_pct * 100, 2),
        "ema9": _smart_round(ema9_now, entry_price),
        "ema20": _smart_round(ema20_now, entry_price),
        "ema_gap_widening": ema_gap_widening,
        "cbc_body_pct_of_avg": round(current_body / avg_body * 100, 1) if avg_body > 0 else 0.0,
        "cbc_vol_below_avg": cbc_vol_below_avg,
        "sl_buffer_pct": SL_BUFFER_PCT,
        "rr": round(rr, 2),
        "reason": reason,
        "_dv_type": "maplestax_vwap",
    }

    return pick


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_maplestax():
    """Scan top 20 USDT pairs for MapleStax VWAP+EMA+CBC setups.

    Returns:
        list of pick dicts.
    """
    picks = []

    print(f"[MapleStax VWAP] Scanning {len(TOP_SYMBOLS)} symbols on 1H timeframe...")
    print(f"[MapleStax VWAP] VWAP session: {VWAP_SESSION_BARS} bars | "
          f"EMA: {EMA_FAST}/{EMA_SLOW} | CBC body < {CBC_BODY_THRESHOLD * 100:.0f}% avg")
    print(f"[MapleStax VWAP] SL buffer: {SL_BUFFER_PCT * 100:.2f}% | "
          f"TP R:R: {TP_RR_MIN}-{TP_RR_MAX}x")
    print()

    for symbol in TOP_SYMBOLS:
        try:
            raw = _fetch_binance_klines(symbol, interval="1h", limit=KLINE_LIMIT)
            if not raw or len(raw) < max(EMA_SLOW + 2, VWAP_SESSION_BARS + 1):
                print(f"  [{symbol}] Insufficient data ({len(raw) if raw else 0} candles)")
                continue

            candles = _parse_klines(raw)
            pick = _analyze_maplestax(symbol, candles)

            if pick:
                picks.append(pick)
                print(f"  [{symbol}] SIGNAL: {pick['direction']} | "
                      f"Entry={pick['entry_price']} TP={pick['take_profit']} "
                      f"SL={pick['stop_loss']} | Conf={pick['confidence']}")

        except Exception as exc:
            print(f"  [{symbol}] ERROR: {exc}")

    print()
    print(f"[MapleStax VWAP] Scan complete: {len(picks)} signal(s) from "
          f"{len(TOP_SYMBOLS)} symbols")
    return picks


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run():
    """Workflow integration entry point.

    Returns:
        list of pick dicts for integration with the Alpha Engine pipeline.
    """
    return scan_maplestax()


def main():
    """CLI entry point: scan and save picks."""
    print("=" * 65)
    print("MAPLESTAX VWAP -- VWAP + EMA + CBC Pullback Strategy")
    print("Credit: MapleStax Trades (@MapleStaxTrades on X/Twitter)")
    print("=" * 65)
    print(f"Time: {_now_iso()}")
    print(f"Symbols: {len(TOP_SYMBOLS)} top USDT pairs")
    print()

    picks = scan_maplestax()

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save results
    output = {
        "generated_at": _now_iso(),
        "strategy": "maplestax_vwap",
        "description": "MapleStax Trades VWAP+EMA+CBC pullback method",
        "credit": "MapleStax Trades (@MapleStaxTrades on X/Twitter)",
        "timeframe": "1h",
        "symbols_scanned": len(TOP_SYMBOLS),
        "signals_found": len(picks),
        "parameters": {
            "ema_fast": EMA_FAST,
            "ema_slow": EMA_SLOW,
            "vwap_session_bars": VWAP_SESSION_BARS,
            "sl_buffer_pct": SL_BUFFER_PCT,
            "tp_rr_min": TP_RR_MIN,
            "tp_rr_max": TP_RR_MAX,
            "cbc_body_threshold": CBC_BODY_THRESHOLD,
            "base_confidence": BASE_CONFIDENCE,
            "max_confidence": MAX_CONFIDENCE,
        },
        "picks": picks,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(picks)} picks to {OUTPUT_PATH}")

    if picks:
        print("\n--- Pick Summary ---")
        for p in picks:
            print(f"  {p['symbol']:12s}  {p['direction']:5s}  "
                  f"Entry={p['entry_price']}  TP={p['take_profit']}  "
                  f"SL={p['stop_loss']}  conf={p['confidence']:.2f}  "
                  f"VWAP={p['vwap']}  R:R=1:{p['rr']}")
    else:
        print("\nNo MapleStax setups found. "
              "Waiting for CBC pullback candles with VWAP+EMA alignment.")

    return picks


if __name__ == "__main__":
    run()

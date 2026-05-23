"""
BTC BREAKOUT -- Dynamic S/R Breakout Scanner (BTCUSDT Only)
============================================================
Standalone scanner based on the MQL5 "BTC AutoTrader" system
(78% WR, PF 1.26, broker-verified).

Strategy: btc_breakout
  - Symbol: BTCUSDT only
  - Timeframe: 1H candles
  - Calculates dynamic support (lowest low of last 20 candles)
    and resistance (highest high of last 20 candles)
  - LONG: price breaks above resistance with volume confirmation
    (volume > 1.5x 20-period average) and 2+ consecutive bullish candles
  - SHORT: price breaks below support with volume confirmation
    and 2+ consecutive bearish candles
  - SL at opposite side of the range
  - TP at 1.5x the range (R:R = 1:1.5)
  - Trailing stop: move SL to breakeven when +1% in profit
  - Filters: skip if range < 0.5% (consolidation) or > 5% (too volatile)

References:
- MQL5 BTC AutoTrader: 78% WR, PF 1.26 (broker-verified backtest)
- Donchian Channel breakout methodology (Donchian, 1960)
- Volume confirmation filter reduces false breakouts by ~30% (Kroll, 1988)
"""

from __future__ import annotations

import json
import os
import sys
import time
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
OUTPUT_PATH = os.path.join(DATA_DIR, "btc_breakout_picks.json")

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

# Non-Binance fallbacks (CoinGecko, KuCoin, CryptoCompare)
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# -- Strategy parameters --
SYMBOL = "BTCUSDT"
LOOKBACK_PERIOD = 20          # 20-candle lookback for S/R
VOLUME_CONFIRM_MULT = 1.5     # Volume must be > 1.5x average
VOLUME_AVG_PERIOD = 20        # Period for average volume
CONSECUTIVE_CANDLES = 2       # Require 2 consecutive candles in direction
RANGE_MIN_PCT = 0.005         # Skip if range < 0.5% of price
RANGE_MAX_PCT = 0.05          # Skip if range > 5% of price
RR_RATIO = 1.5                # Risk:Reward = 1:1.5
BREAKEVEN_TRIGGER_PCT = 0.01  # Move SL to breakeven at +1%
KLINE_LIMIT = 50              # Fetch 50 1H candles
RSI_PERIOD = 14


# ---------------------------------------------------------------------------
# Helpers (pure Python, no numpy/pandas)
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


def _fetch_binance_klines(symbol, interval="1h", limit=50):
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
    """Parse Binance klines into dict of lists."""
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


def _compute_rsi(closes, period=14):
    """Compute RSI using Wilder's smoothing. Pure Python."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi_values = [50.0] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_values


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _analyze_breakout(candles):
    """Analyze BTCUSDT for dynamic S/R breakout signals.

    Returns a pick dict if signal triggers, else None.
    """
    n = len(candles["close"])
    if n < LOOKBACK_PERIOD + CONSECUTIVE_CANDLES + 1:
        print(f"  [BTCUSDT] Insufficient data: {n} candles (need {LOOKBACK_PERIOD + CONSECUTIVE_CANDLES + 1})")
        return None

    closes = candles["close"]
    highs = candles["high"]
    lows = candles["low"]
    opens = candles["open"]
    volumes = candles["volume"]

    current_price = closes[-1]

    # -- Dynamic Support/Resistance from last 20 candles (excluding current) --
    lookback_highs = highs[-(LOOKBACK_PERIOD + 1):-1]
    lookback_lows = lows[-(LOOKBACK_PERIOD + 1):-1]

    resistance = max(lookback_highs)
    support = min(lookback_lows)
    sr_range = resistance - support

    # -- Range filters --
    range_pct = sr_range / current_price if current_price > 0 else 0
    if range_pct < RANGE_MIN_PCT:
        print(f"  [BTCUSDT] SKIP: range too tight ({range_pct*100:.2f}% < {RANGE_MIN_PCT*100:.1f}%)")
        return None
    if range_pct > RANGE_MAX_PCT:
        print(f"  [BTCUSDT] SKIP: range too wide ({range_pct*100:.2f}% > {RANGE_MAX_PCT*100:.1f}%)")
        return None

    # -- Volume confirmation --
    vol_lookback = min(VOLUME_AVG_PERIOD, n - 1)
    if vol_lookback > 0:
        avg_vol = sum(volumes[-(vol_lookback + 1):-1]) / vol_lookback
    else:
        avg_vol = volumes[-1]
    current_vol = volumes[-1]
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
    volume_confirmed = vol_ratio >= VOLUME_CONFIRM_MULT

    # -- Consecutive candle check --
    # Check last CONSECUTIVE_CANDLES candles are in breakout direction
    bullish_streak = all(
        closes[-(i + 1)] > opens[-(i + 1)]
        for i in range(CONSECUTIVE_CANDLES)
    )
    bearish_streak = all(
        closes[-(i + 1)] < opens[-(i + 1)]
        for i in range(CONSECUTIVE_CANDLES)
    )

    # -- Breakout detection --
    long_breakout = (
        current_price > resistance
        and volume_confirmed
        and bullish_streak
    )
    short_breakout = (
        current_price < support
        and volume_confirmed
        and bearish_streak
    )

    if not long_breakout and not short_breakout:
        print(f"  [BTCUSDT] No breakout. Price={current_price:.2f} "
              f"S={support:.2f} R={resistance:.2f} "
              f"VolRatio={vol_ratio:.2f} "
              f"Bull={bullish_streak} Bear={bearish_streak}")
        return None

    # -- Direction --
    if long_breakout:
        direction = "LONG"
        signal_type = "BUY"
        entry_price = current_price
        stop_loss = _smart_round(support, entry_price)
        risk = entry_price - support
        take_profit = _smart_round(entry_price + (risk * RR_RATIO), entry_price)
        breakeven_price = _smart_round(entry_price * (1.0 + BREAKEVEN_TRIGGER_PCT), entry_price)
        breakout_type = "resistance_breakout"
    else:
        direction = "SHORT"
        signal_type = "SELL"
        entry_price = current_price
        stop_loss = _smart_round(resistance, entry_price)
        risk = resistance - entry_price
        take_profit = _smart_round(entry_price - (risk * RR_RATIO), entry_price)
        breakeven_price = _smart_round(entry_price * (1.0 - BREAKEVEN_TRIGGER_PCT), entry_price)
        breakout_type = "support_breakdown"

    # -- RSI for context --
    rsi_values = _compute_rsi(closes, RSI_PERIOD)
    current_rsi = rsi_values[-1] if rsi_values else 50.0

    # -- Confidence: based on volume strength and range clarity --
    # Higher volume ratio and mid-range price = higher confidence
    vol_conf = min(1.0, vol_ratio / 3.0)  # Caps at 3x volume
    range_conf = min(1.0, range_pct / 0.03)  # Caps at 3% range
    confidence = round(min(0.90, 0.55 + vol_conf * 0.20 + range_conf * 0.15), 3)

    # -- ATR (average of high-low over last 14 bars) --
    atr_lookback = min(14, n)
    atr = sum(highs[-(i + 1)] - lows[-(i + 1)] for i in range(atr_lookback)) / atr_lookback

    today = _today_str()
    hhmm = _today_hhmm()
    pick_id = f"btc_breakout::{SYMBOL}::{today}_{hhmm}"

    # -- Build pick dict matching active_picks.json schema --
    pick = {
        "id": pick_id,
        "strategy": "btc_breakout",
        "symbol": SYMBOL,
        "category": "crypto",
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": _smart_round(entry_price, entry_price),
        "entry_date": today,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "ml_score": None,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "high_water_mark": None,
        "status": "OPEN",
        "regime_at_entry": "breakout",
        "atr_at_entry": _smart_round(atr, entry_price),
        "rsi_at_entry": round(current_rsi, 1),
        "volume_ratio": round(vol_ratio, 2),
        "hold_days": None,
        "allocation": 2000.0,
        "gross_tp": take_profit,
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
        # -- BTC Breakout extra fields --
        "breakout_type": breakout_type,
        "resistance": _smart_round(resistance, entry_price),
        "support": _smart_round(support, entry_price),
        "sr_range": _smart_round(sr_range, entry_price),
        "sr_range_pct": round(range_pct * 100, 2),
        "breakeven_trigger": breakeven_price,
        "trailing_stop_note": f"Move SL to breakeven ({_smart_round(entry_price, entry_price)}) when price reaches {breakeven_price}",
        "rr": RR_RATIO,
        "lookback_period": LOOKBACK_PERIOD,
        "volume_threshold": VOLUME_CONFIRM_MULT,
        "consecutive_candles": CONSECUTIVE_CANDLES,
        "reason": (
            f"BTC AutoTrader Breakout | {breakout_type.replace('_', ' ').title()} | "
            f"Price={_smart_round(entry_price, entry_price)} broke "
            f"{'R=' + str(_smart_round(resistance, entry_price)) if direction == 'LONG' else 'S=' + str(_smart_round(support, entry_price))} | "
            f"Vol={vol_ratio:.1f}x avg | Range={range_pct*100:.1f}% | "
            f"RSI={current_rsi:.1f} | R:R=1:{RR_RATIO}"
        ),
        "_dv_type": "btc_breakout",
        "_rsi": round(current_rsi, 2),
    }

    return pick


# ---------------------------------------------------------------------------
# Scanner entry points
# ---------------------------------------------------------------------------

def scan_btc_breakout():
    """Scan BTCUSDT for dynamic S/R breakout signals.

    Returns:
        list of pick dicts (0 or 1 elements).
    """
    picks = []

    print(f"[BTC Breakout] Scanning {SYMBOL} on 1H timeframe...")
    print(f"[BTC Breakout] S/R lookback: {LOOKBACK_PERIOD} candles")
    print(f"[BTC Breakout] Volume threshold: {VOLUME_CONFIRM_MULT}x avg")
    print(f"[BTC Breakout] Range filter: {RANGE_MIN_PCT*100:.1f}% - {RANGE_MAX_PCT*100:.1f}%")
    print(f"[BTC Breakout] R:R = 1:{RR_RATIO}")
    print()

    try:
        raw = _fetch_binance_klines(SYMBOL, interval="1h", limit=KLINE_LIMIT)
        if not raw or len(raw) < LOOKBACK_PERIOD + CONSECUTIVE_CANDLES + 1:
            print(f"  [{SYMBOL}] Insufficient data ({len(raw) if raw else 0} candles)")
            return picks

        candles = _parse_klines(raw)
        pick = _analyze_breakout(candles)

        if pick:
            picks.append(pick)
            print(f"  [{SYMBOL}] SIGNAL: {pick['breakout_type']}")
            print(f"    Entry={pick['entry_price']}  TP={pick['take_profit']}  "
                  f"SL={pick['stop_loss']}  R:R=1:{RR_RATIO}")
            print(f"    S={pick['support']}  R={pick['resistance']}  "
                  f"Range={pick['sr_range_pct']}%  Vol={pick['volume_ratio']}x")
        else:
            print(f"  [{SYMBOL}] No breakout signal at this time.")

    except Exception as exc:
        print(f"  [{SYMBOL}] ERROR: {exc}")

    print()
    print(f"[BTC Breakout] Scan complete: {len(picks)} signal(s)")
    return picks


def run():
    """Workflow integration entry point.

    Returns:
        list of pick dicts for integration with the Alpha Engine pipeline.
    """
    return scan_btc_breakout()


def main():
    """CLI entry point: scan and save picks."""
    print("=" * 60)
    print("BTC BREAKOUT -- Dynamic S/R Breakout Scanner")
    print("Based on MQL5 BTC AutoTrader (78% WR, PF 1.26)")
    print("=" * 60)
    print(f"Time: {_now_iso()}")
    print(f"Symbol: {SYMBOL}")
    print()

    picks = scan_btc_breakout()

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save results
    output = {
        "generated_at": _now_iso(),
        "strategy": "btc_breakout",
        "symbol": SYMBOL,
        "timeframe": "1h",
        "signals_found": len(picks),
        "parameters": {
            "lookback_period": LOOKBACK_PERIOD,
            "volume_confirm_mult": VOLUME_CONFIRM_MULT,
            "range_min_pct": RANGE_MIN_PCT,
            "range_max_pct": RANGE_MAX_PCT,
            "rr_ratio": RR_RATIO,
            "consecutive_candles": CONSECUTIVE_CANDLES,
            "breakeven_trigger_pct": BREAKEVEN_TRIGGER_PCT,
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
                  f"SL={p['stop_loss']}  conf={p['confidence']:.3f}  "
                  f"type={p['breakout_type']}")
    else:
        print("\nNo breakout signal. BTC is within the 20-candle S/R range.")

    return picks


if __name__ == "__main__":
    main()

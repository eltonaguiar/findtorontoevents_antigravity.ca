#!/usr/bin/env python3
"""
EDGE FINDER — Combination Strategy Backtester
Tests 6 novel combination strategies designed to find a consistent, repeatable edge.

Strategies:
  A: SuperTrend + VWMA Confluence (dual confirmation)
  B: Keltner Squeeze + RSI2 Oversold (squeeze breakout)
  C: Triple Confirmation (SuperTrend + ADX + Volume)
  D: Mean Reversion with Trend Guard (double oversold + trend)
  E: Momentum Persistence (breakout continuation)
  F: SHORT-Only Fear/Greed Contrarian

12 symbols x 3 timeframes, Binance API with failover, 1000 bars, 0.05% commission.
"""

import json, time, sys, os, statistics
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── Configuration ─────────────────────────────────────────────────
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
FALLBACK_APIS = [
    # CoinGecko, KuCoin, CryptoCompare — used if all Binance mirrors fail
    ("coingecko", "https://api.coingecko.com/api/v3"),
    ("kucoin", "https://api.kucoin.com"),
    ("cryptocompare", "https://min-api.cryptocompare.com"),
]

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT",
    "LINKUSDT", "DOGEUSDT", "LTCUSDT", "XRPUSDT", "NEARUSDT", "DOTUSDT",
]
TIMEFRAMES = ["1h", "4h", "1d"]
COMMISSION = 0.0005  # 0.05%
BARS = 1000

RESULTS_PATH = "e:/findtorontoevents_antigravity.ca/backtest_edge_finder_results.json"

# ─── Data Fetching ─────────────────────────────────────────────────
def fetch_klines(symbol, interval, limit=BARS):
    """Fetch klines with Binance mirror failover + alternative exchanges."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            candles = []
            for k in data:
                candles.append({
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
        except Exception as e:
            continue

    # KuCoin fallback
    kucoin_tf_map = {"1h": "1hour", "4h": "4hour", "1d": "1day"}
    kc_sym = symbol.replace("USDT", "-USDT")
    kc_tf = kucoin_tf_map.get(interval, "1hour")
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type={kc_tf}&symbol={kc_sym}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
        if raw.get("code") == "200000" and raw.get("data"):
            candles = []
            for k in reversed(raw["data"][:limit]):
                candles.append({
                    "open": float(k[1]),
                    "close": float(k[2]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
    except:
        pass

    print(f"  [ERROR] All sources failed for {symbol} {interval}")
    return None


# ─── Indicators ────────────────────────────────────────────────────
def calc_rsi(closes, period=14):
    rsi = [None] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i-1]
        if delta > 0: gains += delta
        else: losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - 100 / (1 + rs)
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i-1]
        g = delta if delta > 0 else 0
        l = -delta if delta < 0 else 0
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - 100 / (1 + rs)
    return rsi


def calc_atr(candles, period=14):
    atr = [None] * len(candles)
    if len(candles) < period + 1:
        return atr
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i-1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return atr
    avg = sum(trs[:period]) / period
    atr[period] = avg
    for i in range(period, len(trs)):
        avg = (avg * (period - 1) + trs[i]) / period
        atr[i + 1] = avg
    return atr


def calc_ema(values, period):
    ema = [None] * len(values)
    k = 2 / (period + 1)
    start = None
    for i, v in enumerate(values):
        if v is not None:
            start = i
            break
    if start is None or (len(values) - start) < period:
        return ema
    sma = sum(values[start:start+period]) / period
    ema[start + period - 1] = sma
    for i in range(start + period, len(values)):
        if values[i] is None:
            ema[i] = ema[i-1]
        else:
            ema[i] = values[i] * k + ema[i-1] * (1 - k)
    return ema


def calc_sma(values, period):
    sma = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if None in window:
            sma[i] = sma[i-1] if i > 0 and sma[i-1] is not None else None
        else:
            sma[i] = sum(window) / period
    return sma


def calc_vwma(candles, period):
    vwma = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        cv_sum = sum(candles[j]["close"] * candles[j]["volume"] for j in range(i - period + 1, i + 1))
        v_sum = sum(candles[j]["volume"] for j in range(i - period + 1, i + 1))
        vwma[i] = cv_sum / v_sum if v_sum > 0 else candles[i]["close"]
    return vwma


def calc_adx(candles, period=14):
    adx = [None] * len(candles)
    if len(candles) < 2 * period + 1:
        return adx
    plus_dm_list, minus_dm_list, tr_list = [], [], []
    for i in range(1, len(candles)):
        h, l = candles[i]["high"], candles[i]["low"]
        ph, pl = candles[i-1]["high"], candles[i-1]["low"]
        pc = candles[i-1]["close"]
        up, down = h - ph, pl - l
        plus_dm_list.append(up if (up > down and up > 0) else 0)
        minus_dm_list.append(down if (down > up and down > 0) else 0)
        tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(tr_list) < period:
        return adx
    atr_s = sum(tr_list[:period])
    pdm_s = sum(plus_dm_list[:period])
    mdm_s = sum(minus_dm_list[:period])
    dx_list = []
    for i in range(period, len(tr_list)):
        atr_s = atr_s - atr_s / period + tr_list[i]
        pdm_s = pdm_s - pdm_s / period + plus_dm_list[i]
        mdm_s = mdm_s - mdm_s / period + minus_dm_list[i]
        if atr_s == 0:
            dx_list.append(0)
            continue
        plus_di = 100 * pdm_s / atr_s
        minus_di = 100 * mdm_s / atr_s
        di_sum = plus_di + minus_di
        dx_list.append(100 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0)
    if len(dx_list) < period:
        return adx
    adx_val = sum(dx_list[:period]) / period
    idx_base = 2 * period
    if idx_base < len(candles):
        adx[idx_base] = adx_val
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period
        ci = i + period + 1
        if ci < len(candles):
            adx[ci] = adx_val
    return adx


def calc_supertrend(candles, period=10, multiplier=3.0):
    """Returns list of (direction, st_value) tuples. direction: 1=bullish, -1=bearish."""
    n = len(candles)
    st = [(0, 0.0)] * n
    atr = calc_atr(candles, period)

    upper_band = [0.0] * n
    lower_band = [0.0] * n
    direction = [1] * n

    for i in range(period, n):
        if atr[i] is None:
            continue
        hl2 = (candles[i]["high"] + candles[i]["low"]) / 2
        ub = hl2 + multiplier * atr[i]
        lb = hl2 - multiplier * atr[i]

        # Adjust bands
        if i > period:
            if lb > lower_band[i-1] or candles[i-1]["close"] < lower_band[i-1]:
                lower_band[i] = lb
            else:
                lower_band[i] = lower_band[i-1]

            if ub < upper_band[i-1] or candles[i-1]["close"] > upper_band[i-1]:
                upper_band[i] = ub
            else:
                upper_band[i] = upper_band[i-1]
        else:
            upper_band[i] = ub
            lower_band[i] = lb

        # Direction
        if i > period:
            prev_dir = direction[i-1]
            if prev_dir == 1:
                direction[i] = 1 if candles[i]["close"] > lower_band[i] else -1
            else:
                direction[i] = -1 if candles[i]["close"] < upper_band[i] else 1
        else:
            direction[i] = 1 if candles[i]["close"] > lower_band[i] else -1

        val = lower_band[i] if direction[i] == 1 else upper_band[i]
        st[i] = (direction[i], val)

    return st


def calc_bollinger(closes, period=20, std_mult=2.0):
    """Returns (upper, middle, lower) arrays."""
    n = len(closes)
    upper, middle, lower = [None]*n, [None]*n, [None]*n
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        m = sum(window) / period
        variance = sum((x - m)**2 for x in window) / period
        std = variance ** 0.5
        middle[i] = m
        upper[i] = m + std_mult * std
        lower[i] = m - std_mult * std
    return upper, middle, lower


def calc_keltner(candles, ema_period=20, atr_period=10, atr_mult=1.5):
    """Returns (upper, middle, lower) arrays."""
    closes = [c["close"] for c in candles]
    n = len(candles)
    mid = calc_ema(closes, ema_period)
    atr = calc_atr(candles, atr_period)
    upper, lower = [None]*n, [None]*n
    for i in range(n):
        if mid[i] is not None and atr[i] is not None:
            upper[i] = mid[i] + atr_mult * atr[i]
            lower[i] = mid[i] - atr_mult * atr[i]
    return upper, mid, lower


def calc_stochastic(candles, k_period=14, d_period=3, smooth=3):
    """Returns (K, D) arrays."""
    n = len(candles)
    raw_k = [None] * n
    for i in range(k_period - 1, n):
        window_h = [candles[j]["high"] for j in range(i - k_period + 1, i + 1)]
        window_l = [candles[j]["low"] for j in range(i - k_period + 1, i + 1)]
        hh, ll = max(window_h), min(window_l)
        if hh == ll:
            raw_k[i] = 50.0
        else:
            raw_k[i] = 100 * (candles[i]["close"] - ll) / (hh - ll)

    # Smooth K
    k_vals = [None] * n
    for i in range(n):
        if i < smooth - 1 or raw_k[i] is None:
            continue
        window = [raw_k[i - j] for j in range(smooth) if raw_k[i - j] is not None]
        if len(window) == smooth:
            k_vals[i] = sum(window) / smooth

    # D = SMA of K
    d_vals = [None] * n
    for i in range(n):
        if i < d_period - 1 or k_vals[i] is None:
            continue
        window = [k_vals[i - j] for j in range(d_period) if k_vals[i - j] is not None]
        if len(window) == d_period:
            d_vals[i] = sum(window) / d_period

    return k_vals, d_vals


# ─── Trade Simulator ───────────────────────────────────────────────
def simulate_trades(signals, candles, commission=COMMISSION):
    atr = calc_atr(candles)
    trades = []
    for idx, direction, tp_mult, sl_mult, max_hold in signals:
        if idx >= len(candles) - 2:
            continue
        if atr[idx] is None or atr[idx] == 0:
            continue
        # FIX: Enter at NEXT bar open, not signal bar close (prevents look-ahead bias)
        entry = candles[idx + 1]["open"]
        a = atr[idx]
        if direction == "LONG":
            tp = entry + tp_mult * a
            sl = entry - sl_mult * a
        else:
            tp = entry - tp_mult * a
            sl = entry + sl_mult * a

        exit_price = None
        exit_bar = None
        exit_reason = None
        for j in range(idx + 2, min(idx + 2 + max_hold, len(candles))):
            h, l = candles[j]["high"], candles[j]["low"]
            if direction == "LONG":
                if l <= sl:
                    exit_price, exit_bar, exit_reason = sl, j, "SL"; break
                if h >= tp:
                    exit_price, exit_bar, exit_reason = tp, j, "TP"; break
            else:
                if h >= sl:
                    exit_price, exit_bar, exit_reason = sl, j, "SL"; break
                if l <= tp:
                    exit_price, exit_bar, exit_reason = tp, j, "TP"; break
        if exit_price is None:
            exit_bar = min(idx + 1 + max_hold, len(candles) - 1)
            exit_price = candles[exit_bar]["close"]
            exit_reason = "HOLD"

        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry - 2 * commission
        else:
            pnl_pct = (entry - exit_price) / entry - 2 * commission
        trades.append({
            "entry_bar": idx, "exit_bar": exit_bar, "direction": direction,
            "entry": entry, "exit": exit_price, "pnl_pct": pnl_pct, "reason": exit_reason,
        })
    return trades


def calc_stats(trades):
    if not trades:
        return {"trades": 0, "win_rate": 0, "pf": 0, "total_pnl": 0, "avg_pnl": 0,
                "max_dd_pct": 0, "avg_hold": 0, "sharpe": 0, "longs": 0, "shorts": 0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.0001
    total_pnl = sum(t["pnl_pct"] for t in trades)
    pnls = [t["pnl_pct"] for t in trades]
    avg_pnl = total_pnl / len(trades)
    if len(pnls) > 1:
        std = statistics.stdev(pnls)
        sharpe = (avg_pnl / std) * (len(pnls) ** 0.5) if std > 0 else 0
    else:
        sharpe = 0
    cum = 0; peak = 0; max_dd = 0
    for p in pnls:
        cum += p
        if cum > peak: peak = cum
        dd = peak - cum
        if dd > max_dd: max_dd = dd
    avg_hold = sum(t["exit_bar"] - t["entry_bar"] for t in trades) / len(trades)
    longs = sum(1 for t in trades if t["direction"] == "LONG")
    shorts = sum(1 for t in trades if t["direction"] == "SHORT")
    return {
        "trades": len(trades),
        "win_rate": round(100 * len(wins) / len(trades), 1),
        "pf": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0,
        "total_pnl": round(100 * total_pnl, 2),
        "avg_pnl": round(100 * avg_pnl, 3),
        "max_dd_pct": round(100 * max_dd, 2),
        "avg_hold": round(avg_hold, 1),
        "sharpe": round(sharpe, 2),
        "longs": longs,
        "shorts": shorts,
    }


# ─── Strategy Implementations ─────────────────────────────────────

def strategy_A_supertrend_vwma(candles):
    """SuperTrend + VWMA Confluence — dual confirmation."""
    st = calc_supertrend(candles, period=10, multiplier=3.0)
    vwma = calc_vwma(candles, 20)
    closes = [c["close"] for c in candles]
    ema20 = calc_ema(closes, 20)
    signals = []
    for i in range(30, len(candles)):
        if st[i][0] == 0 or vwma[i] is None or ema20[i] is None:
            continue
        direction_st = st[i][0]  # 1=bull, -1=bear
        # Check for direction change (avoid piling up signals)
        if i > 30 and st[i-1][0] == direction_st:
            # Only fire on transitions or every 5 bars
            if i % 5 != 0:
                continue
        if direction_st == 1 and vwma[i] > ema20[i]:
            signals.append((i, "LONG", 2.5, 2.0, 20))
        elif direction_st == -1 and vwma[i] < ema20[i]:
            signals.append((i, "SHORT", 2.5, 2.0, 20))
    return simulate_trades(signals, candles)


def strategy_B_keltner_squeeze_rsi2(candles):
    """Keltner Squeeze + RSI2 Oversold."""
    closes = [c["close"] for c in candles]
    bb_upper, bb_mid, bb_lower = calc_bollinger(closes, 20, 2.0)
    kc_upper, kc_mid, kc_lower = calc_keltner(candles, 20, 10, 1.5)
    rsi2 = calc_rsi(closes, 2)
    ema100 = calc_ema(closes, 100)
    signals = []

    # Track squeeze bars
    squeeze_count = 0
    for i in range(100, len(candles)):
        if (bb_upper[i] is None or kc_upper[i] is None or
            bb_lower[i] is None or kc_lower[i] is None or
            rsi2[i] is None or ema100[i] is None):
            squeeze_count = 0
            continue

        # BB inside Keltner = squeeze
        in_squeeze = bb_upper[i] < kc_upper[i] and bb_lower[i] > kc_lower[i]
        if in_squeeze:
            squeeze_count += 1
        else:
            # Post-squeeze: check within 3 bars of squeeze ending
            if squeeze_count >= 3:
                if rsi2[i] is not None and rsi2[i] < 15 and closes[i] > ema100[i]:
                    signals.append((i, "LONG", 3.0, 2.0, 15))
                elif rsi2[i] is not None and rsi2[i] > 85 and closes[i] < ema100[i]:
                    signals.append((i, "SHORT", 3.0, 2.0, 15))
            squeeze_count = 0

        # During squeeze
        if squeeze_count >= 3:
            if rsi2[i] < 15 and closes[i] > ema100[i]:
                signals.append((i, "LONG", 3.0, 2.0, 15))
            elif rsi2[i] > 85 and closes[i] < ema100[i]:
                signals.append((i, "SHORT", 3.0, 2.0, 15))
    return simulate_trades(signals, candles)


def strategy_C_triple_confirmation(candles):
    """Triple Confirmation: SuperTrend + ADX + Volume."""
    st = calc_supertrend(candles, 10, 3.0)
    adx = calc_adx(candles, 14)
    volumes = [c["volume"] for c in candles]
    vol_sma20 = calc_sma(volumes, 20)
    signals = []
    for i in range(30, len(candles)):
        if st[i][0] == 0 or adx[i] is None or vol_sma20[i] is None:
            continue
        if vol_sma20[i] == 0:
            continue
        high_vol = candles[i]["volume"] > 1.5 * vol_sma20[i]
        strong_trend = adx[i] > 25
        if not high_vol or not strong_trend:
            continue
        if st[i][0] == 1:
            signals.append((i, "LONG", 2.0, 2.0, 15))
        elif st[i][0] == -1:
            signals.append((i, "SHORT", 2.0, 2.0, 15))
    return simulate_trades(signals, candles)


def strategy_D_mean_reversion_trend_guard(candles):
    """Mean Reversion with Trend Guard — double oversold + trend filter."""
    closes = [c["close"] for c in candles]
    rsi2 = calc_rsi(closes, 2)
    stoch_k, stoch_d = calc_stochastic(candles, 14, 3, 3)
    ema50 = calc_ema(closes, 50)
    signals = []
    for i in range(50, len(candles)):
        if rsi2[i] is None or stoch_k[i] is None or ema50[i] is None:
            continue
        if rsi2[i] < 10 and stoch_k[i] < 20 and closes[i] > ema50[i]:
            signals.append((i, "LONG", 1.5, 2.0, 8))
        elif rsi2[i] > 90 and stoch_k[i] > 80 and closes[i] < ema50[i]:
            signals.append((i, "SHORT", 1.5, 2.0, 8))
    return simulate_trades(signals, candles)


def strategy_E_momentum_persistence(candles):
    """Momentum Persistence — breakout continuation."""
    closes = [c["close"] for c in candles]
    adx = calc_adx(candles, 14)
    volumes = [c["volume"] for c in candles]
    vol_sma20 = calc_sma(volumes, 20)
    signals = []
    for i in range(30, len(candles)):
        if adx[i] is None or vol_sma20[i] is None:
            continue
        if adx[i] <= 30 or vol_sma20[i] == 0:
            continue
        if candles[i]["volume"] <= 2.0 * vol_sma20[i]:
            continue
        # 20-bar high/low
        lookback = closes[max(0, i-20):i]
        if not lookback:
            continue
        new_high = closes[i] > max(lookback)
        new_low = closes[i] < min(lookback)
        if new_high:
            signals.append((i, "LONG", 3.0, 1.5, 20))
        elif new_low:
            signals.append((i, "SHORT", 3.0, 1.5, 20))
    return simulate_trades(signals, candles)


def strategy_F_short_only_contrarian(candles):
    """SHORT-Only Fear/Greed Contrarian."""
    closes = [c["close"] for c in candles]
    rsi14 = calc_rsi(closes, 14)
    bb_upper, bb_mid, bb_lower = calc_bollinger(closes, 20, 2.0)
    adx = calc_adx(candles, 14)
    signals = []
    for i in range(30, len(candles)):
        if rsi14[i] is None or bb_upper[i] is None or adx[i] is None:
            continue
        if rsi14[i] > 70 and closes[i] > bb_upper[i] and adx[i] > 20:
            signals.append((i, "SHORT", 2.0, 2.0, 12))
    return simulate_trades(signals, candles)


# ─── Strategy Registry ─────────────────────────────────────────────
STRATEGIES = {
    "A_SuperTrend_VWMA": strategy_A_supertrend_vwma,
    "B_Keltner_Squeeze_RSI2": strategy_B_keltner_squeeze_rsi2,
    "C_Triple_Confirmation": strategy_C_triple_confirmation,
    "D_Mean_Reversion_Guard": strategy_D_mean_reversion_trend_guard,
    "E_Momentum_Persistence": strategy_E_momentum_persistence,
    "F_SHORT_Only_Contrarian": strategy_F_short_only_contrarian,
}


# ─── Main Runner ───────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  EDGE FINDER — Combination Strategy Backtester")
    print(f"  {len(SYMBOLS)} symbols x {len(TIMEFRAMES)} timeframes x {len(STRATEGIES)} strategies")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    all_results = {}
    total_combos = len(SYMBOLS) * len(TIMEFRAMES) * len(STRATEGIES)
    done = 0

    # Cache candle data
    candle_cache = {}

    for sym in SYMBOLS:
        for tf in TIMEFRAMES:
            key = f"{sym}_{tf}"
            if key not in candle_cache:
                candles = fetch_klines(sym, tf, BARS)
                if candles is None:
                    for strat_name in STRATEGIES:
                        done += 1
                    continue
                candle_cache[key] = candles
                time.sleep(0.15)  # Rate limit

            candles = candle_cache[key]

            for strat_name, strat_fn in STRATEGIES.items():
                done += 1
                combo_key = f"{strat_name}|{sym}|{tf}"
                try:
                    trades = strat_fn(candles)
                    stats = calc_stats(trades)
                    all_results[combo_key] = stats
                    marker = ""
                    if stats["trades"] >= 8 and stats["pf"] > 1.0:
                        marker = " ***"
                    if stats["trades"] >= 10 and stats["win_rate"] > 55 and stats["pf"] > 1.5:
                        marker = " <<<RECOMMENDED>>>"
                    if stats["sharpe"] > 1.5 and stats["trades"] >= 8:
                        marker = " <<<EDGE FOUND>>>"
                    print(f"  [{done}/{total_combos}] {combo_key}: {stats['trades']}t "
                          f"WR={stats['win_rate']}% PF={stats['pf']} "
                          f"PnL={stats['total_pnl']}% Sharpe={stats['sharpe']}{marker}")
                except Exception as e:
                    print(f"  [{done}/{total_combos}] {combo_key}: ERROR - {e}")
                    all_results[combo_key] = {"trades": 0, "error": str(e)}

    # ─── Analysis ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  RESULTS ANALYSIS")
    print("=" * 80)

    # 1. All combos with PF > 1.0 and trades >= 8
    profitable = {k: v for k, v in all_results.items()
                  if v.get("trades", 0) >= 8 and v.get("pf", 0) > 1.0}
    profitable_sorted = sorted(profitable.items(), key=lambda x: x[1].get("pf", 0), reverse=True)

    print(f"\n{'='*80}")
    print(f"  ALL PROFITABLE COMBOS (PF > 1.0, trades >= 8): {len(profitable_sorted)}")
    print(f"{'='*80}")
    for k, v in profitable_sorted:
        parts = k.split("|")
        print(f"  {parts[0]:30s} {parts[1]:10s} {parts[2]:4s} | "
              f"Trades={v['trades']:3d} WR={v['win_rate']:5.1f}% PF={v['pf']:6.2f} "
              f"PnL={v['total_pnl']:+7.2f}% Sharpe={v['sharpe']:+5.2f} "
              f"DD={v['max_dd_pct']:5.2f}% L={v.get('longs',0)} S={v.get('shorts',0)}")

    # 2. RECOMMENDED: WR > 55% AND PF > 1.5 AND trades >= 10
    recommended = {k: v for k, v in all_results.items()
                   if v.get("trades", 0) >= 10 and v.get("win_rate", 0) > 55 and v.get("pf", 0) > 1.5}
    recommended_sorted = sorted(recommended.items(), key=lambda x: x[1].get("pf", 0), reverse=True)

    print(f"\n{'='*80}")
    print(f"  RECOMMENDED (WR>55% AND PF>1.5 AND trades>=10): {len(recommended_sorted)}")
    print(f"{'='*80}")
    if not recommended_sorted:
        print("  (none)")
    for k, v in recommended_sorted:
        parts = k.split("|")
        print(f"  {parts[0]:30s} {parts[1]:10s} {parts[2]:4s} | "
              f"Trades={v['trades']:3d} WR={v['win_rate']:5.1f}% PF={v['pf']:6.2f} "
              f"PnL={v['total_pnl']:+7.2f}% Sharpe={v['sharpe']:+5.2f} "
              f"DD={v['max_dd_pct']:5.2f}%")

    # 3. EDGE FOUND: Sharpe > 1.5 and trades >= 8
    edges = {k: v for k, v in all_results.items()
             if v.get("trades", 0) >= 8 and v.get("sharpe", 0) > 1.5}
    edges_sorted = sorted(edges.items(), key=lambda x: x[1].get("sharpe", 0), reverse=True)

    print(f"\n{'='*80}")
    print(f"  EDGE FOUND (Sharpe > 1.5, institutional grade): {len(edges_sorted)}")
    print(f"{'='*80}")
    if not edges_sorted:
        print("  (none)")
    for k, v in edges_sorted:
        parts = k.split("|")
        print(f"  {parts[0]:30s} {parts[1]:10s} {parts[2]:4s} | "
              f"Trades={v['trades']:3d} WR={v['win_rate']:5.1f}% PF={v['pf']:6.2f} "
              f"PnL={v['total_pnl']:+7.2f}% Sharpe={v['sharpe']:+5.2f} "
              f"DD={v['max_dd_pct']:5.2f}%")

    # 4. Per-strategy average performance
    print(f"\n{'='*80}")
    print(f"  STRATEGY AVERAGES (across all symbols/timeframes)")
    print(f"{'='*80}")
    strategy_agg = {}
    for k, v in all_results.items():
        strat = k.split("|")[0]
        if strat not in strategy_agg:
            strategy_agg[strat] = {"trades": [], "win_rate": [], "pf": [], "total_pnl": [],
                                    "sharpe": [], "max_dd": [], "count": 0}
        if v.get("trades", 0) > 0:
            strategy_agg[strat]["trades"].append(v["trades"])
            strategy_agg[strat]["win_rate"].append(v["win_rate"])
            strategy_agg[strat]["pf"].append(v["pf"])
            strategy_agg[strat]["total_pnl"].append(v["total_pnl"])
            strategy_agg[strat]["sharpe"].append(v["sharpe"])
            strategy_agg[strat]["max_dd"].append(v["max_dd_pct"])
            strategy_agg[strat]["count"] += 1

    strat_scores = {}
    for strat, agg in sorted(strategy_agg.items()):
        if not agg["trades"]:
            continue
        avg_trades = sum(agg["trades"]) / len(agg["trades"])
        avg_wr = sum(agg["win_rate"]) / len(agg["win_rate"])
        avg_pf = sum(agg["pf"]) / len(agg["pf"])
        avg_pnl = sum(agg["total_pnl"]) / len(agg["total_pnl"])
        avg_sharpe = sum(agg["sharpe"]) / len(agg["sharpe"])
        avg_dd = sum(agg["max_dd"]) / len(agg["max_dd"])
        profitable_pct = 100 * sum(1 for p in agg["total_pnl"] if p > 0) / len(agg["total_pnl"])
        # Composite score: weight PF(30%), WR(20%), Sharpe(30%), profitable%(20%)
        score = avg_pf * 0.3 + (avg_wr / 100) * 0.2 + avg_sharpe * 0.3 + (profitable_pct / 100) * 0.2
        strat_scores[strat] = score
        print(f"  {strat:30s} | Combos={agg['count']:2d} AvgTrades={avg_trades:5.1f} "
              f"AvgWR={avg_wr:5.1f}% AvgPF={avg_pf:5.2f} AvgPnL={avg_pnl:+6.2f}% "
              f"AvgSharpe={avg_sharpe:+5.2f} AvgDD={avg_dd:5.2f}% "
              f"Profitable={profitable_pct:4.0f}% Score={score:5.3f}")

    # 5. Best strategy overall
    if strat_scores:
        best_strat = max(strat_scores, key=strat_scores.get)
        print(f"\n{'='*80}")
        print(f"  BEST STRATEGY OVERALL: {best_strat}")
        print(f"  Composite Score: {strat_scores[best_strat]:.3f}")
        print(f"{'='*80}")

        # Also show best individual combo
        best_combo = None
        best_pf = 0
        for k, v in all_results.items():
            if v.get("trades", 0) >= 10 and v.get("pf", 0) > best_pf:
                best_pf = v["pf"]
                best_combo = k
        if best_combo:
            v = all_results[best_combo]
            parts = best_combo.split("|")
            print(f"\n  BEST SINGLE COMBO: {parts[0]} | {parts[1]} | {parts[2]}")
            print(f"  Trades={v['trades']} WR={v['win_rate']}% PF={v['pf']} "
                  f"PnL={v['total_pnl']}% Sharpe={v['sharpe']} DD={v['max_dd_pct']}%")

    # Per-symbol performance
    print(f"\n{'='*80}")
    print(f"  PER-SYMBOL PERFORMANCE (best strategy for each)")
    print(f"{'='*80}")
    for sym in SYMBOLS:
        best_k, best_v = None, None
        for k, v in all_results.items():
            if sym in k and v.get("trades", 0) >= 5:
                if best_v is None or v.get("pf", 0) > best_v.get("pf", 0):
                    best_k, best_v = k, v
        if best_k:
            parts = best_k.split("|")
            print(f"  {sym:10s} -> {parts[0]:30s} {parts[2]:4s} | "
                  f"Trades={best_v['trades']:3d} WR={best_v['win_rate']:5.1f}% "
                  f"PF={best_v['pf']:6.2f} PnL={best_v['total_pnl']:+7.2f}%")

    # SHORT vs LONG breakdown
    print(f"\n{'='*80}")
    print(f"  SHORT vs LONG PERFORMANCE")
    print(f"{'='*80}")
    for strat in sorted(strategy_agg.keys()):
        total_longs = 0
        total_shorts = 0
        for k, v in all_results.items():
            if k.startswith(strat):
                total_longs += v.get("longs", 0)
                total_shorts += v.get("shorts", 0)
        print(f"  {strat:30s} | LONGs={total_longs:4d} SHORTs={total_shorts:4d}")

    # Save results
    output = {
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols": SYMBOLS,
            "timeframes": TIMEFRAMES,
            "bars": BARS,
            "commission": COMMISSION,
            "strategies": list(STRATEGIES.keys()),
        },
        "all_results": all_results,
        "profitable": {k: v for k, v in profitable_sorted},
        "recommended": {k: v for k, v in recommended_sorted},
        "edges": {k: v for k, v in edges_sorted},
        "strategy_scores": strat_scores,
        "best_strategy": best_strat if strat_scores else None,
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {RESULTS_PATH}")
    print(f"  Total combos tested: {total_combos}")
    print(f"  Profitable combos: {len(profitable_sorted)}")
    print(f"  Recommended combos: {len(recommended_sorted)}")
    print(f"  Edge found combos: {len(edges_sorted)}")


if __name__ == "__main__":
    main()

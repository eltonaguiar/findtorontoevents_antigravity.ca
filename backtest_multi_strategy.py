#!/usr/bin/env python3
"""
Multi-Strategy Backtester — 5 Strategies x 10 Symbols x 3 Timeframes
=====================================================================
Strategies:
  1. Bollinger Band Squeeze Breakout
  2. EMA Crossover with Volume Confirmation
  3. MACD Histogram Divergence
  4. Stochastic RSI Oversold/Overbought with Trend
  5. Keltner Channel Breakout with ADX Filter

Uses Binance 4-mirror failover chain per project rules.
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import requests
except ImportError:
    print("ERROR: requests library required.  pip install requests")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────────

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT",
    "LINKUSDT", "DOGEUSDT", "LTCUSDT", "ADAUSDT", "XRPUSDT",
]
TIMEFRAMES = ["1h", "4h", "1d"]
LIMIT = 1000
COMMISSION_PCT = 0.05  # 0.05 % per trade (entry + exit = 0.10 % round-trip)

RESULTS_FILE = Path(__file__).parent / "backtest_multi_strategy_results.json"

# ── Data fetching (Binance 4-mirror failover) ─────────────────────────────────

def fetch_klines(symbol: str, interval: str, limit: int = 1000) -> np.ndarray | None:
    """Fetch OHLCV from Binance with 4-mirror failover.  Returns (N,5) float64."""
    mirrors = ["api", "api1", "api2", "api3"]
    for mirror in mirrors:
        url = f"https://{mirror}.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 100:
                    # O H L C V
                    arr = np.array(
                        [[float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
                         for c in data], dtype=np.float64
                    )
                    return arr
        except Exception:
            continue
    return None

# ── Indicator helpers ─────────────────────────────────────────────────────────

def ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average, handles leading NaN values."""
    out = np.full_like(data, np.nan)
    if len(data) < period:
        return out
    k = 2.0 / (period + 1)
    # Find first window of `period` consecutive non-NaN values for seeding
    seed_start = -1
    count = 0
    for i in range(len(data)):
        if not np.isnan(data[i]):
            if count == 0:
                seed_start = i
            count += 1
            if count == period:
                break
        else:
            count = 0
            seed_start = -1
    if seed_start < 0 or count < period:
        return out
    seed_end = seed_start + period
    out[seed_end - 1] = np.mean(data[seed_start:seed_end])
    for i in range(seed_end, len(data)):
        if np.isnan(data[i]):
            out[i] = out[i - 1]  # hold previous value
        else:
            out[i] = data[i] * k + out[i - 1] * (1 - k)
    return out


def sma(data: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(data, np.nan)
    # Handle NaN-containing data with a rolling loop
    if np.any(np.isnan(data)):
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            valid = window[~np.isnan(window)]
            if len(valid) == period:
                out[i] = np.mean(valid)
    else:
        cs = np.cumsum(data)
        out[period - 1:] = (cs[period - 1:] - np.concatenate([[0], cs[:-period]])) / period
        out[period - 1] = cs[period - 1] / period
    return out


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range."""
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    return ema(tr, period)


def bollinger_bands(close: np.ndarray, period: int = 20, mult: float = 2.0):
    mid = sma(close, period)
    std = np.full_like(close, np.nan)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1:i + 1], ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    width = upper - lower
    return mid, upper, lower, width


def macd(close: np.ndarray, fast: int = 12, slow: int = 26, sig: int = 9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, sig)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI using Wilder smoothing (produces values from bar `period` onward)."""
    n = len(close)
    out = np.full(n, np.nan)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    if n < period + 1:
        return out
    avg_gain = np.mean(gain[1:period + 1])
    avg_loss = np.mean(loss[1:period + 1])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            out[i] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def stoch_rsi(close: np.ndarray, rsi_period: int = 14, stoch_period: int = 14,
              k_smooth: int = 3, d_smooth: int = 3):
    rsi_val = rsi(close, rsi_period)
    n = len(close)
    stoch_raw = np.full(n, np.nan)
    # StochRSI starts after rsi_period + stoch_period bars
    start = rsi_period + stoch_period
    for i in range(start, n):
        window = rsi_val[i - stoch_period + 1:i + 1]
        if np.any(np.isnan(window)):
            continue
        lo, hi = np.nanmin(window), np.nanmax(window)
        stoch_raw[i] = ((rsi_val[i] - lo) / (hi - lo) * 100) if hi > lo else 50.0
    # Smooth K and D using simple loops to avoid NaN propagation issues
    k_line = np.full(n, np.nan)
    d_line = np.full(n, np.nan)
    for i in range(start + k_smooth - 1, n):
        window = stoch_raw[i - k_smooth + 1:i + 1]
        valid = window[~np.isnan(window)]
        if len(valid) == k_smooth:
            k_line[i] = np.mean(valid)
    for i in range(start + k_smooth + d_smooth - 2, n):
        window = k_line[i - d_smooth + 1:i + 1]
        valid = window[~np.isnan(window)]
        if len(valid) == d_smooth:
            d_line[i] = np.mean(valid)
    return k_line, d_line


def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average Directional Index."""
    n = len(close)
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = np.concatenate([[0], plus_dm])
    minus_dm = np.concatenate([[0], minus_dm])

    atr_val = atr(high, low, close, period)
    smooth_plus = ema(plus_dm, period)
    smooth_minus = ema(minus_dm, period)

    plus_di = np.where(atr_val > 0, 100 * smooth_plus / atr_val, 0)
    minus_di = np.where(atr_val > 0, 100 * smooth_minus / atr_val, 0)

    di_sum = plus_di + minus_di
    dx = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, 0)
    adx_val = ema(dx, period)
    return adx_val

# ── Trade simulation engine ───────────────────────────────────────────────────

def simulate_trades(close: np.ndarray, signals: list, atr_arr: np.ndarray,
                    tp_mult: float, sl_mult: float, max_hold: int,
                    commission_pct: float = COMMISSION_PCT) -> list:
    """
    signals: list of (bar_index, direction)  direction = 1 for LONG, -1 for SHORT
    Returns list of trade dicts.
    """
    trades = []
    in_trade = False
    entry_bar = 0
    entry_price = 0.0
    direction = 0
    tp_price = 0.0
    sl_price = 0.0

    signal_dict = {}
    for idx, d in signals:
        if idx not in signal_dict:
            signal_dict[idx] = d

    for i in range(len(close)):
        # Check exit if in trade
        if in_trade:
            bars_held = i - entry_bar
            hit_tp = False
            hit_sl = False
            exit_price = close[i]

            if direction == 1:  # LONG
                hit_tp = close[i] >= tp_price
                hit_sl = close[i] <= sl_price
            else:  # SHORT
                hit_tp = close[i] <= tp_price
                hit_sl = close[i] >= sl_price

            should_exit = hit_tp or hit_sl or bars_held >= max_hold

            if should_exit:
                if hit_tp:
                    exit_price = tp_price
                elif hit_sl:
                    exit_price = sl_price

                if direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

                # Deduct commission (entry + exit)
                pnl_pct -= 2 * commission_pct

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "direction": direction,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "bars_held": bars_held,
                    "exit_reason": "TP" if hit_tp else ("SL" if hit_sl else "MAX_HOLD"),
                })
                in_trade = False

        # Check entry
        if not in_trade and i in signal_dict:
            direction = signal_dict[i]
            entry_bar = i
            entry_price = close[i]
            a = atr_arr[i] if not np.isnan(atr_arr[i]) else 0
            if direction == 1:
                tp_price = entry_price + tp_mult * a
                sl_price = entry_price - sl_mult * a
            else:
                tp_price = entry_price - tp_mult * a
                sl_price = entry_price + sl_mult * a
            in_trade = True

    return trades


def compute_metrics(trades: list) -> dict:
    """Compute strategy metrics from trade list."""
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "net_pnl_pct": 0, "max_drawdown_pct": 0, "sharpe": 0,
            "avg_bars_held": 0, "long_wr": 0, "short_wr": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    # Equity curve for drawdown
    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    drawdowns = running_max - equity
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0

    # Sharpe
    pnl_arr = np.array(pnls)
    sharpe = float(np.mean(pnl_arr) / np.std(pnl_arr)) if np.std(pnl_arr) > 0 else 0

    # Long / short breakdown
    long_trades = [t for t in trades if t["direction"] == 1]
    short_trades = [t for t in trades if t["direction"] == -1]
    long_wins = sum(1 for t in long_trades if t["pnl_pct"] > 0)
    short_wins = sum(1 for t in short_trades if t["pnl_pct"] > 0)

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_profit / gross_loss, 3),
        "net_pnl_pct": round(sum(pnls), 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 3),
        "avg_bars_held": round(np.mean([t["bars_held"] for t in trades]), 1),
        "long_wr": round(long_wins / len(long_trades) * 100, 2) if long_trades else 0,
        "short_wr": round(short_wins / len(short_trades) * 100, 2) if short_trades else 0,
    }

# ── Strategy signal generators ────────────────────────────────────────────────

def strategy_bb_squeeze(ohlcv: np.ndarray) -> tuple:
    """Strategy 1: Bollinger Band Squeeze Breakout.
    BB width normalized by mid-band; squeeze = width/mid < threshold for 5+ bars.
    Entry on first close outside BB after squeeze."""
    o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
    atr_arr = atr(h, l, c, 14)
    mid, upper, lower, width = bollinger_bands(c, 20, 2.0)

    # Normalize BB width by price level (percentage bandwidth)
    pct_bw = np.where(mid > 0, width / mid * 100, np.nan)

    # Compute median bandwidth for adaptive threshold
    valid_bw = pct_bw[~np.isnan(pct_bw)]
    if len(valid_bw) < 50:
        return [], "BB_Squeeze_Breakout"
    bw_median = np.median(valid_bw)
    squeeze_thresh = bw_median * 0.6  # squeeze = bandwidth < 60% of median

    signals = []
    squeeze_count = np.zeros(len(c))
    for i in range(1, len(c)):
        if not np.isnan(pct_bw[i]):
            if pct_bw[i] < squeeze_thresh:
                squeeze_count[i] = squeeze_count[i - 1] + 1
            else:
                squeeze_count[i] = 0

    in_squeeze_recently = False
    for i in range(5, len(c)):
        if np.isnan(upper[i]) or np.isnan(lower[i]) or np.isnan(atr_arr[i]):
            continue
        # Was in squeeze (5+ bars) in last 3 bars?
        was_squeezed = any(squeeze_count[max(0, i - j)] >= 5 for j in range(1, 4))
        currently_not_squeezed = squeeze_count[i] == 0
        if was_squeezed and currently_not_squeezed:
            if c[i] > upper[i]:
                signals.append((i, 1))
            elif c[i] < lower[i]:
                signals.append((i, -1))

    trades = simulate_trades(c, signals, atr_arr, tp_mult=2.0, sl_mult=1.0, max_hold=15)
    return trades, "BB_Squeeze_Breakout"


def strategy_ema_crossover_vol(ohlcv: np.ndarray) -> tuple:
    """Strategy 2: EMA Crossover with Volume Confirmation."""
    o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
    atr_arr = atr(h, l, c, 14)
    ema9 = ema(c, 9)
    ema21 = ema(c, 21)
    vol_sma20 = sma(v, 20)

    signals = []
    for i in range(1, len(c)):
        if np.isnan(ema9[i]) or np.isnan(ema21[i]) or np.isnan(ema9[i - 1]) or np.isnan(ema21[i - 1]):
            continue
        if np.isnan(vol_sma20[i]):
            continue
        vol_ok = v[i] > 1.5 * vol_sma20[i]
        if not vol_ok:
            continue
        # Bullish crossover
        if ema9[i - 1] <= ema21[i - 1] and ema9[i] > ema21[i]:
            signals.append((i, 1))
        # Bearish crossover
        elif ema9[i - 1] >= ema21[i - 1] and ema9[i] < ema21[i]:
            signals.append((i, -1))

    trades = simulate_trades(c, signals, atr_arr, tp_mult=2.5, sl_mult=1.5, max_hold=20)
    return trades, "EMA_Cross_Volume"


def strategy_macd_divergence(ohlcv: np.ndarray) -> tuple:
    """Strategy 3: MACD Histogram Divergence.
    Compares consecutive same-type MACD histogram waves for divergence."""
    o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
    atr_arr = atr(h, l, c, 14)
    _, _, hist = macd(c, 12, 26, 9)

    # Collect trough waves and peak waves separately
    troughs = []  # list of (bar, hist_val, price_at_bar)
    peaks = []

    # Find valid start
    start = 0
    for j in range(len(hist)):
        if not np.isnan(hist[j]):
            start = j
            break

    # Segment histogram by zero crosses
    wave_start = start
    for i in range(start + 1, len(hist)):
        if np.isnan(hist[i]):
            continue
        crossed = (hist[i] >= 0 and hist[i - 1] < 0) or (hist[i] < 0 and hist[i - 1] >= 0)
        is_last = (i == len(hist) - 1)
        if crossed or is_last:
            end = i if crossed else i + 1
            seg_h = hist[wave_start:end]
            seg_c = c[wave_start:end]
            if len(seg_h) >= 2:
                valid = ~np.isnan(seg_h)
                if np.any(valid):
                    if seg_h[valid][0] < 0:  # negative segment
                        idx = np.argmin(seg_h)
                        troughs.append((wave_start + idx, float(seg_h[idx]), float(np.min(seg_c))))
                    else:  # positive segment
                        idx = np.argmax(seg_h)
                        peaks.append((wave_start + idx, float(seg_h[idx]), float(np.max(seg_c))))
            if crossed:
                wave_start = i

    signals = []
    last_signal_bar = -10

    # Bullish divergence: consecutive troughs where price lower but hist higher
    for ti in range(1, len(troughs)):
        bar_prev, hist_prev, price_prev = troughs[ti - 1]
        bar_curr, hist_curr, price_curr = troughs[ti]
        if bar_curr - last_signal_bar < 5:
            continue
        if price_curr < price_prev and hist_curr > hist_prev:
            signals.append((bar_curr, 1))
            last_signal_bar = bar_curr

    # Bearish divergence: consecutive peaks where price higher but hist lower
    for pi in range(1, len(peaks)):
        bar_prev, hist_prev, price_prev = peaks[pi - 1]
        bar_curr, hist_curr, price_curr = peaks[pi]
        if bar_curr - last_signal_bar < 5:
            continue
        if price_curr > price_prev and hist_curr < hist_prev:
            signals.append((bar_curr, -1))
            last_signal_bar = bar_curr

    # Sort signals by bar index
    signals.sort(key=lambda x: x[0])

    trades = simulate_trades(c, signals, atr_arr, tp_mult=3.0, sl_mult=1.5, max_hold=20)
    return trades, "MACD_Divergence"


def strategy_stoch_rsi_trend(ohlcv: np.ndarray) -> tuple:
    """Strategy 4: Stochastic RSI Oversold/Overbought with Trend.
    Avoid re-entry within cooldown bars after a signal."""
    o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
    atr_arr = atr(h, l, c, 14)
    k_line, d_line = stoch_rsi(c, 14, 14, 3, 3)
    ema50 = ema(c, 50)

    signals = []
    cooldown = 0
    for i in range(50, len(c)):
        if np.isnan(k_line[i]) or np.isnan(ema50[i]):
            continue
        if cooldown > 0:
            cooldown -= 1
            continue
        # Oversold in uptrend
        if k_line[i] < 20 and c[i] > ema50[i]:
            signals.append((i, 1))
            cooldown = 5
        # Overbought in downtrend
        elif k_line[i] > 80 and c[i] < ema50[i]:
            signals.append((i, -1))
            cooldown = 5

    trades = simulate_trades(c, signals, atr_arr, tp_mult=1.5, sl_mult=1.0, max_hold=8)
    return trades, "StochRSI_Trend"


def strategy_keltner_adx(ohlcv: np.ndarray) -> tuple:
    """Strategy 5: Keltner Channel Breakout with ADX Filter."""
    o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
    atr_arr = atr(h, l, c, 14)
    ema20 = ema(c, 20)
    adx_val = adx(h, l, c, 14)

    kc_upper = ema20 + 1.5 * atr_arr
    kc_lower = ema20 - 1.5 * atr_arr

    signals = []
    for i in range(1, len(c)):
        if np.isnan(ema20[i]) or np.isnan(atr_arr[i]) or np.isnan(adx_val[i]):
            continue
        if adx_val[i] <= 25:
            continue
        # Breakout above upper Keltner
        if c[i - 1] <= kc_upper[i - 1] and c[i] > kc_upper[i]:
            signals.append((i, 1))
        # Breakout below lower Keltner
        elif c[i - 1] >= kc_lower[i - 1] and c[i] < kc_lower[i]:
            signals.append((i, -1))

    trades = simulate_trades(c, signals, atr_arr, tp_mult=2.0, sl_mult=1.0, max_hold=12)
    return trades, "Keltner_ADX"


# ── Main runner ───────────────────────────────────────────────────────────────

STRATEGIES = [
    strategy_bb_squeeze,
    strategy_ema_crossover_vol,
    strategy_macd_divergence,
    strategy_stoch_rsi_trend,
    strategy_keltner_adx,
]


def main():
    print("=" * 80)
    print("  MULTI-STRATEGY BACKTESTER  —  5 strategies x 10 symbols x 3 timeframes")
    print("=" * 80)
    print(f"  Symbols:    {', '.join(SYMBOLS)}")
    print(f"  Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"  Bars/req:   {LIMIT}")
    print(f"  Commission: {COMMISSION_PCT}% per side")
    print(f"  Started:    {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)
    print()

    all_results = []
    total_combos = len(SYMBOLS) * len(TIMEFRAMES)
    combo_num = 0

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            combo_num += 1
            print(f"[{combo_num}/{total_combos}] Fetching {symbol} {tf} ...", end=" ", flush=True)

            ohlcv = fetch_klines(symbol, tf, LIMIT)
            if ohlcv is None:
                print("FAILED (no data)")
                continue

            print(f"got {len(ohlcv)} bars. Running strategies ...", flush=True)

            for strat_fn in STRATEGIES:
                try:
                    trades, strat_name = strat_fn(ohlcv)
                    metrics = compute_metrics(trades)
                    metrics["strategy"] = strat_name
                    metrics["symbol"] = symbol
                    metrics["timeframe"] = tf
                    all_results.append(metrics)

                    wr = metrics["win_rate"]
                    pf = metrics["profit_factor"]
                    nt = metrics["total_trades"]
                    pnl = metrics["net_pnl_pct"]
                    print(f"    {strat_name:25s}  trades={nt:4d}  WR={wr:5.1f}%  PF={pf:6.3f}  PnL={pnl:+7.2f}%")
                except Exception as e:
                    print(f"    {strat_fn.__name__:25s}  ERROR: {e}")
                    traceback.print_exc()

            # Rate-limit to avoid Binance 429
            time.sleep(0.3)

    # ── Save results ──────────────────────────────────────────────────────────
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {RESULTS_FILE}")

    # ── Ranked table: PF > 1.0  and  trades >= 10 ────────────────────────────
    qualified = [r for r in all_results if r["profit_factor"] > 1.0 and r["total_trades"] >= 10]
    qualified.sort(key=lambda x: x["profit_factor"], reverse=True)

    print("\n" + "=" * 120)
    print("  RANKED TABLE  —  PF > 1.0  AND  Trades >= 10   (sorted by Profit Factor)")
    print("=" * 120)
    header = (f"{'Rank':>4s}  {'Strategy':25s}  {'Symbol':10s}  {'TF':4s}  "
              f"{'Trades':>6s}  {'WR%':>6s}  {'PF':>7s}  {'PnL%':>8s}  "
              f"{'MaxDD%':>7s}  {'Sharpe':>7s}  {'AvgBars':>7s}  {'LongWR':>6s}  {'ShortWR':>7s}")
    print(header)
    print("-" * 120)

    for rank, r in enumerate(qualified, 1):
        row = (f"{rank:4d}  {r['strategy']:25s}  {r['symbol']:10s}  {r['timeframe']:4s}  "
               f"{r['total_trades']:6d}  {r['win_rate']:6.1f}  {r['profit_factor']:7.3f}  "
               f"{r['net_pnl_pct']:+8.2f}  {r['max_drawdown_pct']:7.2f}  {r['sharpe']:7.3f}  "
               f"{r['avg_bars_held']:7.1f}  {r['long_wr']:6.1f}  {r['short_wr']:7.1f}")
        print(row)

    if not qualified:
        print("  (no combos meet the criteria)")

    # ── RECOMMENDED section ───────────────────────────────────────────────────
    recommended = [r for r in all_results
                   if r["win_rate"] > 50 and r["profit_factor"] > 1.2 and r["total_trades"] >= 15]
    recommended.sort(key=lambda x: x["profit_factor"], reverse=True)

    print("\n" + "=" * 120)
    print("  RECOMMENDED  —  WR > 50%  AND  PF > 1.2  AND  Trades >= 15")
    print("=" * 120)
    print(header)
    print("-" * 120)

    for rank, r in enumerate(recommended, 1):
        row = (f"{rank:4d}  {r['strategy']:25s}  {r['symbol']:10s}  {r['timeframe']:4s}  "
               f"{r['total_trades']:6d}  {r['win_rate']:6.1f}  {r['profit_factor']:7.3f}  "
               f"{r['net_pnl_pct']:+8.2f}  {r['max_drawdown_pct']:7.2f}  {r['sharpe']:7.3f}  "
               f"{r['avg_bars_held']:7.1f}  {r['long_wr']:6.1f}  {r['short_wr']:7.1f}")
        print(row)

    if not recommended:
        print("  (no combos meet the RECOMMENDED criteria)")

    # ── Summary stats ─────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"  Total combos tested:     {len(all_results)}")
    print(f"  Profitable (PF>1):       {sum(1 for r in all_results if r['profit_factor'] > 1.0)}")
    print(f"  Qualified (PF>1, N>=10): {len(qualified)}")
    print(f"  Recommended:             {len(recommended)}")

    if qualified:
        best = qualified[0]
        print(f"\n  BEST COMBO: {best['strategy']} | {best['symbol']} | {best['timeframe']}")
        print(f"    PF={best['profit_factor']:.3f}  WR={best['win_rate']:.1f}%  "
              f"PnL={best['net_pnl_pct']:+.2f}%  Trades={best['total_trades']}")

    print(f"\n  Finished: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)


if __name__ == "__main__":
    main()

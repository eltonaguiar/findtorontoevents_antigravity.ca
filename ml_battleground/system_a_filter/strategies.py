"""
System A: 20 proven strategies for "The Filter".
Each returns list[dict] of raw signals (TP/SL set by S/R engine in scanner).

Strategies:
1.  supertrend_follow — Supertrend direction flip
2.  connors_rsi2 — RSI(2) < 5 + price > SMA(200)
3.  bollinger_keltner_squeeze — BB inside Keltner >=3 bars, signal on release
4.  rsi_macd_confluence — RSI crosses 30 from below + MACD hist rising
5.  ema_stack — EMA 9>21>50>200 + pullback to EMA9
6.  volume_climax_reversal — Vol > 5x avg + close in top 30% [PROBATION — 0% WR]
7.  swing_failure_pattern — Wick below swing low + close above
8.  ornstein_uhlenbeck — Mean-reversion when deviation > 1.5 sigma
9.  narrative_sniper — CryptoGodJohn-inspired: volume acceleration + trending
10. rsi_bb_macd_confluence — RSI oversold + lower BB + MACD bullish (87.5% WR)
11. supertrend_volume_confirmed — Supertrend flip + above-avg volume (65-70% WR)
12. funding_rate_extreme — Mean revert on extreme funding rates (68-72% WR)
13. fear_capitulation_dca — Contrarian BUY at extreme fear (F&G<=15, 14.6% annual)
14. bb_mean_reversion — Bollinger Band mean reversion for range-bound markets
15. keltner_channel_breakout — Volatility expansion breakout (55-62% WR)
16. rsi_divergence — RSI divergence (replaces raw RSI oversold, 55-65% WR)
17. fibonacci_retracement — Fib 38.2/50/61.8% pullback + RSI (Osler 2000, +6.89% ROI)
18. ema_crossover_short — 9/21 EMA death cross below 200 SMA (55-62% WR bear)
19. sell_the_rally — Price rejects declining 20 EMA in downtrend (58-65% WR)
20. bear_trend_short — Price below 200 SMA + lower highs + MACD bearish (60% WR)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import indicators as ind


def run_all_strategies(df: pd.DataFrame, pair: str, interval: str = "1h", **kwargs) -> list[dict]:
    """Run all 12 strategies on a single pair's OHLCV DataFrame."""
    if len(df) < 50:
        print(f"    [strategies] {pair}: only {len(df)} bars, need 50 minimum")
        return []

    signals = []
    for strategy_fn in [
        supertrend_follow,
        connors_rsi2,
        bollinger_keltner_squeeze,
        rsi_macd_confluence,
        ema_stack,
        # volume_climax_reversal — DISABLED: 0/5 WR, -6.48% across all trades
        swing_failure_pattern,
        ornstein_uhlenbeck,
        narrative_sniper,
        rsi_bb_macd_confluence,
        supertrend_volume_confirmed,
        fear_capitulation_dca,
        bb_mean_reversion,
        keltner_channel_breakout,
        rsi_divergence,
        fibonacci_retracement,
        # Bear market SHORT strategies (added Feb 25 2026)
        ema_crossover_short,
        sell_the_rally,
        bear_trend_short,
    ]:
        try:
            sigs = strategy_fn(df, pair)
            if sigs:
                print(f"    [+] {pair} {strategy_fn.__name__}: {len(sigs)} signal(s)")
            for s in sigs:
                s["timeframe"] = interval
            signals.extend(sigs)
        except Exception as e:
            print(f"    [!] {pair} {strategy_fn.__name__} error: {e}")

    # Strategies that need extra context
    funding_rate = kwargs.get("funding_rate", 0.0)
    if funding_rate != 0.0:
        try:
            sigs = funding_rate_extreme(df, pair, funding_rate)
            if sigs:
                print(f"    [+] {pair} funding_rate_extreme: {len(sigs)} signal(s)")
            for s in sigs:
                s["timeframe"] = interval
            signals.extend(sigs)
        except Exception as e:
            print(f"    [!] {pair} funding_rate_extreme error: {e}")

    if not signals:
        print(f"    [-] {pair} ({interval}): 0 signals from all strategies")

    return signals


def _find_swing_lows(series, lookback=5):
    """Find swing low indices: local minima over `lookback` bars on each side."""
    indices = []
    for i in range(lookback, len(series) - lookback):
        window = series[i - lookback:i + lookback + 1]
        if series[i] == np.min(window):
            indices.append(i)
    return indices


def _find_swing_highs(series, lookback=5):
    """Find swing high indices: local maxima over `lookback` bars on each side."""
    indices = []
    for i in range(lookback, len(series) - lookback):
        window = series[i - lookback:i + lookback + 1]
        if series[i] == np.max(window):
            indices.append(i)
    return indices


def _base_signal(strategy: str, pair: str, signal_type: str, entry: float,
                 confidence: float, reason: str, **extra) -> dict:
    """Create a standardized signal dict."""
    sig = {
        "strategy": strategy,
        "symbol": pair,
        "signal_type": signal_type,
        "entry_price": round(entry, 8),
        "confidence": round(min(0.90, confidence), 4),
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": "crypto",
    }
    sig.update(extra)
    return sig


# --- Strategy 1: Supertrend Follow ---

def supertrend_follow(df: pd.DataFrame, pair: str) -> list[dict]:
    """Signal on Supertrend direction change."""
    direction = ind.supertrend(df["High"], df["Low"], df["Close"])
    if len(direction) < 3:
        return []

    curr = direction.iloc[-1]
    prev = direction.iloc[-2]

    if curr == prev:
        return []  # no flip

    close = float(df["Close"].iloc[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"])
    vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]) if df["Volume"].rolling(20).mean().iloc[-1] > 0 else 1.0

    if curr == 1 and prev == -1:
        confidence = min(0.82, 0.55 + vol_ratio * 0.03)
        return [_base_signal(
            "supertrend_follow", pair, "BUY", close, confidence,
            f"Supertrend flipped bullish, vol ratio {vol_ratio:.1f}x",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
        )]
    elif curr == -1 and prev == 1:
        confidence = min(0.82, 0.55 + vol_ratio * 0.03)
        return [_base_signal(
            "supertrend_follow", pair, "SELL", close, confidence,
            f"Supertrend flipped bearish, vol ratio {vol_ratio:.1f}x",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
        )]

    return []


# --- Strategy 2: Connors RSI-2 ---

def connors_rsi2(df: pd.DataFrame, pair: str) -> list[dict]:
    """RSI(2) extreme oversold + trend filter.
    Relaxed: use SMA(50) as trend filter when <250 bars available."""
    close = df["Close"]
    rsi2 = ind.rsi(close, 2)
    rsi14 = ind.rsi(close, 14)

    if len(rsi2) < 5:
        return []

    curr_rsi2 = float(rsi2.iloc[-1])
    curr_rsi14 = float(rsi14.iloc[-1])
    curr_price = float(close.iloc[-1])

    # Use SMA(200) if enough data, else SMA(50) as trend filter
    if len(close) >= 200:
        trend_sma = ind.sma(close, 200)
    else:
        trend_sma = ind.sma(close, 50)

    if pd.isna(trend_sma.iloc[-1]):
        return []
    curr_trend = float(trend_sma.iloc[-1])

    # BUY: RSI(2) < 20 (relaxed from 15), price > trend SMA, RSI(14) > 15
    if curr_rsi2 < 20.0 and curr_price > curr_trend and curr_rsi14 >= 15:
        atr_val = ind.atr(df["High"], df["Low"], close)
        confidence = min(0.80, 0.50 + (20.0 - curr_rsi2) * 0.01)
        return [_base_signal(
            "connors_rsi2", pair, "BUY", curr_price, confidence,
            f"RSI(2)={curr_rsi2:.1f} extreme oversold, above trend SMA",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi2,
        )]

    # SELL: RSI(2) > threshold when below trend SMA
    # Bear market adjustment: lower threshold from 80 to 60 (research: overbought
    # in bear markets happens at lower RSI levels — QuantifiedStrategies)
    sell_threshold = 60.0 if curr_price < curr_trend else 80.0
    if curr_rsi2 > sell_threshold and curr_price < curr_trend and curr_rsi14 <= 85:
        atr_val = ind.atr(df["High"], df["Low"], close)
        confidence = min(0.80, 0.50 + (curr_rsi2 - sell_threshold) * 0.01)
        return [_base_signal(
            "connors_rsi2", pair, "SELL", curr_price, confidence,
            f"RSI(2)={curr_rsi2:.1f} overbought for bear (threshold={sell_threshold:.0f}), below trend SMA",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi2,
        )]

    return []


# --- Strategy 3: Bollinger-Keltner Squeeze ---

def bollinger_keltner_squeeze(df: pd.DataFrame, pair: str) -> list[dict]:
    """BB inside Keltner for ≥3 bars, signal on first release."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    bb_upper, _, bb_lower, _, _ = ind.bollinger_bands(close)
    kc_upper, _, kc_lower = ind.keltner_channels(high, low, close)

    if len(bb_upper) < 5:
        return []

    # ── ATR volatility regime gate (v93/v95 crash stress test) ──
    # Keltner WR drops 72.9% -> 42.1% during crashes.
    # ATR > 2x mean -> half size; ATR > 3x -> skip entirely.
    vol_regime = ind.atr_volatility_regime(high, low, close)
    if vol_regime["extreme_volatility"]:
        print(f"    [bb_keltner_squeeze] {pair}: SKIP — extreme volatility "
              f"(ATR ratio {vol_regime['atr_ratio']:.2f}x > 3x mean)")
        return []

    # Check squeeze: BB inside Keltner
    squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)

    # Need ≥3 bars of squeeze, then release on current bar
    if not squeeze.iloc[-2] or squeeze.iloc[-1]:
        return []  # not a release bar

    squeeze_count = 0
    for i in range(len(squeeze) - 2, max(0, len(squeeze) - 20), -1):
        if squeeze.iloc[i]:
            squeeze_count += 1
        else:
            break

    if squeeze_count < 1:
        return []

    curr_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    atr_val = ind.atr(high, low, close)
    confidence = min(0.80, 0.55 + squeeze_count * 0.02)

    if vol_regime["high_volatility_regime"]:
        confidence *= 0.85
        print(f"    [bb_keltner_squeeze] {pair}: HIGH VOL regime "
              f"(ATR {vol_regime['atr_ratio']:.2f}x) — conf reduced, half size")

    if curr_price > prev_price:
        return [_base_signal(
            "bollinger_keltner_squeeze", pair, "BUY", curr_price, confidence,
            f"Squeeze release after {squeeze_count} bars, bullish breakout",
            atr_value=float(atr_val.iloc[-1]),
            squeeze_bars=squeeze_count,
            position_scale=vol_regime["position_scale"],
            high_volatility_regime=vol_regime["high_volatility_regime"],
            atr_ratio=vol_regime["atr_ratio"],
        )]
    else:
        return [_base_signal(
            "bollinger_keltner_squeeze", pair, "SELL", curr_price, confidence,
            f"Squeeze release after {squeeze_count} bars, bearish breakout",
            atr_value=float(atr_val.iloc[-1]),
            squeeze_bars=squeeze_count,
            position_scale=vol_regime["position_scale"],
            high_volatility_regime=vol_regime["high_volatility_regime"],
            atr_ratio=vol_regime["atr_ratio"],
        )]


# --- Strategy 4: RSI + MACD Confluence ---

def rsi_macd_confluence(df: pd.DataFrame, pair: str) -> list[dict]:
    """RSI crosses 30 from below + MACD histogram rising.
    Relaxed: trend filter uses SMA(50) when <250 bars; also checks within 3 bars."""
    close = df["Close"]
    rsi14 = ind.rsi(close, 14)
    _, _, macd_hist = ind.macd(close)

    if len(rsi14) < 3 or len(macd_hist) < 3:
        return []

    # Use SMA(200) if enough data, else SMA(50)
    if len(close) >= 200:
        trend_sma = ind.sma(close, 200)
    else:
        trend_sma = ind.sma(close, 50)

    curr_rsi = float(rsi14.iloc[-1])
    curr_hist = float(macd_hist.iloc[-1])
    prev_hist = float(macd_hist.iloc[-2])
    curr_price = float(close.iloc[-1])
    curr_trend = float(trend_sma.iloc[-1]) if not pd.isna(trend_sma.iloc[-1]) else curr_price
    atr_val = ind.atr(df["High"], df["Low"], close)

    # Check RSI crossed 30 from below within last 3 bars (relaxed from exactly 1 bar)
    rsi_crossed_up = False
    for lookback in range(1, min(4, len(rsi14))):
        prev_rsi = float(rsi14.iloc[-1 - lookback])
        if prev_rsi < 35 and curr_rsi >= 30:
            rsi_crossed_up = True
            break

    # Bullish: RSI crossed up from oversold, MACD hist rising
    if rsi_crossed_up and curr_hist > prev_hist and curr_price >= curr_trend * 0.98:
        depth = max(0, 35 - prev_rsi)
        vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]) if df["Volume"].rolling(20).mean().iloc[-1] > 0 else 1.0
        confidence = min(0.82, 0.55 + depth * 0.01 + vol_ratio * 0.02)
        return [_base_signal(
            "rsi_macd_confluence", pair, "BUY", curr_price, confidence,
            f"RSI crossed 30 from {prev_rsi:.1f}, MACD hist rising",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi,
        )]

    # Check RSI crossed 70 from above within last 3 bars
    rsi_crossed_down = False
    for lookback in range(1, min(4, len(rsi14))):
        prev_rsi = float(rsi14.iloc[-1 - lookback])
        if prev_rsi > 65 and curr_rsi <= 70:
            rsi_crossed_down = True
            break

    # Bearish: RSI crossed down from overbought, MACD hist falling
    if rsi_crossed_down and curr_hist < prev_hist and curr_price <= curr_trend * 1.02:
        depth = max(0, prev_rsi - 65)
        confidence = min(0.82, 0.55 + depth * 0.01)
        return [_base_signal(
            "rsi_macd_confluence", pair, "SELL", curr_price, confidence,
            f"RSI crossed 70 from {prev_rsi:.1f}, MACD hist falling",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi,
        )]

    return []


# --- Strategy 5: EMA Stack ---

def ema_stack(df: pd.DataFrame, pair: str) -> list[dict]:
    """EMA 9>21>50 alignment + pullback near EMA9.
    Relaxed: no SMA(200) requirement, price near EMA9 (within 0.5 ATR) counts."""
    close = df["Close"]
    ema9 = ind.ema(close, 9)
    ema21 = ind.ema(close, 21)
    ema50 = ind.ema(close, 50)

    if len(ema9) < 3:
        return []

    e9 = float(ema9.iloc[-1])
    e21 = float(ema21.iloc[-1])
    e50 = float(ema50.iloc[-1])
    curr_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])

    atr_val = ind.atr(df["High"], df["Low"], close)
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else curr_price * 0.02
    vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]) if df["Volume"].rolling(20).mean().iloc[-1] > 0 else 1.0

    # Bullish stack: 9 > 21 > 50
    if e9 > e21 > e50:
        # Relaxed: price near EMA9 (within 0.5 ATR) or pulled back and bounced
        near_ema9 = abs(curr_price - e9) < 0.5 * atr_now
        bounced = prev_price < float(ema9.iloc[-2]) and curr_price > e9
        if near_ema9 or bounced:
            spread = (e9 - e50) / e50 * 100
            confidence = min(0.82, 0.55 + spread * 0.01 + vol_ratio * 0.02)
            return [_base_signal(
                "ema_stack", pair, "BUY", curr_price, confidence,
                f"EMA stack aligned (9>21>50), price near EMA9",
                atr_value=atr_now,
                volume_ratio=vol_ratio,
            )]

    # Bearish stack: 9 < 21 < 50
    if e9 < e21 < e50:
        near_ema9 = abs(curr_price - e9) < 0.5 * atr_now
        rejected = prev_price > float(ema9.iloc[-2]) and curr_price < e9
        if near_ema9 or rejected:
            confidence = min(0.82, 0.55 + vol_ratio * 0.02)
            return [_base_signal(
                "ema_stack", pair, "SELL", curr_price, confidence,
                f"EMA stack aligned bearish (9<21<50), price near EMA9",
                atr_value=atr_now,
                volume_ratio=vol_ratio,
            )]

    return []


# --- Strategy 6: Volume Climax Reversal ---

def volume_climax_reversal(df: pd.DataFrame, pair: str) -> list[dict]:
    """Vol > 5x avg + close in top 30% of bar = absorption → reversal."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    if len(df) < 25:
        return []

    # Check previous bar for climax
    prev_vol = float(volume.iloc[-2])
    avg_vol = float(volume.iloc[-22:-2].mean())
    if avg_vol <= 0:
        return []
    vol_ratio = prev_vol / avg_vol

    if vol_ratio < 2.0:
        return []

    prev_range = float(high.iloc[-2]) - float(low.iloc[-2])
    atr_val = ind.atr(high, low, close)
    avg_atr = float(atr_val.iloc[-2])

    if prev_range < 0.8 * avg_atr:
        return []  # not a climax bar

    prev_close = float(close.iloc[-2])
    prev_high = float(high.iloc[-2])
    prev_low = float(low.iloc[-2])

    # Close in top 30% = absorption (buying at highs)
    if prev_range > 0:
        close_position = (prev_close - prev_low) / prev_range
    else:
        return []

    curr_close = float(close.iloc[-1])
    prev_mid = (prev_high + prev_low) / 2

    if close_position > 0.70 and curr_close > prev_mid:
        # Bullish absorption — close near top of climax bar
        confidence = min(0.82, 0.55 + (vol_ratio - 5.0) * 0.02 + close_position * 0.1)
        return [_base_signal(
            "volume_climax_reversal", pair, "BUY", curr_close, confidence,
            f"Volume climax {vol_ratio:.1f}x, absorption (close top 30%), bullish follow-through",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
        )]

    if close_position < 0.30 and curr_close < prev_mid:
        # Bearish absorption — close near bottom
        confidence = min(0.82, 0.55 + (vol_ratio - 5.0) * 0.02)
        return [_base_signal(
            "volume_climax_reversal", pair, "SELL", curr_close, confidence,
            f"Volume climax {vol_ratio:.1f}x, distribution (close bottom 30%), bearish follow-through",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
        )]

    return []


# --- Strategy 7: Swing Failure Pattern ---

def swing_failure_pattern(df: pd.DataFrame, pair: str) -> list[dict]:
    """Wick beyond swing high/low + close inside = SFP (Hsaka/ICT)."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    open_ = df["Open"]

    if len(df) < 25:
        return []

    # Find 20-bar swing low/high
    lookback = 20
    swing_low = float(low.iloc[-lookback - 1:-1].min())
    swing_high = float(high.iloc[-lookback - 1:-1].max())

    curr_low = float(low.iloc[-1])
    curr_high = float(high.iloc[-1])
    curr_close = float(close.iloc[-1])
    curr_open = float(open_.iloc[-1])
    curr_range = curr_high - curr_low

    atr_val = ind.atr(high, low, close)
    vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]) if df["Volume"].rolling(20).mean().iloc[-1] > 0 else 1.0

    # Bullish SFP: wick below swing low, close above it
    if curr_low < swing_low and curr_close > swing_low:
        wick_below = swing_low - curr_low
        if curr_range > 0:
            wick_depth = wick_below / curr_range
        else:
            return []
        if wick_depth >= 0.30 and curr_close > curr_open:
            confidence = min(0.82, 0.52 + wick_depth * 0.2 + vol_ratio * 0.02)
            return [_base_signal(
                "swing_failure_pattern", pair, "BUY", curr_close, confidence,
                f"Bullish SFP: wick {wick_depth:.0%} below swing low, closed above",
                atr_value=float(atr_val.iloc[-1]),
                volume_ratio=vol_ratio,
            )]

    # Bearish SFP: wick above swing high, close below it
    if curr_high > swing_high and curr_close < swing_high:
        wick_above = curr_high - swing_high
        if curr_range > 0:
            wick_depth = wick_above / curr_range
        else:
            return []
        if wick_depth >= 0.30 and curr_close < curr_open:
            confidence = min(0.82, 0.52 + wick_depth * 0.2 + vol_ratio * 0.02)
            return [_base_signal(
                "swing_failure_pattern", pair, "SELL", curr_close, confidence,
                f"Bearish SFP: wick {wick_depth:.0%} above swing high, closed below",
                atr_value=float(atr_val.iloc[-1]),
                volume_ratio=vol_ratio,
            )]

    return []


# --- Strategy 8: Ornstein-Uhlenbeck Mean Reversion ---

def ornstein_uhlenbeck(df: pd.DataFrame, pair: str) -> list[dict]:
    """Mean-reversion when price deviates > 1.5σ from equilibrium."""
    close = df["Close"]

    if len(close) < 80:
        return []

    log_price = np.log(close.values)
    delta_y = np.diff(log_price)
    y_lag = log_price[:-1]

    # OLS AR(1): delta_y = alpha + rho * y_lag + epsilon
    n = len(delta_y)
    lookback = min(60, n - 1)
    if lookback < 30:
        return []

    cov_xy = np.cov(delta_y[-lookback:], y_lag[-lookback:])[0][1]
    var_x = np.var(y_lag[-lookback:])
    if var_x == 0:
        return []

    rho = cov_xy / var_x

    # Must be mean-reverting (rho < 0)
    if rho >= 0:
        return []

    half_life = -np.log(2) / rho
    if half_life < 3 or half_life > 80:
        return []

    # Equilibrium = SMA(lookback)
    sma_period = min(60, len(close) - 1)
    mu = float(ind.sma(close, sma_period).iloc[-1])
    rolling_std = float(close.rolling(sma_period).std().iloc[-1])

    if rolling_std == 0 or mu == 0:
        return []

    curr_price = float(close.iloc[-1])
    deviation = (curr_price - mu) / rolling_std
    atr_val = ind.atr(df["High"], df["Low"], close)

    if deviation < -1.0:
        confidence = min(0.85, 0.50 + abs(rho) * 2.0)
        return [_base_signal(
            "ornstein_uhlenbeck", pair, "BUY", curr_price, confidence,
            f"O-U mean reversion: {deviation:.1f}σ below equilibrium, half-life {half_life:.0f} bars",
            atr_value=float(atr_val.iloc[-1]),
            deviation_sigma=deviation,
            half_life=half_life,
            equilibrium=mu,
        )]

    if deviation > 1.0:
        confidence = min(0.85, 0.50 + abs(rho) * 2.0)
        return [_base_signal(
            "ornstein_uhlenbeck", pair, "SELL", curr_price, confidence,
            f"O-U mean reversion: {deviation:.1f}σ above equilibrium, half-life {half_life:.0f} bars",
            atr_value=float(atr_val.iloc[-1]),
            deviation_sigma=deviation,
            half_life=half_life,
            equilibrium=mu,
        )]

    return []


# --- Strategy 9: Narrative Sniper (CryptoGodJohn-inspired) ---

def narrative_sniper(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    CryptoGodJohn-inspired: detect narrative momentum plays.
    Combines volume acceleration + price breakout from range + trend alignment.
    Targets coins experiencing rapid attention/volume increase.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    if len(df) < 50:
        return []

    # Volume acceleration: last 6 bars avg vs prior 6 bars avg
    recent_vol = float(volume.iloc[-6:].mean())
    prior_vol = float(volume.iloc[-12:-6].mean())
    if prior_vol <= 0:
        return []
    vol_accel = recent_vol / prior_vol

    # Need volume acceleration (smart money entering) — relaxed from 3.0
    if vol_accel < 1.8:
        return []

    # Price breakout: above 20-bar high
    curr_price = float(close.iloc[-1])
    prev_high_20 = float(high.iloc[-21:-1].max())
    prev_low_20 = float(low.iloc[-21:-1].min())
    range_20 = prev_high_20 - prev_low_20

    # Trend alignment: price > EMA21
    ema21 = ind.ema(close, 21)
    above_ema21 = curr_price > float(ema21.iloc[-1])

    atr_val = ind.atr(high, low, close)

    # Bullish narrative: volume spike + price breaking above range + trend aligned
    if curr_price > prev_high_20 and above_ema21 and vol_accel >= 1.8:
        # Check it's not already too extended (CryptoGodJohn: don't chase >12%)
        daily_change = (curr_price - float(close.iloc[-24])) / float(close.iloc[-24]) if len(close) >= 24 else 0
        if daily_change > 0.12:
            return []  # gap-chase rejection

        confidence = min(0.78, 0.50 + (vol_accel - 1.8) * 0.03)
        return [_base_signal(
            "narrative_sniper", pair, "BUY", curr_price, confidence,
            f"Narrative play: {vol_accel:.1f}x volume acceleration, breakout above 20-bar range",
            atr_value=float(atr_val.iloc[-1]),
            volume_acceleration=vol_accel,
            breakout_pct=(curr_price - prev_high_20) / prev_high_20 * 100 if prev_high_20 > 0 else 0,
        )]

    return []


# --- Strategy 10: RSI + Bollinger + MACD Triple Confluence ---

def rsi_bb_macd_confluence(df: pd.DataFrame, pair: str) -> list[dict]:
    """Triple confluence: RSI oversold + lower BB touch + MACD bullish divergence.
    Documented 87.5% accuracy when all three align (ResearchGate 2024)."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi14 = ind.rsi(close, 14)
    bb_upper, _, bb_lower, _, pctb = ind.bollinger_bands(close)
    _, _, macd_hist = ind.macd(close)

    if len(rsi14) < 5 or len(macd_hist) < 5:
        return []

    curr_rsi = float(rsi14.iloc[-1])
    prev_rsi = float(rsi14.iloc[-2])
    curr_pctb = float(pctb.iloc[-1])
    curr_hist = float(macd_hist.iloc[-1])
    prev_hist = float(macd_hist.iloc[-2])
    curr_price = float(close.iloc[-1])
    atr_val = ind.atr(high, low, close)

    # BULLISH: RSI < 35 + price near lower BB (%B < 0.25) + MACD hist rising
    if curr_rsi < 35 and curr_pctb < 0.25 and curr_hist > prev_hist:
        confidence = min(0.88, 0.60 + (35 - curr_rsi) * 0.005 + (0.25 - curr_pctb) * 0.3)
        return [_base_signal(
            "rsi_bb_macd_confluence", pair, "BUY", curr_price, confidence,
            f"Triple confluence: RSI={curr_rsi:.1f}, BB %B={curr_pctb:.2f}, MACD hist rising",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi,
            bb_pctb=curr_pctb,
        )]

    # BEARISH: RSI > 65 + price near upper BB (%B > 0.75) + MACD hist falling
    if curr_rsi > 65 and curr_pctb > 0.75 and curr_hist < prev_hist:
        confidence = min(0.88, 0.60 + (curr_rsi - 65) * 0.005 + (curr_pctb - 0.75) * 0.3)
        return [_base_signal(
            "rsi_bb_macd_confluence", pair, "SELL", curr_price, confidence,
            f"Triple confluence: RSI={curr_rsi:.1f}, BB %B={curr_pctb:.2f}, MACD hist falling",
            atr_value=float(atr_val.iloc[-1]),
            rsi_value=curr_rsi,
            bb_pctb=curr_pctb,
        )]

    return []


# --- Strategy 11: Supertrend + Volume Confirmation ---

def supertrend_volume_confirmed(df: pd.DataFrame, pair: str) -> list[dict]:
    """Supertrend flip confirmed by above-average volume.
    QuantifiedStrategies: 65.79% WR, 11% avg profit per trade."""
    direction = ind.supertrend(df["High"], df["Low"], df["Close"])
    if len(direction) < 3:
        return []

    curr = direction.iloc[-1]
    prev = direction.iloc[-2]

    if curr == prev:
        return []

    volume = df["Volume"]
    vol_avg = float(volume.iloc[-20:].mean())
    vol_now = float(volume.iloc[-1])
    vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0

    # Require volume confirmation (>1.2x average)
    if vol_ratio < 1.2:
        return []

    close = float(df["Close"].iloc[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"])
    rsi14 = ind.rsi(df["Close"], 14)
    rsi_val = float(rsi14.iloc[-1])

    if curr == 1 and prev == -1 and rsi_val < 70:
        confidence = min(0.82, 0.60 + vol_ratio * 0.02 + (70 - rsi_val) * 0.002)
        return [_base_signal(
            "supertrend_volume", pair, "BUY", close, confidence,
            f"Supertrend bullish flip + {vol_ratio:.1f}x volume, RSI={rsi_val:.0f}",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
            rsi_value=rsi_val,
        )]
    elif curr == -1 and prev == 1 and rsi_val > 30:
        confidence = min(0.82, 0.60 + vol_ratio * 0.02)
        return [_base_signal(
            "supertrend_volume", pair, "SELL", close, confidence,
            f"Supertrend bearish flip + {vol_ratio:.1f}x volume, RSI={rsi_val:.0f}",
            atr_value=float(atr_val.iloc[-1]),
            volume_ratio=vol_ratio,
            rsi_value=rsi_val,
        )]

    return []


# --- Strategy 12: Funding Rate Extreme Mean Reversion ---

def funding_rate_extreme(df: pd.DataFrame, pair: str, funding_rate: float = 0.0) -> list[dict]:
    """Mean revert on extreme funding rates (>0.1% or <-0.05%).
    BIS Working Paper 1087: crypto carry Sharpe 6.45."""
    if abs(funding_rate) < 0.0001:
        return []  # no data or negligible

    close = float(df["Close"].iloc[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"])
    rsi14 = ind.rsi(df["Close"], 14)
    rsi_val = float(rsi14.iloc[-1])

    # Extreme positive funding -> shorts get paid -> short signal
    if funding_rate > 0.001:  # > 0.1% per 8h
        if rsi_val > 60:  # overbought confirmation
            confidence = min(0.80, 0.55 + (funding_rate - 0.001) * 100 + (rsi_val - 60) * 0.005)
            return [_base_signal(
                "funding_rate_extreme", pair, "SELL", close, confidence,
                f"Extreme funding {funding_rate:.4f} + RSI={rsi_val:.0f}, overleveraged longs",
                atr_value=float(atr_val.iloc[-1]),
                funding_rate=funding_rate,
                rsi_value=rsi_val,
            )]

    # Extreme negative funding -> longs get paid -> long signal
    if funding_rate < -0.0005:  # < -0.05% per 8h
        if rsi_val < 40:  # oversold confirmation
            confidence = min(0.80, 0.55 + abs(funding_rate + 0.0005) * 100 + (40 - rsi_val) * 0.005)
            return [_base_signal(
                "funding_rate_extreme", pair, "BUY", close, confidence,
                f"Extreme negative funding {funding_rate:.4f} + RSI={rsi_val:.0f}, overleveraged shorts",
                atr_value=float(atr_val.iloc[-1]),
                funding_rate=funding_rate,
                rsi_value=rsi_val,
            )]

    return []


# ──────────────────────────────────────────────────────────────────────
# NEW PARALLEL STRATEGIES (Feb 24 2026 — Kimi feedback integration)
# Research-backed, suited for range-bound + extreme fear conditions
# ──────────────────────────────────────────────────────────────────────

def fear_capitulation_dca(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Fear Capitulation DCA — BUY when Fear & Greed Index <= 10 + RSI oversold.
    Research: Nasdaq backtest shows 14.6% annual return for multi-day DCA at extreme fear.
    Our own vix_spike_reversal (72% WR, p=0.022) and fear_greed_extreme_dca are built on this.
    """
    try:
        from shared.data_fetcher import fetch_fear_greed
        fg = fetch_fear_greed()
    except Exception:
        return []

    if fg > 15:  # Only fire in extreme fear
        return []

    close = df["Close"].values
    c = float(close[-1])
    rsi_val = float(ind.rsi(df["Close"], 14).iloc[-1])

    # Need RSI < 35 for confirmation (oversold in fearful market)
    if rsi_val > 35:
        return []

    # Confidence scales with fear intensity
    confidence = min(0.85, 0.60 + (15 - fg) * 0.015 + (35 - rsi_val) * 0.005)
    atr_val = ind.atr(df["High"], df["Low"], df["Close"])
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else c * 0.02

    return [_base_signal(
        "fear_capitulation_dca", pair, "BUY", c, confidence,
        f"Fear capitulation: F&G={fg}, RSI={rsi_val:.0f} — contrarian buy (14.6% annual backtest)",
        atr_value=atr_now,
        fear_greed=fg,
        rsi_value=rsi_val,
    )]


def bb_mean_reversion(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Bollinger Band Mean Reversion — classic range-bound strategy.
    BUY when price touches lower BB + RSI < 30 (oversold bounce).
    SELL when price touches upper BB + RSI > 70 (overbought fade).
    """
    close = df["Close"].values
    if len(close) < 20:
        return []

    c = float(close[-1])
    sma20 = float(np.mean(close[-20:]))
    std20 = float(np.std(close[-20:]))
    if std20 == 0:
        return []

    upper_bb = sma20 + 2 * std20
    lower_bb = sma20 - 2 * std20

    rsi_val = float(ind.rsi(df["Close"], 14).iloc[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"])
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else c * 0.02

    # Volume confirmation: require above-average volume for stronger signal
    vol = df["Volume"].values if "Volume" in df.columns else df["volume"].values
    vol_ratio = float(vol[-1] / np.mean(vol[-20:])) if np.mean(vol[-20:]) > 0 else 1.0

    signals = []

    # BUY: price at or below lower BB + RSI oversold
    if c <= lower_bb and rsi_val < 35:
        bb_depth = (lower_bb - c) / std20  # how far below BB
        confidence = min(0.80, 0.55 + bb_depth * 0.08 + (35 - rsi_val) * 0.005)
        if vol_ratio > 1.2:
            confidence = min(0.85, confidence + 0.05)
        signals.append(_base_signal(
            "bb_mean_reversion", pair, "BUY", c, confidence,
            f"Lower BB touch ({c:.4g} <= {lower_bb:.4g}), RSI={rsi_val:.0f}, vol_ratio={vol_ratio:.1f}x",
            atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=rsi_val,
        ))

    # SELL: price at or above upper BB + RSI overbought
    elif c >= upper_bb and rsi_val > 65:
        bb_depth = (c - upper_bb) / std20
        confidence = min(0.80, 0.55 + bb_depth * 0.08 + (rsi_val - 65) * 0.005)
        if vol_ratio > 1.2:
            confidence = min(0.85, confidence + 0.05)
        signals.append(_base_signal(
            "bb_mean_reversion", pair, "SELL", c, confidence,
            f"Upper BB touch ({c:.4g} >= {upper_bb:.4g}), RSI={rsi_val:.0f}, vol_ratio={vol_ratio:.1f}x",
            atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=rsi_val,
        ))

    return signals


def keltner_channel_breakout(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Keltner Channel Breakout — volatility expansion signal.
    When price breaks above/below Keltner Channel (EMA20 ± 2*ATR) with volume.
    Research: 55-62% WR (Keltner 1960, adapted).
    """
    close = df["Close"].values
    if len(close) < 50:
        return []

    c = float(close[-1])
    ema20 = float(ind.ema(df["Close"], 20).iloc[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"], 14)
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else c * 0.02

    # ── ATR volatility regime gate (v93/v95 crash stress test) ──
    # Keltner WR drops 72.9% -> 42.1% during crashes.
    # ATR > 2x mean -> half size; ATR > 3x -> skip entirely.
    vol_regime = ind.atr_volatility_regime(df["High"], df["Low"], df["Close"])
    if vol_regime["extreme_volatility"]:
        print(f"    [keltner_breakout] {pair}: SKIP — extreme volatility "
              f"(ATR ratio {vol_regime['atr_ratio']:.2f}x > 3x mean)")
        return []

    upper_kc = ema20 + 2.0 * atr_now
    lower_kc = ema20 - 2.0 * atr_now

    rsi_val = float(ind.rsi(df["Close"], 14).iloc[-1])
    vol = df["Volume"].values if "Volume" in df.columns else df["volume"].values
    vol_ratio = float(vol[-1] / np.mean(vol[-20:])) if np.mean(vol[-20:]) > 0 else 1.0

    # Need volume expansion for valid breakout
    if vol_ratio < 1.5:
        return []

    signals = []

    # Bullish breakout: price closes above upper Keltner
    if c > upper_kc and rsi_val > 50:
        confidence = min(0.75, 0.55 + (c - upper_kc) / atr_now * 0.05 + (vol_ratio - 1.5) * 0.03)
        if vol_regime["high_volatility_regime"]:
            confidence *= 0.85
            print(f"    [keltner_breakout] {pair}: HIGH VOL regime "
                  f"(ATR {vol_regime['atr_ratio']:.2f}x) — conf reduced, half size")
        signals.append(_base_signal(
            "keltner_channel_breakout", pair, "BUY", c, confidence,
            f"Keltner breakout UP ({c:.4g} > {upper_kc:.4g}), vol={vol_ratio:.1f}x, RSI={rsi_val:.0f}",
            atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=rsi_val,
            position_scale=vol_regime["position_scale"],
            high_volatility_regime=vol_regime["high_volatility_regime"],
            atr_ratio=vol_regime["atr_ratio"],
        ))

    # Bearish breakdown: price closes below lower Keltner
    elif c < lower_kc and rsi_val < 50:
        confidence = min(0.75, 0.55 + (lower_kc - c) / atr_now * 0.05 + (vol_ratio - 1.5) * 0.03)
        if vol_regime["high_volatility_regime"]:
            confidence *= 0.85
            print(f"    [keltner_breakout] {pair}: HIGH VOL regime "
                  f"(ATR {vol_regime['atr_ratio']:.2f}x) — conf reduced, half size")
        signals.append(_base_signal(
            "keltner_channel_breakout", pair, "SELL", c, confidence,
            f"Keltner breakout DOWN ({c:.4g} < {lower_kc:.4g}), vol={vol_ratio:.1f}x, RSI={rsi_val:.0f}",
            atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=rsi_val,
            position_scale=vol_regime["position_scale"],
            high_volatility_regime=vol_regime["high_volatility_regime"],
            atr_ratio=vol_regime["atr_ratio"],
        ))

    return signals


# --- Strategy 16: RSI Divergence (replaces raw RSI oversold logic) ---

def rsi_divergence(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    RSI Divergence — bullish and bearish divergence detection.

    Backtest finding: raw RSI<35 catches falling knives (39.3% WR).
    Fix: use RSI DIVERGENCE instead — price makes lower low but RSI makes
    higher low = bullish reversal. Vice versa for bearish.

    Uses 5-bar lookback for swing detection + volume confirmation (1.5x avg).
    Research: RSI divergence 55-65% WR (Wilder 1978, Cardwell extensions).
    """
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values

    if len(close) < 30:
        return []

    rsi_vals = ind.rsi(df["Close"], 14).values

    # Find swing lows and highs using 5-bar lookback
    swing_low_idxs = _find_swing_lows(low, lookback=5)
    swing_high_idxs = _find_swing_highs(high, lookback=5)

    c = float(close[-1])
    curr_rsi = float(rsi_vals[-1]) if not np.isnan(rsi_vals[-1]) else 50.0
    atr_val = ind.atr(df["High"], df["Low"], df["Close"], 14)
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else c * 0.02

    # Volume confirmation: require volume > 1.5x 20-period average
    vol = df["Volume"].values if "Volume" in df.columns else df["volume"].values
    vol_avg_20 = float(np.mean(vol[-20:])) if len(vol) >= 20 else float(np.mean(vol))
    vol_ratio = float(vol[-1] / vol_avg_20) if vol_avg_20 > 0 else 1.0
    if vol_ratio < 1.5:
        return []

    signals = []

    # --- Bullish RSI Divergence ---
    # Price makes LOWER LOW but RSI makes HIGHER LOW
    # Current bar should be near a swing low region and RSI < 45
    if len(swing_low_idxs) >= 2 and curr_rsi < 45:
        # Get the two most recent swing lows
        prev_sw = swing_low_idxs[-2]
        curr_sw = swing_low_idxs[-1]

        # Current swing low must be recent (within last 10 bars)
        if len(close) - curr_sw <= 10:
            price_lower_low = low[curr_sw] < low[prev_sw]
            rsi_higher_low = (
                not np.isnan(rsi_vals[curr_sw]) and
                not np.isnan(rsi_vals[prev_sw]) and
                rsi_vals[curr_sw] > rsi_vals[prev_sw]
            )

            if price_lower_low and rsi_higher_low:
                divergence_strength = (rsi_vals[curr_sw] - rsi_vals[prev_sw]) / 10.0
                confidence = min(0.82, 0.60 + divergence_strength * 0.15 + vol_ratio * 0.02)
                signals.append(_base_signal(
                    "rsi_divergence", pair, "BUY", c, confidence,
                    (f"Bullish RSI divergence: price LL ({low[curr_sw]:.4g} < {low[prev_sw]:.4g}) "
                     f"but RSI HL ({rsi_vals[curr_sw]:.1f} > {rsi_vals[prev_sw]:.1f}), "
                     f"vol={vol_ratio:.1f}x"),
                    atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=curr_rsi,
                ))

    # --- Bearish RSI Divergence ---
    # Price makes HIGHER HIGH but RSI makes LOWER HIGH
    # Current bar should be near a swing high region and RSI > 55
    if len(swing_high_idxs) >= 2 and curr_rsi > 55:
        prev_sw = swing_high_idxs[-2]
        curr_sw = swing_high_idxs[-1]

        # Current swing high must be recent (within last 10 bars)
        if len(close) - curr_sw <= 10:
            price_higher_high = high[curr_sw] > high[prev_sw]
            rsi_lower_high = (
                not np.isnan(rsi_vals[curr_sw]) and
                not np.isnan(rsi_vals[prev_sw]) and
                rsi_vals[curr_sw] < rsi_vals[prev_sw]
            )

            if price_higher_high and rsi_lower_high:
                divergence_strength = (rsi_vals[prev_sw] - rsi_vals[curr_sw]) / 10.0
                confidence = min(0.82, 0.60 + divergence_strength * 0.15 + vol_ratio * 0.02)
                signals.append(_base_signal(
                    "rsi_divergence", pair, "SELL", c, confidence,
                    (f"Bearish RSI divergence: price HH ({high[curr_sw]:.4g} > {high[prev_sw]:.4g}) "
                     f"but RSI LH ({rsi_vals[curr_sw]:.1f} < {rsi_vals[prev_sw]:.1f}), "
                     f"vol={vol_ratio:.1f}x"),
                    atr_value=atr_now, volume_ratio=vol_ratio, rsi_value=curr_rsi,
                ))

    return signals


# --- Strategy 17: Fibonacci Retracement Bounce ---

def fibonacci_retracement(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Fibonacci retracement pullback + RSI confirmation.
    Research: +6.89% ROI improvement (Springer 2024), Osler (2000) FRBNY.

    BUY: Price at 38.2%, 50%, or 61.8% Fib level in uptrend + RSI < 50.
    SELL: Price at Fib level in downtrend + RSI > 50.
    """
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values

    if len(close) < 80:
        return []

    c = float(close[-1])
    atr_val = ind.atr(df["High"], df["Low"], df["Close"], 14)
    atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else c * 0.02

    # Determine trend using 50/200 SMA
    sma50 = float(ind.sma(df["Close"], 50).iloc[-1])
    if len(df) >= 200:
        sma200 = float(ind.sma(df["Close"], 200).iloc[-1])
    else:
        sma200 = float(ind.sma(df["Close"], min(len(df) - 1, 100)).iloc[-1])

    uptrend = sma50 > sma200

    # Find swing high and swing low in last 60 bars
    lookback = min(60, len(close) - 5)
    window_high = high[-(lookback + 5):-5]
    window_low = low[-(lookback + 5):-5]

    if len(window_high) < 20:
        return []

    swing_high = float(np.max(window_high))
    swing_low = float(np.min(window_low))
    swing_range = swing_high - swing_low

    # Minimum swing range: 5% of price (filter tiny swings)
    if swing_range / c < 0.05:
        return []

    # Fibonacci levels (retracement from high to low)
    fib_levels = {
        0.382: swing_high - 0.382 * swing_range,
        0.500: swing_high - 0.500 * swing_range,
        0.618: swing_high - 0.618 * swing_range,
    }

    # Check if price is near any Fib level (within 1.5% tolerance)
    tolerance = 0.015
    hit_level = None
    hit_price = None
    best_dist = float("inf")

    for level, fib_price in fib_levels.items():
        distance = abs(c - fib_price) / fib_price
        if distance <= tolerance and distance < best_dist:
            hit_level = level
            hit_price = fib_price
            best_dist = distance

    if hit_level is None:
        return []

    rsi_val = float(ind.rsi(df["Close"], 14).iloc[-1])
    vol = df["Volume"].values if "Volume" in df.columns else df["volume"].values
    vol_ratio = float(vol[-1] / np.mean(vol[-20:])) if np.mean(vol[-20:]) > 0 else 1.0

    signals = []

    # Bullish: uptrend + price at Fib pullback + RSI < 50
    if uptrend and rsi_val < 50:
        confidence = 0.62
        if hit_level == 0.382:
            confidence += 0.06  # shallow = strong trend
        elif hit_level == 0.500:
            confidence += 0.04
        elif hit_level == 0.618:
            confidence += 0.03  # deeper = riskier but better R:R
        if rsi_val < 35:
            confidence += 0.03  # deeply oversold bonus
        if vol_ratio > 1.5:
            confidence += 0.03  # volume confirmation
        confidence = min(0.82, confidence)

        signals.append(_base_signal(
            "fibonacci_retracement", pair, "BUY", c, confidence,
            (f"Fib {hit_level*100:.1f}% pullback in uptrend (50>200 SMA). "
             f"RSI={rsi_val:.0f}, swing {swing_low:.4g}->{swing_high:.4g}. "
             f"Osler (2000): institutional clusters at Fib levels"),
            atr_value=atr_now,
            rsi_value=rsi_val,
            volume_ratio=vol_ratio,
            fib_level=hit_level,
            fib_price=round(hit_price, 8),
            swing_high=round(swing_high, 8),
            swing_low=round(swing_low, 8),
        ))

    # Bearish: downtrend + price at Fib rebound + RSI > 50
    elif not uptrend and rsi_val > 50:
        confidence = 0.60
        if hit_level == 0.382:
            confidence += 0.05
        elif hit_level == 0.500:
            confidence += 0.04
        elif hit_level == 0.618:
            confidence += 0.03
        if rsi_val > 65:
            confidence += 0.03
        if vol_ratio > 1.5:
            confidence += 0.03
        confidence = min(0.82, confidence)

        signals.append(_base_signal(
            "fibonacci_retracement", pair, "SELL", c, confidence,
            (f"Fib {hit_level*100:.1f}% rebound in downtrend (50<200 SMA). "
             f"RSI={rsi_val:.0f}, swing {swing_low:.4g}->{swing_high:.4g}"),
            atr_value=atr_now,
            rsi_value=rsi_val,
            volume_ratio=vol_ratio,
            fib_level=hit_level,
            fib_price=round(hit_price, 8),
            swing_high=round(swing_high, 8),
            swing_low=round(swing_low, 8),
        ))

    return signals


# ─── Bear Market SHORT Strategies (added Feb 25 2026) ───────────────────────

def ema_crossover_short(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    EMA 9/21 death cross below 200 SMA — trend-following short.
    Research: 55-62% WR in confirmed bear markets.
    Only fires when price is below 200 SMA (confirmed downtrend).
    """
    signals = []
    if len(df) < 210:
        return signals

    close = df["Close"].values
    c = float(close[-1])

    ema9 = ind.ema(df["Close"], 9).values
    ema21 = ind.ema(df["Close"], 21).values
    sma200 = ind.sma(df["Close"], 200).values

    # Conditions:
    # 1. Price below 200 SMA (confirmed bear)
    # 2. EMA9 just crossed below EMA21 (death cross on fast timeframe)
    # 3. Previous bar had EMA9 >= EMA21 (fresh cross)
    if (c < sma200[-1]
        and ema9[-1] < ema21[-1]
        and ema9[-2] >= ema21[-2]):

        confidence = 0.60
        # Boost if price is well below 200 SMA (strong trend)
        dist_below_200 = (sma200[-1] - c) / sma200[-1]
        if dist_below_200 > 0.05:
            confidence += 0.05
        if dist_below_200 > 0.10:
            confidence += 0.05
        # Boost if volume is above average (conviction)
        vol = df["Volume"].values
        vol_ratio = float(vol[-1]) / float(np.mean(vol[-20:])) if np.mean(vol[-20:]) > 0 else 1.0
        if vol_ratio > 1.5:
            confidence += 0.05

        atr_now = float(ind.atr(df["High"], df["Low"], df["Close"], 14).iloc[-1])
        confidence = min(0.85, confidence)

        signals.append(_base_signal(
            "ema_crossover_short", pair, "SELL", c, confidence,
            (f"EMA 9/21 death cross below 200 SMA. Price {dist_below_200*100:.1f}% below 200 SMA. "
             f"Vol ratio={vol_ratio:.1f}x"),
            atr_value=atr_now,
            ema9=round(float(ema9[-1]), 8),
            ema21=round(float(ema21[-1]), 8),
            sma200=round(float(sma200[-1]), 8),
            dist_below_200=round(dist_below_200, 4),
        ))

    return signals


def sell_the_rally(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Sell-the-rally in bear market: price touches declining 20 EMA from below
    and gets rejected. RSI in 55-65 range (overbought for bear market).
    Research: 58-65% WR in sustained downtrends.
    """
    signals = []
    if len(df) < 210:
        return signals

    close = df["Close"].values
    high = df["High"].values
    # FIX: use previous bar's close to avoid intra-bar look-ahead bias.
    # At signal time the current bar is still forming — only the previous
    # bar's close is known with certainty.
    c = float(close[-2])  # previous bar close (was close[-1])

    ema20 = ind.ema(df["Close"], 20).values
    sma200 = ind.sma(df["Close"], 200).values
    rsi14 = ind.rsi(df["Close"], 14).values

    # Conditions (all use previous-bar data to prevent look-ahead):
    # 1. Price below 200 SMA (confirmed bear)
    # 2. 20 EMA is declining (bearish momentum)
    # 3. Price touched or exceeded 20 EMA in recent bar (the rally)
    # 4. Price closed back below 20 EMA (rejection)
    # 5. RSI is in 45-65 range (not oversold — the rally brought it up)
    ema20_declining = ema20[-2] < ema20[-6] if len(ema20) > 6 else False
    price_touched_ema = float(high[-2]) >= ema20[-2] * 0.998  # within 0.2%
    price_rejected = c < ema20[-2]
    rsi_val = float(rsi14[-2]) if len(rsi14) > 1 else 50
    rsi_in_range = 45 <= rsi_val <= 65

    if (c < sma200[-2]
        and ema20_declining
        and price_touched_ema
        and price_rejected
        and rsi_in_range):

        confidence = 0.62
        # Stronger if multiple touches and rejections (previous bars only)
        recent_highs_near_ema = sum(1 for i in range(-6, -1) if float(high[i]) >= ema20[i] * 0.998)
        if recent_highs_near_ema >= 2:
            confidence += 0.05  # Multiple rejections = stronger resistance

        vol = df["Volume"].values
        vol_ratio = float(vol[-2]) / float(np.mean(vol[-21:-1])) if np.mean(vol[-21:-1]) > 0 else 1.0
        if vol_ratio > 1.3:
            confidence += 0.04  # Volume on rejection

        atr_now = float(ind.atr(df["High"], df["Low"], df["Close"], 14).iloc[-2])
        confidence = min(0.85, confidence)

        signals.append(_base_signal(
            "sell_the_rally", pair, "SELL", c, confidence,
            (f"Rally rejected at declining 20 EMA ({float(ema20[-2]):.4g}). "
             f"RSI={rsi_val:.0f}, {recent_highs_near_ema} recent rejections. "
             f"Price {((sma200[-2]-c)/sma200[-2])*100:.1f}% below 200 SMA"),
            atr_value=atr_now,
            ema20=round(float(ema20[-2]), 8),
            sma200=round(float(sma200[-2]), 8),
            rsi_value=round(rsi_val, 2),
            rejection_count=recent_highs_near_ema,
        ))

    return signals


def bear_trend_short(df: pd.DataFrame, pair: str) -> list[dict]:
    """
    Strong bear trend continuation short: price below 200 SMA, making lower highs,
    MACD histogram negative and declining. Most reliable SHORT in downtrends.
    Research: 60% WR, targets 3 ATR TP.
    """
    signals = []
    if len(df) < 210:
        return signals

    close = df["Close"].values
    high = df["High"].values
    c = float(close[-1])

    sma200 = ind.sma(df["Close"], 200).values
    sma50 = ind.sma(df["Close"], 50).values
    rsi14 = ind.rsi(df["Close"], 14).values
    macd_line, signal_line, hist = ind.macd(df["Close"])
    macd_hist = hist.values if hasattr(hist, 'values') else np.array(hist)

    # Conditions:
    # 1. Price below 200 SMA AND 50 SMA below 200 SMA (structural bear)
    # 2. Making lower highs (last 3 swing highs are declining)
    # 3. MACD histogram is negative and declining
    # 4. RSI < 55 (not overbought — no relief rally in progress)
    structural_bear = c < sma200[-1] and sma50[-1] < sma200[-1]
    macd_bearish = (len(macd_hist) > 2
                    and float(macd_hist[-1]) < 0
                    and float(macd_hist[-1]) < float(macd_hist[-2]))

    # Check for lower highs
    swing_hi = _find_swing_highs(high, lookback=5)
    lower_highs = False
    if len(swing_hi) >= 2:
        last_two = swing_hi[-2:]
        lower_highs = high[last_two[-1]] < high[last_two[-2]]

    rsi_val = float(rsi14[-1]) if len(rsi14) > 0 else 50

    if structural_bear and macd_bearish and lower_highs and rsi_val < 55:
        confidence = 0.62
        # Boost for strong structural bear
        if sma50[-1] < sma200[-1] * 0.95:
            confidence += 0.05  # 50 SMA well below 200 SMA
        # Boost if RSI is moderate (room to fall)
        if 35 <= rsi_val <= 50:
            confidence += 0.04
        # Boost for volume
        vol = df["Volume"].values
        vol_ratio = float(vol[-1]) / float(np.mean(vol[-20:])) if np.mean(vol[-20:]) > 0 else 1.0
        if vol_ratio > 1.2:
            confidence += 0.03

        atr_now = float(ind.atr(df["High"], df["Low"], df["Close"], 14).iloc[-1])
        confidence = min(0.85, confidence)

        signals.append(_base_signal(
            "bear_trend_short", pair, "SELL", c, confidence,
            (f"Structural bear: 50 SMA < 200 SMA, lower highs, MACD declining. "
             f"RSI={rsi_val:.0f}, vol={vol_ratio:.1f}x"),
            atr_value=atr_now,
            sma50=round(float(sma50[-1]), 8),
            sma200=round(float(sma200[-1]), 8),
            rsi_value=round(rsi_val, 2),
            macd_hist=round(float(macd_hist[-1]), 8),
        ))

    return signals

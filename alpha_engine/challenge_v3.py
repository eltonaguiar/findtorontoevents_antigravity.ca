#!/usr/bin/env python3
"""
ALPHA ENGINE -- 2-HOUR CHALLENGE V3 (INSTITUTIONAL GRADE)
==========================================================
Institutional-quality strategies + risk management.
- Equal risk per position (no single pick can destroy portfolio)
- Correlation filter (no redundant bets)
- Multiple timeframes (5m, 15m, 1h)
- EST timestamps on everything
- Restartable rounds with full history

Usage:
  python challenge_v3.py start     # Start a new round
  python challenge_v3.py check     # Check current round
  python challenge_v3.py restart   # Restart with new picks
  python challenge_v3.py history   # Show all rounds
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

EST = timezone(timedelta(hours=-5))
DATA_DIR = Path(__file__).resolve().parent / "data"
CHALLENGE_FILE = DATA_DIR / "challenge_v3.json"
HISTORY_FILE = DATA_DIR / "challenge_v3_history.json"

# Portfolio config
PORTFOLIO_SIZE = 10000  # $10k challenge portfolio
MAX_RISK_PER_TRADE = 0.01  # 1% of portfolio per trade = $100 max loss
MAX_POSITIONS = 15
MAX_CORRELATED = 2  # Max trades on same symbol

# Symbols - focus on high liquidity
SYMBOLS = {
    "BTC-USD":  {"cat": "crypto", "name": "Bitcoin"},
    "ETH-USD":  {"cat": "crypto", "name": "Ethereum"},
    "SOL-USD":  {"cat": "crypto", "name": "Solana"},
    "DOGE-USD": {"cat": "crypto", "name": "Dogecoin"},
    "XRP-USD":  {"cat": "crypto", "name": "XRP"},
    "AVAX-USD": {"cat": "crypto", "name": "Avalanche"},
    "LINK-USD": {"cat": "crypto", "name": "Chainlink"},
    "ADA-USD":  {"cat": "crypto", "name": "Cardano"},
    "EURUSD=X": {"cat": "forex", "name": "EUR/USD"},
    "GBPUSD=X": {"cat": "forex", "name": "GBP/USD"},
    "USDJPY=X": {"cat": "forex", "name": "USD/JPY"},
    "AUDUSD=X": {"cat": "forex", "name": "AUD/USD"},
    "USDCAD=X": {"cat": "forex", "name": "USD/CAD"},
    "GBPJPY=X": {"cat": "forex", "name": "GBP/JPY"},
    "EURJPY=X": {"cat": "forex", "name": "EUR/JPY"},
    "NZDUSD=X": {"cat": "forex", "name": "NZD/USD"},
}


def now_est():
    return datetime.now(EST)

def est_str(dt=None):
    if dt is None:
        dt = now_est()
    return dt.strftime("%Y-%m-%d %I:%M:%S %p EST")

# =============================================================================
# DATA
# =============================================================================

def fetch_multi_tf(symbols):
    """Fetch multiple timeframes for all symbols."""
    result = {}
    for interval, period in [("5m", "5d"), ("15m", "5d"), ("1h", "1mo")]:
        tickers = " ".join(symbols)
        try:
            raw = yf.download(tickers, period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        df = raw.copy()
                    else:
                        df = raw[sym].copy() if sym in raw.columns.get_level_values(0) else None
                    if df is not None and not df.empty:
                        df = df.dropna(subset=["Close"])
                        if len(df) >= 20:
                            if sym not in result:
                                result[sym] = {}
                            result[sym][interval] = df
                except Exception:
                    continue
        except Exception:
            continue
    return result


# =============================================================================
# INDICATORS
# =============================================================================

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def ema(series, span):
    return series.ewm(span=span).mean()

def bollinger(close, period=20, std_mult=2):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma, sma + std_mult * std, sma - std_mult * std

def vwap(df):
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].replace(0, np.nan)
    cum_tp_vol = (typical * vol).cumsum()
    cum_vol = vol.cumsum()
    return cum_tp_vol / cum_vol

def zscore(series, period=20):
    mean = series.rolling(period).mean()
    std = series.rolling(period).std()
    return (series - mean) / std.replace(0, np.nan)


# =============================================================================
# INSTITUTIONAL STRATEGIES
# =============================================================================

def strat_orb_breakout(df, sym, meta, tf="5m"):
    """Opening Range Breakout -- institutional favorite.
    Uses the first N bars as the 'opening range', trades breakout.
    Works on crypto (24/7) and forex."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    if len(close) < 30:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    # Opening range = first 6 bars of the session (30 min on 5m)
    n_bars = 6 if tf == "5m" else 3
    if len(close) < n_bars + 5:
        return []

    orh = float(high.iloc[-n_bars:].max())  # Opening range high
    orl = float(low.iloc[-n_bars:].min())   # Opening range low

    # Breakout above range
    if price > orh and float(close.iloc[-2]) <= orh:
        tp = price + 1.5 * atr_val
        sl = price - 1.0 * atr_val
        picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                               "orb_breakout", tf,
                               f"Broke above opening range {orh:.6g}"))

    # Breakdown below range
    if price < orl and float(close.iloc[-2]) >= orl:
        tp = price - 1.5 * atr_val
        sl = price + 1.0 * atr_val
        picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                               "orb_breakout", tf,
                               f"Broke below opening range {orl:.6g}"))
    return picks


def strat_vwap_deviation(df, sym, meta, tf="5m"):
    """VWAP Deviation Bands -- reversion to VWAP from 2-sigma extremes.
    Institutional-grade mean reversion."""
    close = df["Close"]
    vol = df["Volume"]
    if len(close) < 25 or vol.sum() == 0:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    vwap_val = vwap(df)
    if vwap_val.isna().all():
        return []

    vwap_now = float(vwap_val.iloc[-1])
    vwap_std = float((close - vwap_val).rolling(20).std().iloc[-1])
    if vwap_std == 0:
        return []

    upper_band = vwap_now + 2 * vwap_std
    lower_band = vwap_now - 2 * vwap_std

    # Price at lower deviation band, bouncing up
    if price < lower_band and float(close.iloc[-2]) < float(close.iloc[-1]):
        tp = vwap_now  # Target: revert to VWAP
        sl = price - 1.0 * atr_val
        if tp > price:
            picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                   "vwap_deviation", tf,
                                   f"Below VWAP -2σ ({lower_band:.6g}), reverting"))

    # Price at upper deviation band, falling
    if price > upper_band and float(close.iloc[-2]) > float(close.iloc[-1]):
        tp = vwap_now
        sl = price + 1.0 * atr_val
        if tp < price:
            picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                   "vwap_deviation", tf,
                                   f"Above VWAP +2σ ({upper_band:.6g}), reverting"))
    return picks


def strat_ema_rsi_momentum(df, sym, meta, tf="5m"):
    """EMA crossover + RSI filter -- enhanced institutional version.
    EMA(5) x EMA(20) with RSI in 30-70 band (no extremes)."""
    close = df["Close"]
    if len(close) < 30:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    ema5 = ema(close, 5)
    ema20 = ema(close, 20)
    rsi_val = float(rsi(close, 14).iloc[-1])

    # Bullish crossover with RSI filter
    if (float(ema5.iloc[-1]) > float(ema20.iloc[-1]) and
        float(ema5.iloc[-2]) <= float(ema20.iloc[-2]) and
        30 < rsi_val < 70 and
        price > float(ema20.iloc[-1])):
        tp = price + 1.4 * atr_val
        sl = price - 1.0 * atr_val
        picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                               "ema_rsi_momentum", tf,
                               f"EMA5>EMA20 cross, RSI={rsi_val:.0f}"))

    # Bearish crossover with RSI filter
    if (float(ema5.iloc[-1]) < float(ema20.iloc[-1]) and
        float(ema5.iloc[-2]) >= float(ema20.iloc[-2]) and
        30 < rsi_val < 70 and
        price < float(ema20.iloc[-1])):
        tp = price - 1.4 * atr_val
        sl = price + 1.0 * atr_val
        picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                               "ema_rsi_momentum", tf,
                               f"EMA5<EMA20 cross, RSI={rsi_val:.0f}"))
    return picks


def strat_zscore_pairs(df, sym, meta, tf="5m"):
    """Z-Score mean reversion -- when price stretches 2+ sigma from mean.
    Institutional stat-arb adapted for single-asset."""
    close = df["Close"]
    if len(close) < 30:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    z = float(zscore(close, 20).iloc[-1])
    z_prev = float(zscore(close, 20).iloc[-2])

    # Oversold: z crossed above -2 (was < -2, now > -2)
    if z > -2.0 and z < -1.0 and z_prev <= -2.0:
        mean_price = float(close.rolling(20).mean().iloc[-1])
        tp = mean_price  # Revert to mean
        sl = price - 1.5 * atr_val
        if tp > price:
            picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                   "zscore_reversion", tf,
                                   f"Z-score reverting from {z_prev:.2f} to {z:.2f}"))

    # Overbought: z crossed below +2
    if z < 2.0 and z > 1.0 and z_prev >= 2.0:
        mean_price = float(close.rolling(20).mean().iloc[-1])
        tp = mean_price
        sl = price + 1.5 * atr_val
        if tp < price:
            picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                   "zscore_reversion", tf,
                                   f"Z-score reverting from {z_prev:.2f} to {z:.2f}"))
    return picks


def strat_bb_squeeze_expansion(df, sym, meta, tf="5m"):
    """Bollinger Band squeeze into expansion -- volatility breakout.
    Wait for squeeze (narrow bands), then trade the breakout direction."""
    close = df["Close"]
    if len(close) < 30:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    sma, upper, lower = bollinger(close, 20, 2)
    bandwidth = (upper - lower) / sma
    bw_now = float(bandwidth.iloc[-1])
    bw_lookback = bandwidth.iloc[-20:]

    if len(bw_lookback) < 20:
        return []

    bw_percentile = (bw_lookback < bw_now).sum() / len(bw_lookback)

    # Currently in squeeze (bandwidth in bottom 20th percentile)
    # and price just broke out
    if bw_percentile < 0.25:
        upper_val = float(upper.iloc[-1])
        lower_val = float(lower.iloc[-1])

        if price > upper_val:
            tp = price + 2.0 * atr_val
            sl = float(sma.iloc[-1])
            picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                   "bb_squeeze_expansion", tf,
                                   f"BB squeeze breakout UP, BW pctl={bw_percentile:.0%}"))
        elif price < lower_val:
            tp = price - 2.0 * atr_val
            sl = float(sma.iloc[-1])
            picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                   "bb_squeeze_expansion", tf,
                                   f"BB squeeze breakout DOWN, BW pctl={bw_percentile:.0%}"))
    return picks


def strat_triple_ema_trend(df, sym, meta, tf="15m"):
    """Triple EMA alignment -- strong trend filter.
    EMA(8) > EMA(21) > EMA(55) for longs, reversed for shorts.
    Only enters on pullbacks to EMA(21)."""
    close = df["Close"]
    if len(close) < 60:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    ema8 = ema(close, 8)
    ema21 = ema(close, 21)
    ema55 = ema(close, 55)

    e8 = float(ema8.iloc[-1])
    e21 = float(ema21.iloc[-1])
    e55 = float(ema55.iloc[-1])

    # Bullish alignment: EMA8 > EMA21 > EMA55
    if e8 > e21 > e55:
        # Price pulled back to EMA21 (within 0.5 ATR)
        if abs(price - e21) < 0.5 * atr_val and price > e21:
            tp = price + 2.0 * atr_val
            sl = e55  # Stop at EMA55
            if tp > sl:
                picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                       "triple_ema_trend", tf,
                                       f"Bullish EMA alignment, pullback to EMA21"))

    # Bearish alignment: EMA8 < EMA21 < EMA55
    if e8 < e21 < e55:
        if abs(price - e21) < 0.5 * atr_val and price < e21:
            tp = price - 2.0 * atr_val
            sl = e55
            if tp < sl:
                picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                       "triple_ema_trend", tf,
                                       f"Bearish EMA alignment, pullback to EMA21"))
    return picks


def strat_volume_climax(df, sym, meta, tf="5m"):
    """Volume climax reversal -- extreme volume signals exhaustion.
    When volume spikes 3x+ average with a large candle, fade the move."""
    close = df["Close"]
    vol = df["Volume"]
    opn = df["Open"]
    if len(close) < 25 or vol.iloc[-5:].sum() == 0:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    avg_vol = float(vol.rolling(20).mean().iloc[-1])
    cur_vol = float(vol.iloc[-1])

    if avg_vol == 0:
        return []

    vol_ratio = cur_vol / avg_vol
    candle_size = abs(float(close.iloc[-1]) - float(opn.iloc[-1]))
    candle_ratio = candle_size / atr_val if atr_val > 0 else 0

    # Volume climax: 3x+ volume with large candle
    if vol_ratio >= 3.0 and candle_ratio >= 1.0:
        # Fade the move (reversal)
        if float(close.iloc[-1]) > float(opn.iloc[-1]):
            # Big green candle with huge volume = exhaustion, short
            tp = price - 1.5 * atr_val
            sl = price + 0.8 * atr_val
            picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                   "volume_climax_reversal", tf,
                                   f"Volume climax (vol {vol_ratio:.1f}x avg), fading rally"))
        else:
            # Big red candle with huge volume = capitulation, long
            tp = price + 1.5 * atr_val
            sl = price - 0.8 * atr_val
            picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                   "volume_climax_reversal", tf,
                                   f"Volume capitulation (vol {vol_ratio:.1f}x avg), buying dip"))
    return picks


def strat_rsi_divergence(df, sym, meta, tf="15m"):
    """RSI divergence -- price makes new low but RSI doesn't (bullish).
    Or price makes new high but RSI doesn't (bearish)."""
    close = df["Close"]
    if len(close) < 30:
        return []

    picks = []
    price = float(close.iloc[-1])
    atr_val = float(atr(df).iloc[-1])
    if atr_val == 0:
        atr_val = price * 0.005

    rsi_vals = rsi(close, 14)

    # Look at last 15 bars for divergence
    window = 15
    if len(close) < window + 5:
        return []

    prices_window = close.iloc[-window:]
    rsi_window = rsi_vals.iloc[-window:]

    price_min_idx = prices_window.idxmin()
    price_max_idx = prices_window.idxmax()
    price_min = float(prices_window.min())
    price_max = float(prices_window.max())

    # Bullish divergence: price at/near low, RSI higher than at the price low
    if price <= price_min * 1.002:  # Near the low
        rsi_at_low = float(rsi_window.loc[price_min_idx]) if price_min_idx in rsi_window.index else None
        rsi_now = float(rsi_vals.iloc[-1])
        if rsi_at_low and rsi_now > rsi_at_low + 5:
            tp = price + 2.0 * atr_val
            sl = price - 1.0 * atr_val
            picks.append(make_pick(sym, meta, "BUY", price, tp, sl, atr_val,
                                   "rsi_divergence", tf,
                                   f"Bullish divergence: price near low, RSI rising"))

    # Bearish divergence
    if price >= price_max * 0.998:
        rsi_at_high = float(rsi_window.loc[price_max_idx]) if price_max_idx in rsi_window.index else None
        rsi_now = float(rsi_vals.iloc[-1])
        if rsi_at_high and rsi_now < rsi_at_high - 5:
            tp = price - 2.0 * atr_val
            sl = price + 1.0 * atr_val
            picks.append(make_pick(sym, meta, "SELL", price, tp, sl, atr_val,
                                   "rsi_divergence", tf,
                                   f"Bearish divergence: price near high, RSI falling"))
    return picks


# =============================================================================
# RISK MANAGEMENT (INSTITUTIONAL GRADE)
# =============================================================================

def calculate_position_size(entry, sl, portfolio=PORTFOLIO_SIZE, risk_pct=MAX_RISK_PER_TRADE):
    """Equal risk per trade -- no single pick can lose more than risk_pct of portfolio."""
    max_loss = portfolio * risk_pct  # e.g., $100
    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        return 0, 0
    units = max_loss / risk_per_unit
    position_value = units * entry
    return round(position_value, 2), round(max_loss, 2)


def apply_risk_management(all_picks):
    """Filter and size picks with institutional risk management."""
    # 1. Calculate position sizes
    for p in all_picks:
        pos_size, max_loss = calculate_position_size(p["entry_price"], p["stop_loss"])
        p["position_size"] = pos_size
        p["max_loss"] = max_loss

    # 2. Remove zero-size positions
    all_picks = [p for p in all_picks if p["position_size"] > 0]

    # 3. No conflicting positions: only one direction per symbol (best R:R wins)
    sym_direction = {}  # sym -> (direction, best_rr, pick)
    for p in sorted(all_picks, key=lambda x: x.get("risk_reward", 0), reverse=True):
        key = p["symbol"]
        direction = p["signal_type"]
        if key not in sym_direction:
            sym_direction[key] = (direction, p["risk_reward"], p)
        elif sym_direction[key][0] == direction:
            # Same direction, allow up to MAX_CORRELATED
            pass
        else:
            # Opposite direction -- skip (the first/best R:R wins)
            continue

    # Now limit to MAX_CORRELATED per symbol
    sym_count = defaultdict(int)
    filtered = []
    for p in sorted(all_picks, key=lambda x: x.get("risk_reward", 0), reverse=True):
        key = p["symbol"]
        direction = p["signal_type"]
        # Only allow the winning direction
        if key in sym_direction and sym_direction[key][0] != direction:
            continue
        if sym_count[key] < MAX_CORRELATED:
            sym_count[key] += 1
            filtered.append(p)
    all_picks = filtered

    # 4. Cap total positions
    all_picks = all_picks[:MAX_POSITIONS]

    return all_picks


# =============================================================================
# CORE
# =============================================================================

def make_pick(sym, meta, signal_type, price, tp, sl, atr_val, strategy, timeframe, reason):
    risk_per_unit = abs(price - sl)
    reward_per_unit = abs(tp - price)
    rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
    return {
        "symbol": sym,
        "name": meta["name"],
        "category": meta["cat"],
        "signal_type": signal_type,
        "entry_price": round(price, 8),
        "take_profit": round(tp, 8),
        "stop_loss": round(sl, 8),
        "atr": round(atr_val, 8),
        "risk_reward": round(rr, 2),
        "strategy": strategy,
        "timeframe": timeframe,
        "reason": reason,
        "entry_time_est": est_str(),
        "entry_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


STRATEGY_FUNCS = {
    "5m": [strat_orb_breakout, strat_vwap_deviation, strat_ema_rsi_momentum,
           strat_zscore_pairs, strat_bb_squeeze_expansion, strat_volume_climax],
    "15m": [strat_triple_ema_trend, strat_rsi_divergence,
            strat_ema_rsi_momentum, strat_zscore_pairs],
    "1h": [strat_triple_ema_trend, strat_bb_squeeze_expansion,
           strat_orb_breakout, strat_vwap_deviation],
}


def start_round():
    t = now_est()
    print("\n" + "=" * 80)
    print("  ALPHA ENGINE V3 -- INSTITUTIONAL 2-HOUR CHALLENGE")
    print(f"  Start: {est_str(t)}")
    print(f"  End:   {est_str(t + timedelta(hours=2))}")
    print(f"  Portfolio: ${PORTFOLIO_SIZE:,} | Max Risk/Trade: {MAX_RISK_PER_TRADE*100:.0f}% (${PORTFOLIO_SIZE*MAX_RISK_PER_TRADE:.0f})")
    print("=" * 80)

    history = load_history()
    round_num = len(history) + 1
    print(f"\n  Round #{round_num}")

    print(f"\n[1/3] Fetching multi-timeframe data for {len(SYMBOLS)} symbols...")
    symbols = list(SYMBOLS.keys())
    all_data = fetch_multi_tf(symbols)
    for sym in symbols:
        tfs = list(all_data.get(sym, {}).keys())
        if tfs:
            pass  # silently loaded
    loaded = sum(1 for s in all_data if all_data[s])
    print(f"  Loaded data for {loaded}/{len(symbols)} symbols")

    print(f"\n[2/3] Running institutional strategies across timeframes...")
    all_picks = []

    for tf, strat_fns in STRATEGY_FUNCS.items():
        for strat_fn in strat_fns:
            for sym, meta in SYMBOLS.items():
                if sym not in all_data or tf not in all_data[sym]:
                    continue
                try:
                    picks = strat_fn(all_data[sym][tf], sym, meta, tf=tf)
                    if picks:
                        all_picks.extend(picks)
                        for p in picks:
                            print(f"  [{tf}] [{p['strategy']}] {p['signal_type']} "
                                  f"{sym} @ {p['entry_price']:.8g} -- {p['reason']}")
                except Exception as e:
                    pass

    print(f"\n  Raw signals: {len(all_picks)}")

    print(f"\n[3/3] Applying risk management...")
    all_picks = apply_risk_management(all_picks)
    print(f"  After risk filter: {len(all_picks)} picks")

    for p in all_picks:
        print(f"  {p['signal_type']:>4s} {p['symbol']:>12s} @ {p['entry_price']:>12.8g} "
              f"TP={p['take_profit']:>12.8g} SL={p['stop_loss']:>12.8g} "
              f"R:R={p['risk_reward']:.1f}x Size=${p['position_size']:,.0f} "
              f"MaxLoss=${p['max_loss']:.0f} [{p['strategy']}|{p['timeframe']}]")

    challenge = {
        "round": round_num,
        "version": "V3-INSTITUTIONAL",
        "start_time_est": est_str(t),
        "end_time_est": est_str(t + timedelta(hours=2)),
        "start_utc": datetime.now(timezone.utc).isoformat(),
        "portfolio_size": PORTFOLIO_SIZE,
        "max_risk_per_trade": MAX_RISK_PER_TRADE,
        "total_picks": len(all_picks),
        "strategies_used": list(set(p["strategy"] for p in all_picks)),
        "symbols_covered": list(set(p["symbol"] for p in all_picks)),
        "picks": all_picks,
        "checks": [],
        "status": "ACTIVE",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Summary
    print(f"\n" + "=" * 80)
    print(f"  ROUND #{round_num} -- {len(all_picks)} PICKS LOCKED")
    by_cat = defaultdict(int)
    by_strat = defaultdict(int)
    for p in all_picks:
        by_cat[p["category"]] += 1
        by_strat[p["strategy"]] += 1

    print(f"  Categories: {dict(by_cat)}")
    print(f"  Strategies: {dict(by_strat)}")
    total_risk = sum(p["max_loss"] for p in all_picks)
    print(f"  Total portfolio risk: ${total_risk:,.0f} "
          f"({total_risk/PORTFOLIO_SIZE*100:.1f}% of ${PORTFOLIO_SIZE:,})")
    print(f"\n  Check: python challenge_v3.py check")
    print("=" * 80)
    return challenge


def check_round():
    if not CHALLENGE_FILE.exists():
        print("No active round. Run 'start' first.")
        return None

    with open(CHALLENGE_FILE) as f:
        challenge = json.load(f)

    picks = challenge["picks"]
    if not picks:
        print("No picks.")
        return None

    start_utc = challenge.get("start_utc", datetime.now(timezone.utc).isoformat())
    try:
        start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    except Exception:
        start_dt = datetime.now(timezone.utc)
    elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60

    t = now_est()
    print("\n" + "=" * 80)
    print(f"  V3 INSTITUTIONAL -- ROUND #{challenge.get('round', '?')}")
    print(f"  Started: {challenge.get('start_time_est', '?')}")
    print(f"  Now:     {est_str(t)}")
    print(f"  Elapsed: {elapsed_min:.0f} min | Portfolio: ${challenge.get('portfolio_size', PORTFOLIO_SIZE):,}")
    print("=" * 80)

    unique_syms = list(set(p["symbol"] for p in picks))
    print(f"\n  Fetching real-time prices...")

    current_prices = {}
    period_highs = {}
    period_lows = {}

    # CRITICAL: Only check price action SINCE entry time (honest results)
    entry_cutoff = start_dt

    for interval, period in [("5m", "1d"), ("15m", "5d"), ("1d", "5d")]:
        try:
            raw = yf.download(" ".join(unique_syms), period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            if raw is not None and not raw.empty:
                for sym in unique_syms:
                    if sym in current_prices:
                        continue
                    try:
                        if len(unique_syms) == 1:
                            df = raw
                        else:
                            df = raw[sym] if sym in raw.columns.get_level_values(0) else None
                        if df is not None and not df.empty:
                            df = df.dropna(subset=["Close"])
                            if len(df) > 0:
                                current_prices[sym] = float(df["Close"].iloc[-1])
                                # Only use candles AFTER entry for TP/SL checking
                                if df.index.tz is not None:
                                    cutoff = entry_cutoff
                                else:
                                    cutoff = entry_cutoff.replace(tzinfo=None)
                                post_entry = df[df.index >= cutoff]
                                if len(post_entry) > 0:
                                    period_highs[sym] = float(post_entry["High"].max())
                                    period_lows[sym] = float(post_entry["Low"].min())
                                else:
                                    # No candles after entry yet, use latest
                                    period_highs[sym] = float(df["High"].iloc[-1])
                                    period_lows[sym] = float(df["Low"].iloc[-1])
                    except Exception:
                        continue
            if len(current_prices) >= len(unique_syms) * 0.7:
                print(f"  Got {len(current_prices)}/{len(unique_syms)} prices via {interval}")
                break
        except Exception:
            continue

    results = []
    for p in picks:
        sym = p["symbol"]
        entry = p["entry_price"]
        tp = p["take_profit"]
        sl = p["stop_loss"]
        sig = p["signal_type"]
        pos_size = p.get("position_size", 2000)
        current = current_prices.get(sym)
        day_high = period_highs.get(sym, current)
        day_low = period_lows.get(sym, current)

        if current is None or entry <= 0:
            results.append({**p, "current_price": None, "pnl_pct": 0,
                            "pnl_dollar": 0, "status": "NO_DATA",
                            "check_time_est": est_str()})
            continue

        status = "OPEN"
        exit_price = current

        if sig == "BUY":
            if tp and day_high >= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_low <= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl_pct = (exit_price - entry) / entry
        else:
            if tp and day_low <= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_high >= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl_pct = (entry - exit_price) / entry

        # Dollar P&L based on actual position size
        pnl_dollar = pnl_pct * pos_size

        results.append({
            **p,
            "current_price": round(current, 8),
            "exit_price": round(exit_price, 8),
            "pnl_pct": round(pnl_pct * 100, 4),
            "pnl_dollar": round(pnl_dollar, 2),
            "status": status,
            "check_time_est": est_str(),
        })

    # Leaderboard
    by_strat = defaultdict(list)
    for r in results:
        by_strat[r["strategy"]].append(r)

    strat_scores = []
    for strat, sr in by_strat.items():
        valid = [r for r in sr if r["status"] != "NO_DATA"]
        if not valid:
            continue
        wins = sum(1 for r in valid if r["pnl_pct"] > 0)
        tp_hits = sum(1 for r in valid if r["status"] == "TP_HIT")
        sl_hits = sum(1 for r in valid if r["status"] == "SL_HIT")
        total_pnl = sum(r["pnl_dollar"] for r in valid)
        wr = wins / len(valid) * 100 if valid else 0
        strat_scores.append({
            "strategy": strat,
            "picks": len(valid),
            "winning": wins,
            "losing": len(valid) - wins,
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "win_rate": round(wr, 1),
            "total_pnl": round(total_pnl, 2),
        })

    strat_scores.sort(key=lambda x: x["total_pnl"], reverse=True)

    print(f"\n  STRATEGY LEADERBOARD:")
    print(f"  {'#':>3s} {'Strategy':>25s} {'Picks':>5s} {'W':>3s} {'L':>3s} "
          f"{'WR%':>5s} {'TP':>3s} {'SL':>3s} {'P&L':>10s}")
    print(f"  {'-'*3} {'-'*25} {'-'*5} {'-'*3} {'-'*3} "
          f"{'-'*5} {'-'*3} {'-'*3} {'-'*10}")

    for i, s in enumerate(strat_scores, 1):
        medal = {1: " [1ST]", 2: " [2ND]", 3: " [3RD]"}.get(i, "")
        print(f"  {i:>3d} {s['strategy']:>25s} {s['picks']:>4d} {s['winning']:>3d} "
              f"{s['losing']:>3d} {s['win_rate']:>4.0f}% {s['tp_hits']:>3d} "
              f"{s['sl_hits']:>3d} ${s['total_pnl']:>+9.2f}{medal}")

    all_pnl = sum(s["total_pnl"] for s in strat_scores)
    all_n = sum(s["picks"] for s in strat_scores)
    all_w = sum(s["winning"] for s in strat_scores)
    wr = all_w / all_n * 100 if all_n > 0 else 0
    pnl_pct = all_pnl / PORTFOLIO_SIZE * 100

    print(f"\n  PORTFOLIO: ${all_pnl:+,.2f} ({pnl_pct:+.2f}%) | "
          f"{all_n} picks, {all_w}W/{all_n-all_w}L ({wr:.1f}% WR)")

    # Asset class
    print(f"\n  BY ASSET CLASS:")
    by_cat = defaultdict(lambda: {"pnl": 0, "n": 0, "w": 0})
    for r in results:
        if r["status"] == "NO_DATA":
            continue
        cat = r["category"]
        by_cat[cat]["n"] += 1
        by_cat[cat]["pnl"] += r["pnl_dollar"]
        if r["pnl_pct"] > 0:
            by_cat[cat]["w"] += 1
    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        wr2 = d["w"] / d["n"] * 100 if d["n"] > 0 else 0
        print(f"    {cat:>10s}: {d['n']:>3d} picks, {wr2:>5.1f}% WR, ${d['pnl']:>+10.2f}")

    # Individual picks
    print(f"\n  ALL PICKS:")
    for r in sorted(results, key=lambda x: x.get("pnl_dollar", 0), reverse=True):
        if r["status"] == "NO_DATA":
            continue
        status_icon = {"TP_HIT": "++", "SL_HIT": "XX", "OPEN": ".."}[r["status"]]
        print(f"  {status_icon} {r['signal_type']:>4s} {r['name']:>12s} ({r['symbol']}) "
              f"Entry={r['entry_price']:.8g} Now={r['current_price']:.8g} "
              f"{r['pnl_pct']:>+7.3f}% ${r['pnl_dollar']:>+8.2f} "
              f"[{r['strategy']}|{r['timeframe']}] {r['status']}")

    # Save check
    check_entry = {
        "check_time_est": est_str(),
        "elapsed_min": round(elapsed_min, 1),
        "portfolio_pnl": round(all_pnl, 2),
        "portfolio_pnl_pct": round(pnl_pct, 4),
        "win_rate": round(wr, 1),
        "strategy_scores": strat_scores,
    }
    challenge["checks"].append(check_entry)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    if elapsed_min >= 115:
        print(f"\n  {'='*60}")
        print(f"  FINAL VERDICT -- ROUND #{challenge.get('round', '?')}")
        print(f"  Portfolio P&L: ${all_pnl:+,.2f} ({pnl_pct:+.2f}%)")
        if all_pnl > 0:
            print(f"  VERDICT: PROFITABLE!")
        else:
            print(f"  VERDICT: LOSING -- restart recommended")
        print(f"  {'='*60}")
        challenge["status"] = "COMPLETED"
        challenge["final_pnl"] = round(all_pnl, 2)
        with open(CHALLENGE_FILE, "w") as f:
            json.dump(challenge, f, indent=2, default=str)
        save_to_history(challenge)

    print("=" * 80)
    return strat_scores


def restart_round():
    if CHALLENGE_FILE.exists():
        with open(CHALLENGE_FILE) as f:
            old = json.load(f)
        old["status"] = "ABANDONED"
        save_to_history(old)
        print(f"  Archived round #{old.get('round', '?')}")
    return start_round()


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_to_history(ch):
    history = load_history()
    history.append({
        "round": ch.get("round"),
        "version": ch.get("version", "V3"),
        "start": ch.get("start_time_est"),
        "end": est_str(),
        "status": ch.get("status"),
        "picks": ch.get("total_picks", 0),
        "pnl": ch.get("final_pnl", 0),
        "strategies": ch.get("strategies_used", []),
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python challenge_v3.py [start|check|restart|history]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_round()
    elif cmd == "check":
        check_round()
    elif cmd == "restart":
        restart_round()
    elif cmd == "history":
        show_history() if "show_history" in dir() else print("Use check/start")
    else:
        print(f"Unknown: {cmd}")

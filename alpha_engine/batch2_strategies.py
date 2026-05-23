"""
BATCH 2: 10 new candidate strategies for survivor backtest.
Run: py alpha_engine/batch2_runner.py
"""
import numpy as np
import pandas as pd


def stochastic_oversold_mr(df, k_period=14, d_period=3, sma_period=200):
    """Slow Stochastic oversold mean reversion. Lane 1984."""
    if len(df) < sma_period + 10:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    hh = pd.Series(high).rolling(k_period).max().values
    ll = pd.Series(low).rolling(k_period).min().values
    denom = hh - ll
    denom[denom == 0] = np.nan
    stoch_k = 100 * (close - ll) / denom
    stoch_d = pd.Series(stoch_k).rolling(d_period).mean().values
    sma = pd.Series(close).rolling(sma_period).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(sma_period + 1, n):
        if np.isnan(stoch_k[i]) or np.isnan(stoch_d[i]) or np.isnan(sma[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if stoch_k[i - 1] < stoch_d[i - 1] and stoch_k[i] >= stoch_d[i] and stoch_k[i] < 25 and close[i] > sma[i]:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or stoch_k[i] > 80 or days >= 12:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else ("overbought" if stoch_k[i] > 80 else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def roc_exhaustion(df, roc_period=10, roc_threshold=-8.0, sma_period=200):
    """Rate-of-Change exhaustion reversal."""
    if len(df) < sma_period + 10:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    roc = np.full(n, np.nan)
    for i in range(roc_period, n):
        if close[i - roc_period] != 0:
            roc[i] = ((close[i] - close[i - roc_period]) / close[i - roc_period]) * 100
    sma = pd.Series(close).rolling(sma_period).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(sma_period + 1, n):
        if np.isnan(roc[i]) or np.isnan(roc[i - 1]) or np.isnan(sma[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if roc[i - 1] < roc_threshold and roc[i] > roc[i - 1] and close[i] > sma[i] * 0.92:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or roc[i] > 5 or days >= 15:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else ("roc_exit" if roc[i] > 5 else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def mfi_reversal(df, mfi_period=14, oversold=20, overbought=80):
    """Money Flow Index oversold reversal. Quong & Soudack 1989."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    pos_mf = np.zeros(n)
    neg_mf = np.zeros(n)
    for i in range(1, n):
        if tp[i] > tp[i - 1]:
            pos_mf[i] = raw_mf[i]
        elif tp[i] < tp[i - 1]:
            neg_mf[i] = raw_mf[i]
    pos_sum = pd.Series(pos_mf).rolling(mfi_period).sum().values
    neg_sum = pd.Series(neg_mf).rolling(mfi_period).sum().values
    neg_sum[neg_sum == 0] = 1e-10
    mfr = pos_sum / neg_sum
    mfi = 100 - (100 / (1 + mfr))
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(mfi[i]) or np.isnan(mfi[i - 1]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if mfi[i - 1] < oversold and mfi[i] >= oversold and close[i] > sma200[i]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif mfi[i - 1] > overbought and mfi[i] <= overbought and close[i] < sma200[i]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_v = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl_v = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp_v) or (side == "SHORT" and close[i] <= tp_v)
            hit_sl = (side == "LONG" and close[i] <= sl_v) or (side == "SHORT" and close[i] >= sl_v)
            if hit_tp or hit_sl or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def percentile_rank_mr(df, lookback=100, entry_pctl=5, exit_pctl=50):
    """100-day percentile rank < 5 mean reversion. Connors & Alvarez."""
    if len(df) < lookback + 200:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    pctl = np.full(n, np.nan)
    for i in range(lookback, n):
        window = close[i - lookback:i]
        pctl[i] = (np.sum(window < close[i]) / lookback) * 100
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(pctl[i]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if pctl[i] < entry_pctl and close[i] > sma200[i] * 0.9:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or pctl[i] > exit_pctl or days >= 12:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else ("pctl_exit" if pctl[i] > exit_pctl else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def rsi2_bb_squeeze(df, bb_period=20, bb_std=2.0):
    """RSI(2)<10 + inside Bollinger Band. Connors + Bollinger fusion."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=2, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=2, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi2 = 100 - 100 / (1 + rs)
    bb_mid = pd.Series(close).rolling(bb_period).mean().values
    bb_std_arr = pd.Series(close).rolling(bb_period).std().values
    bb_lower = bb_mid - bb_std * bb_std_arr
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(rsi2[i]) or np.isnan(bb_lower[i]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if rsi2[i] < 10 and close[i] <= bb_lower[i] * 1.01 and close[i] > sma200[i]:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or rsi2[i] > 70 or days >= 10:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else ("rsi_exit" if rsi2[i] > 70 else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def hammer_volume(df, sma_period=50):
    """Hammer candlestick + volume spike at 20-day low. Nison 1991."""
    if len(df) < sma_period + 30:
        return []
    close = df["Close"].values.astype(float)
    opn = df["Open"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)
    vol_avg = pd.Series(volume).rolling(20).mean().values
    low20 = pd.Series(close).rolling(20).min().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(sma_period + 1, n):
        if atr[i] <= 0 or vol_avg[i] <= 0:
            continue
        if not in_trade:
            body = abs(close[i] - opn[i])
            candle_range = high[i] - low[i]
            lower_shadow = min(close[i], opn[i]) - low[i]
            if candle_range <= 0:
                continue
            is_hammer = (lower_shadow > 2 * body) and (body < candle_range * 0.35) and (close[i] >= opn[i])
            at_low = close[i] <= low20[i] * 1.02
            vol_spike = volume[i] > vol_avg[i] * 1.3
            if is_hammer and at_low and vol_spike:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or days >= 12:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def atr_channel_mr(df, sma_period=50, atr_mult=2.5):
    """Price 2.5x ATR below 50 SMA = extreme displacement reversal."""
    if len(df) < sma_period + 20:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    sma = pd.Series(close).rolling(sma_period).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(sma_period + 1, n):
        if np.isnan(sma[i]) or atr[i] <= 0:
            continue
        lower_band = sma[i] - atr_mult * atr[i]
        upper_band = sma[i] + atr_mult * atr[i]
        if not in_trade:
            if close[i] < lower_band and close[i] > close[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif close[i] > upper_band and close[i] < close[i - 1]:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_v = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl_v = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp_v) or (side == "SHORT" and close[i] <= tp_v)
            hit_sl = (side == "LONG" and close[i] <= sl_v) or (side == "SHORT" and close[i] >= sl_v)
            mean_revert = (side == "LONG" and close[i] >= sma[i]) or (side == "SHORT" and close[i] <= sma[i])
            if hit_tp or hit_sl or mean_revert or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("mean_revert" if mean_revert else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def consecutive_down_rsi(df, min_down_days=4, rsi_threshold=35):
    """4+ consecutive down days + RSI(14)<35 exhaustion. Connors variant."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0).astype(float)
    loss = np.where(delta < 0, -delta, 0).astype(float)
    avg_gain = pd.Series(gain).ewm(span=14, adjust=False).mean().values
    avg_loss = pd.Series(loss).ewm(span=14, adjust=False).mean().values
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi14 = 100 - 100 / (1 + rs)
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    consec_down = np.zeros(n, dtype=int)
    for i in range(1, n):
        if close[i] < close[i - 1]:
            consec_down[i] = consec_down[i - 1] + 1
        else:
            consec_down[i] = 0
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(rsi14[i]) or np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if consec_down[i] >= min_down_days and rsi14[i] < rsi_threshold and close[i] > sma200[i]:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or close[i] > close[i - 1] or days >= 10:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else ("up_day" if close[i] > close[i - 1] else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def obv_divergence_mr(df, lookback=20):
    """OBV bullish divergence: price new low but OBV higher. Granville 1963."""
    if len(df) < 220:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    volume = df["Volume"].values.astype(float)
    n = len(close)
    obv = np.zeros(n)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    sma200 = pd.Series(close).rolling(200).mean().values
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    price_low = pd.Series(close).rolling(lookback).min().values
    signals = []
    in_trade = False
    entry_price = entry_idx = 0
    for i in range(201, n):
        if np.isnan(sma200[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            at_price_low = close[i] <= price_low[i] * 1.01
            obv_window = obv[max(0, i - lookback):i + 1]
            obv_not_low = obv[i] > np.min(obv_window) * 1.05 if len(obv_window) > 0 else False
            if at_price_low and obv_not_low and close[i] > sma200[i] * 0.9:
                in_trade, entry_price, entry_idx = True, close[i], i
        else:
            days = i - entry_idx
            tp = entry_price + 3 * atr[entry_idx]
            sl = entry_price - 2 * atr[entry_idx]
            if close[i] >= tp or close[i] <= sl or days >= 15:
                pnl = (close[i] - entry_price) / entry_price
                reason = "tp" if close[i] >= tp else ("sl" if close[i] <= sl else "time_exit")
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


def mean_reversion_zscore(df, lookback=50, z_entry=-2.5, z_exit=0.0):
    """Close z-score < -2.5 vs 50d mean, exit at 0. Pure statistical MR."""
    if len(df) < lookback + 20:
        return []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)
    sma = pd.Series(close).rolling(lookback).mean().values
    std_arr = pd.Series(close).rolling(lookback).std().values
    zscore = np.full(n, np.nan)
    for i in range(lookback, n):
        if std_arr[i] > 0:
            zscore[i] = (close[i] - sma[i]) / std_arr[i]
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    signals = []
    in_trade = False
    side = None
    entry_price = entry_idx = 0
    for i in range(lookback + 1, n):
        if np.isnan(zscore[i]) or atr[i] <= 0:
            continue
        if not in_trade:
            if zscore[i] < z_entry:
                in_trade, side, entry_price, entry_idx = True, "LONG", close[i], i
            elif zscore[i] > -z_entry:
                in_trade, side, entry_price, entry_idx = True, "SHORT", close[i], i
        else:
            days = i - entry_idx
            tp_v = entry_price + 3 * atr[entry_idx] if side == "LONG" else entry_price - 3 * atr[entry_idx]
            sl_v = entry_price - 2 * atr[entry_idx] if side == "LONG" else entry_price + 2 * atr[entry_idx]
            hit_tp = (side == "LONG" and close[i] >= tp_v) or (side == "SHORT" and close[i] <= tp_v)
            hit_sl = (side == "LONG" and close[i] <= sl_v) or (side == "SHORT" and close[i] >= sl_v)
            z_revert = (side == "LONG" and zscore[i] >= z_exit) or (side == "SHORT" and zscore[i] <= -z_exit)
            if hit_tp or hit_sl or z_revert or days >= 15:
                pnl = ((close[i] - entry_price) / entry_price) if side == "LONG" else ((entry_price - close[i]) / entry_price)
                reason = "tp" if hit_tp else ("sl" if hit_sl else ("z_exit" if z_revert else "time_exit"))
                signals.append({"entry_idx": entry_idx, "exit_idx": i, "entry_price": entry_price,
                                "exit_price": close[i], "pnl": pnl, "days": days, "exit_reason": reason})
                in_trade = False
    return signals


BATCH2_STRATEGIES = {
    "stochastic_oversold_mr": {"func": stochastic_oversold_mr, "desc": "Slow Stochastic %K<%D cross below 20 + SMA200 (Lane 1984)"},
    "roc_exhaustion": {"func": roc_exhaustion, "desc": "ROC < -8% exhaustion reversal (Appel & Hitschler 2005)"},
    "mfi_reversal": {"func": mfi_reversal, "desc": "Money Flow Index < 20 oversold reversal (Quong & Soudack 1989)"},
    "percentile_rank_mr": {"func": percentile_rank_mr, "desc": "100-day percentile rank < 5 mean reversion (Connors)"},
    "rsi2_bb_squeeze": {"func": rsi2_bb_squeeze, "desc": "RSI(2)<10 + lower Bollinger Band (Connors + Bollinger)"},
    "hammer_volume": {"func": hammer_volume, "desc": "Hammer candlestick + volume spike at 20-day low (Nison 1991)"},
    "atr_channel_mr": {"func": atr_channel_mr, "desc": "Price 2.5x ATR below 50 SMA extreme displacement reversal"},
    "consecutive_down_rsi": {"func": consecutive_down_rsi, "desc": "4+ down days + RSI(14)<35 exhaustion (Connors variant)"},
    "obv_divergence_mr": {"func": obv_divergence_mr, "desc": "OBV bullish divergence at price low (Granville 1963)"},
    "mean_reversion_zscore": {"func": mean_reversion_zscore, "desc": "Z-score < -2.5 vs 50d mean, exit at 0 (statistical MR)"},
}

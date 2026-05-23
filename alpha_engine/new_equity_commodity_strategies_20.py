"""
ALPHA_ENGINE -- 20 New Equity/ETF/Commodity Strategies
=======================================================
10 equity/ETF + 10 commodity strategies with academic backing.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import EQUITY_SYMBOLS, COMMODITY_SYMBOLS, ETF_SYMBOLS, CATEGORY_RISK, SECTOR_ETFS
from indicators import sma, ema, rsi, atr, adx, macd, bollinger_bands, volume_ratio, zscore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _equity_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
                  tp_mult: float = 2.5, sl_mult: float = 1.5,
                  direction: str = "BUY") -> tuple[float, float, float]:
    atr_val = atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp_dist = min(tp_mult * current_atr, price * 0.08)
    sl_dist = min(sl_mult * current_atr, price * 0.05)
    if direction == "BUY":
        return price, price + tp_dist, price - sl_dist
    return price, price - tp_dist, price + sl_dist


def _commodity_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
                     tp_mult: float = 2.0, sl_mult: float = 1.5,
                     direction: str = "BUY") -> tuple[float, float, float]:
    atr_val = atr(high, low, close, 14)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp_dist = min(tp_mult * current_atr, price * 0.05)
    sl_dist = min(sl_mult * current_atr, price * 0.03)
    if direction == "BUY":
        return price, price + tp_dist, price - sl_dist
    return price, price - tp_dist, price + sl_dist


def _rr(entry: float, tp: float, sl: float, direction: str = "BUY") -> float:
    if direction == "BUY":
        reward = tp - entry
        risk = entry - sl
    else:
        reward = entry - tp
        risk = sl - entry
    return reward / risk if risk > 0 else 0.0


# =========================================================================
# EQUITY/ETF STRATEGY 1: Post-Earnings Announcement Drift (PEAD)
# Reference: Bernard & Thomas (1989) JAR. 55-65% WR.
# =========================================================================
def post_earnings_drift(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY 3 days after an earnings gap-up (>3% on high volume). PEAD effect."""
    signals = []
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 10:
                continue
            close = df["Close"]
            volume = df["Volume"]
            high = df["High"]
            low = df["Low"]
            # Look for gap-up >= 3% 3 bars ago on volume > 2x avg
            if len(df) < 5:
                continue
            gap_bar = df.iloc[-4]
            prev_bar = df.iloc[-5]
            gap_pct = (gap_bar["Close"] - prev_bar["Close"]) / prev_bar["Close"]
            avg_vol = float(volume.iloc[-20:].mean()) if len(df) >= 20 else float(volume.mean())
            gap_vol_ratio = float(gap_bar["Volume"]) / avg_vol if avg_vol > 0 else 0
            if gap_pct < 0.03 or gap_vol_ratio < 2.0:
                continue
            # Price continuing higher after gap
            if float(close.iloc[-1]) <= float(close.iloc[-4]):
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.5, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "post_earnings_drift",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.62, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"PEAD: gap-up {gap_pct:.1%} on {gap_vol_ratio:.1f}x volume 3 days ago, price continuing",
                "timeframe": "1d",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 2: 52-Week High Breakout
# Reference: George & Hwang (2004) JF. Sharpe 0.89.
# =========================================================================
def week52_high_breakout(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY when stock breaks above 52-week high on volume >1.5x avg."""
    signals = []
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 252:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            high52 = float(high.iloc[-252:-1].max())
            curr_close = float(close.iloc[-1])
            avg_vol = float(volume.iloc[-20:].mean())
            curr_vol = float(volume.iloc[-1])
            if curr_close <= high52:
                continue
            if avg_vol <= 0 or (curr_vol / avg_vol) < 1.5:
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 3.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "week52_high_breakout",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.65, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"52-week high breakout at {curr_close:.2f} (prev high {high52:.2f}) on {curr_vol/avg_vol:.1f}x volume",
                "timeframe": "1d",
                "max_hold_bars": 20,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 3: Low Volatility Factor
# Reference: Baker, Bradley, Wurgler (2011) FAJ.
# =========================================================================
def low_volatility_factor(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Buy 5 least-volatile stocks (lowest normalized 20-day std dev)."""
    signals = []
    vols = {}
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 25:
                continue
            close = df["Close"]
            price = float(close.iloc[-1])
            if price <= 0:
                continue
            std20 = float(close.pct_change().iloc[-20:].std())
            vols[symbol] = std20
        except Exception:
            continue
    if not vols:
        return signals
    sorted_syms = sorted(vols, key=lambda s: vols[s])[:5]
    for symbol in sorted_syms:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 25:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            # Only enter if above 50d SMA
            s50 = sma(close, 50)
            if float(close.iloc[-1]) < float(s50.iloc[-1]):
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "low_volatility_factor",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Low-vol anomaly: 20d vol={vols[symbol]:.4f}, in top-5 least volatile",
                "timeframe": "1d",
                "max_hold_bars": 30,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 4: Short Interest Squeeze
# Reference: Desai, Ramesh, Thiagarajan (2002). 58-64% WR.
# =========================================================================
def short_interest_squeeze(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY when volume >3x avg AND price rises >2% in one day (short covering)."""
    signals = []
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 25:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            avg_vol = float(volume.iloc[-20:].mean())
            curr_vol = float(volume.iloc[-1])
            day_chg = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])
            if avg_vol <= 0 or (curr_vol / avg_vol) < 3.0:
                continue
            if day_chg < 0.02:
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.5, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "short_interest_squeeze",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.61, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Short squeeze: {curr_vol/avg_vol:.1f}x volume, +{day_chg:.1%} day move",
                "timeframe": "1d",
                "max_hold_bars": 5,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 5: Sector Rotation ETF
# Reference: Moskowitz & Grinblatt (1999) JF.
# =========================================================================
def sector_rotation_etf(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Buy ETF with strongest 4-week momentum vs SPY (excess return >2%)."""
    signals = []
    spy_df = data.get("SPY")
    if spy_df is None or len(spy_df) < 25:
        return signals
    spy_ret = (float(spy_df["Close"].iloc[-1]) - float(spy_df["Close"].iloc[-21])) / float(spy_df["Close"].iloc[-21])

    best_sym = None
    best_excess = -999
    for symbol in SECTOR_ETFS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 25:
                continue
            ret4w = (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-21])) / float(df["Close"].iloc[-21])
            excess = ret4w - spy_ret
            if excess > best_excess:
                best_excess = excess
                best_sym = symbol
        except Exception:
            continue

    if best_sym is None or best_excess < 0.02:
        return signals

    try:
        df = data.get(best_sym)
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        entry, tp, sl = _equity_tp_sl(close, high, low, 2.5, 1.5)
        rr = _rr(entry, tp, sl)
        if rr < 1.2:
            return signals
        signals.append({
            "strategy": "sector_rotation_etf",
            "symbol": best_sym,
            "category": "etf",
            "signal_type": "BUY",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": min(0.63, 0.85),
            "risk_reward": round(rr, 2),
            "reason": f"Sector leader: {best_excess:.1%} excess return vs SPY over 4 weeks",
            "timeframe": "1d",
            "max_hold_bars": 21,
            "timestamp": _now_iso(),
        })
    except Exception:
        pass
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 6: Bollinger Band Squeeze Breakout
# Reference: Connors & Raschke (1995). 68-72% follow-through.
# =========================================================================
def bollinger_band_squeeze_stocks(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY on first breakout after BB squeeze (width < 5th percentile of 252d)."""
    signals = []
    for symbol in list(EQUITY_SYMBOLS.keys()) + list(ETF_SYMBOLS.keys()):
        try:
            df = data.get(symbol)
            if df is None or len(df) < 60:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            bb_upper, bb_mid, bb_lower = bollinger_bands(close, 20, 2.0)
            width = (bb_upper - bb_lower) / bb_mid
            lookback = min(252, len(width))
            pct5 = float(np.percentile(width.dropna().iloc[-lookback:], 5))
            curr_width = float(width.iloc[-1])
            prev_width = float(width.iloc[-2])
            curr_close = float(close.iloc[-1])
            curr_upper = float(bb_upper.iloc[-1])
            # Squeeze: was below 5th pct, now breaking out above upper band
            if prev_width > pct5 * 1.1 or curr_close <= curr_upper:
                continue
            if curr_width >= pct5:
                continue
            is_etf = symbol in ETF_SYMBOLS
            cat = "etf" if is_etf else EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock")
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.5, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "bollinger_band_squeeze_stocks",
                "symbol": symbol,
                "category": cat,
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.68, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"BB squeeze breakout: width={curr_width:.4f} (5th pct={pct5:.4f}), close above upper band",
                "timeframe": "1d",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 7: Reversal After 3 Consecutive Down Days
# Reference: Connors & Alvarez (2009). 64% WR.
# =========================================================================
def reversal_after_3_down_days(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY after 3 consecutive down days, stock above 200d SMA."""
    signals = []
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 205:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            s200 = sma(close, 200)
            if float(close.iloc[-1]) < float(s200.iloc[-1]):
                continue
            # 3 consecutive down days
            if not (float(close.iloc[-2]) < float(close.iloc[-3]) and
                    float(close.iloc[-3]) < float(close.iloc[-4]) and
                    float(close.iloc[-4]) < float(close.iloc[-5])):
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 45:
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "reversal_after_3_down_days",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.64, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"3 consecutive down days above 200d SMA, RSI={rsi_val:.1f}",
                "timeframe": "1d",
                "max_hold_bars": 5,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 8: Dividend Capture (Seasonal Proxy)
# Reference: Kalay (1982) JFE.
# =========================================================================
def dividend_capture_strategy(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Buy high-yield proxies at turn-of-month + uptrend for dividend capture."""
    signals = []
    today = datetime.now(timezone.utc)
    # Approximate ex-div: near start/end of month
    dom = today.day
    if dom not in list(range(1, 8)) + list(range(24, 32)):
        return signals
    # High-yield equity proxies: stable, above 50d SMA, RSI 40-60
    for symbol in EQUITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 55:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            s50 = sma(close, 50)
            if float(close.iloc[-1]) < float(s50.iloc[-1]):
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])
            if not (40 <= rsi_val <= 60):
                continue
            # Low recent volatility (stable stock = likely dividend payer)
            std10 = float(close.pct_change().iloc[-10:].std())
            if std10 > 0.025:
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "dividend_capture_strategy",
                "symbol": symbol,
                "category": EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock"),
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.58, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Dividend capture proxy: turn-of-month day {dom}, RSI={rsi_val:.1f}, low vol",
                "timeframe": "1d",
                "max_hold_bars": 7,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 9: Golden Cross 50/200
# Reference: Glabadanidis (2015) IRFA. 65-70% WR.
# =========================================================================
def golden_cross_200d(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY when 50d SMA crosses above 200d SMA with RSI 45-60 and ADX>20."""
    signals = []
    for symbol in list(EQUITY_SYMBOLS.keys()) + list(ETF_SYMBOLS.keys()):
        try:
            df = data.get(symbol)
            if df is None or len(df) < 205:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            s50 = sma(close, 50)
            s200 = sma(close, 200)
            # Cross: yesterday below, today above
            if not (float(s50.iloc[-2]) < float(s200.iloc[-2]) and
                    float(s50.iloc[-1]) >= float(s200.iloc[-1])):
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])
            if not (45 <= rsi_val <= 60):
                continue
            adx_val = float(adx(high, low, close, 14).iloc[-1])
            if adx_val < 20:
                continue
            is_etf = symbol in ETF_SYMBOLS
            cat = "etf" if is_etf else EQUITY_SYMBOLS.get(symbol, {}).get("cat", "stock")
            entry, tp, sl = _equity_tp_sl(close, high, low, 3.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "golden_cross_200d",
                "symbol": symbol,
                "category": cat,
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.67, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Golden cross: 50d SMA crossed above 200d SMA, RSI={rsi_val:.1f}, ADX={adx_val:.1f}",
                "timeframe": "1d",
                "max_hold_bars": 60,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# EQUITY/ETF STRATEGY 10: Mean Reversion 2-Day (SPY/QQQ)
# Reference: Connors (2012). 72% WR on SPY since 2005.
# =========================================================================
def mean_reversion_2day(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY SPY/QQQ when RSI(2)<10 and price dropped >1.5% in a day."""
    signals = []
    for symbol in ["SPY", "QQQ"]:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 10:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            rsi2 = float(rsi(close, 2).iloc[-1])
            day_chg = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])
            if rsi2 >= 10 or day_chg > -0.015:
                continue
            entry, tp, sl = _equity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "mean_reversion_2day",
                "symbol": symbol,
                "category": "etf",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.72, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Mean reversion: RSI(2)={rsi2:.1f}, day change={day_chg:.1%}",
                "timeframe": "1d",
                "max_hold_bars": 4,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 1: Gold Real Yield Signal
# Reference: Erb & Harvey (2013) FAJ.
# =========================================================================
def gold_real_yield_signal(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY gold when TLT rises (yields falling) and gold near 20d SMA."""
    signals = []
    try:
        tlt = data.get("TLT")
        gc = data.get("GC=F")
        if tlt is None or gc is None or len(tlt) < 22 or len(gc) < 22:
            return signals
        tlt_close = tlt["Close"]
        gc_close = gc["Close"]
        # TLT rising = yields falling = gold bullish
        tlt_chg = (float(tlt_close.iloc[-1]) - float(tlt_close.iloc[-5])) / float(tlt_close.iloc[-5])
        if tlt_chg < 0.005:
            return signals
        gc_sma20 = float(sma(gc_close, 20).iloc[-1])
        gc_price = float(gc_close.iloc[-1])
        # Gold within 2% of 20d SMA (consolidating)
        if abs(gc_price - gc_sma20) / gc_sma20 > 0.02:
            return signals
        high = gc["High"]
        low = gc["Low"]
        entry, tp, sl = _commodity_tp_sl(gc_close, high, low, 2.0, 1.5)
        rr = _rr(entry, tp, sl)
        if rr < 1.2:
            return signals
        signals.append({
            "strategy": "gold_real_yield_signal",
            "symbol": "GC=F",
            "category": "commodity",
            "signal_type": "BUY",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": min(0.63, 0.85),
            "risk_reward": round(rr, 2),
            "reason": f"Falling real yields (TLT +{tlt_chg:.1%} 5d), gold consolidating near 20d SMA",
            "timeframe": "1d",
            "max_hold_bars": 14,
            "timestamp": _now_iso(),
        })
    except Exception:
        pass
    return signals


# =========================================================================
# COMMODITY STRATEGY 2: CCI Bounce
# Reference: Lambert (1980). 57-63% WR.
# =========================================================================
def commodity_channel_index_bounce(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY when CCI(20) crosses back above -100 from oversold."""
    signals = []
    for symbol in COMMODITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 25:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            # CCI = (Typical Price - SMA) / (0.015 * Mean Deviation)
            tp_series = (high + low + close) / 3
            sma20 = sma(tp_series, 20)
            mean_dev = tp_series.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
            cci = (tp_series - sma20) / (0.015 * mean_dev)
            if len(cci.dropna()) < 3:
                continue
            prev_cci = float(cci.iloc[-2])
            curr_cci = float(cci.iloc[-1])
            # Cross above -100
            if not (prev_cci < -100 and curr_cci >= -100):
                continue
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "commodity_channel_index_bounce",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"CCI crossed above -100 ({prev_cci:.1f} -> {curr_cci:.1f}), oversold reversal",
                "timeframe": "1d",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 3: Contango/Backwardation Roll Yield
# Reference: Gorton & Rouwenhorst (2006) FAJ.
# =========================================================================
def contango_roll_yield(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY when commodity price above 3m SMA (backwardation-like, positive roll yield)."""
    signals = []
    for symbol in COMMODITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 65:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            sma63 = sma(close, 63)
            curr = float(close.iloc[-1])
            sma_val = float(sma63.iloc[-1])
            # Backwardation proxy: spot above 3m average
            if curr <= sma_val * 1.005:
                continue
            # Momentum confirmation: also above 20d SMA
            sma20_val = float(sma(close, 20).iloc[-1])
            if curr < sma20_val:
                continue
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "contango_roll_yield",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Backwardation proxy: price {curr:.2f} > 3m SMA {sma_val:.2f} (+{(curr/sma_val-1):.1%})",
                "timeframe": "1d",
                "max_hold_bars": 14,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 4: Precious Metals Gold/Silver Ratio
# Reference: Tully & Lucey (2007) RP.
# =========================================================================
def precious_metals_correlation_pair(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY Silver when Gold/Silver ratio > 90 (Silver cheap relative to Gold)."""
    signals = []
    try:
        gc = data.get("GC=F")
        si = data.get("SI=F")
        if gc is None or si is None or len(gc) < 5 or len(si) < 5:
            return signals
        gold_price = float(gc["Close"].iloc[-1])
        silver_price = float(si["Close"].iloc[-1])
        if silver_price <= 0:
            return signals
        ratio = gold_price / silver_price
        if ratio <= 90:
            return signals
        close = si["Close"]
        high = si["High"]
        low = si["Low"]
        entry, tp, sl = _commodity_tp_sl(close, high, low, 2.5, 1.5)
        rr = _rr(entry, tp, sl)
        if rr < 1.2:
            return signals
        signals.append({
            "strategy": "precious_metals_correlation_pair",
            "symbol": "SI=F",
            "category": "commodity",
            "signal_type": "BUY",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": min(0.62, 0.85),
            "risk_reward": round(rr, 2),
            "reason": f"Gold/Silver ratio={ratio:.1f} > 90, Silver historically cheap vs Gold",
            "timeframe": "1d",
            "max_hold_bars": 21,
            "timestamp": _now_iso(),
        })
    except Exception:
        pass
    return signals


# =========================================================================
# COMMODITY STRATEGY 5: Energy EIA Inventory Proxy
# Reference: Ye, Zyren, Shore (2002).
# =========================================================================
def energy_eia_inventory_proxy(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY energy commodities rising >1.5% mid-week (EIA Wednesday proxy)."""
    signals = []
    today = datetime.now(timezone.utc)
    # Wednesday = 2 in Python's weekday()
    if today.weekday() != 2:
        return signals
    energy_syms = [s for s in COMMODITY_SYMBOLS if any(x in s for x in ["CL=F", "NG=F", "HO=F", "RB=F"])]
    for symbol in energy_syms:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 5:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            day_chg = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])
            if day_chg < 0.015:
                continue
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "energy_eia_inventory_proxy",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"EIA Wednesday proxy: energy up +{day_chg:.1%} today",
                "timeframe": "1d",
                "max_hold_bars": 3,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 6: Copper Economic Cycle ("Dr. Copper")
# Reference: Goss & Avsar (2013).
# =========================================================================
def copper_economic_cycle(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY Copper when new 20-day high AND above 50d SMA."""
    signals = []
    try:
        df = data.get("HG=F")
        if df is None or len(df) < 55:
            return signals
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        high20 = float(high.iloc[-20:].max())
        curr_close = float(close.iloc[-1])
        s50 = float(sma(close, 50).iloc[-1])
        if curr_close < high20:
            return signals
        if curr_close < s50:
            return signals
        entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
        rr = _rr(entry, tp, sl)
        if rr < 1.2:
            return signals
        signals.append({
            "strategy": "copper_economic_cycle",
            "symbol": "HG=F",
            "category": "commodity",
            "signal_type": "BUY",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": min(0.63, 0.85),
            "risk_reward": round(rr, 2),
            "reason": f"Dr. Copper: new 20d high at {curr_close:.2f}, above 50d SMA {s50:.2f}",
            "timeframe": "1d",
            "max_hold_bars": 14,
            "timestamp": _now_iso(),
        })
    except Exception:
        pass
    return signals


# =========================================================================
# COMMODITY STRATEGY 7: Agricultural Weather Premium
# Reference: Roll (1984) AER.
# =========================================================================
def agricultural_weather_premium(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY agricultural commodities in planting months on breakout with volume."""
    signals = []
    month = datetime.now(timezone.utc).month
    # Planting months: March-June for US corn/soy/wheat
    if month not in [3, 4, 5, 6]:
        return signals
    ag_syms = [s for s in COMMODITY_SYMBOLS if any(x in s for x in ["ZC=F", "ZW=F", "ZS=F"])]
    for symbol in ag_syms:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 15:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            high10 = float(high.iloc[-10:].max())
            curr_close = float(close.iloc[-1])
            if curr_close < high10:
                continue
            avg_vol = float(volume.iloc[-10:].mean())
            curr_vol = float(volume.iloc[-1])
            if avg_vol <= 0 or (curr_vol / avg_vol) < 1.2:
                continue
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "agricultural_weather_premium",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Ag weather premium: month={month}, 10d high breakout on {curr_vol/avg_vol:.1f}x volume",
                "timeframe": "1d",
                "max_hold_bars": 14,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 8: Commodity Momentum 12-1
# Reference: Gorton, Hayashi, Rouwenhorst (2013) RFS. Sharpe 0.82.
# =========================================================================
def commodity_momentum_12_1(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Buy top 3 commodities by 12-month return minus last month (skip-1-month momentum)."""
    signals = []
    rets = {}
    for symbol in COMMODITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 252:
                continue
            close = df["Close"]
            ret12 = (float(close.iloc[-22]) - float(close.iloc[-252])) / float(close.iloc[-252])
            ret1 = (float(close.iloc[-1]) - float(close.iloc[-22])) / float(close.iloc[-22])
            rets[symbol] = ret12 - ret1
        except Exception:
            continue
    if not rets:
        return signals
    top3 = sorted(rets, key=lambda s: rets[s], reverse=True)[:3]
    for symbol in top3:
        if rets[symbol] <= 0:
            continue
        try:
            df = data.get(symbol)
            if df is None:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "commodity_momentum_12_1",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.62, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"12-1 momentum={rets[symbol]:.1%}, top-3 commodity universe",
                "timeframe": "1d",
                "max_hold_bars": 21,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 9: Commodity Volatility Risk Premium
# Reference: Gorton & Rouwenhorst (2006).
# =========================================================================
def commodity_volatility_risk_premium(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY commodities where 20d realized vol < 30d average vol (expanding from low vol)."""
    signals = []
    for symbol in COMMODITY_SYMBOLS:
        try:
            df = data.get(symbol)
            if df is None or len(df) < 35:
                continue
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            rets = close.pct_change().dropna()
            vol20 = float(rets.iloc[-20:].std())
            vol30 = float(rets.iloc[-30:].std())
            if vol30 <= 0 or vol20 >= vol30:
                continue
            # Also require uptrend
            s20 = float(sma(close, 20).iloc[-1])
            curr = float(close.iloc[-1])
            if curr < s20:
                continue
            entry, tp, sl = _commodity_tp_sl(close, high, low, 2.0, 1.5)
            rr = _rr(entry, tp, sl)
            if rr < 1.2:
                continue
            signals.append({
                "strategy": "commodity_volatility_risk_premium",
                "symbol": symbol,
                "category": "commodity",
                "signal_type": "BUY",
                "entry_price": round(entry, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": min(0.60, 0.85),
                "risk_reward": round(rr, 2),
                "reason": f"Vol risk premium: 20d vol={vol20:.4f} < 30d vol={vol30:.4f}, uptrend",
                "timeframe": "1d",
                "max_hold_bars": 10,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =========================================================================
# COMMODITY STRATEGY 10: Platinum/Palladium Spread
# Reference: CRB historical ratio analysis.
# =========================================================================
def platinum_palladium_spread(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """BUY Platinum when RSI<40 and below 50d SMA (cheap vs historical)."""
    signals = []
    try:
        df = data.get("PL=F")
        if df is None or len(df) < 55:
            return signals
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])
        s50 = float(sma(close, 50).iloc[-1])
        curr = float(close.iloc[-1])
        if rsi_val >= 40 or curr >= s50:
            return signals
        entry, tp, sl = _commodity_tp_sl(close, high, low, 2.5, 1.5)
        rr = _rr(entry, tp, sl)
        if rr < 1.2:
            return signals
        signals.append({
            "strategy": "platinum_palladium_spread",
            "symbol": "PL=F",
            "category": "commodity",
            "signal_type": "BUY",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": min(0.61, 0.85),
            "risk_reward": round(rr, 2),
            "reason": f"Platinum cheap: RSI={rsi_val:.1f} < 40, below 50d SMA ({curr:.2f} vs {s50:.2f})",
            "timeframe": "1d",
            "max_hold_bars": 21,
            "timestamp": _now_iso(),
        })
    except Exception:
        pass
    return signals


# =========================================================================
# Registry
# =========================================================================
NEW_EQUITY_COMMODITY_STRATEGIES_20 = {
    "post_earnings_drift": post_earnings_drift,
    "week52_high_breakout": week52_high_breakout,
    "low_volatility_factor": low_volatility_factor,
    "short_interest_squeeze": short_interest_squeeze,
    "sector_rotation_etf": sector_rotation_etf,
    "bollinger_band_squeeze_stocks": bollinger_band_squeeze_stocks,
    "reversal_after_3_down_days": reversal_after_3_down_days,
    "dividend_capture_strategy": dividend_capture_strategy,
    "golden_cross_200d": golden_cross_200d,
    "mean_reversion_2day": mean_reversion_2day,
    "gold_real_yield_signal": gold_real_yield_signal,
    "commodity_channel_index_bounce": commodity_channel_index_bounce,
    "contango_roll_yield": contango_roll_yield,
    "precious_metals_correlation_pair": precious_metals_correlation_pair,
    "energy_eia_inventory_proxy": energy_eia_inventory_proxy,
    "copper_economic_cycle": copper_economic_cycle,
    "agricultural_weather_premium": agricultural_weather_premium,
    "commodity_momentum_12_1": commodity_momentum_12_1,
    "commodity_volatility_risk_premium": commodity_volatility_risk_premium,
    "platinum_palladium_spread": platinum_palladium_spread,
}

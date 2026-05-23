"""
Multi-Timeframe Confirmation -- checks higher TF alignment before committing TP/SL.
1H signals check 4H, 4H signals check 1D.
"""
import pandas as pd
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    from indicators import ema, rsi
except ImportError:
    from alpha_engine.indicators import ema, rsi

_HTF_MAP = {"5m": "1h", "15m": "1h", "1h": "4h", "4h": "1d", "1d": "1w"}


def confirm_direction(symbol: str, direction: str, base_tf: str,
                      htf_data: Optional[pd.DataFrame] = None) -> Dict:
    htf = _HTF_MAP.get(base_tf, "1d")
    is_long = direction in ("BUY", "LONG")

    if htf_data is None:
        htf_data = _fetch_htf_data(symbol, htf)

    if htf_data is None or len(htf_data) < 30:
        return {"confirmed": True, "htf": htf, "htf_trend": "UNKNOWN",
                "tp_adjustment": 1.0, "sl_adjustment": 1.0}

    ema_21 = ema(htf_data["Close"], 21)
    ema_50 = ema(htf_data["Close"], 50)
    rsi_val = rsi(htf_data["Close"]).iloc[-1]
    price = htf_data["Close"].iloc[-1]

    bullish = price > ema_21.iloc[-1] > ema_50.iloc[-1]
    bearish = price < ema_21.iloc[-1] < ema_50.iloc[-1]
    htf_trend = "BULLISH" if bullish else ("BEARISH" if bearish else "NEUTRAL")

    if (is_long and htf_trend == "BULLISH") or (not is_long and htf_trend == "BEARISH"):
        return {"confirmed": True, "htf": htf, "htf_trend": htf_trend,
                "tp_adjustment": 1.1, "sl_adjustment": 0.95}
    elif htf_trend == "NEUTRAL":
        return {"confirmed": True, "htf": htf, "htf_trend": htf_trend,
                "tp_adjustment": 1.0, "sl_adjustment": 1.0}
    else:
        return {"confirmed": False, "htf": htf, "htf_trend": htf_trend,
                "tp_adjustment": 0.8, "sl_adjustment": 1.1}


def adjust_tp_sl(entry: float, tp: float, sl: float, direction: str,
                 tp_adj: float, sl_adj: float) -> tuple:
    is_long = direction in ("BUY", "LONG")
    if is_long:
        new_tp = entry + (tp - entry) * tp_adj
        new_sl = entry - (entry - sl) * sl_adj
    else:
        new_tp = entry - (entry - tp) * tp_adj
        new_sl = entry + (sl - entry) * sl_adj
    return new_tp, new_sl


def _fetch_htf_data(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
        if timeframe == "4h":
            yf_interval = "1h"
            period = "60d"
        elif timeframe == "1w":
            yf_interval = "1wk"
            period = "2y"
        else:
            yf_interval = timeframe
            period = "60d" if timeframe == "1h" else "1y"

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=yf_interval)
        if df.empty:
            return None

        if timeframe == "4h" and yf_interval == "1h":
            df = df.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()

        return df
    except Exception as e:
        logger.warning(f"HTF data fetch failed for {symbol} {timeframe}: {e}")
        return None

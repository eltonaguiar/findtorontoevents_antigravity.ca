import pandas as pd
import numpy as np

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def run_strategy(strategy_def: dict, df: pd.DataFrame) -> list[dict]:
    """Execute a parameterized strategy variant on a dataframe.
    
    Returns a list of signal dicts (usually 0 or 1).
    """
    if df is None or len(df) < 200:
        return []
    
    template = strategy_def.get("template")
    params = strategy_def.get("params", {})
    strat_id = strategy_def.get("id")
    
    close = df['Close']
    price = float(close.iloc[-1])
    signals = []
    
    # 1. Forex RSI Reversion Template
    if template == "forex_rsi_reversion":
        rsi_period = params.get("rsi_period", 2)
        rsi_entry = params.get("rsi_entry", 5)
        sma_filter = params.get("sma_filter", 200)
        
        rsi_val = float(rsi(close, rsi_period).iloc[-1])
        sma_val = float(sma(close, sma_filter).iloc[-1])
        
        if rsi_val < rsi_entry and price > sma_val:
            signals.append({
                "strategy": strat_id,
                "direction": "LONG",
                "confidence": 0.70 + (rsi_entry - rsi_val) * 0.02
            })
        elif rsi_val > (100 - rsi_entry) and price < sma_val:
            signals.append({
                "strategy": strat_id,
                "direction": "SHORT",
                "confidence": 0.70 + (rsi_val - (100 - rsi_entry)) * 0.02
            })

    # 2. Crypto Momentum Trend Template
    elif template == "crypto_momentum_trend":
        atr_mult = params.get("atr_mult", 3.0)
        mom_period = params.get("mom_period", 14)
        
        atr_val = float(atr(df, 14).iloc[-1])
        mom = float(close.diff(mom_period).iloc[-1])
        
        if mom > (atr_val * atr_mult):
            signals.append({
                "strategy": strat_id,
                "direction": "LONG",
                "confidence": 0.65 + (mom / (atr_val * atr_mult) - 1) * 0.1
            })
        elif mom < -(atr_val * atr_mult):
            signals.append({
                "strategy": strat_id,
                "direction": "SHORT",
                "confidence": 0.65 + (abs(mom) / (atr_val * atr_mult) - 1) * 0.1
            })

    # 3. Stock High-Vol Breakout Template
    elif template == "stock_high_vol_breakout":
        rvol_threshold = params.get("rvol_threshold", 1.5)
        lookback = params.get("lookback", 20)
        
        vol = df['Volume']
        avg_vol = float(vol.iloc[-lookback-1:-1].mean())
        curr_vol = float(vol.iloc[-1])
        rvol = curr_vol / avg_vol if avg_vol > 0 else 0
        
        high_n = float(df['High'].iloc[-lookback-1:-1].max())
        low_n = float(df['Low'].iloc[-lookback-1:-1].min())
        
        if rvol > rvol_threshold and price > high_n:
            signals.append({
                "strategy": strat_id,
                "direction": "LONG",
                "confidence": 0.60 + (rvol / rvol_threshold - 1) * 0.05
            })
        elif rvol > rvol_threshold and price < low_n:
            signals.append({
                "strategy": strat_id,
                "direction": "SHORT",
                "confidence": 0.60 + (rvol / rvol_threshold - 1) * 0.05
            })

    # 4. Commodities Squeeze Template
    elif template == "commodities_squeeze":
        bb_period = params.get("bb_period", 20)
        std_mult = params.get("std_mult", 2.0)
        
        mid = sma(close, bb_period)
        std = close.rolling(bb_period).std()
        upper = mid + std_mult * std
        lower = mid - std_mult * std
        
        # Simple squeeze breakout logic
        if price > upper.iloc[-1]:
            signals.append({
                "strategy": strat_id,
                "direction": "LONG",
                "confidence": 0.72
            })
        elif price < lower.iloc[-1]:
            signals.append({
                "strategy": strat_id,
                "direction": "SHORT",
                "confidence": 0.72
            })

    # 5. Crypto Momentum Continuation Template
    elif template == "crypto_momentum_continuation":
        rsi_low = params.get("rsi_low", 35)
        rsi_high = params.get("rsi_high", 60)
        ema_fast = params.get("ema_fast", 9)
        ema_slow = params.get("ema_slow", 21)
        atr_max_pct = params.get("atr_max_pct", 3.0)
        vol_mult = params.get("vol_mult", 1.1)

        df["rsi"] = rsi(df["Close"], 14)
        df["ema_fast"] = df["Close"].ewm(span=ema_fast, adjust=False).mean()
        df["ema_slow"] = df["Close"].ewm(span=ema_slow, adjust=False).mean()
        df["atr"] = atr(df, 14)
        df["atr_pct"] = df["atr"] / df["Close"] * 100
        df["vol_avg"] = df["Volume"].rolling(12).mean()

        for i in range(max(ema_slow, 20), len(df)):
            r = df["rsi"].iloc[i]
            ef = df["ema_fast"].iloc[i]
            es = df["ema_slow"].iloc[i]
            a_pct = df["atr_pct"].iloc[i]
            vol = df["Volume"].iloc[i]
            vol_avg = df["vol_avg"].iloc[i]

            if (rsi_low <= r <= rsi_high
                    and ef > es
                    and a_pct < atr_max_pct
                    and vol > vol_avg * vol_mult):
                signals.append({
                    "strategy": strat_id,
                    "direction": "LONG",
                    "confidence": min(0.60 + (r - 35) / 100, 0.85),
                })
            elif (r > 70
                    and ef < es
                    and vol > vol_avg * vol_mult):
                signals.append({
                    "strategy": strat_id,
                    "direction": "SHORT",
                    "confidence": 0.65,
                })

    # 6. Crypto ATR Compression Breakout Template
    elif template == "crypto_atr_compression_breakout":
        atr_max_pct = params.get("atr_max_pct", 3.0)
        bb_period = params.get("bb_period", 20)
        bb_std = params.get("bb_std", 2.0)
        vol_spike_mult = params.get("vol_spike_mult", 1.5)
        slope_min = params.get("slope_min", 0.5)

        df["atr"] = atr(df, 14)
        df["atr_pct"] = df["atr"] / df["Close"] * 100
        df["ema9"] = df["Close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["Close"].ewm(span=21, adjust=False).mean()
        df["bb_mid"] = df["Close"].rolling(bb_period).mean()
        df["bb_std"] = df["Close"].rolling(bb_period).std()
        df["bb_upper"] = df["bb_mid"] + bb_std * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - bb_std * df["bb_std"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"] * 100
        df["vol_avg"] = df["Volume"].rolling(20).mean()
        df["slope"] = df["Close"].pct_change(10) * 100

        for i in range(30, len(df)):
            a_pct = df["atr_pct"].iloc[i]
            bw = df["bb_width"].iloc[i]
            ef = df["ema9"].iloc[i]
            es = df["ema21"].iloc[i]
            sl = df["slope"].iloc[i]
            vol = df["Volume"].iloc[i]
            va = df["vol_avg"].iloc[i]
            r = rsi(df["Close"].iloc[:i+1], 14).iloc[-1] if i > 14 else 50

            vol_spike = vol > va * vol_spike_mult if va > 0 else False

            if (a_pct < atr_max_pct
                    and bw < 4.0
                    and ef > es
                    and sl > slope_min
                    and (vol_spike or r > 50)):
                signals.append({
                    "strategy": strat_id,
                    "direction": "LONG",
                    "confidence": min(0.62 + (0.08 if vol_spike else 0) + (0.05 if a_pct < 2 else 0), 0.85),
                })
            elif (a_pct < atr_max_pct
                    and bw < 4.0
                    and ef < es
                    and sl < -slope_min
                    and (vol_spike or r < 45)):
                signals.append({
                    "strategy": strat_id,
                    "direction": "SHORT",
                    "confidence": min(0.62 + (0.08 if vol_spike else 0), 0.85),
                })

    return signals

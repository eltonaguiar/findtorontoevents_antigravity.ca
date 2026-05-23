
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from integration import save_live_pick
# CONFIG
PAIRS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "LINK-USD"]
TIMEFRAMES = ["4h", "1d"]
LOOKBACK = 720
COMMISSION = 0.1 / 100
POSITION_SIZE = 0.20


def compute_indicators(df):
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]

    # Bollinger Bands
    df["bb_mid"] = c.rolling(20).mean()
    df["bb_std"] = c.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

    # Keltner Channels
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(20).mean()
    df["kc_upper"] = df["bb_mid"] + 1.5 * df["atr"]
    df["kc_lower"] = df["bb_mid"] - 1.5 * df["atr"]

    # Squeeze: BB inside KC
    df["squeeze"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])

    # Direction: RSI + Momentum
    df["rsi"] = rsi(c, 14)
    df["mom"] = c.diff(10)
    
    # ADX (14)
    up = h.diff()
    down = -l.diff()
    pos_dm = np.where((up > down) & (up > 0), up, 0)
    neg_dm = np.where((down > up) & (down > 0), down, 0)
    tr_ema = tr.ewm(alpha=1/14, adjust=False).mean()
    df["plus_di"] = 100 * (pd.Series(pos_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr_ema)
    df["minus_di"] = 100 * (pd.Series(neg_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr_ema)
    dx = (abs(df["plus_di"] - df["minus_di"]) / (df["plus_di"] + df["minus_di"])) * 100
    df["adx"] = dx.rolling(14).mean()

    # Signal: Squeeze Fired + Directional Momentum + ADX > 25
    df["sig"] = 0
    sqz_fired = (~df["squeeze"]) & df["squeeze"].shift(1)
    df.loc[sqz_fired & (df["mom"] > 0) & (df["rsi"] > 50) & (df["adx"] > 25), "sig"] = 1
    df.loc[sqz_fired & (df["mom"] < 0) & (df["rsi"] < 50) & (df["adx"] > 25), "sig"] = -1

    return df

def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def backtest(df):
    equity = 10000
    pos = 0
    entry_p = 0
    ts_p = 0
    trades = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]
        p = row["Close"]
        sig = row["sig"]
        atr = row["atr"]

        if pos != 0:
            pnl_pct = (p / entry_p - 1) * pos * 100
            # Trailing stop
            if pos == 1:
                ts_p = max(ts_p, p)
                stop_price = ts_p - 3.0 * atr
                if p <= stop_price:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "TS"})
                    pos = 0
            elif pos == -1:
                ts_p = min(ts_p, p)
                stop_price = ts_p + 3.0 * atr
                if p >= stop_price:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "TS"})
                    pos = 0
            
            # 5% hard SL
            if pos != 0 and pnl_pct <= -5:
                pnl = equity * POSITION_SIZE * (-0.05) - (equity * POSITION_SIZE * COMMISSION * 2)
                equity += pnl
                trades.append({"pnl_pct": -5, "reason": "SL"})
                pos = 0

        if pos == 0 and sig != 0 and not np.isnan(atr):
            pos = int(sig)
            entry_p = p
            ts_p = p
            equity -= (equity * POSITION_SIZE * COMMISSION)

        equity_curve.append(equity)

    return trades, equity_curve

def run():
    print("CRYPTO SQUEEZE RESEARCH")
    all_res = []
    for pair in PAIRS:
        for tf in TIMEFRAMES:
            df = yf.download(pair, start=(datetime.now() - timedelta(days=LOOKBACK)).strftime("%Y-%m-%d"), interval=tf, progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = compute_indicators(df)
            trades, curve = backtest(df)
            wr = len([t for t in trades if t["pnl_pct"] > 0]) / len(trades) * 100 if trades else 0
            ret = (curve[-1] / 10000 - 1) * 100 if curve else 0
            print(f"{pair} {tf}: WR={wr:.1f}%, Return={ret:.1f}%, Trades={len(trades)}")
            all_res.append({"pair": pair, "tf": tf, "wr": wr, "ret": ret, "trades": len(trades)})

            # Check for live signal (last row)
            last_row = df.iloc[-1]
            if last_row["sig"] != 0:
                print(f"  [SIGNAL] LIVE {pair} {tf}: {last_row['sig']}")
                # Confidence: simple WR proxy or static 0.75
                conf = 0.75 + (wr/1000)
                # Simple TP/SL
                atr = last_row["atr"]
                p = last_row["Close"]
                if last_row["sig"] == 1:
                    tp = p + 3.0 * atr
                    sl = p - 2.0 * atr
                else:
                    tp = p - 3.0 * atr
                    sl = p + 2.0 * atr
                    
                save_live_pick(
                    strategy_name=f"crypto_squeeze_{tf}",
                    symbol=pair,
                    signal=last_row["sig"],
                    entry_price=p,
                    tp=tp,
                    sl=sl,
                    confidence=conf,
                    category="crypto"
                )
    return all_res

if __name__ == "__main__":
    run()

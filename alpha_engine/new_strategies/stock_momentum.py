
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from integration import save_live_pick
# CONFIG
SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", "GOOGL"]
TIMEFRAMES = ["1d"]
LOOKBACK = 365
COMMISSION = 0.05 / 100
POSITION_SIZE = 0.20


def compute_indicators(df):
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]

    # RVOL (Relative Volume) - 20 day avg
    df["vol_sma"] = v.rolling(20).mean()
    df["rvol"] = v / df["vol_sma"].replace(0, np.nan)
    
    # EMAs
    df["ema9"] = c.ewm(span=9, adjust=False).mean()
    df["ema20"] = c.ewm(span=20, adjust=False).mean()
    df["sma50"] = c.rolling(50).mean()

    # Pre-calculated ATR
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    # Simple ADX (14-period)
    up = h.diff()
    down = -l.diff()
    pos_dm = np.where((up > down) & (up > 0), up, 0)
    neg_dm = np.where((down > up) & (down > 0), down, 0)
    
    tr_ema = tr.ewm(alpha=1/14, adjust=False).mean()
    df["plus_di"] = 100 * (pd.Series(pos_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr_ema)
    df["minus_di"] = 100 * (pd.Series(neg_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr_ema)
    dx = (abs(df["plus_di"] - df["minus_di"]) / (df["plus_di"] + df["minus_di"])) * 100
    df["adx"] = dx.rolling(14).mean()

    # Signal: RVOL > 1.5 AND Price > EMA 9 AND Price > EMA 20 AND Price > SMA 50 AND ADX > 20
    df["sig"] = 0
    df.loc[(df["rvol"] > 1.5) & (c > df["ema9"]) & (c > df["ema20"]) & (c > df["sma50"]) & (df["adx"] > 20), "sig"] = 1
    # Short: RVOL > 1.5 AND Price < EMA 20 AND Price < SMA 50 AND ADX > 20
    df.loc[(df["rvol"] > 1.5) & (c < df["ema9"]) & (c < df["ema20"]) & (c < df["sma50"]) & (df["adx"] > 20), "sig"] = -1

    return df

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
            # Trailing stop update
            if pos == 1:
                ts_p = max(ts_p, p)
                stop_price = ts_p - 2.0 * atr
                if p <= stop_price:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "TS"})
                    pos = 0
            elif pos == -1:
                ts_p = min(ts_p, p)
                stop_price = ts_p + 2.0 * atr
                if p >= stop_price:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "TS"})
                    pos = 0

            # Initial SL / TP for safety
            if pos != 0 and pnl_pct <= -3:
                pnl = equity * POSITION_SIZE * (-0.03) - (equity * POSITION_SIZE * COMMISSION * 2)
                equity += pnl
                trades.append({"pnl_pct": -3, "reason": "SL"})
                pos = 0

        if pos == 0 and sig != 0 and not np.isnan(atr):
            pos = int(sig)
            entry_p = p
            ts_p = p
            equity -= (equity * POSITION_SIZE * COMMISSION)

        equity_curve.append(equity)

    return trades, equity_curve

def run():
    print("STOCK MOMENTUM RESEARCH")
    all_res = []
    for sym in SYMBOLS:
        for tf in TIMEFRAMES:
            df = yf.download(sym, start=(datetime.now() - timedelta(days=LOOKBACK)).strftime("%Y-%m-%d"), interval=tf, progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = compute_indicators(df)
            trades, curve = backtest(df)
            wr = len([t for t in trades if t["pnl_pct"] > 0]) / len(trades) * 100 if trades else 0
            ret = (curve[-1] / 10000 - 1) * 100 if curve else 0
            print(f"{sym} {tf}: WR={wr:.1f}%, Return={ret:.1f}%, Trades={len(trades)}")
            all_res.append({"symbol": sym, "tf": tf, "wr": wr, "ret": ret, "trades": len(trades)})

            # Check for live signal (last row)
            last_row = df.iloc[-1]
            if last_row["sig"] != 0:
                print(f"  [SIGNAL] LIVE {sym} {tf}: {last_row['sig']}")
                # Confidence: simple WR proxy or static 0.75
                conf = 0.7 + (wr/1000)
                # Simple TP/SL
                atr = last_row["atr"]
                p = last_row["Close"]
                if last_row["sig"] == 1:
                    tp = p + 2.0 * atr
                    sl = p - 1.5 * atr
                else:
                    tp = p - 2.0 * atr
                    sl = p + 1.5 * atr
                    
                save_live_pick(
                    strategy_name=f"stock_momentum_{tf}",
                    symbol=sym,
                    signal=last_row["sig"],
                    entry_price=p,
                    tp=tp,
                    sl=sl,
                    confidence=conf,
                    category="equity"
                )
    return all_res

if __name__ == "__main__":
    run()

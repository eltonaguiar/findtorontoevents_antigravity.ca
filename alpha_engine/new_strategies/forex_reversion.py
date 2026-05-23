
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from integration import save_live_pick
# CONFIG
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
TIMEFRAMES = ["1h"]
LOOKBACK = 365
COMMISSION = 0.05 / 100
POSITION_SIZE = 0.20


def compute_indicators(df):
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    
    # RSI 2-period for extreme mean reversion
    df["rsi2"] = rsi(c, 2)
    # EMA 200 for trend filter
    df["ema200"] = c.ewm(span=200, adjust=False).mean()
    
    # ATR for trailing stop
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    # Lower Highs / Higher Lows filter
    df["sig"] = 0
    # Long: Price > EMA 200 AND RSI2 < 5
    df.loc[(c > df["ema200"]) & (df["rsi2"] < 5), "sig"] = 1
    # Short: Price < EMA 200 AND RSI2 > 95
    df.loc[(c < df["ema200"]) & (df["rsi2"] > 95), "sig"] = -1

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
            # Update Trailing Stop price
            if pos == 1:
                ts_p = max(ts_p, p)
                stop_price = ts_p - 2.5 * atr
                if p <= stop_price or row["rsi2"] > 70:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "EXIT"})
                    pos = 0
            elif pos == -1:
                ts_p = min(ts_p, p)
                stop_price = ts_p + 2.5 * atr
                if p >= stop_price or row["rsi2"] < 30:
                    pnl = equity * POSITION_SIZE * (pnl_pct/100) - (equity * POSITION_SIZE * COMMISSION * 2)
                    equity += pnl
                    trades.append({"pnl_pct": pnl_pct, "reason": "EXIT"})
                    pos = 0

        if pos == 0 and sig != 0 and not np.isnan(atr):
            pos = int(sig)
            entry_p = p
            ts_p = p
            equity -= (equity * POSITION_SIZE * COMMISSION)

        equity_curve.append(equity)

    return trades, equity_curve

def run():
    print("FOREX REVERSION RESEARCH")
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
                conf = 0.7 + (wr/1000)
                # Simple TP/SL
                atr = last_row["atr"]
                p = last_row["Close"]
                if last_row["sig"] == 1:
                    tp = p + 2.5 * atr
                    sl = p - 1.5 * atr
                else:
                    tp = p - 2.5 * atr
                    sl = p + 1.5 * atr
                    
                save_live_pick(
                    strategy_name=f"forex_reversion_{tf}",
                    symbol=pair,
                    signal=last_row["sig"],
                    entry_price=p,
                    tp=tp,
                    sl=sl,
                    confidence=conf,
                    category="forex"
                )
    return all_res

if __name__ == "__main__":
    run()

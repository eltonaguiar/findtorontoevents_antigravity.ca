"""
Commodities Mean Reversion & Momentum Strategy
- Gold (GC=F), Silver (SI=F), WTI Oil (CL=F), Natural Gas (NG=F), Copper (HG=F)
- Strategy: Bollinger Band mean reversion in ranging + ATR breakout for trends
- Uses RSI confirmation to avoid false reversals
- Protocol-gated: requires MC prob_profitable > 0.65 AND PF > 1.2
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from protocol_validation import bootstrap_ci, monte_carlo_prob_profitable, walk_forward_validation, protocol_gate

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

SYMBOLS = ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"]
STRATEGY_NAME = "commodities_bb_mean_reversion"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "commodities_mr_report.json")
MIN_TRADES = 5  # commodities are lower-frequency on daily


def fetch(symbol: str, period: str = "5y") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    return df.dropna()


def run_backtest(df: pd.DataFrame) -> list:
    """Bollinger Band mean reversion + RSI confirmation."""
    df = df.copy()
    df["sma20"] = df["close"].rolling(20).mean()
    df["std20"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["sma20"] + 2.0 * df["std20"]
    df["bb_lower"] = df["sma20"] - 2.0 * df["std20"]
    df["rsi"] = _rsi(df["close"], 14)
    df["atr"] = _atr(df, 14)
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_date = None
    sl = 0.0
    tp = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        if in_trade:
            pnl_pct = (row["close"] - entry_price) / entry_price * 100
            # Stop loss or take profit
            if row["low"] <= sl or row["high"] >= tp or i - entry_idx >= 20:
                win = row["close"] >= entry_price
                pnl = (row["close"] - entry_price) / entry_price * 100
                trades.append({"pnl": pnl, "win": win, "date": str(df.index[i])[:10]})
                in_trade = False
        else:
            # Entry: price below lower BB + RSI oversold (< 35)
            if row["close"] < row["bb_lower"] and row["rsi"] < 35:
                in_trade = True
                entry_price = row["close"]
                entry_date = str(df.index[i])[:10]
                entry_idx = i
                sl = entry_price - 1.5 * row["atr"]
                tp = row["sma20"]  # target is mean
    return trades


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def main():
    results = []
    for symbol in SYMBOLS:
        print(f"  Backtesting {symbol} ...", flush=True)
        try:
            df = fetch(symbol)
            if len(df) < 100:
                print(f"    Skipping {symbol}: insufficient data")
                continue
            trades = run_backtest(df)
            if not trades:
                print(f"    No trades for {symbol}")
                continue

            pnls = [t["pnl"] for t in trades]
            wins = [t["win"] for t in trades]
            wr = sum(wins) / len(wins) * 100
            avg_win = np.mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 0
            avg_loss = abs(np.mean([p for p in pnls if p < 0])) if any(p < 0 for p in pnls) else 0.001
            pf = (sum(p for p in pnls if p > 0)) / (abs(sum(p for p in pnls if p < 0)) or 0.001)

            # Statistical validation
            ci = bootstrap_ci(pnls)
            mc = monte_carlo_prob_profitable(pnls, n_sims=2000, horizon=30)
            proto = protocol_gate(trade_count=len(trades), win_rate=wr/100, profit_factor=pf, ci=ci, mc_prob=mc["prob_profitable"], min_trades=MIN_TRADES, min_ci_check=False)

            r = {
                "symbol": symbol,
                "trades": len(trades),
                "win_rate": round(wr, 2),
                "avg_pnl": round(float(np.mean(pnls)), 4),
                "profit_factor": round(pf, 3),
                "bootstrap": ci,
                "monte_carlo": mc,
                "protocol": proto,
            }
            results.append(r)
            print(f"    {symbol}: {len(trades)} trades, WR={wr:.1f}%, PF={pf:.2f}, MC={mc['prob_profitable']:.2f}, gate={proto['gate']}")
        except Exception as e:
            print(f"    ERROR {symbol}: {e}")

    out = {"generated_at": datetime.utcnow().isoformat() + "Z", "strategy": STRATEGY_NAME, "results": results}
    with open(REPORT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {REPORT_FILE}")
    passed = [r for r in results if r.get("protocol", {}).get("gate") == "PASS"]
    print(f"Passed protocol gate: {len(passed)}/{len(results)} symbols")
    return out


if __name__ == "__main__":
    main()

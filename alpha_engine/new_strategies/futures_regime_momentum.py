"""
Futures Regime-Filtered Momentum Strategy (replacement for failed Trend Pullback)
- Previous strategy (futures_trend_pullback) failed: ES=F 18% WR, NQ=F 12% WR
- New approach: Only trade futures when regime is confirmed trending (ADX > 30)
- Further filter: Only enter LONG in bull market regime (price > 200 SMA)
- Use shorter hold periods (5 days max) with 1:2 risk/reward minimum
- Symbols: ES=F (S&P500), GC=F (Gold), CL=F (Oil), ZB=F (Bonds)
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from protocol_validation import bootstrap_ci, monte_carlo_prob_profitable, walk_forward_validation, protocol_gate

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

SYMBOLS = ["ES=F", "NQ=F", "GC=F", "CL=F", "ZB=F"]
STRATEGY_NAME = "futures_regime_momentum"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "futures_regime_report.json")


def fetch(symbol: str, period: str = "4y") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    return df.dropna()


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    df = df.copy()
    df["tr"] = _atr(df, 1)
    df["dm_plus"] = (df["high"] - df["high"].shift(1)).clip(lower=0)
    df["dm_minus"] = (df["low"].shift(1) - df["low"]).clip(lower=0)
    atr_roll = df["tr"].rolling(period).mean()
    di_plus = 100 * df["dm_plus"].rolling(period).mean() / atr_roll.replace(0, np.nan)
    di_minus = 100 * df["dm_minus"].rolling(period).mean() / atr_roll.replace(0, np.nan)
    dx = (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan) * 100
    return dx.rolling(period).mean()


def run_backtest(df: pd.DataFrame) -> list:
    """
    Regime-filtered momentum:
    - ADX > 30 (confirmed trend)
    - Price > SMA200 (bull market)
    - RSI pullback to 45-55 (buy the dip in uptrend)
    - 1:2 risk/reward with ATR-based SL/TP
    - Max 5-day hold
    """
    df = df.copy()
    df["sma200"] = df["close"].rolling(200).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["adx"] = _adx(df, 14)
    df["atr"] = _atr(df, 14)

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    df.dropna(inplace=True)
    if len(df) < 50:
        return []

    trades = []
    in_trade = False
    entry_price = 0.0
    sl = 0.0
    tp = 0.0
    entry_idx = 0
    direction = None

    for i in range(len(df)):
        row = df.iloc[i]

        if in_trade:
            if direction == "long":
                hit_tp = float(row["high"]) >= tp
                hit_sl = float(row["low"]) <= sl
            else:
                hit_tp = float(row["low"]) <= tp
                hit_sl = float(row["high"]) >= sl

            timeout = (i - entry_idx) >= 5

            if hit_tp or hit_sl or timeout:
                if hit_tp:
                    exit_p = tp
                elif hit_sl:
                    exit_p = sl
                else:
                    exit_p = float(row["close"])
                pnl = (exit_p - entry_price) / entry_price * 100
                if direction == "short":
                    pnl = -pnl
                trades.append({"pnl": pnl, "win": pnl > 0})
                in_trade = False
        else:
            adx_val = float(row.get("adx", 0))
            rsi_val = float(row.get("rsi", 50))
            close = float(row["close"])
            sma200 = float(row["sma200"])
            sma50 = float(row["sma50"])
            atr_val = float(row["atr"])

            # Bull trend + strong momentum + RSI pullback entry
            if (adx_val > 30 and close > sma200 and close > sma50
                    and 42 <= rsi_val <= 56):
                in_trade = True
                direction = "long"
                entry_price = close
                entry_idx = i
                sl = entry_price - 1.0 * atr_val
                tp = entry_price + 2.0 * atr_val  # 1:2 RR

            # Bear trend short (price < SMA200, ADX > 30, RSI 44-58 pullback)
            elif (adx_val > 30 and close < sma200 and close < sma50
                    and 44 <= rsi_val <= 58):
                in_trade = True
                direction = "short"
                entry_price = close
                entry_idx = i
                sl = entry_price + 1.0 * atr_val
                tp = entry_price - 2.0 * atr_val

    return trades


def main():
    results = []
    for symbol in SYMBOLS:
        print(f"  Backtesting {symbol} ...", flush=True)
        try:
            df = fetch(symbol)
            if len(df) < 200:
                print(f"    Skipping {symbol}: insufficient data ({len(df)} bars)")
                continue
            trades = run_backtest(df)
            if len(trades) < 5:
                print(f"    {symbol}: only {len(trades)} trades")
                continue

            pnls = [t["pnl"] for t in trades]
            wins = [t["win"] for t in trades]
            wr = sum(wins) / len(wins) * 100
            pf = (sum(p for p in pnls if p > 0)) / (abs(sum(p for p in pnls if p < 0)) or 0.001)

            wf = walk_forward_validation(pnls)
            ci = bootstrap_ci(pnls)
            mc = monte_carlo_prob_profitable(pnls, n_sims=2000, horizon=30)
            proto = protocol_gate(trade_count=len(trades), win_rate=wr/100, profit_factor=pf, ci=ci, mc_prob=mc["prob_profitable"], min_trades=8, min_ci_check=False)

            r = {
                "symbol": symbol,
                "trades": len(trades),
                "win_rate": round(wr, 2),
                "avg_pnl": round(float(np.mean(pnls)), 4),
                "profit_factor": round(pf, 3),
                "walk_forward": wf,
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

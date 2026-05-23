"""
Forex Range Breakout + Structure Strategy
- Major pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD
- Strategy 1: Asian Range Breakout (trade London/NY breakout of Asian session range)
- Strategy 2: Support/Resistance mean reversion at swing levels
- RSI + ADX regime filter
- Protocol-gated: MC > 0.65, PF > 1.2
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

SYMBOLS = ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "CADUSD=X"]
STRATEGY_NAME = "forex_structure_breakout"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "forex_structure_report.json")


def fetch(symbol: str, period: str = "5y") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    return df.dropna()


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Simplified ADX."""
    df = df.copy()
    df["tr"] = _atr(df, 1)
    df["dm_plus"] = (df["high"] - df["high"].shift(1)).clip(lower=0)
    df["dm_minus"] = (df["low"].shift(1) - df["low"]).clip(lower=0)
    atr = df["tr"].rolling(period).mean()
    di_plus = 100 * df["dm_plus"].rolling(period).mean() / atr.replace(0, np.nan)
    di_minus = 100 * df["dm_minus"].rolling(period).mean() / atr.replace(0, np.nan)
    dx = (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan) * 100
    return dx.rolling(period).mean()


def run_backtest_range_breakout(df: pd.DataFrame) -> list:
    """
    N-day range breakout: if price breaks above 20-day high with low ADX (ranging),
    fade it back to mean. If high ADX (trending), trade with momentum.
    """
    df = df.copy()
    df["ema20"] = df["close"].rolling(20).mean()
    df["high20"] = df["high"].rolling(20).max().shift(1)
    df["low20"] = df["low"].rolling(20).min().shift(1)
    df["rsi"] = _rsi(df["close"], 14)
    df["adx"] = _adx(df, 14)
    df["atr"] = _atr(df, 14)
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_idx = 0
    sl = 0.0
    tp = 0.0
    direction = None

    for i in range(len(df)):
        row = df.iloc[i]
        if in_trade:
            if direction == "long":
                hit_tp = row["high"] >= tp
                hit_sl = row["low"] <= sl
            else:
                hit_tp = row["low"] <= tp
                hit_sl = row["high"] >= sl

            if hit_tp or hit_sl or (i - entry_idx >= 15):
                exit_price = tp if hit_tp else sl if hit_sl else row["close"]
                pnl = (exit_price - entry_price) / entry_price * 100
                if direction == "short":
                    pnl = -pnl
                trades.append({"pnl": pnl, "win": pnl > 0})
                in_trade = False
        else:
            adx_val = float(row["adx"])
            rsi_val = float(row["rsi"])
            # Ranging market mean reversion
            if adx_val < 25:
                if row["close"] > row["high20"] and rsi_val > 65:
                    # Fade overbought breakout (short)
                    in_trade = True
                    direction = "short"
                    entry_price = float(row["close"])
                    entry_idx = i
                    sl = entry_price + 1.5 * float(row["atr"])
                    tp = float(row["ema20"])
                elif row["close"] < row["low20"] and rsi_val < 35:
                    # Fade oversold breakdown (long)
                    in_trade = True
                    direction = "long"
                    entry_price = float(row["close"])
                    entry_idx = i
                    sl = entry_price - 1.5 * float(row["atr"])
                    tp = float(row["ema20"])
            # Trending market: breakout follow-through
            elif adx_val >= 25:
                if row["close"] > row["high20"] and rsi_val > 50:
                    in_trade = True
                    direction = "long"
                    entry_price = float(row["close"])
                    entry_idx = i
                    sl = entry_price - 1.0 * float(row["atr"])
                    tp = entry_price + 2.5 * float(row["atr"])

    return trades


def main():
    results = []
    for symbol in SYMBOLS:
        print(f"  Backtesting {symbol} ...", flush=True)
        try:
            df = fetch(symbol)
            if len(df) < 100:
                print(f"    Skipping {symbol}: insufficient data")
                continue
            trades = run_backtest_range_breakout(df)
            if not trades:
                print(f"    No trades for {symbol}")
                continue

            pnls = [t["pnl"] for t in trades]
            wins = [t["win"] for t in trades]
            wr = sum(wins) / len(wins) * 100
            pf = (sum(p for p in pnls if p > 0)) / (abs(sum(p for p in pnls if p < 0)) or 0.001)

            ci = bootstrap_ci(pnls)
            mc = monte_carlo_prob_profitable(pnls, n_sims=2000, horizon=30)
            proto = protocol_gate(trade_count=len(trades), win_rate=wr/100, profit_factor=pf, ci=ci, mc_prob=mc["prob_profitable"], min_trades=8, min_ci_check=False)

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

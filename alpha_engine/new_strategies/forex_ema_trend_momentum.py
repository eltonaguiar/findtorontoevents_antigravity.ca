"""
Forex Carry + Trend Momentum Strategy
- Theory: trade in direction of high-yield currency + daily trend alignment
- Implementation: EMA crossover (EMA5 crosses EMA20 in direction of weekly trend EMA50)
- ADX > 20 confirms trend is present before entry
- Risk: 1.0x ATR stop, 2.0x ATR target (1:2 RR ensures profitability at 40% WR)
- Pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCHF
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

SYMBOLS = ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "NZDUSD=X", "USDCHF=X"]
STRATEGY_NAME = "forex_ema_trend_momentum"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "forex_ema_trend_report.json")


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


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    df = df.copy()
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["dm_plus"] = (df["high"] - df["high"].shift(1)).clip(lower=0)
    df["dm_minus"] = (df["low"].shift(1) - df["low"]).clip(lower=0)
    atr_roll = tr.rolling(period).mean()
    di_plus = 100 * df["dm_plus"].rolling(period).mean() / atr_roll.replace(0, np.nan)
    di_minus = 100 * df["dm_minus"].rolling(period).mean() / atr_roll.replace(0, np.nan)
    dx = (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan) * 100
    return dx.rolling(period).mean(), di_plus, di_minus


def run_backtest(df: pd.DataFrame) -> list:
    """
    EMA5/EMA20 crossover in direction of EMA50 trend, ADX > 20.
    1:2 RR with ATR-based stops.
    """
    df = df.copy()
    df["ema5"] = df["close"].ewm(span=5).mean()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema5_prev"] = df["ema5"].shift(1)
    df["ema20_prev"] = df["ema20"].shift(1)
    df["atr"] = _atr(df, 14)
    adx, di_plus, di_minus = _adx(df, 14)
    df["adx"] = adx
    df["di_plus"] = di_plus
    df["di_minus"] = di_minus
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    sl = 0.0
    tp = 0.0
    direction = None
    entry_idx = 0

    for i in range(len(df)):
        row = df.iloc[i]
        close = float(row["close"])
        ema5 = float(row["ema5"])
        ema20 = float(row["ema20"])
        ema50 = float(row["ema50"])
        ema5_prev = float(row["ema5_prev"])
        ema20_prev = float(row["ema20_prev"])
        adx_val = float(row["adx"])
        atr_val = float(row["atr"])

        if in_trade:
            if direction == "long":
                hit_tp = float(row["high"]) >= tp
                hit_sl = float(row["low"]) <= sl
            else:
                hit_tp = float(row["low"]) <= tp
                hit_sl = float(row["high"]) >= sl
            timeout = (i - entry_idx) >= 20

            if hit_tp or hit_sl or timeout:
                exit_p = tp if hit_tp else (sl if hit_sl else close)
                pnl = (exit_p - entry_price) / entry_price * 100
                if direction == "short":
                    pnl = -pnl
                trades.append({"pnl": pnl, "win": pnl > 0})
                in_trade = False
        else:
            if adx_val < 20:
                continue

            # Bullish crossover in bull trend
            bullish_cross = (ema5_prev <= ema20_prev) and (ema5 > ema20)
            if bullish_cross and close > ema50:
                in_trade = True
                direction = "long"
                entry_price = close
                entry_idx = i
                sl = entry_price - 1.0 * atr_val
                tp = entry_price + 2.0 * atr_val

            # Bearish crossover in bear trend
            bearish_cross = (ema5_prev >= ema20_prev) and (ema5 < ema20)
            if bearish_cross and close < ema50:
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
            if len(df) < 150:
                print(f"    Skipping {symbol}: insufficient data")
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

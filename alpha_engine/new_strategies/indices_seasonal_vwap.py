"""
Indices Seasonal + VWAP Deviation Strategy
- US Indices: SPY, QQQ, IWM, DIA, MDY (S&P, Nasdaq, Russell, Dow, Mid-Cap)
- Strategy: Monthly/seasonal bias combined with intraday VWAP deviation (daily proxy)
- Signal: Price extended >1.5% from 5-day VWAP proxy + seasonal month bias
- Monthly seasonality: historically bullish months (Nov, Dec, Jan, Apr) get long bias
- Anti-seasonal months (May, Sep) get short bias
- Exit: Mean reversion to 5-day SMA or 7-day timeout
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

SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "MDY"]
STRATEGY_NAME = "indices_seasonal_vwap_dev"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "indices_seasonal_report.json")

# Historical monthly seasonal bias (+1 = bullish, -1 = bearish, 0 = neutral)
MONTH_BIAS = {
    1: 1,   # Jan (January effect)
    2: 0,
    3: 0,
    4: 1,   # April tax season rally
    5: -1,  # Sell in May
    6: 0,
    7: 1,   # Summer rally
    8: -1,  # Late summer weakness
    9: -1,  # Worst month historically
    10: 0,  # Recovery
    11: 1,  # Santa rally starts
    12: 1,  # Santa rally
}


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


def run_backtest(df: pd.DataFrame) -> list:
    """
    VWAP proxy: 5-day SMA of typical price (HLC/3).
    Entry: price deviated > 1.5% from 5-day SMA AND seasonal bias aligns.
    Exit: mean reversion back to 5-day SMA OR stop at 2ATR.
    """
    df = df.copy()
    df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap_proxy"] = df["typical"].rolling(5).mean()
    df["sma5"] = df["close"].rolling(5).mean()
    df["sma20"] = df["close"].rolling(20).mean()
    df["atr"] = _atr(df, 14)
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    direction = None
    entry_idx = 0
    sl = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        idx = df.index[i]
        month = idx.month if hasattr(idx, "month") else pd.Timestamp(idx).month
        seasonal_bias = MONTH_BIAS.get(month, 0)

        dev = (float(row["close"]) - float(row["vwap_proxy"])) / float(row["vwap_proxy"]) * 100

        if in_trade:
            current = float(row["close"])
            # Mean reversion exit
            reverted = (direction == "long" and current >= float(row["sma5"])) or \
                       (direction == "short" and current <= float(row["sma5"]))
            hit_sl = (direction == "long" and float(row["low"]) <= sl) or \
                     (direction == "short" and float(row["high"]) >= sl)
            timeout = (i - entry_idx) >= 7

            if reverted or hit_sl or timeout:
                exit_p = float(row["close"])
                pnl = (exit_p - entry_price) / entry_price * 100
                if direction == "short":
                    pnl = -pnl
                trades.append({"pnl": pnl, "win": pnl > 0, "month": month})
                in_trade = False
        else:
            # Long: price stretched below vwap + seasonal bullish
            if dev < -1.5 and seasonal_bias >= 0 and float(row["close"]) > float(row["sma20"]):
                in_trade = True
                direction = "long"
                entry_price = float(row["close"])
                entry_idx = i
                sl = entry_price - 2.0 * float(row["atr"])
            # Short: price stretched above vwap + seasonal bearish or neutral + downtrend
            elif dev > 1.5 and seasonal_bias <= 0 and float(row["close"]) < float(row["sma20"]):
                in_trade = True
                direction = "short"
                entry_price = float(row["close"])
                entry_idx = i
                sl = entry_price + 2.0 * float(row["atr"])

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

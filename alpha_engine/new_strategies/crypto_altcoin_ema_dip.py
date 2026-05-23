"""
Crypto Altcoin Momentum + Dip Strategy (Replacement)
- Targets low-coverage altcoins with broader entry criteria
- Strategy: EMA21/55 trend filter + RSI dip (30-50) in uptrend = buy the pullback
- Uses 2-year lookback, 12% TP, 1.5x ATR trailing stop
- More signals than volume-surge approach
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

SYMBOLS = ["ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "NEAR-USD", "FIL-USD", "ATOM-USD", "ONE-USD", "ALGO-USD", "VET-USD"]
STRATEGY_NAME = "crypto_altcoin_ema_dip"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "crypto_altcoin_dip_report.json")


def fetch(symbol: str, period: str = "3y") -> pd.DataFrame:
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


def run_backtest(df: pd.DataFrame) -> list:
    """
    Buy pullback in uptrend:
    - EMA21 > EMA55 (uptrend)
    - RSI dips to 30-50 (pullback)
    - Close > EMA55 (not broken support)
    Exit: 12% TP or 1.5x ATR trailing stop or 20 days
    """
    df = df.copy()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema55"] = df["close"].ewm(span=55).mean()
    df["rsi"] = _rsi(df["close"], 14)
    df["atr"] = _atr(df, 14)
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    trail_stop = 0.0
    entry_idx = 0

    for i in range(len(df)):
        row = df.iloc[i]
        ema21 = float(row["ema21"])
        ema55 = float(row["ema55"])
        rsi_val = float(row["rsi"])
        close = float(row["close"])
        atr_val = float(row["atr"])

        if in_trade:
            new_trail = close - 1.5 * atr_val
            trail_stop = max(trail_stop, new_trail)
            tp = entry_price * 1.12  # 12% TP
            hit_tp = float(row["high"]) >= tp
            hit_sl = float(row["low"]) <= trail_stop
            timeout = (i - entry_idx) >= 20

            if hit_tp or hit_sl or timeout:
                exit_p = tp if hit_tp else (trail_stop if hit_sl else close)
                pnl = (exit_p - entry_price) / entry_price * 100
                trades.append({"pnl": pnl, "win": pnl > 0})
                in_trade = False
        else:
            # Pullback buy in uptrend
            if ema21 > ema55 and close > ema55 and 30 <= rsi_val <= 50:
                in_trade = True
                entry_price = close
                entry_idx = i
                trail_stop = entry_price - 1.5 * atr_val

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

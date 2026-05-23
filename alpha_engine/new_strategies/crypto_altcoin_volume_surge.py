"""
Crypto Altcoin Volume Surge Momentum Strategy
- Targets low-pick altcoins: ADA, DOGE, SHIB, AVAX, MATIC/POL, DOT, FIL, NEAR, OP, ARB
- Strategy: Volume spike (>2x 20-day avg) + price momentum + RSI not overbought
- Pyramid stops: initial ATR-based SL, trail after 2% gain
- Assets: Low-coverage in existing system (these symbols have <5 picks historically)
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

# Low-pick crypto assets that need coverage
SYMBOLS = ["ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "NEAR-USD", "OP-USD", "ARB-USD", "FIL-USD", "ATOM-USD", "APT-USD"]
STRATEGY_NAME = "crypto_altcoin_volume_surge"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "crypto_altcoin_vol_report.json")


def fetch(symbol: str, period: str = "2y") -> pd.DataFrame:
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
    Entry: Volume > 2x 20-day MA AND close > EMA(10) > EMA(21) AND RSI 45-70
    Exit: Trailing stop (1.5x ATR) or 8% TP or 15 days
    """
    df = df.copy()
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["ema10"] = df["close"].ewm(span=10).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
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
        vol_surge = float(row["volume"]) > 2.0 * float(row["vol_ma20"])

        if in_trade:
            current_price = float(row["close"])
            # Update trailing stop
            new_trail = current_price - 1.5 * float(row["atr"])
            trail_stop = max(trail_stop, new_trail)

            tp = entry_price * 1.08  # 8% TP
            hit_tp = float(row["high"]) >= tp
            hit_sl = float(row["low"]) <= trail_stop
            timeout = (i - entry_idx) >= 15

            if hit_tp or hit_sl or timeout:
                if hit_tp:
                    exit_p = tp
                elif hit_sl:
                    exit_p = trail_stop
                else:
                    exit_p = current_price
                pnl = (exit_p - entry_price) / entry_price * 100
                trades.append({"pnl": pnl, "win": pnl > 0, "date": str(df.index[i])[:10]})
                in_trade = False
        else:
            # Trend up + volume surge + RSI health zone
            rsi_val = float(row["rsi"])
            if (float(row["close"]) > float(row["ema10"]) > float(row["ema21"])
                    and vol_surge
                    and 45 <= rsi_val <= 70
                    and float(row["close"]) > float(row["ema50"])):
                in_trade = True
                entry_price = float(row["close"])
                entry_idx = i
                trail_stop = entry_price - 1.5 * float(row["atr"])

    return trades


def main():
    results = []
    for symbol in SYMBOLS:
        print(f"  Backtesting {symbol} ...", flush=True)
        try:
            df = fetch(symbol)
            if len(df) < 80:
                print(f"    Skipping {symbol}: insufficient data")
                continue
            trades = run_backtest(df)
            if len(trades) < 5:
                print(f"    {symbol}: only {len(trades)} trades, skipping stats")
                continue

            pnls = [t["pnl"] for t in trades]
            wins = [t["win"] for t in trades]
            wr = sum(wins) / len(wins) * 100
            gross_win = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0)) or 0.001
            pf = gross_win / gross_loss

            # Walk-forward
            wf = walk_forward_validation(pnls)
            ci = bootstrap_ci(pnls)
            mc = monte_carlo_prob_profitable(pnls, n_sims=2000, horizon=30)
            proto = protocol_gate(trade_count=len(trades), win_rate=wr/100, profit_factor=pf, ci=ci, mc_prob=mc["prob_profitable"])

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

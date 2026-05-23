"""
Crypto Dead-Cat Bounce Short Strategy
- Insight from system data: SHORT = 56.7% WR vs LONG = 48.7% WR
- Strategy: Short altcoins during dead-cat bounces in bear market regime
- Regime filter: BTC below its 50-day SMA = crypto bear market
- Entry: RSI 55-70 (overbought bounce) + close < EMA21 (still in downtrend)
- This avoids catching falling knives on LONG and instead profits from failed bounces
- Symbols: major altcoins with highest liquidity
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

SYMBOLS = ["ADA-USD", "XRP-USD", "DOT-USD", "LINK-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "ETC-USD"]
BTC_SYMBOL = "BTC-USD"
STRATEGY_NAME = "crypto_dead_cat_short"
REPORT_FILE = os.path.join(os.path.dirname(__file__), "crypto_dead_cat_short_report.json")


def fetch(symbol: str, period: str = "3y") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    return df.dropna()


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


def run_backtest(df: pd.DataFrame, btc: pd.DataFrame) -> list:
    """
    Short dead-cat bounces when BTC is in bear market.
    Entry: BTC < BTC_SMA50 AND altcoin RSI 55-72 (overbought bounce) 
           AND altcoin close < EMA21 (still below trend)
           AND altcoin making higher than prev 3-day close (bounce pattern)
    Exit: 8% TP (down) or 1.5x ATR stop loss or 12 days
    """
    # Align BTC regime to altcoin dates
    btc_sma50 = btc["close"].rolling(50).mean()
    btc_bear = btc["close"] < btc_sma50
    btc_bear = btc_bear.reindex(df.index, method="ffill")

    df = df.copy()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema55"] = df["close"].ewm(span=55).mean()
    df["rsi"] = _rsi(df["close"], 14)
    df["atr"] = _atr(df, 14)
    df["close_3ago"] = df["close"].shift(3)
    df["btc_bear"] = btc_bear
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    sl = 0.0
    tp = 0.0
    entry_idx = 0

    for i in range(len(df)):
        row = df.iloc[i]
        close = float(row["close"])
        ema21 = float(row["ema21"])
        rsi_val = float(row["rsi"])
        atr_val = float(row["atr"])
        btc_is_bear = bool(row.get("btc_bear", False))

        if in_trade:
            # Short: profit when price falls
            hit_tp = float(row["low"]) <= tp
            hit_sl = float(row["high"]) >= sl
            timeout = (i - entry_idx) >= 12

            if hit_tp or hit_sl or timeout:
                exit_p = tp if hit_tp else (sl if hit_sl else close)
                # SHORT: PnL = (entry - exit) / entry * 100
                pnl = (entry_price - exit_p) / entry_price * 100
                trades.append({"pnl": pnl, "win": pnl > 0})
                in_trade = False
        else:
            # Bear regime + overbought bounce
            if (btc_is_bear
                    and close < ema21  # still in downtrend
                    and 55 <= rsi_val <= 72  # overbought relative to bear regime
                    and close > float(row.get("close_3ago", close))):  # making bounce
                in_trade = True
                entry_price = close
                entry_idx = i
                tp = entry_price * 0.92  # 8% profit target (downside)
                sl = entry_price + 1.5 * atr_val  # stop above

    return trades


def main():
    print("Fetching BTC regime data ...")
    btc = fetch(BTC_SYMBOL, period="3y")
    
    results = []
    for symbol in SYMBOLS:
        print(f"  Backtesting {symbol} ...", flush=True)
        try:
            df = fetch(symbol)
            if len(df) < 100:
                print(f"    Skipping {symbol}: insufficient data")
                continue

            # Align dates
            common = df.index.intersection(btc.index)
            df = df.loc[common]
            btc_aligned = btc.loc[common]

            trades = run_backtest(df, btc_aligned)
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
                "direction": "short",
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

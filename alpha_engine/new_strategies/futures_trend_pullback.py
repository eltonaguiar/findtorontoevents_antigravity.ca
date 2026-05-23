import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

from integration import save_live_pick
from protocol_validation import summarize_protocol

SYMBOLS = ["ES=F", "NQ=F", "GC=F", "CL=F", "HG=F"]
LOOKBACK_DAYS = 650


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def build_signals(df: pd.DataFrame) -> pd.DataFrame:
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)

    out = df.copy()
    out["ema20"] = c.ewm(span=20, adjust=False).mean()
    out["ema100"] = c.ewm(span=100, adjust=False).mean()
    out["rsi14"] = rsi(c, 14)
    out["atr14"] = tr.rolling(14).mean()
    out["signal"] = 0

    # Long pullback in uptrend
    out.loc[(out["ema20"] > out["ema100"]) & (out["rsi14"] < 42), "signal"] = 1
    # Short rally in downtrend
    out.loc[(out["ema20"] < out["ema100"]) & (out["rsi14"] > 58), "signal"] = -1
    return out


def run_backtest(df: pd.DataFrame):
    trades = []
    pos = 0
    entry = 0.0
    stop = 0.0

    for i in range(1, len(df)):
        p = float(df["Close"].iloc[i])
        sig = int(df["signal"].iloc[i])
        atr = float(df["atr14"].iloc[i]) if not np.isnan(df["atr14"].iloc[i]) else 0.0

        if pos != 0:
            pnl = (p / entry - 1) * 100 * pos
            if pos == 1:
                stop = max(stop, p - 2.0 * atr)
                if p <= stop or df["rsi14"].iloc[i] > 67:
                    trades.append(float(pnl))
                    pos = 0
            else:
                stop = min(stop, p + 2.0 * atr)
                if p >= stop or df["rsi14"].iloc[i] < 33:
                    trades.append(float(pnl))
                    pos = 0

        if pos == 0 and sig != 0 and atr > 0:
            pos = sig
            entry = p
            stop = p

    return trades


def normalize_symbol(sym: str) -> str:
    return sym.replace("=F", "") + "_F"


def main():
    print("Futures Trend Pullback (low-pick futures booster)")
    rows = []
    now = datetime.utcnow()
    start = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    for sym in SYMBOLS:
        df = yf.download(sym, start=start, interval="1d", progress=False)
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        sig_df = build_signals(df)
        pnls = run_backtest(sig_df)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        stats = summarize_protocol(pnls, wins, losses)
        rows.append({"symbol": sym, **stats})

        last = sig_df.iloc[-1]
        passes_live_gate = (
            stats["trades"] >= 10
            and stats["win_rate"] >= 50
            and stats["profit_factor"] >= 1.2
            and stats["monte_carlo"]["prob_profitable"] >= 0.6
        )

        if passes_live_gate and int(last["signal"]) != 0 and not np.isnan(last["atr14"]):
            p = float(last["Close"])
            atr = float(last["atr14"])
            signal = int(last["signal"])
            tp = p + (2.8 * atr * signal)
            sl = p - (1.8 * atr * signal)
            conf = min(0.88, max(0.6, stats["win_rate"] / 100.0 + 0.1))
            save_live_pick(
                strategy_name="futures_trend_pullback",
                symbol=normalize_symbol(sym),
                signal=signal,
                entry_price=p,
                tp=tp,
                sl=sl,
                confidence=conf,
                category="futures",
            )

    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "strategy": "futures_trend_pullback",
        "results": rows,
    }
    with open("alpha_engine/new_strategies/futures_trend_pullback_report.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    for r in rows:
        print(f"{r['symbol']}: WR={r['win_rate']:.1f}% PF={r['profit_factor']:.2f} Trades={r['trades']} MC={r['monte_carlo']['prob_profitable']:.2f}")


if __name__ == "__main__":
    main()

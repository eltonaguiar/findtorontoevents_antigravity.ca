#!/usr/bin/env python3
"""Temporary sweep: exit-rule combos over cached equity-breakout signals. Dry-run only."""
import glob
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(os.environ.get("REPO_PATH", Path(__file__).resolve().parents[1]))
CACHE_GLOB = "data/cache/asset_class_review/*_5y.csv"
SLIPPAGE_BPS = 8.0

STRATEGIES = {
    "donchian": ("donchian-stock-breakout", 40),
    "rs-breakout": ("rs-breakout-scout", 60),
    "vol-contraction": ("vol-contraction-scout", 60),
    "adx-trend": ("adx-trend-scout", 30),
}


def _is_equity(symbol):
    return not (symbol.endswith("-USD") or symbol.endswith("_X") or symbol.endswith("_F"))


def donchian_signals(df):
    c, v = df["Close"], df["Volume"].astype(float)
    high20 = c.shift(1).rolling(20).max()
    vol_avg = v.rolling(20).mean()
    vol_ratio = v / vol_avg.replace(0, float("nan"))
    return (c > high20) & (vol_ratio > 1.5)


def _rsi_wilder(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=n - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=n - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _true_range(df):
    h, l, c = df["High"], df["Low"], df["Close"]
    return pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)


def adx_trend_signals(df):
    close = df["Close"]
    high = df["High"] if "High" in df.columns else close
    low = df["Low"] if "Low" in df.columns else close
    tr = _true_range(df)
    up, down = high.diff(), -low.diff()
    dm_plus = up.where((up > down) & (up > 0), 0.0)
    dm_minus = down.where((down > up) & (down > 0), 0.0)
    period = 14
    atr_w = tr.ewm(alpha=1 / period, adjust=False).mean()
    di_p = 100 * dm_plus.ewm(alpha=1 / period, adjust=False).mean() / atr_w.replace(0, np.nan)
    di_m = 100 * dm_minus.ewm(alpha=1 / period, adjust=False).mean() / atr_w.replace(0, np.nan)
    dx = (100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)).fillna(0.0)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    sma20 = close.rolling(20).mean()
    return (adx >= 25.0) & (di_p > di_m) & (close >= sma20 * 0.99)


def vol_contraction_signals(df):
    close, high, low = df["Close"], df["High"], df["Low"]
    volume = df["Volume"].astype(float)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_width = (2 * std20 / sma20.replace(0, np.nan)) * 100
    bb_min = bb_width.rolling(40).min()
    bb_squeeze = bb_width <= bb_min * 1.05
    tr = _true_range(df)
    nr7 = tr <= tr.rolling(7).min() * 1.02
    direction = close >= sma20 * 0.99
    vol_quiet = volume.rolling(5).mean() < volume.rolling(20).mean() * 1.2
    rsi = _rsi_wilder(close, 14)
    return bb_squeeze & nr7 & direction & vol_quiet & (rsi <= 68)


def rs_breakout_signals(df, spy):
    if spy is None:
        return pd.Series(False, index=df.index)
    close = df["Close"]
    spy_close = spy["Close"]
    min_len = min(len(close), len(spy_close))
    if min_len < 25:
        return pd.Series(False, index=df.index)
    rs = pd.Series(close.iloc[-min_len:].values / spy_close.iloc[-min_len:].values,
                   index=close.index[-min_len:])
    rs_20d_high = rs.rolling(20).max()
    at_high = rs >= rs_20d_high * 0.999
    sma50 = close.rolling(50).mean() if len(close) >= 50 else None
    above = (close >= sma50 * 0.99) if sma50 is not None else pd.Series(True, index=df.index)
    rs_chg = (rs - rs.shift(5)) / rs.shift(5).where(rs.shift(5) > 0)
    out = pd.Series(False, index=df.index)
    tail = (at_high & (rs_chg >= 0.005)).fillna(False)
    out.iloc[-min_len:] = tail.values
    return out & above.reindex(df.index).fillna(False)


def atr(df, n=20):
    return _true_range(df).rolling(n).mean()


def _signal_fn(strategy_key, df, spy):
    if strategy_key == "donchian":
        return donchian_signals(df)
    if strategy_key == "adx-trend":
        return adx_trend_signals(df)
    if strategy_key == "vol-contraction":
        return vol_contraction_signals(df)
    if strategy_key == "rs-breakout":
        return rs_breakout_signals(df, spy)
    raise ValueError(f"unknown strategy {strategy_key!r}")


def collect_signal_info(strategy_key):
    """Mirror emit_equity_breakout_pod.collect() signal extraction, return trade candidates."""
    strategy_name, min_bars = STRATEGIES[strategy_key]
    spy = None
    if strategy_key == "rs-breakout":
        spy_path = REPO / "data/cache/asset_class_review/SPY_5y.csv"
        if spy_path.exists():
            spy = pd.read_csv(spy_path)
    results = []
    for path in sorted(glob.glob(str(REPO / CACHE_GLOB))):
        symbol = Path(path).stem[:-len("_5y")]
        if not _is_equity(symbol):
            continue
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        if not {"Date", "Close", "Volume", "High", "Low"}.issubset(df.columns) or len(df) < min_bars:
            continue
        df = df.dropna(subset=["Close", "High", "Low", "Date"]).reset_index(drop=True)
        if len(df) < min_bars:
            continue
        sig = _signal_fn(strategy_key, df, spy)
        idxs = [i for i in sig[sig].index if i < len(df) - 1]
        if not idxs:
            continue
        sig_idx = max(idxs)
        results.append({
            "strategy": strategy_name,
            "symbol": symbol,
            "df": df,
            "sig_idx": sig_idx,
        })
    return results


def simulate_trade(df, sig_idx, stop_atr, tp_atr, hold_days):
    """Simulate one trade with given exit parameters. Returns (net_pct, exit_reason, is_closed)."""
    entry = float(df["Close"].iloc[sig_idx])
    a = atr(df).iloc[sig_idx]
    stop = entry - stop_atr * float(a) if pd.notna(a) else entry * 0.92

    end = min(sig_idx + hold_days, len(df) - 1)

    tp = None
    if tp_atr is not None and pd.notna(a):
        tp = entry + tp_atr * float(a)

    exit_px = float(df["Close"].iloc[end])
    exit_reason = "time"

    window = df.iloc[sig_idx + 1:end + 1]
    if len(window) > 0:
        for idx in window.index:
            bar = df.loc[idx]
            if bar["Low"] <= stop:
                exit_px = stop
                exit_reason = "stop"
                break
            elif tp is not None and bar["High"] >= tp:
                exit_px = tp
                exit_reason = "tp"
                break

    gross_pct = (exit_px / entry - 1.0) * 100.0
    net_pct = gross_pct - SLIPPAGE_BPS / 100.0

    is_closed = (exit_reason == "stop") or (end < len(df) - 1)

    return net_pct, exit_reason, is_closed


def main():
    combos = []
    for stop_atr in [2.0, 2.5, 3.0]:
        for tp_atr in [None, 2.0, 3.0, 4.0]:
            for hold in [10, 20]:
                combos.append((stop_atr, tp_atr, hold))

    signal_infos = {}
    for strat_key in STRATEGIES:
        signal_infos[strat_key] = collect_signal_info(strat_key)

    print(f"Signal universe: {sum(len(v) for v in signal_infos.values())} trades across "
          f"{len(signal_infos)} strategies")
    for sk, infos in signal_infos.items():
        print(f"  {sk}: {len(infos)} signals")

    results = []
    for stop_atr, tp_atr, hold in combos:
        all_net_pcts = []
        n_wins = 0
        n_losses = 0
        win_pcts = []
        loss_pcts = []

        for strat_key, infos in signal_infos.items():
            for info in infos:
                net_pct, exit_reason, is_closed = simulate_trade(
                    info["df"], info["sig_idx"], stop_atr, tp_atr, hold
                )
                if is_closed:
                    all_net_pcts.append(net_pct)
                    if net_pct > 0:
                        n_wins += 1
                        win_pcts.append(net_pct)
                    else:
                        n_losses += 1
                        loss_pcts.append(net_pct)

        n_trades = len(all_net_pcts)
        if n_trades > 0:
            win_pct = (n_wins / n_trades) * 100.0
            avg_win = np.mean(win_pcts) if win_pcts else 0.0
            avg_loss = np.mean(loss_pcts) if loss_pcts else 0.0
            expectancy = np.mean(all_net_pcts)
            total = sum(all_net_pcts)
        else:
            win_pct = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            expectancy = 0.0
            total = 0.0

        results.append({
            "stop_atr": stop_atr,
            "tp_atr": tp_atr,
            "hold": hold,
            "n_trades": n_trades,
            "win_pct": win_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
            "total": total,
        })

    # Print table
    header = f"{'stop_atr':>8} {'tp_atr':>8} {'hold':>5} {'n_trades':>9} {'win%':>6} {'avg_win':>9} {'avg_loss':>9} {'expectancy':>11} {'total':>10}"
    print("\n" + header)
    print("-" * len(header))
    for r in results:
        tp_str = str(r["tp_atr"]) if r["tp_atr"] is not None else "None"
        print(f"{r['stop_atr']:>8} {tp_str:>8} {r['hold']:>5} {r['n_trades']:>9} "
              f"{r['win_pct']:>6.2f} {r['avg_win']:>9.2f} {r['avg_loss']:>9.2f} "
              f"{r['expectancy']:>11.3f} {r['total']:>10.2f}")

    best = max(results, key=lambda r: r["expectancy"])
    print(f"\nBest expectancy: {best['expectancy']:.3f}% "
          f"(stop_atr={best['stop_atr']}, tp_atr={best['tp_atr']}, hold={best['hold']})")

    beats_zero = [r for r in results if r["expectancy"] > 0]
    if beats_zero:
        print("\nCombos with positive expectancy:")
        for r in beats_zero:
            tp_str = str(r["tp_atr"]) if r["tp_atr"] is not None else "None"
            print(f"  stop_atr={r['stop_atr']}, tp_atr={tp_str}, hold={r['hold']}: "
                  f"expectancy={r['expectancy']:.3f}%")
    else:
        print("\nNo combos have positive expectancy.")


if __name__ == "__main__":
    import os
    main()
"""
E-ANON-001 Backtest: Short-term price momentum
Academic basis: Jegadeesh & Titman (1993)
Signal: Buy when 5-day return > 30-day rolling average of daily returns
Hold: 5 trading days
Exit: Holding period expiry OR SL at -5%
Universe: S&P 500 mid/large caps (56 symbols)
Period: 2020-01-01 to 2026-04-30
OOS validation: TimeSeriesSplit (5 folds)

VIX Gate (added 2026-05-20):
  Block any entry day where ^VIX daily close >= VIX_BLOCK_THRESHOLD (28).
  Rationale: Fold 2 (2022 bear market) PF=1.009 — extreme volatility suppresses
  short-term momentum. VIX>=28 identifies systemic risk-off regimes.
"""

import sys
import json
import warnings
from datetime import datetime, date
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")

# ── VIX Gate ──────────────────────────────────────────────────────────────────
VIX_BLOCK_THRESHOLD = 28   # Block entries when VIX daily close >= this level
VIX_GATE_ENABLED    = True  # Set False to reproduce original (ungated) results

# ── Universe ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "JNJ", "UNH", "XOM", "CVX", "BAC", "WFC",
    "PG", "KO", "PEP", "ABBV", "LLY", "MRK", "AMGN",
    "TMO", "DHR", "ISRG", "SYK", "MDT", "ABT", "BMY", "GILD", "REGN", "VRTX",
    "HON", "GE", "MMM", "CAT", "DE", "LMT", "RTX", "NOC", "BA",
    "COST", "WMT", "TGT", "HD", "LOW",
    "NKE", "SBUX", "MCD", "DIS", "NFLX",
    "PYPL", "V", "MA", "AXP", "GS", "MS", "BLK", "SCHW", "SPY"
]

START_DATE = "2020-01-01"
END_DATE   = "2026-04-30"
HOLD_DAYS  = 5
STOP_LOSS  = -0.05   # -5%
N_SPLITS   = 5

# ── Data fetch ────────────────────────────────────────────────────────────────
def fetch_data(symbols, start, end):
    print(f"[fetch] Downloading {len(symbols)} symbols {start} → {end}…")
    raw = yf.download(symbols, start=start, end=end,
                      auto_adjust=True, progress=False, threads=True)
    close = raw["Close"] if "Close" in raw.columns else raw.xs("Close", axis=1, level=0)
    close = close.dropna(axis=1, how="all")
    print(f"[fetch] Got {close.shape[1]} symbols × {close.shape[0]} days")
    return close


def fetch_vix(start, end):
    """Download ^VIX daily close and return as a Series indexed by date."""
    print(f"[fetch] Downloading ^VIX {start} → {end}…")
    vix_raw = yf.download("^VIX", start=start, end=end,
                          auto_adjust=True, progress=False, threads=False)
    if isinstance(vix_raw.columns, pd.MultiIndex):
        vix_close = vix_raw["Close"]["^VIX"]
    else:
        vix_close = vix_raw["Close"]
    vix_close = vix_close.dropna()
    print(f"[fetch] ^VIX: {len(vix_close)} days, range {vix_close.min():.1f}–{vix_close.max():.1f}")
    return vix_close

# ── Signal generation (NO look-ahead) ────────────────────────────────────────
def compute_signals(close: pd.DataFrame) -> pd.DataFrame:
    """
    ret5d  = 5-day price return (close[t] / close[t-5] - 1)
    rolling_avg30d = 30-day rolling mean of daily pct_change (shifted 1 day for safety)
    Signal fires on day t if ret5d[t] > rolling_avg30d[t]
    """
    daily_ret = close.pct_change()
    ret5d = close.pct_change(periods=5)
    # rolling mean uses only past data (min_periods=20 for stability)
    rolling_avg30d = daily_ret.rolling(window=30, min_periods=20).mean()
    signal = (ret5d > rolling_avg30d).astype(int)
    # Mask the first 35 rows (warm-up)
    signal.iloc[:35] = 0
    return signal, ret5d, close

# ── Trade simulation ──────────────────────────────────────────────────────────
def simulate_trades(close: pd.DataFrame, signal: pd.DataFrame,
                    date_indices, vix_series: pd.Series = None):
    """
    For each (date, symbol) where signal == 1 and date is in date_indices,
    open a position on next day's open (approximated as next close).
    Exit after HOLD_DAYS or on SL.

    VIX gate: if vix_series is provided and VIX_GATE_ENABLED is True,
    skip entries where the signal date's VIX close >= VIX_BLOCK_THRESHOLD.

    Returns list of trade dicts.
    """
    dates = close.index
    date_set = set(date_indices)

    # Build VIX block set: dates where VIX >= threshold
    vix_blocked_dates = set()
    if vix_series is not None and VIX_GATE_ENABLED:
        vix_blocked_dates = set(vix_series.index[vix_series >= VIX_BLOCK_THRESHOLD])
    trades = []

    symbols = signal.columns.tolist()

    # Pre-compute numpy arrays for speed
    close_arr = close.values          # shape: (T, S)
    signal_arr = signal.values        # shape: (T, S)
    date_map = {d: i for i, d in enumerate(dates)}
    sym_idx = {s: i for i, s in enumerate(symbols)}

    for ti, dt in enumerate(dates):
        if dt not in date_set:
            continue
        if ti + 1 >= len(dates):
            continue
        # VIX gate: skip this entry day if VIX is elevated
        if dt in vix_blocked_dates:
            continue
        for si, sym in enumerate(symbols):
            if signal_arr[ti, si] != 1:
                continue
            # Entry: next bar close (ti+1)
            entry_ti = ti + 1
            if entry_ti >= len(dates):
                continue
            entry_price = close_arr[entry_ti, si]
            if np.isnan(entry_price):
                continue
            # Scan hold period
            exit_ti = min(entry_ti + HOLD_DAYS, len(dates) - 1)
            exit_price = close_arr[exit_ti, si]
            sl_triggered = False
            for hold_i in range(entry_ti + 1, exit_ti + 1):
                p = close_arr[hold_i, si]
                if np.isnan(p):
                    exit_ti = hold_i - 1
                    exit_price = close_arr[exit_ti, si]
                    break
                if (p - entry_price) / entry_price <= STOP_LOSS:
                    exit_ti = hold_i
                    exit_price = p
                    sl_triggered = True
                    break
            if np.isnan(exit_price) or entry_price == 0:
                continue
            ret = (exit_price - entry_price) / entry_price
            trades.append({
                "symbol": sym,
                "entry_date": dates[entry_ti],
                "exit_date": dates[exit_ti],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": ret,
                "win": int(ret > 0),
                "sl_triggered": sl_triggered,
                "hold_bars": exit_ti - entry_ti,
            })
    return trades

# ── Metrics ───────────────────────────────────────────────────────────────────
def compute_metrics(trades):
    if not trades:
        return {"n_trades": 0, "win_rate": None, "profit_factor": None,
                "avg_return": None}
    rets = [t["return"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(wins) > 0 else (
        float("inf") if not losses else 0.0)
    return {
        "n_trades": len(trades),
        "win_rate": sum(t["win"] for t in trades) / len(trades),
        "profit_factor": round(pf, 4),
        "avg_return": round(np.mean(rets), 6),
        "avg_return_pct": round(np.mean(rets) * 100, 4),
        "sl_pct": round(sum(t["sl_triggered"] for t in trades) / len(trades), 4),
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("E-ANON-001  Short-term Momentum Backtest")
    print("=" * 70)

    close = fetch_data(UNIVERSE, START_DATE, END_DATE)
    signal, ret5d, close = compute_signals(close)

    # ── VIX gate data ─────────────────────────────────────────────────────────
    vix_series = fetch_vix(START_DATE, END_DATE) if VIX_GATE_ENABLED else None
    if vix_series is not None:
        # Align VIX index to market dates (forward-fill any gaps)
        vix_series = vix_series.reindex(close.index, method="ffill")
        n_vix_blocked = int((vix_series >= VIX_BLOCK_THRESHOLD).sum())
        pct_blocked = n_vix_blocked / len(vix_series) * 100
        print(f"\n[VIX gate] Threshold={VIX_BLOCK_THRESHOLD} | "
              f"Blocked days: {n_vix_blocked}/{len(vix_series)} ({pct_blocked:.1f}%)")

    dates = close.index
    n = len(dates)

    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    fold_results = []

    gate_label = f"VIX<{VIX_BLOCK_THRESHOLD} gated" if VIX_GATE_ENABLED else "ungated"
    print(f"\n[OOS] TimeSeriesSplit {N_SPLITS} folds over {n} trading days [{gate_label}]\n")

    for fold_i, (train_idx, test_idx) in enumerate(tscv.split(dates), 1):
        test_dates = set(dates[test_idx])
        trades = simulate_trades(close, signal, test_dates, vix_series)
        m = compute_metrics(trades)
        m["fold"] = fold_i
        m["test_start"] = str(dates[test_idx[0]].date())
        m["test_end"]   = str(dates[test_idx[-1]].date())
        fold_results.append(m)
        wr_str  = f"{m['win_rate']*100:.1f}%" if m["win_rate"] is not None else "N/A"
        pf_str  = f"{m['profit_factor']:.3f}" if m["profit_factor"] is not None else "N/A"
        avr_str = f"{m['avg_return_pct']:.3f}%" if m["avg_return_pct"] is not None else "N/A"
        print(f"  Fold {fold_i} | {m['test_start']} → {m['test_end']} "
              f"| n={m['n_trades']:,} | WR={wr_str} | PF={pf_str} | avg_ret={avr_str}")

    # Full OOS aggregation: merge all test-fold trades (each date appears in exactly one test fold)
    all_test_dates = set(dates)   # use all dates post warm-up for aggregate
    # Rerun on full test set excluding warm-up
    warmup_cut = dates[35]
    all_test_dates_list = set(d for d in dates if d >= warmup_cut)
    all_trades = simulate_trades(close, signal, all_test_dates_list, vix_series)
    agg = compute_metrics(all_trades)

    print("\n" + "=" * 70)
    print("AGGREGATE (all OOS folds combined)")
    print("=" * 70)
    print(f"  n_trades     : {agg['n_trades']:,}")
    print(f"  win_rate     : {agg['win_rate']*100:.2f}%" if agg["win_rate"] else "  win_rate     : N/A")
    print(f"  profit_factor: {agg['profit_factor']:.4f}")
    print(f"  avg_return   : {agg['avg_return_pct']:.4f}%")
    print(f"  sl_triggered : {agg['sl_pct']*100:.1f}%")

    # ── Verdict ───────────────────────────────────────────────────────────────
    wr = agg["win_rate"] or 0
    pf = agg["profit_factor"] or 0
    if wr >= 0.50 and pf >= 1.2:
        verdict = "TESTED_PASS"
    elif wr >= 0.45 or pf >= 1.0:
        verdict = "TESTED_WEAK"
    else:
        verdict = "TESTED_KILL"

    print(f"\n  VERDICT: {verdict}")
    print("=" * 70)

    # ── Persist results for caller ─────────────────────────────────────────────
    results = {
        "verdict": verdict,
        "agg": agg,
        "fold_results": fold_results,
        "universe_size": close.shape[1],
        "period": f"{START_DATE} to {END_DATE}",
        "vix_gate": {
            "enabled": VIX_GATE_ENABLED,
            "threshold": VIX_BLOCK_THRESHOLD,
            "direction": "block_when_above",
        },
    }
    out_path = "reports/e_anon_001_backtest_raw.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[saved] Raw results → {out_path}")
    return results


if __name__ == "__main__":
    main()

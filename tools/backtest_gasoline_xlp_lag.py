#!/usr/bin/env python3
"""Gasoline (RB=F) -> XLP/XLY lag-correlation backtest.

Per gas-price swarm consensus 2026-05-13 (4/4 engines):
  Gasoline prices lead consumer-staples/discretionary by 5-15 days.

Test:
  1. Cross-correlation matrix: RB=F daily returns vs XLP/XLY daily returns at lags 0..30
  2. Identify peak-correlation lag
  3. Build position-rotation strategy: when RB=F 5d return > X%, go long XLP (defensive)
     vs short XLY (discretionary spending pressure)

Universe: RB=F (gasoline futures), XLP (consumer staples ETF), XLY (consumer discretionary ETF).

NFA - hindsight backtest.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ["RB=F", "XLP", "XLY", "SPY"]


def fetch_daily(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes.dropna(how="all")


def cross_corr_matrix(rb_returns, target_returns, max_lag=30):
    """Return DataFrame of cross-correlations at lags 0..max_lag (RB leads target)."""
    rows = []
    for lag in range(0, max_lag + 1):
        # corr(RB at t, target at t+lag)
        rb_shifted = rb_returns.shift(0)
        tgt_shifted = target_returns.shift(-lag)
        # Drop NaN pairs
        df = pd.concat([rb_shifted.rename("rb"), tgt_shifted.rename("tgt")], axis=1).dropna()
        if len(df) < 100:
            corr = np.nan
        else:
            corr = df["rb"].corr(df["tgt"])
        rows.append({"lag": lag, "corr": corr, "n": len(df)})
    return pd.DataFrame(rows)


def backtest_rotation(closes, gas_lookback=5, gas_threshold_pct=2.0,
                      hold_days=10):
    """Long XLP / short XLY rotation when 5d gasoline change > threshold."""
    rb_5d = closes["RB=F"].pct_change(gas_lookback) * 100
    xlp_rets_fwd = closes["XLP"].pct_change(hold_days).shift(-hold_days)
    xly_rets_fwd = closes["XLY"].pct_change(hold_days).shift(-hold_days)

    # Signals: gas-spike triggers long XLP / short XLY
    signal = (rb_5d > gas_threshold_pct).fillna(False)
    # Drop overlapping signals — re-arm after hold_days
    trades = []
    in_position = False
    last_entry = -hold_days - 1
    for i, (date, sig) in enumerate(signal.items()):
        if not sig: continue
        if i - last_entry < hold_days: continue
        last_entry = i
        xlp_r = xlp_rets_fwd.iloc[i] if i < len(xlp_rets_fwd) else None
        xly_r = xly_rets_fwd.iloc[i] if i < len(xly_rets_fwd) else None
        if xlp_r is None or pd.isna(xlp_r): continue
        if xly_r is None or pd.isna(xly_r): continue
        # Long-XLP / short-XLY = relative trade
        pair_ret = (xlp_r - xly_r)  # excess return
        trades.append({
            "date": date.strftime("%Y-%m-%d"),
            "rb_5d_pct": float(rb_5d.iloc[i]),
            "xlp_fwd_pct": float(xlp_r) * 100,
            "xly_fwd_pct": float(xly_r) * 100,
            "pair_excess_pct": float(pair_ret) * 100,
        })
    if not trades: return None
    excess = [t["pair_excess_pct"]/100 for t in trades]
    n = len(excess)
    w = sum(1 for r in excess if r > 0)
    l = sum(1 for r in excess if r < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = sum(r for r in excess if r > 0)
    losses = sum(-r for r in excess if r < 0)
    pf = wins/losses if losses > 0 else 999
    mean = float(np.mean(excess))
    std = float(np.std(excess, ddof=1)) if n > 1 else 0
    # Sharpe annualized: ~25 trades/yr at 10d hold
    trades_per_year = 252 / (hold_days * 2)
    sharpe = (mean/std * np.sqrt(trades_per_year)) if std > 0 else 0
    return {
        "n_trades": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "mean_excess_pct": round(mean*100, 3),
        "std_pct": round(std*100, 3),
        "trades_per_year": round(trades_per_year, 1),
        "sample_trades": trades[-5:],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/gasoline_xlp_lag_backtest.json")
    args = p.parse_args()

    print(f"# fetching RB=F + XLP + XLY + SPY daily", file=sys.stderr)
    closes = fetch_daily(UNIVERSE, args.start, args.end)
    print(f"# closes shape: {closes.shape}", file=sys.stderr)
    rets = closes.pct_change().dropna(how="all")

    # Cross-correlation: RB=F vs XLP and XLY
    if "RB=F" not in rets.columns:
        print("ERROR: RB=F missing", file=sys.stderr); sys.exit(1)
    print(f"\n## Cross-correlation analysis (RB=F leads target)\n", file=sys.stderr)
    rb_rets = rets["RB=F"]
    xc_xlp = cross_corr_matrix(rb_rets, rets["XLP"], max_lag=30)
    xc_xly = cross_corr_matrix(rb_rets, rets["XLY"], max_lag=30)

    print(f"{'lag':>4} {'XLP':>8} {'XLY':>8} {'diff':>8}", file=sys.stderr)
    for i in range(0, 31, 2):
        row_xlp = xc_xlp[xc_xlp.lag == i].iloc[0]
        row_xly = xc_xly[xc_xly.lag == i].iloc[0]
        diff = row_xlp["corr"] - row_xly["corr"]
        print(f"  {i:>2} {row_xlp['corr']:>+8.3f} {row_xly['corr']:>+8.3f} {diff:>+8.3f}",
              file=sys.stderr)

    # Peak-correlation lag (XLP)
    peak_xlp = xc_xlp.loc[xc_xlp["corr"].idxmax()] if not xc_xlp["corr"].isna().all() else None
    peak_xly = xc_xly.loc[xc_xly["corr"].idxmax()] if not xc_xly["corr"].isna().all() else None
    print(f"\n  Peak XLP corr: lag={int(peak_xlp['lag'])} corr={peak_xlp['corr']:.3f}",
          file=sys.stderr)
    print(f"  Peak XLY corr: lag={int(peak_xly['lag'])} corr={peak_xly['corr']:.3f}",
          file=sys.stderr)

    # Backtest variants
    print(f"\n## Rotation backtest (long XLP / short XLY when RB 5d > threshold)", file=sys.stderr)
    variants = []
    for threshold in [1.0, 2.0, 3.0, 5.0]:
        for hold in [5, 10, 15]:
            r = backtest_rotation(closes, gas_threshold_pct=threshold, hold_days=hold)
            if not r: continue
            r["gas_threshold_pct"] = threshold
            r["hold_days"] = hold
            variants.append(r)
            print(f"  RB-5d>{threshold:>4.1f}%, hold={hold:>2}d: "
                  f"n={r['n_trades']:>3} WR={r['win_rate_pct']:>5.1f}% "
                  f"PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f}",
                  file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Gasoline (RB=F) -> XLP/XLY lag-correlation + pair-trade backtest",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end},
        "cross_correlation_xlp": xc_xlp.to_dict("records"),
        "cross_correlation_xly": xc_xly.to_dict("records"),
        "peak_xlp": {"lag": int(peak_xlp["lag"]), "corr": float(peak_xlp["corr"])} if peak_xlp is not None else None,
        "peak_xly": {"lag": int(peak_xly["lag"]), "corr": float(peak_xly["corr"])} if peak_xly is not None else None,
        "rotation_variants": variants,
        "expected_per_swarm": {"sharpe": 1.1, "lag_days": 10},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

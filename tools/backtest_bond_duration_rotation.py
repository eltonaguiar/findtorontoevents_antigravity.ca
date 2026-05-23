#!/usr/bin/env python3
"""BOND duration rotation: short-duration in inverted-curve regime.

Per BOND swarm 2026-05-13 (4/4 engines): rotate between long-duration (TLT)
and short-duration (SHY/BIL) based on 10y-2y yield-curve slope.

Simplified version using yfinance proxies (yield curve from ^TNX - ^FVX):
  - Curve steepening (TNX > FVX by >0.5%): TLT (long duration)
  - Curve flat/normal (TNX-FVX in [-0.5%, 0.5%]): IEF (mid duration)
  - Curve inverted (TNX < FVX by >0.5%): SHY (short duration, defensive)

NFA — hindsight backtest.
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
UNIVERSE = ["TLT", "IEF", "SHY"]


def fetch_monthly(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2003-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/bond_duration_rotation_backtest.json")
    args = p.parse_args()

    print(f"# fetching TLT/IEF/SHY + yield curve proxies", file=sys.stderr)
    bonds = fetch_monthly(UNIVERSE, args.start, args.end)
    bond_rets = bonds.pct_change().dropna(how="all")
    # ^TNX = 10y yield index, ^FVX = 5y yield index (close proxy for 10y-2y slope)
    yields = fetch_monthly(["^TNX", "^FVX"], args.start, args.end)
    if yields.empty:
        print("ERROR: yield fetch failed", file=sys.stderr); sys.exit(1)
    yields = yields.ffill().dropna(how="any")

    # Compute 10y-5y spread (proxy for 10y-2y curve)
    spread = yields["^TNX"] - yields["^FVX"]
    print(f"# yield data: {len(yields)} months, spread range "
          f"{spread.min():.2f} to {spread.max():.2f}", file=sys.stderr)

    trades_rotation = []
    history = []
    eq = 1.0; peak = 1.0; max_dd = 0
    w = lo = 0; w_pnl = lo_pnl = 0.0
    regime_counts = {"long": 0, "mid": 0, "short": 0}
    for i in range(1, len(bond_rets)):
        date = bond_rets.index[i]
        # Find most recent spread <= signal date
        spread_prior = spread[spread.index <= date]
        if spread_prior.empty: continue
        s = float(spread_prior.iloc[-1])
        if s > 0.5:
            pick_ticker = "TLT"; regime_counts["long"] += 1
        elif s < -0.5:
            pick_ticker = "SHY"; regime_counts["short"] += 1
        else:
            pick_ticker = "IEF"; regime_counts["mid"] += 1
        period_ret = bond_rets.iloc[i].get(pick_ticker)
        if pd.isna(period_ret): continue
        eq *= 1 + period_ret
        if period_ret > 0: w += 1; w_pnl += period_ret
        elif period_ret < 0: lo += 1; lo_pnl += abs(period_ret)
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak-eq)/peak)
        trades_rotation.append(period_ret)
        history.append({"date": date.strftime("%Y-%m-%d"),
                        "spread": round(s, 2),
                        "ticker": pick_ticker,
                        "ret_pct": round(float(period_ret)*100, 3)})

    n = len(trades_rotation)
    wr = w/(w+lo)*100 if (w+lo) else 0
    pf = w_pnl/lo_pnl if lo_pnl > 0 else 999
    mean = float(np.mean(trades_rotation))
    std = float(np.std(trades_rotation, ddof=1)) if len(trades_rotation) > 1 else 0
    sharpe = (mean/std*np.sqrt(12)) if std > 0 else 0

    # Benchmarks
    tlt_only_rets = bond_rets["TLT"].dropna()
    bh_eq = (1 + tlt_only_rets).prod()
    bh_total = (bh_eq - 1) * 100
    bh_std = tlt_only_rets.std()
    bh_sharpe = (tlt_only_rets.mean()/bh_std * np.sqrt(12)) if bh_std > 0 else 0

    print(f"\n## Duration rotation (TLT/IEF/SHY)")
    print(f"n={n} WR={wr:.1f}% PF={pf:.2f} Sharpe={sharpe:.2f} MDD={max_dd*100:.1f}% Total={(eq-1)*100:+.1f}%")
    print(f"regime counts: {regime_counts}")
    print(f"\n## Buy-and-hold TLT benchmark")
    print(f"Sharpe={bh_sharpe:.2f}  Total={bh_total:+.1f}%")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Duration rotation via 10y-5y spread (^TNX-^FVX, proxy for 10y-2y)",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "rules": "spread>0.5: TLT; spread<-0.5: SHY; else IEF"},
        "results": {
            "n_periods": n, "win_rate_pct": round(wr, 2),
            "profit_factor": round(pf, 4),
            "sharpe_annualized": round(float(sharpe), 4),
            "max_drawdown_pct": round(float(max_dd)*100, 2),
            "total_return_pct": round(float(eq-1)*100, 2),
            "regime_counts": regime_counts,
            "history_tail": history[-12:],
        },
        "benchmark_bh_tlt": {
            "sharpe_annualized": round(float(bh_sharpe), 4),
            "total_return_pct": round(float(bh_total), 2),
        },
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

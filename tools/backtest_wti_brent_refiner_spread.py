#!/usr/bin/env python3
"""WTI-Brent spread -> US refiner equity lag-correlation backtest.

Per cerebras (gas-price swarm 2026-05-13): WTI-Brent spread leads MPC/VLO
returns by ~6 days (correlation 0.62). When WTI discount to Brent widens,
US refiners benefit from cheap domestic crude.

Test:
  1. Cross-correlation: (CL=F - BZ=F) daily change vs MPC/VLO/PSX daily returns at lags 0..30
  2. Identify peak-correlation lag
  3. Build position strategy: when WTI-Brent spread widens by X%, long refiner basket

Universe: CL=F (WTI), BZ=F (Brent), MPC + VLO + PSX (refiners), XLE (benchmark).

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
REFINERS = ["MPC", "VLO", "PSX"]
UNIVERSE = ["CL=F", "BZ=F"] + REFINERS + ["XLE"]


def fetch_daily(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes.dropna(how="all")


def cross_corr(driver, target, max_lag=30):
    rows = []
    for lag in range(0, max_lag + 1):
        d = driver.shift(0)
        t = target.shift(-lag)
        df = pd.concat([d.rename("d"), t.rename("t")], axis=1).dropna()
        if len(df) < 100:
            corr = np.nan
        else:
            corr = df["d"].corr(df["t"])
        rows.append({"lag": lag, "corr": corr, "n": len(df)})
    return pd.DataFrame(rows)


def backtest_refiner_long(closes, spread_change_5d_threshold=2.0,
                          hold_days=10):
    """Long refiner basket when WTI-Brent spread widens (CL/BZ ratio drops)."""
    # WTI-Brent spread = CL - BZ (negative when WTI cheaper)
    wti = closes["CL=F"]
    brent = closes["BZ=F"]
    spread = wti - brent  # negative = WTI discount
    # Signal: 5-day change in spread becomes more negative
    spread_5d_chg = spread.diff(5)

    # Basket: equal-weight MPC + VLO + PSX
    refiner_avg = closes[REFINERS].mean(axis=1)
    refiner_fwd = refiner_avg.pct_change(hold_days).shift(-hold_days)
    xle_fwd = closes["XLE"].pct_change(hold_days).shift(-hold_days)

    trades = []
    last_entry = -hold_days - 1
    for i, (date, chg) in enumerate(spread_5d_chg.items()):
        if pd.isna(chg): continue
        # Entry: spread became MORE NEGATIVE by threshold (WTI discount widened)
        if chg > -spread_change_5d_threshold: continue
        if i - last_entry < hold_days: continue
        last_entry = i
        ref_r = refiner_fwd.iloc[i] if i < len(refiner_fwd) else None
        xle_r = xle_fwd.iloc[i] if i < len(xle_fwd) else None
        if ref_r is None or pd.isna(ref_r): continue
        if xle_r is None or pd.isna(xle_r): continue
        # Excess return (refiner basket vs XLE)
        excess = ref_r - xle_r
        trades.append({
            "date": date.strftime("%Y-%m-%d"),
            "spread_5d_chg": float(chg),
            "refiner_fwd_pct": float(ref_r) * 100,
            "xle_fwd_pct": float(xle_r) * 100,
            "excess_pct": float(excess) * 100,
        })
    if not trades: return None
    excess = [t["excess_pct"]/100 for t in trades]
    n = len(excess)
    w = sum(1 for r in excess if r > 0)
    l = sum(1 for r in excess if r < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = sum(r for r in excess if r > 0)
    losses = sum(-r for r in excess if r < 0)
    pf = wins/losses if losses > 0 else 999
    mean = float(np.mean(excess))
    std = float(np.std(excess, ddof=1)) if n > 1 else 0
    trades_per_year = 252 / (hold_days * 2)
    sharpe = (mean/std * np.sqrt(trades_per_year)) if std > 0 else 0
    return {
        "n_trades": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "mean_excess_pct": round(mean*100, 3),
        "trades_per_year": round(trades_per_year, 1),
        "sample_trades": trades[-5:],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/wti_brent_refiner_backtest.json")
    args = p.parse_args()

    print(f"# fetching CL=F + BZ=F + refiners + XLE", file=sys.stderr)
    closes = fetch_daily(UNIVERSE, args.start, args.end)
    print(f"# closes shape: {closes.shape}", file=sys.stderr)
    rets = closes.pct_change().dropna(how="all")

    # Build WTI-Brent spread daily change
    spread = closes["CL=F"] - closes["BZ=F"]
    spread_chg = spread.diff()

    print(f"\n## Cross-correlation: WTI-Brent spread change vs refiner basket (lag = refiner leads)\n", file=sys.stderr)
    refiner_avg_ret = rets[REFINERS].mean(axis=1)
    xc = cross_corr(spread_chg, refiner_avg_ret, max_lag=30)

    print(f"{'lag':>4} {'corr':>9}", file=sys.stderr)
    for i in range(0, 31, 2):
        row = xc[xc.lag == i].iloc[0]
        print(f"  {i:>2} {row['corr']:>+9.3f}", file=sys.stderr)
    peak = xc.loc[xc["corr"].idxmax()] if not xc["corr"].isna().all() else None
    if peak is not None:
        print(f"\n  Peak corr: lag={int(peak['lag'])} corr={peak['corr']:.3f}", file=sys.stderr)
        print(f"  Cerebras claim was: lag=6 corr=0.62", file=sys.stderr)

    print(f"\n## Backtest (long refiner basket when WTI-Brent spread widens)", file=sys.stderr)
    variants = []
    for threshold in [1.0, 2.0, 3.0]:
        for hold in [5, 10, 15]:
            r = backtest_refiner_long(closes, spread_change_5d_threshold=threshold,
                                       hold_days=hold)
            if not r: continue
            r["spread_change_threshold"] = threshold
            r["hold_days"] = hold
            variants.append(r)
            print(f"  spread-Δ<-{threshold:>3.1f}, hold={hold:>2}d: "
                  f"n={r['n_trades']:>3} WR={r['win_rate_pct']:>5.1f}% "
                  f"PF={r['profit_factor']:>5.2f} Sharpe={r['sharpe_annualized']:>5.2f} "
                  f"excess_mean={r['mean_excess_pct']:>+6.3f}%", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "WTI-Brent spread -> US refiner basket lag-corr + pair trade",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end},
        "cross_correlation_refiner_avg": xc.to_dict("records"),
        "peak_corr": {"lag": int(peak["lag"]), "corr": float(peak["corr"])} if peak is not None else None,
        "backtest_variants": variants,
        "cerebras_claim": {"lag_days": 6, "correlation": 0.62},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""Does vol-targeting the core beat just holding it, after cost?

The per-class sweep found 0 cells clearing every gate, and G6b (volatility-matched) found
that the one near-pass - H-201 equity cross-sectional momentum - goes NEGATIVE once scaled
to the benchmark's volatility (matched CI-LB -0.533). That result is worth reading twice,
because it says the sweep's best candidate is not merely "small", it is *volatility* that
was doing the work, not selection.

Which raises the question this tool answers, and it needs no new alpha to answer: if
selection cannot beat the benchmark, can *risk management* beat it? Vol targeting is the
cheapest surviving candidate in the literature - it needs no forecast beyond realised
variance, it trades rarely, and on an ETF it costs single-digit bp per rebalance.

Two honest yardsticks, because the choice changes the answer:
  * Sharpe / certainty equivalent - the risk-adjusted view
  * CAGR and max drawdown - what a reader actually experiences

The trap this tool refuses to fall into is reporting vol targeting as a win because it has a
higher Sharpe while producing a lower CAGR, or vice versa. Both are printed, and the
verdict line names which yardstick it passed.

Costs: 5 bp round trip per unit of turnover on an ETF (spread + commission, deliberately
not zero). Leverage is capped and the position uses yesterday's realised vol, so it never
trades on information it could not have had.

Usage
  python3 tools/vol_target_vs_hold.py --start 2005-01-01 --out reports/portfolio/vol_target_vs_hold.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def download(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    return close.dropna(how="all")


def perf(ret: pd.Series, label: str) -> dict:
    r = ret.dropna()
    if len(r) < 60:
        return {"label": label, "error": "insufficient observations", "n": int(len(r))}
    eq = (1.0 + r).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / len(r)) - 1.0
    vol = r.std() * np.sqrt(TRADING_DAYS)
    sharpe = (r.mean() / r.std() * np.sqrt(TRADING_DAYS)) if r.std() > 0 else 0.0
    mdd = float((eq / eq.cummax() - 1.0).min())
    # certainty equivalent at risk aversion 1, annualised, on arithmetic returns
    ce = r.mean() * TRADING_DAYS - 0.5 * r.var() * TRADING_DAYS
    return {
        "label": label,
        "n_days": int(len(r)),
        "cagr_pct": round(float(cagr) * 100, 2),
        "vol_pct": round(float(vol) * 100, 2),
        "sharpe": round(float(sharpe), 3),
        "max_drawdown_pct": round(mdd * 100, 2),
        "ce_pct": round(float(ce) * 100, 2),
        "total_return_pct": round(float(eq.iloc[-1] - 1.0) * 100, 2),
    }


def vol_target(asset_ret: pd.Series, target: float, look: int, cap: float,
               cost_bp: float) -> tuple[pd.Series, pd.Series]:
    """Scale exposure to a target annualised vol using only information available yesterday."""
    rv = asset_ret.rolling(look).std() * np.sqrt(TRADING_DAYS)
    lev = (target / rv.replace(0.0, np.nan)).clip(lower=0.0, upper=cap).shift(1)
    lev = lev.fillna(0.0)
    turnover = lev.diff().abs().fillna(lev)
    net = lev * asset_ret - turnover * cost_bp / 1e4
    return net.dropna(), lev


def sma_filter(asset_ret: pd.Series, look: int, cost_bp: float) -> tuple[pd.Series, pd.Series]:
    """Long when close > its own SMA, flat otherwise; yesterday's signal, today's return."""
    px = (1.0 + asset_ret).cumprod()
    signal = (px > px.rolling(look).mean()).shift(1).fillna(False).astype(float)
    turnover = signal.diff().abs().fillna(signal)
    return (signal * asset_ret - turnover * cost_bp / 1e4).dropna(), signal


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--target", type=float, default=0.10, help="annualised vol target")
    ap.add_argument("--cap", type=float, default=2.0, help="max leverage")
    ap.add_argument("--look", type=int, default=60, help="realised-vol window (days)")
    ap.add_argument("--cost-bp", type=float, default=5.0, help="round trip per unit turnover")
    ap.add_argument("--out", default="reports/portfolio/vol_target_vs_hold.json")
    args = ap.parse_args()

    px = download(["SPY", "TLT", "GLD", "DBC"], args.start, args.end)
    rets = px.pct_change().dropna(how="all")
    print(f"data {px.index[0].date()} -> {px.index[-1].date()}  rows={len(px)}  "
          f"cols={list(px.columns)}")

    out: dict = {
        "generated_by": "tools/vol_target_vs_hold.py",
        "question": "can risk management beat buy-and-hold after cost, given that selection did not?",
        "window": {"start": str(px.index[0].date()), "end": str(px.index[-1].date())},
        "assumptions": {
            "vol_target": args.target,
            "leverage_cap": args.cap,
            "realised_vol_lookback_days": args.look,
            "cost_bp_per_unit_turnover": args.cost_bp,
            "signal_lag_days": 1,
            "note": "leverage uses yesterday's realised vol only; no forecast, no look-ahead",
        },
        "sleeves": [],
        "sensitivity": [],
        "verdict": {},
    }

    spy = rets["SPY"]

    # 1) plain hold vs vol-targeted hold
    hold = perf(spy, "SPY hold")
    vt, lev = vol_target(spy, args.target, args.look, args.cap, args.cost_bp)
    vt_perf = perf(vt, f"SPY vol-target {args.target:.0%} cap {args.cap:.0f}x")
    out["sleeves"].append(hold)
    out["sleeves"].append(vt_perf)
    out["sleeves"].append({"label": "SPY vol-target diagnostics",
                           "mean_leverage": round(float(lev.mean()), 3),
                           "max_leverage": round(float(lev.max()), 3),
                           "pct_time_levered_above_1": round(float((lev > 1).mean()) * 100, 1),
                           "pct_time_below_1": round(float((lev < 1).mean()) * 100, 1)})

    # 2) 60/40, monthly rebalanced, plain vs vol-targeted
    if {"TLT"}.issubset(rets.columns):
        w = pd.Series({"SPY": 0.60, "TLT": 0.40})
        monthly = rets[["SPY", "TLT"]].copy()
        # drift-free approximation: rebalance weights at each month start, cost applied then
        reb = monthly.index.to_period("M")
        port = pd.Series(0.0, index=monthly.index)
        prev_month = None
        cur_w = w.copy()
        for d, row in monthly.iterrows():
            m = d.to_period("M")
            if m != prev_month:
                # rebalance cost on the change in weights actually held
                cost = float((cur_w - w).abs().sum()) * args.cost_bp / 1e4
                cur_w = w.copy()
                prev_month = m
            else:
                cost = 0.0
            r = float((cur_w.fillna(0.0) * row.fillna(0.0)).sum()) - cost
            port.loc[d] = r
            if row.notna().all():
                grown = cur_w * (1.0 + row)
                s = grown.sum()
                if s > 0:
                    cur_w = grown / s
        port = port.dropna()
        out["sleeves"].append(perf(port, "60/40 monthly rebalanced"))
        port_vt, lev2 = vol_target(port, args.target, args.look, args.cap, args.cost_bp)
        out["sleeves"].append(perf(port_vt, f"60/40 vol-target {args.target:.0%}"))
        out["sleeves"].append({"label": "60/40 vol-target diagnostics",
                               "mean_leverage": round(float(lev2.mean()), 3)})

    # 3) SMA defensive timing on SPY
    sma_ret, sma_sig = sma_filter(spy, 200, args.cost_bp)
    out["sleeves"].append(perf(sma_ret, "SPY 200d SMA long/flat"))
    out["sleeves"].append({"label": "SPY SMA diagnostics",
                           "pct_time_in_market": round(float(sma_sig.mean()) * 100, 1)})

    # 4) target sensitivity - is the answer a function of an arbitrary choice?
    for tgt in (0.08, 0.10, 0.12, 0.15, 0.20):
        r, _ = vol_target(spy, tgt, args.look, args.cap, args.cost_bp)
        p = perf(r, f"SPY vol-target {tgt:.0%}")
        p["target"] = tgt
        out["sensitivity"].append(p)

    # verdict, stated against both yardsticks separately
    def better(a: dict, b: dict, key: str) -> bool:
        return key in a and key in b and a[key] > b[key]

    sharp_win = better(vt_perf, hold, "sharpe")
    cagr_win = better(vt_perf, hold, "cagr_pct")
    mdd_win = (vt_perf.get("max_drawdown_pct", -1e9) > hold.get("max_drawdown_pct", -1e9))
    ce_win = better(vt_perf, hold, "ce_pct")
    out["verdict"] = {
        "vol_target_vs_hold": {
            "sharpe_better": sharp_win,
            "cagr_better": cagr_win,
            "drawdown_better": mdd_win,
            "certainty_equivalent_better": ce_win,
            "sharpe_delta": round(vt_perf.get("sharpe", 0) - hold.get("sharpe", 0), 3),
            "cagr_delta_pct": round(vt_perf.get("cagr_pct", 0) - hold.get("cagr_pct", 0), 2),
            "mdd_delta_pct": round(vt_perf.get("max_drawdown_pct", 0)
                                   - hold.get("max_drawdown_pct", 0), 2),
            "honest_reading": (
                "vol targeting lowers both risk and return from the same asset; it is an "
                "improvement only if risk-adjusted return (Sharpe / CE) rises AND the reader "
                "wants that risk level. It is not alpha and must never be booked as such."),
        }
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"\n{'sleeve':<40}{'CAGR':>8}{'vol':>8}{'Sharpe':>8}{'MDD':>9}{'CE':>8}")
    for s in out["sleeves"]:
        if "cagr_pct" in s:
            print(f"{s['label']:<40}{s['cagr_pct']:>7.2f}%{s['vol_pct']:>7.2f}%"
                  f"{s['sharpe']:>8.3f}{s['max_drawdown_pct']:>8.2f}%{s['ce_pct']:>7.2f}%")
    print("\ntarget sensitivity (SPY):")
    for s in out["sensitivity"]:
        print(f"  {s['target']:>5.0%}  CAGR {s['cagr_pct']:>6.2f}%  vol {s['vol_pct']:>6.2f}%  "
              f"Sharpe {s['sharpe']:>6.3f}  MDD {s['max_drawdown_pct']:>7.2f}%  CE {s['ce_pct']:>6.2f}%")
    v = out["verdict"]["vol_target_vs_hold"]
    print(f"\nvol-target vs hold: Sharpe {v['sharpe_delta']:+.3f} ({'better' if v['sharpe_better'] else 'worse'}), "
          f"CAGR {v['cagr_delta_pct']:+.2f}pp, MDD {v['mdd_delta_pct']:+.2f}pp, "
          f"CE {'better' if v['certainty_equivalent_better'] else 'worse'}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

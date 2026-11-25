"""Turn-of-month seasonality — programme item B13.

The cheapest family left untested: a few trades per month at ETF cost. If ANY calendar
effect survives cost and a random-window null, it is a legitimate low-turnover candidate;
if it does not, the equity seasonality family closes and the programme stops spending
attention on it.

Pre-registered before the run (M-107), so the test cannot drift to fit the result:
  * SPY daily total return, 1993-01-29 .. last available
  * TOM window = last trading day of month (L) through the 3rd trading day of next month
    (L, +1, +2, +3), the classic construction, held LONG ONLY, flat otherwise
  * also reported: L only, and L+1..+3 only, so the headline is not a choice among three
  * cost 5 bp per unit of turnover (ETF); stress at 10 bp
  * excess return over ^IRX/252 daily accrual; every Sharpe is over that, never over zero
  * GATE: bootstrap CI-LB on mean daily EXCESS return > 0, both halves positive, and the
    observed mean must beat a random-window null that holds the SAME number of days at
    95th percentile. All three, or it does not pass.

Usage
  python3 tools/turn_of_month_check.py --out reports/turn_of_month_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TD = 252


def download(start, end) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(["SPY", "^IRX"], start=start, end=end, auto_adjust=True,
                      progress=False, threads=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    return close.dropna(how="any")


def boot_lb(x, n=5000, seed=20261122):
    if len(x) < 30:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    k = len(x)
    means = np.array([x[rng.integers(0, k, k)].mean() for _ in range(n)])
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


def position_mask(idx: pd.DatetimeIndex, include: tuple[int, ...]) -> np.ndarray:
    """1.0 on the trading days named by `include`, where 0 = last trading day of month."""
    months = pd.Series(idx, index=idx).groupby([idx.year, idx.month])
    ordinals = np.full(len(idx), 99, dtype=int)     # position within the month
    for _, grp in months:
        first = idx.get_loc(grp.iloc[0])
        for j in range(len(grp)):
            ordinals[first + j] = j
    # distance from month end
    from_end = np.full(len(idx), 99, dtype=int)
    for _, grp in months:
        first = idx.get_loc(grp.iloc[0])
        n = len(grp)
        for j in range(n):
            from_end[first + j] = j - n       # negative: -1 is last day
    mask = np.zeros(len(idx))
    for k in include:
        if k == 0:
            mask[from_end == -1] = 1.0
        else:
            mask[ordinals == k] = 1.0
    return mask


def gross_excess_bps(ret, rf_d, mask):
    """Mean daily excess BEFORE cost. Needed because the random-window null is costless:
    comparing a NET observed mean to a GROSS null understates the percentile and was the
    third bug caught in this tool (see updates/2026-11-22-turn-of-month-refuted.md)."""
    ex = mask * ret - mask * rf_d
    return float(ex.mean()) * 1e4


def run(idx, ret, rf_d, mask, cost_bp):
    prev = np.concatenate([[0.0], mask[:-1]])
    turn = np.abs(mask - prev)
    net = mask * ret - turn * cost_bp / 1e4
    ex = net - mask * rf_d
    n = len(ex)
    half = n // 2
    lb, ub = boot_lb(ex)
    sd = ex.std(ddof=1)
    return {"n_days": int(n), "days_held": int(mask.sum()),
            "pct_held": round(float(mask.mean()) * 100, 2),
            "trades": int((turn > 0).sum() // 2),
            "mean_excess_bps_day": round(float(ex.mean()) * 1e4, 3),
            "gross_excess_bps_day": round(gross_excess_bps(ret, rf_d, mask), 3),
            "cost_drag_bps_day": round(float(turn.sum()) * cost_bp / len(ret), 3),
            "ann_excess_pct": round(float(ex.mean()) * TD * 100, 3),
            "sharpe_excess": round(float(ex.mean() / sd * np.sqrt(TD)), 3) if sd else 0.0,
            "ci_lb_bps_day": round(lb * 1e4, 3), "ci_ub_bps_day": round(ub * 1e4, 3),
            "halves_bps_day": [round(float(ex[:half].mean()) * 1e4, 3),
                               round(float(ex[half:].mean()) * 1e4, 3)],
            "total_cost_bp": round(float(turn.sum()) * cost_bp, 1)}


def null_pct(ret, rf_d, mask, observed_bps, n_shuffles=1000, seed=11):
    """Same number of held days, placed at random; where does the observed mean rank?"""
    rng = np.random.default_rng(seed)
    k = int(mask.sum())
    out = []
    for _ in range(n_shuffles):
        m = np.zeros(len(ret))
        m[rng.choice(len(ret), k, replace=False)] = 1.0
        ex = m * ret - m * rf_d
        out.append(ex.mean() * 1e4)
    out = np.array(out)
    return {"percentile": round(float((out < observed_bps).mean()) * 100, 1),
            "null_mean_bps": round(float(out.mean()), 3),
            "null_p95_bps": round(float(np.percentile(out, 95)), 3),
            "n_shuffles": n_shuffles}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1993-01-29")
    ap.add_argument("--end", default="2026-11-21")
    ap.add_argument("--out", default="reports/turn_of_month_2026-11-22.json")
    a = ap.parse_args()

    px = download(a.start, a.end)
    idx = px.index
    ret = px["SPY"].pct_change().fillna(0.0).values
    rf_d = (px["^IRX"] / 100.0 / TD).fillna(0.0).values
    print(f"SPY {idx[0].date()} .. {idx[-1].date()}  n={len(idx)}")

    out = {"generated_by": "tools/turn_of_month_check.py",
           "rule": {"universe": "SPY", "signal": "calendar only, no price information",
                    "variants": {"TOM_L_to_3": [0, 1, 2, 3], "L_only": [0],
                                 "L_plus_1_to_3": [1, 2, 3]},
                    "cost_bp_per_unit_turnover": 5.0,
                    "gate": "CI-LB>0 AND both halves>0 AND null percentile>=95"},
           "window": {"start": str(idx[0].date()), "end": str(idx[-1].date())},
           "variants": {}}

    for name, inc in (("TOM_L_to_3", (0, 1, 2, 3)), ("L_only", (0,)), ("L_plus_1_to_3", (1, 2, 3))):
        m = position_mask(idx, inc)
        r5 = run(idx, ret, rf_d, m, 5.0)
        r10 = run(idx, ret, rf_d, m, 10.0)
        # null is GROSS, so it must be compared against the GROSS observed mean
        nul = null_pct(ret, rf_d, m, r5["gross_excess_bps_day"])
        passes = (r5["ci_lb_bps_day"] > 0 and min(r5["halves_bps_day"]) > 0
                  and nul["percentile"] >= 95)
        out["variants"][name] = {"cost5": r5, "cost10": r10, "null": nul,
                                 "passes_all_three_gates": bool(passes)}
        print(f"\n{name}: held {r5['pct_held']}% of days, {r5['trades']} round trips, "
              f"{r5['total_cost_bp']}bp total cost")
        print(f"  excess {r5['mean_excess_bps_day']:+.3f} bp/day "
              f"({r5['ann_excess_pct']:+.2f}%/yr)  Sharpe {r5['sharpe_excess']:+.3f}  "
              f"CI [{r5['ci_lb_bps_day']:+.3f}, {r5['ci_ub_bps_day']:+.3f}]")
        print(f"  gross {r5['gross_excess_bps_day']:+.3f} bp/day, cost drag "
              f"{r5['cost_drag_bps_day']:.3f} bp/day")
        print(f"  halves {r5['halves_bps_day']}  null pct (gross v gross) {nul['percentile']} "
              f"(p95 {nul['null_p95_bps']:+.3f})  @10bp {r10['ann_excess_pct']:+.2f}%/yr")
        print(f"  PASSES ALL THREE GATES: {passes}")

    n_pass = sum(1 for v in out["variants"].values() if v["passes_all_three_gates"])
    out["verdict"] = {"variants_tested": 3, "variants_passing": n_pass,
                      "family_status": ("CANDIDATE" if n_pass else "REFUTED"),
                      "note": "three variants of one calendar rule are NOT three independent "
                              "trials; the family is counted as ONE trial for multiplicity"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n>>> {n_pass}/3 variants pass; family {out['verdict']['family_status']}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()

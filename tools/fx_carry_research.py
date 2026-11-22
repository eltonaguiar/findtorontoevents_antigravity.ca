"""Item 16: FX carry from ACTUAL interest-rate differentials.

Classic carry: at each month-end, rank currencies by their short-term
interest rate, go long the top quintile and short the bottom quintile,
equal weight, against USD, hold one month, rebalance.

Unlike the price-based FX rounds (momentum, mean-reversion) the return here
has two mechanically separate components, modelled explicitly:

    monthly return of ccy i vs USD  =  (S_{t+1}/S_t - 1)  +  (r_i - r_usd)/12

where the first term is spot P&L and the second is the interest carry that a
FX position earns/pays continuously while held (not a per-trade edge).

Spot comes from data/forex_rate_cache/ (daily close, Frankfurter/ECB).
Short rates come from FRED series (saved under /tmp/fxrates/*.csv by the
research run); each series is joined as-of the rebalance date with a
30-day publication lag so a later-published (revised) print cannot leak.
"""
import csv
import json
import math
import os
import statistics as st
import sys
from datetime import date, datetime, timedelta

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX_DIR = os.path.join(BASE, "data", "forex_rate_cache")
RATE_DIR = "/tmp/fxrates"

# currency -> (fred series file, spot pair file where 1 unit ccy in USD is
# obtained, invert?)
CCY_SPEC = {
    "USD": ("DFF.csv", None, False),
    "EUR": ("ECBDFR.csv", "EURUSD.csv", False),
    "GBP": ("IUDSOIA.csv", "GBPUSD.csv", False),
    "JPY": ("IRSTCI01JPM156N.csv", "USDJPY.csv", True),
    "AUD": ("IR3TIB01AUM156N.csv", "AUDUSD.csv", False),
    "CAD": ("IR3TIB01CAM156N.csv", "USDCAD.csv", True),
    "NZD": ("IR3TIB01NZM156N.csv", "NZDUSD.csv", False),
    "CHF": ("IR3TIB01CHM156N.csv", "USDCHF.csv", True),
    "NOK": ("IR3TIB01NOM156N.csv", "USDNOK.csv", True),
    "SEK": ("IR3TIB01SEM156N.csv", "USDSEK.csv", True),
    "DKK": ("IR3TIB01DKM156N.csv", "USDDKK.csv", True),
}
QUANTILE_FRAC = 0.2      # pre-declared: top/bottom quintile
RATE_LAG_DAYS = 30       # pre-declared publication lag
SEED = 20261122
N_BOOT = 10000
N_NULL = 500
COST_GRID_BP = [1, 2, 3, 5, 10]


def load_spot(pair, invert):
    path = os.path.join(FX_DIR, pair)
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                v = float(r["close"])
            except (KeyError, ValueError):
                continue
            if v > 0:
                out[r["date"]] = 1.0 / v if invert else v
    return out


def load_rate(series_file):
    path = os.path.join(RATE_DIR, series_file)
    out = {}
    with open(path) as f:
        rd = csv.reader(f)
        next(rd)
        for row in rd:
            if len(row) < 2 or not row[1] or row[1] in (".", ""):
                continue
            try:
                out[row[0]] = float(row[1]) / 100.0
            except ValueError:
                continue
    return out


def asof(series, day, max_back=400):
    """value of series at the last date <= day."""
    for k in range(max_back):
        d = (date.fromisoformat(day) - timedelta(days=k)).isoformat()
        if d in series:
            return series[d], d
    return None, None


def month_ends(days):
    ds = sorted(days)
    out = []
    for i, d in enumerate(ds[:-1]):
        if ds[i + 1][:7] != d[:7]:
            out.append(d)
    out.append(ds[-1])
    return out


def maxdd(equity):
    peak, dd = -1e9, 0.0
    for v in equity:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    return dd


def skew(x):
    a = np.asarray(x, float)
    n = len(a)
    m = a.mean()
    s = a.std(ddof=0)
    return float(((a - m) ** 3).mean() / s ** 3) if s > 0 else 0.0


def main():
    spot = {}
    for c, (_, pair, inv) in CCY_SPEC.items():
        if pair:
            s = load_spot(pair, inv)
            spot[c] = s
            print(f"spot {c}: {pair} invert={inv} {min(s)}..{max(s)} n={len(s)}")
    rates = {}
    for c, (sf, _, _) in CCY_SPEC.items():
        rates[c] = load_rate(sf)
    usd_days = None
    for c in spot:
        usd_days = set(spot[c]) if usd_days is None else (usd_days & set(spot[c]))
    days = sorted(usd_days)
    print(f"common spot days: {len(days)} {days[0]}..{days[-1]}")

    mes = month_ends(days)
    me_idx = {d: i for i, d in enumerate(days)}
    rows = []
    for k in range(0, len(mes) - 1):
        d0, d1 = mes[k], mes[k + 1]
        if (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days < 20:
            continue
        yields = {}
        for c in spot:
            r, rd = asof(rates[c], (date.fromisoformat(d0) - timedelta(days=RATE_LAG_DAYS)).isoformat())
            if r is not None:
                yields[c] = r
        if len(yields) < 6:
            continue
        rets = {c: spot[c][d1] / spot[c][d0] - 1 for c in spot}
        rows.append({"d0": d0, "d1": d1, "yields": yields, "spot_ret": rets})
    print(f"monthly observations: {len(rows)}  {rows[0]['d0']}..{rows[-1]['d1']}")

    n_long = max(1, int(round(len(CCY_SPEC) * QUANTILE_FRAC)))

    def one_month(row, cost_bp=0.0, prev=None):
        ys = row["yields"]
        order = sorted(ys, key=ys.get)
        shorts, longs = order[:n_long], order[-n_long:]
        carry = sum(ys[c] for c in longs) / n_long - sum(ys[c] for c in shorts) / n_long
        fx = sum(row["spot_ret"][c] for c in longs) / n_long - sum(row["spot_ret"][c] for c in shorts) / n_long
        gross = fx + carry / 12.0
        # turnover cost: notional traded / 2 legs; positions equal-weight
        turn = 0.0
        if prev is not None:
            pl, ps = prev
            turn = (len(set(longs) - set(pl)) + len(set(shorts) - set(ps))) / n_long
        net = gross - turn * cost_bp * 1e-4
        return net, gross, fx, carry, longs, shorts, turn

    # main run at zero cost
    per = []
    prev = None
    for row in rows:
        net, gross, fx, carry, L, S, turn = one_month(row, 0.0, prev)
        per.append({"d1": row["d1"], "gross": gross, "fx": fx, "carry": carry,
                    "long": L, "short": S, "turnover": turn})
        prev = (L, S)
    mr = [p["gross"] for p in per]
    eq = [1.0]
    for r in mr:
        eq.append(eq[-1] * (1 + r))
    yrs = len(mr) / 12.0
    cagr = eq[-1] ** (1 / yrs) - 1
    vol = st.stdev(mr) * math.sqrt(12)
    rf = 0.0432
    sharpe = (cagr - rf) / vol
    worst = min(per, key=lambda p: p["gross"])
    print(f"\nGROSS carry: months={len(mr)} cagr={cagr:.4%} vol={vol:.4%} sharpe_vs_rf={sharpe:.3f}")
    print(f"  mean monthly={st.mean(mr):.5%} median={st.median(mr):.5%} skew={skew(mr):.3f}")
    print(f"  worst month={worst['gross']:.4%} on {worst['d1']} (fx part {worst['fx']:.4%}, carry {worst['carry']/12:.4%})")
    print(f"  maxDD={maxdd(eq):.4%}  %pos months={sum(1 for r in mr if r>0)/len(mr):.1%}")
    print(f"  mean carry component annualised={st.mean([p['carry'] for p in per]):.4%}  mean fx component annualised={st.mean([p['fx'] for p in per])*12:.4%}")

    # cost sweep
    sweep = {}
    for cb in [0] + COST_GRID_BP:
        prev = None
        rs = []
        for row in rows:
            net, gross, fx, carry, L, S, turn = one_month(row, cb, prev)
            rs.append(net)
            prev = (L, S)
        e = [1.0]
        for r in rs:
            e.append(e[-1] * (1 + r))
        c = e[-1] ** (1 / yrs) - 1
        v = st.stdev(rs) * math.sqrt(12)
        sweep[cb] = {"cagr": c, "vol": v, "sharpe": (c - rf) / v, "maxdd": maxdd(e), "skew": skew(rs)}
        print(f"cost {cb}bp/leg: cagr={c:.4%} sharpe={sweep[cb]['sharpe']:.3f} maxDD={sweep[cb]['maxdd']:.3%} skew={sweep[cb]['skew']:.3f}")

    # break-even cost: cost at which CAGR == 0 (linear in cost)
    c0, c10 = sweep[0]["cagr"], sweep[max(COST_GRID_BP)]["cagr"]
    breakeven = 10 * c0 / (c0 - c10) if c0 > c10 else float("inf")
    print(f"break-even cost (CAGR=0): {breakeven:.2f} bp/unit turnover")

    # SPY same window
    spy = {}
    with open(os.path.join(BASE, "data", "cache", "asset_class_review", "SPY_5y.csv")) as f:
        for r in csv.DictReader(f):
            spy[r["Date"]] = float(r["Close"])
    sd = sorted(spy)
    w0, w1 = rows[0]["d0"], rows[-1]["d1"]
    s0 = min([d for d in sd if d >= w0]); s1 = max([d for d in sd if d <= w1])
    spy_cagr = (spy[s1] / spy[s0]) ** (1 / yrs) - 1
    print(f"SPY buy&hold same window {s0}..{s1}: cagr={spy_cagr:.4%}")

    # item 19: bootstrap CI on excess CAGR (monthly resample, seeded)
    rng = np.random.default_rng(SEED)
    diff = cagr - spy_cagr
    boots = []
    a = np.asarray(mr)
    for _ in range(N_BOOT):
        s = a[rng.integers(0, len(a), len(a))]
        e = np.prod(1 + s)
        boots.append(e ** (12 / len(a)) - 1 - spy_cagr)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"excess CAGR (carry - SPY) = {diff:.4%}  95% CI [{lo:.4%}, {hi:.4%}]")

    # item 48: random-rank null, same long/short count, 500 shuffles
    null = []
    for k in range(N_NULL):
        rr = np.random.default_rng(SEED + k)
        rs = []
        for row in rows:
            order = list(row["yields"])
            rr.shuffle(order)
            longs, shorts = order[-n_long:], order[:n_long]
            fx = sum(row["spot_ret"][c] for c in longs) / n_long - sum(row["spot_ret"][c] for c in shorts) / n_long
            yl = sum(row["yields"][c] for c in longs) / n_long
            ys = sum(row["yields"][c] for c in shorts) / n_long
            rs.append(fx + (yl - ys) / 12.0)
        v = st.stdev(rs) * math.sqrt(12)
        e = np.prod(1 + np.asarray(rs))
        c = e ** (12 / len(rs)) - 1
        null.append((c - rf) / v)
    pct = float((np.array(null) < sharpe).mean() * 100)
    print(f"null Sharpe dist: mean={np.mean(null):.3f} p5={np.percentile(null,5):.3f} p95={np.percentile(null,95):.3f}; observed {sharpe:.3f} => percentile {pct:.1f}")

    out = {
        "item": 16, "strategy": "fx_carry_quintile",
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "data": {
            "spot": "data/forex_rate_cache/ (daily close)",
            "spot_range": [days[0], days[-1]],
            "rates_fred": {c: CCY_SPEC[c][0] for c in CCY_SPEC},
            "currencies": list(CCY_SPEC),
            "months": len(rows), "window": [rows[0]["d0"], rows[-1]["d1"]],
        },
        "rule": {"quantile_frac": QUANTILE_FRAC, "n_long": n_long, "n_short": n_long,
                 "rebalance": "monthly", "weight": "equal", "rate_lag_days": RATE_LAG_DAYS},
        "gross": {"cagr": cagr, "vol": vol, "sharpe_vs_rf": sharpe, "rf": rf,
                  "mean_month": st.mean(mr), "median_month": st.median(mr),
                  "skew": skew(mr), "worst_month": worst["gross"], "worst_month_date": worst["d1"],
                  "worst_month_fx": worst["fx"], "worst_month_carry": worst["carry"] / 12,
                  "maxdd": maxdd(eq), "pct_positive_months": sum(1 for r in mr if r > 0) / len(mr),
                  "carry_component_annual": st.mean([p["carry"] for p in per]),
                  "fx_component_annual": st.mean([p["fx"] for p in per]) * 12},
        "cost_sweep": {str(k): v for k, v in sweep.items()},
        "breakeven_cost_bp": breakeven,
        "spy_same_window": {"cagr": spy_cagr, "window": [s0, s1]},
        "item19_excess_cagr": {"mean": diff, "ci95": [float(lo), float(hi)], "n_boot": N_BOOT, "seed": SEED},
        "item48_null_percentile": {"percentile": pct, "n_shuffles": N_NULL,
                                   "null_mean_sharpe": float(np.mean(null)),
                                   "null_p5": float(np.percentile(null, 5)),
                                   "null_p95": float(np.percentile(null, 95))},
        "monthly": per,
    }
    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    with open(os.path.join(BASE, "reports", "fx_carry_20261122.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""EDGE-5 — SPY overnight vs intraday decomposition (documented anomaly, honest test).

Hypothesis H-OVERNIGHT-SPY (pre-registered):
  A large, persistent share of SPY's total return historically accrues in the
  *overnight* window (prior close -> open), while the intraday window
  (open -> close) is ~flat. Strategy A: long overnight only (buy close, sell open),
  flat intraday. Strategy B: long intraday only. Compare to buy-and-hold.

Honest rules:
  - next-bar-open fills are intrinsic here (we trade the open/close prints).
  - cost charged per round trip on the traded leg (ETF ~4bp RT baseline; ladder given).
  - t-stat, block-bootstrap CI, permutation p, and an OOS split (first vs second half).
  - report the 1993-2008 vs 2009+ sub-periods (the anomaly is widely reported to
    have decayed post-2008; this checks that honestly).

Read-only yfinance. No keys. Not investment advice.
"""
import json, hashlib, datetime
import numpy as np

TICKER = "SPY"
COST_RT_BP = 4.0
RNG = np.random.default_rng(20261127)


def load():
    import yfinance as yf
    df = yf.download(TICKER, start="1993-01-01", progress=False, auto_adjust=False)
    if df is None or len(df) == 0:
        raise SystemExit("no data")
    # flatten possible multiindex
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = [c[0] for c in df.columns]
    df = df.dropna(subset=["Open", "Close"])
    o = df["Open"].to_numpy(float)
    c = df["Close"].to_numpy(float)
    idx = df.index
    return idx, o, c


def bt(o, c, mode, cost_rt_bp):
    """mode: 'overnight' (c[t-1]->o[t]) or 'intraday' (o[t]->c[t]) or 'hold'."""
    rets = []
    for t in range(1, len(c)):
        if mode == "overnight":
            r = o[t]/c[t-1] - 1
            net = r - cost_rt_bp/1e4          # one round trip per day
        elif mode == "intraday":
            r = c[t]/o[t] - 1
            net = r - cost_rt_bp/1e4
        else:  # buy and hold: close to close, cost amortised -> charge once
            r = c[t]/c[t-1] - 1
            net = r
        rets.append(net)
    return np.array(rets, float)


def stats(a, periods_per_year):
    a = a[np.isfinite(a)]
    n = len(a)
    mean, sd = float(a.mean()), float(a.std(ddof=1))
    t = mean/(sd/np.sqrt(n)) if sd > 0 else 0.0
    L = max(2, int(round(n ** (1/3))))
    boots = []
    for _ in range(3000):
        idx = []
        while len(idx) < n:
            s = RNG.integers(0, n)
            idx.extend((s + np.arange(L)) % n)
        idx = np.array(idx[:n])
        boots.append(a[idx].mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    signs = RNG.choice([-1, 1], size=(3000, n))
    p = float(np.mean(np.abs((signs*a).mean(axis=1)) >= abs(mean)))
    return {"n": n, "mean_bp_per_day": round(mean*1e4, 3),
            "ann_pct": round(((1+mean)**periods_per_year - 1)*100, 2) if abs(mean) < 1 else None,
            "t": round(t, 2), "sharpe_ann": round(mean/(sd+1e-12)*np.sqrt(periods_per_year), 3),
            "ci95_lo_bp": round(float(lo)*1e4, 3), "ci95_hi_bp": round(float(hi)*1e4, 3),
            "p_perm": round(p, 4), "win": round(float((a > 0).mean()), 3)}


def main():
    idx, o, c = load()
    out = {"round": "EDGE-5", "hypothesis": "H-OVERNIGHT-SPY",
           "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "ticker": TICKER, "n_days": len(c),
           "span": [str(idx[0].date()), str(idx[-1].date())],
           "cost_rt_bp": COST_RT_BP}
    per_year = 252
    on = bt(o, c, "overnight", COST_RT_BP)
    intr = bt(o, c, "intraday", COST_RT_BP)
    bh = bt(o, c, "hold", 0.0)
    out["full"] = {"overnight": stats(on, per_year),
                   "intraday": stats(intr, per_year),
                   "buy_hold_close_to_close": stats(bh, per_year)}
    # sub-period split by index date
    def split_by_year(start, end):
        mask = np.array([(d.year >= start and d.year <= end) for d in idx[1:]])
        return {"overnight": stats(on[mask], per_year),
                "intraday": stats(intr[mask], per_year),
                "buy_hold": stats(bh[mask], per_year)}
    out["period_1993_2008"] = split_by_year(1993, 2008)
    out["period_2009_2026"] = split_by_year(2009, 2026)
    # OOS halves on overnight
    h = len(on)//2
    out["overnight_oos_halves"] = {"first": stats(on[:h], per_year),
                                   "second": stats(on[h:], per_year)}
    # cost ladder on overnight
    ladder = {}
    for cb in (0.0, 1.0, 4.0, 10.0, 20.0):
        st = stats(bt(o, c, "overnight", cb), per_year)
        ladder[f"{cb}bp_rt"] = {k: st[k] for k in ("mean_bp_per_day", "t", "ci95_lo_bp", "sharpe_ann")}
    out["overnight_cost_ladder"] = ladder
    with open(__file__, "rb") as fh:
        out["artifact_sha"] = hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out, indent=2))
    with open(__file__.replace(".py", ".json"), "w") as fh:
        json.dump(out, fh, indent=2)


if __name__ == "__main__":
    main()
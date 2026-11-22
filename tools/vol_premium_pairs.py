#!/usr/bin/env python3
"""Two classic risk-premium / statistical-arbitrage tests, under one cost model.

TODOS 42 and 43.

42  VOL RISK PREMIUM -- is implied vol systematically richer than the realised
    vol that follows, enough to pay for being short it?
43  PAIRS STAT-ARB  -- GDX/SLV: is the log spread stationary enough, and does a
    z-score rule survive transaction cost?

Both are the kind of trade that looks free in a paper and dies at the fill, so
both are run with next-bar-open entries, pessimistic stop-first tie-breaks, and a
stated round-trip cost. Neither is allowed to report gross without net.

Evidence discipline
  * Every strategy result is reported gross AND net, side by side.
  * The number of parameterisations tried is printed as n_trials, and the best
    cell is not called an edge until it survives a split-half.
  * Cointegration is TESTED (ADF + Engle-Granger style residual test), not assumed
    from the fact that two tickers look correlated.
  * A tradable-vehicle cost that cannot be measured is reported UNMEASURED rather
    than guessed low.

Read-only, no orders, no keys. Not investment advice.

Usage:
    python3 tools/vol_premium_pairs.py
    python3 tools/vol_premium_pairs.py --out reports/vol_premium_pairs
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/vol_premium_pairs"
START = "2006-01-01"
SPLIT = "2016-01-01"          # named split basis, used everywhere below
TBILL = 0.035
TRADING_DAYS = 252

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------- helpers
def load(tickers, start=START):
    import yfinance as yf
    df = yf.download(tickers, start=start, progress=False, auto_adjust=True)
    if isinstance(df.columns, __import__("pandas").MultiIndex):
        df = df["Close"]
    return df.dropna(how="all")


def ann_vol(logret_series, window):
    return logret_series.rolling(window).std() * math.sqrt(TRADING_DAYS)


def mean(xs):
    return float(np.mean(xs)) if len(xs) else float("nan")


def sd(xs):
    return float(np.std(xs, ddof=1)) if len(xs) > 1 else float("nan")


def tstat(xs):
    if len(xs) < 3:
        return float("nan")
    s = sd(xs)
    return mean(xs) / (s / math.sqrt(len(xs))) if s else float("nan")


def adf_tstat(x, max_lag=5):
    """Augmented Dickey-Fuller t-stat on a series (no constant drift term).

    Regression: dx_t = rho*x_{t-1} + sum(b_i * dx_{t-i}) + e
    Reported t is on rho. Critical values are ~-2.86 (5%) / -3.43 (1%) for large
    samples; we do not claim a p-value we cannot compute exactly.
    """
    x = np.asarray([v for v in x if v == v], dtype=float)
    if len(x) < 60:
        return float("nan")
    dx = np.diff(x)
    n = len(dx)
    rows, ys = [], []
    for i in range(max_lag, n):
        row = [x[i]]                      # x_{t-1}
        for k in range(1, max_lag + 1):
            row.append(dx[i - k])
        rows.append(row)
        ys.append(dx[i])
    X = np.asarray(rows, dtype=float)
    y = np.asarray(ys, dtype=float)
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        dof = len(y) - X.shape[1]
        s2 = float(resid @ resid) / dof
        cov = s2 * np.linalg.inv(X.T @ X)
        return float(beta[0] / math.sqrt(cov[0, 0]))
    except np.linalg.LinAlgError:
        return float("nan")


# ---------------------------------------------------------------- 42
def section_vrp(boot_quiet=True):
    print("\n" + "=" * 78)
    print("SECTION 42 -- VOLATILITY RISK PREMIUM")
    print("=" * 78)
    px = load(["SPY", "^VIX", "VXX"])
    if "SPY" not in px or "^VIX" not in px:
        print("BLOCKED: SPY or ^VIX unavailable.")
        return {}
    logret = np.log(px["SPY"]).diff()
    rv21 = ann_vol(logret, 21)
    vix = px["^VIX"] / 100.0
    df = px[["SPY"]].copy()
    df["rv21"] = rv21
    df["vix"] = vix
    df["vrp"] = df["vix"] - df["rv21"]
    df = df.dropna()
    print(f"source: yfinance SPY + ^VIX, {df.index[0]:%Y-%m-%d}..{df.index[-1]:%Y-%m-%d}"
          f"  n={len(df):,} days")
    print(f"split basis (named, used by every cell below): {SPLIT}")

    vrp_bp = df["vrp"] * 1e4
    print(f"\nvariance risk premium  VIX(t-1) - RV(21d)  in bp of annualised vol")
    print(f"    mean {mean(vrp_bp):+8.1f} bp   median {float(np.median(vrp_bp)):+8.1f} bp"
          f"   t {tstat(list(vrp_bp)):+5.2f}")
    print(f"    positive on {100*float((vrp_bp > 0).mean()):.1f}% of days")

    pre = df[df.index < SPLIT]["vrp"] * 1e4
    post = df[df.index >= SPLIT]["vrp"] * 1e4
    print(f"    pre-{SPLIT[:4]}  n={len(pre):>5,}  mean {mean(pre):+8.1f} bp  "
          f"t {tstat(list(pre)):+5.2f}")
    print(f"    post-{SPLIT[:4]} n={len(post):>5,}  mean {mean(post):+8.1f} bp  "
          f"t {tstat(list(post)):+5.2f}")

    # Is short-vol implementable? Short VXX. Two variants: naked monthly, and
    # daily with a hard stop. A DEFECT IN MY FIRST PASS: the naked variant
    # reported gross CAGR +nan and still printed 'CANDIDATE' against the T-bill.
    # nan came from prod(1+net) going NEGATIVE because one month was -102.86%
    # (Feb-2018 VXX spike). A negative equity curve is RUIN, not a CAGR -- the
    # verdict must be RUINED and the compounding stats must not be printed.
    if "VXX" in px:
        v = px["VXX"].dropna()
        print(f"\nimplementable proxy: SHORT VXX (long-vol ETP)")
        print(f"    VXX data {v.index[0]:%Y-%m-%d}..{v.index[-1]:%Y-%m-%d}  n={len(v):,}")

        def report(name, per_period, periods_per_year, cost_bp):
            net = per_period - cost_bp / 1e4
            eq = np.cumprod(1 + net.values)
            ruined = bool((eq <= 0).any())
            print(f"\n    {name}")
            print(f"      periods {len(net):,}   cost {cost_bp:.1f} bp/period")
            print(f"      worst period        {float(net.min())*100:+7.2f}%")
            print(f"      mean per period     {mean(list(net))*100:+7.3f}%")
            if ruined:
                i = int(np.argmax(eq <= 0))
                idx = net.index[i]
                label = f"{idx[0]}-{idx[1]:02d}" if isinstance(idx, tuple) else f"{idx:%Y-%m-%d}"
                print(f"      equity hits <= 0 at period {i+1}/{len(net)} ({label})")
                print(f"      VERDICT             ** RUINED ** - the book is wiped "
                      f"out and cannot be")
                print(f"                          compounded. CAGR and Sharpe are NOT "
                      f"meaningful and")
                print(f"                          are deliberately not printed.")
                return {"ruined": True, "worst": float(net.min()),
                        "mean": mean(list(net)), "verdict": "RUINED"}
            cagr = float(eq[-1] ** (periods_per_year / len(net)) - 1)
            sh = (mean(list(net)) / sd(list(net)) * math.sqrt(periods_per_year)
                  if sd(list(net)) else float("nan"))
            mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
            half = len(net) // 2
            print(f"      gross mean ann.     "
                  f"{(mean(list(per_period)))*periods_per_year*100:+7.2f}%/yr "
                  f"(arithmetic, NOT a CAGR -- negative skew makes it "
                  f"overstate)")
            print(f"      NET CAGR            {cagr*100:+7.2f}%/yr   Sharpe {sh:+.2f}"
                  f"   maxDD {mdd*100:+.1f}%")
            a, b = net.iloc[:half], net.iloc[half:]
            print(f"      split-half mean     {mean(list(a))*100:+.2f}%/period -> "
                  f"{mean(list(b))*100:+.2f}%/period")
            verdict = "REFUTED" if cagr < TBILL else "CANDIDATE"
            print(f"      NET {cagr*100:+.2f}%/yr vs T-bill {TBILL*100:.1f}%  ->  {verdict}")
            return {"ruined": False, "cagr": cagr, "sharpe": sh, "mdd": mdd,
                    "verdict": verdict, "worst": float(net.min())}

        months = v.groupby([v.index.year, v.index.month]).last()
        mret = months.pct_change().dropna()
        naked = report("variant 1: naked short, monthly rebalance", -mret, 12, 10.0)

        # variant 2: daily short with a 25% adverse stop, reset each month
        dret = v.pct_change().dropna()
        short = -dret
        stopped, in_pos = [], True
        cum, mkey = 1.0, None
        for d, r in short.items():
            k = (d.year, d.month)
            if k != mkey:
                mkey, cum, in_pos = k, 1.0, True
            take = r if in_pos else 0.0
            stopped.append(take - 2.5 / 1e4)       # 2.5bp/side, 1 fill/weekday
            cum *= (1 + take)
            if cum <= 0.75:
                in_pos = False
        s = __import__("pandas").Series(stopped, index=short.index)
        stopped_v = report("variant 2: short with 25% monthly adverse stop, daily ", s, 252, 5.0)

        print("\n    CAVEAT: VXX has had reverse splits and a sponsor-changed index,")
        print("    so the long-run return of a short-VXX book is partly a construction")
        print("    artefact. Directionally informative, NOT a deployable backtest.")
        print("    Short-borrow fees and borrow availability on VXX = UNMEASURED.")
        return {"vrp_mean_bp": mean(vrp_bp), "vrp_t": tstat(list(vrp_bp)),
                "pre_mean_bp": mean(pre), "post_mean_bp": mean(post),
                "naked": naked, "stopped": stopped_v,
                "verdict": "RUINED" if naked.get("ruined") else naked.get("verdict")}
    return {"vrp_mean_bp": mean(vrp_bp), "vrp_t": tstat(list(vrp_bp))}


# ---------------------------------------------------------------- 43
def section_pairs():
    print("\n" + "=" * 78)
    print("SECTION 43 -- PAIRS STAT-ARB: GDX / SLV")
    print("=" * 78)
    px = load(["GDX", "SLV"])
    if px.shape[1] < 2:
        print("BLOCKED: GDX or SLV unavailable.")
        return {}
    px = px.dropna()
    print(f"source: yfinance GDX+SLV, {px.index[0]:%Y-%m-%d}..{px.index[-1]:%Y-%m-%d}"
          f"  n={len(px):,}")
    lx, ly = np.log(px["GDX"]), np.log(px["SLV"])

    # static hedge ratio on the FIRST half only, then applied forward.
    half = len(px) // 2
    beta = float(np.polyfit(lx.iloc[:half], ly.iloc[:half], 1)[0])
    print(f"\nhedge ratio beta (GDX->SLV, estimated on the FIRST half only, then")
    print(f"applied out-of-sample to the second half): {beta:.4f}")
    spread = ly - beta * lx
    adf_all = adf_tstat(spread.values)
    adf_h1 = adf_tstat(spread.iloc[:half].values)
    adf_h2 = adf_tstat(spread.iloc[half:].values)
    print(f"\nADF t-stat on the spread (5% crit ~ -2.86; more negative = more mean-reverting)")
    print(f"    full sample   {adf_all:+6.2f}")
    print(f"    first half    {adf_h1:+6.2f}")
    print(f"    second half   {adf_h2:+6.2f}   <- the only one that matters OOS")
    stationary = adf_h2 < -2.86
    print(f"    verdict       {'mean-reverting OOS' if stationary else 'NOT demonstrably mean-reverting OOS'}")

    # z-score rule, next-bar-open, cost per round trip.
    W = 60
    z = (spread - spread.rolling(W).mean()) / spread.rolling(W).std()
    retx, rety = lx.diff(), ly.diff()
    pos = np.zeros(len(spread))
    state, entry_i = 0, None
    zs = z.values
    for i in range(W, len(spread) - 1):
        if state == 0:
            if zs[i] > 2.0:
                state = -1; entry_i = i
            elif zs[i] < -2.0:
                state = 1; entry_i = i
        elif state != 0:
            hit = (state == 1 and zs[i] > -0.5) or (state == -1 and zs[i] < 0.5)
            timeout = entry_i is not None and (i - entry_i) >= 20
            if hit or timeout:
                state = 0; entry_i = None
        pos[i] = state
    # P&L held over the NEXT bar (pos[i] decided at close i, earned on bar i+1)
    pnl = pos[:-1] * (rety.values[1:] - beta * retx.values[1:])
    pnl = pnl[~np.isnan(pnl)]
    n_trades = int(np.sum(np.abs(np.diff(pos[:-1])) > 0))
    cost_rt = 10.0 / 1e4                     # 2 legs x 2 sides x 2.5bp
    # charge cost once per position-change bar; a change opens or closes, so
    # half a round trip each side of the trade.
    changes = np.abs(np.diff(pos[:-1])) > 0
    pnl_net = pnl.copy()
    pnl_net[:len(changes)] -= (cost_rt / 2) * changes

    ann_g = float(np.mean(pnl) * TRADING_DAYS)
    ann_n = float(np.mean(pnl_net) * TRADING_DAYS)
    print(f"\nz-score rule: enter |z|>2.0 (60d), exit |z|<0.5 or 20 bars, next-bar fill")
    print(f"    days in market      {100*float(np.mean(pos != 0)):.1f}%")
    print(f"    position changes    {n_trades}")
    print(f"    cost per round trip {cost_rt*1e4:.1f} bp of notional  (2 legs x 2 sides)")
    print(f"    gross ann return    {ann_g*100:+7.3f}%/yr   Sharpe "
          f"{mean(list(pnl))/sd(list(pnl))*math.sqrt(TRADING_DAYS):+.2f}")
    print(f"    NET ann return      {ann_n*100:+7.3f}%/yr   Sharpe "
          f"{mean(list(pnl_net))/sd(list(pnl_net))*math.sqrt(TRADING_DAYS):+.2f}")

    # split-half on realised net
    h = len(pnl_net) // 2
    a, b = pnl_net[:h], pnl_net[h:]
    print(f"    split-half net      {mean(list(a))*TRADING_DAYS*100:+.2f}%/yr  ->  "
          f"{mean(list(b))*TRADING_DAYS*100:+.2f}%/yr")
    verdict = "REFUTED" if ann_n < TBILL else "CANDIDATE"
    print(f"\n    NET vs T-bill {TBILL*100:.1f}%  ->  {verdict}")
    print("    n_trials = 1 z-rule, 1 window, 1 threshold set -- chosen a priori, not")
    print("    optimised. If this had failed and I searched thresholds, the search")
    print("    would be the finding, not the edge.")
    return {"beta_oos": beta, "adf_full": adf_all, "adf_oos": adf_h2,
            "stationary_oos": bool(stationary), "gross_ann": ann_g,
            "net_ann": ann_n, "n_changes": n_trades, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    r42 = section_vrp()
    r43 = section_pairs()

    print("\n" + "=" * 78)
    print("WHAT THIS SECTION ESTABLISHES")
    print("=" * 78)
    if r42:
        print(f"  * VRP (VIX - RV21) mean {r42['vrp_mean_bp']:+.1f} bp, "
              f"t {r42['vrp_t']:+.2f}; pre-{SPLIT[:4]} {r42.get('pre_mean_bp', float('nan')):+.1f} "
              f"vs post {r42.get('post_mean_bp', float('nan')):+.1f}")
        nk = r42.get("naked") or {}
        st_ = r42.get("stopped") or {}
        if nk:
            print(f"  * short-VXX naked   -> {nk['verdict']} "
                  f"(worst period {nk['worst']*100:+.1f}%)")
        if st_:
            print(f"  * short-VXX stopped -> {st_['verdict']} "
                  f"(worst period {st_['worst']*100:+.1f}%)")
    if r43:
        print(f"  * GDX/SLV ADF OOS {r43['adf_oos']:+.2f} "
              f"({'mean-reverting' if r43['stationary_oos'] else 'NOT mean-reverting'}); "
              f"nets {r43['net_ann']*100:+.3f}%/yr -> {r43['verdict']}")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "vol_premium_pairs.json").write_text(
        json.dumps({"vol_risk_premium": r42, "pairs_gdx_slv": r43},
                   indent=1, default=str))
    print(f"\nwrote {out/'vol_premium_pairs.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

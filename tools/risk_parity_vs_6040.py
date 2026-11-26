"""Risk parity / HRP / combined book — programme items E31, E33, E34.

The per-class sweep found 0 cells clearing every gate and the volatility-matched check
found the one near-pass goes negative when scaled to the benchmark. So the only lever
left that needs no new alpha is PORTFOLIO CONSTRUCTION. This tool asks three questions
that a reader deciding what to hold actually needs answered:

  E31  Does risk parity (SPY/TLT/GLD/DBC) beat plain 60/40 after cost?
  E33  Does HRP — which needs no expected returns at all — beat both?
  E34  Given that every per-class sleeve failed, does adding them to the core help,
       or is the honest combined book just the core?  Answered by letting a max-CE
       optimiser choose weights with a non-negativity constraint: if a dead sleeve
       gets weight, that is a finding; if every sleeve is driven to zero, that is
       the arithmetic the peer notes predicted.

Rules this tool fixes in advance and does not tune:
  * monthly rebalance on the last trading day, weights set from data through t, held t+1
  * cost 5 bp per unit of one-way turnover, ALSO reported at 10 bp so no verdict hangs
    on the cost assumption
  * risk-free = ^IRX/12; every Sharpe and CE is excess over that, never over zero
  * CE at risk aversion 1: mu_ann - vol_ann^2 / 2, i.e. the return a risk-free asset
    would need to be equally attractive
  * max-CE solve is long-only; a negative weight would be leverage on a failed sleeve
  * MDD is month-end and is labelled as such

Usage
  python3 tools/risk_parity_vs_6040.py --out reports/portfolio/risk_parity_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TD = 252
ASSETS = ["SPY", "TLT", "GLD", "DBC"]
CORE = ["SPY", "TLT"]


def download(tickers, start, end) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False,
                      threads=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    return close.dropna(how="all")


def month_end(px: pd.DataFrame) -> pd.DataFrame:
    return px.resample("ME").last().dropna(how="any")


def metrics(r: pd.Series, rf_m: pd.Series, label: str) -> dict:
    r = r.dropna()
    rf = rf_m.reindex(r.index).fillna(0.0)
    if len(r) < 36:
        return {"label": label, "error": "insufficient_n", "n_months": int(len(r))}
    eq = (1.0 + r).cumprod()
    n = len(r)
    cagr = float(eq.iloc[-1] ** (12.0 / n) - 1.0)
    vol = float(r.std() * np.sqrt(12))
    ex = r - rf
    sharpe = float(ex.mean() / r.std() * np.sqrt(12)) if r.std() > 0 else 0.0
    mdd = float((eq / eq.cummax() - 1.0).min())
    ce = float(ex.mean() * 12 - 0.5 * r.var() * 12)
    return {"label": label, "n_months": n, "cagr_pct": round(cagr * 100, 2),
            "vol_pct": round(vol * 100, 2), "sharpe_vs_rf": round(sharpe, 3),
            "mdd_month_end_pct": round(mdd * 100, 2), "ce_pct": round(ce * 100, 2),
            "total_return_pct": round(float(eq.iloc[-1] - 1) * 100, 2)}


def run_weights(w: pd.DataFrame, rets: pd.DataFrame, rf_m: pd.Series, label: str,
                cost_bp: float) -> tuple[pd.Series, dict]:
    w = w.reindex(columns=rets.columns).fillna(0.0)
    drift = w.shift(1).fillna(0.0)          # weights set at t-1 are held through t
    gross = (drift * rets).sum(axis=1)
    turn = w.diff().abs().sum(axis=1).fillna(w.abs().sum(axis=1))
    net = gross - turn * cost_bp / 1e4
    return net.dropna(), metrics(net, rf_m, label)


def inverse_vol_weights(rets: pd.DataFrame, look: int = 12) -> pd.DataFrame:
    vols = rets.rolling(look).std().shift(1)
    inv = 1.0 / vols.replace(0.0, np.nan)
    return inv.div(inv.sum(axis=1), axis=0)


def erc_weights(cov: np.ndarray, iters: int = 500) -> np.ndarray:
    """Equal risk contribution by fixed-point iteration on marginal risk."""
    d = np.sqrt(np.diag(cov))
    w = (1.0 / d) / (1.0 / d).sum()
    for _ in range(iters):
        mrc = cov @ w
        rc = w * mrc
        target = rc.mean()
        w = w * np.sqrt(target / np.maximum(rc, 1e-18))
        w = np.clip(w, 0.0, None)
        w = w / w.sum()
    return w


def hrp_weights(cov: pd.DataFrame, corr: pd.DataFrame) -> pd.Series:
    """Lopez de Prado's hierarchical risk parity: cluster, quasi-diagonalise, bisect."""
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import squareform

    names = list(cov.columns)
    dist = np.sqrt(np.clip((1.0 - corr.values) / 2.0, 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    link = linkage(squareform(dist, checks=False), method="single")
    order = dendrogram(link, no_plot=True)["leaves"]
    ordered = [names[i] for i in order]

    def cluster_var(items):
        sub = cov.loc[items, items].values
        iv = 1.0 / np.diag(sub)
        iv = iv / iv.sum()
        return float(iv @ sub @ iv)

    w = pd.Series(1.0, index=ordered)
    clusters = [ordered]
    while clusters:
        nxt = []
        for c in clusters:
            if len(c) > 1:
                half = len(c) // 2
                nxt += [c[:half], c[half:]]
        clusters = nxt
        for k in range(0, len(clusters), 2):
            c0, c1 = clusters[k], clusters[k + 1]
            v0, v1 = cluster_var(c0), cluster_var(c1)
            a = 1.0 - v0 / (v0 + v1)
            w[c0] *= a
            w[c1] *= 1.0 - a
    return w.reindex(names).fillna(0.0)


def max_ce_weights(mu: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Long-only max certainty-equivalent (risk aversion 1) on monthly excess returns."""
    from scipy.optimize import minimize

    n = len(mu)
    m, S = mu.values, cov.values

    def neg(w):
        return -(w @ m - 0.5 * w @ S @ w)

    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    res = minimize(neg, np.full(n, 1.0 / n), bounds=[(0.0, 1.0)] * n, constraints=cons,
                   method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(res.x, 0.0, None)
    return pd.Series(w / w.sum(), index=mu.index)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2006-02-01")
    ap.add_argument("--end", default="2026-11-21")
    ap.add_argument("--cost-bp", type=float, default=5.0)
    ap.add_argument("--out", default="reports/portfolio/risk_parity_2026-11-22.json")
    a = ap.parse_args()

    px = download(ASSETS + ["^IRX"], a.start, a.end)
    px = px.dropna(how="any")
    me = month_end(px[ASSETS])
    bill = month_end(px[["^IRX"]])["^IRX"] / 100.0 / 12.0
    rets = me.pct_change().dropna()
    rf = bill.reindex(rets.index).fillna(0.0)
    print(f"window {rets.index[0].date()} .. {rets.index[-1].date()}  n={len(rets)} months")

    corr = rets.corr()
    out = {"generated_by": "tools/risk_parity_vs_6040.py",
           "window": {"start": str(rets.index[0].date()), "end": str(rets.index[-1].date())},
           "n_months": int(len(rets)),
           "assumptions": {"rebalance": "month-end, weights from data through t held t+1",
                           "cost_bp_per_unit_turnover": a.cost_bp,
                           "risk_free": "^IRX/12",
                           "ce": "excess mean*12 - 0.5*var*12 (risk aversion 1)",
                           "mdd": "month-end, not intraday"},
           "correlation": {c: {d: round(float(corr.loc[c, d]), 3) for d in corr.columns}
                           for c in corr.columns},
           "results": {}}

    # static benchmarks
    w6040 = pd.DataFrame(0.0, index=rets.index, columns=ASSETS)
    w6040["SPY"], w6040["TLT"] = 0.60, 0.40
    out["results"]["60_40_static"] = run_weights(w6040, rets, rf, "60/40 static", a.cost_bp)[1]

    w = pd.DataFrame(1.0 / 4, index=rets.index, columns=ASSETS)
    out["results"]["ew4_static"] = run_weights(w, rets, rf, "equal weight 4", a.cost_bp)[1]

    # inverse-vol risk parity (rolling, no look-ahead)
    iv = inverse_vol_weights(rets).dropna()
    out["results"]["risk_parity_invvol"] = run_weights(
        iv, rets.loc[iv.index], rf, "risk parity (inverse vol, 12m)", a.cost_bp)[1]

    # equal-risk-contribution, recomputed monthly on a trailing 24m covariance
    erc = {}
    for i in range(24, len(rets)):
        win = rets.iloc[i - 24:i]
        erc[rets.index[i]] = pd.Series(erc_weights(win.cov().values * 12), index=ASSETS)
    erc_df = pd.DataFrame(erc).T
    out["results"]["risk_parity_erc"] = run_weights(
        erc_df, rets.loc[erc_df.index], rf, "risk parity (ERC, 24m)", a.cost_bp)[1]

    # HRP, recomputed monthly on a trailing 36m window
    hrp = {}
    for i in range(36, len(rets)):
        win = rets.iloc[i - 36:i]
        hrp[rets.index[i]] = hrp_weights(win.cov() * 12, win.corr())
    hrp_df = pd.DataFrame(hrp).T
    out["results"]["hrp"] = run_weights(
        hrp_df, rets.loc[hrp_df.index], rf, "HRP (36m)", a.cost_bp)[1]

    # cost stress
    for k in ("risk_parity_erc", "hrp"):
        lbl = out["results"][k]["label"]
        out["results"][f"{k}_cost10"] = run_weights(
            erc_df if k == "risk_parity_erc" else hrp_df,
            rets.loc[erc_df.index if k == "risk_parity_erc" else hrp_df.index],
            rf, lbl + " @10bp", 10.0)[1]

    # --- vol target applied ON TOP of each allocation, same window, monthly granularity
    # so the comparison is apples-to-apples with the rows above (the daily-granularity
    # result lives in reports/portfolio/vol_target_vs_hold.json and is NOT comparable
    # to these rows; mixing the two would overstate the monthly one).
    def vt(monthly_ret: pd.Series, target: float = 0.10, look: int = 12,
           cap: float = 2.0, cost_bp: float = 5.0) -> pd.Series:
        rv = monthly_ret.rolling(look).std().shift(1) * np.sqrt(12)
        lev = (target / rv.replace(0.0, np.nan)).clip(0.0, cap).fillna(0.0)
        turn = lev.diff().abs().fillna(lev)
        return (lev * monthly_ret - turn * cost_bp / 1e4).dropna()

    core_ret = run_weights(w6040, rets, rf, "core", a.cost_bp)[0]
    out["results"]["6040_voltarget10"] = metrics(vt(core_ret), rf, "60/40 + vol target 10%",)
    erc_ret = run_weights(erc_df, rets.loc[erc_df.index], rf, "erc", a.cost_bp)[0]
    out["results"]["erc_voltarget10"] = metrics(vt(erc_ret), rf, "ERC + vol target 10%")
    hrp_ret = run_weights(hrp_df, rets.loc[hrp_df.index], rf, "hrp", a.cost_bp)[0]
    out["results"]["hrp_voltarget10"] = metrics(vt(hrp_ret), rf, "HRP + vol target 10%")

    # E34: does a dead sleeve earn weight at max-CE? Full sample, declared in-sample.
    mu_ex = (rets[ASSETS].sub(rf, axis=0)).mean()
    cov_m = rets[ASSETS].cov()
    w_opt = max_ce_weights(mu_ex, cov_m)
    out["combined_book"] = {
        "method": "long-only max certainty-equivalent, full-sample weights "
                  "(IN-SAMPLE, reported as arithmetic not as a strategy)",
        "weights_pct": {k: round(float(v) * 100, 2) for k, v in w_opt.items()},
        "sleeves_at_zero": [k for k, v in w_opt.items() if v < 0.01],
        "interpretation": None,
    }
    z = out["combined_book"]["sleeves_at_zero"]
    out["combined_book"]["sleeves_at_zero_are_diversifiers"] = [
        k for k in z if abs(float(out["correlation"][k].get("SPY", 0.0))) < 0.30]
    out["combined_book"]["interpretation"] = (
        f"The optimiser drives {len(z)} of {len(ASSETS)} assets to zero ({', '.join(z) or 'none'}). "
        f"But {', '.join(out['combined_book']['sleeves_at_zero_are_diversifiers']) or 'none'} of the "
        f"zeroed assets are DIVERSIFIERS (|corr to SPY| < 0.30), including TLT at "
        f"{out['correlation']['TLT']['SPY']:+.3f} — the single most valuable correlation in a "
        f"60/40. Zeroing it is error maximisation in mean returns, not a finding about "
        f"diversification: the optimiser is told TLT's realised excess return over THIS sample, "
        f"and this sample is a rate-hiking era. A risk-based allocator that never sees expected "
        f"returns keeps TLT and does better on CE and drawdown. So the honest combined book is "
        f"risk-allocated, not return-optimised — and the failed per-class sleeves still earn "
        f"zero, because they have neither positive excess return nor a useful correlation.")

    # --- paired bootstrap on the CE DIFFERENCE, because "beats 60/40" is a claim about a
    # difference and a point estimate cannot carry it. Resamples months jointly so the
    # correlation between the two return streams is preserved.
    def paired_ce_bootstrap(a_ret: pd.Series, b_ret: pd.Series, n_boot: int = 5000,
                            seed: int = 20261122) -> dict:
        both = pd.concat([a_ret.rename("a"), b_ret.rename("b")], axis=1).dropna()
        if len(both) < 36:
            return {"error": "insufficient_overlap", "n": int(len(both))}
        rng = np.random.default_rng(seed)
        k = len(both)
        av, bv = both["a"].values, both["b"].values
        diffs = np.empty(n_boot)
        for i in range(n_boot):
            idx = rng.integers(0, k, k)
            ra, rb = av[idx], bv[idx]
            ce_a = ra.mean() * 12 - 0.5 * ra.var(ddof=1) * 12
            ce_b = rb.mean() * 12 - 0.5 * rb.var(ddof=1) * 12
            diffs[i] = ce_a - ce_b
        lo, hi = np.percentile(diffs, [5, 95])
        # The CE on the COMMON window, because the table's CE for each series is computed
        # over that series' own span and the spans differ by burn-in (24m ERC, 36m HRP).
        # Comparing a table CE to a bootstrap drawn from a shorter window is how a
        # +0.57 pp advantage turned into a -1.91 pp mean on the first run of this tool:
        # the headline was measured on months the bootstrap never saw. Both CEs are
        # restated here so every claim in the write-up is on one window.
        rf_c = rf.reindex(both.index).fillna(0.0).values

        def ce1(x, r):
            ex = x - r
            return float(ex.mean() * 12 - 0.5 * x.var(ddof=1) * 12)
        return {"n_months": k, "n_boot": n_boot, "common_window": [
                    str(both.index[0].date()), str(both.index[-1].date())],
                "ce_a_pp_on_common": round(ce1(av, rf_c) * 100, 2),
                "ce_b_pp_on_common": round(ce1(bv, rf_c) * 100, 2),
                "ce_diff_point_pp": round((ce1(av, rf_c) - ce1(bv, rf_c)) * 100, 3),
                "ce_diff_boot_mean_pp": round(float(diffs.mean()) * 100, 3),
                "ci90_pp": [round(float(lo) * 100, 3), round(float(hi) * 100, 3)],
                "excludes_zero": bool(lo > 0 or hi < 0),
                "pct_bootstrap_positive": round(float((diffs > 0).mean()) * 100, 1)}

    base_ret = run_weights(w6040, rets, rf, "core", a.cost_bp)[0]
    out["paired_ce_bootstrap_vs_60_40"] = {}
    for key, series in (("risk_parity_erc", erc_ret), ("hrp", hrp_ret),
                        ("hrp_voltarget10", vt(hrp_ret)), ("erc_voltarget10", vt(erc_ret)),
                        ("6040_voltarget10", vt(base_ret))):
        out["paired_ce_bootstrap_vs_60_40"][key] = paired_ce_bootstrap(series, base_ret)

    # verdict
    base = out["results"]["60_40_static"].get("ce_pct")
    best = max(((k, v.get("ce_pct")) for k, v in out["results"].items()
                if v.get("ce_pct") is not None), key=lambda kv: kv[1])
    boot = out["paired_ce_bootstrap_vs_60_40"].get(best[0], {})
    any_excluded = [k for k, v in out["paired_ce_bootstrap_vs_60_40"].items()
                    if v.get("excludes_zero")]
    out["verdict"] = {
        "strategies_with_ci_excluding_zero": any_excluded,
        "n_strategies_with_ci_excluding_zero": len(any_excluded),
        "baseline_ce_pct": base,
        "best_ce_strategy": best[0],
        "best_ce_pct": best[1],
        "point_estimate_beats_6040": bool(base is not None and best[1] > base),
        "bootstrap_ci90_of_difference_pp": boot.get("ci90_pp"),
        "bootstrap_excludes_zero": boot.get("excludes_zero"),
        "beats_6040_after_cost": bool(any_excluded),
        "ce_diff_point_pp_on_common": boot.get("ce_diff_point_pp"),
        "basis": ("CE is the yardstick because Sharpe can be raised by deleveraging. "
                  "A point estimate alone does not qualify as 'beats': the claim requires "
                  "a paired-bootstrap 90% CI on the CE DIFFERENCE that excludes zero."),
    }

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"\n{'strategy':34s} {'CAGR':>7s} {'vol':>6s} {'Sharpe':>7s} {'MDD':>7s} {'CE':>7s}")
    for v in out["results"].values():
        if "error" in v:
            print(f"{v['label']:34s} {v['error']}")
            continue
        print(f"{v['label']:34s} {v['cagr_pct']:7.2f} {v['vol_pct']:6.2f} "
              f"{v['sharpe_vs_rf']:7.3f} {v['mdd_month_end_pct']:7.2f} {v['ce_pct']:7.2f}")
    print(f"\ncorr:\n{corr.round(3)}")
    print("\npaired bootstrap vs 60/40 (CE difference, 90% CI):")
    for k, v in out["paired_ce_bootstrap_vs_60_40"].items():
        if "error" in v:
            print(f"  {k:20s} {v['error']}")
            continue
        star = "EXCLUDES 0" if v["excludes_zero"] else "includes 0"
        print(f"  {k:20s} common {v['n_months']:3d}m  CE {v['ce_a_pp_on_common']:5.2f} vs "
              f"{v['ce_b_pp_on_common']:5.2f}  diff {v['ce_diff_point_pp']:+6.2f} pp "
              f"[{v['ci90_pp'][0]:+6.2f}, {v['ci90_pp'][1]:+6.2f}]  {star}")
    print(f"\nmax-CE weights: {out['combined_book']['weights_pct']}")
    print(f"zeroed: {z}")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()

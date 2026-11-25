"""
Top-gainer persistence test — H-237 (daily chase) and H-238 (weekly swing).

Answers the question: could we have predicted the next day's / next week's biggest
gainers? Both hypotheses were pre-registered in reports/hypothesis_registry.json
BEFORE this file was first run.

Design notes that matter for interpreting the output:
  * Survivorship bias: the universe is a fixed list of names liquid TODAY. Using
    today's winners as the historical universe inflates every long-only result.
    So a FAIL here is strong evidence; a PASS would be weak.
  * Cost is charged every rebalance, not per year. Daily rotation pays 0.98 bp
    ~247 times a year; that is the number that kills retail top-gainer screens.
  * The benchmark for the cross-sectional test is the UNIVERSE MEAN, not SPY. A
    long-only selection rule has to beat its own average pick, otherwise it is
    just buying the market with extra steps. Jensen alpha vs SPY is reported
    separately so the beta is not hidden.

Paper only. Zero capital. Not investment advice.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path("data/cache/top_gainer_closes.parquet")
COST_BP_RT = 0.98          # measured, reports/equity_cost_hml.json, USD account
HURDLE = 0.0432            # tools/capacity_model.py HURDLE_TBILL_APR
TRADING_DAYS = 252

# Fixed liquid large-cap universe. Deliberately hardcoded so the universe cannot
# silently change between runs (a moving universe is an unlogged trial).
UNIVERSE = """
AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO BRK-B JPM V MA UNH XOM JNJ PG HD COST
ABBV MRK CVX PEP KO ADBE WMT CSCO CRM ACN LIN MCD TMO ABT DHR NKE TXN PM NEE
WFC DIS AMD QCOM BA INTC CAT GS AMGN IBM SPGI HON UPS RTX BKNG SBUX BLK AXP
DE ISRG GILD MDT SYK PLD ADI TJX VRTX C MMC LRCX KLAC PANW MU ADSK REGN
BSX ETN NOC FDX EMR APSL SLB AON PGR T FCX GM F DAL UAL AAL CCL NCLH MGM WYNN
LVS RCL MAR HLT YUM CMG DPZ LULU ROST TGT DG DLTR BBY ORCL SAP SHOP SQ PYPL
COIN MSTR HOOD SOFI PLTR SNOW NET CRWD DDOG ZS OKTA
""".split()
UNIVERSE = [t.replace(".", "-") for t in UNIVERSE]


def fetch(universe: list[str], period: str = "6y") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        tickers=universe, period=period, interval="1d",
        auto_adjust=True, group_by="column", progress=False, threads=True,
    )
    close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
    close = close.dropna(axis=1, how="all").ffill()
    return close


def load(universe: list[str], refresh: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not refresh:
        return pd.read_parquet(CACHE)
    close = fetch(universe)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    close.to_parquet(CACHE)
    return close


def block_bootstrap_ci(x: np.ndarray, n_boot: int = 4000, block: int = 20,
                       seed: int = 7) -> tuple[float, float]:
    """Moving-block bootstrap 95% CI for the mean of an autocorrelated series."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 2 * block:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    starts_max = n - block
    for i in range(n_boot):
        starts = rng.integers(0, starts_max, n_blocks)
        sample = np.concatenate([x[s:s + block] for s in starts])[:n]
        means[i] = sample.mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def ols_alpha_vs_bench(series: pd.Series, bench: pd.Series,
                       n_boot: int = 3000, block: int = 20,
                       seed: int = 11) -> dict:
    """Jensen's alpha: regress strategy daily returns on benchmark, annualise.

    A point alpha with no interval is not a result. Bootstrapping the (y, x)
    pairs in blocks preserves the autocorrelation of both legs; resampling
    residuals alone would assume the regressor is fixed, which it is not
    (both series are returns).
    """
    j = pd.concat([series, bench], axis=1, join="inner").dropna()
    n = len(j)
    if n < 4 * block:
        return {"alpha_ann": np.nan, "beta": np.nan, "n": int(n),
                "alpha_ci_ann": [np.nan, np.nan], "alpha_excludes_zero": False}
    y = j.iloc[:, 0].to_numpy()
    x = j.iloc[:, 1].to_numpy()

    def fit(yy, xx):
        X = np.column_stack([np.ones_like(xx), xx])
        c, *_ = np.linalg.lstsq(X, yy, rcond=None)
        return c[0], c[1]

    a0, b0 = fit(y, x)
    rng = np.random.default_rng(seed)
    starts_max = n - block
    n_blocks = int(np.ceil(n / block))
    alphas = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.integers(0, starts_max, n_blocks)
        idx = np.concatenate([np.arange(t, t + block) for t in s])[:n]
        alphas[i], _ = fit(y[idx], x[idx])
    lo, hi = np.percentile(alphas, 2.5), np.percentile(alphas, 97.5)
    return {
        "alpha_ann": float(a0 * TRADING_DAYS),
        "beta": float(b0),
        "n": int(n),
        "alpha_ci_ann": [float(lo * TRADING_DAYS), float(hi * TRADING_DAYS)],
        "alpha_excludes_zero": bool(lo > 0),
    }


def run_one(ret: pd.DataFrame, lookback: int, hold: int, top_frac: float,
            label: str) -> dict:
    """Hold the top `top_frac` by trailing `lookback` return for `hold` days."""
    keep = ret.columns[ret.notna().mean() > 0.90]
    ret = ret[keep]
    # Proportional floor, not a magic 20: a hardcoded 20 silently produced an
    # EMPTY result set on any universe smaller than 20 names. Silent-empty is
    # the 'watchdog that lies' pattern -- fail loudly instead.
    min_names = max(5, int(round(0.05 * ret.shape[1])))
    logret = np.log1p(ret)

    trail = logret.rolling(lookback).sum()
    # Forward hold-day sum at t must be a_{t+1}..a_{t+hold}. shift(-hold) moves
    # a_{t+hold} to position t; rolling(hold).sum() then collects a_{t+1}..a_{t+hold}.
    # BUGFIX: an extra .shift(-(hold-1)) was applied here, which re-moved the
    # result by hold-1 and misaligned every hold>1 test.
    fwd = logret.shift(-hold).rolling(hold).sum()

    excess, strat, dates = [], [], []
    for t in ret.index:
        tr = trail.loc[t]
        fw = fwd.loc[t]
        ok = tr.notna() & fw.notna()
        if ok.sum() < min_names:
            continue
        trv, fwv = tr[ok], fw[ok]
        cut = trv.quantile(1 - top_frac)
        top = trv[trv >= cut].index
        if len(top) == 0:
            continue
        excess.append(np.expm1(fwv[top].mean()) - np.expm1(fwv.mean()))
        strat.append(np.expm1(fwv[top].mean()))
        dates.append(t)

    excess = np.asarray(excess)
    strat = np.asarray(strat)
    if excess.size == 0:
        raise ValueError(
            f"{label}: no usable periods (universe={ret.shape[1]}, "
            f"min_names={min_names}, lookback={lookback}, hold={hold}). "
            "Returning an empty result silently would look like a clean run."
        )
    cost = COST_BP_RT / 1e4
    periods_per_year = TRADING_DAYS / hold

    gross_ann = (1 + strat.mean()) ** periods_per_year - 1
    net_per_period = strat.mean() - cost
    net_ann = (1 + net_per_period) ** periods_per_year - 1

    lb, ub = block_bootstrap_ci(excess, block=max(10, hold * 4))
    excess_bp = float(excess.mean() * 1e4)

    return {
        "label": label,
        "lookback_d": lookback,
        "hold_d": hold,
        "top_frac": top_frac,
        "n_periods": int(excess.size),
        "universe": int(len(keep)),
        "excess_bp_per_period": round(excess_bp, 3),
        "excess_ci_bp": [round(lb * 1e4, 3) if np.isfinite(lb) else None,
                         round(ub * 1e4, 3) if np.isfinite(ub) else None],
        "ci_excludes_zero": bool(np.isfinite(lb) and lb > 0),
        "gross_ann_pct": round(gross_ann * 100, 2),
        "cost_drag_ann_pct": round((gross_ann - net_ann) * 100, 2),
        "net_ann_pct": round(net_ann * 100, 2),
        # NOTE: net_ann > hurdle is NOT evidence of edge -- a long-only book with
        # beta > 1 clears an absolute hurdle in a bull market by doing nothing.
        # Kept only so the raw number is visible; the DECIDING field is
        # ci_excludes_zero on the universe-relative excess (beta-free).
        "raw_net_beats_hurdle": bool(net_ann > HURDLE),
        "verdict": ("PASS" if (np.isfinite(lb) and lb > 0) else "REFUTED"),
    }


def daily_series(ret: pd.DataFrame, lookback: int, top_frac: float,
                 hold: int) -> pd.Series:
    """Strategy daily return series (equal-weight top decile, rebalanced every hold)."""
    keep = ret.columns[ret.notna().mean() > 0.90]
    ret = ret[keep]
    min_names = max(3, int(round(0.05 * ret.shape[1])))
    logret = np.log1p(ret)
    trail = logret.rolling(lookback).sum()

    out = {}
    rebal_dates = ret.index[lookback::hold]
    for d in rebal_dates:
        tr = trail.loc[d]
        if tr.notna().sum() < min_names:
            continue
        cut = tr.dropna().quantile(1 - top_frac)
        top = tr[tr >= cut].dropna().index
        if len(top) == 0:
            continue
        idx = ret.index.get_loc(d)
        # BUGFIX (look-ahead): we ranked using returns THROUGH day d, so the
        # position must be entered at the close of d and can only capture
        # returns from d+1 onward. Using iloc[idx:...] captured day d's own
        # return -- the same day used to rank -- which manufactured a +880%
        # annual alpha out of nothing.
        window = ret.iloc[idx + 1: idx + 1 + hold]
        if len(window) < hold:
            continue
        for dd, row in window.iterrows():
            vals = row[top].dropna()
            if len(vals):
                out[dd] = float(vals.mean())
    if not out:
        raise ValueError(
            f"daily_series produced no periods (universe={ret.shape[1]}, "
            f"min_names={min_names}, lookback={lookback}, hold={hold}); "
            "an empty series would silently look like a flat strategy."
        )
    return pd.Series(out).sort_index()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    close = load(UNIVERSE, refresh=args.refresh)
    ret = close.pct_change()
    print(f"universe requested={len(UNIVERSE)} priced={close.shape[1]} "
          f"bars={len(close)} {close.index[0].date()}..{close.index[-1].date()}")

    bench = load_bench()

    results = []
    # --- PRIMARY pre-registered tests -------------------------------------
    results.append(run_one(ret, 1, 1, 0.10, "H-237 daily chase (primary)"))
    results.append(run_one(ret, 5, 5, 0.10, "H-238 weekly swing (primary)"))
    # --- SENSITIVITY (reported, but these cost trials) --------------------
    results.append(run_one(ret, 5, 1, 0.10, "sens: 5d look -> 1d hold"))
    results.append(run_one(ret, 21, 21, 0.10, "sens: 1m look -> 1m hold"))
    results.append(run_one(ret, 63, 21, 0.10, "sens: 3m look -> 1m hold"))
    results.append(run_one(ret, 1, 1, 0.02, "sens: daily top 2% only"))

    print()
    hdr = f"{'strategy':34s} {'n':>5s} {'excess bp/period':>16s} {'CI lb':>8s} {'net ann%':>9s} {'cost drag%':>10s} {'>verdict':>9s}"
    print(hdr)
    for r in results:
        ci = r["excess_ci_bp"]
        print(f"{r['label']:34s} {r['n_periods']:5d} {r['excess_bp_per_period']:16.3f} "
              f"{str(ci[0]):>8s} {r['net_ann_pct']:9.2f} {r['cost_drag_ann_pct']:10.2f} "
              f"{r['verdict']:>9s}")

    print("\n--- Jensen alpha vs benchmark (daily-chase and weekly-swing) ---")
    for lb, hd, lab in [(1, 1, "daily chase"), (5, 5, "weekly swing")]:
        s = daily_series(ret, lb, 0.10, hd)
        a = ols_alpha_vs_bench(s, bench)
        lo, hi = a["alpha_ci_ann"]
        print(f"{lab:14s} beta={a['beta']:.3f} alpha_ann={a['alpha_ann']*100:+.2f}% "
              f"CI[{lo*100:+.2f}%,{hi*100:+.2f}%] "
              f"excl0={a['alpha_excludes_zero']} n={a['n']}")

    out = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "cost_bp_rt": COST_BP_RT, "hurdle": HURDLE,
        "universe_n": int(close.shape[1]), "bars": len(close),
        "window": [str(close.index[0].date()), str(close.index[-1].date())],
        "survivorship_note": "universe is names liquid TODAY -> inflates long-only results; a FAIL is strong, a PASS is weak",
        "trials_added": 2, "sensitivity_reported": 4,
        "results": results,
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/top_gainer_test.json").write_text(json.dumps(out, indent=1))
    print("\nwritten: reports/top_gainer_test.json")
    return 0


def load_bench() -> pd.Series:
    """SPY daily returns from the same cache so the alignment is exact."""
    import yfinance as yf
    p = Path("data/cache/spy_bench.parquet")
    if p.exists():
        df = pd.read_parquet(p)
    else:
        df = yf.download("SPY", period="6y", interval="1d", auto_adjust=True,
                         progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Close"]]
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p)
    return df["Close"].pct_change().rename("SPY")


if __name__ == "__main__":
    sys.exit(main())

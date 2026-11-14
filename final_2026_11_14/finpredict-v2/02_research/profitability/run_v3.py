"""v3: breadth-first test of documented edge families.

Candidates: crypto XS momentum/reversal/TSMOM/trend-filtered momentum; ETF XS momentum/
reversal/TSMOM; country rotation. Validation adds walk-forward, CPCV, and a Reality Check (SPA)
on top of the v1/v2 gates.
"""
from __future__ import annotations

import json
import math
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import (deflated_sharpe, evaluate, metrics, multiple_testing,
                      pbo_cscv, portfolio_returns)
from data.loader import binance_daily, nasdaq_daily, panel, treasury_bill_daily
from strategies import (buy_hold, fixed_mix, tsmom_breadth, xs_quantile)

HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "v3"
RUN.mkdir(parents=True, exist_ok=True)
(RUN / "weights").mkdir(exist_ok=True)

TRAIN_END, OOS_START = "2023-12-31", "2024-01-01"
TODAY = date.today().isoformat()

CRYPTO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
          "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT", "TRXUSDT", "ATOMUSDT",
          "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT", "TIAUSDT",
          "SEIUSDT", "RUNEUSDT", "AAVEUSDT", "UNIUSDT", "MKRUSDT", "CRVUSDT", "COMPUSDT",
          "SNXUSDT", "ETCUSDT"]
CRYPTO_CORE = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
               "LTCUSDT", "BCHUSDT", "TRXUSDT", "LINKUSDT", "DOTUSDT", "ATOMUSDT",
               "ETCUSDT", "XLMUSDT", "EOSUSDT", "FILUSDT", "ALGOUSDT", "VETUSDT",
               "THETAUSDT", "ICPUSDT"]

ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "VGK", "EWJ", "EWG", "EWU", "EWA",
        "EWC", "EWH", "EWY", "EWT", "EWZ", "XLE", "XLF", "XLK", "XLV", "XLY", "XLP",
        "XLI", "XLU", "XLB", "XLRE", "XLC", "TLT", "IEF", "SHY", "LQD", "HYG", "AGG",
        "BND", "GLD", "SLV", "USO", "DBC", "VNQ", "VWO", "VEA", "IYR", "KRE", "SMH",
        "XBI", "IBB", "ITA", "XME", "GDX", "XOP"]
ETF_CORE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "AGG",
            "GLD", "SLV", "USO", "DBC", "VNQ", "VWO", "VEA", "IYR", "SMH", "XBI"]
COUNTRIES = ["EWJ", "EWG", "EWU", "EWA", "EWC", "EWH", "EWY", "EWT", "EWZ", "EWW",
             "EWP", "EWI"]


def cash_returns(idx, tb):
    rate = tb["rate"].reindex(idx, method="ffill").ffill().bfill()
    return (rate / 100.0 / 252.0).fillna(0.0)


def prep(close, tb):
    r = close.pct_change()
    r["CASH"] = cash_returns(close.index, tb)
    return r.dropna(how="all")


def cashify(w):
    out = w.copy()
    out["CASH"] = (1.0 - w.sum(axis=1)).clip(lower=0.0)
    return out


def walk_forward(port, years, ann):
    parts = []
    for y in years:
        p = port.loc[f"{y}-01-01":f"{y}-12-31"]
        if len(p) > 20:
            parts.append(p)
    if not parts:
        return metrics(pd.Series(dtype=float), ann)
    return metrics(pd.concat(parts), ann)


def cpcv_median(mat, n_blocks=6, ann=252):
    T = len(mat)
    if T < n_blocks * 4:
        return float("nan")
    blocks = np.array_split(np.arange(T), n_blocks)
    vals = []
    for combo in combinations(range(n_blocks), n_blocks // 2):
        idx = np.concatenate([blocks[i] for i in combo])
        sub = mat.iloc[idx]
        for c in mat.columns:
            r = sub[c]
            sd = r.std()
            if sd and sd > 0:
                vals.append(float(r.mean() / sd * math.sqrt(ann)))
    return float(np.median(vals)) if vals else float("nan")


def spa_test(excess: pd.DataFrame, n_boot=2000, block=20, seed=11):
    X = excess.dropna()
    T = len(X)
    if T < block * 3 or X.shape[1] == 0:
        return float("nan")
    obs = float(X.mean().max())
    Xc = (X - X.mean()).values
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    hits = 0
    for _ in range(n_boot):
        starts = rng.integers(0, T - block, size=nb)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:T]
        if float(Xc[idx].mean(axis=0).max()) >= obs:
            hits += 1
    return float(hits / n_boot)


def pct(x):
    return "nan" if x != x else f"{x*100:.1f}%"


def main():
    print("[1/4] data ...")
    tb = treasury_bill_daily(2018, int(TODAY[:4]))
    crypto = panel(binance_daily, CRYPTO, start="2018-01-01", end=TODAY).sort_index()
    crypto_core = panel(binance_daily, CRYPTO_CORE, start="2018-01-01", end=TODAY).sort_index()
    etfs = panel(nasdaq_daily, ETFS, start="2016-01-01", end=TODAY).sort_index()
    etf_core = panel(nasdaq_daily, ETF_CORE, start="2016-01-01", end=TODAY).sort_index()
    countries = panel(nasdaq_daily, COUNTRIES, start="2016-01-01", end=TODAY).sort_index()
    print("crypto", crypto.shape, "core", crypto_core.shape, "etfs", etfs.shape,
          "etf_core", etf_core.shape, "countries", countries.shape)

    c_rets, e_rets = prep(crypto, tb), prep(etfs, tb)
    ccore_rets = prep(crypto_core, tb)
    ecore_rets = prep(etf_core, tb)
    ctry_rets = prep(countries, tb)
    btc_trend = (crypto["BTCUSDT"] > crypto["BTCUSDT"].rolling(200, min_periods=200).mean())

    specs = [
        ("H13_CRYPTO_XS_MOM", lambda: cashify(xs_quantile(crypto, 28, 0.2, "top", 180, "W-FRI")),
         c_rets, 10, 365, buy_hold(crypto), 5),
        ("H14_CRYPTO_XS_REV", lambda: cashify(xs_quantile(crypto, 7, 0.2, "bottom", 180, "W-FRI")),
         c_rets, 10, 365, buy_hold(crypto), 5),
        ("H15_CRYPTO_TSMOM_BREADTH", lambda: tsmom_breadth(crypto_core, 252, 20, 0.40, 1.0, 365),
         ccore_rets, 10, 365, buy_hold(crypto_core), 21),
        ("H16_ETF_XS_MOM", lambda: cashify(xs_quantile(etfs, 252, 0.075, "top", 252, "M", skip=21)),
         e_rets, 5, 252, buy_hold(etfs), 21),
        ("H17_ETF_XS_REV", lambda: cashify(xs_quantile(etfs, 5, 0.1, "bottom", 252, "W-FRI")),
         e_rets, 5, 252, buy_hold(etfs), 5),
        ("H18_ETF_TSMOM_BREADTH", lambda: tsmom_breadth(etf_core, 252, 20, 0.40, 1.0, 252),
         ecore_rets, 5, 252, fixed_mix(etf_core, {"SPY": 0.6, "AGG": 0.4}), 21),
        ("H19_COUNTRY_MOM", lambda: cashify(xs_quantile(countries, 252, 0.25, "top", 252, "M", skip=21)),
         ctry_rets, 5, 252, buy_hold(countries), 21),
        ("H20_CRYPTO_MOM_BTC_TREND",
         lambda: cashify(xs_quantile(crypto, 28, 0.2, "top", 180, "W-FRI", trend_filter=btc_trend)),
         c_rets, 10, 365, buy_hold(crypto), 5),
    ]

    print("[2/4] running candidates ...")
    results, pvals, oos_matrix, full_returns, bench_returns = [], {}, {}, {}, {}
    CUM_N = 20
    for name, fn, rets, bps, ann, bench, lag_days in specs:
        try:
            w = fn().reindex(index=rets.index, columns=rets.columns).fillna(0.0)
            r = evaluate(name, w, rets, bps, ann, bench, TRAIN_END, OOS_START)
            stress = evaluate(name, w, rets, bps * 2, ann, bench, TRAIN_END, OOS_START)
            port_full, _ = portfolio_returns(w, rets, bps)
            bench_full, _ = portfolio_returns(bench, rets, 0.0)
            lag_w = w.shift(lag_days).fillna(0.0)
            lag_eval = evaluate(name, lag_w, rets, bps, ann, bench, TRAIN_END, OOS_START)
            wf = walk_forward(port_full, range(2021, 2027), ann)
            bf = walk_forward(bench_full, range(2021, 2027), ann)
            r["stress_oos"] = stress["oos"]
            r["lag_oos"] = lag_eval["oos"]
            r["walk_forward"] = {k: getattr(wf, k) for k in wf.__dataclass_fields__}
            r["bench_walk_forward"] = {k: getattr(bf, k) for k in bf.__dataclass_fields__}
            r["dsr"] = deflated_sharpe(r["oos_returns"], CUM_N)
            r["lag_days"] = lag_days
            pvals[name] = r["pvalue_oos"]
            oos_matrix[name] = r["oos_returns"]
            full_returns[name] = port_full
            bench_returns[name] = bench_full
            r.pop("oos_returns", None)
            r.pop("oos_weights", None)
            results.append(r)
            print(f"  {name}: OOS Sharpe {r['oos']['sharpe']:.2f} | CAGR {pct(r['oos']['cagr'])} | "
                  f"WF {r['walk_forward']['sharpe']:.2f} | DSR {r['dsr']:.3f} | p {r['pvalue_oos']:.3g}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: FAILED {exc}")
            results.append({"name": name, "error": str(exc)})

    print("[3/4] validation ...")
    pd.concat(oos_matrix, axis=1).to_csv(RUN / "oos_returns.csv")
    pd.concat(full_returns, axis=1).to_csv(RUN / "full_returns.csv")

    crypto_names = [n for n in full_returns if n.startswith(("H13", "H14", "H15", "H20"))]
    etf_names = [n for n in full_returns if n.startswith(("H16", "H17", "H18", "H19"))]
    pbo_crypto = pbo_cscv(pd.concat({n: full_returns[n] for n in crypto_names}, axis=1).dropna(), 16)
    pbo_etf = pbo_cscv(pd.concat({n: full_returns[n] for n in etf_names}, axis=1).dropna(), 16)
    cpcv_crypto = cpcv_median(pd.concat({n: full_returns[n] for n in crypto_names}, axis=1).dropna(), 6, 365)
    cpcv_etf = cpcv_median(pd.concat({n: full_returns[n] for n in etf_names}, axis=1).dropna(), 6, 252)

    excess = pd.concat({n: full_returns[n] - bench_returns[n] for n in full_returns}, axis=1).dropna()
    spa_p = spa_test(excess, 2000, 20)
    mt = multiple_testing(pvals)
    mt_all = dict(pvals)
    v1p = HERE / "runs" / "v1" / "results.json"
    v2p = HERE / "runs" / "v2" / "results.json"
    for p in (v1p, v2p):
        if p.exists():
            try:
                d = json.loads(p.read_text())
                for k, v in (d.get("multiple_testing", {}).get("pvalues", {}) or {}).items():
                    mt_all.setdefault(k, v)
            except Exception:
                pass
    mt_cum = multiple_testing(mt_all)

    print("[4/4] gates ...")
    gates = []
    for r in results:
        if "oos" not in r:
            gates.append({"name": r["name"], "status": "ERROR", "reason": r.get("error")})
            continue
        o, b, s, lag = r["oos"], r["benchmark_oos"], r["stress_oos"], r["lag_oos"]
        wf, bwf = r["walk_forward"], r["bench_walk_forward"]
        is_crypto = r["name"].startswith(("H13", "H14", "H15", "H20"))
        pbo_v = pbo_crypto if is_crypto else pbo_etf
        cpcv_v = cpcv_crypto if is_crypto else cpcv_etf
        fails = []
        if not (o["sharpe"] >= 1.0): fails.append("oos_sharpe<1.0")
        if not (o["sharpe"] >= b["sharpe"] + 0.30): fails.append("not_0.3_above_benchmark")
        if not (o["cagr"] > 0): fails.append("oos_cagr<=0")
        if not (o["total_return"] > b["total_return"]): fails.append("below_benchmark_return")
        if not (o["n_changes"] >= 30): fails.append("n_trades<30")
        if not (wf["sharpe"] >= 0.8): fails.append("wf_sharpe<0.8")
        if not (wf["sharpe"] > bwf["sharpe"]): fails.append("wf_below_benchmark")
        if not (cpcv_v >= 0.5): fails.append("cpcv_median<0.5")
        if pbo_v == pbo_v and not (pbo_v < 0.5): fails.append("pbo>=0.5")
        if spa_p == spa_p and not (spa_p < 0.05): fails.append("spa_p>=0.05")
        if not (r["dsr"] >= 0.95): fails.append("dsr<0.95")
        if not (r["bootstrap_oos"]["p05"] > 0): fails.append("bootstrap_p05<=0")
        if not (s["sharpe"] >= 0.5 and s["sharpe"] > b["sharpe"]): fails.append("2x_cost_fail")
        if not (lag["sharpe"] >= 1.0 and lag["sharpe"] > b["sharpe"]): fails.append("execution_lag_fail")
        gates.append({"name": r["name"], "status": "PASSED_GATES" if not fails else "NOT_PROVED",
                      "fails": fails, "dsr": r["dsr"], "pvalue": r["pvalue_oos"],
                      "pbo": pbo_v, "cpcv_median": cpcv_v, "spa_p": spa_p})

    out = {"version": "v3", "run_at": pd.Timestamp.utcnow().isoformat(),
           "train_end": TRAIN_END, "oos_start": OOS_START, "n_v3": len(specs),
           "cumulative_n": CUM_N, "pbo_crypto": pbo_crypto, "pbo_etf": pbo_etf,
           "cpcv_crypto": cpcv_crypto, "cpcv_etf": cpcv_etf, "spa_p": spa_p,
           "multiple_testing_v3": mt, "multiple_testing_cumulative": mt_cum,
           "gates": gates, "results": results}
    (RUN / "results.json").write_text(json.dumps(out, indent=2, default=str))

    passed = [g for g in gates if g["status"] == "PASSED_GATES"]
    lines = ["# v3 Results", "", f"Run: {out['run_at']} | OOS ≥{OOS_START} | v3 N=8 | cumulative N=20", "",
             f"**{len(passed)}/8 passed all v3 gates.**" if passed else "**0/8 passed all v3 gates — NOT PROVED.**", "",
             "| Candidate | OOS Sharpe | OOS CAGR | Bench | WF Sharpe | CPCV med | PBO | SPA p | DSR | Lag Sharpe | Status |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"| {r['name']} | — | — | — | — | — | — | — | — | — | ERROR |")
            continue
        lines.append(f"| {r['name']} | {r['oos']['sharpe']:.2f} | {pct(r['oos']['cagr'])} | "
                     f"{r['benchmark_oos']['sharpe']:.2f} | {r['walk_forward']['sharpe']:.2f} | "
                     f"{g['cpcv_median']:.2f} | {g['pbo']:.2f} | {g['spa_p']:.3f} | {r['dsr']:.3f} | "
                     f"{r['lag_oos']['sharpe']:.2f} | {g['status']} |")
    lines += ["", "## Detail", ""]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"### {r['name']} — ERROR\n\n`{r.get('error')}`\n")
            continue
        lines += [f"### {r['name']} — {g['status']}", "",
                  f"- OOS: Sharpe {r['oos']['sharpe']:.2f}, CAGR {pct(r['oos']['cagr'])}, maxDD {pct(r['oos']['max_dd'])}, changes {r['oos']['n_changes']}, exposure {r['oos']['avg_exposure']:.2f}",
                  f"- Benchmark: Sharpe {r['benchmark_oos']['sharpe']:.2f}, CAGR {pct(r['benchmark_oos']['cagr'])}",
                  f"- Walk-forward: Sharpe {r['walk_forward']['sharpe']:.2f} vs bench {r['bench_walk_forward']['sharpe']:.2f}",
                  f"- CPCV median {g['cpcv_median']:.2f}; PBO {g['pbo']:.2f}; SPA p {g['spa_p']:.3f}",
                  f"- DSR (N=20) {r['dsr']:.3f}; bootstrap p05 {r['bootstrap_oos']['p05']:.2f}",
                  f"- 2x cost Sharpe {r['stress_oos']['sharpe']:.2f}; lag {r['lag_days']}d Sharpe {r['lag_oos']['sharpe']:.2f}",
                  f"- Failures: {', '.join(g.get('fails', [])) or 'none'}", ""]
    lines += ["## Validation", "", f"- PBO crypto {pbo_crypto:.2f}; PBO ETF {pbo_etf:.2f}",
              f"- CPCV median crypto {cpcv_crypto:.2f}; ETF {cpcv_etf:.2f}",
              f"- Reality Check (SPA) p = {spa_p:.3f}",
              f"- Cumulative multiple testing N={mt_cum.get('n')}"]
    (RUN / "REPORT.md").write_text("\n".join(lines))
    print("wrote", RUN / "REPORT.md")


if __name__ == "__main__":
    main()

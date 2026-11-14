"""v2 run: cash-yield implementation + unseen ETF universes.

New candidates (cumulative N = 12 with v1):
  H8  Sector-ETF RSI(2) + T-bill cash
  H9  International-ETF RSI(2) + T-bill cash
  H10 SPY/QQQ RSI(2) + T-bill cash (H7 capital-efficiency variant; exploratory)
  H11 Sector-ETF RSI(2) + 200d trend filter + cash
  H12 Sector-ETF 12-1 momentum, monthly top-3 + cash
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from backtest import deflated_sharpe, evaluate, multiple_testing, pbo_cscv
from data.loader import nasdaq_daily, panel, treasury_bill_daily
from strategies import (buy_hold, rsi2_cash, rsi2_trend_cash, sector_momentum_cash)

TRAIN_END = "2023-12-31"
OOS_START = "2024-01-01"
TODAY = date.today().isoformat()

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE"]
INTL = ["EWJ", "EWG", "EWU", "EWA", "EWC", "EWH", "EWY", "EWW", "EWT", "EWZ"]
CORE = ["SPY", "QQQ"]

RUN = __import__("pathlib").Path(__file__).resolve().parent / "runs" / "v2"
RUN.mkdir(parents=True, exist_ok=True)


def cash_returns(index: pd.DatetimeIndex, tb: pd.DataFrame) -> pd.Series:
    rate = tb["rate"].reindex(index, method="ffill").ffill().bfill()
    return (rate / 100.0 / 252.0).fillna(0.0)


def prep(close: pd.DataFrame, tb: pd.DataFrame):
    r = close.pct_change()
    r["CASH"] = cash_returns(close.index, tb)
    return r.dropna(how="all")


def pct(x):
    return "nan" if x != x else f"{x*100:.1f}%"


def fmt(m):
    return (f"Sharpe {m['sharpe']:.2f} | CAGR {pct(m['cagr'])} | maxDD {pct(m['max_dd'])} | "
            f"PF {m['profit_factor']:.2f} | changes {m['n_changes']} | exposure {m['avg_exposure']:.2f}")


def main():
    print("[1/4] data ...")
    tb = treasury_bill_daily(2018, int(TODAY[:4]))
    sectors = panel(nasdaq_daily, SECTORS, start="2016-01-01", end=TODAY).sort_index()
    intl = panel(nasdaq_daily, INTL, start="2016-01-01", end=TODAY).sort_index()
    core = panel(nasdaq_daily, CORE, start="2016-01-01", end=TODAY).sort_index()
    print("sectors", sectors.shape, "intl", intl.shape, "core", core.shape, "tb", tb.shape)
    s_rets, i_rets, c_rets = prep(sectors, tb), prep(intl, tb), prep(core, tb)

    specs = [
        ("H8_SECTOR_RSI2_CASH", lambda: rsi2_cash(sectors, cash_returns(sectors.index, tb)), s_rets, buy_hold(sectors)),
        ("H9_INTL_RSI2_CASH", lambda: rsi2_cash(intl, cash_returns(intl.index, tb)), i_rets, buy_hold(intl)),
        ("H10_CORE_RSI2_CASH", lambda: rsi2_cash(core, cash_returns(core.index, tb)), c_rets, buy_hold(core)),
        ("H11_SECTOR_RSI2_TREND_CASH", lambda: rsi2_trend_cash(sectors, cash_returns(sectors.index, tb)), s_rets, buy_hold(sectors)),
        ("H12_SECTOR_MOM12_TOP3_CASH", lambda: sector_momentum_cash(sectors, cash_returns(sectors.index, tb)), s_rets, buy_hold(sectors)),
    ]

    print("[2/4] running candidates ...")
    results, pvals, oos_matrix = [], {}, {}
    CUM_N = 12
    for name, fn, rets, bench in specs:
        try:
            w = fn().reindex(index=rets.index, columns=rets.columns).fillna(0.0)
            r = evaluate(name, w, rets, 5.0, 252, bench, TRAIN_END, OOS_START)
            stress = evaluate(name, w, rets, 10.0, 252, bench, TRAIN_END, OOS_START)
            r["stress_oos"] = stress["oos"]
            r["dsr"] = deflated_sharpe(r["oos_returns"], CUM_N)
            pvals[name] = r["pvalue_oos"]
            oos_matrix[name] = r["oos_returns"]
            if name.startswith("H10"):
                w.to_csv(RUN / "h10_weights.csv")
            r.pop("oos_returns", None)
            r.pop("oos_weights", None)
            results.append(r)
            print(f"  {name}: OOS {fmt(r['oos'])} | DSR(CUM N=12) {r['dsr']:.3f} | p {r['pvalue_oos']:.3g}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: FAILED {exc}")
            results.append({"name": name, "error": str(exc)})

    print("[3/4] validation ...")
    pd.concat(oos_matrix, axis=1).to_csv(RUN / "oos_returns.csv")
    mat = pd.concat(oos_matrix, axis=1).dropna()
    pbo = pbo_cscv(mat, n_blocks=16) if len(oos_matrix) >= 4 else float("nan")
    pbo_all = float("nan")
    v1_oos = RUN.parent / "v1" / "oos_returns.csv"
    if v1_oos.exists():
        try:
            v1m = pd.read_csv(v1_oos, index_col=0, parse_dates=True)
            allm = pd.concat([v1m, pd.concat(oos_matrix, axis=1)], axis=1).dropna()
            pbo_all = pbo_cscv(allm, n_blocks=16)
        except Exception:
            pass
    pbo_gate = pbo_all if pbo_all == pbo_all else pbo
    # cumulative multiple testing across v1 + v2
    combined = dict(pvals)
    v1_path = RUN.parent / "v1" / "results.json"
    if v1_path.exists():
        try:
            v1 = json.loads(v1_path.read_text())
            for k, v in (v1.get("multiple_testing", {}).get("pvalues", {}) or {}).items():
                combined.setdefault(k, v)
        except Exception:
            pass
    mt = multiple_testing(combined)

    print("[4/4] gates ...")
    gates = []
    for r in results:
        if "oos" not in r:
            gates.append({"name": r["name"], "status": "ERROR", "reason": r.get("error")})
            continue
        o, b, s = r["oos"], r["benchmark_oos"], r["stress_oos"]
        fails = []
        if not (o["sharpe"] >= 1.0): fails.append("oos_sharpe<1.0")
        if not (o["sharpe"] >= b["sharpe"] + 0.30): fails.append("not_0.3_above_benchmark")
        if not (o["cagr"] > 0): fails.append("oos_cagr<=0")
        if not (o["total_return"] > b["total_return"]): fails.append("below_benchmark_return")
        if not (o["n_changes"] >= 30): fails.append("n_trades<30")
        if not (r["dsr"] >= 0.95): fails.append("dsr<0.95")
        if not (r["bootstrap_oos"]["p05"] > 0): fails.append("bootstrap_p05<=0")
        if not (s["sharpe"] >= 0.5 and s["sharpe"] > b["sharpe"]): fails.append("2x_cost_fail")
        if pbo_gate == pbo_gate and not (pbo_gate < 0.5): fails.append("pbo>=0.5")
        gates.append({"name": r["name"], "status": "PASSED_GATES" if not fails else "NOT_PROVED",
                      "fails": fails, "dsr": r["dsr"], "pvalue": r["pvalue_oos"], "pbo": pbo})

    out = {"version": "v2", "run_at": pd.Timestamp.utcnow().isoformat(),
           "train_end": TRAIN_END, "oos_start": OOS_START, "n_v2": len(specs),
           "cumulative_n": CUM_N, "pbo": pbo, "pbo_all": pbo_all, "pbo_gate": pbo_gate, "multiple_testing": mt,
           "gates": gates, "results": results}
    (RUN / "results.json").write_text(json.dumps(out, indent=2, default=str))

    proved = [g for g in gates if g["status"] == "PROVED"]
    lines = ["# v2 Results", "", f"Run: {out['run_at']} | OOS ≥{OOS_START} | v2 N={len(specs)} | cumulative N={CUM_N}", "",
             f"**{len(proved)}/{len(specs)} passed all mechanical gates; final verdict: NOT_PROVED (see VERDICT.md).**" if proved else "**0 candidates passed all gates — NOT PROVED.**", "",
             "| Candidate | OOS Sharpe | OOS CAGR | Bench Sharpe | Bench CAGR | changes | DSR | p | Status |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"| {r['name']} | — | — | — | — | — | — | — | ERROR |")
            continue
        lines.append(f"| {r['name']} | {r['oos']['sharpe']:.2f} | {pct(r['oos']['cagr'])} | "
                     f"{r['benchmark_oos']['sharpe']:.2f} | {pct(r['benchmark_oos']['cagr'])} | "
                     f"{r['oos']['n_changes']} | {r['dsr']:.3f} | {r['pvalue_oos']:.3g} | {g['status']} |")
    lines += ["", "## Detail", ""]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"### {r['name']} — ERROR\n\n`{r.get('error')}`\n")
            continue
        lines += [f"### {r['name']} — {g['status']}", "",
                  f"- Train: {fmt(r['train'])}", f"- OOS: {fmt(r['oos'])}",
                  f"- Benchmark OOS: {fmt(r['benchmark_oos'])}",
                  f"- Bootstrap OOS: p05 {r['bootstrap_oos']['p05']:.2f}, p95 {r['bootstrap_oos']['p95']:.2f}",
                  f"- 2x cost OOS Sharpe: {r['stress_oos']['sharpe']:.2f}",
                  f"- DSR (cumulative N=12): {r['dsr']:.3f}",
                  f"- Failures: {', '.join(g.get('fails', [])) or 'none'}", ""]
    lines += ["## Validation", "", f"- PBO (v2 ETF candidates): {pbo}", f"- PBO (all 12 candidates, common calendar): {pbo_all}",
              f"- Cumulative multiple testing: `{json.dumps(mt)}`"]
    (RUN / "REPORT.md").write_text("\n".join(lines))
    print("wrote", RUN / "REPORT.md")


if __name__ == "__main__":
    main()

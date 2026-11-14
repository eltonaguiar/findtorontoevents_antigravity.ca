"""v1 pre-registered backtest run.

Candidates (all counted in N):
  H1 BTC 200d TSMOM (long/flat)
  H2 ETH 200d TSMOM (long/flat)
  H3 Cross-sectional crypto momentum (28d, top-3, weekly)
  H4 Crypto RSI(2) mean reversion (BTC/ETH/SOL)
  H5 ETF dual momentum (SPY/EFA/AGG vs BIL)
  H6 Vol-scaled BTC TSMOM (target 40%, cap 1.5x)
  H7 Equity RSI(2) (SPY/QQQ)
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import (deflated_sharpe, evaluate, multiple_testing, pbo_cscv)
from data.loader import binance_daily, frankfurter_daily, nasdaq_daily, panel, stooq_daily
from strategies import (buy_hold, dual_momentum, fixed_mix, rsi2, tsmom,
                        vol_scaled_tsmom, xs_momentum)

HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "v1"
RUN.mkdir(parents=True, exist_ok=True)

TRAIN_END = "2023-12-31"
OOS_START = "2024-01-01"
TODAY = date.today().isoformat()

CRYPTO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
          "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "DOTUSDT"]
ETFS = ["SPY", "EFA", "AGG", "BIL"]
EQUITY = ["SPY", "QQQ"]


def pct(x):
    return "nan" if x != x else f"{x*100:.1f}%"


def fmt(m):
    return (f"Sharpe {m['sharpe']:.2f} | CAGR {pct(m['cagr'])} | maxDD {pct(m['max_dd'])} | "
            f"PF {m['profit_factor']:.2f} | changes {m['n_changes']} | exposure {m['avg_exposure']:.2f}")


def main():
    print("[1/4] loading crypto panel ...")
    crypto = panel(binance_daily, CRYPTO, start="2018-01-01", end=TODAY)
    crypto = crypto.sort_index()
    print("crypto:", crypto.shape, crypto.index.min(), crypto.index.max())
    c_rets = crypto.pct_change().dropna(how="all")

    print("[2/4] loading ETF/equity panel ...")
    etf = panel(nasdaq_daily, ETFS, start="2016-01-01", end=TODAY)
    etf = etf.sort_index()
    eq = panel(nasdaq_daily, EQUITY, start="2016-01-01", end=TODAY)
    eq = eq.sort_index()
    print("etf:", etf.shape, etf.index.min(), etf.index.max())
    print("eq:", eq.shape, eq.index.min(), eq.index.max())
    e_rets = etf.pct_change().dropna(how="all")
    q_rets = eq.pct_change().dropna(how="all")

    btc = crypto[["BTCUSDT"]]
    eth = crypto[["ETHUSDT"]]

    specs = [
        ("H1_BTC_TSMOM200", lambda: tsmom(btc, 200), c_rets, 10, 365, btc.notna().astype(float)),
        ("H2_ETH_TSMOM200", lambda: tsmom(eth, 200), c_rets, 10, 365, eth.notna().astype(float)),
        ("H3_XS_CRYPTO_MOM28_TOP3", lambda: xs_momentum(crypto, 28, 3), c_rets, 10, 365, buy_hold(crypto)),
        ("H4_CRYPTO_RSI2", lambda: rsi2(crypto[["BTCUSDT", "ETHUSDT", "SOLUSDT"]]), c_rets, 10, 365,
         buy_hold(crypto[["BTCUSDT", "ETHUSDT", "SOLUSDT"]])),
        ("H5_ETF_DUAL_MOM", lambda: dual_momentum(etf, ["SPY", "EFA", "AGG"], "BIL", 252), e_rets, 5, 252,
         fixed_mix(etf, {"SPY": 0.6, "AGG": 0.4})),
        ("H6_BTC_VOLSCALED_TSMOM", lambda: vol_scaled_tsmom(btc, 200, 20, 0.40, 1.5), c_rets, 10, 365,
         btc.notna().astype(float)),
        ("H7_EQUITY_RSI2", lambda: rsi2(eq[["SPY", "QQQ"]]), q_rets, 5, 252, buy_hold(eq)),
    ]

    print("[3/4] running candidates ...")
    results = []
    pvals = {}
    oos_matrix = {}
    for name, fn, rets, bps, ann, bench in specs:
        try:
            w = fn().reindex(index=rets.index, columns=rets.columns).fillna(0.0)
            r = evaluate(name, w, rets, bps, ann, bench, TRAIN_END, OOS_START)
            stress = evaluate(name, w, rets, bps * 2, ann, bench, TRAIN_END, OOS_START)
            r["stress_oos"] = stress["oos"]
            r["dsr"] = deflated_sharpe(r["oos_returns"], len(specs))
            pvals[name] = r["pvalue_oos"]
            oos_matrix[name] = r["oos_returns"]
            r.pop("oos_returns", None)
            r.pop("oos_weights", None)
            r.pop("stress_oos_returns", None) if "stress_oos_returns" in r else None
            results.append(r)
            print(f"  {name}: OOS {fmt(r['oos'])} | DSR {r['dsr']:.3f} | p {r['pvalue_oos']:.3g}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: FAILED {exc}")
            results.append({"name": name, "error": str(exc)})

    print("[4/4] validation ...")
    if oos_matrix:
        pd.concat(oos_matrix, axis=1).to_csv(RUN / "oos_returns.csv")
    mt = multiple_testing(pvals)
    # PBO needs a common calendar; use the crypto candidates only (same 365-day calendar).
    crypto_names = [n for n in oos_matrix if n.startswith(("H1", "H2", "H3", "H4", "H6"))]
    pbo = float("nan")
    if len(crypto_names) >= 4:
        mat = pd.concat({n: oos_matrix[n] for n in crypto_names}, axis=1).dropna()
        pbo = pbo_cscv(mat, n_blocks=16)
    etf_names = [n for n in oos_matrix if n.startswith(("H5", "H7"))]
    pbo_etf = float("nan")
    if len(etf_names) >= 4:
        mat = pd.concat({n: oos_matrix[n] for n in etf_names}, axis=1).dropna()
        pbo_etf = pbo_cscv(mat, n_blocks=16)

    pbo_by = {}
    for n in crypto_names:
        pbo_by[n] = pbo
    for n in etf_names:
        pbo_by[n] = pbo_etf

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
        pc = pbo_by.get(r["name"], float("nan"))
        if pc == pc and not (pc < 0.5): fails.append("pbo>=0.5")
        gates.append({"name": r["name"], "status": "PROVED" if not fails else "NOT_PROVED",
                      "fails": fails, "dsr": r["dsr"], "pvalue": r["pvalue_oos"], "pbo": pc})

    out = {
        "version": "v1",
        "run_at": pd.Timestamp.utcnow().isoformat(),
        "train_end": TRAIN_END, "oos_start": OOS_START,
        "n_candidates": len(specs),
        "multiple_testing": mt,
        "pbo_crypto": pbo, "pbo_etf": pbo_etf,
        "gates": gates,
        "results": results,
    }
    (RUN / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote", RUN / "results.json")

    lines = ["# v1 Results", "",
             f"Run: {out['run_at']} | train ≤{TRAIN_END} | OOS ≥{OOS_START} | N={len(specs)}", "",
             "## Verdict", ""]
    proved = [g for g in gates if g["status"] == "PROVED"]
    lines.append(f"**{len(proved)}/{len(specs)} candidates passed all gates.**" if proved else
                 "**0 candidates passed all gates — NOT PROVED.**")
    lines += ["", "| Candidate | OOS Sharpe | OOS CAGR | Bench Sharpe | OOS changes | DSR | p | Status |",
              "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"| {r['name']} | — | — | — | — | — | — | ERROR |")
            continue
        lines.append(f"| {r['name']} | {r['oos']['sharpe']:.2f} | {pct(r['oos']['cagr'])} | "
                     f"{r['benchmark_oos']['sharpe']:.2f} | {r['oos']['n_changes']} | "
                     f"{r['dsr']:.3f} | {r['pvalue_oos']:.3g} | {g['status']} |")
    lines += ["", "## Per-candidate detail", ""]
    for r, g in zip(results, gates):
        if "oos" not in r:
            lines.append(f"### {r['name']} — ERROR\n\n`{r.get('error')}`\n")
            continue
        lines += [f"### {r['name']} — {g['status']}", "",
                  f"- Train: {fmt(r['train'])}",
                  f"- OOS: {fmt(r['oos'])}",
                  f"- Benchmark OOS: {fmt(r['benchmark_oos'])}",
                  f"- Bootstrap OOS: p05 {r['bootstrap_oos']['p05']:.2f}, p95 {r['bootstrap_oos']['p95']:.2f}",
                  f"- 2x cost OOS Sharpe: {r['stress_oos']['sharpe']:.2f}",
                  f"- Failures: {', '.join(g.get('fails', [])) or 'none'}", ""]
    lines += ["## Multiple testing", "", f"```json\n{json.dumps(mt, indent=2, default=str)}\n```",
              "", f"PBO (crypto candidates): {pbo}", f"PBO (ETF candidates): {pbo_etf}"]
    (RUN / "REPORT.md").write_text("\n".join(lines))
    print("wrote", RUN / "REPORT.md")


if __name__ == "__main__":
    main()

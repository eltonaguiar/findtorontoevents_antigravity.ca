"""Robustness checks for the v2 provisional winner H10 (SPY/QQQ RSI2 + T-bill cash).

Checks: dividend fairness, subperiods, parameter stability (train-only), cash-yield and cost
sensitivity, risk-matched benchmark, extra-lag lookahead test.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import evaluate, metrics, portfolio_returns
from data.loader import nasdaq_daily, panel, treasury_bill_daily
from strategies import buy_hold, rsi2_cash

HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "v2"
RUN.mkdir(parents=True, exist_ok=True)
TRAIN_END, OOS_START = "2023-12-31", "2024-01-01"
CORE = ["SPY", "QQQ"]


def cash_returns(idx, tb):
    rate = tb["rate"].reindex(idx, method="ffill").ffill().bfill()
    return (rate / 100.0 / 252.0).fillna(0.0)


def mdict(ret, ann=252):
    m = metrics(ret, ann)
    return {k: getattr(m, k) for k in m.__dataclass_fields__}


def main():
    core = panel(nasdaq_daily, CORE, start="2016-01-01", end="2026-11-14").sort_index()
    tb = treasury_bill_daily(2018, 2026)
    rets = core.pct_change()
    rets["CASH"] = cash_returns(core.index, tb)
    rets = rets.dropna(how="all")

    w = rsi2_cash(core, cash_returns(core.index, tb))
    w = w.reindex(index=rets.index, columns=rets.columns).fillna(0.0)
    port, _ = portfolio_returns(w, rets, 5.0)
    bench, _ = portfolio_returns(buy_hold(core), rets, 0.0)
    oos = port.loc[OOS_START:]
    b_oos = bench.loc[OOS_START:]

    out = {"h10": {"train": mdict(port.loc[:TRAIN_END]), "oos": mdict(oos)},
           "benchmark": {"train": mdict(bench.loc[:TRAIN_END]), "oos": mdict(b_oos)}}

    # 1. Dividends: add approximate annual yields to risk returns (fair to both),
    # and a benchmark-only variant (conservative for the strategy).
    div = {"SPY": 0.013, "QQQ": 0.006}
    rets_div = rets.copy()
    for sym, y in div.items():
        rets_div[sym] = rets_div[sym] + y / 252.0
    port_div, _ = portfolio_returns(w, rets_div, 5.0)
    bench_div, _ = portfolio_returns(buy_hold(core), rets_div, 0.0)
    out["dividends_fair"] = {"oos": mdict(port_div.loc[OOS_START:]), "bench_oos": mdict(bench_div.loc[OOS_START:])}

    # 2. Subperiods
    years = {}
    for y in range(2018, 2027):
        p = port.loc[f"{y}-01-01":f"{y}-12-31"]
        b = bench.loc[f"{y}-01-01":f"{y}-12-31"]
        if len(p) > 20:
            years[str(y)] = {"h10": mdict(p), "bench": mdict(b)}
    out["yearly"] = years

    # 3. Parameter stability (train only for selection; OOS shown for transparency)
    grid = []
    for entry in (5.0, 10.0, 15.0):
        for exit_level in (40.0, 50.0, 60.0):
            for hold in (3, 5, 7):
                ww = rsi2_cash(core, cash_returns(core.index, tb), entry, exit_level, hold)
                ww = ww.reindex(index=rets.index, columns=rets.columns).fillna(0.0)
                pp, _ = portfolio_returns(ww, rets, 5.0)
                grid.append({"entry": entry, "exit": exit_level, "max_hold": hold,
                             "train_sharpe": float(metrics(pp.loc[:TRAIN_END], 252).sharpe),
                             "oos_sharpe": float(metrics(pp.loc[OOS_START:], 252).sharpe)})
    out["parameter_grid_train_only"] = grid

    # 4. Cash-yield and cost sensitivity
    sens = []
    for label, cret in (("no_cash", 0.0), ("half_cash", 0.5), ("actual", 1.0), ("cash_plus_1pct", 1.0 + 0.01)):
        r2 = rets.copy()
        r2["CASH"] = cash_returns(core.index, tb) * (cret if label != "cash_plus_1pct" else 1.0) + (0.01/252 if label == "cash_plus_1pct" else 0.0)
        pp, _ = portfolio_returns(w, r2, 5.0)
        sens.append({"case": label, "oos_sharpe": float(metrics(pp.loc[OOS_START:], 252).sharpe),
                     "oos_cagr": float(metrics(pp.loc[OOS_START:], 252).cagr)})
    out["cash_yield_sensitivity"] = sens
    costs = []
    for bps in (5, 10, 20, 30):
        pp, _ = portfolio_returns(w, rets, bps)
        costs.append({"bps": bps, "oos_sharpe": float(metrics(pp.loc[OOS_START:], 252).sharpe),
                      "oos_cagr": float(metrics(pp.loc[OOS_START:], 252).cagr)})
    out["cost_sensitivity"] = costs

    # 5. Risk-matched benchmark: 17.3% core / 82.7% cash, daily rebalanced
    expo = float(w.drop(columns=["CASH"]).sum(axis=1).mean())
    rm = buy_hold(core) * expo
    rm["CASH"] = 1.0 - expo
    rm_port, _ = portfolio_returns(rm.reindex(index=rets.index, columns=rets.columns).fillna(0.0), rets, 0.0)
    out["risk_matched_benchmark"] = {"exposure": expo, "oos": mdict(rm_port.loc[OOS_START:])}

    # 6. Extra-lag lookahead test: shift targets by 2 days instead of 1
    w2 = w.shift(2).fillna(0.0)
    lag2, _ = portfolio_returns(w2, rets, 5.0)
    out["lag2_oos"] = mdict(lag2.loc[OOS_START:])

    # 7. Trade stats
    rw = w.drop(columns=["CASH"]).reindex(oos.index).fillna(0.0)
    entries = int(((rw > 0) & (rw.shift(1).fillna(0) <= 0)).sum().sum())
    out["trade_stats"] = {"entries": entries, "changes": int((rw.diff().abs().sum(axis=1) > 1e-9).sum())}

    (RUN / "robustness.json").write_text(json.dumps(out, indent=2, default=float))

    lines = ["# H10 Robustness", "",
             f"## Baseline OOS", f"- H10: {out['h10']['oos']['sharpe']:.2f} Sharpe, {out['h10']['oos']['cagr']*100:.1f}% CAGR, {out['h10']['oos']['max_dd']*100:.1f}% maxDD",
             f"- Benchmark: {out['benchmark']['oos']['sharpe']:.2f} Sharpe, {out['benchmark']['oos']['cagr']*100:.1f}% CAGR, {out['benchmark']['oos']['max_dd']*100:.1f}% maxDD",
             "", "## Dividend fairness", f"- Fair (div added to both): H10 {out['dividends_fair']['oos']['sharpe']:.2f} vs bench {out['dividends_fair']['bench_oos']['sharpe']:.2f}; CAGR {out['dividends_fair']['oos']['cagr']*100:.1f}% vs {out['dividends_fair']['bench_oos']['cagr']*100:.1f}%",
             "", "## Yearly", "| Year | H10 Sharpe | H10 CAGR | Bench Sharpe | Bench CAGR |", "|---|---:|---:|---:|---:|"]
    for y, v in years.items():
        lines.append(f"| {y} | {v['h10']['sharpe']:.2f} | {v['h10']['cagr']*100:.1f}% | {v['bench']['sharpe']:.2f} | {v['bench']['cagr']*100:.1f}% |")
    lines += ["", "## Parameter grid (train selection; OOS shown for transparency)", "| entry | exit | hold | train Sharpe | OOS Sharpe |", "|---:|---:|---:|---:|---:|"]
    for g in grid:
        lines.append(f"| {g['entry']} | {g['exit']} | {g['max_hold']} | {g['train_sharpe']:.2f} | {g['oos_sharpe']:.2f} |")
    lines += ["", "## Cash / cost sensitivity", "| case | OOS Sharpe | OOS CAGR |", "|---|---:|---:|"]
    for s in sens:
        lines.append(f"| {s['case']} | {s['oos_sharpe']:.2f} | {s['oos_cagr']*100:.1f}% |")
    for c in costs:
        lines.append(f"| cost {c['bps']}bps | {c['oos_sharpe']:.2f} | {c['oos_cagr']*100:.1f}% |")
    lines += ["", f"## Risk-matched benchmark ({expo*100:.1f}% core / {100-expo*100:.1f}% cash)",
              f"- {out['risk_matched_benchmark']['oos']['sharpe']:.2f} Sharpe, {out['risk_matched_benchmark']['oos']['cagr']*100:.1f}% CAGR, {out['risk_matched_benchmark']['oos']['max_dd']*100:.1f}% maxDD",
              "", "## Extra-lag test (targets shifted 2 days)", f"- {out['lag2_oos']['sharpe']:.2f} Sharpe, {out['lag2_oos']['cagr']*100:.1f}% CAGR",
              "", "## Trade stats", f"- {out['trade_stats']}"]
    (RUN / "ROBUSTNESS.md").write_text("\n".join(lines))
    print("wrote", RUN / "ROBUSTNESS.md")


if __name__ == "__main__":
    main()

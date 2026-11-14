"""v4: crypto funding-rate carry (delta-neutral spot/perp)."""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import deflated_sharpe, metrics, portfolio_returns, block_bootstrap_sharpe
from data.loader import binance_funding, treasury_bill_daily
from strategies import buy_hold

HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "v4"
RUN.mkdir(parents=True, exist_ok=True)
TRAIN_START, TRAIN_END, OOS_START = "2020-01-01", "2023-12-31", "2024-01-01"
TODAY = date.today().isoformat()

CRYPTO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
          "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT", "TRXUSDT", "ATOMUSDT",
          "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT", "TIAUSDT",
          "SEIUSDT", "RUNEUSDT", "AAVEUSDT", "UNIUSDT", "MKRUSDT", "CRVUSDT", "COMPUSDT",
          "SNXUSDT", "ETCUSDT"]


def cash_returns(idx, tb):
    rate = tb["rate"].reindex(idx, method="ffill").ffill().bfill()
    return (rate / 100.0 / 365.0).fillna(0.0)


def funding_panel(start="2020-01-01", end=None):
    end = end or TODAY
    frames = {}
    for sym in CRYPTO:
        try:
            f = binance_funding(sym, start=start, end=end)
            daily = f["rate"].groupby(f.index.normalize()).sum()
            frames[sym] = daily
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] funding {sym}: {exc}")
    panel = pd.concat(frames, axis=1).sort_index()
    idx = pd.date_range(panel.index.min(), panel.index.max(), freq="D")
    return panel.reindex(idx).fillna(0.0)


def carry_weights(funding: pd.DataFrame, lookback=21, top=5, freq="W-FRI") -> pd.DataFrame:
    sig = funding.rolling(lookback, min_periods=lookback).mean()
    idx = funding.index
    rebal = pd.Series(idx, index=idx).groupby(idx.to_period(freq)).max()
    rows = {}
    for d in rebal:
        valid = sig.loc[d].dropna()
        valid = valid[valid > 0]
        cur = pd.Series(0.0, index=funding.columns)
        k = min(top, len(valid))
        if k > 0:
            sel = valid.nlargest(k).index
            cur[sel] = 1.0 / k
        rows[d] = cur
    w = pd.DataFrame(rows).T.reindex(idx).ffill().fillna(0.0)
    w["CASH"] = (1.0 - w.sum(axis=1)).clip(lower=0.0)
    return w


def btc_carry_weights(funding: pd.DataFrame) -> pd.DataFrame:
    sig = funding["BTCUSDT"].rolling(21, min_periods=21).mean()
    w = pd.DataFrame(0.0, index=funding.index, columns=funding.columns)
    w["BTCUSDT"] = (sig > 0).astype(float).fillna(0.0)
    w["CASH"] = 1.0 - w["BTCUSDT"]
    return w


def walk_forward(port, years, ann=365):
    parts = [port.loc[f"{y}-01-01":f"{y}-12-31"] for y in years]
    parts = [p for p in parts if len(p) > 20]
    if not parts:
        return metrics(pd.Series(dtype=float), ann)
    return metrics(pd.concat(parts), ann)


def pct(x):
    return "nan" if x != x else f"{x*100:.1f}%"


def md(series, w=None, turn=None, ann=365):
    m = metrics(series, ann, w, turn)
    return {k: getattr(m, k) for k in m.__dataclass_fields__}


CAPITAL_MULT = 1.5  # 1x spot + ~0.5x perp margin


def main():
    print("[1/3] data ...")
    tb = treasury_bill_daily(2019, int(TODAY[:4]))
    funding = funding_panel()
    print("funding panel", funding.shape, funding.index.min(), funding.index.max())
    rets = funding.copy()
    rets["CASH"] = cash_returns(rets.index, tb)

    cash_w = pd.DataFrame(0.0, index=rets.index, columns=rets.columns)
    cash_w["CASH"] = 1.0

    specs = [
        ("H21_FUNDING_TOP5", carry_weights(funding, 21, 5), 10),
        ("H22_FUNDING_BTC", btc_carry_weights(funding), 10),
        ("H23_FUNDING_TOP10", carry_weights(funding, 21, 10), 10),
    ]

    print("[2/3] running ...")
    results, pvals, full, oos_series = [], {}, {}, {}
    CUM_N = 23
    for name, w, bps in specs:
        w = w.reindex(index=rets.index, columns=rets.columns).fillna(0.0)
        port, turn = portfolio_returns(w, rets, bps)
        stress, turn_s = portfolio_returns(w, rets, bps * 2)
        lag_w = w.shift(5).fillna(0.0)
        lag, turn_l = portfolio_returns(lag_w, rets, bps)
        bench, _ = portfolio_returns(cash_w, rets, 0.0)
        port_cap = port / CAPITAL_MULT
        tr = port.loc[TRAIN_START:TRAIN_END]
        oo = port.loc[OOS_START:]
        wf = walk_forward(port, range(2021, 2027))
        bf = walk_forward(bench, range(2021, 2027))
        r = {
            "name": name, "cost_bps": bps, "capital_mult": CAPITAL_MULT,
            "train": md(tr, w.loc[tr.index], turn.loc[tr.index]),
            "oos": md(oo, w.loc[oo.index], turn.loc[oo.index]),
            "capital_adjusted_oos": md(port_cap.loc[OOS_START:], w.loc[OOS_START:], turn.loc[OOS_START:]),
            "cash_oos": md(bench.loc[OOS_START:], cash_w.loc[OOS_START:]),
            "walk_forward": {k: getattr(wf, k) for k in wf.__dataclass_fields__},
            "bench_walk_forward": {k: getattr(bf, k) for k in bf.__dataclass_fields__},
            "stress_oos": md(stress.loc[OOS_START:], w.loc[OOS_START:], turn_s.loc[OOS_START:]),
            "lag_oos": md(lag.loc[OOS_START:], lag_w.loc[OOS_START:], turn_l.loc[OOS_START:]),
            "bootstrap_oos": block_bootstrap_sharpe(oo, 365),
        }
        r["dsr"] = deflated_sharpe(oo, CUM_N)
        pvals[name] = r["oos"].get("sharpe", float("nan"))
        full[name] = port
        oos_series[name] = oo
        results.append(r)
        print(f"  {name}: OOS Sharpe {r['oos']['sharpe']:.2f} | CAGR {pct(r['oos']['cagr'])} | "
              f"cash CAGR {pct(r['cash_oos']['cagr'])} | cap/1.5 CAGR {pct(r['capital_adjusted_oos']['cagr'])} | WF {r['walk_forward']['sharpe']:.2f} | "
              f"DSR {r['dsr']:.3f}")

    print("[3/3] gates ...")
    gates = []
    for r in results:
        o, cash, s, lag = r["oos"], r["cash_oos"], r["stress_oos"], r["lag_oos"]
        fails = []
        if not (o["sharpe"] >= 1.0): fails.append("oos_sharpe<1.0")
        if not (o["cagr"] > cash["cagr"]): fails.append("cagr<=cash")
        if not (r["capital_adjusted_oos"]["cagr"] > cash["cagr"]): fails.append("capital_adjusted_cagr<=cash")
        if not (o["n_changes"] >= 30): fails.append("n_trades<30")
        if not (r["dsr"] >= 0.95): fails.append("dsr<0.95")
        if not (r["bootstrap_oos"]["p05"] > 0): fails.append("bootstrap_p05<=0")
        if not (s["sharpe"] >= 0.5): fails.append("2x_cost_fail")
        if not (lag["sharpe"] >= 1.0): fails.append("execution_lag_fail")
        gates.append({"name": r["name"], "status": "PASSED_GATES" if not fails else "NOT_PROVED",
                      "fails": fails, "dsr": r["dsr"]})

    out = {"version": "v4", "run_at": pd.Timestamp.utcnow().isoformat(),
           "train": [TRAIN_START, TRAIN_END], "oos_start": OOS_START,
           "n_v4": len(specs), "cumulative_n": CUM_N, "gates": gates, "results": results}
    (RUN / "results.json").write_text(json.dumps(out, indent=2, default=str))
    pd.concat(full, axis=1).to_csv(RUN / "full_returns.csv")
    pd.concat(oos_series, axis=1).to_csv(RUN / "oos_returns.csv")

    passed = [g for g in gates if g["status"] == "PASSED_GATES"]
    lines = ["# v4 Results — Crypto Funding Carry", "",
             f"Run: {out['run_at']} | train {TRAIN_START}..{TRAIN_END} | OOS ≥{OOS_START} | cumulative N={CUM_N}", "",
             f"**{len(passed)}/3 passed all v4 gates.**" if passed else "**0/3 passed all v4 gates — NOT PROVED.**", "",
             "| Candidate | OOS Sharpe | OOS CAGR | Cap/1.5 CAGR | Cash CAGR | WF Sharpe | DSR | 2x Sharpe | Lag Sharpe | Status |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r, g in zip(results, gates):
        lines.append(f"| {r['name']} | {r['oos']['sharpe']:.2f} | {pct(r['oos']['cagr'])} | "
                     f"{pct(r['capital_adjusted_oos']['cagr'])} | {pct(r['cash_oos']['cagr'])} | {r['walk_forward']['sharpe']:.2f} | "
                     f"{r['dsr']:.3f} | {r['stress_oos']['sharpe']:.2f} | {r['lag_oos']['sharpe']:.2f} | {g['status']} |")
    lines += ["", "## Detail", ""]
    for r, g in zip(results, gates):
        lines += [f"### {r['name']} — {g['status']}", "",
                  f"- OOS: Sharpe {r['oos']['sharpe']:.2f}, CAGR {pct(r['oos']['cagr'])}, maxDD {pct(r['oos']['max_dd'])}, changes {r['oos']['n_changes']}, exposure {r['oos']['avg_exposure']:.2f}",
                  f"- Cash benchmark OOS: CAGR {pct(r['cash_oos']['cagr'])}; capital-adjusted CAGR {pct(r['capital_adjusted_oos']['cagr'])} (capital x{r['capital_mult']})",
                  f"- Walk-forward: Sharpe {r['walk_forward']['sharpe']:.2f}",
                  f"- DSR (N=23) {r['dsr']:.3f}; bootstrap p05 {r['bootstrap_oos']['p05']:.2f}",
                  f"- 2x cost Sharpe {r['stress_oos']['sharpe']:.2f}; 5-day lag Sharpe {r['lag_oos']['sharpe']:.2f}",
                  f"- Failures: {', '.join(g.get('fails', [])) or 'none'}", ""]
    (RUN / "REPORT.md").write_text("\n".join(lines))
    print("wrote", RUN / "REPORT.md")


if __name__ == "__main__":
    main()

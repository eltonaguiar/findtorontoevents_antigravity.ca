"""H-234: which half of its own sample does H-201's +7.246 bp/day come from?

Pre-registered: plans/2026-11-23-prereg-H-234-h201-two-window.md
Constructs the cell with the harness's own code -- no retuning, no parameter change.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from per_class_edge_harness import fetch, xsmom, block_bootstrap, monthly_trades, UNIVERSES, BENCH_SYMBOL

WINDOWS = {"A_2012_2019": ("2012-01-01", "2019-06-30"),
           "B_2019_2026": ("2019-07-01", "2026-12-31"),
           "FULL": ("2012-01-01", "2026-12-31")}
LOOK, TOPK, COST, REBAL = 126, 3, 10, 21

def stats(x: np.ndarray, b: np.ndarray) -> dict:
    lo, hi = block_bootstrap(x)
    d = x - b
    dlo, _ = block_bootstrap(d)
    h = len(x) // 2
    return {"n_days": int(len(x)),
            "mean_bps": round(1e4 * float(x.mean()), 3),
            "ci_lb_bps": round(1e4 * float(lo), 3),
            "ci_ub_bps": round(1e4 * float(hi), 3),
            "excess_bps": round(1e4 * float(d.mean()), 3),
            "excess_ci_lb_bps": round(1e4 * float(dlo), 3),
            "halves_bps": [round(1e4 * float(x[:h].mean()), 3), round(1e4 * float(x[h:].mean()), 3)],
            "pos_mean": bool(x.mean() > 0), "pos_ci": bool(lo > 0), "pos_excess": bool(d.mean() > 0)}

def main() -> None:
    syms = UNIVERSES["EQUITY"]
    data = {}
    for s in syms:
        df = fetch(s)
        if df is not None and len(df) > 200:
            data[s] = df
    closes = pd.concat({s: d["close"] for s, d in data.items()}, axis=1).dropna(how="all")
    bdf = fetch(BENCH_SYMBOL["EQUITY"])
    bench = bdf["close"].pct_change().fillna(0.0)
    net, w = xsmom(closes, LOOK, TOPK, COST, REBAL)
    print(f"universe {len(data)}/{len(syms)}  sample {closes.index[0].date()}..{closes.index[-1].date()}  bars={len(closes)}")
    out = {"hypothesis": "H-234", "prereg": "plans/2026-11-23-prereg-H-234-h201-two-window.md",
           "construction": {"lookback": LOOK, "top_k": TOPK, "cost_bps": COST, "rebal_days": REBAL,
                            "universe": sorted(data), "bench": BENCH_SYMBOL["EQUITY"]},
           "sample": {"start": str(closes.index[0].date()), "end": str(closes.index[-1].date()), "bars": int(len(closes))},
           "windows": {}}
    for name, (s, e) in WINDOWS.items():
        m = (net.index >= pd.Timestamp(s)) & (net.index <= pd.Timestamp(e))
        x = net[m].to_numpy(dtype=float)
        b = bench.reindex(net.index[m]).fillna(0.0).to_numpy(dtype=float)
        if len(x) < 100:
            out["windows"][name] = {"error": "insufficient", "n": int(len(x))}; continue
        st = stats(x, b); out["windows"][name] = st
        print(f"{name:<14} n={st['n_days']:4d} mean {st['mean_bps']:>8.3f}bp CI [{st['ci_lb_bps']:>8.3f},"
              f"{st['ci_ub_bps']:>8.3f}] excess {st['excess_bps']:>8.3f}bp halves {st['halves_bps']}")
    acc = [k for k in ("A_2012_2019", "B_2019_2026")]
    good = [k for k in acc if out["windows"].get(k, {}).get("pos_mean")
            and out["windows"][k].get("pos_ci") and out["windows"][k].get("pos_excess")]
    verdict = "ROBUST" if len(good) == 2 else ("HALF_DEPENDENT" if len(good) == 1 else "FRAGILE")
    out["verdict"] = {"label": verdict, "windows_passing_all_three": good,
                      "full_sample_reproduces_ci_lb": out["windows"].get("FULL", {}).get("ci_lb_bps")}
    print(f"windows passing all three criteria: {good} -> {verdict}")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/h234_h201_two_window_2026-11-23.json").write_text(json.dumps(out, indent=2) + "\n")
    print("wrote reports/h234_h201_two_window_2026-11-23.json")

if __name__ == "__main__":
    main()

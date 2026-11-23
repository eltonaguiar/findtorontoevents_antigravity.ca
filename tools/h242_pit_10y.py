#!/usr/bin/env python3
"""H-242: does the 44-name H-201 edge survive a 10-year window?

Pre-registered 2026-11-23 in plans/2026-11-23-prereg-H-242-pit-10y-extension.md BEFORE this file was
first run.

WHY
    H-241 showed the delisting stress is 1.27bp/day against a 12.673bp CI half-width, so H-201's
    blocker is the LENGTH of the sample, not the delisting flag. This spends the extension that
    already exists: the 44-name universe has 10 years of daily bars available, while the published
    H-236 test used only the 5-year slice.

DESIGN
    Same universe (44 names), same rule (xsmom 126 / top-3 / 21d / 10bp per side), same estimator.
    Only the window changes. The W5 control MUST reproduce H-236's published 9.407bp/day and
    -3.147bp CI-LB, otherwise the pipeline differs and the run is INVALID.

Read-only. Paper only. Not investment advice.

Usage:
    python3 tools/h242_pit_10y.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from per_class_edge_harness import fetch, xsmom, block_bootstrap, BENCH_SYMBOL  # noqa: E402

LOOK, TOPK, COST, REBAL = 126, 3, 10, 21
OUT = ROOT / "reports" / "h242_pit_10y_2026-11-23.json"
PIT = ROOT / "reports" / "pit_equity_universe_20261122.json"
H236 = ROOT / "reports" / "h236_h201_pit_universe_2026-11-23.json"
W5 = ("2021-11-22", "2026-11-19")


def stats(x: np.ndarray, b: np.ndarray) -> dict:
    lo, hi = block_bootstrap(x)
    dlo, _ = block_bootstrap(x - b)
    return {"n": int(len(x)), "mean_bps": round(1e4 * float(x.mean()), 3),
            "ci_lb_bps": round(1e4 * lo, 3), "ci_ub_bps": round(1e4 * hi, 3),
            "ci_width_bps": round(1e4 * (hi - lo), 3),
            "excess_bps": round(1e4 * float((x - b).mean()), 3),
            "excess_ci_lb_bps": round(1e4 * dlo, 3)}


def main() -> int:
    pit = json.loads(PIT.read_text())
    names = pit["universe"]

    cols = {}
    for s in names:
        df = fetch(s)
        if df is not None and len(df) > 200 and "close" in df.columns:
            cols[s] = df["close"]
    closes = pd.concat(cols, axis=1).dropna(how="all")
    bench = fetch(BENCH_SYMBOL["EQUITY"])["close"].pct_change().fillna(0.0)

    span = (closes.index[0].date().isoformat(), closes.index[-1].date().isoformat())
    print(f"44-name panel: {closes.shape[0]} bars x {closes.shape[1]} names {span}", flush=True)
    if closes.index[0] > pd.Timestamp("2017-06-01"):
        print("  ! cache starts after 2017 - the 10-year window is NOT available; aborting", flush=True)
        return 2

    net, _ = xsmom(closes, LOOK, TOPK, COST, REBAL)
    prints = {}

    def window(a: str, b: str) -> dict:
        m = (net.index >= pd.Timestamp(a)) & (net.index <= pd.Timestamp(b))
        x = net[m].to_numpy(dtype=float)
        bb = bench.reindex(net.index[m]).fillna(0.0).to_numpy(dtype=float)
        if len(x) < 250:
            return {"error": "insufficient", "n": int(len(x))}
        st = stats(x, bb)
        st["window"] = [a, b]
        return st

    # The pre-registered window is 2016-11-21 .. 2026-11-20. The cached panel happens to start
    # 2012-01-03, which is MORE data than registered - that is reported as W10_FULL and is never
    # allowed to substitute for the registered window, because a wider window chosen after seeing
    # the cache is exactly the kind of substitution pre-registration exists to prevent.
    prints["W10"] = window("2016-11-21", "2026-11-20")
    prints["W10_FULL"] = window(span[0], span[1])
    prints["W5"] = window(*W5)

    published = json.loads(H236.read_text())["books"]["PIT_44"]
    ctrl = prints["W5"]
    reproduced = (abs(ctrl.get("mean_bps", 1e9) - published["mean_bps"]) < 0.01
                  and abs(ctrl.get("ci_lb_bps", 1e9) - published["ci_lb_bps"]) < 0.01)

    w10 = prints["W10"]
    if not reproduced:
        verdict, why = "INVALID", "W5 control did not reproduce H-236"
    elif w10.get("ci_ub_bps", 0) <= 0:
        verdict, why = "REFUTED", "W10 CI upper bound <= 0"
    elif w10.get("ci_lb_bps", -1) > 0:
        narrower = (w10["ci_width_bps"] <= 0.75 * ctrl["ci_width_bps"])
        verdict = "WIDENS_OR_HOLDS" if narrower else "PASSED_BUT_INTERVAL_NOT_NARROWER"
        why = f"W10 CI-LB > 0; width {w10['ci_width_bps']}bp vs W5 {ctrl['ci_width_bps']}bp"
    else:
        verdict, why = "STILL_UNRESOLVED", "more history, same verdict: the interval still spans zero"

    out = {
        "hypothesis": "H-242",
        "prereg": "plans/2026-11-23-prereg-H-242-pit-10y-extension.md",
        "generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": {"xsmom_lookback": LOOK, "top_k": TOPK, "rebal_days": REBAL,
                 "cost_bps_per_side": COST, "benchmark": "SPY"},
        "universe": {"n": int(closes.shape[1]), "source": "reports/pit_equity_universe_20261122.json",
                      "span": list(span), "flag": "BOUNDED (unchanged; a longer window is not a clean universe)"},
        "books": prints,
        "control": {"published_h236": {"mean_bps": published["mean_bps"],
                                        "ci_lb_bps": published["ci_lb_bps"], "n": published["n"]},
                     "recomputed_W5": {"mean_bps": ctrl.get("mean_bps"),
                                        "ci_lb_bps": ctrl.get("ci_lb_bps"), "n": ctrl.get("n")},
                     "reproduced": bool(reproduced)},
        "informational_full_cache_window": {
            "note": "the cached panel starts 2012-01-03 (14y), more history than the registered 10y; "
                    "reported for context only, the verdict uses the registered window",
            "result": prints["W10_FULL"]},
        "intervals": {"w5_width_bps": ctrl.get("ci_width_bps"),
                       "w10_width_bps": w10.get("ci_width_bps"),
                       "narrowing_ratio": (round(w10["ci_width_bps"] / ctrl["ci_width_bps"], 3)
                                            if ctrl.get("ci_width_bps") else None),
                       "sqrt_of_time_expectation": 0.5},
        "verdict": {"label": verdict, "why": why,
                     "period_dependence_warning": (
                         "a W10 pass while W5 failed is PERIOD-DEPENDENT and must be reported with "
                         "both numbers; it does not make H-201 investable")},
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")

    for k in ("W10", "W5"):
        s = prints[k]
        print(f"{k}: n={s.get('n')} mean {s.get('mean_bps')}bp CI"
              f"[{s.get('ci_lb_bps')},{s.get('ci_ub_bps')}] width {s.get('ci_width_bps')}bp "
              f"excess {s.get('excess_bps')}", flush=True)
    print(f"control reproduced={reproduced} | VERDICT: {verdict} - {why}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

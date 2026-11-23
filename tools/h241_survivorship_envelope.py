#!/usr/bin/env python3
"""H-241: can H-201 be re-read without the delisting flag?

WHY THIS FILE EXISTS
    H-201's universe (reports/pit_equity_universe_20261122.json, 44 names) is stamped
    PARTIAL_NON_DELISTING_AWARE: it contains additions but ZERO removals. The clean fix is
    to procure delisted prices. That procurement was attempted and FAILED on 2026-11-23 -
    Yahoo purges dead tickers (30 of 37 known dead names return no data) and Stooq now
    serves a JavaScript proof-of-work challenge instead of CSV. So this tool does the
    second-best thing, pre-registered in plans/2026-11-23-prereg-H-241-survivorship-envelope.md:
    instead of removing the bias, BOUND it.

WHAT IT DOES
    Runs H-201's own rule (xsmom lookback=126, top_k=3, rebal=21, 10bp/side) on the 44-name PIT
    book. Then, on a fixed grid of (annual delisting hazard x terminal haircut), injects synthetic
    delistings: at each rebalance, each SELECTED holding dies with probability
    hazard_annual*21/252; a dead holding earns `haircut` for that holding period instead of its
    realised return, and is re-selected normally afterwards (the next path replays the same dates).

    Only names that are HELD can hurt a long-only top-3 book, and momentum selection is precisely
    what buys a name just before it dies - so the injection targets the holdings, not the universe.

WHAT IT REFUSES TO CLAIM
    This is NOT delisting-aware data. It cannot upgrade H-201's flag past BOUNDED, and it does not
    turn a survivor-conditioned universe into a clean one. The baseline cell (0% hazard) must
    reproduce the published 44-name result exactly or the whole run is INVALID.

Read-only. Paper only. Not investment advice.

Usage:
    python3 tools/h241_survivorship_envelope.py
    python3 tools/h241_survivorship_envelope.py --paths 200 --seed 241
"""
from __future__ import annotations

import argparse
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
OUT = ROOT / "reports" / "h241_survivorship_envelope_2026-11-23.json"
PIT = ROOT / "reports" / "pit_equity_universe_20261122.json"
PUBLISHED_H236 = ROOT / "reports" / "h236_h201_pit_universe_2026-11-23.json"

HAZARDS = [0.00, 0.02, 0.04, 0.06, 0.10]
HAIRCUTS = [-0.30, -0.50, -0.70]


def load_book(names: list[str]) -> pd.DataFrame:
    cols = {}
    for s in names:
        df = fetch(s)
        if df is not None and len(df) > 200 and "close" in df.columns:
            cols[s] = df["close"]
    if not cols:
        raise SystemExit("NO symbols loaded - refusing to invent a book")
    return pd.concat(cols, axis=1).dropna(how="all")


def build(paths: int, seed: int):
    pit = json.loads(PIT.read_text())
    names, w = pit["universe"], pit["window"]
    s0, e0 = pd.Timestamp(w["start"]), pd.Timestamp(w["end"])

    closes = load_book(names)
    bench_df = fetch(BENCH_SYMBOL["EQUITY"])
    bench = bench_df["close"].pct_change().fillna(0.0)

    net, weights = xsmom(closes, LOOK, TOPK, COST, REBAL)
    mask = (net.index >= s0) & (net.index <= e0)
    base = net[mask]
    b = bench.reindex(base.index).fillna(0.0)

    lo, hi = block_bootstrap(base.to_numpy(dtype=float))
    dlo, _ = block_bootstrap(base.to_numpy(dtype=float) - b.to_numpy(dtype=float))
    baseline = {
        "n_days": int(len(base)),
        "mean_bps": round(1e4 * float(base.mean()), 3),
        "ci_lb_bps": round(1e4 * lo, 3),
        "ci_ub_bps": round(1e4 * hi, 3),
        "excess_bps": round(1e4 * float((base - b).mean()), 3),
        "excess_ci_lb_bps": round(1e4 * dlo, 3),
        "symbols_loaded": int(closes.shape[1]),
        "window": w,
    }

    idx = list(base.index)
    pos = {ts: i for i, ts in enumerate(idx)}
    starts = [i for i in range(LOOK + 1, len(closes), REBAL)
              if closes.index[i] in pos and i + REBAL < len(closes)]
    held_at = {}
    for i in starts:
        r = weights.iloc[i]
        held = [c for c in r.index if r[c] > 0]
        if held:
            held_at[i] = held
    starts = sorted(held_at)

    # realised return of each holding over its own holding window
    realized = {}
    for i in starts:
        if i + REBAL >= len(closes):
            continue
        for c in held_at[i]:
            a, z = closes[c].iloc[i], closes[c].iloc[i + REBAL]
            if pd.notna(a) and pd.notna(z) and a > 0:
                realized[(i, c)] = float(z / a - 1.0)

    base_np = base.to_numpy(dtype=float)
    day_pos = {ts: k for k, ts in enumerate(base.index)}

    def one_path(hazard: float, haircut: float, rng: np.random.Generator) -> np.ndarray:
        adj = np.zeros(len(base_np))
        p = min(1.0, hazard * REBAL / 252.0 * TOPK)   # any of the 3 holdings dies
        for i in starts:
            if i + REBAL >= len(closes) or rng.random() >= p:
                continue
            c = held_at[i][int(rng.integers(0, len(held_at[i])))]
            r = realized.get((i, c))
            if r is None:
                continue
            delta = (haircut - r) / TOPK
            t0 = closes.index[i]
            t1 = closes.index[min(i + REBAL, len(closes) - 1)]
            if t0 not in day_pos or t1 not in day_pos:
                continue
            a, z = day_pos[t0], day_pos[t1]
            if z <= a:
                continue
            adj[a:z + 1] += delta / (z - a + 1)
        return base_np + adj

    grid = []
    for h in HAZARDS:
        for k in HAIRCUTS:
            if h == 0.0 and k != HAIRCUTS[0]:
                continue
            rng = np.random.default_rng(seed)
            series = np.stack([one_path(h, k, rng) for _ in range(paths)])
            mean_path = series.mean(axis=0)
            clo, chi = block_bootstrap(mean_path)
            pm = series.mean(axis=1)
            cell = {
                "hazard_annual": h, "haircut": k, "paths": paths,
                "mean_bps": round(1e4 * float(mean_path.mean()), 3),
                "ci_lb_bps": round(1e4 * clo, 3),
                "ci_ub_bps": round(1e4 * chi, 3),
                "frac_paths_mean_gt_0": round(float((pm > 0).mean()), 4),
                "path_mean_p05_bps": round(1e4 * float(np.quantile(pm, 0.05)), 3),
                "path_mean_p95_bps": round(1e4 * float(np.quantile(pm, 0.95)), 3),
                "ci_lb_gt_0": bool(clo > 0),
            }
            grid.append(cell)
            print(f"hazard {h:>4.0%} haircut {k:>5.0%}  mean {cell['mean_bps']:>8.3f}bp "
                  f"CI_LB {cell['ci_lb_bps']:>8.3f}  paths>0 {cell['frac_paths_mean_gt_0']:.2f}")
    return baseline, grid, len(starts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=200)
    ap.add_argument("--seed", type=int, default=241)
    a = ap.parse_args()

    baseline, grid, n_rebal = build(a.paths, a.seed)

    # REPRODUCTION is checked against the PUBLISHED H-236 artifact, not against this run's own
    # baseline cell - comparing a run to itself would always pass and prove nothing.
    published = json.loads(PUBLISHED_H236.read_text())
    pub = published["books"]["PIT_44"]
    repro = {
        "source": "reports/h236_h201_pit_universe_2026-11-23.json:books.PIT_44",
        "published": {"n": pub["n"], "mean_bps": pub["mean_bps"],
                       "ci_lb_bps": pub["ci_lb_bps"], "ci_ub_bps": pub["ci_ub_bps"]},
        "recomputed": {"n": baseline["n_days"], "mean_bps": baseline["mean_bps"],
                        "ci_lb_bps": baseline["ci_lb_bps"], "ci_ub_bps": baseline["ci_ub_bps"]},
        "match_mean": abs(pub["mean_bps"] - baseline["mean_bps"]) < 0.01,
        "match_ci_lb": abs(pub["ci_lb_bps"] - baseline["ci_lb_bps"]) < 0.01,
    }
    reproduces = bool(repro["match_mean"] and repro["match_ci_lb"])

    corner = next(g for g in grid if g["hazard_annual"] == 0.06 and g["haircut"] == -0.50)
    worst = grid[-1]
    breaking = [g for g in grid if g["hazard_annual"] > 0 and not g["ci_lb_gt_0"]]

    # The comparison that decides what the flag is worth: how big is the delisting stress
    # versus the sampling error already in the baseline? If the stress is small next to the
    # CI half-width, then delisting is not the binding uncertainty - the SHORT WINDOW is.
    ci_halfwidth = round((baseline["ci_ub_bps"] - baseline["ci_lb_bps"]) / 2.0, 3)
    stress_at_corner = round(baseline["mean_bps"] - corner["mean_bps"], 3)
    stress_at_worst = round(baseline["mean_bps"] - worst["mean_bps"], 3)

    verdict = ("INVALID" if not reproduces else
               "SURVIVES_SURVIVORSHIP_STRESS" if corner["ci_lb_gt_0"] else
               "NOT_SURVIVES")
    tolerated = [g for g in grid if g["ci_lb_gt_0"] and g["hazard_annual"] > 0]
    worst_ok = (max(tolerated, key=lambda g: (g["hazard_annual"], -abs(g["haircut"])))
                if tolerated else None)

    out = {
        "hypothesis": "H-241",
        "prereg": "plans/2026-11-23-prereg-H-241-survivorship-envelope.md",
        "generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "SYNTHETIC_DELISTING_ENVELOPE — NOT delisting-aware data",
        "rule": {"xsmom_lookback": LOOK, "top_k": TOPK, "rebal_days": REBAL,
                 "cost_bps_per_side": COST, "benchmark": "SPY"},
        "universe": {"source": "reports/pit_equity_universe_20261122.json",
                      "n": baseline["symbols_loaded"],
                      "flag": "PARTIAL_NON_DELISTING_AWARE (unchanged by this run)"},
        "delisted_price_procurement": {
            "status": "FAILED",
            "yahoo_yfinance": "30 of 37 known dead tickers return no data; the 7 that return "
                              "data are recycled live tickers, not delisted histories",
            "stooq": "HTTP 200 with a JavaScript proof-of-work challenge body, not CSV",
            "consequence": "delisted prices are not obtainable free; the bias is bounded, not removed",
        },
        "baseline": baseline,
        "reproduction": repro,
        "n_rebalances": n_rebal,
        "grid": grid,
        "stress_vs_sampling_error": {
            "baseline_ci_halfwidth_bps": ci_halfwidth,
            "delisting_stress_at_corner_bps": stress_at_corner,
            "delisting_stress_at_worst_bps": stress_at_worst,
            "stress_over_halfwidth": (round(stress_at_corner / ci_halfwidth, 4)
                                       if ci_halfwidth else None),
            "reading": ("the delisting stress is far smaller than the sampling error already in "
                        "the baseline, so the flag is not what blocks a verdict for this book"
                        if ci_halfwidth and stress_at_corner / ci_halfwidth < 0.5 else
                        "the delisting stress is of the same order as the sampling error, so the "
                        "flag has to be resolved before any verdict"),
        },
        "verdict": {
            "label": verdict,
            "baseline_reproduced": reproduces,
            "baseline_ci_lb_positive": bool(baseline["ci_lb_bps"] > 0),
            "pessimistic_corner": corner,
            "cells_whose_ci_lb_le_0": breaking,
            "max_tolerated_cell": worst_ok,
            "flag_after_run": "BOUNDED at best; never CLEAN",
            "binding_uncertainty": ("SAMPLING_ERROR (baseline CI spans zero over 5 years), not "
                                     "delisting bias" if not baseline["ci_lb_bps"] > 0 else
                                     "DELISTING (baseline significant, stress breaks it)"),
            "note": "a PASS here does not remove the delisting flag - it states the envelope the "
                    "edge tolerates. A FAIL here is a magnitude, not a new null; and when the "
                    "baseline CI already spans zero, the envelope cannot certify anything.",
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nVERDICT: {verdict}  (published H-236 reproduced={reproduces})")
    print(f"  baseline CI_LB positive: {baseline['ci_lb_bps']:>8.3f}bp  halfwidth {ci_halfwidth}bp")
    print(f"  delisting stress at corner: {stress_at_corner}bp vs worst corner {stress_at_worst}bp")
    print(f"  breaks in {len(breaking)} cell(s)" + (
        f"; worst tolerated: hazard {worst_ok['hazard_annual']:.0%} haircut "
        f"{worst_ok['haircut']:.0%}" if worst_ok else "; NO cell with hazard>0 retains CI_LB>0"))
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

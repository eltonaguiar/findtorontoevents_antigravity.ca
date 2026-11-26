"""PBO block-length sensitivity (item 26) and White's Reality Check (item 27).

Both items were blocked on the same missing artifact: `per_class_edge_2026-11-22.json`
stored only per-cell *summaries* (`pbo_cscv`, `boot_ci_lb_bps`, ...), and neither a
CSCV block-length sweep nor a family-wide data-snooping p-value can be computed from
summaries. `per_class_edge_harness.py` now persists the T x N daily matrices, so both
are answered here without re-fetching a single price.

Two different questions, deliberately kept apart:

  item 26 — Is the reported PBO of 0.345 an artefact of the s=16 block choice?
            CSCV splits T into s blocks and asks how often the in-sample Sharpe
            winner lands below the out-of-sample median. s is a free parameter:
            too few blocks and each block is a regime, too many and the blocks
            are noise. A number that moves wildly with s is not a measurement.

  item 27 — Across all 39 cells tested, is the BEST cell's excess-vs-its-own-
            benchmark distinguishable from lucky? White (2000) bootstraps the
            maximum statistic under the null that no cell beats its benchmark.

Honesty rules encoded here
  * The harness's own PBO convention fills ragged NaN with 0.0 (a cell that does
    not exist yet contributes a 0% return). That SHRINKS the later-entering cells'
    measured Sharpe and so distorts CSCV. The spread-zero convention is used only
    to REPRODUCE 0.345; every reported sensitivity number is on the common window,
    where no cell is scored on days it did not trade.
  * Reality Check recentres the bootstrap on the observed means, so it tests
    "is the max positive", not "is the max bigger than this particular max".
    The studentised variant (Hansen SPA recentring) is reported alongside because
    the un-studentised statistic is dominated by the highest-volatility cell.
  * Cells with `integrity_flag` (H-210/H-211, the unadjusted futures series) are
    KEPT in the family. Dropping the broken cells would narrow the null and make
    the result look better; keeping them is the conservative choice.

Usage:
  python3 tools/pbo_and_reality_check.py \
      --net reports/per_class_edge_series_2026-11-22.csv \
      --excess reports/per_class_edge_excess_2026-11-22.csv \
      --out reports/pbo_reality_check_2026-11-22.json \
      --md reports/pbo_reality_check_2026-11-22.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from per_class_edge_harness import pbo_cscv  # noqa: E402  (same implementation)

B_BOOT = 5000
SEED = 11
DECLARED_BLOCKS = (8, 16, 24)      # stated before the run; not chosen after seeing output


# ------------------------------------------------------------------ bootstrap
def stationary_bootstrap_index(T: int, q: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap: geometric block lengths, mean q."""
    if T < 1:
        return np.empty(0, dtype=int)
    if q < 1:
        q = 1.0
    p_new = 1.0 / q
    idx = np.empty(T, dtype=int)
    cur = int(rng.integers(T))
    for t in range(T):
        idx[t] = cur
        if rng.random() < p_new:
            cur = int(rng.integers(T))
        else:
            cur = (cur + 1) % T
    return idx


def reality_check(F: np.ndarray, block_mean: float | None = None,
                  B: int = B_BOOT, seed: int = SEED,
                  studentize: bool = False, spa_recenter: bool = False) -> dict:
    """White's Reality Check / Hansen SPA on a complete T x N excess matrix.

    H0: max_i E[f_i] <= 0. Statistic: sqrt(T) * max_i mean(f_i), or the
    studentised max_i mean(f_i)/(sd_i/sqrt(T)). Bootstrap the max under the
    recentred null, then p = P(max* >= max).
    """
    F = np.asarray(F, dtype=float)
    T, N = F.shape
    if T < 50 or N < 2:
        return {"p_value": None, "note": "sample too small", "T": int(T), "N": int(N)}
    q = block_mean if block_mean is not None else max(1.0, round(T ** (1.0 / 3.0)))
    mean = F.mean(axis=0)
    sd = F.std(axis=0, ddof=1)
    sd = np.where(sd <= 0, np.nan, sd)
    rng = np.random.default_rng(seed)

    if studentize:
        with np.errstate(invalid="ignore", divide="ignore"):
            stat_cells = mean / (sd / math.sqrt(T))
        stat_cells = np.where(np.isfinite(stat_cells), stat_cells, -np.inf)
        # Hansen (2005): a cell keeps its mean in the recentring term unless it is
        # CLEARLY bad, i.e. unless its t falls below -sqrt(2 log log T). The
        # threshold is NOT zero: a cell sitting just below zero is statistically
        # indistinguishable from the null and MUST still widen it. Thresholding at
        # zero (the first version of this function) excluded those cells and made
        # the p-value anti-conservative -- it reported 0.0096 where the correct
        # rule reports an order of magnitude more.
        if spa_recenter:
            thr = -math.sqrt(2.0 * math.log(math.log(max(T, 3))))
            g = np.where(stat_cells >= thr, mean, 0.0)
        else:
            thr = None
            g = mean
    else:
        stat_cells = math.sqrt(T) * mean
        thr = None
        g = mean
    obs = float(np.max(stat_cells))
    Fc = F - g[None, :]

    boot = np.empty(B, dtype=float)
    for b in range(B):
        i = stationary_bootstrap_index(T, q, rng)
        m = Fc[i].mean(axis=0)
        if studentize:
            with np.errstate(invalid="ignore", divide="ignore"):
                t = m / (sd / math.sqrt(T))
            v = np.where(np.isfinite(t), t, -np.inf)
        else:
            v = math.sqrt(T) * m
        boot[b] = float(np.max(v))

    p = float((boot >= obs).mean())
    best = int(np.argmax(stat_cells))
    # Uncorrected single-cell one-sided p for the winning cell, for contrast:
    # the gap between this and p_value IS the cost of having searched 39 times.
    with np.errstate(invalid="ignore", divide="ignore"):
        t_best = float(mean[best] / (sd[best] / math.sqrt(T)))
    p_unc = float(1.0 - sps.norm.cdf(t_best)) if math.isfinite(t_best) else None
    return {
        "p_value": round(p, 4),
        "observed_stat": round(obs, 4),
        "best_cell_index": best,
        "best_cell_mean_bps": round(1e4 * float(mean[best]), 3),
        "best_cell_t": round(t_best, 3) if math.isfinite(t_best) else None,
        "best_cell_uncorrected_p": None if p_unc is None else round(p_unc, 6),
        "studentize": bool(studentize), "spa_recenter": bool(spa_recenter),
        "spa_recenter_threshold_t": None if thr is None else round(float(thr), 4),
        "n_boot": int(B), "block_mean_days": round(float(q), 2),
        "T": int(T), "N": int(N), "seed": int(seed),
    }


def pbo_sweep(mat: np.ndarray, blocks, seed: int = SEED, trials: int = 200) -> list[dict]:
    rows = []
    for s in blocks:
        v = pbo_cscv(mat, s_blocks=s, trials=trials, seed=seed)
        rows.append({"s_blocks": int(s),
                     "block_days": round(mat.shape[0] / s, 1),
                     "pbo": None if math.isnan(v) else round(float(v), 4)})
    return rows


# ----------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="reports/per_class_edge_series_2026-11-22.csv")
    ap.add_argument("--excess", default="reports/per_class_edge_excess_2026-11-22.csv")
    ap.add_argument("--frozen", default="reports/per_class_edge_2026-11-22.json")
    ap.add_argument("--out", default="reports/pbo_reality_check_2026-11-22.json")
    ap.add_argument("--md", default="reports/pbo_reality_check_2026-11-22.md")
    ap.add_argument("--blocks", default=",".join(str(b) for b in DECLARED_BLOCKS))
    ap.add_argument("--trials", type=int, default=200)
    args = ap.parse_args()

    net = pd.read_csv(args.net, index_col=0, parse_dates=True)
    exc = pd.read_csv(args.excess, index_col=0, parse_dates=True)
    blocks = [int(b) for b in args.blocks.split(",") if b.strip()]

    frozen = {}
    fp = Path(args.frozen)
    if fp.exists():
        frozen = json.loads(fp.read_text())

    complete = net.dropna(how="any")
    complete_exc = exc.loc[complete.index].dropna(how="any")
    assert list(complete.columns) == list(net.columns)

    # ---- item 26 -------------------------------------------------------
    spread_zero = pbo_sweep(net.fillna(0.0).to_numpy(dtype=float), blocks, trials=args.trials)
    common = pbo_sweep(complete.to_numpy(dtype=float), blocks, trials=args.trials)
    repro = None
    if frozen.get("pbo_cscv") is not None:
        row = next((r for r in spread_zero if r["s_blocks"] == 16), None)
        if row and row["pbo"] is not None:
            repro = {"frozen": frozen["pbo_cscv"], "rerun": row["pbo"],
                     "abs_diff": round(abs(row["pbo"] - frozen["pbo_cscv"]), 4),
                     "reproduced": abs(row["pbo"] - frozen["pbo_cscv"]) <= 0.005}

    vals = [r["pbo"] for r in common if r["pbo"] is not None]
    spread = {"min": min(vals) if vals else None,
              "max": max(vals) if vals else None,
              "range": (round(max(vals) - min(vals), 4) if vals else None)}

    # ---- item 27 -------------------------------------------------------
    common_exc = complete_exc.to_numpy(dtype=float)
    names = list(complete_exc.columns)
    rc_raw = reality_check(common_exc, studentize=False)
    rc_stud = reality_check(common_exc, studentize=True, spa_recenter=False)
    spa = reality_check(common_exc, studentize=True, spa_recenter=True)
    for r in (rc_raw, rc_stud, spa):
        bi = r.get("best_cell_index")
        r["best_cell"] = names[bi] if isinstance(bi, int) else None

    # Diagnostic only: the harness's spread-zero convention would let cells score
    # holidays they never traded. Quantify the flattery rather than assume it.
    filled = exc.fillna(0.0).to_numpy(dtype=float)
    rc_filled = reality_check(filled, studentize=False)
    bi = rc_filled.get("best_cell_index")
    rc_filled["best_cell"] = list(exc.columns)[bi] if isinstance(bi, int) else None

    # Robustness: the all-cells common window is only the LAST ~6 years, because a
    # few cells (penny, mutual fund) start late and drag the intersection forward.
    # A p-value on 2021-2026 says nothing about 2012-2020, so the same test is run
    # again on the family of cells present from the first week of the sample.
    first = net.apply(lambda s: s.first_valid_index())
    ref = first.min()
    deep_cols = [c for c in net.columns if (first[c] - ref).days <= 15]
    deep = net[deep_cols].dropna(how="any")
    deep_exc = exc[deep_cols].loc[deep.index].dropna(how="any")
    deep_arr = deep_exc.to_numpy(dtype=float)
    rc_deep = reality_check(deep_arr, studentize=False)
    stud_deep = reality_check(deep_arr, studentize=True, spa_recenter=False)
    spa_deep = reality_check(deep_arr, studentize=True, spa_recenter=True)
    for r in (rc_deep, stud_deep, spa_deep):
        bi = r.get("best_cell_index")
        r["best_cell"] = list(deep_exc.columns)[bi] if isinstance(bi, int) else None
    deep_block = {"n_cells": len(deep_cols), "cells": deep_cols,
                  "rows": int(deep.shape[0]),
                  "window": [str(deep.index.min().date()) if len(deep) else None,
                             str(deep.index.max().date()) if len(deep) else None],
                  "reality_check": rc_deep, "studentized": stud_deep,
                  "hansen_spa": spa_deep}

    per_cell_days = {c: int(net[c].notna().sum()) for c in net.columns}
    out = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "inputs": {"net": args.net, "excess": args.excess,
                   "frozen_scalars": args.frozen},
        "matrix": {
            "n_cells": int(net.shape[1]), "rows_union": int(net.shape[0]),
            "rows_common_window": int(complete.shape[0]),
            "common_window": [str(complete.index.min().date()) if len(complete) else None,
                              str(complete.index.max().date()) if len(complete) else None],
            "cells_dropped_by_common_window": sorted(
                c for c, d in per_cell_days.items() if d < complete.shape[0]),
            "note": "event cells (H-222 PEAD) have no shared time axis and are "
                    "absent by construction, so the family is 39 cells, not 40.",
        },
        "item26_pbo": {
            "declared_blocks": blocks,
            "harness_convention_spread_zero": spread_zero,
            "common_window": common,
            "reproduced_frozen_scalar": repro,
            "range_across_blocks": spread,
        },
        "item27_reality_check": {
            "headline": rc_raw,
            "studentized": rc_stud,
            "hansen_spa": spa,
            "diagnostic_spread_zero_only": rc_filled,
            "full_history_family": deep_block,
        },
        "verdict": {},
    }

    p_rc = rc_raw.get("p_value")
    p_spa = spa.get("p_value")
    p_spa_deep = spa_deep.get("p_value")
    out["verdict"] = {
        "pbo_stable": bool(spread["range"] is not None and spread["range"] <= 0.10),
        "pbo_convention_sensitive": bool(
            vals and min(spread_zero[i]["pbo"] for i in range(len(spread_zero))
                         if spread_zero[i]["pbo"] is not None) is not None
            and abs((spread_zero[1]["pbo"] or 0) - (common[1]["pbo"] or 0)) > 0.10),
        "family_p_range": [p_spa_deep, p_spa, p_rc],
        "any_family_p_below_0_05": bool(
            any(p is not None and p < 0.05 for p in (p_rc, p_spa, p_spa_deep,
                                                     rc_stud.get("p_value")))),
        "note": "PBO is evidence about the SEARCH process (how often the best "
                "cell fails out of sample); the Reality Check is evidence about "
                "the BEST CELL. Neither is a substitute for the other, and "
                "neither covers the 200-round programme's wider search.",
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))

    L = ["# PBO block-length sensitivity and White's Reality Check — 2026-11-22", "",
         f"Matrix: **{net.shape[1]} cells x {net.shape[0]} union rows**, "
         f"common window **{out['matrix']['rows_common_window']} days** "
         f"({out['matrix']['common_window'][0]} → {out['matrix']['common_window'][1]}).",
         "", "## Item 26 — is PBO = 0.345 an artefact of s = 16?", "",
         "| s_blocks | block length (days) | PBO, harness convention (NaN=0) | PBO, common window |",
         "|---|---|---|---|"]
    for a, b in zip(spread_zero, common):
        L.append(f"| {a['s_blocks']} | {a['block_days']} | {a['pbo']} | {b['pbo']} |")
    if repro:
        L += ["", f"Reproduction of the frozen scalar: **{repro['frozen']}** → "
                  f"**{repro['rerun']}** (|diff| {repro['abs_diff']}) — "
                  f"{'reproduced' if repro['reproduced'] else 'NOT reproduced'}."]
    L += ["", "## Item 27 — does the best cell survive a family-wide search?", "",
          "| test | statistic | best cell | observed | p | uncorrected p |",
          "|---|---|---|---|---|---|"]
    for label, r in (("Reality Check (raw)", rc_raw),
                     ("Reality Check (studentised)", rc_stud),
                     ("Hansen SPA", spa),
                     ("RC, spread-zero diagnostic", rc_filled)):
        L.append(f"| {label} | {r['observed_stat']} | {r['best_cell']} | "
                 f"{r['best_cell_mean_bps']} bp/day | {r['p_value']} | "
                 f"{r['best_cell_uncorrected_p']} |")
    L += ["", f"### Full-history family ({deep_block['n_cells']} cells present from "
              f"{deep_block['window'][0]}, {deep_block['rows']} days)", "",
          "The all-cells common window above starts in 2021 only because a few cells "
          "start late; this is the same test on the cells that exist for the whole sample.", "",
          "| test | best cell | observed | p | uncorrected p |", "|---|---|---|---|---|"]
    for label, r in (("Reality Check (raw)", rc_deep),
                     ("Reality Check (studentised)", stud_deep),
                     ("Hansen SPA", spa_deep)):
        L.append(f"| {label} | {r['best_cell']} | {r['best_cell_mean_bps']} bp/day | "
                 f"{r['p_value']} | {r['best_cell_uncorrected_p']} |")
    L += ["", "A cell is only evidence of an edge when CI-LB > 0, CI-LB@2x > 0, both "
              "halves > 0, DSR >= 0.95, excess-vs-bench > 0, **and** the family-wide "
              "p-value clears its threshold. Nothing else counts."]
    Path(args.md).write_text("\n".join(L) + "\n")

    print(f"matrix {net.shape[1]}x{net.shape[0]}, common {complete.shape[0]}")
    print("PBO spread-zero:", spread_zero)
    print("PBO common     :", common)
    print("repro          :", repro)
    print(f"RC   p={rc_raw['p_value']} best={rc_raw['best_cell']} "
          f"({rc_raw['best_cell_mean_bps']} bps, unc {rc_raw['best_cell_uncorrected_p']})")
    print(f"SPA  p={spa['p_value']}")
    print(f"deep family n={deep_block['n_cells']} rows={deep_block['rows']} "
          f"window={deep_block['window']} best={rc_deep['best_cell']}\n"
          f"  deep RC p={rc_deep['p_value']} | deep stud p={stud_deep['p_value']} | "
          f"deep SPA p={spa_deep['p_value']} "
          f"(threshold t={spa_deep.get('spa_recenter_threshold_t')})")
    print(f"wrote {args.out} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

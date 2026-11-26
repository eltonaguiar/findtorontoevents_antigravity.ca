"""How many INDEPENDENT trials is the 34-cell family actually worth?

The programme has two multiplicity corrections that disagree on the same data:

  single-cell DSR at 29 declared trials   -> 0.9483   (fails the 0.95 bar)
  family-wide SPA, correlation-preserving -> p = 0.0152 (rejects)

Both cannot be describing the same search. The difference is one modelling choice: the
DSR deflates as if the 29-34 cells were INDEPENDENT trials, and they are not -- twelve of
them are the same 12-1 TSMOM rule on different tickers, and the FOREX cells are near-copies
of each other. SPA resamples the actual matrix, so it inherits the correlation for free.

This tool measures the effective trial count three ways and then makes the two worlds
comparable in the same units:

  (1) correlation-matrix estimators, N_eff = N / (1 + (N-1)*mean_pairwise_corr) and the
      eigen-spectrum versions (participation ratio, Kaiser, entropy, Marchenko-Pastur edge);
  (2) a direct bootstrap calibration: bootstrap the matrix with ONE shared set of block
      indices per replicate (preserves the true cross-cell correlation) and again with
      INDEPENDENT indices per column (destroys it), then ask which N makes an
      N-independent-trials null reproduce the correlated null's 95th percentile;
  (3) the practical question -- the DSR passes H-201 at any N <= n_clear, so the decision
      reduces to "is N_eff above or below that threshold".

Everything is expressed in one unit so the two literatures can be compared directly:
a daily Sharpe s corresponds to the max-statistic t = s * sqrt(T).

Usage:
  python3 tools/effective_trials.py --out reports/effective_trials_2026-11-22.json \
      --md reports/effective_trials_2026-11-22.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from per_class_edge_harness import dsr, expected_max_sr  # noqa: E402

B_BOOT = 3000
SEED = 11
C95_DRAWS = 40000


# ---------------------------------------------------------------- estimators
def neff_correlation(R: np.ndarray) -> dict:
    """Closed-form effective-N estimates from a correlation matrix."""
    N = R.shape[0]
    off = R[~np.eye(N, dtype=bool)]
    rho_bar = float(np.mean(off))
    lam = np.sort(np.linalg.eigvalsh(R))[::-1]
    lam = np.clip(lam, 1e-12, None)
    total = float(lam.sum())
    # variance-of-a-sum count: N^2 / sum_ij rho_ij  (equals N/(1+(N-1)rho) at equicorrelation)
    denom = float(R.sum())
    return {
        "mean_pairwise_corr": round(rho_bar, 4),
        "median_pairwise_corr": round(float(np.median(off)), 4),
        "share_pairs_above_0.5": round(float((off > 0.5).mean()), 4),
        "neff_variance_of_sum": round(N * N / denom, 2),
        "neff_equicorrelation": round(N / (1.0 + (N - 1) * rho_bar), 2),
        "neff_participation_ratio": round(total * total / float((lam ** 2).sum()), 2),
        "neff_kaiser_eigen_above_1": int((lam > 1.0).sum()),
        "neff_entropy_exp": round(float(np.exp(-(lam / total * np.log(lam / total)).sum())), 2),
        "lambda1_share": round(float(lam[0] / total), 4),
        "eigenvalues_top8": [round(float(x), 3) for x in lam[:8]],
        "N": int(N),
    }


def neff_mp_edge(R: np.ndarray, T: int) -> int:
    """Marchenko-Pastur: how many eigenvalues exceed the upper noise edge for iid data."""
    N = R.shape[0]
    q = N / max(T, 1)
    edge = (1.0 + math.sqrt(q)) ** 2
    lam = np.linalg.eigvalsh(R)
    return int((lam > edge).sum())


# ---------------------------------------------------------------- bootstrap
def _block_index(T: int, B: int, L: int, rng: np.random.Generator) -> np.ndarray:
    """(B, T) matrix of circular-block bootstrap indices, mean block length L.

    Vectorised on purpose: the stationary-bootstrap version of this loop is pure
    Python and would take hours at B=3000 x N=34 x T=3735. Circular blocks are
    the standard alternative and the block length is the parameter that matters
    for the serial-correlation correction being measured here.
    """
    nb = int(math.ceil(T / L))
    starts = rng.integers(0, T, size=(B, nb))
    off = np.arange(L)
    return ((starts[:, :, None] + off[None, None, :]) % T).reshape(B, -1)[:, :T]


def max_t_joint(M: np.ndarray, B: int = B_BOOT, seed: int = SEED,
                chunk: int = 200) -> np.ndarray:
    """Bootstrap rows with ONE shared index set per replicate: correlation preserved."""
    T, N = M.shape
    L = max(2, int(round(T ** (1.0 / 3.0))))
    rng = np.random.default_rng(seed)
    out = np.empty(B)
    done = 0
    while done < B:
        b = min(chunk, B - done)
        X = M[_block_index(T, b, L, rng)]            # (b, T, N)
        with np.errstate(invalid="ignore", divide="ignore"):
            t = X.mean(axis=1) / (X.std(axis=1, ddof=1) / math.sqrt(T))
        out[done:done + b] = np.nanmax(t, axis=1)
        done += b
    return out


def max_t_independent(M: np.ndarray, B: int = B_BOOT, seed: int = SEED) -> np.ndarray:
    """Bootstrap each column with its OWN index set: correlation destroyed."""
    T, N = M.shape
    L = max(2, int(round(T ** (1.0 / 3.0))))
    rng = np.random.default_rng(seed + 1)
    out = np.full(B, -np.inf)
    for j in range(N):
        X = M[_block_index(T, B, L, rng), j]         # (B, T)
        with np.errstate(invalid="ignore", divide="ignore"):
            t = X.mean(axis=1) / (X.std(axis=1, ddof=1) / math.sqrt(T))
        out = np.maximum(out, t)
    return out


def c95_max_of_n(N: int, draws: int = C95_DRAWS, seed: int = SEED) -> float:
    """95th percentile of the max of N independent standard normals."""
    rng = np.random.default_rng(seed + N)
    return float(np.percentile(rng.standard_normal((draws, N)).max(axis=1), 95))


def calibrate_neff(M: np.ndarray, target: float, sizes=(5, 10, 15, 20, 25, 30),
                   reps: int = 3, B: int = 600, seed: int = SEED) -> dict:
    """Map the correlated null onto the SAME bootstrap's independent-null scale.

    The analytic order statistic is not a safe yardstick here: solving it against the
    bootstrap's own independent null returns N=19 for a family of N=34, a ~45% compression
    with no principled source. So the calibration curve is built by running the SAME block
    bootstrap on random subsets of the real cells, which keeps both sides in one currency.
    """
    T, N = M.shape
    rng = np.random.default_rng(seed + 7)
    curve = []
    for n in sizes:
        if n > N:
            continue
        vals = []
        for r in range(reps):
            cols = rng.choice(N, size=n, replace=False)
            vals.append(float(np.percentile(
                max_t_independent(M[:, cols], B=B, seed=seed + r), 95)))
        curve.append({"n_cells": int(n), "p95_independent_null_t": round(float(np.mean(vals)), 4)})
    # monotone interpolation: smallest n whose independent null already reaches the target
    neff = float(curve[-1]["n_cells"]) if curve else float(N)
    for r in curve:
        if r["p95_independent_null_t"] >= target:
            neff = float(r["n_cells"])
            break
    return {"curve": curve, "neff_interpolated": neff}


def solve_neff_max(target_t: float, hi: int = 200) -> float:
    """Which N makes an N-INDEPENDENT-trials null reach `target_t` at its 95th percentile?

    Both sides are t-statistics in which each cell is standardised by its OWN sampling sd,
    so under the null every cell is already ~N(0,1) in t units. The order statistic must
    therefore NOT be rescaled by the cross-sectional Sharpe dispersion: an earlier version
    multiplied by sd_sr*sqrt(T) (1.393 here), mixed the DSR's cross-TRIAL dispersion with a
    null whose cells have sampling sd 1, and solved to N=3 for both the correlated and the
    independent null -- an answer produced entirely by the scaling error.
    """
    for N in range(1, hi + 1):
        if c95_max_of_n(N) >= target_t:
            return float(N)
    return float(hi)


# --------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default="reports/per_class_edge_series_2026-11-22.csv")
    ap.add_argument("--excess", default="reports/per_class_edge_excess_2026-11-22.csv")
    ap.add_argument("--frozen", default="reports/per_class_edge_2026-11-22.json")
    ap.add_argument("--out", default="reports/effective_trials_2026-11-22.json")
    ap.add_argument("--md", default="reports/effective_trials_2026-11-22.md")
    args = ap.parse_args()

    net = pd.read_csv(args.net, index_col=0, parse_dates=True)
    frozen = json.loads(Path(args.frozen).read_text())
    declared = int(frozen["n_trials_declared"])
    frozen_sr0 = float(frozen["expected_max_sharpe_daily"])

    # the same full-history family the Reality Check used
    first = net.apply(lambda s: s.first_valid_index())
    ref = first.min()
    deep = [c for c in net.columns if (first[c] - ref).days <= 15]
    M = net[deep].dropna(how="any").to_numpy(dtype=float)
    T, N = M.shape
    print(f"family {N} cells x {T} days")

    # --- (1) correlation estimators
    R = np.corrcoef(M, rowvar=False)
    est = neff_correlation(R)
    est["neff_mp_edge"] = neff_mp_edge(R, T)

    # --- (2) bootstrap calibration
    # A ZERO-SKILL null must be centred on zero. Bootstrapping the raw series inherits
    # each cell's realised drift, which centres the null on the observed statistics and
    # makes "percentile of the observed t" meaningless. The first run of this tool did
    # exactly that and reported the observed t at the 47.5th percentile of its own null,
    # with both percentiles pinned to the solver cap at 6.09.
    Mc = M - M.mean(axis=0, keepdims=True)
    joint = max_t_joint(Mc)
    indep = max_t_independent(Mc)
    h95_j, h99_j, h985_j = (float(np.percentile(joint, q)) for q in (95, 99, 98.5))
    h95_i = float(np.percentile(indep, 95))

    # sd_sr must use the SAME basis as the frozen DSR (every cell with a Sharpe, not
    # just the deep family). Using the subset gave 0.9761 at N=29 instead of the known
    # 0.9483 and pushed the pass/fail threshold to N=58 -- a different calculation
    # wearing the same name. The reconstruction is a gate, not a footnote.
    srs = np.array([c["sr_daily"] for c in frozen["cells"] if c.get("sr_daily") is not None])
    sd_sr = float(np.std(srs, ddof=1))
    sr0_check = expected_max_sr(declared, sd_sr * sd_sr)
    if abs(sr0_check - frozen_sr0) > 1e-4:
        print(f"ABORT: rebuilt bar {sr0_check:.6f} != frozen {frozen_sr0:.6f} -- basis "
              "does not match, so any DSR below would be a different number")
        return 1
    print(f"bar reconstruction OK: sqrt(var_sr)={sd_sr:.8f} -> sr0(N={declared})="
          f"{sr0_check:.5f} (frozen {frozen_sr0:.5f}), from {len(srs)} cells")

    calib = calibrate_neff(Mc, h95_j)
    neff_max = calib["neff_interpolated"]
    neff_max_indep = solve_neff_max(h95_i)         # analytic cross-check, known compressed
    narrowing = 1.0 - h95_j / h95_i

    # --- (3) the decision: does H-201 clear the DSR bar at each candidate N?
    x = net["H-201"].dropna().to_numpy(dtype=float)
    xT = len(x)

    def dsr_at(n: int) -> float:
        return float(dsr(x, expected_max_sr(n, sd_sr * sd_sr))[0])

    def n_clear(limit: int = 60) -> int:
        best = 0
        for n in range(2, limit + 1):
            if dsr_at(n) >= 0.95:
                best = n
            else:
                break
        return best

    nc = n_clear()

    # the money table: every candidate N in the same t units
    ladder = []
    for n in (1, 3, 5, 8, 10, 15, 20, 28, 29, 34):
        sr0 = expected_max_sr(n, sd_sr * sd_sr)
        ladder.append({
            "n_trials": n,
            "dsr_implied_max_sr_daily": round(float(sr0), 5),
            "dsr_implied_t_threshold": round(float(sr0) * math.sqrt(xT), 3),
            "dsr_for_H201": round(dsr_at(n), 4),
        })

    # where does the observed H-201 statistic sit in the correlated null?
    t_obs = float(x.mean() / (x.std(ddof=1) / math.sqrt(xT)))
    pct_obs = float((joint < t_obs).mean() * 100)

    out = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "family": {"n_cells": int(N), "n_days": int(T), "cells": list(deep),
                   "window": [str(net[deep].dropna(how="any").index.min().date()),
                              str(net[deep].dropna(how="any").index.max().date())]},
        "declared_trials": declared,
        "cross_sectional_sd_of_daily_sharpe": round(sd_sr, 6),
        "estimators": est,
        "bootstrap": {
            "null": "zero-skill (each column recentred on zero) so the two nulls differ "
                    "ONLY in cross-cell correlation",
            "correlation_preserving_pctiles_t": {"p95": round(h95_j, 3),
                                                 "p98_5": round(h985_j, 3),
                                                 "p99": round(h99_j, 3)},
            "independent_pctile95_t": round(h95_i, 3),
            "max_tail_narrowing_pct": round(100 * narrowing, 2),
            "neff_max_statistic": neff_max,
            "neff_max_analytic_crosscheck": neff_max_indep,
            "calibration_curve": calib["curve"],
            "n_boot": B_BOOT,
        },
        "decision": {
            "H201_t_observed": round(t_obs, 3),
            "H201_percentile_in_correlated_null": round(pct_obs, 1),
            "dsr_n_clear_max_passing_trial_count": int(nc),
            "ladder": ladder,
        },
    }

    low = min(v for k, v in est.items() if k.startswith("neff_") and isinstance(v, (int, float)))
    high = max(v for k, v in est.items() if k.startswith("neff_") and isinstance(v, (int, float)))
    out["conclusion"] = {
        "neff_range_variance_and_eigen_estimators": [low, high],
        "neff_for_the_MEAN_statistic": est["neff_variance_of_sum"],
        "neff_for_the_MAX_statistic": neff_max,
        "n_clear_threshold": int(nc),
        "which_matters": "Every multiplicity correction in this programme (DSR, White's RC, "
                         "Hansen SPA) is a MAX-type statistic, so the max-tail number is "
                         "the one that applies. The variance-of-sum number describes the "
                         "average and is the wrong yardstick here.",
        "verdict": ("H201_PASSES_DSR_at_neff" if neff_max <= nc
                    else "H201_STILL_FAILS_DSR_at_neff"),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))

    L = ["# How many independent trials is the family worth? — 2026-11-22", "",
         f"Family **{N} cells × {T} days** "
         f"({out['family']['window'][0]} → {out['family']['window'][1]}). "
         f"Declared trials **{declared}**; cross-sectional sd of daily Sharpe "
         f"**{sd_sr:.6f}**.", "",
         "## 1. Correlation-matrix estimators", "",
         "| estimator | value |", "|---|---|",
         f"| mean pairwise correlation | {est['mean_pairwise_corr']} |",
         f"| median pairwise correlation | {est['median_pairwise_corr']} |",
         f"| share of pairs above 0.5 | {est['share_pairs_above_0.5']} |",
         f"| N² / Σρ (variance of a sum) | **{est['neff_variance_of_sum']}** |",
         f"| N / (1+(N−1)ρ̄) (equicorrelation) | **{est['neff_equicorrelation']}** |",
         f"| participation ratio (Σλ)²/Σλ² | **{est['neff_participation_ratio']}** |",
         f"| Kaiser (λ > 1) | **{est['neff_kaiser_eigen_above_1']}** |",
         f"| entropy exp(−Σp log p) | **{est['neff_entropy_exp']}** |",
         f"| Marchenko-Pastur edge count | **{est['neff_mp_edge']}** |",
         f"| first eigenvalue share | {est['lambda1_share']} |", "",
         "## 2. Bootstrap calibration (the decisive one)", "",
         "| quantity | t |", "|---|---|",
         f"| correlated null, 95th pct | {h95_j:.3f} |",
         f"| correlated null, 98.5th pct | {h985_j:.3f} |",
         f"| correlated null, 99th pct | {h99_j:.3f} |",
         f"| independent null, 95th pct | {h95_i:.3f} |", "",
         f"Correlation narrows the max-tail by only **{100*narrowing:.2f}%** ({h95_i:.3f} → "
         f"{h95_j:.3f}). Calibrating on the same bootstrap's independent null (random "
         f"subsets of the real cells) puts the equivalent count at **N_eff = "
         f"{neff_max:.0f}** for the max statistic.", "",
         "| n cells | independent-null p95 (t) |", "|---|---|"]
    for r in calib["curve"]:
        L.append(f"| {r['n_cells']} | {r['p95_independent_null_t']} |")
    L += ["", f"Target (correlated null p95): **{h95_j:.3f}**. The analytic order-statistic "
         f"solve is reported for reference only ({neff_max_indep:.0f}) — solving it against "
         f"this bootstrap's own independent null returns 19 for a 34-cell family, a ~45% "
         f"compression with no principled cause, so it is not used for the verdict.", "",
         f"This is the crux: the **variance-of-sum** estimator says the family is worth "
         f"**{est['neff_variance_of_sum']}** independent trials, but that is the effective "
         f"count for an AVERAGE. Every correction used here (DSR, RC, SPA) is a MAX-type "
         f"statistic, and for a maximum a common factor both synchronises the cells and "
         f"widens each marginal -- the two effects nearly cancel at ρ̄ = "
         f"{est['mean_pairwise_corr']}. So the number that applies is "
         f"**{neff_max:.0f}**, not {est['neff_variance_of_sum']}.", "",
         "## 3. The decision — DSR by trial count", "",
         "| N trials | DSR-implied max daily SR | DSR-implied t threshold | DSR for H-201 |",
         "|---|---|---|---|"]
    for r in ladder:
        L.append(f"| {r['n_trials']} | {r['dsr_implied_max_sr_daily']} | "
                 f"{r['dsr_implied_t_threshold']} | {r['dsr_for_H201']} |")
    L += ["", f"H-201's observed t is **{t_obs:.3f}**, sitting at the "
              f"**{pct_obs:.1f}th percentile** of the correlation-preserving null. The DSR "
              f"passes only while N ≤ **{nc}**, so the whole question is whether N_eff is "
              f"above or below {nc}.", "",
          f"**Verdict: N_eff(max) ≈ {neff_max:.0f} vs a pass threshold of N ≤ {nc} → "
          f"`{out['conclusion']['verdict']}`.**"]
    Path(args.md).write_text("\n".join(L) + "\n")

    print(json.dumps({k: out[k] for k in ("estimators", "bootstrap", "conclusion")}, indent=1))
    print("ladder:", [(r["n_trials"], r["dsr_implied_t_threshold"], r["dsr_for_H201"])
                      for r in ladder])
    print(f"H201 t_obs {t_obs:.3f} pct {pct_obs:.1f}")
    print(f"narrowing {100*narrowing:.2f}%  neff_max {neff_max} "
          f"(analytic {neff_max_indep})  n_clear {nc}")
    print("calibration curve:", calib["curve"])
    print(f"wrote {args.out} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

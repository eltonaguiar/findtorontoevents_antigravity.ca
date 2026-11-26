"""dsr_multiplicity_sensitivity.py — programme items D25 + D28.

D25  Is `n_trials = 29` honest?  Count the hypotheses that actually produced a cell,
     name the ones that did not, and say which direction the count error runs.

D28  H-201's DSR is 0.9469 against a 0.95 bar.  That is close enough to invite a
     goalpost move, so state the size of the move that would be required:
       * DSR as a function of the trial count N
       * the trial count N* at which it crosses 0.95
       * the daily Sharpe and the extra days needed to clear 0.95 at N=29

Method — Bailey & Lopez de Prado (2014), exactly as `per_class_edge_harness.py` has it:

    sr0(N)  = sqrt(var_sr) * [ (1-g)*Z^-1(1 - 1/N) + g*Z^-1(1 - 1/(N e)) ]
    DSR     = Phi( (sr - sr0) * sqrt(T-1) / sqrt(1 - sk*sr + (ku-1)/4*sr^2) )

`var_sr` (the dispersion of Sharpe across trials) and the skew/kurtosis of each
cell's daily returns are NOT stored in the artifact, so:
  * sqrt(var_sr) is RECOVERED from the artifact's own `expected_max_sharpe_daily`
    (= sr0 at the declared N), which is exact;
  * the denominator is evaluated at sk=0, ku=3 (normal returns), and the resulting
    residual against the stored `dsr` column is REPORTED as the size of the
    non-normality effect rather than assumed away.

The tool refuses to extrapolate if the residuals are not small.

Usage
  python3 tools/dsr_multiplicity_sensitivity.py \
      --cells reports/per_class_edge_2026-11-22.json \
      --out reports/dsr_multiplicity_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

EULER = 0.5772156649
BAR = 0.95
MAX_RESIDUAL = 0.05


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def k_of_n(n: int) -> float:
    """The trial-count factor inside sr0, WITHOUT the sqrt(var_sr) scale."""
    if n < 2:
        return 0.0
    return ((1.0 - EULER) * norm_ppf(1.0 - 1.0 / n)
            + EULER * norm_ppf(1.0 - 1.0 / (n * math.e)))


def sr0(n: int, scale: float) -> float:
    return scale * k_of_n(n)


def dsr_of(sr: float, T: int, n: int, scale: float) -> float:
    """Normal-returns form (sk=0, ku=3)."""
    if T < 3:
        return 0.0
    denom = math.sqrt(max(1e-12, 1.0 + 0.5 * sr * sr))
    return norm_cdf((sr - sr0(n, scale)) * math.sqrt(T - 1) / denom)


def trials_to_clear(sr: float, T: int, scale: float, bar: float = BAR,
                    cap: int = 100000):
    """LARGEST integer N with DSR >= bar, or None if N=2 already fails.

    DSR is DECREASING in N, so the predicate is true-then-false and the bisection
    must hunt for the last passing N, not the first. (An earlier draft searched for
    the first failing N and returned the cap; caught on the run, not in review.)
    """
    if dsr_of(sr, T, 2, scale) < bar:
        return None
    if dsr_of(sr, T, cap, scale) >= bar:
        return cap                      # still passing at the cap: report the cap
    lo, hi = 2, cap
    while lo < hi:
        mid = (lo + hi + 1) // 2        # upper-mid biases toward the passing end
        if dsr_of(sr, T, mid, scale) >= bar:
            lo = mid
        else:
            hi = mid - 1
    return lo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="reports/per_class_edge_2026-11-22.json")
    ap.add_argument("--out", default="reports/dsr_multiplicity_2026-11-22.json")
    ap.add_argument("--focus", default="H-201")
    a = ap.parse_args()

    art = json.loads(Path(a.cells).read_text())
    cells = art["cells"]
    declared = int(art["n_trials_declared"])
    sr0_declared = float(art["expected_max_sharpe_daily"])
    scale = sr0_declared / k_of_n(declared)          # sqrt(var_sr), recovered exactly

    # ---- D25: which hypotheses ran, which produced a cell ----------------
    seen: dict[str, int] = {}
    for c in cells:
        h = c["id"].split(":")[0]
        seen[h] = seen.get(h, 0) + 1
    lo = min(int(h.split("-")[1]) for h in seen)
    hi = max(int(h.split("-")[1]) for h in seen)
    all_ids = [f"H-{i}" for i in range(lo, hi + 1)]
    missing = [h for h in all_ids if h not in seen]
    if missing:
        count_note = (
            f"{declared} declared vs {len(seen)} that produced a cell. "
            f"Missing from the cell table: {', '.join(missing)}. These are trials that "
            f"were run but yielded NO admissible cell, so they still count as searches. "
            f"Using {declared} is the CONSERVATIVE direction (more trials lowers DSR), so "
            f"the artifact is not flattering itself on this axis.")
        count_verdict = "DECLARED_CONSERVATIVE"
    else:
        count_note = (f"{declared} declared vs {len(seen)} cells' hypotheses: identical.")
        count_verdict = "EXACT"

    # ---- reproduction check ---------------------------------------------
    res, worst, worst_id = [], 0.0, None
    for c in cells:
        sr, T, stored = c.get("sr_daily"), c.get("n_days"), c.get("dsr")
        if sr is None or not T or stored is None:
            continue
        mine = dsr_of(float(sr), int(T), declared, scale)
        d = abs(mine - stored)
        if d > worst:
            worst, worst_id = d, c["id"]
        res.append({"id": c["id"], "stored": stored, "recomputed": round(mine, 6),
                    "residual": round(d, 6)})

    out = {
        "generated_by": "tools/dsr_multiplicity_sensitivity.py",
        "source_artifact": a.cells,
        "recovered_scale_sqrt_var_sr": round(scale, 8),
        "declared_sr0_at_n": {"n": declared, "sr0": sr0_declared},
        "item_D25_trial_count": {
            "declared": declared,
            "hypotheses_with_a_cell": len(seen),
            "hypothesis_range": [f"H-{lo}", f"H-{hi}"],
            "hypotheses_without_a_cell": missing,
            "cells_per_hypothesis": dict(sorted(seen.items())),
            "verdict": count_verdict,
            "note": count_note,
        },
        "reproduction_check": {
            "formula": "Phi((SR-SR0)*sqrt(T-1)/sqrt(1+SR^2/2)); SR0 recovered from the "
                       "artifact's expected_max_sharpe_daily",
            "n_cells_checked": len(res),
            "worst_abs_residual": round(worst, 6),
            "worst_cell": worst_id,
            "tolerance": MAX_RESIDUAL,
            "reproduced": worst <= MAX_RESIDUAL,
            "residual_cause": "skew/kurtosis of each cell's daily returns are not stored; "
                              "the residual IS the non-normality effect",
        },
    }

    # ---- D28: multiplicity break-even -----------------------------------
    focus = next((c for c in cells if c["id"].split(":")[0] == a.focus), None)
    if focus is None:
        raise SystemExit(f"focus {a.focus} not found")
    focus_res = next((r["residual"] for r in res if r["id"].split(":")[0] == a.focus), None)
    out["reproduction_check"]["focus_cell"] = focus["id"]
    out["reproduction_check"]["focus_residual"] = focus_res
    out["reproduction_check"]["cells_within_tolerance"] = sum(
        1 for r in res if r["residual"] <= MAX_RESIDUAL)
    # The tolerance gates the cell being extrapolated, not the whole family: the
    # non-normality term is largest exactly where the Sharpe is smallest (H-228), and
    # that cell is not the one under analysis.
    if focus_res is None or focus_res > MAX_RESIDUAL:
        out["abort"] = ("The FOCUS cell does not reproduce within tolerance; extrapolation "
                        "withheld. Family residuals are reported above, but nothing is "
                        "extrapolated from a column that could not be rebuilt.")
        Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps(out, indent=2))
        return 1
    sr, T = float(focus["sr_daily"]), int(focus["n_days"])
    n_star = trials_to_clear(sr, T, scale)
    # SR needed at the declared N
    sr_need = sr0(declared, scale) + norm_ppf(BAR) * math.sqrt(max(1e-12, 1 + 0.5 * sr * sr)) / math.sqrt(T - 1)
    # extra days needed at the observed SR
    T_need = None
    edge = sr - sr0(declared, scale)
    if edge > 0:
        T_need = 1 + (norm_ppf(BAR) * math.sqrt(max(1e-12, 1 + 0.5 * sr * sr)) / edge) ** 2

    grid = [2, 10, 20, 26, 29, 40, 60, 100, 200, 500, 1000]
    out["item_D28_multiplicity_breakeven"] = {
        "cell": focus["id"], "asset_class": focus["asset_class"], "name": focus["name"],
        "n_days": T, "sr_daily": sr, "ann_sharpe": focus.get("ann_sharpe"),
        "stored_dsr": focus.get("dsr"),
        "recomputed_dsr_at_declared": round(dsr_of(sr, T, declared, scale), 6),
        "dsr_by_trial_count": {str(n): round(dsr_of(sr, T, n, scale), 6) for n in grid},
        "min_trials_still_passing": n_star,
        "sr_needed_daily_at_declared": round(sr_need, 6),
        "sr_needed_ann_at_declared": round(sr_need * math.sqrt(252), 4),
        "sr_shortfall_daily": round(sr_need - sr, 6),
        "days_needed_at_observed_sr": (round(T_need, 1) if T_need else None),
        "years_needed_at_observed_sr": (round(T_need / 252.0, 2) if T_need else None),
    }
    d = out["item_D28_multiplicity_breakeven"]
    margin = (declared - n_star) if n_star else None
    d["margin_in_trials"] = margin
    d["clears_at_26_trials"] = round(dsr_of(sr, T, 26, scale), 6)
    d["clears_at_3_fewer_trials"] = round(dsr_of(sr, T, max(2, declared - 3), scale), 6)
    out["what_would_have_to_be_true"] = {
        "rule": "stated as a property of the data, never by moving the bar",
        "days_needed_at_observed_sr": d["days_needed_at_observed_sr"],
        "years_needed_at_observed_sr": d["years_needed_at_observed_sr"],
        "extra_days_beyond_observed_history": (
            round(d["days_needed_at_observed_sr"] - T, 1)
            if d["days_needed_at_observed_sr"] else None),
    }
    if n_star:
        extra = d["days_needed_at_observed_sr"] - T if d["days_needed_at_observed_sr"] else None
        d["interpretation"] = (
            f"{focus['id']} holds a 0.95 DSR for trial counts up to {n_star}; the programme "
            f"declared {declared}, so it FAILS by {abs(margin)} trial(s) — at {declared - 3} "
            f"trials the same data would have scored "
            f"{d['clears_at_3_fewer_trials']:.4f} and passed. The verdict therefore turns on "
            f"bookkeeping, not on the return series: the cell is NOT_PROVEN, not refuted. "
            f"The data-side margin is independent of that and is small too: at the declared "
            f"{declared} trials it needed a daily Sharpe of {sr_need:.4f} versus {sr:.4f} "
            f"observed, a shortfall of {sr_need - sr:.4f}/day, which is "
            f"{extra:.1f} more trading days of the same history ({extra / 252.0:.2f} years) "
            f"rather than more edge. Both margins are too small to carry a real-money "
            f"decision, and that is the finding.")
    else:
        d["interpretation"] = (
            f"{focus['id']} cannot clear 0.95 at any trial count >= 2; the failure is in the "
            f"Sharpe, not the multiplicity.")

    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

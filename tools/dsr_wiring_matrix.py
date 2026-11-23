#!/usr/bin/env python3
"""dsr_wiring_matrix — which DSR implementation does the 658 floor depend on?

The estate now contains FOUR live deflated-Sharpe implementations with
incompatible signatures, plus a documented gate ("DSR >= 0.95 with declared
n_trials, global floor 658"). A number is not reproducible unless you say which
wiring produced it. This harness runs one fixed set of rows through every
implementation, over a grid of n_trials and variance conventions, and reports:

  1. which (implementation, n_trials, ddof) reproduces a peer's claimed vector
  2. what SR hurdle each implementation implies at N=658 for DSR=0.95
     (i.e. what the "658 floor" actually costs in annualised Sharpe)

Rows are stated as wins/losses so they are exactly reconstructible: no closed
pick DB, no sampling, no inference. Deterministic; no network.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from alpha_engine.deflated_sharpe import deflated_sharpe_ratio as dsr_variance_first
from alpha_engine.statistical_rigor import deflated_sharpe_ratio as dsr_returns
from crypto_ml_edge.validation import deflated_sharpe_ratio as dsr_observed

OUT = REPO_ROOT / "reports" / "dsr_wiring_matrix_2026-11-23.json"

# wins, losses, win_pct, loss_pct — the four row sets as published by the peer.
ROWSETS = {
    "A": dict(wins=40, losses=80, win_pct=3.0, loss_pct=-0.6),
    "B": dict(wins=50, losses=100, win_pct=3.0, loss_pct=-0.6),
    "C": dict(wins=70, losses=140, win_pct=4.0, loss_pct=-0.6),
    "D": dict(wins=40, losses=80, win_pct=4.0, loss_pct=-0.6),
}
PEER = {"A": 0.800, "B": 0.994, "C": 1.000, "D": 0.968}
N_TRIALS_GRID = (26, 67, 359, 361, 362, 452, 658)
# sigma_sr documented in docs/TRIAL_BUDGET_2026-11-23.md (grid B, N=658 -> SR* 2.0333)
DOCUMENTED_SIGMA_SR = 0.6488


def returns_of(spec: dict) -> np.ndarray:
    return np.array([spec["win_pct"]] * spec["wins"] + [spec["loss_pct"]] * spec["losses"], dtype=float)


def moments(x: np.ndarray) -> dict:
    m = float(np.mean(x))
    sd = float(np.std(x, ddof=0))
    sd1 = float(np.std(x, ddof=1))
    n = x.size
    skew = float(((x - m) ** 3).mean() / sd ** 3) if sd > 0 else 0.0
    kurt = float(((x - m) ** 4).mean() / sd ** 4) if sd > 0 else 3.0
    return {"n": n, "mean_pct": m, "sd0": sd, "sd1": sd1, "sr": m / sd1 if sd1 else 0.0,
            "sr0": m / sd if sd else 0.0, "skew": skew, "kurtosis": kurt}


def call_statistical_rigor(x: np.ndarray, n_trials: int) -> float | None:
    """returns[] + n_trials; computes SR and the null E[max SR] itself."""
    try:
        return float(dsr_returns(list(x), n_trials))
    except Exception:  # noqa: BLE001
        return None


def call_crypto_ml(x: np.ndarray, n_trials: int, ddof: int) -> float | None:
    """observed_sharpe + n_trials + n_obs; no trial dispersion, assumes iid normal null."""
    m = moments(x)
    sr = m["sr"] if ddof == 1 else m["sr0"]
    try:
        return float(dsr_observed(sr, n_trials, m["n"], skew=m["skew"], kurtosis=m["kurtosis"]))
    except Exception:  # noqa: BLE001
        return None


def call_variance_first(x: np.ndarray, n_trials: int, ddof: int, sr_variance: float) -> float | None:
    """estimated_sharpe + sr_variance + nb_trials + backtest_horizon.

    This is the ONLY implementation that takes the dispersion of the trial SR
    distribution as an argument, which is why the 658 floor's sigma_sr=0.6488
    can only be wired here. Both variance conventions are tried explicitly.
    """
    m = moments(x)
    sr = m["sr"] if ddof == 1 else m["sr0"]
    try:
        return float(dsr_variance_first(sr, sr_variance, n_trials, m["n"], m["skew"], m["kurtosis"]))
    except Exception:  # noqa: BLE001
        return None


def sr_hurdle_for(impl: str, n_trials: int, target: float = 0.95) -> float | None:
    """SR (per-trade) at which the implementation returns `target` — the real cost of a floor."""
    lo, hi = 0.0, 20.0
    x = returns_of(ROWSETS["A"])
    for _ in range(80):
        mid = (lo + hi) / 2
        m = moments(x)
        if impl == "statistical_rigor":
            # shift the series mean so its SR equals `mid`, keeping shape
            shifted = x + (mid - m["sr0"]) * m["sd0"]
            val = call_statistical_rigor(shifted, n_trials)
        elif impl == "crypto_ml":
            val = call_crypto_ml(x, n_trials, 1) if False else float(
                dsr_observed(mid, n_trials, m["n"], skew=m["skew"], kurtosis=m["kurtosis"]))
        else:
            val = call_variance_first(x, n_trials, 1, DOCUMENTED_SIGMA_SR) if False else float(
                dsr_variance_first(mid, DOCUMENTED_SIGMA_SR, n_trials, m["n"], m["skew"], m["kurtosis"]))
        if val is None:
            return None
        if val < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def annualise(sr_per_trade: float, n: int) -> float:
    """Per-trade SR -> annualised, assuming `n` trades per year (stated, not implied)."""
    return sr_per_trade * math.sqrt(n)


def main() -> int:
    out: dict = {
        "schema": "dsr.wiring_matrix.v1",
        "note": "Deterministic reconstruction. Row sets are wins/losses, not samples.",
        "peer_claim": PEER,
        "documented_sigma_sr": DOCUMENTED_SIGMA_SR,
        "implementations": {
            "alpha_engine.statistical_rigor.deflated_sharpe_ratio": "returns[], n_trials",
            "alpha_engine.deflated_sharpe.deflated_sharpe_ratio": "observed_sharpe, sr_variance, nb_trials, horizon, skew, kurt",
            "crypto_ml_edge.validation.deflated_sharpe_ratio": "observed_sharpe, n_trials, n_obs, skew, kurt",
            "alpha_engine.validation.sharpe_metrics.deflated_sharpe_ratio": "returns Series, risk_free_rate, freq — NOT WIRED: computes its own n_trials internally, cannot take 658",
        },
        "rowsets": {},
        "grid": {},
        "best_match": None,
    }

    for key, spec in ROWSETS.items():
        x = returns_of(spec)
        out["rowsets"][key] = {"spec": spec, **{k: round(v, 6) for k, v in moments(x).items()},
                               "peer_dsr": PEER[key]}

    results: dict = {}
    for n_trials in N_TRIALS_GRID:
        row: dict = {}
        for key, spec in ROWSETS.items():
            x = returns_of(spec)
            row[key] = {
                "statistical_rigor": call_statistical_rigor(x, n_trials),
                "deflated_sharpe(sigma=0.6488)": call_variance_first(x, n_trials, 1, DOCUMENTED_SIGMA_SR),
                "deflated_sharpe(sigma=empirical)": call_variance_first(
                    x, n_trials, 1, float(np.var([moments(returns_of(s))["sr"] for s in ROWSETS.values()], ddof=1))),
                "crypto_ml(ddof=1)": call_crypto_ml(x, n_trials, 1),
                "crypto_ml(ddof=0)": call_crypto_ml(x, n_trials, 0),
            }
        results[n_trials] = row
    out["grid"] = results

    # Which wiring reproduces the peer's four numbers?
    impls = list(results[N_TRIALS_GRID[0]][ "A"].keys())
    scored = []
    for impl in impls:
        for n_trials in N_TRIALS_GRID:
            vals = [results[n_trials][k][impl] for k in ROWSETS]
            if any(v is None for v in vals):
                continue
            diffs = [abs(v - PEER[k]) for v, k in zip(vals, ROWSETS)]
            scored.append({"impl": impl, "n_trials": n_trials,
                           "max_abs_err": round(max(diffs), 4),
                           "rmse": round(math.sqrt(sum(d * d for d in diffs) / len(diffs)), 4),
                           "values": {k: round(v, 4) for k, v in zip(ROWSETS, vals)}})
    scored.sort(key=lambda r: r["rmse"])
    out["ranking"] = scored[:10]
    out["best_match"] = scored[0] if scored else None
    out["reproduces_peer"] = bool(scored and scored[0]["max_abs_err"] <= 0.005)

    # What does N=658 cost, per implementation?
    hurdle = {}
    for impl in ("statistical_rigor", "crypto_ml", "deflated_sharpe"):
        sr658 = sr_hurdle_for(impl, 658)
        sr26 = sr_hurdle_for(impl, 26)
        hurdle[impl] = {
            "sr_at_N658": None if sr658 is None else round(sr658, 4),
            "sr_at_N26": None if sr26 is None else round(sr26, 4),
            "annualised_N658_252": None if sr658 is None else round(annualise(sr658, 252), 3),
            "delta_per_trial": None if (sr658 is None or sr26 is None) else round((sr658 - sr26) / (658 - 26), 6),
        }
    out["hurdle_at_95"] = hurdle

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"{'impl':38s} {'N':>4s} {'max_err':>8s} {'rmse':>7s}  values")
    for r in scored[:8]:
        print(f"{r['impl']:38s} {r['n_trials']:>4d} {r['max_abs_err']:>8.3f} {r['rmse']:>7.3f}  {r['values']}")
    print()
    print("peer:", PEER)
    print("reproduces_peer:", out["reproduces_peer"])
    print("hurdle at DSR 0.95:", json.dumps(hurdle, indent=1))
    print("artefact ->", OUT)
    return 0 if out["reproduces_peer"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

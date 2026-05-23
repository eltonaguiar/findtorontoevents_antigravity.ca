"""Monte Carlo random-walk baseline + bootstrap p-value for system expectancy.

Answers the "is this system a coin flip?" question rigorously.

Method:
  1. Load closed picks, filter MATIC ghost rows, extract per-trade pnl_pct.
  2. Compute observed system expectancy (mean pnl_pct) and bootstrap its
     95% confidence interval.
  3. Generate N=10,000 random-walk baselines by sign-shuffling trade magnitudes
     (preserves the payoff distribution but breaks any WR edge).
  4. Report the fraction of baselines whose expectancy >= the observed value —
     that's the one-sided p-value for "our system is better than a random
     walk over the same payoff distribution."
  5. Flag failure if p > 0.05 (not distinguishable from random at 5%).

Stdlib only. Reproducible via fixed seed. Safe-default pass on insufficient
data (n < 30) — does not block CI on tiny samples.

Usage:
    python tools/data_integrity/monte_carlo_baseline.py
    python tools/data_integrity/monte_carlo_baseline.py --ledger universal
    python tools/data_integrity/monte_carlo_baseline.py --iterations 50000

Exit codes:
    0 — system expectancy is statistically better than random (p <= 0.05)
    2 — system expectancy is NOT distinguishable from random (p > 0.05)
    3 — insufficient data (n < 30)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from typing import Any

try:
    from tools.data_integrity import _common
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from tools.data_integrity import _common  # type: ignore

MIN_N = 30
DEFAULT_ITERATIONS = 10_000
DEFAULT_SEED = 42
SIGNIFICANCE = 0.05


def load_pnl_series(ledger: str) -> list[float]:
    """Load per-trade pnl_pct series from the requested ledger, ghost-filtered."""
    if ledger == "closed":
        path = _common.CLOSED_PICKS
    elif ledger == "universal":
        path = _common.UNIVERSAL_RESOLVED
    else:
        raise ValueError(f"unknown ledger: {ledger}")
    if not os.path.exists(path):
        return []
    rows = _common.load_json_list(path)
    series: list[float] = []
    for p in rows:
        if _common.is_ghost_row(p):
            continue
        raw = p.get("pnl_pct")
        if raw is None:
            raw = p.get("pnl")
        try:
            val = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            val = None
        if val is None:
            continue
        series.append(val)
    return series


def bootstrap_ci(series: list[float], iterations: int, seed: int) -> tuple[float, float]:
    """Return 95% bootstrap CI for the mean of `series`."""
    rng = random.Random(seed)
    n = len(series)
    means: list[float] = []
    for _ in range(iterations):
        sample_sum = 0.0
        for _ in range(n):
            sample_sum += series[rng.randrange(n)]
        means.append(sample_sum / n)
    means.sort()
    lo_idx = max(0, int(0.025 * iterations) - 1)
    hi_idx = min(iterations - 1, int(0.975 * iterations))
    return means[lo_idx], means[hi_idx]


def random_walk_pvalue(
    series: list[float],
    iterations: int,
    seed: int,
) -> tuple[float, float, float]:
    """Sign-shuffle Monte Carlo test.

    Null hypothesis: the system has no directional edge — the observed pnl
    signs are random given the magnitude distribution. Under the null, we
    can permute signs independently per trade (each sign = Bernoulli(0.5)).

    Returns (observed_mean, null_mean, p_value) where p_value is
    P(random_mean >= observed_mean) over `iterations` simulations.
    """
    rng = random.Random(seed)
    magnitudes = [abs(x) for x in series]
    observed = statistics.fmean(series)
    n = len(series)
    n_extreme = 0
    null_means: list[float] = []
    for _ in range(iterations):
        s = 0.0
        for i in range(n):
            s += magnitudes[i] if rng.random() < 0.5 else -magnitudes[i]
        m = s / n
        null_means.append(m)
        if m >= observed:
            n_extreme += 1
    p = n_extreme / iterations
    null_mean = statistics.fmean(null_means)
    return observed, null_mean, p


def analyze(ledger: str, iterations: int, seed: int) -> dict[str, Any]:
    series = load_pnl_series(ledger)
    n = len(series)
    result: dict[str, Any] = {
        "ledger": ledger,
        "n": n,
        "iterations": iterations,
        "seed": seed,
    }
    if n < MIN_N:
        result["status"] = "INSUFFICIENT_DATA"
        result["message"] = f"Need at least {MIN_N} trades, got {n}"
        return result

    ci_lo, ci_hi = bootstrap_ci(series, iterations, seed)
    observed, null_mean, p_value = random_walk_pvalue(series, iterations, seed)

    result["observed_expectancy_pct"] = observed
    result["bootstrap_ci_95"] = [ci_lo, ci_hi]
    result["null_expectancy_mean"] = null_mean
    result["p_value_one_sided"] = p_value
    result["significance_threshold"] = SIGNIFICANCE

    if observed <= 0:
        result["status"] = "NEGATIVE_EXPECTANCY"
        result["message"] = (
            f"Observed expectancy {observed:+.4f}% is non-positive — "
            "system is losing money on average. Random-walk test moot."
        )
    elif p_value > SIGNIFICANCE:
        result["status"] = "COIN_FLIP"
        result["message"] = (
            f"p-value {p_value:.4f} > {SIGNIFICANCE} — observed expectancy "
            f"{observed:+.4f}% is NOT statistically distinguishable from a "
            f"random walk over the same payoff magnitudes."
        )
    else:
        result["status"] = "EDGE_CONFIRMED"
        result["message"] = (
            f"p-value {p_value:.4f} <= {SIGNIFICANCE} — observed expectancy "
            f"{observed:+.4f}% is statistically better than random at 5%."
        )
    return result


def format_report(result: dict[str, Any]) -> str:
    lines = ["=== MONTE CARLO BASELINE ==="]
    lines.append(f"Ledger:     {result['ledger']}")
    lines.append(f"n trades:   {result['n']}")
    if result.get("status") == "INSUFFICIENT_DATA":
        lines.append(f"Status:     {result['status']}")
        lines.append(f"Message:    {result['message']}")
        return "\n".join(lines)
    lines.append(f"Iterations: {result['iterations']}  (seed={result['seed']})")
    lines.append("")
    lines.append(
        f"Observed expectancy: {result['observed_expectancy_pct']:+.4f}% per trade"
    )
    ci_lo, ci_hi = result["bootstrap_ci_95"]
    lines.append(f"Bootstrap 95% CI:    [{ci_lo:+.4f}%, {ci_hi:+.4f}%]")
    lines.append(f"Null mean (random):  {result['null_expectancy_mean']:+.4f}%")
    lines.append(f"p-value (one-sided): {result['p_value_one_sided']:.4f}")
    lines.append("")
    lines.append(f"Status:  {result['status']}")
    lines.append(f"Verdict: {result['message']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--ledger",
        choices=("closed", "universal"),
        default="closed",
        help="which ledger to analyze",
    )
    parser.add_argument(
        "--iterations", type=int, default=DEFAULT_ITERATIONS,
        help="Monte Carlo + bootstrap iterations",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    args = parser.parse_args(argv)

    result = analyze(args.ledger, args.iterations, args.seed)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    out_dir = _common.ensure_out_dir()
    out_path = os.path.join(out_dir, f"monte_carlo_{args.ledger}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    status = result.get("status")
    if status == "EDGE_CONFIRMED" or status == "INSUFFICIENT_DATA":
        return 0 if status == "EDGE_CONFIRMED" else 3
    return 2  # NEGATIVE_EXPECTANCY or COIN_FLIP — failure signal


if __name__ == "__main__":
    sys.exit(main())

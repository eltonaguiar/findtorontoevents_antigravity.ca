#!/usr/bin/env python3
"""Paired bootstrap of strategy vs benchmark — the missing second hurdle.

Backlog items D1-D7 (docs/BACKLOG_100_2026-11-23.md).

WHY THIS EXISTS
A kill rule of the form "annualised net > 4.32%" is a CASH hurdle. A strategy
that is long SPY 90% of the time clears it on BETA alone while its signal
contributes nothing. freebuff's C-016 caught exactly this in this programme: ETF
and INDEX showed POSITIVE CI lower bounds on absolute return while running
NEGATIVE excess against their own benchmarks.

The fix is a second, paired hurdle: bootstrap the CI on the DIFFERENCE
(strategy - benchmark) and require it to exclude zero. Absolute return answers
"did I make money"; this answers "did the signal do anything".

The pairing matters. Two independent CIs can overlap while the difference is
significant, because the series are highly correlated. We resample the paired
differences d_t = s_t - b_t with a moving-block bootstrap (blocks preserve
autocorrelation, which an iid bootstrap destroys and which inflates significance
on financial series).

Read-only library + CLI. No network.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

HURDLE_TBILL_APR = 0.0432  # tools/capacity_model.py:49 — 432bp/yr, not the rounded 4.3%
TRADING_DAYS = 252


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mu = _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))


def block_bootstrap_ci(
    diffs: list[float],
    n_boot: int = 10000,
    block: int = 5,
    alpha: float = 0.05,
    seed: int = 20261123,
) -> dict:
    """Moving-block bootstrap CI for the mean of `diffs`.

    `diffs` are per-period paired differences (strategy - benchmark), in decimal.
    Returns the mean, the two-sided (1-alpha) CI, and the fraction of resamples
    whose mean is <= 0 (one-sided evidence against the strategy).
    """
    n = len(diffs)
    if n == 0:
        raise ValueError("empty series")
    if block < 1:
        raise ValueError("block must be >= 1")
    block = min(block, n)
    rng = random.Random(seed)
    n_blocks = math.ceil(n / block)
    means: list[float] = []
    for _ in range(n_boot):
        acc = []
        for _ in range(n_blocks):
            start = rng.randint(0, n - block)
            acc.extend(diffs[start:start + block])
        means.append(_mean(acc[:n]))
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    le_zero = sum(1 for m in means if m <= 0) / n_boot
    return {
        "n_periods": n,
        "n_boot": n_boot,
        "block": block,
        "mean_diff": _mean(diffs),
        "mean_diff_bp": _mean(diffs) * 1e4,
        "ci_low": lo,
        "ci_high": hi,
        "ci_low_bp": lo * 1e4,
        "ci_high_bp": hi * 1e4,
        "p_le_zero": le_zero,
        "excludes_zero": lo > 0,
    }


def ols_beta(strategy_rets: list[float], benchmark_rets: list[float]) -> float:
    """Slope of strategy on benchmark. This is the amount of BETA, not of edge."""
    mb = _mean(benchmark_rets)
    var = sum((b - mb) ** 2 for b in benchmark_rets)
    if var == 0:
        return 0.0
    ms = _mean(strategy_rets)
    cov = sum((s - ms) * (b - mb) for s, b in zip(strategy_rets, benchmark_rets))
    return cov / var


def beta_adjusted_alpha_ci(
    strategy_rets: list[float],
    benchmark_rets: list[float],
    n_boot: int = 10000,
    block: int = 5,
    alpha: float = 0.05,
    seed: int = 20261123,
) -> dict:
    """Bootstrap CI for Jensen's alpha: mean of (strategy - beta * benchmark).

    WHY THIS AND NOT THE RAW DIFFERENCE:
    The raw paired difference (strategy - benchmark) is nonzero for ANY change in
    beta. A 1.5x-leveraged index fund has a large positive difference and zero
    new information. Measured while writing this: `s = 1.5 * b` PASSED a raw
    paired-difference hurdle, which is the beta trap in a new costume.

    Subtracting beta * benchmark removes the exposure and leaves only what the
    signal contributed. Leveraged beta now yields alpha = 0 (correctly failed),
    while genuine stock-selection skill still shows up.
    """
    beta = ols_beta(strategy_rets, benchmark_rets)
    resid = [s - beta * b for s, b in zip(strategy_rets, benchmark_rets)]
    r = block_bootstrap_ci(resid, n_boot=n_boot, block=block, alpha=alpha, seed=seed)
    r["beta"] = beta
    r["kind"] = "beta_adjusted_alpha"
    # DEGENERATE-RESIDUAL GUARD. If the residual has ~zero variance, every resample
    # mean equals the same numerical epsilon, so the CI collapses to a point and
    # "excludes zero" becomes TRUE on floating-point noise. Measured: `s = 1.5*b`
    # left a residual of ~2e-16 and was reported as significant. A near-zero-variance
    # residual carries no information and must never pass.
    if _std(resid) < 1e-12 or abs(_mean(resid)) < 1e-12:
        r["excludes_zero"] = False
        r["degenerate_residual"] = True
    else:
        r["degenerate_residual"] = False
    return r


def sharpe(rets: list[float], periods_per_year: int = TRADING_DAYS) -> float:
    sd = _std(rets)
    if sd == 0:
        return 0.0
    return _mean(rets) / sd * math.sqrt(periods_per_year)


def two_hurdle_gate(
    strategy_rets: list[float],
    benchmark_rets: list[float],
    hurdle_apr: float = HURDLE_TBILL_APR,
    periods_per_year: int = TRADING_DAYS,
    n_boot: int = 10000,
    block: int = 5,
    seed: int = 20261123,
) -> dict:
    """Both hurdles must pass. Returns a verdict with its two numbers.

    Hurdle 1 (cash):   annualised net return > T-bill hurdle
    Hurdle 2 (signal): bootstrap CI on BETA-ADJUSTED alpha excludes 0

    A strategy can fail either one. Failing hurdle 2 while passing hurdle 1 is the
    buy-and-hold-beta failure mode: it made money, but the signal did nothing.
    Hurdle 2 is beta-adjusted, not a raw difference, so leverage cannot buy a pass.
    """
    if len(strategy_rets) != len(benchmark_rets):
        raise ValueError("strategy and benchmark must be paired (same length)")
    ann = _mean(strategy_rets) * periods_per_year
    bc = beta_adjusted_alpha_ci(strategy_rets, benchmark_rets,
                                n_boot=n_boot, block=block, seed=seed)
    raw = block_bootstrap_ci([s - b for s, b in zip(strategy_rets, benchmark_rets)],
                             n_boot=n_boot, block=block, seed=seed)
    h1 = ann > hurdle_apr
    h2 = bc["excludes_zero"]
    if h1 and h2:
        verdict = "PASS"
    elif h1 and not h2:
        verdict = "BETA_ONLY_FAIL_HURDLE_2"
    elif not h1 and h2:
        verdict = "SIGNAL_BUT_BELOW_CASH"
    else:
        verdict = "FAIL_BOTH"
    return {
        "verdict": verdict,
        "ann_return": ann,
        "ann_return_bp": ann * 1e4,
        "hurdle_apr": hurdle_apr,
        "hurdle_apr_bp": hurdle_apr * 1e4,
        "hurdle1_cash_pass": h1,
        "hurdle2_signal_pass": h2,
        "sharpe": sharpe(strategy_rets, periods_per_year),
        "benchmark_sharpe": sharpe(benchmark_rets, periods_per_year),
        "beta": bc["beta"],
        "paired": bc,
        "raw_difference_ci": raw,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strategy", help="JSON file: list of per-period decimal returns")
    ap.add_argument("--benchmark", help="JSON file: list of per-period decimal returns")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--block", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not (a.strategy and a.benchmark):
        ap.print_help()
        return 2
    s = json.loads(Path(a.strategy).read_text())
    b = json.loads(Path(a.benchmark).read_text())
    r = two_hurdle_gate(s, b, n_boot=a.n_boot, block=a.block, seed=a.seed)
    if a.json:
        print(json.dumps(r, indent=2))
        return 0 if r["verdict"] == "PASS" else 1
    print(f"verdict            {r['verdict']}")
    print(f"ann return         {r['ann_return_bp']:.1f} bp  vs hurdle "
          f"{r['hurdle_apr_bp']:.0f} bp  -> hurdle1 {'PASS' if r['hurdle1_cash_pass'] else 'FAIL'}")
    p = r["paired"]
    print(f"paired diff        {p['mean_diff_bp']:+.2f} bp/period  "
          f"CI [{p['ci_low_bp']:+.3f}, {p['ci_high_bp']:+.3f}]  "
          f"-> hurdle2 {'PASS' if p['excludes_zero'] else 'FAIL'}")
    print(f"p(diff<=0)         {p['p_le_zero']:.4f}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

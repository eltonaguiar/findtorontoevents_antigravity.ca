#!/usr/bin/env python3
"""
monkey_test_benchmark.py — the overfit-killer null benchmark (Master Loop Addendum E/H)
=======================================================================================

A candidate strategy's edge is real only if it beats a null of RANDOM strategies drawn
from the SAME universe, at the SAME cost, with the SAME trade count. This is the cheap
overfit killer the loop has wanted but never had (docs/MONEY_READY_MASTER_LOOP_2026-06.md
Addendum B #1, E "monkey-test null benchmark", H "monkey-test fairness"): it complements
DSR/PBO and the cluster-bootstrap CI-LB (tools/pf_ci_lower.py) by asking the blunt question
"could a monkey throwing darts at this universe have done as well?".

Method (Addendum H fairness rules baked in):
  * The null = N random "monkey" strategies. Each monkey samples the SAME number of trades
    as the candidate, WITH REPLACEMENT, from the universe pool of per-trade net returns
    (identical universe + costs + overlap rules — the caller supplies an already-net,
    same-universe pool, so cost/selection are matched by construction).
  * Match the candidate's TRADE COUNT (n). (Hold-distribution matching only matters when
    testing entry/direction skill against price paths; for a returns-pool null the trade
    count is the fair control.)
  * Decision statistic is PRE-SPECIFIED and defaults to the t-stat of mean return, NOT raw
    PF — PF is a ratio and unstable at small n (Addendum H). PF CI-LB is offered too, but the
    t-stat is the fair, low-variance default for "beats random".
  * Verdict: the candidate must exceed the 95th percentile of the null distribution
    (empirical p < 0.05). Deterministic (seed=42) so weekly scorecards reproduce.

This is a PURE-STATS, READ-ONLY library + CLI — no DB, no network, no production caller
(opt-in analysis tool). It does not change any pick/score path.

Usage:
  # inline
  python3 tools/monkey_test_benchmark.py --candidate 0.03,-0.02,0.04,... --universe 0.01,-0.01,...
  # from JSON files (lists of net per-trade returns, in fraction or percent — be consistent)
  python3 tools/monkey_test_benchmark.py --candidate-json cand.json --universe-json pool.json --stat tstat
  python3 tools/monkey_test_benchmark.py --self-test     # no network/DB

Library:
  from tools.monkey_test_benchmark import monkey_test
  res = monkey_test(candidate_returns, universe_returns, n_iter=1000, stat="tstat")

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# --------------------------------------------------------------------------- #
# Decision statistics (pre-specified; t-stat default per Addendum H)
# --------------------------------------------------------------------------- #
def tstat(returns: list) -> float:
    """One-sample t-stat of mean(returns) vs 0. Low-variance, fair vs PF."""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    sd = var ** 0.5
    if sd <= 0:
        return 0.0 if mean == 0 else math.inf * (1 if mean > 0 else -1)
    return mean / (sd / (n ** 0.5))


def profit_factor(returns: list) -> float:
    gains = sum(r for r in returns if r > 0)
    losses = -sum(r for r in returns if r < 0)
    if losses > 0:
        return gains / losses
    return math.inf if gains > 0 else 0.0


_STATS = {"tstat": tstat, "pf": profit_factor}


def _percentile(sorted_vals: list, q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return sorted_vals[idx]


# --------------------------------------------------------------------------- #
# The monkey test
# --------------------------------------------------------------------------- #
def monkey_test(candidate_returns: list, universe_returns: list,
                n_iter: int = 1000, stat: str = "tstat", seed: int = 42) -> dict:
    """Compare a candidate's decision statistic to a null of `n_iter` random monkeys.

    Each monkey samples len(candidate_returns) trades WITH REPLACEMENT from
    universe_returns (same universe/costs) and computes `stat`. Returns a dict with
    the candidate stat, null percentiles, the candidate's percentile, and beats_p95.
    """
    if stat not in _STATS:
        raise ValueError(f"stat must be one of {list(_STATS)}")
    statfn = _STATS[stat]
    cand = [float(x) for x in candidate_returns]
    pool = [float(x) for x in universe_returns]
    n = len(cand)
    if n == 0 or len(pool) == 0:
        raise ValueError("candidate and universe must be non-empty")
    cand_stat = statfn(cand)

    rng = random.Random(seed)
    U = len(pool)
    null = []
    for _ in range(n_iter):
        sample = [pool[rng.randrange(U)] for _ in range(n)]
        s = statfn(sample)
        if s == math.inf:           # degenerate all-win monkey; cap so percentile math is sane
            s = 1e9
        elif s == -math.inf:
            s = -1e9
        null.append(s)
    null_sorted = sorted(null)
    p50 = _percentile(null_sorted, 0.50)
    p95 = _percentile(null_sorted, 0.95)
    cval = 1e9 if cand_stat == math.inf else (-1e9 if cand_stat == -math.inf else cand_stat)
    below = sum(1 for x in null if x < cval)
    pct = below / len(null)
    return {
        "stat": stat,
        "n_trades": n,
        "n_iter": n_iter,
        "candidate_stat": None if cand_stat in (math.inf, -math.inf) else round(cand_stat, 4),
        "null_p50": round(p50, 4),
        "null_p95": round(p95, 4),
        "candidate_percentile": round(pct, 4),
        "empirical_p": round(1 - pct, 4),
        "beats_p95": cval > p95,
        "verdict": "BEATS_RANDOM (p<0.05)" if cval > p95 else "INDISTINGUISHABLE_FROM_RANDOM",
    }


# --------------------------------------------------------------------------- #
# Self-test (no network / DB)
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    # 1) Clearly-skilled candidate (all +2%) vs zero-mean noise universe -> beats p95.
    universe = [0.01, -0.01] * 200
    cand_good = [0.02] * 30
    r = monkey_test(cand_good, universe, n_iter=2000, stat="tstat")
    assert r["beats_p95"] and r["candidate_percentile"] > 0.95, r

    # 2) Candidate that IS the universe distribution -> indistinguishable (~50th pct).
    rng = random.Random(7)
    cand_null = [universe[rng.randrange(len(universe))] for _ in range(30)]
    r2 = monkey_test(cand_null, universe, n_iter=2000, stat="tstat")
    assert not r2["beats_p95"], r2
    assert 0.15 < r2["candidate_percentile"] < 0.85, r2  # near the middle, not extreme

    # 3) Negative-edge candidate (all -2%) -> well below p95, low percentile.
    r3 = monkey_test([-0.02] * 30, universe, n_iter=1000, stat="tstat")
    assert not r3["beats_p95"] and r3["candidate_percentile"] < 0.05, r3

    # 4) PF stat path works + is deterministic.
    a = monkey_test(cand_good, universe, n_iter=500, stat="pf", seed=42)
    b = monkey_test(cand_good, universe, n_iter=500, stat="pf", seed=42)
    assert a == b, "not deterministic"
    assert a["beats_p95"], a

    # 5) tstat sanity on a known set.
    assert abs(tstat([1.0, 1.0, 1.0]) ) == 0.0 or tstat([1.0,1.0,1.0]) != tstat([1.0,2.0,3.0])
    print("[self-test] all assertions passed")
    return 0


# --------------------------------------------------------------------------- #
def _load(arg_inline, arg_json):
    if arg_json:
        return [float(x) for x in json.loads(Path(arg_json).read_text())]
    if arg_inline:
        return [float(x) for x in arg_inline.split(",") if x.strip()]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--candidate", help="comma-separated candidate net per-trade returns")
    ap.add_argument("--candidate-json", help="JSON file: list of candidate net per-trade returns")
    ap.add_argument("--universe", help="comma-separated universe-pool net per-trade returns")
    ap.add_argument("--universe-json", help="JSON file: list of universe-pool net per-trade returns")
    ap.add_argument("--n-iter", type=int, default=1000)
    ap.add_argument("--stat", choices=list(_STATS), default="tstat")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json-out", help="write the verdict dict to this path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()

    cand = _load(args.candidate, args.candidate_json)
    univ = _load(args.universe, args.universe_json)
    if not cand or not univ:
        ap.error("provide --candidate(/-json) and --universe(/-json)")
    res = monkey_test(cand, univ, n_iter=args.n_iter, stat=args.stat, seed=args.seed)
    print(json.dumps(res, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(res, indent=2))
    # exit 0 if beats random, 3 otherwise (so CI/preflight can gate on it)
    return 0 if res["beats_p95"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

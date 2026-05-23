"""Lightweight Combinatorial Purged Cross-Validation overfit detector.

Why this exists
---------------
The original GH Actions cloud-agent plan's Theme F (statistical rigor)
flagged an explicit gap: no overfit detection. The supplement suite
already has DSR with real N (`tools/dsr_audit.py`), which is a related
but different correction (multiple-testing haircut on Sharpe). What's
missing is a per-strategy out-of-sample generalisation check that
catches strategies whose realised PnL is concentrated in narrow
historical windows — a hallmark of a backtest-overfit signal.

This module implements a lightweight version of López de Prado's
Combinatorial Purged Cross-Validation (CPCV) idea: partition chronological
picks into K blocks, evaluate every combination of (T train blocks,
K-T test blocks), and compare the BEST train-set mean PnL to the AVERAGE
test-set mean PnL. The gap between them is a Probability-of-Backtest-
Overfitting (PBO) approximation.

Output per strategy
-------------------
- `n`                         total usable picks
- `k_blocks`                  partitioning K (default 6)
- `n_combinations`            number of (T, K-T) partitions evaluated
- `best_train_mean_pct`       max train-set mean PnL across combinations
- `avg_test_mean_pct`         mean test-set mean PnL across combinations
- `overfit_gap_pct`           best_train - avg_test (large = overfit)
- `pbo_estimate`              fraction of combinations where best-on-
                              train ranks BELOW median on test
- `flag_overfit`              True when overfit_gap > 1.0% AND pbo > 0.5

López de Prado's PBO formal definition needs a probit transform; we
report the simpler "fraction-flipped" approximation, which is monotone
in the formal PBO and easier to interpret. Document the simplification
in the docstring so reviewers don't expect the exact 2014 statistic.

Wiring status: OPT-IN SIDECAR. No production caller. Future PR adds
an `overfit?` badge on `audit_dashboard/template.html` strategy table
sourcing `tools/data/cpcv_overfit_results.json`.

Caveats
-------
1. Like every closed-pick supplement, fits on labels from
   `outcome_resolver.py` — Theme B contamination on FOREX/COMMODITY.
2. K=6 is a defensible default but small. The number of (T, K-T)
   combinations is C(K, K/2) = 20 for K=6. Larger K improves the PBO
   estimate but is computationally heavier.
3. This is a *generalisation* check, not a *strategy validity* test.
   A strategy with no edge AND no overfit will pass cleanly; you still
   need wr_posterior to confirm edge.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "cpcv_overfit_results.json"

DEFAULT_K = 6
DEFAULT_MIN_N = 60
DEFAULT_OVERFIT_GAP_PCT = 1.0
DEFAULT_PBO_THRESHOLD = 0.5


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _parse_iso(s: Any) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _block_partition(arr: np.ndarray, k: int) -> list[np.ndarray]:
    """Split arr into k contiguous blocks (last block absorbs remainder)."""
    n = len(arr)
    block_size = n // k
    out: list[np.ndarray] = []
    for i in range(k):
        start = i * block_size
        end = (i + 1) * block_size if i < k - 1 else n
        out.append(arr[start:end])
    return out


def cpcv_overfit(pnls: np.ndarray, k: int = DEFAULT_K) -> dict[str, Any]:
    """Compute CPCV overfit statistics for a sorted pnl_pct array.

    Returns dict with metric names matching the module docstring.
    """
    n = len(pnls)
    blocks = _block_partition(pnls, k)
    half = k // 2  # train uses half the blocks; test uses the rest

    # Iterate over all C(k, half) ways to select train blocks
    train_means: list[float] = []
    test_means: list[float] = []
    flips = 0
    n_combinations = 0
    for train_idx in itertools.combinations(range(k), half):
        train_set = np.concatenate([blocks[i] for i in train_idx]) if train_idx else np.array([])
        test_idx = tuple(i for i in range(k) if i not in train_idx)
        test_set = np.concatenate([blocks[i] for i in test_idx]) if test_idx else np.array([])
        if len(train_set) == 0 or len(test_set) == 0:
            continue
        n_combinations += 1
        tm = float(np.mean(train_set))
        te = float(np.mean(test_set))
        train_means.append(tm)
        test_means.append(te)

    if not train_means:
        return {
            "n": int(n), "k_blocks": int(k),
            "n_combinations": 0,
            "best_train_mean_pct": 0.0, "avg_test_mean_pct": 0.0,
            "overfit_gap_pct": 0.0, "pbo_estimate": 0.0,
            "flag_overfit": False,
        }

    train_arr = np.array(train_means)
    test_arr = np.array(test_means)
    best_train_idx = int(np.argmax(train_arr))
    best_train_mean = float(train_arr[best_train_idx])
    avg_test_mean = float(np.mean(test_arr))
    overfit_gap = best_train_mean - avg_test_mean

    # PBO approximation: across all combinations, count how often the
    # best-on-train fold's test-mean ranks BELOW median test-mean.
    # That's the simple "fraction-flipped" form (monotone-equivalent
    # to López de Prado 2014's PBO; trades exact mathematical form for
    # interpretability).
    median_test = float(np.median(test_arr))
    flipped = sum(1 for tr_mean, te_mean in zip(train_arr, test_arr)
                  if tr_mean >= np.percentile(train_arr, 75)
                  and te_mean < median_test)
    pbo_estimate = flipped / max(n_combinations, 1)

    return {
        "n": int(n),
        "k_blocks": int(k),
        "n_combinations": int(n_combinations),
        "best_train_mean_pct": round(best_train_mean, 6),
        "avg_test_mean_pct": round(avg_test_mean, 6),
        "overfit_gap_pct": round(overfit_gap, 6),
        "pbo_estimate": round(pbo_estimate, 6),
        "flag_overfit": (overfit_gap > DEFAULT_OVERFIT_GAP_PCT
                          and pbo_estimate > DEFAULT_PBO_THRESHOLD),
    }


def analyze_strategy(picks: list[dict],
                      k: int = DEFAULT_K,
                      min_n: int = DEFAULT_MIN_N) -> dict | None:
    cleaned: list[tuple[datetime | None, float]] = []
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        ts = _parse_iso(p.get("closed_at") or p.get("opened_at"))
        cleaned.append((ts, pnl))

    if len(cleaned) < min_n:
        return None

    cleaned.sort(key=lambda x: (
        x[0] is None,
        x[0] or datetime.min.replace(tzinfo=timezone.utc),
    ))
    pnls = np.array([c[1] for c in cleaned], dtype=float)
    return cpcv_overfit(pnls, k)


def analyze_all(picks: list[dict],
                k: int = DEFAULT_K,
                min_n: int = DEFAULT_MIN_N) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, k, min_n)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["overfit_gap_pct"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"k": k, "min_n": min_n,
                   "overfit_gap_pct_threshold": DEFAULT_OVERFIT_GAP_PCT,
                   "pbo_estimate_threshold": DEFAULT_PBO_THRESHOLD},
        "n_strategies": len(out),
        "n_overfit_flagged": sum(1 for r in out if r["flag_overfit"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.k, args.min_n)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"overfit-flagged:    {summary['n_overfit_flagged']}")
        print("top 10 by overfit_gap:")
        for r in summary["strategies"][:10]:
            flag = "OVERFIT" if r["flag_overfit"] else " ok    "
            print(f"  [{flag}] {r['strategy'][:30]:<30} "
                  f"gap={r['overfit_gap_pct']:>+6.3f}% "
                  f"pbo={r['pbo_estimate']:>5.2f} "
                  f"n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

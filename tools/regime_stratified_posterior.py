"""Regime-stratified Beta-Bernoulli WR posterior.

Why this exists
---------------
`tools/wr_posterior.py` aggregates all closed picks for a strategy into
a single Beta-Bernoulli posterior. That violates the independence
assumption when picks within a single regime are correlated (which they
typically are in trend-following / mean-reversion strategies that
either work or don't depending on macro state).

The wr_posterior docstring documents this as caveat #2: "true credible
intervals are wider than reported". This module addresses it head-on by
fitting a SEPARATE posterior per (strategy, regime). The output catches
the dispositive "looks great on average but only works in one regime"
pattern that the flat aggregate hides.

Regime extraction
-----------------
1. Prefer `pick['regime']` if present (string label).
2. Else infer from `pick['btc_4h_direction']` (+1 = BULL, -1 = BEAR,
   0 = SIDEWAYS).
3. Else fall back to single bucket "UNKNOWN".

The third path makes the module backward-compatible with any pick
schema; the first two paths surface real regime stratification when
upstream emitters provide it.

Output schema
-------------
Per strategy:
  {
    "strategy": "...",
    "regimes": {
        "BULL":  {n, wins, posterior_mean, ci_low_95, ci_high_95, p_above_50},
        "BEAR":  {...},
        ...
    },
    "regime_count": int,
    "weighted_aggregate": {
        "n": total,
        "posterior_mean": frequency-weighted average across regimes,
        "p_above_50_min_regime": min(P(>50%) across regimes),
    },
    "regime_dependent_flag": bool  # True if max-min P(>50%) across regimes > 0.50
  }

Reuses tools/wr_posterior.py:posterior_stats via importlib so all the
Jeffreys-prior + scipy.stats.beta math stays in one place.

Wiring status: OPT-IN SIDECAR. No production caller. Future PR adds
a "regime-dep?" badge on audit_dashboard/template.html strategy table
sourcing tools/data/regime_stratified_posterior_results.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "regime_stratified_posterior_results.json"

DEFAULT_MIN_N = 10  # per (strategy, regime) — below this, skip the regime
DEFAULT_REGIME_DEP_THRESHOLD = 0.50  # max-min P(>50%) gap to flag


def _load_posterior_stats():
    spec = importlib.util.spec_from_file_location(
        "wr_posterior", REPO_ROOT / "tools" / "wr_posterior.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.posterior_stats


def extract_regime(pick: dict) -> str:
    """Return a string regime label for a pick.

    Order of preference:
      1. pick['regime'] (any non-empty string)
      2. pick['btc_4h_direction'] -> BULL/BEAR/SIDEWAYS
      3. fallback "UNKNOWN"
    """
    raw = pick.get("regime")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    btc_dir = pick.get("btc_4h_direction")
    if btc_dir is not None:
        try:
            v = float(btc_dir)
        except (TypeError, ValueError):
            v = None
        if v is not None:
            if v > 0:
                return "BULL"
            if v < 0:
                return "BEAR"
            return "SIDEWAYS"
    return "UNKNOWN"


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def stratify_strategy(picks: list[dict],
                      min_n: int = DEFAULT_MIN_N,
                      regime_dep_threshold: float = DEFAULT_REGIME_DEP_THRESHOLD,
                      posterior_stats=None) -> dict | None:
    """Fit per-regime posteriors for a single strategy's picks.

    Returns None if no usable picks.

    `posterior_stats` defaults to the function from tools/wr_posterior.py;
    tests inject a deterministic fake.
    """
    if posterior_stats is None:
        posterior_stats = _load_posterior_stats()

    by_regime: dict[str, list[int]] = defaultdict(list)
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        regime = extract_regime(p)
        win = 1 if pnl > 0 else 0
        by_regime[regime].append(win)

    if not by_regime:
        return None

    regimes_out: dict[str, Any] = {}
    p_above_values: list[float] = []
    total_n = 0
    weighted_mean_num = 0.0  # sum_regime( regime_n * mean )
    for regime, outcomes in by_regime.items():
        n = len(outcomes)
        if n < min_n:
            regimes_out[regime] = {"n": n, "skipped": True,
                                   "reason": f"n<min_n({min_n})"}
            continue
        wins = sum(outcomes)
        stats = posterior_stats(wins, n)
        regimes_out[regime] = {
            "n": int(n),
            "wins": int(wins),
            "posterior_mean": round(stats.get("posterior_mean", 0.0), 6),
            "ci_low_95": round(stats.get("ci_low_95", 0.0), 6),
            "ci_high_95": round(stats.get("ci_high_95", 1.0), 6),
            "p_above_50": round(stats.get("p_wr_above_50", 0.0), 6),
            "skipped": False,
        }
        p_above_values.append(stats.get("p_wr_above_50", 0.0))
        total_n += n
        weighted_mean_num += n * stats.get("posterior_mean", 0.0)

    active_regimes = [r for r, v in regimes_out.items() if not v.get("skipped")]
    weighted_aggregate: dict[str, Any]
    if total_n > 0 and p_above_values:
        weighted_aggregate = {
            "n": int(total_n),
            "posterior_mean": round(weighted_mean_num / total_n, 6),
            "p_above_50_min_regime": round(min(p_above_values), 6),
            "p_above_50_max_regime": round(max(p_above_values), 6),
        }
        regime_dependent_flag = (max(p_above_values) - min(p_above_values)
                                  > regime_dep_threshold)
    else:
        weighted_aggregate = {"n": 0, "posterior_mean": 0.0,
                              "p_above_50_min_regime": 0.0,
                              "p_above_50_max_regime": 0.0}
        regime_dependent_flag = False

    return {
        "regimes": regimes_out,
        "regime_count": len(active_regimes),
        "weighted_aggregate": weighted_aggregate,
        "regime_dependent_flag": regime_dependent_flag,
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                regime_dep_threshold: float = DEFAULT_REGIME_DEP_THRESHOLD,
                posterior_stats=None) -> dict:
    if posterior_stats is None:
        posterior_stats = _load_posterior_stats()

    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = stratify_strategy(sub, min_n, regime_dep_threshold, posterior_stats)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -(r["weighted_aggregate"]["p_above_50_max_regime"]
                              - r["weighted_aggregate"]["p_above_50_min_regime"]))

    n_dependent = sum(1 for r in out if r["regime_dependent_flag"])
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n_per_regime": min_n,
                   "regime_dep_threshold": regime_dep_threshold},
        "n_strategies": len(out),
        "n_regime_dependent": n_dependent,
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--regime-dep-threshold", type=float,
                    default=DEFAULT_REGIME_DEP_THRESHOLD)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.regime_dep_threshold)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"regime-dependent (P-spread > {args.regime_dep_threshold}): "
              f"{summary['n_regime_dependent']}")
        for r in summary["strategies"][:10]:
            wa = r["weighted_aggregate"]
            spread = wa["p_above_50_max_regime"] - wa["p_above_50_min_regime"]
            flag = "DEP " if r["regime_dependent_flag"] else " ok "
            print(f"  [{flag}] {r['strategy'][:35]:<35} regimes={r['regime_count']} "
                  f"P-spread={spread:.3f} aggregate-mean={wa['posterior_mean']:.3f}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

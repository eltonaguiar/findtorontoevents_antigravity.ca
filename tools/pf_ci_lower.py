#!/usr/bin/env python3
"""pf_ci_lower.py — the Master Loop's §10 referee: bootstrap CI lower bound of net PF.

The promotion bar (docs/MONEY_READY_MASTER_LOOP_2026-06.md §2/§10) is NOT a
point estimate: a strategy promotes only when the 95% CI LOWER BOUND of its
net-of-cost profit factor exceeds 1.15 at n>=80 forward. Point-estimate PF at
small n is how every false Tier-2 of the last three months happened.

Two estimators:
  * plain bootstrap   — resample trades i.i.d. (B draws, percentile method)
  * cluster bootstrap — resample CLUSTERS (default cluster = symbol+UTC-day),
    because same-symbol-same-day trades are one bet, not m independent bets.
    This is the honest one whenever duplicates/re-emissions exist (they do:
    7d emission dup-rate has run 45-72% all June).

Also exports effective_n(): n_eff = n / (1 + (m_bar - 1) * rho) with rho
estimated from within-cluster pnl correlation (falls back to cluster count,
which is the conservative floor, when rho can't be estimated).

Deterministic by default (seed=42) so weekly scorecards are reproducible.

Usage (CLI):
    python3 tools/pf_ci_lower.py --pnls-json picks.json            # [{pnl_pct, symbol?, opened_at?}, ...]
    python3 tools/pf_ci_lower.py --pnls 1.2,-0.5,0.8,-1.1,...      # quick inline
Library:
    from tools.pf_ci_lower import pf_ci_lower, effective_n
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict

DEFAULT_B = 2000
DEFAULT_ALPHA = 0.05
DEFAULT_SEED = 42


def profit_factor(pnls) -> float | None:
    """Net PF. None when there are no losses AND no wins; inf when no losses."""
    wins = sum(p for p in pnls if p > 0)
    losses = sum(-p for p in pnls if p < 0)
    if losses <= 0:
        return float("inf") if wins > 0 else None
    return wins / losses


def _percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1))))
    return sorted_vals[k]


def pf_ci_lower(pnls, *, clusters=None, alpha=DEFAULT_ALPHA, n_boot=DEFAULT_B,
                seed=DEFAULT_SEED) -> dict:
    """Bootstrap lower CI bound of PF.

    pnls:     list of per-trade net pnl (pct or fraction — unit-agnostic).
    clusters: optional list (same length) of hashable cluster keys
              (e.g. f"{symbol}|{day}"). When given, resampling is BY CLUSTER.

    Returns {pf, pf_ci_lower, pf_ci_upper, n, n_clusters, method, alpha, n_boot}.
    pf_ci_lower is None when undefined (n<5 or PF undefined in >20% of draws).
    """
    pnls = [float(p) for p in pnls]
    n = len(pnls)
    out = {"pf": profit_factor(pnls), "n": n, "alpha": alpha, "n_boot": n_boot,
           "pf_ci_lower": None, "pf_ci_upper": None,
           "method": "cluster" if clusters else "iid", "n_clusters": None}
    if n < 5:
        return out
    rng = random.Random(seed)
    if clusters is not None:
        assert len(clusters) == n, "clusters must align with pnls"
        groups = defaultdict(list)
        for c, p in zip(clusters, pnls):
            groups[c].append(p)
        keys = list(groups.keys())
        out["n_clusters"] = len(keys)
        draws = []
        for _ in range(n_boot):
            sample = []
            for _ in range(len(keys)):
                sample.extend(groups[rng.choice(keys)])
            pf = profit_factor(sample)
            if pf is not None and not math.isinf(pf):
                draws.append(pf)
    else:
        draws = []
        for _ in range(n_boot):
            sample = [pnls[rng.randrange(n)] for _ in range(n)]
            pf = profit_factor(sample)
            if pf is not None and not math.isinf(pf):
                draws.append(pf)
    # If too many draws were degenerate (no losses), the CI is not estimable
    # honestly — report None rather than a fantasy bound.
    if len(draws) < n_boot * 0.8:
        return out
    draws.sort()
    out["pf_ci_lower"] = round(_percentile(draws, alpha), 4)
    out["pf_ci_upper"] = round(_percentile(draws, 1 - alpha), 4)
    return out


def effective_n(pnls, clusters) -> dict:
    """n_eff = n / (1 + (m_bar - 1) * rho); rho from within-cluster dispersion.

    rho estimate: 1 - (mean within-cluster variance / overall variance),
    clamped to [0, 1]. Degenerate cases fall back to rho=1 (n_eff = number of
    clusters) — the conservative floor.
    """
    pnls = [float(p) for p in pnls]
    n = len(pnls)
    groups = defaultdict(list)
    for c, p in zip(clusters, pnls):
        groups[c].append(p)
    k = len(groups)
    m_bar = n / k if k else 0.0
    overall_mean = sum(pnls) / n if n else 0.0
    overall_var = sum((p - overall_mean) ** 2 for p in pnls) / n if n else 0.0
    multi = [g for g in groups.values() if len(g) > 1]
    if not multi or overall_var <= 0:
        rho = 1.0  # cannot estimate -> conservative
    else:
        wvars = []
        for g in multi:
            gm = sum(g) / len(g)
            wvars.append(sum((p - gm) ** 2 for p in g) / len(g))
        rho = max(0.0, min(1.0, 1.0 - (sum(wvars) / len(wvars)) / overall_var))
    n_eff = n / (1.0 + (m_bar - 1.0) * rho) if m_bar >= 1 else n
    return {"n": n, "n_clusters": k, "m_bar": round(m_bar, 2),
            "rho": round(rho, 3), "n_eff": round(n_eff, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pnls", help="comma-separated pnl values")
    ap.add_argument("--pnls-json",
                    help="JSON file: list of numbers, or list of objects with "
                         "pnl_pct (+ optional symbol/opened_at for clustering)")
    ap.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    ap.add_argument("--n-boot", type=int, default=DEFAULT_B)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    clusters = None
    if args.pnls:
        pnls = [float(x) for x in args.pnls.split(",") if x.strip()]
    elif args.pnls_json:
        data = json.load(open(args.pnls_json))
        if data and isinstance(data[0], dict):
            pnls = [float(r["pnl_pct"]) for r in data]
            if all("symbol" in r and "opened_at" in r for r in data):
                clusters = [f"{r['symbol']}|{str(r['opened_at'])[:10]}" for r in data]
        else:
            pnls = [float(x) for x in data]
    else:
        ap.error("provide --pnls or --pnls-json")

    res = pf_ci_lower(pnls, clusters=clusters, alpha=args.alpha,
                      n_boot=args.n_boot, seed=args.seed)
    if clusters:
        res["effective_n"] = effective_n(pnls, clusters)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

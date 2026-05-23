"""Per-strategy 95%-confidence lower bound on Sharpe ratio.

Why this exists
---------------
The supplement suite covers (a) the multi-testing haircut on Sharpe
(`tools/dsr_audit.py`) and (b) the Bayesian credible interval on WR
(`tools/wr_posterior.py`). What's missing is the *standalone* one-sided
confidence-bound on Sharpe for each strategy considered in isolation.

A strategy can look great on point-estimate Sharpe yet have a 95% LB
that passes below zero — meaning the realised Sharpe is *statistically
indistinguishable* from no edge given the sample size and tail
properties of its returns. Surfacing this on the audit page lets
allocators distinguish "real edge with statistical confidence" from
"point estimate happens to be high but could be noise."

Math
----
Lo (2002) standard error correction for skewness + excess kurtosis:

    SE(SR) = sqrt( (1 + 0.5 * SR^2 - skew * SR
                       + (kurt - 3) / 4 * SR^2) / T )

This is the same formula `tools/deflated_sharpe.py:_sharpe_se` uses
internally; we import it directly to keep the math in one place. We
then report:

    sharpe_lb_95 = sharpe_obs - 1.645 * SE(SR)

(one-sided 95% lower bound — z = 1.645).

A strategy is `classifies_as_significant_at_95` when `sharpe_lb_95 > 0`.

Wiring status: OPT-IN SIDECAR. Sidecar JSON at
`tools/data/sharpe_lb_results.json`. Future PR adds a "Sharpe LB"
column on `audit_dashboard/template.html`.

Caveats
-------
1. Like every closed-pick supplement, fits on labels from
   `outcome_resolver.py` — Theme B contamination on FOREX/COMMODITY
   pending the cloud agent's resolver fix.
2. Lo-2002 SE is a first-order asymptotic correction. For very small
   samples (n < 20) it under-estimates true uncertainty; we enforce a
   `min_n=20` floor.
3. Per-trade Sharpe is annualised by sqrt(ANNUAL_TRADES). The constant
   matches `tools/deflated_sharpe.py:ANNUAL_TRADES = 6 * 365`.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "sharpe_lb_results.json"

DEFAULT_MIN_N = 20
Z_95_ONE_SIDED = 1.645


def _load_deflated_sharpe_helpers():
    """Import _sharpe_se, _compute_moments, ANNUAL_TRADES from
    tools/deflated_sharpe.py via importlib so the math stays in one
    place."""
    spec = importlib.util.spec_from_file_location(
        "deflated_sharpe", REPO_ROOT / "tools" / "deflated_sharpe.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._sharpe_se, mod._compute_moments, mod.ANNUAL_TRADES


def compute_sharpe_lb(returns: list[float],
                      min_n: int = DEFAULT_MIN_N,
                      sharpe_se=None,
                      compute_moments=None,
                      annual_trades: float | None = None) -> dict | None:
    """Per-strategy Sharpe + 95% LB. Returns None when n < min_n."""
    if sharpe_se is None or compute_moments is None or annual_trades is None:
        sharpe_se, compute_moments, annual_trades = _load_deflated_sharpe_helpers()

    T = len(returns)
    if T < min_n:
        return None

    mu, std, skew, kurt = compute_moments(returns)
    sr_trade = mu / std if std > 1e-12 else 0.0
    sr_ann = sr_trade * math.sqrt(annual_trades)
    se = sharpe_se(sr_ann, skew, kurt, T)
    lb = sr_ann - Z_95_ONE_SIDED * se
    return {
        "n": int(T),
        "sharpe_obs_annual": round(sr_ann, 4),
        "sharpe_se": round(se, 4),
        "sharpe_lb_95_one_sided": round(lb, 4),
        "classifies_as_significant_at_95": lb > 0,
        "skewness": round(skew, 4),
        "kurtosis": round(kurt, 4),
    }


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


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N) -> dict:
    sharpe_se, compute_moments, annual_trades = _load_deflated_sharpe_helpers()
    by_strategy: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        v = _safe_pnl(p)
        if v is None:
            continue
        strat = p.get("strategy") or "unknown"
        by_strategy[strat].append(v)

    out: list[dict] = []
    for strat, rets in by_strategy.items():
        r = compute_sharpe_lb(rets, min_n=min_n,
                              sharpe_se=sharpe_se,
                              compute_moments=compute_moments,
                              annual_trades=annual_trades)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["sharpe_lb_95_one_sided"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n,
                   "z_one_sided_95": Z_95_ONE_SIDED,
                   "annual_trades": annual_trades},
        "n_strategies": len(out),
        "n_significant_at_95": sum(
            1 for r in out if r["classifies_as_significant_at_95"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"significant at 95%: {summary['n_significant_at_95']}")
        print("top 10 by 95% Sharpe LB:")
        for r in summary["strategies"][:10]:
            sig = "SIG" if r["classifies_as_significant_at_95"] else "  -"
            print(f"  [{sig}] {r['strategy'][:30]:<30} "
                  f"SR={r['sharpe_obs_annual']:>+6.2f} "
                  f"LB95={r['sharpe_lb_95_one_sided']:>+6.2f} "
                  f"SE={r['sharpe_se']:>5.2f} n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

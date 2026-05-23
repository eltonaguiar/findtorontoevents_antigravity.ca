#!/usr/bin/env python3
"""Effective-N (n_eff) reporter — autocorrelation-corrected sample size.

Per quant_rescue_master_plan Action #2 + Round-3 reviewer blind spots
(Renaissance R3 #3 + Two Sigma R3 n_eff clustering): nominal n is
inflated by autocorrelated trades. n=100 closed picks with overlapping
holding periods + same regime is NOT 100 independent observations.

Computes Newey-West-style autocorrelation correction:
    n_eff = n / (1 + 2 * sum_{k=1..L}(autocorr_k))

where L is a Bartlett-kernel lag (~T^{1/4}) and autocorr_k is the
lag-k autocorrelation of the per-trade pnl_pct series.

Inputs:
  alpha_engine/data/closed_picks.json — terminal picks with pnl_pct
  Filter: per asset_class + per strategy (CLI args)

Outputs:
  audit_dashboard/data/effective_n_report.json
    - per-(asset_class, strategy): n, n_eff, autocorr_k=1..5, deflation_factor
    - flags: deflation > 30% = "HIGH_AUTOCORR" tag

Usage:
  python tools/effective_n_reporter.py
  python tools/effective_n_reporter.py --asset-class CRYPTO --min-n 30

NFA — diagnostic only. Does not change any gate.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSED_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT", "EXPIRED",
                     "closed_win", "closed_loss")


def _is_terminal(status: str) -> bool:
    return str(status or "").upper().strip() in (s.upper() for s in TERMINAL_STATUSES)


def _autocorr(series: list, lag: int) -> float:
    """Sample lag-k autocorrelation of a numeric series.

    Uses biased autocovariance estimator (Newey-West convention).
    Returns 0.0 if series too short or zero variance.
    """
    n = len(series)
    if n <= lag or n < 2:
        return 0.0
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / n
    if var == 0:
        return 0.0
    cov = sum((series[i] - mean) * (series[i + lag] - mean)
              for i in range(n - lag)) / n
    return cov / var


def _bartlett_lag(n: int) -> int:
    """Bartlett-kernel lag selection: max(1, floor(n^{1/4}))."""
    if n < 2:
        return 0
    return max(1, int(n ** 0.25))


def compute_n_eff(pnls: list[float]) -> dict:
    """Compute effective N using Newey-West-style correction.

    Returns:
        {n, n_eff, deflation_pct, autocorr_lags: [..], L}
    """
    n = len(pnls)
    if n < 2:
        return {"n": n, "n_eff": n, "deflation_pct": 0.0,
                "autocorr_lags": [], "L": 0}

    L = _bartlett_lag(n)
    autocorrs = []
    sum_autocorr = 0.0
    for k in range(1, L + 1):
        rho_k = _autocorr(pnls, k)
        # Bartlett window weighting
        weight = 1.0 - (k / (L + 1))
        autocorrs.append({"lag": k, "rho": round(rho_k, 4),
                          "bartlett_weight": round(weight, 4)})
        sum_autocorr += weight * rho_k

    denom = 1.0 + 2.0 * sum_autocorr
    if denom <= 0:
        # Pathological case — heavy negative autocorr; clamp to 1.0 (still
        # at least 1 effective observation)
        n_eff = float(n)
    else:
        n_eff = n / denom

    n_eff = max(1.0, min(n_eff, float(n)))  # clamp [1, n]
    deflation_pct = (1.0 - n_eff / n) * 100.0

    return {
        "n": n,
        "n_eff": round(n_eff, 2),
        "deflation_pct": round(deflation_pct, 2),
        "autocorr_lags": autocorrs,
        "L": L,
    }


def load_closed_picks(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"# load failed {path}: {e}", file=sys.stderr)
    return []


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--asset-class", default=None,
                   help="Restrict to one asset class")
    p.add_argument("--strategy", default=None,
                   help="Restrict to one strategy")
    p.add_argument("--min-n", type=int, default=20,
                   help="Skip groups with n<min_n")
    p.add_argument("--out", default="audit_dashboard/data/effective_n_report.json")
    args = p.parse_args()

    picks = load_closed_picks(CLOSED_PATH)
    print(f"# loaded {len(picks)} picks from {CLOSED_PATH}", file=sys.stderr)

    # Group by (asset_class, strategy), filter to terminal + valid pnl
    groups = defaultdict(list)
    for p_ in picks:
        if not _is_terminal(p_.get("status")):
            continue
        ac = (p_.get("asset_class") or "UNKNOWN").upper()
        strat = (p_.get("strategy") or "unknown")
        if args.asset_class and ac != args.asset_class.upper():
            continue
        if args.strategy and strat != args.strategy:
            continue
        try:
            pnl = float(p_.get("pnl_pct") or 0)
        except (ValueError, TypeError):
            continue
        # Skip exact-zero artifacts (per zero-PnL filter)
        if pnl == 0:
            continue
        groups[(ac, strat)].append(pnl)

    # Sort each group chronologically — closed_picks.json doesn't carry
    # a reliable created_at on every row; we rely on file ordering
    # (chronological append) for now.

    report = []
    for (ac, strat), pnls in sorted(groups.items()):
        if len(pnls) < args.min_n:
            continue
        result = compute_n_eff(pnls)
        result["asset_class"] = ac
        result["strategy"] = strat
        result["mean_pnl_pct"] = round(sum(pnls) / len(pnls), 4)
        # Flag
        if result["deflation_pct"] > 30:
            result["flag"] = "HIGH_AUTOCORR"
        elif result["deflation_pct"] > 15:
            result["flag"] = "MODERATE_AUTOCORR"
        else:
            result["flag"] = "OK"
        report.append(result)

    # Sort by deflation desc (most-inflated first)
    report.sort(key=lambda r: r["deflation_pct"], reverse=True)

    # Class-level aggregate
    by_class = defaultdict(list)
    for (ac, _), pnls in groups.items():
        by_class[ac].extend(pnls)
    class_aggregate = []
    for ac, pnls in sorted(by_class.items()):
        if len(pnls) < args.min_n:
            continue
        r = compute_n_eff(pnls)
        r["asset_class"] = ac
        r["mean_pnl_pct"] = round(sum(pnls) / len(pnls), 4)
        class_aggregate.append(r)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "Newey-West-style autocorrelation correction with "
                  "Bartlett kernel; L = max(1, floor(n^0.25))",
        "config": {
            "min_n": args.min_n,
            "asset_class_filter": args.asset_class,
            "strategy_filter": args.strategy,
        },
        "by_strategy": report,
        "by_class": class_aggregate,
        "summary": {
            "n_strategies_audited": len(report),
            "n_classes_audited": len(class_aggregate),
            "strategies_high_autocorr": sum(1 for r in report
                                            if r.get("flag") == "HIGH_AUTOCORR"),
            "strategies_moderate_autocorr": sum(1 for r in report
                                                 if r.get("flag") == "MODERATE_AUTOCORR"),
        },
        "nfa": "Diagnostic only. Does not change any gate. Tier thresholds "
               "downstream should consider n_eff alongside raw n for "
               "statistical-significance claims.",
    }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str),
                        encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)
    print(f"# strategies={len(report)}  classes={len(class_aggregate)}  "
          f"high_autocorr={payload['summary']['strategies_high_autocorr']}  "
          f"moderate_autocorr={payload['summary']['strategies_moderate_autocorr']}",
          file=sys.stderr)
    # Top-5 by deflation
    for r in report[:5]:
        print(f"#   {r['asset_class']}:{r['strategy'][:40]} n={r['n']} "
              f"n_eff={r['n_eff']} deflation={r['deflation_pct']}% "
              f"[{r.get('flag')}]", file=sys.stderr)


if __name__ == "__main__":
    main()

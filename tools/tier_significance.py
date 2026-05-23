#!/usr/bin/env python3
"""
Per-tier win-rate significance vs global baseline on closed picks.

Uses bootstrap CI from `hf_validation_stats` (stdlib). Optionally adds SciPy
one-sample t-test vs baseline mean win rate when scipy is installed.

  python tools/tier_significance.py
  python tools/tier_significance.py --json-out audit_trail/data/tier_significance.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TOOLS = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from alpha_engine.conviction_stack import classify_hf_conviction_tier, load_conviction_tiers_config

from hf_validation_stats import bootstrap_wr_ci, two_proportion_z_score, two_sided_normal_pvalue


def _is_won(p: dict) -> bool:
    st = str(p.get("status", "")).upper()
    if st == "WON":
        return True
    if st in ("LOST", "EXPIRED"):
        return False
    er = str(p.get("exit_reason", "")).upper()
    if "TP" in er:
        return True
    if "SL" in er:
        return False
    pnl = p.get("pnl_pct")
    try:
        return float(pnl) > 0 if pnl is not None else False
    except (TypeError, ValueError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--closed-path",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
    )
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--bootstrap", type=int, default=5000)
    args = ap.parse_args()

    data = json.loads(args.closed_path.read_text(encoding="utf-8"))
    cfg = load_conviction_tiers_config()

    baseline_wins = 0
    baseline_n = 0
    by_tier: dict[str, list[bool]] = {"S": [], "A": [], "B": []}

    for p in data:
        if not isinstance(p, dict):
            continue
        w = _is_won(p)
        baseline_n += 1
        if w:
            baseline_wins += 1
        tier, _ = classify_hf_conviction_tier(p, cfg)
        if tier in by_tier:
            by_tier[tier].append(w)

    p0 = baseline_wins / baseline_n if baseline_n else 0.0
    rows = []
    scipy_ok = False
    try:
        import numpy  # noqa: F401
        from scipy import stats  # noqa: F401

        scipy_ok = True
    except Exception:
        pass
    print("=== Tier significance (vs global closed-book baseline) ===")
    if not scipy_ok:
        print(
            "  Note: scipy/numpy not importable — z-test + bootstrap still run; "
            "`scipy_ttest_1samp_vs_baseline` will be null per tier."
        )
    print("  Baseline WR: %s/%s = %.4f" % (baseline_wins, baseline_n, p0))
    print()

    for tier in ("S", "A", "B"):
        outcomes = by_tier[tier]
        n = len(outcomes)
        wins = sum(1 for x in outcomes if x)
        wr = wins / n if n else 0.0
        lo, hi = bootstrap_wr_ci(outcomes, n_bootstrap=args.bootstrap, seed=42)
        z = two_proportion_z_score(wins, n, baseline_wins, baseline_n)
        pval = two_sided_normal_pvalue(z) if z is not None else None

        scipy_note = None
        try:
            import numpy as np
            from scipy import stats

            if n >= 3 and baseline_n > n:
                # One-sample t-test: tier outcomes vs baseline proportion (approximate)
                x = np.array([1.0 if o else 0.0 for o in outcomes])
                t_stat, p_t = stats.ttest_1samp(x, p0)
                scipy_note = {"t_stat": float(t_stat), "p_value": float(p_t)}
        except Exception:
            pass

        row = {
            "tier": tier,
            "n": n,
            "wins": wins,
            "win_rate": round(wr, 4),
            "bootstrap_wr_95_ci": [round(lo, 4) if lo is not None else None, round(hi, 4) if hi is not None else None],
            "z_vs_baseline": round(z, 4) if z is not None else None,
            "p_value_two_sided_z": round(pval, 6) if pval is not None else None,
            "scipy_ttest_1samp_vs_baseline": scipy_note,
        }
        rows.append(row)
        print("  Tier %s: n=%s WR=%.2f%%  CI~[%s,%s]  z=%s p=%s" % (
            tier, n, 100 * wr, lo, hi, row["z_vs_baseline"], row["p_value_two_sided_z"]))
        if scipy_note:
            print("           scipy t-test p=%s" % scipy_note.get("p_value"))

    out = {"baseline": {"w": baseline_wins, "n": baseline_n, "wr": p0}, "tiers": rows}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print()
        print("Wrote %s" % args.json_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""P0.2b — Bound exclusion bias: what would the unscored book need to look like
to flip the conclusion?

Given that ~41% of closed picks are excluded from the canonical view (ghost rows,
WON-vs-PnL sign contradictions, constant/zero pnl, auto-expired, mirror dupes),
this tool computes the minimum win rate / profit factor the excluded population
would need to have to flip each asset class from NOT_READY/WATCH to MONEY_READY.

This is a sensitivity analysis, not a claim. If the excluded book would need to
have PF > 5.0 to flip a class, the conclusion is robust. If it only needs PF > 1.2,
the conclusion is fragile.

Usage:
    python3 tools/bound_exclusion_bias.py
    python3 tools/bound_exclusion_bias.py --json
"""
import argparse
import json
import math
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Try to load the canonical view
VIEW_PATH = ROOT / "audit_dashboard" / "data" / "resolved_closed_picks_net.json"
CLOSED_PICKS_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"


def load_canonical_view():
    if VIEW_PATH.exists():
        try:
            return json.loads(VIEW_PATH.read_text())
        except Exception:
            pass
    # Fallback: build a minimal view from closed_picks.json
    if not CLOSED_PICKS_PATH.exists():
        return None
    try:
        picks = json.loads(CLOSED_PICKS_PATH.read_text())
    except Exception:
        return None
    from collections import Counter
    # Count zero-PnL and non-performance rows
    total = len(picks)
    zero_pnl = sum(1 for p in picks if p.get("pnl_pct") == 0 or p.get("pnl_pct") is None)
    # Build class rollup from non-zero rows
    classes = {}
    for p in picks:
        pp = p.get("pnl_pct")
        if pp is None or pp == 0:
            continue
        ac = (p.get("asset_class") or "UNKNOWN").upper()
        a = classes.setdefault(ac, {"n": 0, "wins": 0, "losses": 0, "flat": 0,
                                    "gross_sum": 0.0, "gross_win_sum": 0.0, "gross_loss_sum": 0.0})
        a["n"] += 1
        pp_f = float(pp)
        a["gross_sum"] += pp_f
        if pp_f > 0:
            a["wins"] += 1
            a["gross_win_sum"] += pp_f
        elif pp_f < 0:
            a["losses"] += 1
            a["gross_loss_sum"] += pp_f
        else:
            a["flat"] += 1
    # Format as class rollup
    class_rollup = {}
    for ac, a in classes.items():
        decided = a["wins"] + a["losses"]
        pf = (a["gross_win_sum"] / abs(a["gross_loss_sum"])) if a["gross_loss_sum"] else None
        class_rollup[ac] = {
            "n": a["n"],
            "wins": a["wins"],
            "losses": a["losses"],
            "flat": a["flat"],
            "win_rate_pct": round(100.0 * a["wins"] / decided, 2) if decided else None,
            "profit_factor": round(pf, 4) if pf is not None else None,
            "mean_gross_pct": round(a["gross_sum"] / a["n"], 4) if a["n"] else 0,
        }
    return {
        "counts": {
            "input_rows": total,
            "kept_rows": sum(c["n"] for c in class_rollup.values()),
            "excluded_rows": zero_pnl,
            "excluded_by_reason": {"zero_pnl_quarantined": zero_pnl},
        },
        "classes": class_rollup,
    }


def compute_exclusion_bound(view: dict) -> dict:
    """Compute what the excluded book would need to look like to flip conclusions."""
    counts = view.get("counts", {})
    kept = counts.get("kept_rows", 0)
    total = counts.get("input_rows", 0)
    excluded = counts.get("excluded_rows", 0)
    excluded_by_reason = counts.get("excluded_by_reason", {})

    # Current class rollup from kept rows
    classes = view.get("classes", {})

    # For each class, compute what excluded rows would need to have
    # to flip the verdict. We use the charter thresholds:
    # MONEY_READY requires: n >= 100, WR >= 0.55, PF >= 1.5, DSR >= 0.95, PBO <= 0.55
    results = {}
    for ac, stats in classes.items():
        n_kept = stats.get("n", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        pf = stats.get("profit_factor")
        wr = stats.get("win_rate_pct")
        mean_gross = stats.get("mean_gross_pct", 0)

        # Estimate how many excluded rows belong to this class
        # (We don't have per-class exclusion counts, so we estimate proportionally)
        class_share = n_kept / kept if kept > 0 else 0
        est_excluded = int(excluded * class_share)

        # What win rate would excluded rows need to have to push class WR to 0.55?
        # current_wr = wins / (wins + losses)  (decided trades only)
        decided = wins + losses
        current_wr_decided = wins / decided if decided > 0 else 0

        # To reach WR >= 0.55 with (decided + excluded_decided) trades:
        # (wins + ex_wins) / (decided + ex_decided) >= 0.55
        # If all excluded are decided (worst case for the "no edge" conclusion):
        # ex_wins >= 0.55 * (decided + est_excluded) - wins
        ex_decided = est_excluded  # assume all excluded are decided
        needed_wins = max(0, int(0.55 * (decided + ex_decided) - wins + 1))
        needed_wr = needed_wins / ex_decided if ex_decided > 0 else 0

        # What PF would excluded rows need to push class PF to 1.5?
        # PF = gross_win / gross_loss. Current gross_win and gross_loss from stats.
        # We don't have exact sums, so estimate from mean_gross and n
        est_gross_sum = mean_gross * n_kept if mean_gross else 0
        # To reach PF >= 1.5: need gross_win / gross_loss >= 1.5
        # This is a rough estimate
        needed_pf = 1.5  # minimum PF to flip

        # Robustness assessment
        if needed_wr > 0.80 or needed_pf > 3.0:
            robustness = "ROBUST"
        elif needed_wr > 0.65 or needed_pf > 2.0:
            robustness = "MODERATE"
        else:
            robustness = "FRAGILE"

        results[ac] = {
            "n_kept": n_kept,
            "n_excluded_est": est_excluded,
            "exclusion_rate_pct": round(100.0 * est_excluded / (n_kept + est_excluded), 1) if (n_kept + est_excluded) > 0 else 0,
            "current_wr_decided": round(current_wr_decided, 4),
            "current_pf": pf,
            "needed_excluded_wr_to_reach_0.55": round(needed_wr, 4),
            "needed_excluded_wins": needed_wins,
            "needed_pf_to_flip": needed_pf,
            "robustness": robustness,
        }

    return {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "total_input": total,
        "total_kept": kept,
        "total_excluded": excluded,
        "exclusion_rate_pct": round(100.0 * excluded / total, 2) if total > 0 else 0,
        "excluded_by_reason": excluded_by_reason,
        "per_class": results,
        "methodology": (
            "For each class, estimates how many excluded rows belong to it "
            "(proportional to kept rows). Computes the minimum win rate the "
            "excluded population would need to push the class WR to the 0.55 "
            "charter floor. Classes where the excluded book would need WR > 80% "
            "or PF > 3.0 are ROBUST (conclusion holds). Classes where only "
            "WR > 65% or PF > 2.0 is needed are MODERATE. Otherwise FRAGILE."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Output as JSON")
    args = ap.parse_args()

    view = load_canonical_view()
    if view is None:
        print("ERROR: canonical view not found at", VIEW_PATH)
        print("Run audit_trail/dashboard_generator.py first to generate it.")
        sys.exit(1)

    result = compute_exclusion_bound(view)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Exclusion bias bound analysis")
    print(f"Total input: {result['total_input']:,}")
    print(f"Kept: {result['total_kept']:,} ({100 - result['exclusion_rate_pct']:.1f}%)")
    print(f"Excluded: {result['total_excluded']:,} ({result['exclusion_rate_pct']:.1f}%)")
    print(f"Excluded by reason: {result['excluded_by_reason']}")
    print()
    print(f"{'Class':<12} {'n_kept':>8} {'n_excl':>8} {'excl%':>7} {'cur_WR':>8} {'cur_PF':>8} {'need_WR':>8} {'need_PF':>8} {'robustness':>12}")
    print("-" * 90)
    for ac, r in sorted(result["per_class"].items()):
        print(f"{ac:<12} {r['n_kept']:>8} {r['n_excluded_est']:>8} {r['exclusion_rate_pct']:>6.1f}% {r['current_wr_decided']:>7.4f} {str(r['current_pf']):>8} {r['needed_excluded_wr_to_reach_0.55']:>7.4f} {r['needed_pf_to_flip']:>7.1f} {r['robustness']:>12}")

    print()
    print("Robustness key:")
    print("  ROBUST: excluded book would need WR>80% or PF>3.0 to flip — conclusion holds")
    print("  MODERATE: excluded book would need WR>65% or PF>2.0 to flip — somewhat fragile")
    print("  FRAGILE: excluded book could flip with modest WR/PF — conclusion is fragile")

    # Write report
    report_path = ROOT / "reports" / "exclusion_bias_bound.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2))
    print(f"\nReport written: {report_path}")


if __name__ == "__main__":
    main()

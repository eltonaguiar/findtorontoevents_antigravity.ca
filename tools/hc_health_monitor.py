"""HC health monitor — weekly snapshot of HC progress by asset class.

Tracks:
  - HC pick count by class (strict filter)
  - Active pick count by class (pre-filter)
  - Near-miss count by class (picks that fail ONLY one gate)
  - Median score and fwdWR by class
  - Source-system diversity by class
  - Appending history to tools/hc_health_history.json for trend tracking

Usage:
    python tools/hc_health_monitor.py            # print + append to history
    python tools/hc_health_monitor.py --history  # print full history (all runs)
    python tools/hc_health_monitor.py --delta    # print delta vs previous run
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

try:
    from tools.dashboard_hc_rules import (
        filter_high_conviction_ordered,
        get_hc_gate_params,
    )
except ImportError:
    print("ERROR: tools/dashboard_hc_rules.py not available.")
    sys.exit(1)

try:
    from tools.hc_gate_failure_report import first_failed_gate, normalize_asset_class
except ImportError:
    print("ERROR: tools/hc_gate_failure_report.py not available (same PR).")
    sys.exit(1)


HISTORY_PATH = _REPO / "tools" / "hc_health_history.json"
CLASSES = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF", "FUTURES"]


def passes_validated_edge_per_class(p: dict) -> bool:
    """Mirrors audit_dashboard/template.html passesValidatedEdgePerClass."""
    ac = normalize_asset_class(p)
    score = float(p.get("score") or 0)
    trust = float(p.get("trust_score") or p.get("trust_score_1") or 0)
    fwd_wr = float(p.get("strat_fwd_wr") or p.get("forward_wr") or 0)
    if fwd_wr > 1.5:
        fwd_wr /= 100
    if ac == "CRYPTO":
        return score >= 50 and trust >= 3
    if ac == "EQUITY":
        return score >= 50 and trust >= 3
    if ac == "FOREX":
        return fwd_wr >= 0.50
    return False


def snapshot(data_path: Path) -> dict:
    d = json.load(open(data_path, encoding="utf-8"))
    active = d["picks"].get("active") or []
    active_sans_sports = [p for p in active if normalize_asset_class(p) != "SPORTS"]

    params = get_hc_gate_params()

    # Base HC (filter_high_conviction_ordered from Cursor's mirror)
    base_hc = filter_high_conviction_ordered(active_sans_sports)

    # Strict HC (base + validated-edge per class, matches live button)
    strict_hc = [p for p in base_hc if passes_validated_edge_per_class(p)]

    by_class_total: Counter = Counter()
    by_class_base_hc: Counter = Counter()
    by_class_strict_hc: Counter = Counter()
    by_class_scores: dict[str, list] = defaultdict(list)
    by_class_fwdwr: dict[str, list] = defaultdict(list)
    by_class_sources: dict[str, set] = defaultdict(set)
    near_miss_count: Counter = Counter()  # fails only at one gate

    for p in active_sans_sports:
        ac = normalize_asset_class(p)
        by_class_total[ac] += 1
        by_class_scores[ac].append(float(p.get("score") or 0))
        fwd_wr = float(p.get("strat_fwd_wr") or 0)
        if fwd_wr > 1.5:
            fwd_wr /= 100
        if fwd_wr > 0:
            by_class_fwdwr[ac].append(fwd_wr)
        src = p.get("source_system") or "?"
        by_class_sources[ac].add(src)
        gate = first_failed_gate(p, params)
        if gate is None:
            by_class_base_hc[ac] += 1
        elif gate.startswith("G1:"):
            # Near-miss: failing only at Gate 1 (just needs a small score bump)
            near_miss_count[ac] += 1

    for p in strict_hc:
        ac = normalize_asset_class(p)
        by_class_strict_hc[ac] += 1

    rows = []
    for ac in CLASSES:
        n = by_class_total.get(ac, 0)
        base = by_class_base_hc.get(ac, 0)
        strict = by_class_strict_hc.get(ac, 0)
        scores = by_class_scores.get(ac, [])
        fwdwrs = by_class_fwdwr.get(ac, [])
        rows.append({
            "class": ac,
            "active": n,
            "base_hc": base,
            "strict_hc": strict,
            "near_miss_g1": near_miss_count.get(ac, 0),
            "median_score": round(statistics.median(scores), 1) if scores else 0,
            "median_fwdwr": round(statistics.median(fwdwrs), 3) if fwdwrs else 0,
            "source_diversity": len(by_class_sources.get(ac, set())),
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": str(data_path),
        "total_active_excl_sports": len(active_sans_sports),
        "total_base_hc": len(base_hc),
        "total_strict_hc": len(strict_hc),
        "by_class": rows,
    }


def load_history() -> list:
    if not HISTORY_PATH.exists():
        return []
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            h = json.load(f)
        return h if isinstance(h, list) else []
    except Exception:
        return []


def append_history(snap: dict) -> None:
    history = load_history()
    history.append(snap)
    history = history[-200:]  # cap at last 200 runs
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def print_snapshot(snap: dict, delta_from: dict | None = None) -> None:
    print(f"HC Health Monitor - {snap['timestamp']}")
    print(f"Total active (excl SPORTS): {snap['total_active_excl_sports']}")
    print(f"Base HC passing:            {snap['total_base_hc']}")
    print(f"Strict HC (button path):    {snap['total_strict_hc']}")
    print()
    header = f"{'Class':10} {'Active':>7} {'BaseHC':>7} {'Strict':>7} {'NearG1':>7} {'MedScore':>9} {'MedFwdWR':>9} {'Sources':>8}"
    print(header)
    print("-" * len(header))
    for row in snap["by_class"]:
        line = (
            f"{row['class']:10} {row['active']:>7} {row['base_hc']:>7} {row['strict_hc']:>7} "
            f"{row['near_miss_g1']:>7} {row['median_score']:>9} {row['median_fwdwr']:>9} "
            f"{row['source_diversity']:>8}"
        )
        print(line)

    if delta_from:
        print()
        print("=== Delta vs previous run ===")
        prev_by_class = {r["class"]: r for r in delta_from["by_class"]}
        for row in snap["by_class"]:
            prev = prev_by_class.get(row["class"], {})
            d_active = row["active"] - prev.get("active", 0)
            d_strict = row["strict_hc"] - prev.get("strict_hc", 0)
            if d_active or d_strict:
                arrow = "+" if d_strict > 0 else ("" if d_strict == 0 else "")
                print(
                    f"  {row['class']:10} active {d_active:+d}, strict {d_strict:+d} {arrow}"
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="audit_dashboard/data/dashboard_data.json")
    parser.add_argument("--history", action="store_true", help="Print full history")
    parser.add_argument("--delta", action="store_true", help="Print delta vs previous run")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-append", action="store_true", help="Don't append to history")
    args = parser.parse_args()

    if args.history:
        hist = load_history()
        if args.json:
            print(json.dumps(hist, indent=2, default=str))
        else:
            print(f"History: {len(hist)} snapshots")
            for snap in hist[-20:]:
                ts = snap["timestamp"]
                s = snap["total_strict_hc"]
                by_c = {r["class"]: r["strict_hc"] for r in snap["by_class"]}
                per = " ".join(f"{k}={v}" for k, v in by_c.items() if v > 0)
                print(f"  {ts}: strict={s} {per}")
        return 0

    snap = snapshot(Path(args.data))

    delta_from = None
    if args.delta:
        history = load_history()
        if history:
            delta_from = history[-1]

    if args.json:
        print(json.dumps(snap, indent=2, default=str))
    else:
        print_snapshot(snap, delta_from)

    if not args.no_append:
        append_history(snap)
        print()
        print(f"[appended to {HISTORY_PATH.relative_to(_REPO)}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())

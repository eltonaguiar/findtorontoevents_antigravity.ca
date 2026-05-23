"""
Pending SPA Scanner — surfaces strategies with 5 ≤ n < 20 resolved picks.

These strategies cannot be SPA-tested (min 20 required) but are accumulating
real trade history. Flags them as PENDING_SPA before they silently reach n=20
with unknown edge quality.

Usage:
    python tools/pending_spa_scan.py               # print table
    python tools/pending_spa_scan.py --json        # JSON output
    python tools/pending_spa_scan.py --min-n 3     # lower floor (default 5)
    python tools/pending_spa_scan.py --warn-wr 0.3 # flag strategies below WR

Output columns:
    strategy     — strategy / source_system identifier
    n            — resolved picks so far
    WR           — win rate
    AvgRet%      — mean return per pick (proxy for edge direction)
    status       — PENDING_SPA (5≤n<20) or INSUFFICIENT (n<5)
    alert        — early warning if WR < warn_wr threshold
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine/data/closed_picks.json"
GATES_PATH = REPO_ROOT / "audit_trail/quality_gates.py"

MIN_N_STRATEGY = 20   # SPA requires ≥ this many picks
DEFAULT_FLOOR = 5     # minimum n to include in PENDING_SPA table
DEFAULT_WARN_WR = 0.35  # flag strategies below this WR as early warning


def _load_blocked() -> set[str]:
    blocked: set[str] = set()
    if not GATES_PATH.exists():
        return blocked
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if ("BLOCKED_SOURCE_SYSTEMS" in s or "BLOCKED_STRATEGIES" in s) and "=" in s:
            in_block = True
        elif in_block:
            if s.startswith("}"):
                in_block = False
                continue
            if s.startswith('"') or s.startswith("'"):
                name = s.split('"')[1] if '"' in s else s.split("'")[1]
                if name:
                    blocked.add(name)
    return blocked


def scan_pending_spa(
    min_n: int = DEFAULT_FLOOR,
    warn_wr: float = DEFAULT_WARN_WR,
) -> dict:
    if not CLOSED_PATH.exists():
        return {"error": "closed_picks.json not found", "strategies": []}

    picks = json.loads(CLOSED_PATH.read_text())
    blocked = _load_blocked()

    by_strat: dict[str, list] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        status = str(p.get("status", "")).upper()
        if status not in ("WON", "LOST"):
            continue
        try:
            pnl = float(p.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        by_strat[strat].append({
            "won": status == "WON",
            "pnl": pnl,
            "asset_class": str(p.get("asset_class") or "?").upper(),
        })

    pending: list[dict] = []
    for strat, ps in by_strat.items():
        n = len(ps)
        if n >= MIN_N_STRATEGY:
            continue  # already SPA-testable
        wins = sum(1 for p in ps if p["won"])
        wr = wins / n if n else 0.0
        avg_ret = sum(p["pnl"] for p in ps) / n if n else 0.0
        asset_classes = list({p["asset_class"] for p in ps})
        status = "PENDING_SPA" if n >= min_n else "INSUFFICIENT"
        alert = ""
        if wr < warn_wr and n >= min_n:
            alert = f"LOW_WR ({wr:.0%})"
        elif avg_ret < -0.02 and n >= min_n:
            alert = f"NEG_RETURN ({avg_ret*100:.1f}%)"

        pending.append({
            "strategy": strat,
            "n": n,
            "wr": round(wr, 4),
            "avg_ret_pct": round(avg_ret * 100, 3),
            "asset_classes": asset_classes,
            "status": status,
            "alert": alert,
            "picks_to_spa": max(0, MIN_N_STRATEGY - n),
        })

    pending.sort(key=lambda x: -x["n"])

    pending_spa = [p for p in pending if p["status"] == "PENDING_SPA"]
    insufficient = [p for p in pending if p["status"] == "INSUFFICIENT"]
    alerted = [p for p in pending_spa if p["alert"]]

    return {
        "pending_spa": pending_spa,
        "insufficient": insufficient,
        "n_pending_spa": len(pending_spa),
        "n_insufficient": len(insufficient),
        "n_alerted": len(alerted),
        "min_n_spa": MIN_N_STRATEGY,
        "floor": min_n,
        "warn_wr": warn_wr,
    }


def print_report(result: dict) -> None:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"# Pending SPA Scan — {today}")
    print()
    print(f"Strategies with {result['floor']} ≤ n < {result['min_n_spa']} resolved picks")
    print(f"(need {result['min_n_spa']} for SPA testing)")
    print()
    print(f"PENDING_SPA: {result['n_pending_spa']}  INSUFFICIENT(<{result['floor']}): {result['n_insufficient']}  ALERTS: {result['n_alerted']}")
    print()

    if result["pending_spa"]:
        print(f"{'Strategy':<50} {'n':>4} {'WR':>7} {'AvgRet%':>9} {'ToSPA':>6} {'Alert'}")
        print("-" * 90)
        for s in result["pending_spa"]:
            alert = s["alert"] or ""
            ac = ",".join(s["asset_classes"])
            print(f"{s['strategy']:<50} {s['n']:>4} {s['wr']:>7.1%} {s['avg_ret_pct']:>9.2f} {s['picks_to_spa']:>6}  {alert}")
    else:
        print("*(no strategies in PENDING_SPA range)*")

    if result["n_alerted"]:
        print()
        print("## Alerts (early warning — may need intervention before n=20)")
        for s in result["pending_spa"]:
            if s["alert"]:
                print(f"  ⚠ {s['strategy']} — n={s['n']}, {s['alert']}, {s['picks_to_spa']} picks to SPA threshold")


def get_pending_spa_alerts(
    min_n: int = DEFAULT_FLOOR,
    warn_wr: float = DEFAULT_WARN_WR,
) -> dict:
    """Return structured alert dict for dashboard embedding."""
    from datetime import datetime, timezone
    result = scan_pending_spa(min_n=min_n, warn_wr=warn_wr)
    pending_spa = result.get("pending_spa", [])
    alerted = [s for s in pending_spa if s["alert"]]
    return {
        "alerts": [
            {
                "strategy": s["strategy"],
                "n": s["n"],
                "wr_pct": round(s["wr"] * 100, 1),
                "reason": s["alert"],
                "asset_classes": s.get("asset_classes", []),
            }
            for s in alerted
        ],
        "pending_spa_count": result.get("n_pending_spa", 0),
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pending SPA scanner")
    parser.add_argument("--min-n", type=int, default=DEFAULT_FLOOR,
                        help=f"Minimum n to include (default {DEFAULT_FLOOR})")
    parser.add_argument("--warn-wr", type=float, default=DEFAULT_WARN_WR,
                        help=f"WR below this triggers alert (default {DEFAULT_WARN_WR})")
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--fail-on-alert", action="store_true",
                        help="Exit 1 if any strategy has WR < --wr-threshold")
    parser.add_argument("--wr-threshold", type=float, default=25.0,
                        help="WR%% floor; strategies below this trigger --fail-on-alert")
    args = parser.parse_args()

    result = scan_pending_spa(min_n=args.min_n, warn_wr=args.warn_wr)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)

    if args.fail_on_alert:
        threshold = args.wr_threshold / 100.0
        violations = [
            s for s in result.get("pending_spa", [])
            if s["wr"] < threshold
        ]
        if violations:
            print(f"\nFAIL: {len(violations)} strategies below WR {args.wr_threshold}% threshold:")
            for s in violations:
                print(f"  {s['strategy']}: WR={s['wr']:.1%} n={s['n']}")
            sys.exit(1)


if __name__ == "__main__":
    main()

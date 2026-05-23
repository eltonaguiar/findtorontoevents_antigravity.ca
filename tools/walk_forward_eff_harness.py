#!/usr/bin/env python3
"""
Walk-Forward Eff-Stability Harness (PATH_TO_PROVEN_EDGE Step 1).

A score is admissible to the gate ONLY if its WON-vs-LOST discrimination
(standardised effect size `eff`) is:
  - eff >= EFF_FLOOR (default 0.30) in the same direction
  - across >= MIN_WINDOWS consecutive 14-day rolling windows

Run:
    python tools/walk_forward_eff_harness.py
    python tools/walk_forward_eff_harness.py --window 14 --min-windows 3 --floor 0.30
    python tools/walk_forward_eff_harness.py --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "walk_forward_eff_stability.json"

# Additional ledger files whose closed picks are not merged into closed_picks.json.
# Each entry is read, deduped by 'id', and merged into the pool for the harness.
EXTRA_LEDGER_PATHS: list[Path] = [
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks_fast.json",
    REPO_ROOT / "alpha_engine" / "data" / "augmented_training.json",
]

# Admissibility thresholds
WINDOW_DAYS: int = 14
MIN_WINDOWS: int = 3
EFF_FLOOR: float = 0.30
MIN_N_PER_WINDOW: int = 20  # need ≥20 resolved picks per window for meaningful eff

SCORE_FIELDS = [
    "elite_score",
    "ml_score",
    "ml_composite_score",
    "confidence",
    "method_a_score",
    "risk_reward",
    "forward_wr",
]

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}


def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(s)[:26].strip(), fmt.replace("%z", "").strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _is_win(pick: dict) -> bool | None:
    status = str(pick.get("status") or "").upper()
    pnl = pick.get("pnl_pct")
    if status in WIN_STATUSES:
        return True
    if status in LOSS_STATUSES:
        return False
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


def _eff(won_vals: list[float], lost_vals: list[float]) -> float:
    """Standardised mean difference (Cohen's d)."""
    if not won_vals or not lost_vals:
        return 0.0
    n1, n2 = len(won_vals), len(lost_vals)
    m1 = sum(won_vals) / n1
    m2 = sum(lost_vals) / n2
    var1 = sum((x - m1) ** 2 for x in won_vals) / max(n1 - 1, 1)
    var2 = sum((x - m2) ** 2 for x in lost_vals) / max(n2 - 1, 1)
    pooled_std = math.sqrt((var1 * (n1 - 1) + var2 * (n2 - 1)) / max(n1 + n2 - 2, 1))
    if pooled_std < 1e-12:
        return 0.0
    return (m1 - m2) / pooled_std


def compute_rolling_eff(
    picks: list[dict],
    score_field: str,
    window_days: int = WINDOW_DAYS,
    n_windows: int = 10,
) -> list[dict]:
    """Compute eff for score_field across rolling windows."""
    now = datetime.now(timezone.utc)
    windows = []
    for i in range(n_windows):
        end = now - timedelta(days=i * window_days)
        start = end - timedelta(days=window_days)
        won, lost = [], []
        for p in picks:
            dt = _parse_dt(p.get("closed_at") or p.get("exit_date") or p.get("resolved_at"))
            if dt is None or not (start <= dt < end):
                continue
            val = p.get(score_field)
            if val is None:
                continue
            try:
                val = float(val)
            except (TypeError, ValueError):
                continue
            outcome = _is_win(p)
            if outcome is True:
                won.append(val)
            elif outcome is False:
                lost.append(val)
        windows.append({
            "window": i,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "n_won": len(won),
            "n_lost": len(lost),
            "n_total": len(won) + len(lost),
            "mean_won": round(sum(won) / len(won), 4) if won else None,
            "mean_lost": round(sum(lost) / len(lost), 4) if lost else None,
            "eff": round(_eff(won, lost), 4),
        })
    return windows


def admissibility_verdict(
    windows: list[dict],
    min_windows: int = MIN_WINDOWS,
    eff_floor: float = EFF_FLOOR,
    min_n: int = MIN_N_PER_WINDOW,
) -> dict[str, Any]:
    """
    A score is ADMISSIBLE if, in the most-recent `min_windows` consecutive
    windows that have enough data, eff is >= eff_floor and all in the same sign.
    """
    # Filter to windows with enough picks
    usable = [w for w in windows if w["n_total"] >= min_n]
    if len(usable) < min_windows:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "reason": f"only {len(usable)} windows with n>={min_n} (need {min_windows})",
            "windows_checked": len(usable),
        }

    # Most-recent `min_windows` usable windows (window 0 = most recent)
    recent = sorted(usable, key=lambda w: w["window"])[:min_windows]
    effs = [w["eff"] for w in recent]
    signs = [1 if e > 0 else -1 for e in effs]
    sign_stable = len(set(signs)) == 1
    all_strong = all(abs(e) >= eff_floor for e in effs)

    if sign_stable and all_strong:
        direction = "WINNERS_HIGHER" if signs[0] == 1 else "WINNERS_LOWER"
        return {
            "verdict": "ADMISSIBLE",
            "direction": direction,
            "reason": f"eff stable (sign={direction}, min={round(min(abs(e) for e in effs), 3)}) across {min_windows} windows",
            "effs": effs,
            "windows_checked": len(recent),
        }
    elif sign_stable and not all_strong:
        return {
            "verdict": "WEAK",
            "reason": f"consistent sign but eff too weak (min={round(min(abs(e) for e in effs), 3)}<{eff_floor})",
            "effs": effs,
        }
    else:
        return {
            "verdict": "UNSTABLE",
            "reason": f"sign flips across windows — regime-specific noise (effs={effs})",
            "effs": effs,
        }


def run_harness(
    picks: list[dict],
    score_fields: list[str] = SCORE_FIELDS,
    window_days: int = WINDOW_DAYS,
    n_windows: int = 10,
    min_windows: int = MIN_WINDOWS,
    eff_floor: float = EFF_FLOOR,
) -> dict:
    results = {}
    for field in score_fields:
        windows = compute_rolling_eff(picks, field, window_days, n_windows)
        verdict = admissibility_verdict(windows, min_windows, eff_floor)
        results[field] = {
            "score_field": field,
            "windows": windows,
            **verdict,
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "window_days": window_days,
            "n_windows_evaluated": n_windows,
            "min_windows_for_admissibility": min_windows,
            "eff_floor": eff_floor,
            "min_n_per_window": MIN_N_PER_WINDOW,
        },
        "scores": results,
        "summary": {
            "admissible": [f for f, v in results.items() if v.get("verdict") == "ADMISSIBLE"],
            "weak": [f for f, v in results.items() if v.get("verdict") == "WEAK"],
            "unstable": [f for f, v in results.items() if v.get("verdict") == "UNSTABLE"],
            "insufficient_data": [f for f, v in results.items() if v.get("verdict") == "INSUFFICIENT_DATA"],
        },
    }


def _read_json_picks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("picks", "closed_picks", "data"):
            if isinstance(data.get(key), list):
                return data[key]
        # fallback: first list value
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def load_picks(path: Path = CLOSED_PATH) -> list[dict]:
    picks = _read_json_picks(path)
    seen_ids: set[str] = {p.get("id", "") for p in picks if p.get("id")}
    extra_count = 0
    for extra_path in EXTRA_LEDGER_PATHS:
        for pick in _read_json_picks(extra_path):
            pid = pick.get("id", "")
            if pid and pid in seen_ids:
                continue
            picks.append(pick)
            if pid:
                seen_ids.add(pid)
            extra_count += 1
    if extra_count:
        print(f"[harness] merged {extra_count} extra picks from {len(EXTRA_LEDGER_PATHS)} ledger files "
              f"(total pool: {len(picks)})", file=sys.stderr)
    return picks


def print_report(result: dict) -> None:
    from datetime import datetime as _dt
    print(f"\n{'='*65}")
    print(f"Walk-Forward Eff-Stability Harness")
    print(f"Generated: {result['generated_at']}")
    cfg = result["config"]
    print(f"Config: {cfg['window_days']}d windows, {cfg['min_windows_for_admissibility']} consecutive, eff≥{cfg['eff_floor']}")
    print(f"{'='*65}\n")

    verdicts = {"ADMISSIBLE": "✅", "WEAK": "⚠️", "UNSTABLE": "❌", "INSUFFICIENT_DATA": "🔵"}
    for field, data in result["scores"].items():
        icon = verdicts.get(data.get("verdict", ""), "?")
        print(f"{icon} {field:<30} {data.get('verdict','?'):<20} {data.get('reason','')[:60]}")

    print(f"\n{'─'*65}")
    s = result["summary"]
    print(f"ADMISSIBLE ({len(s['admissible'])}): {', '.join(s['admissible']) or 'none'}")
    print(f"WEAK       ({len(s['weak'])}): {', '.join(s['weak']) or 'none'}")
    print(f"UNSTABLE   ({len(s['unstable'])}): {', '.join(s['unstable']) or 'none'}")
    print(f"NO DATA    ({len(s['insufficient_data'])}): {', '.join(s['insufficient_data']) or 'none'}")
    print()
    if not s["admissible"]:
        print("⚠️  NO score passes the eff-stability gate.")
        print("   This means the system has no proven discriminating signal.")
        print("   Action: keep hunting for new features; do NOT gate on existing scores.")
    else:
        print(f"Gate-admissible scores: {s['admissible']}")
        print("These can be used as gate features. All others should NOT be relied on.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward eff-stability harness")
    parser.add_argument("--window", type=int, default=WINDOW_DAYS, help="Window size in days")
    parser.add_argument("--n-windows", type=int, default=10, help="Number of windows to evaluate")
    parser.add_argument("--min-windows", type=int, default=MIN_WINDOWS, help="Min consecutive windows for admissibility")
    parser.add_argument("--floor", type=float, default=EFF_FLOOR, help="Eff floor for admissibility")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--out", type=str, default=str(OUTPUT_PATH), help="Output path for JSON")
    parser.add_argument("--ledger", nargs="*", help="Extra ledger JSON file paths to merge (in addition to EXTRA_LEDGER_PATHS)")
    args = parser.parse_args()

    if args.ledger:
        EXTRA_LEDGER_PATHS.extend(Path(p) for p in args.ledger)

    picks = load_picks()
    if not picks:
        print("No closed picks found.", file=sys.stderr)
        sys.exit(1)

    result = run_harness(
        picks,
        window_days=args.window,
        n_windows=args.n_windows,
        min_windows=args.min_windows,
        eff_floor=args.floor,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)
        print(f"\nJSON written: {out_path}")


if __name__ == "__main__":
    main()

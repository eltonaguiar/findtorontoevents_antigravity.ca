#!/usr/bin/env python3
"""ml_gatekeeper A/B Sleeve Decision Tool — Phase D (2026-05-12)

Reads BOTH sleeves' picks + cross-references against closed_picks.json
to compute realized WR per sleeve. Runs one-sided z-test on the WR
delta. If WR_NEW > WR_OLD + 2pp with p < 0.10, NEW wins.

Per `reports/ml_gatekeeper_ab_sleeve_design_2026-05-12.md` Phase D.

Inputs:
  ml_gatekeeper/data/active_picks.json           (OLD sleeve emissions)
  ml_gatekeeper/data/active_picks_ab_new.json    (NEW sleeve emissions)
  alpha_engine/data/closed_picks.json            (realized outcomes)

Outputs:
  audit_dashboard/data/ml_gatekeeper_ab_decision.json
    - per-sleeve: n_emitted, n_closed, n_won, n_lost, wr_pct, mean_pnl
    - per-class: same breakdown
    - z-test: z_stat, p_value (one-sided), wr_delta_pp
    - verdict: PENDING (n<min) / NEW_WINS / OLD_WINS / INCONCLUSIVE

Usage:
  python tools/ml_gatekeeper_ab_decision.py
  python tools/ml_gatekeeper_ab_decision.py --min-n 30 --wr-delta-pp 2.0

NFA — read-only diagnostic. Does not flip production gate.

Sample-size note: per design doc, n=30+ closed picks per sleeve is the
minimum for declaring significance. At ~50-80 NEW picks/day after 50%
split, expect 1500-2400 closed over a 30-day window (subject to per-class
holding-period mix).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_PATH = ROOT / "ml_gatekeeper" / "data" / "active_picks.json"
NEW_PATH = ROOT / "ml_gatekeeper" / "data" / "active_picks_ab_new.json"
CLOSED_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"

WIN_STATUSES = ("WON", "WIN", "TP_HIT", "closed_win")
LOSS_STATUSES = ("LOST", "LOSS", "SL_HIT", "closed_loss")
TERMINAL_STATUSES = WIN_STATUSES + LOSS_STATUSES + ("EXPIRED",)


def _hash_bucket(pick_id: str) -> int:
    """Mirror of ml_gatekeeper.gatekeeper._hash_bucket."""
    if not pick_id:
        return 0
    return hashlib.md5(str(pick_id).encode("utf-8")).digest()[0] % 2


def _load_json(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"# WARN: failed to load {path}: {e}", file=sys.stderr)
        return []


def _is_won(status: str) -> bool:
    return str(status or "").upper().strip() in (s.upper() for s in WIN_STATUSES)


def _is_lost(status: str) -> bool:
    return str(status or "").upper().strip() in (s.upper() for s in LOSS_STATUSES)


def _is_terminal(status: str) -> bool:
    return str(status or "").upper().strip() in (s.upper() for s in TERMINAL_STATUSES)


def compute_sleeve_outcomes(active_picks: list, closed_picks: list) -> dict:
    """For each pick in active_picks, see if it exists in closed_picks
    with a terminal status. Return per-sleeve aggregate stats.

    A pick is "closed" if its (symbol, direction, strategy, timestamp)
    matches a closed_picks row with terminal status. We use a relaxed
    match — closed_picks.json doesn't have a clean foreign key.
    """
    # Build lookup: (symbol, direction, strategy) → list of closed entries
    closed_by_key = defaultdict(list)
    for cp in closed_picks:
        key = (
            str(cp.get("symbol", "")).upper(),
            str(cp.get("direction", "")).upper(),
            str(cp.get("strategy", "")).lower(),
        )
        if _is_terminal(cp.get("status")):
            closed_by_key[key].append(cp)

    n_emitted = len(active_picks)
    n_closed = 0
    n_won = 0
    n_lost = 0
    pnls = []
    by_class = defaultdict(lambda: {"n_emitted": 0, "n_closed": 0,
                                     "n_won": 0, "n_lost": 0, "pnls": []})

    for ap in active_picks:
        ac = (ap.get("asset_class") or "UNKNOWN").upper()
        by_class[ac]["n_emitted"] += 1
        key = (
            str(ap.get("symbol", "")).upper(),
            str(ap.get("direction", "")).upper(),
            str(ap.get("strategy", "")).lower(),
        )
        candidates = closed_by_key.get(key, [])
        if not candidates:
            continue
        # Pick the most-recent closed candidate
        cp = candidates[-1]
        n_closed += 1
        by_class[ac]["n_closed"] += 1
        if _is_won(cp.get("status")):
            n_won += 1
            by_class[ac]["n_won"] += 1
        elif _is_lost(cp.get("status")):
            n_lost += 1
            by_class[ac]["n_lost"] += 1
        pnl = cp.get("pnl_pct")
        try:
            pnl_f = float(pnl) if pnl is not None else 0.0
        except (ValueError, TypeError):
            pnl_f = 0.0
        pnls.append(pnl_f)
        by_class[ac]["pnls"].append(pnl_f)

    wr_pct = (n_won * 100.0 / n_closed) if n_closed else None
    mean_pnl = (sum(pnls) / len(pnls)) if pnls else None

    # Per-class WR
    class_breakdown = {}
    for ac, d in by_class.items():
        cw = (d["n_won"] * 100.0 / d["n_closed"]) if d["n_closed"] else None
        cm = (sum(d["pnls"]) / len(d["pnls"])) if d["pnls"] else None
        class_breakdown[ac] = {
            "n_emitted": d["n_emitted"],
            "n_closed": d["n_closed"],
            "n_won": d["n_won"],
            "n_lost": d["n_lost"],
            "wr_pct": round(cw, 2) if cw is not None else None,
            "mean_pnl_pct": round(cm, 4) if cm is not None else None,
        }

    return {
        "n_emitted": n_emitted,
        "n_closed": n_closed,
        "n_won": n_won,
        "n_lost": n_lost,
        "wr_pct": round(wr_pct, 2) if wr_pct is not None else None,
        "mean_pnl_pct": round(mean_pnl, 4) if mean_pnl is not None else None,
        "by_class": class_breakdown,
    }


def two_proportion_z_test(won_new, n_new, won_old, n_old):
    """One-sided z-test: H0 WR_NEW <= WR_OLD ; H1 WR_NEW > WR_OLD.

    Returns dict with z_stat, p_value, wr_new, wr_old, wr_delta_pp.
    """
    if n_new < 1 or n_old < 1:
        return {"z_stat": None, "p_value": None, "wr_new": None,
                "wr_old": None, "wr_delta_pp": None}
    p_new = won_new / n_new
    p_old = won_old / n_old
    p_pool = (won_new + won_old) / (n_new + n_old)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_new + 1 / n_old))
    if se == 0:
        return {"z_stat": None, "p_value": None,
                "wr_new": round(p_new * 100, 2),
                "wr_old": round(p_old * 100, 2),
                "wr_delta_pp": round((p_new - p_old) * 100, 2)}
    z = (p_new - p_old) / se
    # One-sided p-value (right tail)
    p_value = 0.5 * math.erfc(z / math.sqrt(2))
    return {
        "z_stat": round(z, 4),
        "p_value": round(p_value, 5),
        "wr_new": round(p_new * 100, 2),
        "wr_old": round(p_old * 100, 2),
        "wr_delta_pp": round((p_new - p_old) * 100, 2),
    }


def decide(old_stats, new_stats, min_n: int, wr_delta_pp_min: float,
           p_threshold: float):
    """Determine A/B verdict per design doc."""
    n_new = new_stats["n_closed"] or 0
    n_old = old_stats["n_closed"] or 0

    if n_new < min_n or n_old < min_n:
        return {
            "verdict": "PENDING",
            "reason": f"insufficient sample (need >={min_n} per sleeve; "
                      f"have OLD={n_old}, NEW={n_new})",
            "z_test": None,
        }

    z = two_proportion_z_test(
        new_stats["n_won"], n_new,
        old_stats["n_won"], n_old,
    )

    if z["p_value"] is None:
        return {"verdict": "INCONCLUSIVE",
                "reason": "z-test could not be computed (zero variance)",
                "z_test": z}

    if z["p_value"] < p_threshold and z["wr_delta_pp"] >= wr_delta_pp_min:
        return {
            "verdict": "NEW_WINS",
            "reason": (f"WR_NEW={z['wr_new']}% > WR_OLD={z['wr_old']}% + "
                       f"{wr_delta_pp_min}pp; z={z['z_stat']}, "
                       f"p={z['p_value']} < {p_threshold}"),
            "z_test": z,
        }

    return {
        "verdict": "OLD_WINS",
        "reason": (f"Either WR delta {z['wr_delta_pp']}pp < {wr_delta_pp_min}pp "
                   f"OR p {z['p_value']} >= {p_threshold}. Forward features "
                   f"are not liabilities (or NEW is not yet conclusively better)."),
        "z_test": z,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-n", type=int, default=30,
                   help="Min closed picks per sleeve to declare verdict (default 30)")
    p.add_argument("--wr-delta-pp", type=float, default=2.0,
                   help="Min WR delta (pp) for NEW to win (default 2.0)")
    p.add_argument("--p-threshold", type=float, default=0.10,
                   help="One-sided p threshold (default 0.10)")
    p.add_argument("--out", default="audit_dashboard/data/ml_gatekeeper_ab_decision.json")
    args = p.parse_args()

    old_picks = _load_json(OLD_PATH)
    new_picks = _load_json(NEW_PATH)
    closed_picks = _load_json(CLOSED_PATH)

    if not isinstance(old_picks, list) or not isinstance(new_picks, list):
        print("# WARN: OLD or NEW sleeve JSON not a list; bailing", file=sys.stderr)
        return

    print(f"# ml_gatekeeper A/B decision tool — OLD={len(old_picks)} "
          f"NEW={len(new_picks)} closed={len(closed_picks)}",
          file=sys.stderr)

    old_stats = compute_sleeve_outcomes(old_picks, closed_picks)
    new_stats = compute_sleeve_outcomes(new_picks, closed_picks)
    verdict = decide(old_stats, new_stats, args.min_n, args.wr_delta_pp,
                     args.p_threshold)

    # Phase E rollback check: count zero-emission flag (Phase D doesn't
    # persist multi-cycle state; that's Phase E proper. This field just
    # flags the current cycle.)
    rollback_warning = (len(new_picks) == 0 and isinstance(new_picks, list))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "min_n_per_sleeve": args.min_n,
            "wr_delta_pp_min": args.wr_delta_pp,
            "p_threshold_one_sided": args.p_threshold,
        },
        "old_sleeve": old_stats,
        "new_sleeve": new_stats,
        "verdict": verdict["verdict"],
        "reason": verdict["reason"],
        "z_test": verdict.get("z_test"),
        "rollback_warning_this_cycle": rollback_warning,
        "nfa": "Research surface only. Does not flip production gate. "
               "Real-money sizing remains gated on 10-step Lopez de Prado "
               "AFML readiness pipeline regardless of A/B outcome.",
    }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str),
                        encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)
    print(f"# verdict: {verdict['verdict']}", file=sys.stderr)
    print(f"# reason: {verdict['reason']}", file=sys.stderr)
    if verdict.get("z_test"):
        z = verdict["z_test"]
        print(f"#   WR_OLD={z.get('wr_old')}% WR_NEW={z.get('wr_new')}% "
              f"delta={z.get('wr_delta_pp')}pp z={z.get('z_stat')} "
              f"p={z.get('p_value')}", file=sys.stderr)


if __name__ == "__main__":
    main()

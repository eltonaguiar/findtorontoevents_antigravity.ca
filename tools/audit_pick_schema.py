"""
Audit pick schema health for HC dashboard.

Loads closed + active pick arrays from dashboard JSON, checks required HC fields,
reports null/empty counts, and flags inconsistent forward-WR scale (0-1 vs 0-100).

Usage:
    python tools/audit_pick_schema.py [--data PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"

REQUIRED_CLOSED_FIELDS = [
    "symbol",
    "asset_class",
    "score",
    "trust_score",
    "strat_fwd_wr",
    "strat_fwd_trades",
    "pnl_pct",
    "direction",
    "confidence",
]
REQUIRED_ACTIVE_FIELDS = [
    "symbol",
    "asset_class",
    "score",
    "trust_score",
    "strat_fwd_wr",
    "strat_fwd_trades",
    "direction",
    "confidence",
]


def _load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _count_nulls(picks: list[dict], fields: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for field in fields:
        cnt = 0
        for p in picks:
            v = p.get(field)
            if v is None or v == "" or v == "null":
                cnt += 1
        out[field] = cnt
    return out


def _fwd_wr_scale_audit(picks: list[dict]) -> dict[str, int]:
    in_0_1 = 0
    in_1_100 = 0
    in_100_plus = 0
    missing = 0
    for p in picks:
        v = p.get("strat_fwd_wr")
        if v is None or v == "" or v == "null":
            missing += 1
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            missing += 1
            continue
        if 0 < fv <= 1:
            in_0_1 += 1
        elif 1 < fv <= 100:
            in_1_100 += 1
        elif fv > 100:
            in_100_plus += 1
    return {
        "in_0_1": in_0_1,
        "in_1_100": in_1_100,
        "in_100_plus": in_100_plus,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit pick schema for HC dashboard")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to dashboard_data.json")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    data = _load_data(args.data)
    picks = data.get("picks", {})
    closed = picks.get("recent_closed", picks.get("closed_picks", []))
    active = picks.get("active", [])

    report: dict[str, Any] = {
        "source": str(args.data),
        "closed_count": len(closed),
        "active_count": len(active),
        "closed_nulls": _count_nulls(closed, REQUIRED_CLOSED_FIELDS),
        "active_nulls": _count_nulls(active, REQUIRED_ACTIVE_FIELDS),
        "closed_fwd_wr_scale": _fwd_wr_scale_audit(closed),
        "active_fwd_wr_scale": _fwd_wr_scale_audit(active),
    }

    # Score distribution on closed
    score_bins = {"<0": 0, "0-10": 0, "10-25": 0, "25-40": 0, "40-55": 0, "55-70": 0, "70+": 0}
    for p in closed:
        s = p.get("score")
        try:
            sv = float(s) if s is not None else None
        except (TypeError, ValueError):
            sv = None
        if sv is None:
            score_bins["<0"] += 1
        elif sv < 0:
            score_bins["<0"] += 1
        elif sv < 10:
            score_bins["0-10"] += 1
        elif sv < 25:
            score_bins["10-25"] += 1
        elif sv < 40:
            score_bins["25-40"] += 1
        elif sv < 55:
            score_bins["40-55"] += 1
        elif sv < 70:
            score_bins["55-70"] += 1
        else:
            score_bins["70+"] += 1
    report["closed_score_distribution"] = score_bins

    # HC pass rate on active
    try:
        sys.path.insert(0, str(REPO))
        from tools.dashboard_hc_rules import passes_high_conviction_pick

        hc_active = [p for p in active if passes_high_conviction_pick(p)]
        report["active_hc_pass_rate"] = round(len(hc_active) / len(active), 4) if active else 0
        report["active_hc_pass_count"] = len(hc_active)
    except Exception as e:
        report["active_hc_pass_rate"] = None
        report["active_hc_pass_error"] = str(e)

    print(json.dumps(report, indent=2))

    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

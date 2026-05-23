#!/usr/bin/env python3
"""
Rolling edge monitor: compare recent-window win rate vs older baseline per HF tier.

Uses real closed_picks.json fields (exit_time / closed_at) and assigns tier via
`classify_hf_conviction_tier` (stored picks rarely include hf_conviction_tier).

  python tools/edge_decay_monitor.py
  python tools/edge_decay_monitor.py --json-out audit_trail/data/edge_decay_report.json --fail-on-alert
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_engine.conviction_stack import classify_hf_conviction_tier, load_conviction_tiers_config


def _parse_exit_dt(p: dict) -> datetime | None:
    for key in ("exit_time", "closed_at", "close_date", "exit_date"):
        raw = p.get(key)
        if not raw:
            continue
        s = str(raw).replace("Z", "+00:00").replace(" EST", "")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            continue
    return None


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


def rolling_edge_report(
    closed_picks: list[dict[str, Any]],
    *,
    cfg: dict[str, Any],
    window_days: int = 30,
    baseline_span_days: int = 150,
    min_recent: int = 5,
    min_baseline: int = 10,
    decay_alert_pp: float = 10.0,
    watch_pp: float = 5.0,
    critical_recent_wr: float = 0.45,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Recent window: [now - window_days, now].
    Baseline window: [now - window_days - baseline_span_days, now - window_days).

    decay_pp = (baseline_wr - recent_wr) * 100 (positive means recent worse).
    """
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    recent_lo = now - timedelta(days=window_days)
    baseline_lo = now - timedelta(days=window_days + baseline_span_days)

    tiers: dict[str, dict[str, list[float]]] = {}

    for pick in closed_picks:
        if not isinstance(pick, dict):
            continue
        close_dt = _parse_exit_dt(pick)
        if close_dt is None:
            continue
        tier, _ = classify_hf_conviction_tier(pick, cfg)
        label = tier if tier in ("S", "A", "B") else "UNTIERED"
        outcome = 1.0 if _is_won(pick) else 0.0

        if label not in tiers:
            tiers[label] = {"recent": [], "baseline": []}

        if close_dt >= recent_lo:
            tiers[label]["recent"].append(outcome)
        elif close_dt >= baseline_lo:
            tiers[label]["baseline"].append(outcome)

    report: dict[str, Any] = {}
    alert_any = False

    for tier, windows in sorted(tiers.items()):
        recent = windows["recent"]
        baseline = windows["baseline"]
        if len(recent) < min_recent or len(baseline) < min_baseline:
            report[tier] = {
                "status": "INSUFFICIENT_DATA",
                "recent_n": len(recent),
                "baseline_n": len(baseline),
                "recent_window_days": window_days,
                "baseline_span_days": baseline_span_days,
            }
            continue

        recent_wr = sum(recent) / len(recent)
        baseline_wr = sum(baseline) / len(baseline)
        decay_pp = (baseline_wr - recent_wr) * 100.0

        status = "OK"
        if recent_wr < critical_recent_wr:
            status = "CRITICAL"
            alert_any = True
        elif decay_pp > decay_alert_pp:
            status = "DECAYING"
            alert_any = True
        elif decay_pp > watch_pp:
            status = "WATCH"

        row = {
            "status": status,
            "recent_wr": round(recent_wr, 4),
            "baseline_wr": round(baseline_wr, 4),
            "decay_pp": round(decay_pp, 2),
            "recent_n": len(recent),
            "baseline_n": len(baseline),
            "as_of_utc": now.isoformat() + "Z",
        }
        report[tier] = row
        if tier in ("S", "A", "B") and status in ("DECAYING", "CRITICAL"):
            alert_any = True

    return {"tiers": report, "meta": {"alert_any_hf_tier": alert_any}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--closed-path",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
    )
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit 1 if any S/A/B tier is DECAYING or CRITICAL",
    )
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--baseline-span-days", type=int, default=150)
    args = ap.parse_args()

    if not args.closed_path.is_file():
        print("Missing %s" % args.closed_path, file=sys.stderr)
        return 1

    data = json.loads(args.closed_path.read_text(encoding="utf-8"))
    cfg = load_conviction_tiers_config()
    rep = rolling_edge_report(
        data,
        cfg=cfg,
        window_days=args.window_days,
        baseline_span_days=args.baseline_span_days,
    )

    print("=== Rolling edge monitor (HF tiers + UNTIERED) ===")
    for tier, d in rep["tiers"].items():
        st = d.get("status", "?")
        flag = ""
        if st == "DECAYING":
            flag = "  <-- DECAY"
        elif st == "CRITICAL":
            flag = "  <-- CRITICAL"
        elif st == "WATCH":
            flag = "  (watch)"
        print("  %-10s %s%s" % (tier, d, flag))

    out = args.json_out or (_REPO / "audit_trail" / "data" / "edge_decay_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print()
    print("Wrote %s" % out)

    if args.fail_on_alert:
        bad = []
        for t in ("S", "A", "B"):
            td = rep["tiers"].get(t, {})
            if td.get("status") in ("DECAYING", "CRITICAL"):
                bad.append("%s:%s" % (t, td.get("status")))
        if bad:
            print("ALERT: %s" % "; ".join(bad), file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

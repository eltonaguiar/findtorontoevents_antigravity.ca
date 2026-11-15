#!/usr/bin/env python3
"""build_forward_clock.py — the dashboard's view of the forward-test clock.

Writes audit_dashboard/data/forward_clock.json from state/forward_test/plan.json
plus the ledger.

This tool deliberately contains NO verdict logic of its own: decide() and
interim_verdict() are imported from tools/forward_tracker.py, so the panel can
never disagree with `forward_tracker.py status`. If the panel computed its own
numbers, the dashboard and the CLI would drift apart and the CLI would win the
argument every time — while the panel was the thing people looked at.

Run:  python3 tools/build_forward_clock.py
"""
import json
import os
import sys
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import forward_tracker as ft  # noqa: E402

OUT = os.path.join(ROOT, "audit_dashboard", "data", "forward_clock.json")


def _row(name, cfg, mine, today):
    verdict, note, stats = ft.decide(name, cfg, mine, today)
    iv = ft.interim_verdict(cfg, mine, today) or {}
    start = cfg.get("start") or None
    try:
        days = (today - datetime.strptime(start, "%Y-%m-%d").date()).days if start else None
    except (TypeError, ValueError):
        days = None
    windows = len({(t.get("opened"), t.get("closed")) for t in mine})
    target = iv.get("target")
    prior = (cfg.get("prior") or cfg.get("baseline") or {})
    return {
        "strategy": name,
        "class": cfg.get("class"),
        "started": start,
        "days_elapsed": days,
        "trades": stats.get("n", 0),
        "windows": windows,
        "target_windows": target,
        "pct_of_target": (round(100.0 * windows / target, 1) if target else None),
        "verdict": verdict,
        "note": note,
        "mean_hold_days": stats.get("avg_hold"),
        "has_measurement_design": bool(iv),
        "interim_verdict": iv.get("verdict"),
        "look": iv.get("look"),
        "next_look": iv.get("next_look"),
        "z": iv.get("z"),
        "boundary": iv.get("boundary"),
        "all_boundaries": iv.get("boundaries"),
        "endpoint": iv.get("endpoint"),
        # labelled as a PRIOR everywhere it is shown: it is in-sample selection,
        # not evidence that survives the forward clock.
        "prior_excess_pp": prior.get("mean_excess_pp"),
        "prior_status": prior.get("status"),
        "prior_is_in_sample": bool(prior),
    }


def main():
    plan = ft.load_plan()
    trades = ft.load_trades()
    by = {}
    for t in trades:
        by.setdefault(t.get("strategy"), []).append(t)
    today = date.today()
    rows = [_row(name, cfg, by.get(name, []), today) for name, cfg in plan["strategies"].items()]
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": str(today),
        "rules_version": plan.get("rules_version"),
        "ledger_rows": len(trades),
        "cost_model": plan.get("cost_model") or {},
        "strategies": rows,
        "note": ("Progress only. No strategy here is money-ready, and a PRIOR column is "
                 "in-sample selection, not forward evidence."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    total_targets = sum(r["target_windows"] or 0 for r in rows)
    print(f"wrote {OUT}: {len(rows)} strategies, {len(trades)} ledger rows, "
          f"{sum(r['windows'] for r in rows)}/{total_targets} windows")


if __name__ == "__main__":
    main()

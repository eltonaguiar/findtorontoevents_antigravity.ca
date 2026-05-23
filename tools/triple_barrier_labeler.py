"""Triple-barrier labeler — Lopez de Prado method, adapted for our pick structure.

Standard method in quant finance (Advances in Financial Machine Learning, Ch. 3):
for each entry, define THREE barriers that end the trade:

  1. Upper barrier  = entry + TP distance   (WIN  for long, LOSS for short)
  2. Lower barrier  = entry - SL distance   (LOSS for long, WIN  for short)
  3. Time barrier   = entry + max_holding_period (TIMEOUT, labeled by P&L sign)

The FIRST barrier hit determines the label: {WIN, LOSS, TIMEOUT}.

Why we need this
----------------
Our closed-pick dataset has an 88-row cohort (`non_crypto_consensus`) with
pnl_pct == 0.0 for every closed pick. These are FORCE_CLOSED / flat-close
artifacts — the resolver never saw any barrier get hit. The triple-barrier
method would catch this: if a pick closes without any of the three barriers
triggering, the resolver itself is broken.

Secondary use: ML labels. Every future meta-labeling / ensemble-classifier
training set needs consistent {WIN, LOSS, TIMEOUT} labels. Our current
pnl_pct-only data conflates small losses with timeouts.

Conservative approach
---------------------
This module is an offline auditor + re-labeler, NOT a production resolver.
It takes closed picks as input, derives the three barriers from entry/TP/SL/
created_at fields, and identifies which label each pick *should* have had.

Usage:

    from tools.triple_barrier_labeler import label_closed_picks, audit_labels
    dp = json.load(open("audit_trail/data/dashboard_payload.json"))
    labels = label_closed_picks(dp["picks"]["recent_closed"])
    report = audit_labels(labels, dp["picks"]["recent_closed"])
    # report contains: mislabeled_picks, strategies_with_flat_close_bug, etc.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def label_pick(pick: dict, default_hold_hours: float = 72.0) -> dict:
    """Derive the triple-barrier label for a single closed pick.

    Returns a record with:
      label          : WIN | LOSS | TIMEOUT | FLAT_CLOSE_BUG | UNLABELED
      first_barrier  : TP | SL | TIME | NONE
      pnl_pct        : copy of pick["pnl_pct"] if present
      inferred_from  : "pnl_sign" | "barriers" | "none"
    """
    direction = (pick.get("direction") or "").upper()
    entry = _f(pick.get("entry_price"))
    tp = _f(pick.get("take_profit"))
    sl = _f(pick.get("stop_loss"))
    pnl = pick.get("pnl_pct")
    created = _parse_iso(pick.get("created_at") or pick.get("timestamp") or pick.get("entry_time"))
    closed = _parse_iso(pick.get("closed_at") or pick.get("resolved_at"))

    rec = {
        "id": pick.get("id"),
        "symbol": pick.get("symbol"),
        "strategy": pick.get("strategy") or pick.get("source_system"),
        "direction": direction,
        "pnl_pct": pnl,
        "label": "UNLABELED",
        "first_barrier": "NONE",
        "inferred_from": "none",
    }

    if pnl is None:
        return rec  # no outcome yet

    pnl_f = _f(pnl)

    # Flat-close bug detector: pnl exactly 0.0 AND no barrier distance to check
    # (entry/TP/SL missing or degenerate) = resolver never saw a barrier hit.
    if pnl_f == 0.0 and (entry <= 0 or tp <= 0 or sl <= 0 or (tp == entry and sl == entry)):
        rec["label"] = "FLAT_CLOSE_BUG"
        rec["first_barrier"] = "NONE"
        rec["inferred_from"] = "degenerate_barriers"
        return rec

    # Did the holding period exceed the default window?
    exceeded_window = False
    if created and closed:
        hours_held = (closed - created).total_seconds() / 3600.0
        if hours_held >= default_hold_hours:
            exceeded_window = True

    # Sign-based labeling when barriers are well-defined
    if entry > 0 and tp > 0 and sl > 0:
        # Which barrier is closer to entry in direction of profit?
        tp_dist = abs(tp - entry)
        sl_dist = abs(sl - entry)
        # WIN/LOSS from pnl sign; which barrier likely hit depends on direction + distance
        if pnl_f > 0.01:
            rec["label"] = "WIN"
            rec["first_barrier"] = "TP"
        elif pnl_f < -0.01:
            rec["label"] = "LOSS"
            rec["first_barrier"] = "SL"
        else:
            # pnl ~= 0: either timeout or flat close. If exceeded window, it's TIMEOUT.
            rec["label"] = "TIMEOUT" if exceeded_window else "FLAT_CLOSE_BUG"
            rec["first_barrier"] = "TIME" if exceeded_window else "NONE"
        rec["inferred_from"] = "pnl_sign"
        rec["tp_distance_pct"] = round(tp_dist / entry * 100, 3) if entry else None
        rec["sl_distance_pct"] = round(sl_dist / entry * 100, 3) if entry else None
    else:
        # barriers missing; fall back to pnl sign
        if pnl_f > 0.01:
            rec["label"] = "WIN"
        elif pnl_f < -0.01:
            rec["label"] = "LOSS"
        else:
            rec["label"] = "TIMEOUT" if exceeded_window else "FLAT_CLOSE_BUG"
        rec["inferred_from"] = "pnl_sign"

    return rec


def label_closed_picks(picks: list[dict], default_hold_hours: float = 72.0) -> list[dict]:
    """Label a batch of closed picks."""
    return [label_pick(p, default_hold_hours=default_hold_hours) for p in picks]


def audit_labels(labels: list[dict], picks: list[dict]) -> dict:
    """Aggregate: count labels + flag strategies with chronic FLAT_CLOSE_BUG."""
    from collections import Counter, defaultdict

    label_counter = Counter(l["label"] for l in labels)
    by_strat_flat: dict[str, int] = defaultdict(int)
    by_strat_total: dict[str, int] = defaultdict(int)

    for l in labels:
        strat = l.get("strategy") or "unknown"
        by_strat_total[strat] += 1
        if l["label"] == "FLAT_CLOSE_BUG":
            by_strat_flat[strat] += 1

    # Strategies with >= 50% FLAT_CLOSE_BUG and n >= 10 = resolver broken
    broken_strategies = []
    for s, n in by_strat_total.items():
        if n >= 10 and by_strat_flat.get(s, 0) / n >= 0.5:
            broken_strategies.append({
                "strategy": s,
                "n_total": n,
                "n_flat_close": by_strat_flat[s],
                "flat_close_rate_pct": round(by_strat_flat[s] / n * 100, 1),
            })

    return {
        "label_counts": dict(label_counter),
        "total_labeled": len(labels),
        "broken_strategies": sorted(broken_strategies, key=lambda x: -x["flat_close_rate_pct"]),
        "n_strategies_tested": len(by_strat_total),
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Triple-barrier audit on closed picks.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    ap.add_argument("--hold-hours", type=float, default=72.0)
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = [p for p in dp["picks"]["recent_closed"] if p.get("pnl_pct") is not None]
    labels = label_closed_picks(closed, default_hold_hours=args.hold_hours)
    report = audit_labels(labels, closed)

    print(json.dumps(report, indent=2))

"""Compare Smart Picks vs Verified Alpha vs Track% across 4 time windows.

Reads audit_dashboard/data/dashboard_data.json -> picks.recent_closed,
computes metrics, and performs a bug hunt on Track% field population.

Track% is computed two ways:
  * trackp_pickwr:  pick-level forward_wr  >= 50%
  * trackp_stratwr: strategy-level strat_fwd_wr >= 50%  (this is how the
                    live dashboard filter works; matches Gemini's numbers)
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

REPO = r"c:\findtorontoevents_antigravity.ca"
sys.path.insert(0, REPO)

from audit_trail.quality_gates import passes_smart_gate  # noqa: E402

DATA = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
TIME_FIELDS = ("closed_at", "resolved_at", "exit_time")


def _smart_at_issue(p):
    q = dict(p)
    q["status"] = "ACTIVE"
    q.pop("outcome", None)
    try:
        return bool(passes_smart_gate(q))
    except Exception:
        return False


def parse_ts(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except Exception:
            return None
    s = str(val).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def get_close_ts(p):
    for f in TIME_FIELDS:
        if p.get(f):
            ts = parse_ts(p[f])
            if ts:
                return ts, f
    return None, None


def _to_ratio(v):
    if v is None:
        return None
    try:
        fv = float(v)
    except Exception:
        return None
    if math.isnan(fv):
        return None
    if fv > 1.5:
        fv /= 100.0
    return fv


def is_proven(p):
    for f in ("trust_tier", "registry_trust_tier", "at_issue_trust_tier"):
        v = p.get(f)
        if isinstance(v, str) and v.upper() == "PROVEN":
            return True
    return False


def metrics(picks):
    n = len(picks)
    if n == 0:
        return {"n": 0}
    pnls = []
    for p in picks:
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            pnls.append(float(v))
        except Exception:
            pass
    if not pnls:
        return {"n": n, "n_pnl": 0}
    wins = sum(1 for x in pnls if x > 0)
    pos = sum(x for x in pnls if x > 0)
    neg = sum(x for x in pnls if x < 0)
    pf = (pos / abs(neg)) if neg < 0 else (float("inf") if pos > 0 else None)
    mean = statistics.fmean(pnls)
    std = statistics.pstdev(pnls) if len(pnls) > 1 else 0.0
    sharpe = (mean / std) if std > 0 else None
    return {
        "n": n,
        "n_pnl": len(pnls),
        "wr": wins / len(pnls),
        "mean_pnl": mean,
        "total_pnl": sum(pnls),
        "pf": pf,
        "sharpe": sharpe,
    }


def main():
    with open(DATA, "r", encoding="utf-8") as f:
        data = json.load(f)
    recent = data.get("picks", {}).get("recent_closed", [])

    enriched = []
    skipped_no_ts = 0
    for p in recent:
        ts, fld = get_close_ts(p)
        if ts is None:
            skipped_no_ts += 1
            continue
        fwr_pick = _to_ratio(p.get("forward_wr"))
        fwr_strat = _to_ratio(p.get("strat_fwd_wr"))
        enriched.append({
            "pick": p,
            "ts": ts,
            "fwr_pick": fwr_pick,
            "fwr_strat": fwr_strat,
            "smart": _smart_at_issue(p),
            "proven": is_proven(p),
        })

    max_ts = max(e["ts"] for e in enriched)

    windows = {
        "this_week_0_7d": (0, 7),
        "last_week_7_14d": (7, 14),
        "this_month_0_30d": (0, 30),
        "last_month_30_60d": (30, 60),
    }

    results = {}
    for wname, (lo, hi) in windows.items():
        hi_ts = max_ts - timedelta(days=lo)
        lo_ts = max_ts - timedelta(days=hi)
        in_win = [e for e in enriched if lo_ts <= e["ts"] <= hi_ts]
        smart = [e["pick"] for e in in_win if e["smart"]]
        verified = [e["pick"] for e in in_win if e["proven"]]
        tp_pick = [e["pick"] for e in in_win if e["fwr_pick"] is not None and e["fwr_pick"] >= 0.5]
        tp_strat = [e["pick"] for e in in_win if e["fwr_strat"] is not None and e["fwr_strat"] >= 0.5]
        results[wname] = {
            "window_lo": lo_ts.isoformat(),
            "window_hi": hi_ts.isoformat(),
            "total_in_window": len(in_win),
            "smart": metrics(smart),
            "verified": metrics(verified),
            "trackp_pickwr": metrics(tp_pick),
            "trackp_stratwr": metrics(tp_strat),
        }

    # ---- Bug hunt on Track% (strat_fwd_wr, the field the dashboard uses) ----
    strat_counts = defaultdict(lambda: {"total": 0, "pop": 0})
    for e in enriched:
        strat = e["pick"].get("strategy") or e["pick"].get("source_system") or "UNKNOWN"
        strat_counts[strat]["total"] += 1
        if e["fwr_strat"] is not None:
            strat_counts[strat]["pop"] += 1
    zero_pop_big = [(s, c["total"]) for s, c in strat_counts.items()
                    if c["total"] > 20 and c["pop"] == 0]

    sym_stats = defaultdict(lambda: {"total": 0, "pop": 0})
    for e in enriched:
        k = (e["pick"].get("strategy") or "UNKNOWN", e["pick"].get("symbol") or "?")
        sym_stats[k]["total"] += 1
        if e["fwr_strat"] is not None:
            sym_stats[k]["pop"] += 1
    inconsistent = [(k, c["total"], c["pop"]) for k, c in sym_stats.items()
                    if c["total"] >= 5 and 0 < c["pop"] < c["total"]]
    inconsistent.sort(key=lambda x: -x[1])

    clamped = defaultdict(lambda: {"n": 0, "zero": 0, "one": 0})
    for e in enriched:
        if e["fwr_strat"] is None:
            continue
        s = e["pick"].get("strategy") or "UNKNOWN"
        clamped[s]["n"] += 1
        if e["fwr_strat"] == 0.0:
            clamped[s]["zero"] += 1
        if e["fwr_strat"] == 1.0:
            clamped[s]["one"] += 1
    clamp_bugs = [(s, c) for s, c in clamped.items()
                  if c["n"] > 10 and (c["zero"] / c["n"] > 0.8 or c["one"] / c["n"] > 0.8)]

    # Pick-level forward_wr vs strategy-level strat_fwd_wr disagreement (informational)
    disagree = []
    for e in enriched:
        a = e["fwr_pick"]; b = e["fwr_strat"]
        if a is None or b is None:
            continue
        if abs(a - b) > 0.10:  # > 10 pp diff
            disagree.append((e["pick"].get("symbol"), e["pick"].get("strategy"),
                             round(a, 3), round(b, 3)))
    disagree_sample = disagree[:8]

    missing_strat_fwr = sum(1 for e in enriched if e["fwr_strat"] is None)
    missing_strat_by_strat = defaultdict(int)
    for e in enriched:
        if e["fwr_strat"] is None:
            missing_strat_by_strat[e["pick"].get("strategy") or e["pick"].get("source_system") or "UNKNOWN"] += 1

    out = {
        "max_close_ts": max_ts.isoformat(),
        "total_recent_closed": len(recent),
        "skipped_no_ts": skipped_no_ts,
        "usable": len(enriched),
        "windows": results,
        "bugs": {
            "zero_pop_big": zero_pop_big,
            "inconsistent_count": len(inconsistent),
            "inconsistent_top10": inconsistent[:10],
            "clamp_bugs": clamp_bugs,
            "disagree_over_10pp_count": len(disagree),
            "disagree_sample": disagree_sample,
            "missing_strat_fwr_total": missing_strat_fwr,
            "missing_strat_by_strategy": dict(missing_strat_by_strat),
        },
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()

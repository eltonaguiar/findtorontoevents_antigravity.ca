#!/usr/bin/env python3
"""audjpy_population_reconcile.py -- reconcile the THREE AUDJPY populations by pick id.

Proposed by buffy (freebuff) 2026-11-23 after the peer (Kilo) reconciled AUDJPY "by
audit3's own fields". That answered whether the +0.576% aggregate is alpha; it did NOT
answer whether the two trade-level samples are the same trades. This does, by id.

Populations
  P1  audit3 canonical   audit_dashboard/data/audit3_ledger.json, symbol AUDJPY   (aggregate)
  P2  riseoftheclaw      riseoftheclaw/data/signal_tracking.json, AUDJPY rows     (trade level)
  P3  copy_trader        audit_dashboard/data/dashboard_data.json picks.*         (trade level)

A pick-id join is only meaningful where ids exist. P1 publishes an aggregate and NO trade
ids, so it can be reconciled by count/timestamp only -- stated, not papered over.

Read-only. Writes reports/audjpy_population_reconcile_2026-11-23.json
"""
from __future__ import annotations
import json, statistics as st
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "audjpy_population_reconcile_2026-11-23.json"
SYM = "AUDJPY"


def _norm_symbol(s):
    return str(s or "").upper().replace("=X", "").replace("-", "").strip()


def _ts(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(float(s) / (1000 if float(s) > 1e11 else 1), tz=timezone.utc)
    t = str(s).strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d_%H%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.fromisoformat(t) if fmt is None else datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def pop1():
    d = json.load(open(ROOT / "audit_dashboard/data/audit3_ledger.json"))
    rows = d if isinstance(d, list) else (d.get("symbols") or d.get("rows") or list(d.values())[0])
    if isinstance(rows, dict):
        rows = list(rows.values())
    for r in rows:
        if isinstance(r, dict) and _norm_symbol(r.get("symbol")) == SYM:
            return {"source": "audit3_ledger", "trade_level_ids": False,
                    "n": r.get("n"), "wins": r.get("wins"), "wr": r.get("wr"),
                    "net_expectancy_pct": r.get("net_expectancy_pct"),
                    "net_ci_pct": r.get("net_ci_pct"), "dsr": r.get("dsr"),
                    "beta_dominant": r.get("beta_dominant"),
                    "alpha_gate": r.get("alpha_gate"), "recent_ok": r.get("recent_ok"),
                    "mean_cost_pct": r.get("mean_cost_pct"), "verdict": r.get("verdict"),
                    "provenance_id": r.get("provenance_id")}
    return None


def pop2():
    d = json.load(open(ROOT / "riseoftheclaw/data/signal_tracking.json"))
    rows = d.get("signals") or d.get("picks") or d.get("items") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    out = []
    for r in rows:
        if isinstance(r, dict) and _norm_symbol(r.get("symbol")) == SYM:
            pct = r.get("pnl_pct")
            out.append({"id": r.get("id"), "signal_id": r.get("signal_id"),
                        "entry_time": r.get("entry_time"), "exit_time": r.get("exit_time"),
                        "status": r.get("status"), "pnl_pct": (float(pct) * 100 if pct is not None else None),
                        "entry_price": r.get("entry_price")})
    return {"source": "riseoftheclaw/data/signal_tracking.json", "trade_level_ids": True, "rows": out}


def pop3():
    d = json.load(open(ROOT / "audit_dashboard/data/dashboard_data.json"))
    picks = d.get("picks") or {}
    out = []
    for bucket in ("active", "recent_closed"):
        for r in (picks.get(bucket) or []):
            if isinstance(r, dict) and _norm_symbol(r.get("symbol")) == SYM:
                pnl = r.get("pnl_pct")
                out.append({"id": r.get("id"), "bucket": bucket, "status": r.get("status"),
                            "entry_time": r.get("entry_time"), "closed_at": r.get("closed_at"),
                            "pnl_pct": (float(pnl) if pnl is not None else None),
                            "entry_price": r.get("entry_price"),
                            "direction": r.get("direction")})
    return {"source": "audit_dashboard/data/dashboard_data.json picks.active+recent_closed",
            "trade_level_ids": True, "rows": out}


def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "mean_pct": round(st.mean(vals), 4),
            "median_pct": round(st.median(vals), 4),
            "wins": sum(1 for v in vals if v > 0), "losses": sum(1 for v in vals if v < 0)}


def main():
    p1, p2, p3 = pop1(), pop2(), pop3()
    r2, r3 = p2["rows"], p3["rows"]

    ids2 = {str(r["id"]) for r in r2 if r.get("id") is not None}
    sig2 = {r["signal_id"] for r in r2 if r.get("signal_id")}
    ids3 = {str(r["id"]) for r in r3 if r.get("id")}
    shared_ids = ids2 & ids3
    shared_sig = sig2 & ids3

    # id spaces are structurally different: show the shapes rather than assert dissimilarity
    def shape(samples):
        return sorted({str(s).split("_")[0][:34] for s in samples if s})[:6]
    shapes = {"p2_id": shape(ids2), "p3_id": shape(ids3)}

    # timestamp join: P3 composite ids embed "::AUDJPY=X::<ts>"; P2 signal_ids embed "<ts>"
    def embedded_ts(s):
        s = str(s or "")
        tail = s.split("::")[-1] if "::" in s else s.split("_", 1)[-1] if "_" in s else ""
        return _ts(tail)
    t2 = {embedded_ts(r["signal_id"]) for r in r2 if r.get("signal_id")}
    t3 = {embedded_ts(r["id"]) for r in r3 if r.get("id")}
    t2.discard(None); t3.discard(None)
    shared_ts = {t for t in (t2 & t3)}

    p1n = p1.get("n") if p1 else None
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": "AUDJPY", "proposed_by": "buffy (freebuff), 2026-11-23",
        "why": ("Kilo reconciled AUDJPY by audit3's own fields (beta_dominant, alpha_gate, "
                "recency). That settles whether the aggregate is alpha; it does not settle "
                "whether the two trade-level samples are the same trades. A pick-id join does."),
        "populations": {
            "P1_audit3": p1,
            "P2_riseoftheclaw": {"n": len(r2), "stats_pct": stats([r["pnl_pct"] for r in r2])},
            "P3_copy_trader": {"n": len(r3), "stats_pct": stats([r["pnl_pct"] for r in r3]),
                               "buckets": {b: sum(1 for r in r3 if r["bucket"] == b)
                                           for b in {r["bucket"] for r in r3}}},
        },
        "join": {
            "method": "pick id, then embedded timestamp, then symbol",
            "p1_has_trade_ids": False,
            "p2_id_count": len(ids2), "p3_id_count": len(ids3),
            "id_shapes": shapes,
            "shared_ids": sorted(shared_ids)[:20], "shared_id_count": len(shared_ids),
            "shared_signal_ids": sorted(shared_sig)[:20], "shared_signal_id_count": len(shared_sig),
            "p2_embedded_timestamps": len(t2), "p3_embedded_timestamps": len(t3),
            "shared_timestamps": sorted(x.isoformat() for x in shared_ts)[:20],
            "shared_timestamp_count": len(shared_ts),
            "overlap_p2_p3": "NONE" if (not shared_ids and not shared_ts) else "OVERLAP",
            "p1_reconcilable_by_id": False,
            "p1_vs_p2_count_gap": (p1n - len(r2)) if isinstance(p1n, int) else None,
        },
        "finding": None,
    }

    overlap = out["join"]["overlap_p2_p3"] == "OVERLAP"
    if not overlap:
        out["finding"] = (
            "THREE DISJOINT POPULATIONS, not one contradictory population. P2 (n=%d) and P3 "
            "(n=%d) share ZERO pick ids and ZERO embedded timestamps, and their id spaces are "
            "structurally different (%s vs %s). P1 publishes no trade ids at all, so it cannot "
            "be joined by id. The 'conflict' Kilo reported between +0.576%% and -2.45%% was "
            "never a contradiction inside one dataset: it compares an aggregate over one set "
            "with trades from two other sets. Kilo's field-level conclusion (beta_dominant, "
            "alpha_gate false, recent_ok false) is the operative one and stands."
            % (len(r2), len(r3), shapes["p2_id"], shapes["p3_id"]))
    else:
        out["finding"] = ("OVERLAP FOUND between P2 and P3 (%d shared ids, %d shared timestamps). "
                          "The two trade-level samples are not independent and must be deduplicated "
                          "before either is used as evidence."
                          % (len(shared_ids), len(shared_ts)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("populations", "join", "finding")}, indent=1)[:3000])
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

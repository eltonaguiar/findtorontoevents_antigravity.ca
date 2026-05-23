#!/usr/bin/env python3
"""
HC Edge Re-Validation Script
=============================
Re-runs the per-asset-class edge analysis for High Conviction filter thresholds.

Usage:
    python3 audit_trail/hc_edge_revalidation.py
    python3 audit_trail/hc_edge_revalidation.py --baseline     # show baseline comparison

Compares current data against the 2026-04-15 baseline:
    CRYPTO:  FWD>=45% + Score>=55  =>  WR 56.3% (N=474)
    EQUITY:  FWD>=55% + Score>=50  =>  WR 68.8% (N=80)
    FOREX:   FWD>=55% + Score>=40  =>  WR 70.6% (N=34)  ⚠️ small sample
    COMMODITY/BOND/ETF: rejected (weak/nodata)

If FOREX N drops or WR falls significantly, the script flags it for threshold revision.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# ── Config ──
PROJECT = Path(__file__).resolve().parent.parent
PAYLOAD = PROJECT / "audit_trail" / "data" / "dashboard_payload.json"
BASELINE = {
    "date": "2026-04-15",
    "source": "dashboard_payload.json recent_closed",
    "thresholds": {
        "CRYPTO": {"fwd_wr_min_pct": 45, "score_min": 55, "trust_min": 3,
                    "observed_wr": 56.3, "observed_n": 474},
        "EQUITY": {"fwd_wr_min_pct": 55, "score_min": 50, "trust_min": 3,
                    "observed_wr": 68.8, "observed_n": 80},
        # FOREX thresholds were calibrated on N=34 — highest revalidation priority as N grows.
        # ⚠️ This threshold needs the MOST scrutiny at the next revalidation:
        #   small sample means even a few new losses could flip the edge.
        #   Re-run when N >= 50 and compare; if WR drops below 60% consider tightening.
        "FOREX":  {"fwd_wr_min_pct": 55, "score_min": 40, "trust_min": 0,
                    "observed_wr": 70.6, "observed_n": 34, "warning": "small sample"},
    },
}


def _fwd_wr_pct(p: dict) -> float:
    f = p.get("strat_fwd_wr", p.get("forward_wr", 0))
    try:
        f = float(f)
    except (ValueError, TypeError):
        return 0
    return f if f > 1.5 else f * 100


def _score(p: dict) -> float:
    try:
        return float(p.get("score", 0))
    except (ValueError, TypeError):
        return 0


def _trust(p: dict) -> float:
    try:
        return float(p.get("trust_score", p.get("trust_score_1", 0)))
    except (ValueError, TypeError):
        return 0


def _asset_class(p: dict) -> str:
    ac = str(p.get("asset_class", "")).upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        ac = "EQUITY"
    if ac == "COMMODITIES":
        ac = "COMMODITY"
    if ac == "BONDS":
        ac = "BOND"
    return ac or "CRYPTO"


def passes_hc_gate(p: dict, cls: str) -> bool:
    """Check if a pick passes the NEW per-class HC gate."""
    fwd = _fwd_wr_pct(p)
    score = _score(p)
    trust = _trust(p)

    if cls == "CRYPTO":
        return fwd >= 45 and score >= 55 and trust >= 3
    if cls == "EQUITY":
        return fwd >= 55 and score >= 50 and trust >= 3
    if cls == "FOREX":
        return fwd >= 55 and score >= 40
    return False


def run_analysis() -> dict:
    """Run edge analysis on current data and return results dict."""
    if not PAYLOAD.exists():
        raise FileNotFoundError(f"Payload not found: {PAYLOAD}")

    data = json.loads(PAYLOAD.read_text(encoding="utf-8", errors="replace"))
    recent_closed = data.get("picks", {}).get("recent_closed", [])
    if not recent_closed:
        raise ValueError(f"No recent_closed picks found in {PAYLOAD}")

    print(f"Loaded {len(recent_closed)} recent closed picks from dashboard_payload.json")

    # ── Per-asset-class WR for picks passing HC gates ──
    results: dict[str, dict] = {}

    for cls in ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF"):
        cls_picks = [p for p in recent_closed if _asset_class(p) == cls]
        hc_pass = [p for p in cls_picks if passes_hc_gate(p, cls)]

        won = 0
        decided = 0
        for p in hc_pass:
            status = str(p.get("status", "")).upper()
            if status == "WON" or "TP_HIT" in status:
                won += 1
                decided += 1
            elif status == "LOST" or "SL_HIT" in status or "STOP_LOSS" in status:
                decided += 1

        wr = (won / decided * 100) if decided > 0 else 0
        results[cls] = {
            "total_in_class": len(cls_picks),
            "hc_pass_count": len(hc_pass),
            "decided": decided,
            "won": won,
            "wr_pct": round(wr, 1),
        }

    # ── Also compute baseline threshold WR (all classes, no gate) ──
    for cls in ("CRYPTO", "EQUITY", "FOREX"):
        cls_picks = [p for p in recent_closed if _asset_class(p) == cls]
        won_all = 0
        decided_all = 0
        for p in cls_picks:
            status = str(p.get("status", "")).upper()
            if status == "WON" or "TP_HIT" in status:
                won_all += 1
                decided_all += 1
            elif status == "LOST" or "SL_HIT" in status or "STOP_LOSS" in status:
                decided_all += 1
        wr_all = (won_all / decided_all * 100) if decided_all > 0 else 0
        results[cls]["ungated_decided"] = decided_all
        results[cls]["ungated_wr_pct"] = round(wr_all, 1)

    return results


def compare_baseline(results: dict) -> None:
    """Compare current results against baseline and flag drift."""
    print("\n" + "=" * 70)
    print("HC EDGE RE-VALIDATION — Baseline Comparison")
    print("=" * 70)
    print(f"Baseline date: {BASELINE['date']}")
    print(f"Current date:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    flags = []

    for cls in ("CRYPTO", "EQUITY", "FOREX"):
        bl = BASELINE["thresholds"].get(cls)
        if not bl:
            continue
        cur = results.get(cls, {})

        bl_wr = bl["observed_wr"]
        bl_n = bl["observed_n"]
        cur_wr = cur.get("wr_pct", 0)
        cur_n = cur.get("decided", 0)

        delta_wr = cur_wr - bl_wr
        delta_n = cur_n - bl_n

        # Flag criteria
        flag_reasons = []
        if cls == "FOREX" and cur_n < 50:
            flag_reasons.append(f"FOREX N={cur_n} still < 50 (baseline N={bl_n})")
        if abs(delta_wr) > 10:
            flag_reasons.append(f"WR drifted {delta_wr:+.1f}pp from baseline {bl_wr}%")
        if cur_wr < 50:
            flag_reasons.append(f"WR below 50% -- no edge!")

        status = "OK" if not flag_reasons else "FLAG"
        print(f"  [{status:4s}] {cls:9s}  Baseline WR={bl_wr}% (N={bl_n})  "
              f"Current WR={cur_wr}% (N={cur_n})  dWR={delta_wr:+.1f}pp  dN={delta_n:+d}")

        if flag_reasons:
            for r in flag_reasons:
                print(f"     WARNING: {r}")
            flags.append(cls)

    print()
    if flags:
        print(f"!! CLASSES NEEDING THRESHOLD REVISION: {', '.join(flags)}")
        print("   Consider relaxing or tightening HC gates for these classes.")
        print("   Edit: audit_dashboard/hc_filter.js + template.html passesValidatedEdgePerClass()")
    else:
        print("OK  All classes stable -- HC thresholds remain valid.")


def print_results(results: dict) -> None:
    """Print the raw analysis results."""
    print("\n" + "=" * 70)
    print("HC EDGE ANALYSIS — Current Data")
    print("=" * 70)

    for cls in ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF"):
        r = results.get(cls, {})
        print(f"\n  {cls}:")
        print(f"    Total picks in class:  {r.get('total_in_class', 0)}")
        print(f"    Pass HC gate:          {r.get('hc_pass_count', 0)}")
        print(f"    Decided (W/L):         {r.get('decided', 0)}")
        print(f"    Won:                   {r.get('won', 0)}")
        print(f"    WR:                    {r.get('wr_pct', 0)}%")
        if "ungated_wr_pct" in r:
            print(f"    Ungated WR (all picks): {r.get('ungated_wr_pct', 0)}% "
                  f"(N={r.get('ungated_decided', 0)})")
            lift = r.get('wr_pct', 0) - r.get('ungated_wr_pct', 0)
            print(f"    HC lift:               {lift:+.1f}pp")


def main():
    try:
        results = run_analysis()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print_results(results)
    compare_baseline(results)

    # Save current results for future comparison
    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": str(PAYLOAD),
        "results": results,
        "baseline": BASELINE,
    }
    out_path = PROJECT / "audit_trail" / "data" / "hc_edge_latest.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()

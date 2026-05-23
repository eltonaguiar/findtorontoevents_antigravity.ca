"""Per-pick HC gate failure diagnostic.

Reads dashboard_data.json and emits a report of which gate each active pick
hits first, grouped by asset class. Useful for answering:
  "If I wanted to unlock EQUITY HC picks, which gate do I have to improve?"
  "Which source systems are dominant in Gate 1 failures?"
  "Is META still near-miss on Gate 1, or has its score shifted?"

Reuses Cursor's gate logic from tools/dashboard_hc_rules.py for parity
with the live JS filter.

Usage:
    python tools/hc_gate_failure_report.py
    python tools/hc_gate_failure_report.py --json  # machine-readable
    python tools/hc_gate_failure_report.py --class EQUITY  # filter to one class
    python tools/hc_gate_failure_report.py --promote  # write promoted near-miss picks
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

try:
    from tools.dashboard_hc_rules import get_hc_gate_params, _num, count_independent_groups
except ImportError:
    print("ERROR: tools/dashboard_hc_rules.py not available — needed for gate parity.")
    sys.exit(1)


def normalize_asset_class(p: dict) -> str:
    ac = str(p.get("asset_class") or p.get("asset_class_type") or "").upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        return "EQUITY"
    if ac == "COMMODITIES":
        return "COMMODITY"
    if ac == "BONDS":
        return "BOND"
    return ac or "CRYPTO"


def first_failed_gate(p: dict, params: dict) -> str | None:
    """Return the first gate name that fails, or None if the pick passes."""
    score = _num(p.get("score"))
    trust = _num(p.get("trust_score") or p.get("trust_score_1"))
    trust_tier = str(p.get("trust_tier") or "").upper()
    fwd_wr = _num(p.get("strat_fwd_wr") or p.get("forward_wr"))
    if fwd_wr > 1.5:
        fwd_wr /= 100.0
    fwd_n = int(_num(p.get("strat_fwd_trades") or p.get("forward_trades") or 0))
    conf = _num(p.get("confidence") or 0)
    if conf > 1:
        conf /= 100
    direction = str(p.get("direction") or p.get("signal_type") or "LONG").upper()
    regime = str(p.get("regime_at_entry") or p.get("market_regime") or p.get("regime") or "").lower()
    ac = normalize_asset_class(p)
    wf = str(p.get("wf_verdict") or p.get("walk_forward_verdict") or "").upper()

    if score < params.get("scoreAbsoluteFloor", 40):
        return f"G1: score={score:.0f} < {params.get('scoreAbsoluteFloor', 40)}"
    if score < params.get("scoreCompoundFloor", 50) and trust < params.get("scoreCompoundTrustMin", 8):
        return f"G2: compound (score {score:.0f}<50 AND trust {trust:.0f}<8)"
    bl = params.get("trustTierBlacklist", [])
    if trust_tier in [str(x).upper() for x in bl]:
        return f"G3: trust_tier={trust_tier} in blacklist"
    if fwd_n < params.get("forwardTradesMin", 5):
        return f"G4: fwdN={fwd_n} < {params.get('forwardTradesMin', 5)}"
    if fwd_wr < params.get("forwardWRMinPct", 45) / 100:
        return f"G5: fwdWR={fwd_wr:.2f} < {params.get('forwardWRMinPct', 45) / 100}"
    trust_floor = (
        params.get("trustScoreMinCrypto", 6) if ac == "CRYPTO" else params.get("trustScoreMinOther", 5)
    )
    if trust < trust_floor:
        return f"G6: trust={trust:.0f} < {trust_floor} ({ac})"
    if conf > params.get("confidenceExtremeMax", 0.95) and fwd_n < params.get("confidenceExtremeFwdTradesMax", 30):
        return f"G7a: conf={conf:.2f} > 0.95 AND fwdN<30"
    if conf > params.get("confidenceMax", 0.90) and fwd_n < params.get("confidenceFwdTradesMax", 20):
        return f"G7b: conf={conf:.2f} > 0.90 AND fwdN<20"
    bear_regimes = params.get("bearRegimes", ["bear", "trending_down", "crash", "distribution"])
    if direction == "LONG" and any(b in regime for b in bear_regimes):
        return f"G8a: long in bear regime ({regime})"
    bull_regimes = params.get("bullRegimes", ["bull", "trending_up", "strong_bull"])
    if direction == "SHORT" and any(b in regime for b in bull_regimes) and trust_tier != "PROVEN":
        return f"G8b: short in bull regime"
    if params.get("rejectWalkForwardFailing", True) and wf == "FAILING":
        return f"G9: walk_forward=FAILING"
    # Consensus gate
    igmin = int(params.get("independentGroupsMin", 3))
    if igmin > 0:
        sources_raw = p.get("source_systems") or p.get("agreeing_sources") or ""
        has_sources = (
            (isinstance(sources_raw, list) and len(sources_raw) > 0)
            or (isinstance(sources_raw, str) and sources_raw.strip())
        )
        if has_sources:
            signal_groups = params.get("signalGroups", {})
            n_groups = count_independent_groups(p, signal_groups)
            if n_groups < igmin:
                return f"G_consensus: {n_groups} indep groups < {igmin}"

    # Gate 10 (score/elite/conf/proven/diversification paths)
    if score >= params.get("scoreEliteFloor", 70):
        return None  # passes via score-elite path
    elite = _num(p.get("elite_score") or 0)
    if elite >= params.get("eliteScoreFloor", 60):
        return None
    conf_floor = params.get("confidenceEdgeFloor", 0.75)
    if conf >= conf_floor:
        exclude = params.get("confidenceEdgeExcludeStrategies", [])
        strategy = str(p.get("strategy") or "")
        if strategy not in exclude:
            return None
    return f"G10: no elite/conf/proven path (score={score:.0f}, elite={elite:.0f}, conf={conf:.2f})"

    # G10 exhaustively covers remaining picks: pass via elite/conf paths above,
    # else fail with message above — no unhandled case remains


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--class", dest="asset_class", default=None, help="Filter to one asset class")
    parser.add_argument("--data", default="audit_dashboard/data/dashboard_data.json")
    parser.add_argument("--promote", action="store_true", help="Write promoted near-miss picks to data/near_miss_promoted.json")
    args = parser.parse_args()

    d = json.load(open(args.data, encoding="utf-8"))
    active = d["picks"]["active"]
    params = get_hc_gate_params()

    per_class_gate_counts: dict[str, Counter] = defaultdict(Counter)
    per_class_total: Counter = Counter()
    passing_picks: list = []
    near_miss: dict[str, list] = defaultdict(list)  # picks failing only at one specific gate

    for p in active:
        ac = normalize_asset_class(p)
        if ac == "SPORTS":
            continue
        if args.asset_class and ac != args.asset_class.upper():
            continue
        per_class_total[ac] += 1
        gate = first_failed_gate(p, params)
        if gate is None:
            passing_picks.append({
                "symbol": p.get("symbol"), "class": ac,
                "score": p.get("score"), "trust": p.get("trust_score"),
                "fwd_wr": p.get("strat_fwd_wr"), "fwd_n": p.get("strat_fwd_trades"),
                "source": p.get("source_system"), "strategy": p.get("strategy"),
            })
        else:
            gate_name = gate.split(":")[0]
            per_class_gate_counts[ac][gate_name] += 1
            # Track near-misses specifically for first-gate-only failures
            if gate_name in ("G1", "G2"):
                near_miss[ac].append({
                    "symbol": p.get("symbol"),
                    "score": p.get("score"),
                    "trust": p.get("trust_score"),
                    "fwd_n": p.get("strat_fwd_trades"),
                    "fwd_wr": p.get("strat_fwd_wr"),
                    "gate": gate,
                    "source": p.get("source_system"),
                    "strategy": p.get("strategy"),
                })

    if args.promote:
        # Write near-miss picks to data/near_miss_promoted.json for ingestion
        out_path = Path("data/near_miss_promoted.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_near_miss": sum(len(v) for v in near_miss.values()),
                    "near_miss_by_class": {k: len(v) for k, v in near_miss.items()},
                    "picks": [
                        {
                            "symbol": p["symbol"],
                            "class": ac,
                            "score": p["score"],
                            "fwd_wr": p["fwd_wr"],
                            "fwd_n": p["fwd_n"],
                            "source": p["source"],
                            "strategy": p["strategy"],
                        }
                        for ac, picks in near_miss.items()
                        for p in picks[:10]  # cap per class
                    ],
                },
                f, indent=2, default=str
            )
        print(f"  [PROMOTE] Wrote {sum(len(v) for v in near_miss.values())} near-miss picks to {out_path}")
        print("  [PROMOTE] Ingest via: python tools/ingest_near_miss.py (or production_scanner.py will auto-promote)")
        return 0

    if args.json:
        out = {
            "total_active": sum(per_class_total.values()),
            "passing": len(passing_picks),
            "per_class_total": dict(per_class_total),
            "per_class_gate_counts": {
                k: dict(v) for k, v in per_class_gate_counts.items()
            },
            "passing_picks": passing_picks,
            "near_miss_g1_g2": dict(near_miss),
        }
        print(json.dumps(out, indent=2, default=str))
        return 0

    # Human-readable
    print(f"Active picks (excl SPORTS): {sum(per_class_total.values())}")
    print(f"Passing all gates: {len(passing_picks)}")
    print()
    for ac in sorted(per_class_total.keys()):
        n_total = per_class_total[ac]
        n_pass = sum(1 for p in passing_picks if p["class"] == ac)
        print(f"  {ac}: {n_pass} pass / {n_total} total")
        if per_class_gate_counts[ac]:
            for gate, count in sorted(per_class_gate_counts[ac].items()):
                print(f"    {gate}: {count}")
    print()
    print("=== Passing picks ===")
    for p in passing_picks:
        print(f"  {p['symbol']:14} | {p['class']:7} | s={p['score']} t={p['trust']} "
              f"fwdWR={p['fwd_wr']} fwdN={p['fwd_n']} | {p['source']} / {str(p['strategy'])[:30]}")

    print()
    print("=== Near-miss picks (G1/G2 only) ===")
    for ac, picks in near_miss.items():
        for p in picks[:10]:
            print(f"  {p['symbol']:14} | {ac:7} | s={p['score']} t={p['trust']} "
                  f"fwdN={p['fwd_n']} fwdWR={p['fwd_wr']} | {p['gate']:40} | {p['source']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

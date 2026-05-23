"""Diagnostic: why non-crypto rows fail HC gates (single dashboard snapshot)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from tools.dashboard_hc_rules import (  # noqa: E402
    filter_high_conviction_ordered,
    get_hc_gate_params,
    _num,
    count_independent_groups,
)


def _normalize_ac(p):
    ac = str(p.get("asset_class") or p.get("asset_class_type") or "").upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        ac = "EQUITY"
    if ac == "COMMODITIES":
        ac = "COMMODITY"
    if ac == "BONDS":
        ac = "BOND"
    if not ac:
        ac = "CRYPTO"
    return ac


def passes_validated_edge_per_class(p):
    if not p:
        return False
    ac = _normalize_ac(p)
    score = float(p.get("score") or 0)
    trust = float(p.get("trust_score") or p.get("trust_score_1") or 0)
    fwd_wr = float(p.get("strat_fwd_wr") or p.get("forward_wr") or 0)
    if fwd_wr > 1.5:
        fwd_wr = fwd_wr / 100.0
    if ac == "CRYPTO":
        return score >= 50 and trust >= 3
    if ac == "EQUITY":
        return score >= 50 and trust >= 3
    if ac == "FOREX":
        return fwd_wr >= 0.50
    return False


def gate_failure_reason(p):
    params = get_hc_gate_params()
    sc = _num(p.get("score"))
    trust = _num(p.get("trust_score") or p.get("trust_score_1"))
    trust_tier = str(p.get("trust_tier") or "").upper()
    fwd_wr = _num(p.get("strat_fwd_wr") or p.get("forward_wr"))
    if fwd_wr > 1.5:
        fwd_wr = fwd_wr / 100.0
    raw_fwd_n = (
        p.get("strat_fwd_trades")
        if p.get("strat_fwd_trades") is not None
        else p.get("forward_trades", 0)
    )
    fwd_n = int(_num(raw_fwd_n))
    cf = _num(p.get("confidence"))
    if cf > 1:
        cf = cf / 100.0
    direction = str(p.get("direction") or p.get("signal_type") or "LONG").upper()
    regime = str(
        p.get("regime_at_entry") or p.get("market_regime") or p.get("regime") or ""
    ).lower()
    asset_class = _normalize_ac(p)

    if sc < params.get("scoreAbsoluteFloor", 40):
        return "Gate1_score_lt_40"
    if sc < params.get("scoreCompoundFloor", 50) and trust < params.get(
        "scoreCompoundTrustMin", 8
    ):
        return "Gate2_compound_score_trust"
    bl = [s.upper() for s in (params.get("trustTierBlacklist") or [])]
    if trust_tier in bl:
        return "Gate3_trust_tier_blacklist"
    if fwd_n < params.get("forwardTradesMin", 5):
        return "Gate4_fwd_n_lt_5"
    if fwd_wr < (params.get("forwardWRMinPct", 45) / 100.0):
        return "Gate5_fwd_wr_lt_45pct"
    trust_floor = (
        params.get("trustScoreMinCrypto", 6)
        if asset_class == "CRYPTO"
        else params.get("trustScoreMinOther", 5)
    )
    if trust < trust_floor:
        return "Gate6_trust_floor"
    cx_max = params.get("confidenceExtremeMax", 0.95)
    cx_fwd = params.get("confidenceExtremeFwdTradesMax", 30)
    if cf > cx_max and fwd_n < cx_fwd:
        return "Gate_conf_extreme"
    c_max = params.get("confidenceMax", 0.90)
    c_fwd = params.get("confidenceFwdTradesMax", 20)
    if cf > c_max and fwd_n < c_fwd:
        return "Gate_conf_high"
    bear_list = params.get("bearRegimes", [])
    bull_list = params.get("bullRegimes", [])
    if params.get("longBlockedInBear") and direction == "LONG":
        for br in bear_list:
            if br in regime:
                return "Gate_bear_long"
    if params.get("shortBlockedInBull") and direction == "SHORT":
        for bu in bull_list:
            if bu in regime:
                if params.get("shortInBullRequiresProven") and trust_tier != "PROVEN":
                    return "Gate_bull_short"
    wf = str(
        p.get("wf_verdict") or p.get("wf_verdict_class") or p.get("walk_forward_verdict") or ""
    ).upper()
    if params.get("rejectWalkForwardFailing") and wf == "FAILING":
        return "Gate_wf_failing"
    ig_min = int(params.get("independentGroupsMin", 0))
    if ig_min > 0:
        raw_src = p.get("source_systems") or p.get("agreeing_sources") or ""
        has_sources = (isinstance(raw_src, list) and len(raw_src) > 0) or (
            isinstance(raw_src, str) and raw_src.strip()
        )
        if has_sources:
            ngrp = count_independent_groups(p, params.get("signalGroups", {}))
            if ngrp < ig_min:
                return "Gate8_independent_groups"
    return "pass_base_gates_or_tier_path"


def main():
    db = _REPO / "audit_dashboard" / "data" / "dashboard_data.json"
    if not db.exists():
        print("no dashboard_data.json")
        return
    data = json.loads(db.read_text(encoding="utf-8"))
    active = data.get("picks", {}).get("active", [])
    print("active_total", len(active))
    ac_ct = Counter(_normalize_ac(p) for p in active)
    print("by_asset_class", dict(ac_ct))
    sports = [p for p in active if _normalize_ac(p) == "SPORTS" or "SPORT" in str(p.get("asset_class", "")).upper()]
    print("sports_like_rows", len(sports))

    non_crypto = [p for p in active if _normalize_ac(p) not in ("CRYPTO", "SPORTS")]
    print("non_crypto_active", len(non_crypto))

    # Per-source forward stats for equity-like
    by_reason = Counter()
    equity_detail = []
    for p in non_crypto:
        r = gate_failure_reason(p)
        by_reason[r] += 1
        if _normalize_ac(p) == "EQUITY":
            equity_detail.append(
                {
                    "symbol": p.get("symbol"),
                    "strategy": (str(p.get("strategy") or ""))[:60],
                    "source": p.get("source_system"),
                    "score": p.get("score"),
                    "trust": p.get("trust_score") or p.get("trust_score_1"),
                    "fwd_n": p.get("strat_fwd_trades"),
                    "fwd_wr": p.get("strat_fwd_wr"),
                    "fail": r,
                }
            )
    print("\nnon_crypto_gate_failure_first_hit", dict(by_reason.most_common(12)))

    hc_ordered = filter_high_conviction_ordered([dict(x) for x in active])
    strict = [p for p in hc_ordered if passes_validated_edge_per_class(p)]
    strict_ac = Counter(_normalize_ac(p) for p in strict)
    print("\nstrict_hc_count", len(strict), "by_class", dict(strict_ac))

    print("\nEQUITY rows sample (up to 15):")
    for row in equity_detail[:15]:
        print(
            " ",
            row["symbol"],
            row["source"],
            f"sc={row['score']} tr={row['trust']} n={row['fwd_n']} wr={row['fwd_wr']}",
            row["fail"],
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Python port of audit_dashboard/hc_filter.js (high-conviction gates v3).
Merged params: embedded defaults (match HC_GATE_PARAMS_EMBEDDED) shallow-overridden
by config/hc_gate_params.json — same as browser/Node getHcGateParams().
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, Optional, Set

REPO = Path(__file__).resolve().parent.parent
HC_CONFIG = REPO / "config" / "hc_gate_params.json"

HC_GATE_PARAMS_EMBEDDED: Dict[str, Any] = {
    "scoreAbsoluteFloor": 40,
    "scoreCompoundFloor": 50,
    "scoreCompoundTrustMin": 8,
    "trustTierBlacklist": ["SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"],
    "trustScoreMinCrypto": 6,
    "trustScoreMinOther": 5,
    "forwardTradesMin": 5,
    "forwardWRMinPct": 55,
    "forwardWRMinPctCrypto": 45,
    "forwardWRMinPctEquity": 55,
    "forwardWRMinPctForex": 55,
    "forwardWRMinPctCommodity": 40,
    "forwardWRMinPctFutures": 40,
    "forwardWRMinPctBond": 40,
    "forwardWRMinPctETF": 40,
    "scoreFloorCrypto": 55,
    "scoreFloorEquity": 50,
    "scoreFloorForex": 40,
    "scoreFloorCommodity": 40,
    "scoreFloorFutures": 40,
    "scoreFloorBond": 40,
    "scoreFloorETF": 40,
    "forexRelaxedWRMinPct": 50,
    "confidenceMax": 0.90,
    "confidenceFwdTradesMax": 20,
    "confidenceExtremeMax": 0.95,
    "confidenceExtremeFwdTradesMax": 30,
    "confidenceLoBand": 0.85,
    "confidenceHiBand": 0.95,
    "confidenceLoBandFwdTradesMin": 30,
    "longBlockedInBear": True,
    "bearRegimes": ["bear", "trending_down", "crash", "distribution"],
    "shortBlockedInBull": True,
    "bullRegimes": ["bull", "trending_up", "strong_bull"],
    "shortInBullRequiresProven": True,
    "rejectWalkForwardFailing": True,
    "independentGroupsMin": 3,
    "tierSABypassIndependentConsensus": True,
    "signalGroups": {
        "ml_engine": [
            "alpha_engine",
            "alpha_engine_fast",
            "ml_crypto_pred",
            "ml_crypto_pred_v12",
            "mercury2",
            "predictions",
            "crypto_ml_edge",
            "dna_winner_picks",
        ],
        "technical": [
            "luxalgo_filters",
            "rapid_fire",
            "breakout_b_ml",
            "breakout_c_spike",
            "baby_strats_forward",
            "tsmom_strategy",
            "super_signals",
        ],
        "regime_group": [
            "regime_terminal",
            "battleground",
            "quan_engine",
            "fear_greed_contrarian",
        ],
        "prediction_market": [
            "pm_whale_signals",
            "pm_kalshi_signals",
            "prediction_market_consensus",
            "pm_momentum_signals",
        ],
        "copy_trader": [
            "copy_trader_highscore",
            "copy_trader_intel",
            "copy_trader_clones",
            "copy_trader_consensus",
        ],
        "ai_challenge": [
            "ai_challenge_predictable",
            "ai_challenge_scanner",
            "claude_gainer_st",
            "chatgpt_combined",
            "kimi_riseoftheclaw",
        ],
        "fundamentals": [
            "pead_earnings_drift",
            "quality_minus_junk",
            "quality_value",
            "earnings_drift",
        ],
    },
    "corrPairs": {
        "ETHUSDT": ["SOLUSDT", "AVAXUSDT", "NEARUSDT"],
        "SOLUSDT": ["ETHUSDT", "AVAXUSDT", "NEARUSDT"],
        "BTCUSDT": ["ETHUSDT", "BNBUSDT"],
        "BNBUSDT": ["BTCUSDT"],
        "AVAXUSDT": ["ETHUSDT", "SOLUSDT"],
        "NEARUSDT": ["ETHUSDT", "SOLUSDT"],
    },
}

HF_TIER_CONTRACT = {
    "fearGreedSubstrings": ["fear_greed_contrarian"],
    "tierSSymbols": ["DOTUSDT", "SUIUSDT", "LTCUSDT", "NEARUSDT", "XRPUSDT"],
    "tierAExtraSymbols": [
        "LINKUSDT",
        "ATOMUSDT",
        "AVAXUSDT",
        "SOLUSDT",
        "ADAUSDT",
        "BNBUSDT",
    ],
    "tierBMajors": ["BTCUSDT", "ETHUSDT"],
    "nonCryptoTierAStrats": ["pead_earnings_drift", "quality_value"],
    "nonCryptoTierBStrats": [
        "pead_earnings_drift",
        "quality_minus_junk",
        "quality_value",
        "earnings_drift",
    ],
}

_params_cache: Optional[Dict[str, Any]] = None


def _shallow_merge(base: Dict[str, Any], over: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(base)
    if not over:
        return out
    for k, v in over.items():
        if k == "_doc":
            continue
        out[k] = v
    return out


def get_hc_gate_params() -> Dict[str, Any]:
    global _params_cache
    if _params_cache is not None:
        return _params_cache
    file_p: Dict[str, Any] = {}
    if HC_CONFIG.is_file():
        try:
            raw = json.loads(HC_CONFIG.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                file_p = raw
        except (OSError, json.JSONDecodeError):
            pass
    _params_cache = _shallow_merge(deepcopy(HC_GATE_PARAMS_EMBEDDED), file_p)
    return _params_cache


def reset_hc_gate_params_cache() -> None:
    global _params_cache
    _params_cache = None


def normalize_asset_class(pick: Dict[str, Any]) -> str:
    ac = str(pick.get("asset_class") or pick.get("asset_class_type") or "").upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        ac = "EQUITY"
    if ac == "COMMODITIES":
        ac = "COMMODITY"
    if not ac:
        ac = "CRYPTO"
    return ac


def _split_sources(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [
            re.sub(r"_(standalone|live_signals|signal_tracking)$", "", str(s).strip().lower())
            for s in raw
        ]
    s = str(raw or "").strip()
    if not s:
        return []
    return [x.strip().lower() for x in re.split(r"[,;|]", s) if x.strip()]


def count_independent_groups(pick: Dict[str, Any], groups: Dict[str, List[str]]) -> int:
    sources = _split_sources(pick.get("source_systems") or pick.get("agreeing_sources") or "")
    if not sources:
        return 0
    seen: Set[str] = set()
    for src in sources:
        for gname, members in groups.items():
            if gname in seen:
                continue
            for m in members:
                if m.lower() in src:
                    seen.add(gname)
                    break
    return len(seen)


def passes_per_asset_tier_contract(pick: Dict[str, Any]) -> bool:
    tier = str(pick.get("hf_conviction_tier") or "").upper()
    if tier not in ("S", "A", "B"):
        return False
    ac = normalize_asset_class(pick)
    sym = str(pick.get("symbol") or "").upper()
    strat = str(pick.get("strategy") or "").lower()
    C = HF_TIER_CONTRACT
    if ac != "CRYPTO":
        frags = C["nonCryptoTierAStrats"] if tier == "A" else C["nonCryptoTierBStrats"]
        if tier in ("A", "B"):
            for frag in frags:
                if frag in strat:
                    return True
        return False
    fear = any(fs in strat for fs in C["fearGreedSubstrings"])
    if tier == "S" and fear and sym in C["tierSSymbols"]:
        return True
    if (
        tier == "A"
        and fear
        and (sym in C["tierSSymbols"] or sym in C["tierAExtraSymbols"])
    ):
        return True
    if tier == "B" and sym in C["tierBMajors"]:
        return True
    if tier == "B" and str(pick.get("trade_timeframe") or pick.get("timeframe") or "").upper() == "INTRADAY":
        return True
    return False


def has_bypass_tier_reason(pick: Dict[str, Any]) -> bool:
    raw = pick.get("hf_conviction_reasons")
    reasons = raw if isinstance(raw, list) else ([raw] if raw else [])
    for r in reasons:
        reason = str(r or "").lower()
        if reason.startswith("bypass_tier_a_") or reason.startswith("bypass_tier_b_"):
            return True
    return False


def evaluate_hc_gates_1to9(
    pick: Dict[str, Any],
    *,
    skip_independent_consensus: bool = False,
    corr_registry: Optional[MutableMapping[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> bool:
    p = pick or {}
    params = params or get_hc_gate_params()

    sc = float(p.get("score") or 0)
    trust = float(p.get("trust_score") or p.get("trust_score_1") or 0)
    trust_tier = str(p.get("trust_tier") or "").upper()

    fwd_wr = float(p.get("strat_fwd_wr") or p.get("forward_wr") or 0)
    if fwd_wr > 1.5:
        fwd_wr /= 100.0

    fwd_n = int(
        p.get("strat_fwd_trades") if p.get("strat_fwd_trades") is not None else p.get("forward_trades") or 0
    )

    cf = float(p.get("confidence") or 0)
    if cf > 1:
        cf /= 100.0

    direction = str(p.get("direction") or p.get("signal_type") or "LONG").upper()
    if direction in ("BUY",):
        direction = "LONG"
    if direction in ("SELL",):
        direction = "SHORT"

    regime = str(p.get("regime_at_entry") or p.get("market_regime") or p.get("regime") or "").lower()
    asset_class = normalize_asset_class(p)

    if sc < float(params.get("scoreAbsoluteFloor") or 40):
        return False
    if sc < float(params.get("scoreCompoundFloor") or 50) and trust < float(params.get("scoreCompoundTrustMin") or 8):
        return False

    for bl in params.get("trustTierBlacklist") or []:
        if trust_tier == str(bl or "").upper():
            return False

    small_sample_low_floor = asset_class in ("COMMODITY", "FUTURES", "BOND", "ETF")
    fwd_min_trades = 2 if small_sample_low_floor else int(params.get("forwardTradesMin") or 5)
    if fwd_n < fwd_min_trades:
        return False

    def _num(x: Any, default: float) -> float:
        try:
            return float(x)
        except (TypeError, ValueError):
            return float(default)

    fwd_floor_ac = (
        _num(params.get("forwardWRMinPctCrypto"), 45)
        if asset_class == "CRYPTO"
        else _num(params.get("forwardWRMinPctEquity"), 55)
        if asset_class == "EQUITY"
        else _num(params.get("forwardWRMinPctForex"), 55)
        if asset_class == "FOREX"
        else _num(params.get("forwardWRMinPctCommodity"), 40)
        if asset_class == "COMMODITY"
        else _num(params.get("forwardWRMinPctFutures"), 40)
        if asset_class == "FUTURES"
        else _num(params.get("forwardWRMinPctBond"), 40)
        if asset_class == "BOND"
        else _num(params.get("forwardWRMinPctETF"), 40)
        if asset_class == "ETF"
        else _num(params.get("forwardWRMinPct"), 55)
    )

    forex_auto_relax = asset_class == "FOREX" and fwd_n < 20
    if forex_auto_relax:
        fwd_floor_ac = float(params.get("forexRelaxedWRMinPct") or 50)

    if fwd_wr < fwd_floor_ac / 100.0:
        return False

    score_floor_ac = (
        _num(params.get("scoreFloorCrypto"), 55)
        if asset_class == "CRYPTO"
        else _num(params.get("scoreFloorEquity"), 50)
        if asset_class == "EQUITY"
        else _num(params.get("scoreFloorForex"), 40)
        if asset_class == "FOREX"
        else _num(params.get("scoreFloorCommodity"), 40)
        if asset_class == "COMMODITY"
        else _num(params.get("scoreFloorFutures"), 40)
        if asset_class == "FUTURES"
        else _num(params.get("scoreFloorBond"), 40)
        if asset_class == "BOND"
        else _num(params.get("scoreFloorETF"), 40)
        if asset_class == "ETF"
        else float(params.get("scoreCompoundFloor") or 50)
    )
    if sc < score_floor_ac:
        return False

    trust_floor = float(params.get("trustScoreMinCrypto") or 6) if asset_class == "CRYPTO" else float(
        params.get("trustScoreMinOther") or 5
    )
    if trust < trust_floor:
        return False

    cx_max = float(params.get("confidenceExtremeMax") or 0.95)
    cx_fwd = int(params.get("confidenceExtremeFwdTradesMax") or 30)
    if cf > cx_max and fwd_n < cx_fwd:
        return False
    c_max = float(params.get("confidenceMax") or 0.90)
    c_fwd = int(params.get("confidenceFwdTradesMax") or 20)
    if cf > c_max and fwd_n < c_fwd:
        return False

    # Gate 7b: REMOVED 2026-04-23 (matches hc_filter.js line 381).
    # Prior evidence: PF 0.61 on n=126 picks, but larger analysis showed
    # flat/non-predictive at 0.85–0.95 band. Now a tiebreaker, not rejection.
    # Python parity fix (2026-05-02): comment this out to match JS behavior.
    # if not forex_auto_relax:
    #     cf_lo = float(params.get("confidenceLoBand") or 0.85)
    #     cf_hi = float(params.get("confidenceHiBand") or 0.95)
    #     cf_lo_fwd_min = int(params.get("confidenceLoBandFwdTradesMin") or 30)
    #     if cf_lo <= cf <= cf_hi and fwd_n < cf_lo_fwd_min:
    #         return False

    bear_list = params.get("bearRegimes") or []
    bull_list = params.get("bullRegimes") or []
    if params.get("longBlockedInBear") and direction == "LONG":
        for br in bear_list:
            if str(br).lower() in regime:
                return False
    if params.get("shortBlockedInBull") and direction == "SHORT":
        for br in bull_list:
            if str(br).lower() in regime:
                if params.get("shortInBullRequiresProven") and trust_tier != "PROVEN":
                    return False

    wf = str(
        p.get("wf_verdict") or p.get("wf_verdict_class") or p.get("walk_forward_verdict") or ""
    ).upper()
    if params.get("rejectWalkForwardFailing") and wf == "FAILING":
        return False

    ig_min = int(params.get("independentGroupsMin") or 0)
    if not skip_independent_consensus and ig_min > 0:
        raw_src = p.get("source_systems") or p.get("agreeing_sources") or ""
        has_sources = bool(
            (isinstance(raw_src, list) and len(raw_src) > 0) or str(raw_src).strip()
        )
        if has_sources:
            ngrp = count_independent_groups(p, params.get("signalGroups") or {})
            if ngrp < ig_min:
                return False

    corr_pairs = params.get("corrPairs") or {}
    sym_u = str(p.get("symbol") or "").upper()
    if corr_registry is not None and sym_u and sym_u in corr_pairs:
        neighbors = corr_pairs[sym_u]
        if isinstance(neighbors, list):
            for other in neighbors:
                ou = str(other or "").upper()
                if ou in corr_registry and corr_registry[ou] == direction:
                    return False

    return True


def passes_stamped_tier_supplemental_path(pick: Dict[str, Any], corr_registry: Optional[MutableMapping[str, str]] = None) -> bool:
    p = pick or {}
    tier = str(p.get("hf_conviction_tier") or "").upper()
    if tier not in ("S", "A", "B"):
        return False
    if not passes_per_asset_tier_contract(p) and not has_bypass_tier_reason(p):
        return False
    params = get_hc_gate_params()
    bypass = bool(params.get("tierSABypassIndependentConsensus"))
    skip8 = bypass and tier in ("S", "A")
    if tier == "B":
        skip8 = False
    return evaluate_hc_gates_1to9(p, skip_independent_consensus=skip8, corr_registry=corr_registry)


def passes_high_conviction_pick(
    pick: Dict[str, Any], corr_registry: Optional[MutableMapping[str, str]] = None
) -> bool:
    if evaluate_hc_gates_1to9(pick, corr_registry=corr_registry):
        return True
    return passes_stamped_tier_supplemental_path(pick, corr_registry=corr_registry)


def filter_high_conviction_ordered(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    registry: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for pick in picks:
        if passes_high_conviction_pick(pick, corr_registry=registry):
            out.append(pick)
            sym = str(pick.get("symbol") or "").upper()
            direction = str(pick.get("direction") or pick.get("signal_type") or "LONG").upper()
            if sym:
                registry[sym] = direction
    return out


# ---------------------------------------------------------------------------
# B17 (2026-05-02) — After-cost shadow HC gate
# ---------------------------------------------------------------------------
# Uses after_cost_net_per_trade + wilson_lb_wr stamped by dashboard_generator.py
# from the B16 forward-edge-audit artifact (tools/forward_edge_audit.py).
#
# Default-OFF behind HC_AFTER_COST_GATE_ENABLED=1 env flag. When OFF: returns
# True (passthrough) — no production behavior change. When ON: blocks picks
# whose strategy is a KNOWN non-survivor (after_cost_net_per_trade ≤ 0 OR
# wilson_lb_wr < 50). None fields (unknown strategy) always pass.
#
# Usage:
#   if not passes_hc_after_cost(pick):
#       skip  # during 14-day shadow run, log only
# ---------------------------------------------------------------------------
import os as _os


def passes_hc_after_cost(pick: Dict[str, Any]) -> bool:
    """Shadow after-cost HC gate.  Default-OFF (HC_AFTER_COST_GATE_ENABLED=1 to enable).

    Returns True (pass) when:
    - Flag is OFF (default)
    - Fields are None (strategy not in B16 index — unknown, not blocked)
    - after_cost_net_per_trade > 0 AND wilson_lb_wr >= 50.0
    Returns False (block) only when:
    - Flag is ON AND both fields are populated AND either criterion fails.
    """
    if _os.environ.get("HC_AFTER_COST_GATE_ENABLED", "0") != "1":
        return True  # shadow flag OFF — passthrough

    net = pick.get("after_cost_net_per_trade")
    lb = pick.get("wilson_lb_wr")

    if net is None or lb is None:
        return True  # unknown strategy — don't filter

    try:
        return float(net) > 0 and float(lb) >= 50.0
    except (TypeError, ValueError):
        return True  # malformed fields — don't filter

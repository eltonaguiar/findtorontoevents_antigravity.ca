"""
Python mirror of audit_dashboard/hc_filter.js — v3 shared gates + stamped HF tier / per-class contract.

Keep in sync when JS changes — run `python tools/validate_dashboard_parity.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional

_REPO = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _REPO / "config" / "hc_gate_params.json"

_PARAMS_CACHE: dict[str, Any] | None = None

_EMBEDDED_DEFAULTS: dict[str, Any] = {
    "scoreAbsoluteFloor": 40,
    "scoreCompoundFloor": 50,
    "scoreCompoundTrustMin": 8,
    "trustTierBlacklist": ["SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"],
    "trustScoreMinCrypto": 4,
    "trustScoreMinOther": 5,
    "forwardTradesMin": 5,
    "forwardWRMinPct": 55,
    # 2026-04-14: Per-asset-class validated-edge FWD WR + Score floors (3500-pick analysis)
    "forwardWRMinPctCrypto": 40,
    "forwardWRMinPctEquity": 50,
    "forwardWRMinPctForex": 55,
    "scoreFloorCrypto": 45,
    "scoreFloorEquity": 45,
    "scoreFloorForex": 40,
    "forexRelaxedWRMinPct": 50,  # FOREX auto-relax: used when fwdN < 20 (small sample)
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
            "alpha_engine", "alpha_engine_fast", "ml_crypto_pred", "ml_crypto_pred_v12",
            "mercury2", "predictions", "crypto_ml_edge", "dna_winner_picks",
        ],
        "technical": [
            "luxalgo_filters", "rapid_fire", "breakout_b_ml", "breakout_c_spike",
            "baby_strats_forward", "tsmom_strategy", "super_signals",
        ],
        "regime_group": [
            "regime_terminal", "battleground", "quan_engine", "fear_greed_contrarian",
        ],
        "prediction_market": [
            "pm_whale_signals", "pm_kalshi_signals", "prediction_market_consensus",
            "pm_momentum_signals",
        ],
        "copy_trader": [
            "copy_trader_highscore", "copy_trader_intel", "copy_trader_clones",
            "copy_trader_consensus",
        ],
        "ai_challenge": [
            "ai_challenge_predictable", "ai_challenge_scanner",
            "claude_gainer_st", "chatgpt_combined", "kimi_riseoftheclaw",
        ],
        "fundamentals": [
            "pead_earnings_drift", "quality_minus_junk", "quality_value", "earnings_drift",
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

# Mirrors config/hf_conviction_tiers.json (subset for dashboard contract).
_HF_TIER_CONTRACT: dict[str, Any] = {
    "fearGreedSubstrings": ["fear_greed_contrarian"],
    "tierSSymbols": ["DOTUSDT", "SUIUSDT", "LTCUSDT", "NEARUSDT", "XRPUSDT"],
    "tierAExtraSymbols": ["LINKUSDT", "ATOMUSDT", "AVAXUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT"],
    "tierBMajors": ["BTCUSDT", "ETHUSDT"],
    "nonCryptoTierAStrats": ["pead_earnings_drift", "quality_value"],
    "nonCryptoTierBStrats": [
        "pead_earnings_drift",
        "quality_minus_junk",
        "quality_value",
        "earnings_drift",
    ],
}


def _num(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def reset_params_cache() -> None:
    global _PARAMS_CACHE
    _PARAMS_CACHE = None


def get_hc_gate_params() -> dict[str, Any]:
    global _PARAMS_CACHE
    if _PARAMS_CACHE is not None:
        return _PARAMS_CACHE
    merged = dict(_EMBEDDED_DEFAULTS)
    if _CONFIG_PATH.exists():
        try:
            raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            raw.pop("_doc", None)
            merged.update(raw)
        except Exception:
            pass
    _PARAMS_CACHE = merged
    return merged


def _normalize_asset_class(pick: Mapping[str, Any]) -> str:
    asset_class = str(pick.get("asset_class") or pick.get("asset_class_type") or "").upper()
    if asset_class in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        asset_class = "EQUITY"
    if asset_class == "COMMODITIES":
        asset_class = "COMMODITY"
    if not asset_class:
        asset_class = "CRYPTO"
    return asset_class


def passes_per_asset_tier_contract(pick: Mapping[str, Any]) -> bool:
    tier = str(pick.get("hf_conviction_tier") or "").upper()
    if tier not in ("S", "A", "B"):
        return False
    ac = _normalize_asset_class(pick)
    sym = str(pick.get("symbol") or "").upper()
    strat = str(pick.get("strategy") or "").lower()
    c = _HF_TIER_CONTRACT
    if ac != "CRYPTO":
        frags = c["nonCryptoTierAStrats"] if tier == "A" else c["nonCryptoTierBStrats"]
        if tier in ("A", "B"):
            for frag in frags:
                if frag in strat:
                    return True
        return False
    fear = any(fs in strat for fs in c["fearGreedSubstrings"])
    if tier == "S" and fear and sym in c["tierSSymbols"]:
        return True
    if tier == "A" and fear and (sym in c["tierSSymbols"] or sym in c["tierAExtraSymbols"]):
        return True
    if tier == "B" and sym in c["tierBMajors"]:
        return True
    if tier == "B" and str(pick.get("trade_timeframe") or pick.get("timeframe") or "").upper() == "INTRADAY":
        return True
    return False


def has_bypass_tier_reason(pick: Mapping[str, Any]) -> bool:
    raw = pick.get("hf_conviction_reasons")
    reasons = raw if isinstance(raw, list) else ([raw] if raw else [])
    for reason in reasons:
        text = str(reason or "").lower()
        if text.startswith("bypass_tier_a_") or text.startswith("bypass_tier_b_"):
            return True
    return False


def _corr_same_direction_blocked(
    symbol: str,
    direction: str,
    passed_registry: dict[str, str],
    corr_pairs: dict[str, list[str]],
) -> bool:
    u = symbol.upper()
    if not u or u not in corr_pairs:
        return False
    for other in corr_pairs[u]:
        ou = str(other).upper()
        if passed_registry.get(ou) == direction:
            return True
    return False


def count_independent_groups(pick: Mapping[str, Any], groups: dict[str, list[str]]) -> int:
    raw = pick.get("source_systems") or pick.get("agreeing_sources") or ""
    if isinstance(raw, list):
        sources = [
            re.sub(r"_(standalone|live_signals|signal_tracking)$", "", s.strip().lower())
            for s in raw
        ]
    else:
        sources = [s.strip().lower() for s in re.split(r"[,;|]", str(raw)) if s.strip()]
    if not sources:
        return 0
    seen: set[str] = set()
    for src in sources:
        for gname, members in groups.items():
            if gname in seen:
                continue
            for m in members:
                if m.lower() in src:
                    seen.add(gname)
                    break
    return len(seen)


def evaluate_hc_gates_1_to_9(
    pick: Mapping[str, Any] | None,
    *,
    passed_registry: dict[str, str] | None = None,
    skip_independent_consensus: bool = False,
) -> bool:
    p = pick or {}
    params = get_hc_gate_params()

    sc = _num(p.get("score"))
    trust = _num(p.get("trust_score") or p.get("trust_score_1"))
    trust_tier = str(p.get("trust_tier") or "").upper()
    fwd_wr = _num(p.get("strat_fwd_wr") or p.get("forward_wr"))
    if fwd_wr > 1.5:
        fwd_wr = fwd_wr / 100.0
    raw_fwd_n = p.get("strat_fwd_trades") if p.get("strat_fwd_trades") is not None else p.get("forward_trades", 0)
    fwd_n = int(_num(raw_fwd_n))
    cf = _num(p.get("confidence"))
    if cf > 1:
        cf = cf / 100.0
    direction = str(p.get("direction") or p.get("signal_type") or "LONG").upper()
    regime = str(
        p.get("regime_at_entry") or p.get("market_regime") or p.get("regime") or ""
    ).lower()
    asset_class = _normalize_asset_class(p)

    if sc < params.get("scoreAbsoluteFloor", 40):
        return False
    if sc < params.get("scoreCompoundFloor", 50) and trust < params.get("scoreCompoundTrustMin", 8):
        return False

    bl = [s.upper() for s in (params.get("trustTierBlacklist") or [])]
    if trust_tier in bl:
        return False

    if fwd_n < params.get("forwardTradesMin", 5):
        return False
    # 2026-04-14: Per-asset-class validated-edge FWD WR + Score floors
    # Class-specific floor replaces generic forwardWRMinPct (generic is fallback for unlisted classes)
    fwd_floor_ac = (
        params.get("forwardWRMinPctCrypto", 40) if asset_class == "CRYPTO"
        else params.get("forwardWRMinPctEquity", 50) if asset_class == "EQUITY"
        else params.get("forwardWRMinPctForex", 60) if asset_class == "FOREX"
        else params.get("forwardWRMinPct", 55)
    )
    # FOREX auto-relax: if fwdN < 20 (small sample), relax FWD WR floor from 55% to 50%
    forex_auto_relax_active = asset_class == "FOREX" and fwd_n < 20
    if forex_auto_relax_active:
        fwd_floor_ac = params.get("forexRelaxedWRMinPct", 50)
    if fwd_wr < (fwd_floor_ac / 100.0):
        return False

    score_floor_ac = (
        params.get("scoreFloorCrypto", 45) if asset_class == "CRYPTO"
        else params.get("scoreFloorEquity", 45) if asset_class == "EQUITY"
        else params.get("scoreFloorForex", 60) if asset_class == "FOREX"
        else params.get("scoreCompoundFloor", 50)
    )
    if sc < score_floor_ac:
        return False

    trust_floor = (
        params.get("trustScoreMinCrypto", 4)
        if asset_class == "CRYPTO"
        else params.get("trustScoreMinOther", 5)
    )
    if trust < trust_floor:
        return False

    cx_max = params.get("confidenceExtremeMax", 0.95)
    cx_fwd = params.get("confidenceExtremeFwdTradesMax", 30)
    if cf > cx_max and fwd_n < cx_fwd:
        return False
    c_max = params.get("confidenceMax", 0.90)
    c_fwd = params.get("confidenceFwdTradesMax", 20)
    if cf > c_max and fwd_n < c_fwd:
        return False

    # Gate 7b: confidence 0.85-0.95 band with low fwd_n (T1-A, 2026-04-15)
    # Evidence: PF 0.61 on n=126 picks in 0.85-0.95 confidence range
    # Exception: skip if FOREX auto-relax is active (small-sample relax already acknowledges low N)
    if not forex_auto_relax_active:
        cf_lo = params.get("confidenceLoBand", 0.85)
        cf_hi = params.get("confidenceHiBand", 0.95)
        cf_lo_fwd_min = params.get("confidenceLoBandFwdTradesMin", 30)
        if cf >= cf_lo and cf <= cf_hi and fwd_n < cf_lo_fwd_min:
            return False

    bear_list = params.get("bearRegimes", ["bear", "trending_down", "crash", "distribution"])
    bull_list = params.get("bullRegimes", ["bull", "trending_up", "strong_bull"])
    if params.get("longBlockedInBear") and direction == "LONG":
        for br in bear_list:
            if br in regime:
                return False
    if params.get("shortBlockedInBull") and direction == "SHORT":
        for bu in bull_list:
            if bu in regime:
                if params.get("shortInBullRequiresProven") and trust_tier != "PROVEN":
                    return False

    wf = str(p.get("wf_verdict") or p.get("wf_verdict_class") or p.get("walk_forward_verdict") or "").upper()
    if params.get("rejectWalkForwardFailing") and wf == "FAILING":
        return False

    ig_min = int(params.get("independentGroupsMin", 3))
    if not skip_independent_consensus and ig_min > 0:
        raw_src = p.get("source_systems") or p.get("agreeing_sources") or ""
        has_sources = (isinstance(raw_src, list) and len(raw_src) > 0) or (
            isinstance(raw_src, str) and raw_src.strip()
        )
        if has_sources:
            ngrp = count_independent_groups(p, params.get("signalGroups", {}))
            if ngrp < ig_min:
                return False

    if passed_registry is not None:
        sym_u = str(p.get("symbol") or "").upper()
        cp = params.get("corrPairs") or {}
        if isinstance(cp, dict) and _corr_same_direction_blocked(
            sym_u, direction, passed_registry, cp
        ):
            return False

    return True


def passes_stamped_tier_supplemental_path(
    pick: Mapping[str, Any] | None,
    *,
    passed_registry: dict[str, str] | None = None,
) -> bool:
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
    return evaluate_hc_gates_1_to_9(
        p,
        passed_registry=passed_registry,
        skip_independent_consensus=skip8,
    )


def passes_high_conviction_pick(
    pick: Mapping[str, Any] | None,
    *,
    passed_registry: dict[str, str] | None = None,
) -> bool:
    """Same logic as passesHighConvictionPick() in audit_dashboard/hc_filter.js (v3)."""
    # B18: shadow-probation picks are explicitly excluded from HC — they haven't
    # earned a track record yet. Operator sees them on /audit but they don't
    # pass the High-Conviction button filter.
    if pick and pick.get("shadow_mode"):
        return False
    if evaluate_hc_gates_1_to_9(pick, passed_registry=passed_registry):
        return True
    return passes_stamped_tier_supplemental_path(pick, passed_registry=passed_registry)


def filter_high_conviction_ordered(
    picks: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Python mirror of filterHighConvictionOrdered() — preserves Gate 9 batch semantics."""
    reg: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    for raw in picks:
        if not isinstance(raw, dict):
            continue
        p = dict(raw)
        if passes_high_conviction_pick(p, passed_registry=reg):
            sym_u = str(p.get("symbol") or "").upper()
            d = str(p.get("direction") or p.get("signal_type") or "LONG").upper()
            if sym_u:
                reg[sym_u] = d
            out.append(p)
    return out


def passes_high_conviction_heuristics_only(pick: Mapping[str, Any] | None) -> bool:
    """Full dashboard HC predicate (shared gates + stamped tier path)."""
    return passes_high_conviction_pick(pick)


def passes_high_conviction_with_stamped_tier(
    pick: Mapping[str, Any] | None, tier: str | None, reasons: list[str] | None = None
) -> bool:
    """Dashboard behavior if hf_conviction_tier were set from the classifier output."""
    p = dict(pick or {})
    if tier in ("S", "A", "B"):
        p["hf_conviction_tier"] = tier
    if reasons:
        p["hf_conviction_reasons"] = list(reasons)
    return passes_high_conviction_pick(p)


# ---------------------------------------------------------------------------
# B17 (2026-05-02) — After-cost shadow HC gate (import from canonical source)
# ---------------------------------------------------------------------------
# Re-exported here so callers importing from dashboard_hc_rules don't need to
# know about hc_gates_python.  Canonical implementation lives in hc_gates_python.
try:
    from tools.hc_gates_python import passes_hc_after_cost  # noqa: F401
except ImportError:
    import os as _os
    from typing import Any as _Any, Dict as _Dict

    def passes_hc_after_cost(pick: _Dict[str, _Any]) -> bool:  # type: ignore[misc]
        """Fallback when hc_gates_python not importable."""
        if _os.environ.get("HC_AFTER_COST_GATE_ENABLED", "0") != "1":
            return True
        net = pick.get("after_cost_net_per_trade")
        lb = pick.get("wilson_lb_wr")
        if net is None or lb is None:
            return True
        try:
            return float(net) > 0 and float(lb) >= 50.0
        except (TypeError, ValueError):
            return True

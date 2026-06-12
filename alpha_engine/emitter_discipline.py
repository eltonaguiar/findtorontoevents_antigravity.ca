"""
EAGLE2 Emitter Discipline — v1.0 (2026-06-02)

Applies emitter quality gates BEFORE the main quality gate pipeline in
production_scanner.py. Ensures only strategies with forward proof can emit
picks that affect capital.

Tiers:
  PROVEN     — allow through (normal sizing)
  PROBATION  — allow at 0.25x sizing
  MONITOR_ONLY — block from active, optionally log to shadow tracker
  KILL       — hard-block
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

log = logging.getLogger("emitter_discipline")

ROOT = Path(__file__).resolve().parent.parent
AUDIT_FILE = ROOT / "audit_trail" / "data" / "emitter_audit.json"
SHADOW_LOG = ROOT / "audit_trail" / "data" / "emitter_discipline_rejected.json"

_ENFORCE = os.environ.get("EMITTER_DISCIPLINE_ENFORCE", "1").strip().lower() in (
    "1", "true", "yes", "on",
)
_SHADOW_LOG_ENABLED = os.environ.get("EMITTER_DISCIPLINE_SHADOW_LOG", "0").strip().lower() in (
    "1", "true", "yes", "on",
)

HARD_KILL_STRATEGIES: Set[str] = {
    "quan_engine_scalp", "quan_engine_swing", "quan_engine_position",
    "cta_replicator", "rapid_fire", "ensemble", "battleground_luxalgo",
    "binance_smart_money", "multi_asset_scanner",
    "forex_carry_momentum", "forex_carry_ppp", "myfxbook_retail_contrarian",
    "forex_carry_bb_hybrid", "carry_trade_momentum", "forex_rsi2_mean_reversion",
    "inverse_carry_contrarian", "ml_breakout", "genome_mutations",
    "hl_funding_fade", "kimi_signal_tracking", "multi_period_rsi_confluence_eth",
    "claude_gainer_st", "gainer_promoter",
    # P0-4 (2026-06-12): fear-greed contrarian drag
    "st_fear_greed_contrarian", "crypto_fear_greed_contrarian",
    # P0-B (2026-06-12): intrabar bleeders still emitting via backfill
    "futures_momentum", "ig_contrarian_sentiment", "stocks_rsi2_pullback",
    "prediction_market_consensus", "rsi_bounce", "bollinger_squeeze",
    "fx_smart_carry_trade_momentum",
}

MONITOR_ONLY_STRATEGIES: Set[str] = {
    "claude_3_5_haiku", "claude_haiku_4_5", "gpt4o_mini", "gemini_flash",
    "llama_405b", "mistral_small", "nvidia_minimax_m2", "reflexivity_trader",
}

PROVEN_STRATEGIES: Set[str] = {
    "etf_dual_momentum", "etf_sector_momentum", "etf_faber_tactical",
    "etf_risk_parity_rotation", "etf_trend_following",
    "vwap_reversion", "bollinger_mean_reversion", "keltner_squeeze",
    "triple_ema_pullback", "volatility_compression_breakout",
    "vwap_mean_reversion", "inverse_fvg_contrarian", "stochrsi_divergence",
    "adaptive_keltner", "keltner_rsi_squeeze", "keltner_vwap_confluence",
    "obv_support_divergence", "feargreed_contrarian", "multi_day_momentum",
    "williams_r", "triple_rsi", "generic_volatility_breakout",
    "prop_firm_conservative", "donchian_adx_trend_follow",
    "funding_rate_carry", "cross_exchange_basis_carry",
    "cta_commodity_momentum", "commodity_momentum_12_1",
    "volatility_mean_reversion", "trend_triple_confirmation",
    "cross_asset_rotation",
    "deepseek_v4", "gpt4o", "grok3", "deepseek_r1",
}


def is_emission_allowed(strategy: str, source_system: str = "") -> Tuple[bool, str]:
    """P0-B central kill gate (docs/plans/2026-06-12-P0B-unified-kill-list-plan.md).

    ONE function every writer consults — production_scanner already routes via
    apply_emitter_discipline(); ingest writers (backfill_local_sources & co.)
    historically had NO gate, so kills never stuck at the data layer
    (INCIDENT_OVERALL #135: pair-scoped blocklists bypassed by other emitters).

    Checks (cheap, no DB):
      1. HARD_KILL_STRATEGIES (this module)
      2. config.BLACKLISTED_STRATEGIES (lazy import; fail-open if unavailable)
    Returns (allowed, reason). Reason is loggable for shadow audits
    (EMITTER_DISCIPLINE_SHADOW_LOG=1 writers may record rejections).
    """
    strat = (strategy or "").strip().lower()
    src = (source_system or "").strip().lower()
    if not strat and not src:
        return True, "no identity — fail-open"
    hard = {s.lower() for s in HARD_KILL_STRATEGIES}
    if strat in hard or src in hard:
        return False, f"HARD_KILL_STRATEGIES: {strat or src}"
    try:
        from alpha_engine.config import BLACKLISTED_STRATEGIES as _bl
        bl = {str(s).lower() for s in _bl}
        if strat in bl or src in bl:
            return False, f"BLACKLISTED_STRATEGIES: {strat or src}"
    except Exception:
        pass  # config unavailable -> rely on local set only
    try:
        from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS as _bss
        bss = {str(s).lower() for s in _bss}
        if src in bss or strat in bss:
            return False, f"BLOCKED_SOURCE_SYSTEMS: {src or strat}"
    except Exception:
        pass  # quality_gates is heavy/optional in some contexts -> fail-open
    return True, "allowed"


def _load_audit_tiers() -> Tuple[Set[str], Set[str], Set[str]]:
    kill_set = set(HARD_KILL_STRATEGIES)
    monitor_set = set(MONITOR_ONLY_STRATEGIES)
    proven_set = set(PROVEN_STRATEGIES)

    if AUDIT_FILE.exists():
        try:
            with open(AUDIT_FILE) as f:
                audit = json.load(f)
            recs = audit.get("recommended_actions", {})
            for strat in recs.get("force_kill", []):
                if isinstance(strat, str):
                    kill_set.add(strat.lower())
            for strat in recs.get("monitor_only", []):
                if isinstance(strat, str):
                    monitor_set.add(strat.lower())
            for strat in recs.get("proven", []):
                if isinstance(strat, str) and strat.lower() not in kill_set:
                    proven_set.add(strat.lower())
        except (json.JSONDecodeError, IOError):
            pass

    return kill_set, monitor_set, proven_set


def _get_strategy_tier(strategy_name: str) -> str:
    strat = strategy_name.lower().strip()
    if not strat:
        return "UNKNOWN"
    kill_set, monitor_set, proven_set = _load_audit_tiers()
    if strat in kill_set:
        return "KILL"
    if strat in monitor_set:
        return "MONITOR_ONLY"
    if strat in proven_set:
        return "PROVEN"
    try:
        from strategy_priority import get_strategy_tier
        return get_strategy_tier(strategy_name).upper()
    except ImportError:
        return "UNKNOWN"


def apply_emitter_discipline(picks: List[dict]) -> Tuple[List[dict], List[dict]]:
    if not _ENFORCE:
        return picks, []

    passed: List[dict] = []
    rejected: List[dict] = []

    for pick in picks:
        strat = pick.get("strategy", pick.get("strategy_name", ""))
        source = pick.get("source_system", pick.get("system", ""))
        strat_tier = _get_strategy_tier(strat) if strat else "UNKNOWN"
        source_tier = _get_strategy_tier(source) if source else "UNKNOWN"

        tier_order = {"KILL": 0, "MONITOR_ONLY": 1, "UNKNOWN": 2, "PROVEN": 3}
        worst_tier = "PROVEN"
        worst_rank = 3
        for t in (strat_tier, source_tier):
            rank = tier_order.get(t, 2)
            if rank < worst_rank:
                worst_rank = rank
                worst_tier = t

        if worst_tier == "KILL":
            pick["_emitter_rejected"] = f"KILL: {strat or source} — hard-blocked"
            rejected.append(pick)
            continue

        if worst_tier == "MONITOR_ONLY":
            pick["_emitter_rejected"] = f"MONITOR_ONLY: {strat or source}"
            pick["position_multiplier"] = 0.0
            pick["_sizing_override"] = "zero"
            pick["_monitor_mode"] = True
            passed.append(pick)
            continue

        passed.append(pick)

    if rejected and _SHADOW_LOG_ENABLED:
        try:
            SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if SHADOW_LOG.exists():
                with open(SHADOW_LOG) as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            for r in rejected:
                existing.append({
                    "symbol": r.get("symbol", ""),
                    "strategy": r.get("strategy", ""),
                    "asset_class": r.get("asset_class", ""),
                    "rejected_at": datetime.now(timezone.utc).isoformat(),
                    "reason": r.get("_emitter_rejected", ""),
                })
            if len(existing) > 10000:
                existing = existing[-10000:]
            with open(SHADOW_LOG, "w") as f:
                json.dump(existing, f, indent=2)
        except (IOError, json.JSONDecodeError) as e:
            log.warning("Shadow log failed: %s", e)

    return passed, rejected

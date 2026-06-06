#!/usr/bin/env python3
"""Emitter whitelist + toxic kill switch from pf_registry (T2-01 / T2-02).

Loads ``audit_dashboard/data/pf_registry.json`` and builds:
  - allowlist: (asset_class, strategy) with policy_clean_net PF/WR/n thresholds
  - toxic set: n>=20 and PF<1.2 (auto) plus hardcoded swarm kills

Gate modes (env):
  EMITTER_REGISTRY_GATE=1     — run checks in passes_active_gate (default on)
  EMITTER_WHITELIST_ENFORCE=1 — reject picks not on allowlist (default off / shadow)
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO / "audit_dashboard" / "data" / "pf_registry.json"

Pair = Tuple[str, str]

# Grok pf_registry autopsy + MERGED_ACTION_PLAN T2-02 (2026-05-19)
HARDCODED_TOXIC_PAIRS: frozenset[Pair] = frozenset({
    ("CRYPTO", "quan_engine"),
    ("CRYPTO", "quan_engine_scalp"),
    ("CRYPTO", "quan_engine_swing"),
    ("CRYPTO", "quan_engine_position"),
    ("CRYPTO", "prediction_market_consensus"),
    ("CRYPTO", "copy_trader_intel"),
    ("COMMODITY", "cta_replicator"),
    ("FOREX", "multi_asset_copytrader"),
    ("FOREX", "forex_rsi2_mean_reversion"),
    ("EQUITY", "multi_asset_copytrader"),
    ("EQUITY", "regime_terminal"),
    # 2026-06-05: multi_asset_cot COMMODITY live stats WR=17% (n=223 closed) + 91 OPEN
    # losing positions. Hard-code as toxic since policy_clean view has 0 rows.
    ("COMMODITY", "multi_asset_cot"),
})

# Money-ready sleeve mode (INVERSE_ML_BTC_15M_ENABLED=1): only these CRYPTO strategies emit.
INVERSE_ML_SLEEVE_STRATEGIES: frozenset[str] = frozenset({
    "inverse_ml_enhanced_BTCUSDT_15m_D",
    "inverse_ml_enhanced_ADAUSDT_15m_D",
})

# Seeds when registry n is below whitelist floor but forward track is approved
MANUAL_ALLOWLIST_PAIRS: frozenset[Pair] = frozenset({
    ("CRYPTO", "crypto_rsi_whaleconfirmed_v1"),
    ("CRYPTO", "inverse_ml_enhanced_BTCUSDT_15m_D"),
    ("CRYPTO", "inverse_ml_enhanced_ADAUSDT_15m_D"),
    ("COMMODITY", "multi_asset_copytrader"),
    ("FOREX", "cta_replicator"),
})

DEFAULT_MIN_PF = 1.4
DEFAULT_MIN_WR = 55.0
DEFAULT_MIN_N = 50
TOXIC_MIN_N = 20
TOXIC_MAX_PF = 1.2


def _truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def registry_gate_enabled() -> bool:
    return _truthy("EMITTER_REGISTRY_GATE", "1")


def whitelist_enforce_enabled() -> bool:
    return _truthy("EMITTER_WHITELIST_ENFORCE", "0")


def inverse_ml_sleeve_enabled() -> bool:
    return _truthy("INVERSE_ML_BTC_15M_ENABLED", "0")


def passes_inverse_ml_sleeve_gate(pick: Dict[str, Any]) -> bool:
    """When sleeve mode is on, block all CRYPTO picks except inverse_ml BTC/ADA."""
    if not inverse_ml_sleeve_enabled():
        return True
    ac = str(pick.get("asset_class") or pick.get("category") or "CRYPTO").upper()
    if ac != "CRYPTO":
        return True
    strat = str(pick.get("strategy") or pick.get("strategy_name") or "").strip()
    if strat in INVERSE_ML_SLEEVE_STRATEGIES:
        return True
    pick["_hf_quality_gate_reason"] = f"inverse_ml_sleeve_block:{strat or '?'}"
    return False


def _pick_pair(pick: Dict[str, Any]) -> Pair:
    ac = str(pick.get("asset_class") or "CRYPTO").upper()
    strat = str(pick.get("strategy") or pick.get("strategy_name") or "").strip()
    return ac, strat


def _row_pf(row: dict) -> Optional[float]:
    pf = row.get("profit_factor")
    if pf is None:
        return None
    try:
        v = float(pf)
        return v if v == v else None  # NaN guard
    except (TypeError, ValueError):
        return None


def _row_wr(row: dict) -> float:
    try:
        return float(row.get("win_rate_pct") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _row_n(row: dict) -> int:
    try:
        return int(row.get("n") or 0)
    except (TypeError, ValueError):
        return 0


@lru_cache(maxsize=1)
def _load_registry_rows() -> list:
    if not REGISTRY_PATH.is_file():
        return []
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("by_asset_class_strategy_policy_clean_net")
    return rows if isinstance(rows, list) else []


@lru_cache(maxsize=1)
def get_allowlist_pairs() -> frozenset[Pair]:
    min_pf = float(os.environ.get("EMITTER_WHITELIST_MIN_PF", DEFAULT_MIN_PF))
    min_wr = float(os.environ.get("EMITTER_WHITELIST_MIN_WR", DEFAULT_MIN_WR))
    min_n = int(os.environ.get("EMITTER_WHITELIST_MIN_N", DEFAULT_MIN_N))
    allowed: Set[Pair] = set(MANUAL_ALLOWLIST_PAIRS)
    for row in _load_registry_rows():
        if not isinstance(row, dict):
            continue
        ac = str(row.get("asset_class") or "").upper()
        strat = str(row.get("strategy") or "").strip()
        if not ac or not strat:
            continue
        n = _row_n(row)
        pf = _row_pf(row)
        wr = _row_wr(row)
        if n >= min_n and pf is not None and pf >= min_pf and wr >= min_wr:
            allowed.add((ac, strat))
    return frozenset(allowed)


@lru_cache(maxsize=1)
def get_registry_toxic_pairs() -> frozenset[Pair]:
    toxic: Set[Pair] = set()
    for row in _load_registry_rows():
        if not isinstance(row, dict):
            continue
        ac = str(row.get("asset_class") or "").upper()
        strat = str(row.get("strategy") or "").strip()
        if not ac or not strat:
            continue
        n = _row_n(row)
        pf = _row_pf(row)
        if n >= TOXIC_MIN_N and pf is not None and pf < TOXIC_MAX_PF:
            toxic.add((ac, strat))
    return frozenset(toxic)


@lru_cache(maxsize=1)
def get_all_toxic_pairs() -> frozenset[Pair]:
    return HARDCODED_TOXIC_PAIRS | get_registry_toxic_pairs()


def is_toxic_pair(asset_class: str, strategy: str) -> bool:
    return (str(asset_class or "").upper(), str(strategy or "").strip()) in get_all_toxic_pairs()


def is_allowlisted_pair(asset_class: str, strategy: str) -> bool:
    return (str(asset_class or "").upper(), str(strategy or "").strip()) in get_allowlist_pairs()


def evaluate_emitter_registry_gate(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Return verdict dict for stamping on pick + gate decision."""
    ac, strat = _pick_pair(pick)
    toxic = is_toxic_pair(ac, strat)
    allowed = is_allowlisted_pair(ac, strat)
    enforce = whitelist_enforce_enabled()
    would_block = toxic or (bool(strat) and not allowed)
    enforce_block = toxic or (enforce and bool(strat) and not allowed)
    reason = ""
    if toxic:
        reason = f"toxic_pair:{ac}/{strat}"
    elif enforce and strat and not allowed:
        reason = f"not_whitelisted:{ac}/{strat}"
    return {
        "enabled": registry_gate_enabled(),
        "enforce_whitelist": enforce,
        "toxic": toxic,
        "allowlisted": allowed,
        "would_block": would_block,
        "enforce_block": enforce_block,
        "reason": reason,
        "pair": [ac, strat],
    }


def passes_emitter_registry_gate(pick: Dict[str, Any]) -> bool:
    """Admission helper for passes_active_gate. Fail-soft on import errors."""
    if not registry_gate_enabled():
        return True
    try:
        verdict = evaluate_emitter_registry_gate(pick)
        pick["_emitter_registry_gate"] = verdict
        if verdict.get("enforce_block"):
            pick["_hf_quality_gate_reason"] = verdict.get("reason") or "emitter_registry_gate"
            return False
        if verdict.get("would_block"):
            pick["_emitter_registry_would_block"] = True
        return True
    except Exception:
        return True


def clear_caches() -> None:
    _load_registry_rows.cache_clear()
    get_allowlist_pairs.cache_clear()
    get_registry_toxic_pairs.cache_clear()
    get_all_toxic_pairs.cache_clear()

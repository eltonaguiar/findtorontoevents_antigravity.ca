"""Central ATR-based TP/SL policy defaults by asset class."""

from __future__ import annotations

from typing import Any


TP_SL_POLICY: dict[str, dict[str, float]] = {
    "crypto": {
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "default_atr_pct": 2.0,
    },
    "forex": {
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "default_atr_pct": 0.2,
    },
    "equity": {
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "default_atr_pct": 2.0,
    },
    "stock": {
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "default_atr_pct": 2.0,
    },
    "etf": {
        "tp_atr_mult": 1.6,
        "sl_atr_mult": 1.2,
        "default_atr_pct": 1.25,
    },
    "commodity": {
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.5,
        "default_atr_pct": 2.5,
    },
    "futures": {
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.5,
        "default_atr_pct": 2.5,
    },
    "on-chain": {
        "tp_atr_mult": 1.5,
        "sl_atr_mult": 1.0,
        "default_atr_pct": 2.0,
    },
}


def normalize_tpsl_category(category: str | None) -> str:
    raw = str(category or "").strip().lower()
    if raw in TP_SL_POLICY:
        return raw
    if raw in {"stocks"}:
        return "stock"
    if raw in {"onchain", "on_chain"}:
        return "on-chain"
    return "crypto"


def get_tpsl_policy(category: str | None, atr_pct: float | None = None) -> dict[str, Any]:
    normalized = normalize_tpsl_category(category)
    policy = TP_SL_POLICY[normalized]
    atr_pct_value = float(atr_pct) if atr_pct is not None else float(policy["default_atr_pct"])
    tp_pct = atr_pct_value * float(policy["tp_atr_mult"]) / 100.0
    sl_pct = atr_pct_value * float(policy["sl_atr_mult"]) / 100.0
    return {
        "category": normalized,
        "atr_pct": atr_pct_value,
        "tp_atr_mult": float(policy["tp_atr_mult"]),
        "sl_atr_mult": float(policy["sl_atr_mult"]),
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
    }


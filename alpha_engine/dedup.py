"""
alpha_engine/dedup.py — Canonical deduplication and ID helpers for the measurement pipeline.

This module provides the single source of truth for keys used in at_pick_outcomes
and related pf_registry / money-ready calculations.

All changes here are P0 §15 (dedup key harmonization) driven by internal audit
and external TON validation (2026-06-01 fast4 results).
"""

from __future__ import annotations

from typing import Any


def _normalize_symbol(sym: Any) -> str:
    """Upper-case and strip a symbol for stable key construction."""
    return str(sym or "").strip().upper()


def build_canonical_outcomes_pick_id(pick: dict) -> str:
    """
    Single source of truth for the pick_id stored in at_pick_outcomes.

    Must be called by both writers (universal_pick_resolver.py and
    alpha_engine/outcome_resolver.py) and ideally by emitters when enriching
    picks so the "id" they emit is already the canonical outcomes key.

    Refined per TON fast4 consensus (2026-06-01):
    - Prefer a stable raw ID (namespaced with emitter/source context).
    - Fallback uses deterministic fields that align with emission dedup.
    - No redundant hash in the fallback (the fields are sufficient).
    - Version prefix for future-proofing.

    This eliminates the divergence between emission-time dedup keys and the
    primary key used for the outcomes measurement table (the root cause of
    the TON-flagged dedup harmonization gap).

    Args:
        pick: A pick dictionary (from any emitter or resolver stage).

    Returns:
        A stable, versioned canonical string key suitable for at_pick_outcomes.
    """
    # 1. Prefer stable raw ID (namespaced to avoid cross-emitter collisions)
    raw_id = pick.get("id") or pick.get("pick_id") or pick.get("signal_id")
    if raw_id not in (None, ""):
        emitter = pick.get("emitter") or pick.get("source_system") or pick.get("source") or "unknown"
        return f"v1::{emitter}::{raw_id}"

    # 2. Deterministic fallback (no hash — per TON refinement)
    sym = _normalize_symbol(pick.get("symbol"))
    direction = str(pick.get("direction") or pick.get("signal_type") or "LONG").strip().upper()
    if direction in ("SELL", "SHORT"):
        direction = "SHORT"
    else:
        direction = "LONG"

    strategy = str(pick.get("strategy") or pick.get("source_system") or "").strip()
    asset_class = str(pick.get("asset_class") or pick.get("category") or "UNKNOWN").strip()

    # Prefer a stable entry/opened time; fall back to resolved_at only if needed
    ts = (
        str(pick.get("opened_at") or pick.get("entry_time") or pick.get("timestamp") or "").strip()[:19]
        or str(pick.get("resolved_at") or "").strip()[:19]
    )

    seed = f"{sym}|{direction}|{strategy}|{ts}|{asset_class}"
    return f"v1::fallback::{seed}"


# Future: add dedup helpers, collision detection, etc. here as the harmonization work expands.

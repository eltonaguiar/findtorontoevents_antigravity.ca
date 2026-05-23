#!/usr/bin/env python3
"""Rule-engine attribution adapter.

Production picks from the rule-based pipeline (`smart_picks_engine` etc.)
carry a `source_system` / `strategy` string but no AI-engine attribution.
The AI Leaderboard (`tools/ai_attribution/build_ai_leaderboard.py`) ranks
engines off each pick's `models_consulted[]` array — so rule-based picks
are currently invisible to it.

This module maps a production pick dict to the swarm-pick attribution
shape, stamping the synthetic engine `"rule_engine"`, so rule-based
strategies appear on the leaderboard alongside genuine LLM engines.

Pure, stdlib-only. Imports nothing from the rest of the repo.

## Wiring Plan (Wire-Up Rule — opt-in sidecar)
Target caller: a follow-up that, after `smart_picks_engine` emits a pick,
calls `to_attribution_record()` and appends the result through
`tools/swarm/swarm_pick_schema.append_picks()`. Until that wire-up lands
this module changes no production behaviour — it is a pure transform with
unit tests, ready to be called.

Usage:
    from tools.ai_attribution.capture_production_pick import to_attribution_record
    rec = to_attribution_record(production_pick)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_VALID_DIRECTIONS = {"LONG", "SHORT"}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_direction(raw: Any) -> str:
    """Map buy/sell/long/short (any case) -> LONG / SHORT. Default LONG."""
    s = str(raw or "").strip().upper()
    if s in ("BUY", "LONG", "L", "BID"):
        return "LONG"
    if s in ("SELL", "SHORT", "S", "ASK"):
        return "SHORT"
    return s if s in _VALID_DIRECTIONS else "LONG"


def _confidence_pct(raw: Any) -> int:
    """Map a 0.0-1.0 confidence float to an int 0-100, clamped.

    Accepts None, strings, out-of-range values without crashing.
    A value already > 1.5 is treated as already-a-percent.
    """
    if raw is None:
        return 0
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0
    if v <= 1.5:          # fraction -> percent
        v *= 100.0
    return max(0, min(100, int(round(v))))


def to_attribution_record(production_pick: dict[str, Any]) -> dict[str, Any]:
    """Map a production (rule-engine) pick to the swarm-pick attribution shape.

    Defensive — every field is optional; missing keys get safe defaults.
    The returned dict carries a single-entry `models_consulted` with
    `underlying_model="rule_engine"` so the AI Leaderboard can rank
    rule-based strategies alongside LLM engines.
    """
    pick = production_pick or {}
    direction = _normalize_direction(pick.get("direction"))
    timeframe = str(pick.get("timeframe") or "1h")
    source = str(pick.get("source_system") or pick.get("strategy") or "rule_engine")
    strategy = str(pick.get("strategy") or pick.get("source_system") or "rule-based pick")

    pick_id = pick.get("id") or f"ruleadapt-{uuid.uuid4().hex[:12]}"
    created_at = pick.get("created_at") or _utc_iso()

    return {
        "pick_id": str(pick_id),
        "created_at": str(created_at),
        "symbol": pick.get("symbol"),
        "asset_class": str(pick.get("asset_class") or "UNKNOWN").upper(),
        "direction": direction,
        "timeframe": timeframe,
        "consensus_tier": "rule_engine",
        "models_consulted": [{
            "name": source,
            "role": "strategy",
            "underlying_model": "rule_engine",
            "vote": direction,
            "confidence_0_100": _confidence_pct(pick.get("confidence")),
            "timeframe": timeframe,
            "justification_summary": strategy,
        }],
        "_source": "rule_engine_adapter",
    }

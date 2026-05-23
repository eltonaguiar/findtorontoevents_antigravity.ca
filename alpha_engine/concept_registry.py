"""Concept taxonomy registry for the audit dashboard (Cursor Phase 2).

Centralises the source-system → concept-family derivation that was previously
inlined in ``audit_trail/dashboard_generator.py``.  Every pick flowing through
``_normalize_pick`` is tagged with a ``concept_family`` via :func:`get_concept_family`.

Feature flags (read from environment at import time):
  TAXONOMY_EMISSION      default 1  — stamp concept_family on every pick.
                                       Turn off only to benchmark overhead.
  CONCEPT_SCORING_SHADOW default 0  — Phase 3 (B5): shadow scoring modifiers.
  CONCEPT_GATE_ENFORCE   default 0  — Phase 6 (B6): hard gate on concept quality.

Known concept families
----------------------
  long_term_value  : UEPS + value screener picks (pick_type=long_term_value).
  skyrocket        : penny-stock skyrocket detector.
  tradingagents    : TradingAgents LLM consensus emitter (PR #544 / #550).
  penny_stock      : generic penny category (not already tagged skyrocket).
  meme_coin        : meme scanner / meme coin scout strategies.
  mercury2         : Mercury2 and revival_mercury2 systems.
  reverse_engineer : winner/strategy reverse engineer + gainer predictor.
  standard         : default — everything not matched above.

Wiring status per concept path
-------------------------------
  long_term_value  wired    → dashboard_generator._normalize_pick (PR #548)
  skyrocket        wired    → dashboard_generator._normalize_pick (PR #548)
  tradingagents    wired    → dashboard_generator._normalize_pick (PR #548)
  penny_stock      wired    → dashboard_generator._normalize_pick (PR #548)
  meme_coin        wired    → dashboard_generator._normalize_pick (PR #548)
  mercury2         wired    → dashboard_generator._normalize_pick (PR #548)
  reverse_engineer wired    → dashboard_generator._normalize_pick (PR #548)
  standard         wired    → dashboard_generator._normalize_pick (PR #548)

Future wiring targets (opt-in until their PRs land):
  CONCEPT_SCORING_SHADOW → alpha_engine/elite_scorer.py (B5 / PR TBD)
  CONCEPT_GATE_ENFORCE   → audit_trail/quality_gates.py (B6 / PR TBD)
"""

from __future__ import annotations

import os

__all__ = [
    "TAXONOMY_EMISSION",
    "CONCEPT_SCORING_SHADOW",
    "CONCEPT_GATE_ENFORCE",
    "CONCEPT_FAMILIES",
    "WIRING_STATUS",
    "get_concept_family",
]

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

TAXONOMY_EMISSION: int = int(os.getenv("TAXONOMY_EMISSION", "1"))
CONCEPT_SCORING_SHADOW: int = int(os.getenv("CONCEPT_SCORING_SHADOW", "0"))
CONCEPT_GATE_ENFORCE: int = int(os.getenv("CONCEPT_GATE_ENFORCE", "0"))

# ---------------------------------------------------------------------------
# Source-system registries
# ---------------------------------------------------------------------------

# Mercury2 source-system identifiers — explicit list per Codebuff review
# (no glob matching to avoid accidental hits on unrelated systems).
MERCURY2_SOURCES: frozenset[str] = frozenset({
    "mercury2",
    "mercury2_fast",
    "revival_mercury2",
    "ai_challenge_mercury",
})

# Reverse-engineer strategy/source names.  Strict equality match.
REVERSE_ENGINEER_STRATEGIES: frozenset[str] = frozenset({
    "winner_reverse_engineer",
    "strategy_reverse_engineer",
    "gainer_predictor",
    "gainer_predictor_score",
})

# ---------------------------------------------------------------------------
# Authoritative concept family list
# ---------------------------------------------------------------------------

CONCEPT_FAMILIES: frozenset[str] = frozenset({
    "long_term_value",
    "skyrocket",
    "tradingagents",
    "penny_stock",
    "meme_coin",
    "mercury2",
    "reverse_engineer",
    "standard",
})

# ---------------------------------------------------------------------------
# Wiring status declaration (concept-family level, not source-system level)
# ---------------------------------------------------------------------------

WIRING_STATUS: dict[str, dict] = {
    "long_term_value": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "skyrocket": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "tradingagents": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "penny_stock": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "meme_coin": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "mercury2": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "reverse_engineer": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    "standard": {
        "status": "wired",
        "caller": "audit_trail/dashboard_generator.py::assign_concept_fields",
        "wiring_pr": "#548",
    },
    # Future opt-in paths (not yet wired):
    "concept_scoring_shadow": {
        "status": "opt-in",
        "caller": "alpha_engine/elite_scorer.py (target)",
        "wiring_pr": "B5 PR (TBD)",
    },
    "concept_gate_enforce": {
        "status": "opt-in",
        "caller": "audit_trail/quality_gates.py (target)",
        "wiring_pr": "B6 PR (TBD)",
    },
}


# ---------------------------------------------------------------------------
# Core derivation function
# ---------------------------------------------------------------------------

def get_concept_family(pick: dict) -> str:
    """Derive the concept family for a pick dict.

    Pure function — no I/O, no global mutation.  Returns one of the strings
    in :data:`CONCEPT_FAMILIES`.  Always returns a non-empty string.

    Derivation order (most specific first):
      1. long_term_value  — pick_type field OR ueps_/value_screener source prefix
      2. skyrocket        — explicit strategy or source_system match
      3. tradingagents    — tradingagents consensus strategy/source
      4. penny_stock      — category=penny
      5. meme_coin        — "meme" in strategy or source or category
      6. mercury2         — source_system in MERCURY2_SOURCES
      7. reverse_engineer — strategy in REVERSE_ENGINEER_STRATEGIES or source prefix
      8. standard         — default fallback
    """
    if not isinstance(pick, dict):
        return "standard"

    strategy = str(pick.get("strategy") or "").strip()
    strategy_lc = strategy.lower()
    source_system = str(pick.get("source_system") or "").strip()
    source_lc = source_system.lower()
    category = str(pick.get("category") or "").strip().lower()
    pick_type = str(pick.get("pick_type") or "").strip().lower()

    # 2026-05-08: also match bare "ueps" source_system (was prefix-only "ueps_"
    # which dropped 38 live UEPS picks into concept_family="standard" instead
    # of "long_term_value", breaking the LONG_TERM filter on /audit).
    if (
        pick_type == "long_term_value"
        or source_lc.startswith(("value_screener", "ueps_"))
        or source_lc == "ueps"
    ):
        return "long_term_value"
    if strategy == "skyrocket_detector" or source_system == "skyrocket_detector":
        return "skyrocket"
    if strategy == "tradingagents_consensus" or source_system == "tradingagents":
        return "tradingagents"
    if category == "penny":
        return "penny_stock"
    if "meme" in strategy_lc or "meme" in source_lc or category == "meme":
        return "meme_coin"
    if source_system in MERCURY2_SOURCES:
        return "mercury2"
    if strategy in REVERSE_ENGINEER_STRATEGIES or source_lc.startswith("winner_reverse"):
        return "reverse_engineer"
    return "standard"


def validate_source_concept_coverage(source_name: str) -> str:
    """Return the concept family a synthetic pick from *source_name* would receive.

    Used by the CI gate in ``tests/test_concept_registry.py`` to assert that
    every JSON_PICK_SOURCES entry produces a non-empty concept family (i.e. no
    source falls through to None/empty, which would break the dashboard).
    """
    synthetic_pick = {"source_system": source_name, "strategy": source_name}
    return get_concept_family(synthetic_pick)

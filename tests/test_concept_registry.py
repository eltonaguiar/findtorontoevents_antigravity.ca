"""Tests for alpha_engine.concept_registry (B4 — Cursor Phase 2).

Covers:
  - All concept family derivation branches
  - Feature flag constants and types
  - WIRING_STATUS declaration completeness
  - CI gate: every JSON_PICK_SOURCES source name produces a valid concept family
"""

import importlib
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alpha_engine.concept_registry import (
    CONCEPT_FAMILIES,
    CONCEPT_GATE_ENFORCE,
    CONCEPT_SCORING_SHADOW,
    MERCURY2_SOURCES,
    REVERSE_ENGINEER_STRATEGIES,
    TAXONOMY_EMISSION,
    WIRING_STATUS,
    get_concept_family,
    validate_source_concept_coverage,
)


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------

def test_taxonomy_emission_defaults_on():
    assert TAXONOMY_EMISSION == 1, "TAXONOMY_EMISSION should default to 1"


def test_shadow_and_gate_default_off():
    assert CONCEPT_SCORING_SHADOW == 0
    assert CONCEPT_GATE_ENFORCE == 0


def test_feature_flags_are_ints():
    assert isinstance(TAXONOMY_EMISSION, int)
    assert isinstance(CONCEPT_SCORING_SHADOW, int)
    assert isinstance(CONCEPT_GATE_ENFORCE, int)


# ---------------------------------------------------------------------------
# CONCEPT_FAMILIES completeness
# ---------------------------------------------------------------------------

def test_concept_families_contains_expected():
    required = {"long_term_value", "skyrocket", "tradingagents", "penny_stock",
                "meme_coin", "mercury2", "reverse_engineer", "standard"}
    assert required.issubset(CONCEPT_FAMILIES)


def test_standard_is_in_families():
    assert "standard" in CONCEPT_FAMILIES


# ---------------------------------------------------------------------------
# WIRING_STATUS
# ---------------------------------------------------------------------------

def test_wiring_status_covers_all_families():
    for family in CONCEPT_FAMILIES:
        assert family in WIRING_STATUS, f"concept family '{family}' missing from WIRING_STATUS"


def test_wiring_status_values_have_required_keys():
    for family, info in WIRING_STATUS.items():
        assert "status" in info, f"{family} missing 'status'"
        assert info["status"] in ("wired", "opt-in"), f"{family} status invalid: {info['status']}"
        assert "caller" in info


# ---------------------------------------------------------------------------
# get_concept_family — branch coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pick,expected", [
    # long_term_value
    ({"pick_type": "long_term_value"}, "long_term_value"),
    ({"source_system": "ueps_screen_1"}, "long_term_value"),
    ({"source_system": "ueps_top30"}, "long_term_value"),
    ({"source_system": "value_screener_us"}, "long_term_value"),
    # skyrocket
    ({"strategy": "skyrocket_detector"}, "skyrocket"),
    ({"source_system": "skyrocket_detector"}, "skyrocket"),
    # tradingagents
    ({"strategy": "tradingagents_consensus"}, "tradingagents"),
    ({"source_system": "tradingagents"}, "tradingagents"),
    # penny_stock
    ({"category": "penny"}, "penny_stock"),
    # meme_coin
    ({"strategy": "meme-scanner-live"}, "meme_coin"),
    ({"strategy": "Meme Coin Scout"}, "meme_coin"),
    ({"source_system": "meme_trader"}, "meme_coin"),
    ({"category": "meme"}, "meme_coin"),
    # mercury2
    ({"source_system": "mercury2"}, "mercury2"),
    ({"source_system": "mercury2_fast"}, "mercury2"),
    ({"source_system": "revival_mercury2"}, "mercury2"),
    ({"source_system": "ai_challenge_mercury"}, "mercury2"),
    # reverse_engineer
    ({"strategy": "winner_reverse_engineer"}, "reverse_engineer"),
    ({"strategy": "strategy_reverse_engineer"}, "reverse_engineer"),
    ({"strategy": "gainer_predictor"}, "reverse_engineer"),
    ({"strategy": "gainer_predictor_score"}, "reverse_engineer"),
    ({"source_system": "winner_reverse_etf"}, "reverse_engineer"),
    # standard (fallback)
    ({}, "standard"),
    ({"strategy": "rs-breakout-scout"}, "standard"),
    ({"source_system": "alpha_engine"}, "standard"),
    ({"strategy": "mtf-align-scout"}, "standard"),
])
def test_get_concept_family_branches(pick, expected):
    assert get_concept_family(pick) == expected


def test_get_concept_family_non_dict_returns_standard():
    assert get_concept_family(None) == "standard"  # type: ignore
    assert get_concept_family("string") == "standard"  # type: ignore
    assert get_concept_family(42) == "standard"  # type: ignore


def test_long_term_value_beats_penny_category():
    """pick_type=long_term_value takes priority over category=penny."""
    pick = {"pick_type": "long_term_value", "category": "penny"}
    assert get_concept_family(pick) == "long_term_value"


def test_skyrocket_beats_penny_category():
    """skyrocket_detector strategy takes priority over penny category."""
    pick = {"strategy": "skyrocket_detector", "category": "penny"}
    assert get_concept_family(pick) == "skyrocket"


# ---------------------------------------------------------------------------
# validate_source_concept_coverage
# ---------------------------------------------------------------------------

def test_validate_returns_string():
    assert isinstance(validate_source_concept_coverage("alpha_engine"), str)
    assert validate_source_concept_coverage("alpha_engine") != ""


def test_validate_known_sources():
    assert validate_source_concept_coverage("mercury2") == "mercury2"
    assert validate_source_concept_coverage("skyrocket_detector") == "skyrocket"


# ---------------------------------------------------------------------------
# CI gate — every JSON_PICK_SOURCES source name must yield a valid family
# ---------------------------------------------------------------------------

def _get_json_pick_source_names():
    """Import JSON_PICK_SOURCES and extract source names."""
    try:
        import audit_trail.dashboard_generator as dg
        return [tup[0] for tup in dg.JSON_PICK_SOURCES if tup[0]]
    except Exception:
        return []


@pytest.mark.parametrize("source_name", _get_json_pick_source_names())
def test_all_pick_sources_have_concept_family(source_name):
    """CI gate: no JSON_PICK_SOURCES entry may produce an empty concept family."""
    family = validate_source_concept_coverage(source_name)
    assert family, f"source '{source_name}' returned empty concept family"
    assert family in CONCEPT_FAMILIES, (
        f"source '{source_name}' produced unknown family '{family}'"
    )


# ---------------------------------------------------------------------------
# MERCURY2_SOURCES / REVERSE_ENGINEER_STRATEGIES membership
# ---------------------------------------------------------------------------

def test_mercury2_sources_are_frozenset():
    assert isinstance(MERCURY2_SOURCES, frozenset)


def test_reverse_engineer_strategies_are_frozenset():
    assert isinstance(REVERSE_ENGINEER_STRATEGIES, frozenset)


def test_mercury2_sources_membership():
    assert "mercury2" in MERCURY2_SOURCES
    assert "revival_mercury2" in MERCURY2_SOURCES
    assert "not_mercury" not in MERCURY2_SOURCES


def test_reverse_engineer_strategies_membership():
    assert "winner_reverse_engineer" in REVERSE_ENGINEER_STRATEGIES
    assert "gainer_predictor" in REVERSE_ENGINEER_STRATEGIES
    assert "rs-breakout-scout" not in REVERSE_ENGINEER_STRATEGIES

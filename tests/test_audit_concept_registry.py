"""Unit tests for the concept-family taxonomy used by /audit pick normalization.

Covers:
  * get_concept_family — strategy/source mappings (UEPS, mercury2, skyrocket,
    meme, tradingagents, reverse_engineer, default standard)
  * assign_concept_fields — idempotency on already-tagged picks
  * assign_concept_fields — upgrades the "standard" placeholder to the real
    concept_family (regression for commit 97cfb9efccf — was blocking 16 UEPS
    picks from being tagged long_term_value).
"""

from __future__ import annotations

import pytest

from alpha_engine.concept_registry import get_concept_family
from audit_trail.dashboard_generator import assign_concept_fields


def test_get_concept_family_long_term_value_via_pick_type():
    assert get_concept_family({"pick_type": "long_term_value"}) == "long_term_value"


def test_get_concept_family_long_term_value_via_ueps_source():
    assert get_concept_family({"source_system": "ueps_value", "strategy": "x"}) == "long_term_value"
    assert get_concept_family({"source_system": "value_screener_a", "strategy": "x"}) == "long_term_value"


def test_get_concept_family_mercury2():
    for src in ("mercury2", "mercury2_fast", "revival_mercury2", "ai_challenge_mercury"):
        assert get_concept_family({"source_system": src}) == "mercury2", \
            f"expected mercury2 for source {src!r}"


def test_get_concept_family_tradingagents():
    assert get_concept_family({"strategy": "tradingagents_consensus"}) == "tradingagents"
    assert get_concept_family({"source_system": "tradingagents"}) == "tradingagents"


def test_get_concept_family_skyrocket():
    assert get_concept_family({"strategy": "skyrocket_detector"}) == "skyrocket"
    assert get_concept_family({"source_system": "skyrocket_detector"}) == "skyrocket"


def test_get_concept_family_penny_stock():
    assert get_concept_family({"category": "penny"}) == "penny_stock"


def test_get_concept_family_meme_coin():
    assert get_concept_family({"strategy": "meme_runner_v2"}) == "meme_coin"
    assert get_concept_family({"category": "meme"}) == "meme_coin"


def test_get_concept_family_reverse_engineer():
    for strat in (
        "winner_reverse_engineer",
        "strategy_reverse_engineer",
        "gainer_predictor",
        "gainer_predictor_score",
    ):
        assert get_concept_family({"strategy": strat}) == "reverse_engineer", \
            f"expected reverse_engineer for strategy {strat!r}"


def test_get_concept_family_default_standard():
    assert get_concept_family({"source_system": "aggregated_picks", "strategy": "ema_cross"}) == "standard"
    assert get_concept_family({}) == "standard"


def test_assign_concept_fields_stamps_family_and_source():
    pick = {"strategy": "skyrocket_detector", "source_system": "skyrocket_detector"}
    out = assign_concept_fields(pick)
    assert out is pick  # mutates in place + returns same dict
    assert pick["concept_family"] == "skyrocket"
    assert pick["concept_source"] == "skyrocket_detector"


def test_assign_concept_fields_idempotent_for_real_family():
    """Running twice on a non-'standard' tagged pick must not re-derive."""
    pick = {
        "strategy": "mercury2",
        "source_system": "mercury2",
        "concept_family": "mercury2",
        "concept_source": "mercury2",
    }
    assign_concept_fields(pick)
    snapshot = dict(pick)
    assign_concept_fields(pick)
    assert pick == snapshot, "second assign_concept_fields call mutated the pick"


def test_assign_concept_fields_upgrades_standard_placeholder():
    """Regression for 97cfb9efccf — the inline _normalize_pick can stamp
    concept_family='standard' before pick_type is fully populated; the registry
    must be allowed to upgrade that placeholder to the real concept.
    """
    pick = {
        "pick_type": "long_term_value",
        "source_system": "ueps_value",
        "strategy": "ueps_value_screener",
        "concept_family": "standard",  # the placeholder we want upgraded
    }
    assign_concept_fields(pick)
    assert pick["concept_family"] == "long_term_value", \
        "standard placeholder should be upgraded to long_term_value"
    assert pick["concept_source"] == "ueps_value_screener"


def test_assign_concept_fields_preserves_explicit_non_standard_tag():
    """If an upstream emitter explicitly tagged a pick with a non-'standard'
    concept_family, trust the upstream tag — don't re-derive.
    """
    pick = {
        "strategy": "ema_cross",
        "source_system": "aggregated_picks",
        "concept_family": "meme_coin",  # explicit override from upstream
    }
    assign_concept_fields(pick)
    assert pick["concept_family"] == "meme_coin", "explicit upstream tag was overwritten"


def test_assign_concept_fields_handles_non_dict():
    """Non-dict input must not raise — should return the input unchanged."""
    assert assign_concept_fields(None) is None  # type: ignore[arg-type]
    assert assign_concept_fields("not a pick") == "not a pick"  # type: ignore[arg-type]

"""Tests for the concept taxonomy stamping helper (Phase 1 — PR #549).

Background: per Cursor's "Audit Concepts Integration" plan, every pick
flowing through ``audit_trail.dashboard_generator._normalize_pick`` should
carry a ``concept_family`` + ``concept_source`` tag. These tests pin the
contract so future schema changes can't silently de-tag picks.

Concept families covered:
  - long_term_value, skyrocket, tradingagents, penny_stock,
    meme_coin, mercury2, reverse_engineer, standard

Hard rules:
  1. Default ``standard`` for any pick that doesn't match a registry rule.
  2. Already-tagged picks (upstream override) are preserved untouched.
  3. The function mutates in place AND returns the dict (chainable).
  4. Order matters: pick_type=long_term_value wins over a later
     category=meme override (specificity).
"""
from __future__ import annotations

import pytest

from audit_trail.dashboard_generator import assign_concept_fields


# ────────────────────────────────────────────────────────────────────────
# Concept derivation
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "pick,expected_family",
    [
        # long_term_value (UEPS)
        ({"pick_type": "long_term_value"}, "long_term_value"),
        ({"source_system": "value_screener"}, "long_term_value"),
        ({"source_system": "ueps_long"}, "long_term_value"),
        ({"source_system": "UEPS_short"}, "long_term_value"),  # case-insensitive
        # skyrocket (penny detector)
        ({"strategy": "skyrocket_detector"}, "skyrocket"),
        ({"source_system": "skyrocket_detector"}, "skyrocket"),
        # skyrocket should win over the later penny_stock rule even when both apply
        ({"strategy": "skyrocket_detector", "category": "penny"}, "skyrocket"),
        # tradingagents (PR #544 emitter)
        ({"strategy": "tradingagents_consensus"}, "tradingagents"),
        ({"source_system": "tradingagents"}, "tradingagents"),
        # penny_stock (any category=penny that isn't already skyrocket)
        ({"category": "penny", "strategy": "manual_penny_pick"}, "penny_stock"),
        # meme_coin
        ({"strategy": "meme-scanner-live"}, "meme_coin"),
        ({"strategy": "Meme Coin Scout"}, "meme_coin"),
        ({"source_system": "meme_scanner"}, "meme_coin"),
        ({"category": "meme", "strategy": "x"}, "meme_coin"),
        # mercury2 — explicit list, no glob
        ({"source_system": "mercury2"}, "mercury2"),
        ({"source_system": "mercury2_fast"}, "mercury2"),
        ({"source_system": "revival_mercury2"}, "mercury2"),
        ({"source_system": "ai_challenge_mercury"}, "mercury2"),
        # reverse_engineer
        ({"strategy": "winner_reverse_engineer"}, "reverse_engineer"),
        ({"strategy": "strategy_reverse_engineer"}, "reverse_engineer"),
        ({"strategy": "gainer_predictor"}, "reverse_engineer"),
        ({"source_system": "winner_reverse_other"}, "reverse_engineer"),
        # standard (default)
        ({"strategy": "rs-breakout-scout"}, "standard"),
        ({"strategy": "luxalgo_confluence"}, "standard"),
        ({}, "standard"),
        ({"strategy": None, "source_system": None}, "standard"),
    ],
)
def test_concept_family_derivation(pick, expected_family):
    out = assign_concept_fields(dict(pick))  # copy so test cases stay independent
    assert out["concept_family"] == expected_family


def test_concept_source_attribution():
    """concept_source = strategy if present, else source_system."""
    p = assign_concept_fields({"strategy": "skyrocket_detector", "source_system": "x"})
    assert p["concept_source"] == "skyrocket_detector"

    p = assign_concept_fields({"source_system": "tradingagents"})
    assert p["concept_source"] == "tradingagents"

    p = assign_concept_fields({})
    assert p["concept_source"] == ""


# ────────────────────────────────────────────────────────────────────────
# Backward-compatibility / no-mutation contract
# ────────────────────────────────────────────────────────────────────────

def test_already_tagged_picks_preserved():
    """An upstream emitter that already set concept_family must not be
    overwritten — gives downstream producers a way to assert custom tags."""
    p = assign_concept_fields({"concept_family": "custom_tag_xyz", "strategy": "skyrocket_detector"})
    assert p["concept_family"] == "custom_tag_xyz"
    # concept_source is filled in if missing, even when family is preserved
    assert p["concept_source"] == "skyrocket_detector"


def test_already_tagged_with_source_preserved():
    p = assign_concept_fields({
        "concept_family": "custom",
        "concept_source": "upstream_label",
        "strategy": "skyrocket_detector",
    })
    assert p["concept_family"] == "custom"
    assert p["concept_source"] == "upstream_label"


def test_helper_mutates_in_place_and_returns_dict():
    p = {"strategy": "skyrocket_detector"}
    out = assign_concept_fields(p)
    assert out is p  # same object, mutated in place
    assert "concept_family" in p


def test_non_dict_input_returns_unchanged():
    """Defensive guard — never crash on a malformed pick."""
    assert assign_concept_fields(None) is None  # type: ignore[arg-type]
    assert assign_concept_fields("not a dict") == "not a dict"  # type: ignore[arg-type]


# ────────────────────────────────────────────────────────────────────────
# Specificity ordering
# ────────────────────────────────────────────────────────────────────────

def test_long_term_value_wins_over_meme_when_both_apply():
    """A pick with pick_type=long_term_value AND a meme strategy name
    classifies as long_term_value — pick_type is more specific."""
    p = assign_concept_fields({
        "pick_type": "long_term_value",
        "strategy": "meme-scanner-live",
    })
    assert p["concept_family"] == "long_term_value"


def test_skyrocket_wins_over_meme_when_strategy_is_skyrocket():
    """skyrocket detector takes precedence over meme even if the symbol's
    category contains 'meme' — the strategy name is the source of truth."""
    p = assign_concept_fields({
        "strategy": "skyrocket_detector",
        "source_system": "skyrocket_detector",
        "category": "meme",
    })
    assert p["concept_family"] == "skyrocket"


# ────────────────────────────────────────────────────────────────────────
# Integration with _normalize_pick
# ────────────────────────────────────────────────────────────────────────

def test_normalize_pick_stamps_concept_fields():
    """Confidence check that _normalize_pick (the actual call site) does
    invoke assign_concept_fields. If a future refactor removes the call,
    this test fails loudly."""
    from audit_trail.dashboard_generator import _normalize_pick

    raw = {
        "symbol": "NVDA",
        "strategy": "skyrocket_detector",
        "asset_class": "EQUITY",
        "category": "penny",
        "direction": "LONG",
        "entry_price": 1.50,
        "take_profit": 2.10,
        "stop_loss": 1.275,
        "score": 75,
    }
    normalized = _normalize_pick(raw, source_system="skyrocket_detector", status="OPEN")
    assert normalized.get("concept_family") == "skyrocket"
    assert normalized.get("concept_source") == "skyrocket_detector"


def test_normalize_pick_default_standard_for_generic_pick():
    from audit_trail.dashboard_generator import _normalize_pick

    raw = {
        "symbol": "BTCUSDT",
        "strategy": "luxalgo_confluence",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "entry_price": 60000,
        "take_profit": 61000,
        "stop_loss": 59500,
    }
    normalized = _normalize_pick(raw, source_system="luxalgo_filters", status="OPEN")
    assert normalized.get("concept_family") == "standard"

"""Tests for strategy-family attribution (operator-approved, additive)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.strategy_family import family_of, is_claim_family, dump_mapping  # noqa: E402


@pytest.mark.parametrize("name,expected", [
    ("volume_spike_breakout", "breakout"),
    ("bollinger_squeeze", "breakout"),
    ("macd_rsi_confluence", "momentum"),        # RSI must NOT make this mean_reversion
    ("stochrsi_macd_combo", "momentum"),        # same trap
    ("rsi_bounce", "mean_reversion"),
    ("forex_rsi2_mean_reversion", "mean_reversion"),
    ("B_flip_PriceRocMeanReversion", "mean_reversion"),  # 'roc' must not win over 'reversion'
    ("commodity_rsi_divergence", "mean_reversion"),
    ("forex_zscore_200d_fade", "mean_reversion"),
    ("etf_faber_tactical", "trend_following"),
    ("fx_cot_extremes", "positioning"),
    ("prediction_market_consensus", "prediction_market"),
    ("clone_hl_copy_lb_None", "copy_trade"),
    ("regime_accumulation", "regime"),
])
def test_family_mapping(name, expected):
    fam, prov = family_of(name, None)
    assert fam == expected
    assert prov == "mapped"


def test_ordering_bug_regression():
    """The first draft mapped this to momentum via 'roc'. Pin the correct answer."""
    fam, _ = family_of("B_flip_PriceRocMeanReversion", None)
    assert fam == "mean_reversion", "rule order regressed: reversion must precede momentum"


def test_unknown_is_declared_not_guessed():
    fam, prov = family_of("totally_made_up_thing", "also_made_up")
    assert fam == "unknown"
    assert prov == "unmapped"


def test_strategy_wins_over_system_name():
    """A scanner name must not override the strategy's own family."""
    fam, _ = family_of("volume_spike_breakout", "ml_ensemble_scanner")
    assert fam == "breakout", "system name should only be a fallback"


def test_system_name_is_used_as_fallback():
    fam, prov = family_of(None, "breakout_b_ml")
    assert fam == "breakout"
    assert prov == "mapped"


def test_claim_families_are_exactly_three():
    assert is_claim_family("momentum")
    assert is_claim_family("breakout")
    assert is_claim_family("trend_following")
    assert not is_claim_family("mean_reversion")


def test_mapping_dump_is_labelled_as_judgement():
    d = dump_mapping(["volume_spike_breakout"])
    assert d["status"] == "JUDGEMENT_NOT_MEASUREMENT"
    assert d["ordered_rules"], "rule table must be committed for review"
    assert d["resolved_names"][0]["family"] == "breakout"


def test_resolver_emits_field_additively():
    """_extract_pick_fields must ADD the key without disturbing existing ones."""
    from audit_trail.universal_pick_resolver import _extract_pick_fields

    req = {"id", "symbol", "direction", "entry_price", "take_profit", "stop_loss",
           "timestamp", "strategy", "source_system", "asset_class"}
    p = _extract_pick_fields({"symbol": "X", "strategy": "rsi_bounce"}, "s")
    assert not (req - set(p)), f"pre-existing keys lost: {req - set(p)}"
    assert p["strategy_family"] == "mean_reversion"
    assert p["strategy_family_provenance"] == "mapped"

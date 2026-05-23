"""Tests for per_class_position_caps sidecar module (PR #730 reviewer follow-up)."""
import os

import pytest

from alpha_engine.per_class_position_caps import (
    PER_CLASS_MAX_CONCURRENT,
    PER_CLASS_POSITION_PCT,
    UNIVERSAL_MAX_CONCURRENT,
    UNIVERSAL_POSITION_PCT,
    count_class_active,
    get_max_concurrent,
    get_max_position_pct,
    is_concurrent_cap_breached,
)


def test_position_pct_per_class_returns_calibrated_value():
    """Each defined class returns its calibrated position size cap."""
    assert get_max_position_pct("EQUITY") == 0.08, "EQUITY should be uplifted (T2 candidate)"
    assert get_max_position_pct("COMMODITY") == 0.07, "COMMODITY meets T2 PF — uplift"
    assert get_max_position_pct("CRYPTO") == 0.05
    assert get_max_position_pct("MEME") == 0.02, "MEME high-vol — downsized"
    assert get_max_position_pct("FOREX") == 0.03, "FOREX sub-floor — downsized"
    assert get_max_position_pct("BOND") == 0.04
    assert get_max_position_pct("ETF") == 0.05
    assert get_max_position_pct("FUTURES") == 0.03


def test_position_pct_falls_back_to_universal_for_unknown():
    assert get_max_position_pct("UNKNOWN_CLASS") == UNIVERSAL_POSITION_PCT
    assert get_max_position_pct(None) == UNIVERSAL_POSITION_PCT
    assert get_max_position_pct("") == UNIVERSAL_POSITION_PCT


def test_position_pct_is_case_insensitive():
    assert get_max_position_pct("equity") == 0.08
    assert get_max_position_pct("Forex") == 0.03


def test_position_pct_disabled_env_returns_universal(monkeypatch):
    """PER_CLASS_POSITION_PCT_DISABLED=1 reverts to universal."""
    monkeypatch.setenv("PER_CLASS_POSITION_PCT_DISABLED", "1")
    assert get_max_position_pct("EQUITY") == UNIVERSAL_POSITION_PCT
    assert get_max_position_pct("MEME") == UNIVERSAL_POSITION_PCT


def test_max_concurrent_per_class_returns_calibrated_value():
    assert get_max_concurrent("CRYPTO") == 15
    assert get_max_concurrent("BOND") == 5, "BOND 336h hold — small concurrent cap"
    assert get_max_concurrent("MEME") == 5
    assert get_max_concurrent("EQUITY") == 8


def test_max_concurrent_falls_back_to_universal_for_unknown():
    assert get_max_concurrent("UNKNOWN_CLASS") == UNIVERSAL_MAX_CONCURRENT
    assert get_max_concurrent(None) == UNIVERSAL_MAX_CONCURRENT


def test_max_concurrent_disabled_env_returns_universal(monkeypatch):
    monkeypatch.setenv("PER_CLASS_CONCURRENT_DISABLED", "1")
    assert get_max_concurrent("CRYPTO") == UNIVERSAL_MAX_CONCURRENT
    assert get_max_concurrent("BOND") == UNIVERSAL_MAX_CONCURRENT


def test_count_class_active_handles_mixed_picks():
    picks = [
        {"asset_class": "CRYPTO", "symbol": "BTCUSDT"},
        {"asset_class": "crypto", "symbol": "ETHUSDT"},  # case insensitive
        {"asset_class": "FOREX", "symbol": "EURUSD=X"},
        {"category": "BOND", "symbol": "TLT"},  # 'category' fallback field
        {"asset_class": "EQUITY", "symbol": "AAPL"},
    ]
    assert count_class_active(picks, "CRYPTO") == 2
    assert count_class_active(picks, "FOREX") == 1
    assert count_class_active(picks, "BOND") == 1
    assert count_class_active(picks, "EQUITY") == 1
    assert count_class_active(picks, "MEME") == 0


def test_is_concurrent_cap_breached_returns_true_at_cap():
    """Reject NEW pick when current count == cap."""
    bond_picks = [{"asset_class": "BOND"}] * 5  # BOND cap is 5
    assert is_concurrent_cap_breached(bond_picks, "BOND") is True


def test_is_concurrent_cap_breached_returns_false_below_cap():
    bond_picks = [{"asset_class": "BOND"}] * 4
    assert is_concurrent_cap_breached(bond_picks, "BOND") is False


def test_is_concurrent_cap_breached_unknown_class_uses_universal():
    """Unknown class falls back to UNIVERSAL_MAX_CONCURRENT (30)."""
    # 100 picks of WEIRD class > universal cap 30 → breached
    picks = [{"asset_class": "WEIRD"}] * 100
    assert is_concurrent_cap_breached(picks, "WEIRD") is True
    # 25 picks < universal cap 30 → not breached
    picks_under = [{"asset_class": "WEIRD"}] * 25
    assert is_concurrent_cap_breached(picks_under, "WEIRD") is False


def test_is_concurrent_cap_breached_empty_class_returns_false():
    """Empty/None class returns False — defer to upstream rather than enforcing."""
    picks = [{"asset_class": "ANYTHING"}] * 100
    assert is_concurrent_cap_breached(picks, None) is False
    assert is_concurrent_cap_breached(picks, "") is False


def test_per_class_maps_have_no_unexpected_classes():
    """Lock the schema — both maps contain the same 8 documented classes."""
    expected = {"CRYPTO", "MEME", "EQUITY", "ETF", "COMMODITY", "FUTURES", "FOREX", "BOND"}
    assert set(PER_CLASS_POSITION_PCT.keys()) == expected
    assert set(PER_CLASS_MAX_CONCURRENT.keys()) == expected


def test_position_pcts_are_within_safe_bounds():
    """No class should ever exceed 10% per position (sanity)."""
    for ac, pct in PER_CLASS_POSITION_PCT.items():
        assert 0.01 <= pct <= 0.10, f"{ac} pct {pct} outside safe bounds [0.01, 0.10]"


def test_concurrent_caps_are_within_safe_bounds():
    """No per-class cap should exceed universal max."""
    for ac, n in PER_CLASS_MAX_CONCURRENT.items():
        assert 1 <= n <= UNIVERSAL_MAX_CONCURRENT, (
            f"{ac} cap {n} outside [1, {UNIVERSAL_MAX_CONCURRENT}]"
        )

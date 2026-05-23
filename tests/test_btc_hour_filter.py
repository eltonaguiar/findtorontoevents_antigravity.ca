"""Tests for alpha_engine.btc_hour_filter — BTC UTC hour death-zone filter.

Memory citation: `feedback_clean_data_symbol_wr` + `feedback_quick_guess_horizons`.
08-09 UTC = death zone (-12), 22 UTC = sweet spot (+5), all others neutral (0).
"""
from __future__ import annotations

import pytest

from alpha_engine.btc_hour_filter import (
    BTC_HOUR_PENALTIES,
    btc_hour_score_adjustment,
)


def test_btc_death_zone_hour_08_utc():
    pick = {"symbol": "BTCUSDT", "created_at": "2026-05-15T08:15:00Z"}
    assert btc_hour_score_adjustment(pick) == -12


def test_btc_death_zone_hour_09_utc():
    pick = {"symbol": "BTCUSDT", "created_at": "2026-05-15T09:45:30Z"}
    assert btc_hour_score_adjustment(pick) == -12


def test_btc_sweet_spot_hour_22_utc():
    pick = {"symbol": "BTCUSDT", "created_at": "2026-05-15T22:05:00Z"}
    assert btc_hour_score_adjustment(pick) == 5


def test_btc_neutral_hour_12_utc():
    pick = {"symbol": "BTCUSDT", "created_at": "2026-05-15T12:00:00Z"}
    assert btc_hour_score_adjustment(pick) == 0


def test_non_btc_symbol_unaffected_in_death_zone():
    pick = {"symbol": "ETHUSDT", "created_at": "2026-05-15T08:15:00Z"}
    assert btc_hour_score_adjustment(pick) == 0


def test_unparseable_timestamp_fail_open():
    pick = {"symbol": "BTCUSDT", "created_at": "not-a-date"}
    assert btc_hour_score_adjustment(pick) == 0


def test_btc_with_binance_prefix_still_matches():
    pick = {"symbol": "BINANCE:BTCUSDT", "created_at": "2026-05-15T08:30:00Z"}
    assert btc_hour_score_adjustment(pick) == -12


def test_btc_with_binance_prefix_sweet_spot():
    pick = {"symbol": "BINANCE:BTCUSDT", "created_at": "2026-05-15T22:30:00Z"}
    assert btc_hour_score_adjustment(pick) == 5


def test_signal_time_fallback_when_created_at_missing():
    pick = {"symbol": "BTCUSDT", "signal_time": "2026-05-15T08:00:00Z"}
    assert btc_hour_score_adjustment(pick) == -12


def test_epoch_float_timestamp_supported():
    # 2026-05-15T08:30:00Z → 1778834400.0
    pick = {"symbol": "BTCUSDT", "created_at": 1778834400.0}
    assert btc_hour_score_adjustment(pick) == -12


def test_missing_symbol_returns_zero():
    pick = {"created_at": "2026-05-15T08:15:00Z"}
    assert btc_hour_score_adjustment(pick) == 0


def test_non_dict_input_returns_zero():
    assert btc_hour_score_adjustment(None) == 0  # type: ignore[arg-type]
    assert btc_hour_score_adjustment("not a pick") == 0  # type: ignore[arg-type]


def test_penalty_table_shape():
    assert BTC_HOUR_PENALTIES[8] == -12
    assert BTC_HOUR_PENALTIES[9] == -12
    assert BTC_HOUR_PENALTIES[22] == 5
    assert 12 not in BTC_HOUR_PENALTIES


def test_score_booster_delegates_btc_death_zone(monkeypatch):
    # M-070 wiring: _apply_crypto_hour_filter delegates BTCUSDT hour 8 to btc_hour_filter (-12).
    monkeypatch.setenv("CRYPTO_HOUR_FILTER", "1")
    from alpha_engine.score_booster import _apply_crypto_hour_filter
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "created_at": "2026-05-17T08:30:00Z",
    }
    adj = _apply_crypto_hour_filter(pick)
    # btc_hour_filter returns -12 for hour 8; inline would return -20. Confirm module wins.
    assert adj == -12, f"expected -12 from btc_hour_filter delegation, got {adj}"


def test_score_booster_non_btc_crypto_uses_inline(monkeypatch):
    # Non-BTC CRYPTO (e.g. ETHUSDT) still uses the inline -20 penalty for hour 8.
    monkeypatch.setenv("CRYPTO_HOUR_FILTER", "1")
    from alpha_engine.score_booster import _apply_crypto_hour_filter
    pick = {
        "asset_class": "CRYPTO",
        "symbol": "ETHUSDT",
        "created_at": "2026-05-17T08:30:00Z",
    }
    adj = _apply_crypto_hour_filter(pick)
    assert adj == -20, f"expected -20 inline penalty for non-BTC CRYPTO, got {adj}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

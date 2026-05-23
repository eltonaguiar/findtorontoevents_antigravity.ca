"""Unit tests for the preferred-pairs bonus feature in audit_trail/quality_gates.py.

Covers commit 823d253a1e:
    feat(HF-P0): preferred strategy-symbol pair bonus in quality_gates

Tests the `_load_preferred_pairs`, `_matches_preferred_pair`, and the +10 bonus
application inside `_apply_score_penalties`, including fail-safe behavior when
the backing JSON file is missing or malformed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from audit_trail import quality_gates


# Canonical sample recommended payload — covers all asset classes that the
# production whitelist expects the fuzzy matcher to handle.
_SAMPLE_RECOMMENDED = {
    "recommended": {
        "EQUITY|A_SuperTrend_VWMA|GOOGL|1d": {"sharpe": 2.43, "wr": 0.69},
        "COMMODITY|C_Triple_Confirmation|GC=F|1h": {"sharpe": 2.10, "wr": 0.73},
        "COMMODITY|A_SuperTrend_VWMA|SI=F|1h": {"sharpe": 1.95, "wr": 0.64},
        "FOREX|F_SHORT_Only_Contrarian|EURUSD=X|1d": {"sharpe": 2.80, "wr": 0.85},
        "CRYPTO|BreakoutMomentum|BTC|4h": {"sharpe": 1.90, "wr": 0.61},
        "ETF|LeveragedTrend|TQQQ|1d": {"sharpe": 1.88, "wr": 0.62},
        "FUTURES|A_SuperTrend_VWMA|ES=F|1h": {"sharpe": 2.05, "wr": 0.66},
    }
}


def _reset_cache_with_payload(tmp_path: Path, payload: Dict[str, Any]) -> None:
    """Write a sample payload next to a fake module parent and repoint the loader."""
    # Reset module-level cache so the next call re-reads fresh data.
    quality_gates._PREFERRED_PAIRS_CACHE = None

    # The loader reads `Path(__file__).parent.parent / cross_asset_edge_finder_results.json`.
    # To keep tests hermetic we write to the real target path, snapshotting the
    # original file first and restoring it in the fixture teardown.
    target = Path(quality_gates.__file__).resolve().parent.parent / "cross_asset_edge_finder_results.json"
    target.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def preferred_pairs_env(tmp_path):
    """Swap in a controlled preferred-pairs JSON for the duration of a test."""
    target = Path(quality_gates.__file__).resolve().parent.parent / "cross_asset_edge_finder_results.json"
    backup_bytes = target.read_bytes() if target.exists() else None

    # Start with a clean cache; the individual test decides what payload to use.
    quality_gates._PREFERRED_PAIRS_CACHE = None

    yield target

    # Restore the real file so other tests / live code remain unaffected.
    if backup_bytes is None:
        if target.exists():
            target.unlink()
    else:
        target.write_bytes(backup_bytes)
    quality_gates._PREFERRED_PAIRS_CACHE = None


def _install_payload(target: Path, payload: Dict[str, Any]) -> None:
    quality_gates._PREFERRED_PAIRS_CACHE = None
    target.write_text(json.dumps(payload), encoding="utf-8")


def _pick(**overrides: Any) -> Dict[str, Any]:
    """Build a minimal pick dict suitable for preferred-pair matching tests."""
    base = {"asset_class": "EQUITY", "strategy": "A_SuperTrend_VWMA", "symbol": "GOOGL"}
    base.update(overrides)
    return base


# ─────────────────────────── _load_preferred_pairs ───────────────────────────


def test_load_preferred_pairs_parses_keys_into_tuple_set(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pairs = quality_gates._load_preferred_pairs()
    assert isinstance(pairs, set)
    # Symbol suffix (=F / =X) is stripped at load time per the loader contract.
    assert ("EQUITY", "A_SUPERTREND_VWMA", "GOOGL") in pairs
    assert ("COMMODITY", "C_TRIPLE_CONFIRMATION", "GC") in pairs
    assert ("FOREX", "F_SHORT_ONLY_CONTRARIAN", "EURUSD") in pairs
    assert len(pairs) == len(_SAMPLE_RECOMMENDED["recommended"])


def test_load_preferred_pairs_is_cached(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    first = quality_gates._load_preferred_pairs()
    # Wipe the JSON; cached value should still be returned on second call.
    preferred_pairs_env.unlink()
    second = quality_gates._load_preferred_pairs()
    assert first is second


def test_load_preferred_pairs_missing_file_returns_empty(preferred_pairs_env):
    quality_gates._PREFERRED_PAIRS_CACHE = None
    if preferred_pairs_env.exists():
        preferred_pairs_env.unlink()
    pairs = quality_gates._load_preferred_pairs()
    assert pairs == set()
    # And no crash when we then try to match.
    assert quality_gates._matches_preferred_pair(_pick()) is False


def test_load_preferred_pairs_malformed_file_returns_empty(preferred_pairs_env):
    quality_gates._PREFERRED_PAIRS_CACHE = None
    preferred_pairs_env.write_text("{not valid json", encoding="utf-8")
    pairs = quality_gates._load_preferred_pairs()
    assert pairs == set()


def test_load_preferred_pairs_skips_short_keys(preferred_pairs_env):
    _install_payload(
        preferred_pairs_env,
        {"recommended": {"EQUITY|OnlyTwoParts": {}, "EQUITY|Good|AAPL|1d": {}}},
    )
    pairs = quality_gates._load_preferred_pairs()
    assert pairs == {("EQUITY", "GOOD", "AAPL")}


# ─────────────────────────── _matches_preferred_pair ─────────────────────────


def test_matches_exact(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    assert quality_gates._matches_preferred_pair(_pick()) is True


def test_matches_futures_symbol_with_equals_f(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="COMMODITY", strategy="C_Triple_Confirmation", symbol="GC=F")
    assert quality_gates._matches_preferred_pair(pick) is True


def test_matches_forex_symbol_with_equals_x(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(
        asset_class="FOREX", strategy="F_SHORT_Only_Contrarian", symbol="EURUSD=X"
    )
    assert quality_gates._matches_preferred_pair(pick) is True
    # And the already-stripped form matches too.
    pick2 = _pick(
        asset_class="FOREX", strategy="F_SHORT_Only_Contrarian", symbol="EURUSD"
    )
    assert quality_gates._matches_preferred_pair(pick2) is True


def test_matches_crypto_suffix_strip(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    # BTCUSDT should reduce to BTC for the crypto entry.
    pick = _pick(asset_class="CRYPTO", strategy="BreakoutMomentum", symbol="BTCUSDT")
    assert quality_gates._matches_preferred_pair(pick) is True
    # And the bare BTC form works directly.
    pick2 = _pick(asset_class="CRYPTO", strategy="BreakoutMomentum", symbol="BTC")
    assert quality_gates._matches_preferred_pair(pick2) is True


def test_matches_etf_leveraged_alias(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="ETF_LEVERAGED", strategy="LeveragedTrend", symbol="TQQQ")
    assert quality_gates._matches_preferred_pair(pick) is True


def test_matches_index_alias_to_futures(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="INDEX", strategy="A_SuperTrend_VWMA", symbol="ES=F")
    assert quality_gates._matches_preferred_pair(pick) is True


def test_matches_substring_strategy_both_directions(preferred_pairs_env):
    # Use a whitelist with the short fragment; pipeline sends a longer name.
    _install_payload(
        preferred_pairs_env,
        {"recommended": {"EQUITY|SuperTrend_VWMA|MSFT|1d": {}}},
    )
    # Pipeline name is a superset of whitelist fragment.
    pick_long = _pick(asset_class="EQUITY", strategy="A_SuperTrend_VWMA", symbol="MSFT")
    assert quality_gates._matches_preferred_pair(pick_long) is True
    # Now reverse: whitelist has the long form, pipeline sends the short form.
    _install_payload(
        preferred_pairs_env,
        {"recommended": {"EQUITY|A_SuperTrend_VWMA|MSFT|1d": {}}},
    )
    pick_short = _pick(asset_class="EQUITY", strategy="SuperTrend_VWMA", symbol="MSFT")
    assert quality_gates._matches_preferred_pair(pick_short) is True


def test_no_match_wrong_asset_class(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="CRYPTO", strategy="A_SuperTrend_VWMA", symbol="GOOGL")
    assert quality_gates._matches_preferred_pair(pick) is False


def test_no_match_wrong_symbol(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="EQUITY", strategy="A_SuperTrend_VWMA", symbol="AAPL")
    assert quality_gates._matches_preferred_pair(pick) is False


def test_no_match_wrong_strategy(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _pick(asset_class="EQUITY", strategy="random_pm_whale_signal", symbol="GOOGL")
    assert quality_gates._matches_preferred_pair(pick) is False


def test_no_match_when_whitelist_empty(preferred_pairs_env):
    _install_payload(preferred_pairs_env, {"recommended": {}})
    assert quality_gates._matches_preferred_pair(_pick()) is False


# ─────────────────────── +10 bonus in _apply_score_penalties ─────────────────


def _base_scoring_pick(**overrides: Any) -> Dict[str, Any]:
    pick = {
        "asset_class": "EQUITY",
        "strategy": "A_SuperTrend_VWMA",
        "symbol": "GOOGL",
        "score": 60,
        "confidence": 0.75,
        "direction": "LONG",
        "trust_score": 6,
        "source_system": "alpha_engine",
        "timestamp": "2026-04-05T12:00:00+00:00",
    }
    pick.update(overrides)
    return pick


def test_apply_score_penalties_adds_preferred_pair_bonus(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    matching_pick = _base_scoring_pick()
    quality_gates._apply_score_penalties(matching_pick)
    # Bonus should be recorded in _penalties.
    penalties = matching_pick.get("_penalties") or []
    assert any("preferred_pair_edge:+10" in p for p in penalties), penalties

    # Compare against an identical pick that differs ONLY in symbol (no match)
    # — every other scoring layer applies identically, so the delta should be +10.
    control = _base_scoring_pick(symbol="XYZ_NOT_WHITELISTED")
    quality_gates._apply_score_penalties(control)
    ctrl_penalties = control.get("_penalties") or []
    assert not any("preferred_pair_edge" in p for p in ctrl_penalties)
    # Exact +10 delta is the contract of the bonus.
    assert matching_pick["score"] - control["score"] == pytest.approx(10.0)


def test_apply_score_penalties_no_bonus_on_non_match(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _base_scoring_pick(symbol="AAPL")
    quality_gates._apply_score_penalties(pick)
    penalties = pick.get("_penalties") or []
    assert not any("preferred_pair_edge" in p for p in penalties), penalties


def test_apply_score_penalties_no_bonus_when_file_missing(preferred_pairs_env):
    quality_gates._PREFERRED_PAIRS_CACHE = None
    if preferred_pairs_env.exists():
        preferred_pairs_env.unlink()
    pick = _base_scoring_pick()
    quality_gates._apply_score_penalties(pick)  # must not crash
    penalties = pick.get("_penalties") or []
    assert not any("preferred_pair_edge" in p for p in penalties), penalties


def test_apply_score_penalties_is_idempotent(preferred_pairs_env):
    _install_payload(preferred_pairs_env, _SAMPLE_RECOMMENDED)
    pick = _base_scoring_pick()
    quality_gates._apply_score_penalties(pick)
    first_score = pick["score"]
    first_penalties = list(pick.get("_penalties") or [])
    # Second invocation should short-circuit via the _penalties guard.
    quality_gates._apply_score_penalties(pick)
    assert pick["score"] == first_score
    assert pick.get("_penalties") == first_penalties
    # And only one preferred_pair_edge entry exists.
    prefs = [p for p in (pick.get("_penalties") or []) if "preferred_pair_edge" in p]
    assert len(prefs) == 1

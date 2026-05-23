"""
Regression test for alpha_engine/adaptive_tp_sl.py asset_class preservation.

Background
----------
Before this fix, `apply_adaptive_tp_sl()` called `pick.get("category", "crypto")`
and used `_normalize_category(...)` which also defaulted unknown categories to
"crypto". That meant non-crypto picks (FX, equity, commodity, futures, ETF)
flowing through the adaptive TP/SL path were silently assigned crypto-tuned
levels AND were never back-filled with a correct `asset_class` tag — so the
downstream ledgers (`alpha_engine/data/closed_picks.json`,
`audit_trail/data/universal_resolved_picks.json`) ended up with ~99% of
non-crypto rows tagged CRYPTO or UNKNOWN.

This test constructs a synthetic pick per asset class with NO pre-set
`asset_class`/`category` and asserts that `apply_adaptive_tp_sl` infers the
correct class from the symbol and writes it back to the pick.

Agent D located the root cause (PR #159). PR #145 provides the companion
helper `tools/data_integrity/_common.classify_asset()`.
"""
from __future__ import annotations

import os
import sys

import pytest

# Ensure repo root on path so `alpha_engine` is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine import adaptive_tp_sl  # noqa: E402


# (symbol, expected asset_class upper-case, expected category lower-case)
FIXTURES = [
    ("BTCUSDT", "CRYPTO", "crypto"),
    ("EURUSD",  "FOREX",  "forex"),
    ("AAPL",    "EQUITY", "equity"),
    ("GC=F",    "COMMODITY", "commodity"),
    ("ES=F",    "FUTURES", "futures"),
    ("SPY",     "ETF",    "etf"),
]


def _make_pick(symbol: str) -> dict:
    """Synthetic pick with no asset_class / category preset.

    Uses a fresh strategy name with no prior history so the adaptive cache
    cannot supply per-strategy TP/SL — the code path must reach the category
    default branch, which is where the old default-to-crypto bug lives.
    """
    return {
        "id": f"test_{symbol}",
        "symbol": symbol,
        "strategy": "unit_test_no_history_strategy",
        "entry_price": 100.0,
        "take_profit": 102.0,
        "stop_loss": 99.0,
        "direction": "LONG",
        "status": "ACTIVE",
    }


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Force an empty adaptive cache so tests don't depend on repo data."""
    empty = {"per_strategy": {}, "per_symbol": {}}
    monkeypatch.setattr(adaptive_tp_sl, "_CACHE", empty, raising=False)
    monkeypatch.setattr(adaptive_tp_sl, "_CACHE_LOADED", True, raising=False)
    # Point OUTPUT_PATH at a tmp file so _ensure_cache can't reload stale JSON
    monkeypatch.setattr(
        adaptive_tp_sl,
        "OUTPUT_PATH",
        tmp_path / "adaptive_tp_sl.json",
        raising=False,
    )
    yield


@pytest.mark.parametrize("symbol,expected_ac,expected_cat", FIXTURES)
def test_apply_adaptive_tp_sl_preserves_asset_class(symbol, expected_ac, expected_cat):
    pick = _make_pick(symbol)
    out = adaptive_tp_sl.apply_adaptive_tp_sl([pick])
    assert out and len(out) == 1
    p = out[0]

    assert p.get("asset_class", "").upper() == expected_ac, (
        f"{symbol}: expected asset_class={expected_ac}, "
        f"got {p.get('asset_class')!r}"
    )
    assert str(p.get("category", "")).lower() == expected_cat, (
        f"{symbol}: expected category={expected_cat}, "
        f"got {p.get('category')!r}"
    )


def test_existing_asset_class_is_respected():
    """A pre-set asset_class on a pick must not be overwritten."""
    pick = _make_pick("EURUSD")
    pick["asset_class"] = "FOREX"
    pick["category"] = "forex"
    adaptive_tp_sl.apply_adaptive_tp_sl([pick])
    assert pick["asset_class"] == "FOREX"
    assert pick["category"] == "forex"


def test_classifier_helper_direct():
    """Direct unit test of the classifier helper on each fixture symbol."""
    # Helper must exist after the fix
    assert hasattr(adaptive_tp_sl, "_infer_asset_class_from_symbol"), (
        "adaptive_tp_sl must expose _infer_asset_class_from_symbol() after fix"
    )
    fn = adaptive_tp_sl._infer_asset_class_from_symbol
    for symbol, expected_ac, _cat in FIXTURES:
        got = fn(symbol)
        assert got.upper() == expected_ac, (
            f"{symbol}: classifier returned {got!r}, expected {expected_ac}"
        )

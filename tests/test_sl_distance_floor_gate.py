"""Unit tests for sl_distance_floor_gate.

One case per category (crypto, forex, equity/stock, commodity, futures, etf,
default) plus safe-default fall-throughs for missing / non-numeric / invalid
inputs. Each case constructs a pick with a specific entry-vs-stop distance and
asserts pass/block + that the rejection reason matches the expected category
floor.

Backed by DEEPSEEK_APR122026.MD §6B (75.5% SL hit rate on
universal_resolved_picks.json) — this is the entry-side complement to PR #137
which added the exit-side partial-TP + breakeven activation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "non_crypto_agent"))

from main import sl_distance_floor_gate  # noqa: E402


def _pick(category: str, entry: float, sl: float) -> dict:
    return {"category": category, "entry_price": entry, "stop_loss": sl}


# ---------------------------------------------------------------------------
# Per-category pass/block pairs
# ---------------------------------------------------------------------------

def test_crypto_tight_stop_blocked():
    # 1.0% distance, floor 2.0% -> block
    allowed, reason = sl_distance_floor_gate(_pick("crypto", 100.0, 99.0))
    assert not allowed
    assert "2.00%" in reason
    assert "crypto" in reason


def test_crypto_wide_stop_passes():
    # 2.5% distance, floor 2.0% -> pass
    allowed, _ = sl_distance_floor_gate(_pick("crypto", 100.0, 97.5))
    assert allowed


def test_forex_tight_stop_blocked():
    # 0.3% distance, floor 0.5% -> block
    allowed, reason = sl_distance_floor_gate(_pick("forex", 1.1000, 1.0967))
    assert not allowed
    assert "forex" in reason


def test_forex_wide_stop_passes():
    # 0.6% distance, floor 0.5% -> pass
    allowed, _ = sl_distance_floor_gate(_pick("forex", 1.1000, 1.0934))
    assert allowed


def test_equity_tight_stop_blocked():
    # 1.0% distance, floor 1.5% -> block
    allowed, reason = sl_distance_floor_gate(_pick("equity", 200.0, 198.0))
    assert not allowed
    assert "equity" in reason


def test_stock_alias_tight_stop_blocked():
    # "stock" is an alias for equity, same 1.5% floor
    allowed, reason = sl_distance_floor_gate(_pick("stock", 200.0, 198.0))
    assert not allowed
    assert "stock" in reason


def test_commodity_tight_stop_blocked():
    # 1.0% distance, floor 1.5% -> block
    allowed, reason = sl_distance_floor_gate(_pick("commodity", 2000.0, 1980.0))
    assert not allowed
    assert "commodity" in reason


def test_futures_tight_stop_blocked():
    # 1.0% distance, floor 1.5% -> block
    allowed, reason = sl_distance_floor_gate(_pick("futures", 5000.0, 4950.0))
    assert not allowed
    assert "futures" in reason


def test_etf_tight_stop_blocked():
    # 1.0% distance, floor 1.2% -> block
    allowed, reason = sl_distance_floor_gate(_pick("etf", 400.0, 396.0))
    assert not allowed
    assert "etf" in reason


def test_etf_wide_stop_passes():
    # 1.5% distance, floor 1.2% -> pass
    allowed, _ = sl_distance_floor_gate(_pick("etf", 400.0, 394.0))
    assert allowed


def test_default_category_tight_stop_blocked():
    # unknown category -> 1.0% default floor; 0.5% distance -> block
    allowed, reason = sl_distance_floor_gate(_pick("unknown_asset", 100.0, 99.5))
    assert not allowed
    assert "default" in reason or "unknown_asset" in reason


def test_default_category_wide_stop_passes():
    # unknown category -> 1.0% default floor; 1.2% distance -> pass
    allowed, _ = sl_distance_floor_gate(_pick("", 100.0, 98.8))
    assert allowed


# ---------------------------------------------------------------------------
# Safe-default fall-throughs
# ---------------------------------------------------------------------------

def test_missing_entry_passes():
    allowed, reason = sl_distance_floor_gate({"category": "crypto", "stop_loss": 99.0})
    assert allowed
    assert "missing" in reason


def test_missing_stop_passes():
    allowed, reason = sl_distance_floor_gate({"category": "crypto", "entry_price": 100.0})
    assert allowed
    assert "missing" in reason


def test_non_numeric_passes():
    allowed, reason = sl_distance_floor_gate(
        {"category": "crypto", "entry_price": "n/a", "stop_loss": 99.0}
    )
    assert allowed
    assert "non-numeric" in reason


def test_zero_entry_passes():
    allowed, _ = sl_distance_floor_gate(
        {"category": "crypto", "entry_price": 0.0, "stop_loss": 0.5}
    )
    assert allowed

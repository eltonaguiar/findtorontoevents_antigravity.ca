"""Unit tests for STOCKS #7 defense-in-depth: the mysql_trading_sync
# 2026-06-11 INCIDENT_OVERALL#88: category canonical form is now UPPERCASE at the
# ingest chokepoint (consumer-derived; see mysql_trading_sync._CATEGORY_CANONICAL_MAP).
# Expectations updated lowercase->UPPERCASE; 'meme' stays passthrough (env-mapped downstream).

classifier override that catches upstream category=crypto mistags on
non-crypto symbols.

Refs: reports/stocks_7_equity_mistag_investigation_2026-05-31.md
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# We import the formatter and rely on it calling _detect_asset_class for
# the sanity check on raw_cat="crypto".
from alpha_engine.mysql_trading_sync import pick_to_row  # type: ignore  # noqa: E402


def _base_pick(symbol: str, category: str) -> dict:
    return {
        "id": f"test_{symbol}_{category}",
        "symbol": symbol,
        "direction": "LONG",
        "strategy": "test_strategy",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "confidence": 0.8,
        "category": category,
        "source_system": "unit_test",
        "status": "ACTIVE",
        "created_at": "2026-05-31T00:00:00Z",
    }


def test_aapl_crypto_tag_overridden_to_equity():
    row = pick_to_row(_base_pick("AAPL", "crypto"))
    assert row is not None, "AAPL pick should not be filtered"
    assert row["category"] == "EQUITY", (
        f"AAPL tagged crypto must be overridden to equity, got {row['category']!r}"
    )


def test_btcusdt_crypto_tag_kept():
    row = pick_to_row(_base_pick("BTCUSDT", "crypto"))
    assert row is not None
    assert row["category"] == "CRYPTO", (
        f"BTCUSDT crypto must remain crypto, got {row['category']!r}"
    )


def test_pep_crypto_tag_overridden_to_equity():
    row = pick_to_row(_base_pick("PEP", "crypto"))
    assert row is not None
    assert row["category"] == "EQUITY", (
        f"PEP tagged crypto must be overridden to equity, got {row['category']!r}"
    )

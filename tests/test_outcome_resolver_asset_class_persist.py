"""Regression test for the asset-class persistence patch.

After resolution, picks that came in with null/empty/'UNKNOWN' asset_class
should be tagged with the resolver-derived value. Picks with an explicit
upstream tag must NOT be clobbered.

Per reports/asset_class_tagger_investigation_2026_05_04.md (Patch 1).
"""
from __future__ import annotations
from alpha_engine.outcome_resolver import _resolve_asset_class


def _persist(pick: dict) -> None:
    """Apply the same gate that's now in resolve_single_pick / preview branch."""
    existing = str(pick.get("asset_class") or "").upper().strip()
    if existing in ("UNKNOWN", "NONE"):
        scrubbed = dict(pick); scrubbed["asset_class"] = None
        asset_class = _resolve_asset_class(scrubbed)
    else:
        asset_class = _resolve_asset_class(pick)
    if asset_class and (not existing or existing in ("UNKNOWN", "NONE")):
        pick["asset_class"] = asset_class


def test_null_asset_class_gets_crypto_tag_for_usdt_symbol():
    pick = {"symbol": "BTCUSDT", "asset_class": None}
    _persist(pick)
    assert pick["asset_class"] == "CRYPTO"


def test_empty_string_asset_class_gets_tagged():
    pick = {"symbol": "MATICUSDT", "asset_class": ""}
    _persist(pick)
    assert pick["asset_class"] == "CRYPTO"


def test_unknown_string_asset_class_gets_re_derived():
    pick = {"symbol": "FETUSDT", "asset_class": "UNKNOWN"}
    _persist(pick)
    assert pick["asset_class"] == "CRYPTO"


def test_explicit_upstream_tag_is_preserved():
    """If upstream tagged COMMODITY (e.g. CT=F), do NOT clobber it."""
    pick = {"symbol": "CT=F", "asset_class": "COMMODITY"}
    _persist(pick)
    assert pick["asset_class"] == "COMMODITY"


def test_explicit_equity_is_preserved_even_with_unusual_symbol():
    pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
    _persist(pick)
    assert pick["asset_class"] == "EQUITY"


def test_forex_suffix_resolves_to_forex():
    pick = {"symbol": "EURUSD=X", "asset_class": None}
    _persist(pick)
    assert pick["asset_class"] == "FOREX"


def test_futures_suffix_resolves_to_commodity():
    """=F suffix routes through _is_non_crypto -> commodity per resolver."""
    pick = {"symbol": "CT=F", "asset_class": None}
    _persist(pick)
    # The resolver's _resolve_asset_class returns "COMMODITY" for =F.
    assert pick["asset_class"] == "COMMODITY"


def test_none_string_literal_treated_as_null():
    """Some upstream writers stamp the literal string 'None'."""
    pick = {"symbol": "ETHUSDT", "asset_class": "None"}
    _persist(pick)
    assert pick["asset_class"] == "CRYPTO"


def test_lowercase_unknown_is_normalized_via_existing_check():
    """The gate uses .upper() before comparing, so lowercase 'unknown' is caught."""
    pick = {"symbol": "SOLUSDT", "asset_class": "unknown"}
    _persist(pick)
    assert pick["asset_class"] == "CRYPTO"

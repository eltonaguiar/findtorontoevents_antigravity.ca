"""Regression test for the resolver-step7 BOND dispatch bug (2026-05-19).

500+ crypto memecoin rows landed in at_raw_picks with asset_class='BOND'
(symbols: PEPEUSDT / WIFUSDT / BONKUSDT / DOGEUSDT / SHIBUSDT / FLOKIUSDT).
yfinance correctly failed to price them; the workflow's Bug-2 fail-loud
raised. Root cause traced to:

  audit_trail/dashboard_generator.py::_normalize_orphan_emitter_pick
      → stamped BOND on ANY symbol from bond_picks.json
  audit_trail/asset_classification.py::resolve_asset_class
      → trusted the upstream asset_class tag without a crypto-symbol guard

This test pins the defensive guard that prevents BOND/ETF/EQUITY/FOREX/
COMMODITY tags on obviously-crypto symbols.
"""
import importlib

import pytest

from audit_trail.asset_classification import (
    is_obviously_crypto_symbol,
    resolve_asset_class,
)


CRYPTO_MEMES_THAT_MUST_NOT_BE_BOND = [
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT",
    "PEPE-USDT", "PEPE/USDT", "PEPE_USDT",
    "PEPE-USD", "BONK-USD", "WIF-USD",
    "BTCUSDT", "ETHUSDT", "SOLUSDC",
]


@pytest.mark.parametrize("symbol", CRYPTO_MEMES_THAT_MUST_NOT_BE_BOND)
def test_crypto_symbol_never_classifies_as_bond_even_with_explicit_tag(symbol):
    """Defensive guard: an explicit `asset_class=BOND` on a crypto symbol
    must be refused. This is the exact mis-tag that caused run 26130640164."""
    assert is_obviously_crypto_symbol(symbol), \
        f"{symbol} should be detected as crypto"

    # Resolve with poisoned raw dict — simulates the historical bulk-update bug.
    result = resolve_asset_class(symbol, raw={"asset_class": "BOND"})
    assert result == "CRYPTO", (
        f"resolve_asset_class trusted upstream BOND tag for crypto symbol "
        f"{symbol} (got {result!r}); this is the resolver-step7 dispatch bug."
    )

    # Same via category hint
    result2 = resolve_asset_class(symbol, raw={"category": "bond"})
    assert result2 == "CRYPTO", \
        f"category=bond was trusted for crypto symbol {symbol}"


def test_real_bond_symbol_still_classifies_correctly():
    """Sanity: the guard must NOT break legitimate BOND classification."""
    dg = importlib.import_module("audit_trail.dashboard_generator")
    for sym in ("TLT", "IEF", "SHY", "LQD", "HYG", "BND", "AGG"):
        out = dg._normalize_orphan_emitter_pick(
            {"symbol": sym, "entry_price": 100.0, "direction": "LONG"},
            "orphan_emitter_bond",
        )
        assert out["asset_class"] == "BOND", \
            f"{sym} should still classify as BOND, got {out['asset_class']!r}"
        assert "_orphan_emitter_class_override" not in out


def test_orphan_emitter_refuses_bond_for_crypto_symbol():
    """Defense-in-depth: a poisoned bond_picks.json listing a crypto symbol
    must be downgraded to CRYPTO at the orphan-emitter normalization layer."""
    dg = importlib.import_module("audit_trail.dashboard_generator")
    poisoned = {"symbol": "PEPEUSDT", "entry_price": 0.00001, "direction": "LONG"}
    out = dg._normalize_orphan_emitter_pick(poisoned, "orphan_emitter_bond")
    assert out["asset_class"] == "CRYPTO", (
        f"orphan_emitter_bond stamped BOND on PEPEUSDT; "
        f"got {out['asset_class']!r}"
    )
    assert out.get("_orphan_emitter_class_override") == \
        "refused_BOND_for_crypto_symbol"


def test_forex_with_usdt_quote_not_misclassified_as_crypto():
    """Edge case: rare EURUSDT-style forex pair should NOT trip the
    crypto guard (the FX-base exclusion keeps it safe)."""
    assert not is_obviously_crypto_symbol("EURUSDT"), \
        "EURUSDT is a forex pair; guard must not classify it as crypto"
    assert not is_obviously_crypto_symbol("GBPUSDT"), \
        "GBPUSDT is a forex pair; guard must not classify it as crypto"

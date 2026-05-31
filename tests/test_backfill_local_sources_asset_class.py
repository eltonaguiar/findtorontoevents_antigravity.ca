"""Tests for derive_asset_class() in audit_trail/backfill_local_sources.py.

P0 fix from PR #118 diagnosis: the mirror was emitting EQUITY 169 outcomes
vs CRYPTO 53k because derive_asset_class() hard-coded a 13-symbol allowlist
and always re-derived asset_class from symbol, ignoring the source row's
asset_class field. AMZN/GOOGL/META/AMD/NFLX (~35 symbols in
alpha_engine.config.EQUITY_SYMBOLS + LARGE_CAP_EQUITY_SYMBOLS) mirrored in
as UNKNOWN.

This test pins:
  1. row asset_class is honored when non-empty/non-UNKNOWN
  2. symbol-based fallback uses the EQUITY_SYMBOLS allowlist (incl. AMZN)
  3. CRYPTO derivation still works
  4. UNKNOWN/None row asset_class falls through to symbol-based derivation
"""

import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from audit_trail.backfill_local_sources import derive_asset_class


def test_row_asset_class_honored_for_amzn():
    # Source row says EQUITY → honored even though AMZN was previously
    # missing from the hard-coded allowlist.
    assert derive_asset_class("AMZN", row_asset_class="EQUITY") == "EQUITY"


def test_symbol_fallback_amzn_now_equity():
    # No row asset_class → symbol-based derivation must now classify AMZN
    # as EQUITY via the imported EQUITY_SYMBOLS allowlist.
    assert derive_asset_class("AMZN") == "EQUITY"
    assert derive_asset_class("GOOGL") == "EQUITY"
    assert derive_asset_class("META") == "EQUITY"
    assert derive_asset_class("AMD") == "EQUITY"


def test_row_asset_class_honored_for_crypto():
    assert derive_asset_class("BTCUSDT", row_asset_class="CRYPTO") == "CRYPTO"


def test_symbol_fallback_crypto_still_works():
    assert derive_asset_class("BTCUSDT") == "CRYPTO"
    assert derive_asset_class("ETHUSDT") == "CRYPTO"


def test_unknown_row_asset_class_falls_through():
    # Empty / UNKNOWN / None / "null" should NOT short-circuit — must fall
    # back to symbol-based derivation.
    assert derive_asset_class("AMZN", row_asset_class="") == "EQUITY"
    assert derive_asset_class("AMZN", row_asset_class="UNKNOWN") == "EQUITY"
    assert derive_asset_class("AMZN", row_asset_class=None) == "EQUITY"
    assert derive_asset_class("AMZN", row_asset_class="null") == "EQUITY"


def test_row_asset_class_normalized_uppercase():
    # Source row may use lowercase — derive must normalize.
    assert derive_asset_class("AMZN", row_asset_class="equity") == "EQUITY"
    assert derive_asset_class("BTCUSDT", row_asset_class=" crypto ") == "CRYPTO"


def test_truly_unknown_symbol_returns_unknown():
    assert derive_asset_class("ZZZZZZ") == "UNKNOWN"


def test_row_asset_class_overrides_symbol_derivation():
    # If source row explicitly tags an outcome as BOND but symbol would
    # otherwise resolve to CRYPTO, the row wins. This is the central
    # behavior change of this P0 fix.
    assert derive_asset_class("BTCUSDT", row_asset_class="BOND") == "BOND"

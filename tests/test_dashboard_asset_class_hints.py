"""Asset-class hint precedence tests for `audit_trail/dashboard_generator.py`.

Pins three misclassification fixes identified in research/21 (peer w03yqel9):

1. Meme env-flag (this PR): the `"meme": "CRYPTO"` entry in
   `_ASSET_CLASS_HINTS` was hardcoded, bypassing the
   `ASSET_CLASS_MAP_MEME_TO_CRYPTO` env-flag convention. Default ON for
   back-compat; set to "0" to unmap memes.

2. ZN=F (already shipped in #492 / 7c8c107fac): treasury futures were
   labeled BOND because upstream `category="bond"` won over the symbol
   suffix. Pinned in `tests/test_derive_asset_class_precedence.py`;
   re-asserted here as a guard against regression of this companion fix.

3. Bond ETFs (already shipped in #492 / 7c8c107fac): TLT/HYG were
   labeled ETF in 5+ rows because hand-stamped `category="etf"` beat
   the BOND_SYMBOLS lookup. Pinned in
   `tests/test_derive_asset_class_precedence.py`; HYG (not previously
   covered) is added here.
"""

from __future__ import annotations

import importlib
import os

import pytest

import audit_trail.dashboard_generator as dg


@pytest.fixture
def reload_with_env(monkeypatch):
    """Reload `dashboard_generator` after applying env vars so the
    module-level `_MEME_TO_CRYPTO` flag and `_ASSET_CLASS_HINTS` dict
    are rebuilt against the current process environment.
    """

    def _do(env: dict[str, str | None]):
        for key, value in env.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        importlib.reload(dg)
        return dg

    yield _do
    # Cleanup: restore module to env-unset default state so other test
    # files (e.g. test_derive_asset_class_precedence.py) get a clean
    # baseline. monkeypatch already rolls back env, but the module-level
    # `_MEME_TO_CRYPTO` was captured at reload time — re-reload after
    # the patch unwinds.
    monkeypatch.undo()
    importlib.reload(dg)


# ---------------------------------------------------------------------------
# Bug 1 — Meme env-flag (default ON for back-compat)
# ---------------------------------------------------------------------------


def test_meme_picks_default_to_crypto_when_env_unset(reload_with_env) -> None:
    """With `ASSET_CLASS_MAP_MEME_TO_CRYPTO` unset, meme picks classify
    as CRYPTO (back-compat behavior preserved).

    Uses a synthetic ticker (`FAKEMEME`) that is NOT in `_KNOWN_CRYPTO`,
    so the only path to CRYPTO is the meme hint. This isolates the env
    flag from the canonical-set short-circuit.
    """
    mod = reload_with_env({"ASSET_CLASS_MAP_MEME_TO_CRYPTO": None})
    assert mod._MEME_TO_CRYPTO is True
    assert mod._ASSET_CLASS_HINTS.get("meme") == "CRYPTO"
    assert mod._derive_asset_class("FAKEMEME", {"category": "meme"}) == "CRYPTO"


def test_meme_picks_default_to_crypto_when_env_set_to_one(reload_with_env) -> None:
    """Explicit `ASSET_CLASS_MAP_MEME_TO_CRYPTO=1` keeps the legacy
    mapping (parity with unset)."""
    mod = reload_with_env({"ASSET_CLASS_MAP_MEME_TO_CRYPTO": "1"})
    assert mod._MEME_TO_CRYPTO is True
    assert mod._derive_asset_class("FAKEMEME", {"category": "meme"}) == "CRYPTO"


def test_meme_picks_unmap_when_env_zero(reload_with_env) -> None:
    """With `ASSET_CLASS_MAP_MEME_TO_CRYPTO=0`, the `"meme"` hint is
    DROPPED from the lookup so a pick whose only hint is
    `category="meme"` falls through the rest of `_derive_asset_class`.

    For an unknown ticker like `FAKEMEME` (not in `_KNOWN_CRYPTO`, no
    =F/=X suffix, no crypto suffix, no source/strategy hint), the
    function falls back to EQUITY. The env flag exists exactly to
    surface these picks for inspection rather than silently bucketing
    them as CRYPTO via category metadata alone.

    Note: legitimate crypto tickers (in `_KNOWN_CRYPTO` or with USDT/
    USDC/BUSD suffixes) are NOT affected — their CRYPTO classification
    comes from the symbol path, not the meme hint. The env-flag-on/off
    delta is purely about category="meme" with NO other crypto signal.
    """
    mod = reload_with_env({"ASSET_CLASS_MAP_MEME_TO_CRYPTO": "0"})
    assert mod._MEME_TO_CRYPTO is False
    assert "meme" not in mod._ASSET_CLASS_HINTS
    # Synthetic meme ticker with no other crypto signal flips off CRYPTO.
    assert mod._derive_asset_class("FAKEMEME", {"category": "meme"}) != "CRYPTO"
    # Symbol-based crypto detection still wins regardless of the env flag.
    # DOGEUSDT has the USDT suffix → CRYPTO via `_symbol_strongly_crypto`.
    assert mod._derive_asset_class("DOGEUSDT", {"category": "meme"}) == "CRYPTO"
    # Known crypto tickers in `_KNOWN_CRYPTO` (DOGE, SHIB) also stay CRYPTO
    # — the env flag does not unmap canonical crypto tickers.
    assert mod._derive_asset_class("DOGE", {"category": "meme"}) == "CRYPTO"


# ---------------------------------------------------------------------------
# Bug 2 — ZN=F (treasury future) routes to FUTURES (already in #492; re-pin)
# ---------------------------------------------------------------------------


def test_zn_f_with_bond_category_is_futures() -> None:
    """ZN=F + upstream `category="bond"` → FUTURES (not BOND).

    Re-asserted from `tests/test_derive_asset_class_precedence.py` so a
    failure here flags the dashboard hint precedence regression even if
    that file is moved/renamed.
    """
    assert dg._derive_asset_class("ZN=F", {"category": "bond"}) == "FUTURES"


# ---------------------------------------------------------------------------
# Bug 3 — Bond ETFs route to BOND (already in #492 for TLT; HYG added here)
# ---------------------------------------------------------------------------


def test_tlt_with_etf_category_is_bond() -> None:
    """TLT + `category="etf"` → BOND. Re-pin of #492 contract."""
    assert dg._derive_asset_class("TLT", {"category": "etf"}) == "BOND"


def test_hyg_with_etf_category_is_bond() -> None:
    """HYG (high-yield bond ETF) is in BOND_SYMBOLS (alpha_engine.asset_class)
    and must classify as BOND even with hand-stamped `category="etf"`.

    HYG was not directly covered in
    `tests/test_derive_asset_class_precedence.py`; added here per
    research/21 cluster (5+ rows mislabeled ETF).
    """
    assert dg._derive_asset_class("HYG", {"category": "etf"}) == "BOND"

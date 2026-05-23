"""Asset-class precedence regression tests for `_derive_asset_class`.

Cross-AI PR review (2026-04-28) HIGH cleanup item:
The `_derive_asset_class` function in audit_trail/dashboard_generator.py is
the single source of truth for routing every dashboard pick to its asset
class on /audit. Two regressions must NEVER recur:

1. `ZN=F` (10y Treasury futures) was being labeled BOND because upstream
   `category="bond"` metadata won over the symbol heuristic. Fix: any
   `=F` suffix is unambiguously FUTURES; never let upstream hints flip it.

2. Bond ETFs (TLT/IEF/SHY/LQD/HYG/...) were being labeled ETF because
   hand-stamped `category="etf"` beat the BOND_SYMBOLS lookup (which was
   checked AFTER the hint loop). Fix: BOND_SYMBOLS hard-match runs BEFORE
   the hint loop, so bond ETFs always classify as BOND regardless of
   upstream category metadata.

This file pins both contracts plus a regression check that real ETFs
(SPY/QQQ/IWM) still classify as ETF via the late hint path — i.e. the
fix doesn't accidentally route every ETF to BOND.
"""

from __future__ import annotations

import importlib

import pytest

import audit_trail.dashboard_generator as dg


@pytest.fixture(autouse=True)
def _reload_module():
    """Reload the generator before each test so module-level state (env
    flags, hoisted imports) is reset and tests don't bleed into each other.
    """
    importlib.reload(dg)
    yield


# ---------------------------------------------------------------------------
# Futures =F precedence: symbol suffix beats upstream category
# ---------------------------------------------------------------------------


def test_zn_f_with_bond_category_is_futures() -> None:
    """ZN=F with upstream `category="bond"` MUST be FUTURES, not BOND.

    This is the regression that motivated the precedence rebuild —
    treasury futures were being aggregated into the BOND tile and
    polluting bond P/F numbers.
    """
    assert dg._derive_asset_class("ZN=F", {"category": "bond"}) == "FUTURES"


def test_es_f_index_future() -> None:
    """ES=F (E-mini S&P 500) is in _INDEX_FUTURES_ROOTS -> FUTURES."""
    assert dg._derive_asset_class("ES=F", {}) == "FUTURES"


def test_cl_f_oil_future_is_commodity() -> None:
    """CL=F (WTI crude) is in _COMMODITY_ROOTS -> COMMODITY (NOT FUTURES)."""
    assert dg._derive_asset_class("CL=F", {}) == "COMMODITY"


def test_unknown_f_root_with_bond_category_still_futures() -> None:
    """Unknown =F root + upstream `category="bond"` -> still FUTURES.

    The =F suffix is unambiguous; never let upstream hints flip it
    to BOND/EQUITY/ETF (per research/21).
    """
    assert dg._derive_asset_class("XX=F", {"category": "bond"}) == "FUTURES"


# ---------------------------------------------------------------------------
# Bond ETF precedence: BOND_SYMBOLS hard-match beats upstream category
# ---------------------------------------------------------------------------


def test_tlt_with_etf_category_is_bond() -> None:
    """TLT with upstream `category="etf"` MUST be BOND, not ETF.

    TLT is in BOND_SYMBOLS (alpha_engine.asset_class). The fix ensures
    hand-stamped category metadata cannot leak bond ETFs into the
    generic ETF tile.
    """
    assert dg._derive_asset_class("TLT", {"category": "etf"}) == "BOND"


def test_ief_bond_etf_no_category() -> None:
    """IEF (7-10y Treasury ETF) is in BOND_SYMBOLS -> BOND with no metadata."""
    assert dg._derive_asset_class("IEF", {}) == "BOND"


def test_shy_with_explicit_etf_asset_class() -> None:
    """SHY (1-3y Treasury ETF) BOND classification beats `asset_class="ETF"`."""
    assert dg._derive_asset_class("SHY", {"asset_class": "ETF"}) == "BOND"


# ---------------------------------------------------------------------------
# Real-ETF regression: SPY / QQQ / IWM stay as ETF (fix didn't break them)
# ---------------------------------------------------------------------------


def test_spy_with_etf_category_stays_etf() -> None:
    """SPY is in ETF_SYMBOLS (NOT BOND_SYMBOLS) -> ETF."""
    assert dg._derive_asset_class("SPY", {"category": "etf"}) == "ETF"


def test_qqq_with_etf_category_stays_etf() -> None:
    """QQQ is in ETF_SYMBOLS (NOT BOND_SYMBOLS) -> ETF."""
    assert dg._derive_asset_class("QQQ", {"category": "etf"}) == "ETF"


def test_iwm_no_category_stays_etf() -> None:
    """IWM is in ETF_SYMBOLS -> ETF without any upstream hint."""
    assert dg._derive_asset_class("IWM", {}) == "ETF"


# ---------------------------------------------------------------------------
# contract_type precedence: the additive tag routes true index/rates/currency
# futures into the FUTURES tile (shipped 2026-05-16). See
# tools/swarm_v2/_task_futures_tile_from_contract_type.md.
# ---------------------------------------------------------------------------


def test_contract_type_index_future_routes_to_futures() -> None:
    """A pick tagged `contract_type="index_future"` routes to FUTURES."""
    assert dg._derive_asset_class("ES=F", {"contract_type": "index_future"}) == "FUTURES"


def test_contract_type_rates_future_routes_to_futures() -> None:
    """`contract_type="rates_future"` routes to FUTURES even with bond hint."""
    assert (
        dg._derive_asset_class("ZN=F", {"contract_type": "rates_future",
                                        "category": "bond"})
        == "FUTURES"
    )


def test_contract_type_currency_future_routes_to_futures() -> None:
    """`contract_type="currency_future"` (e.g. 6E=F) routes to FUTURES."""
    assert (
        dg._derive_asset_class("6E=F", {"contract_type": "currency_future"})
        == "FUTURES"
    )


def test_contract_type_commodity_future_does_not_override() -> None:
    """`commodity_future` is NOT in the override set — CL=F stays COMMODITY.

    This is the guard that keeps historical energy/metal/grain numbers
    in the COMMODITY tile; only index/rates/currency futures get promoted.
    """
    assert (
        dg._derive_asset_class("CL=F", {"contract_type": "commodity_future"})
        == "COMMODITY"
    )


def test_contract_type_override_is_case_insensitive() -> None:
    """The tag match lowercases the raw value before comparison."""
    assert (
        dg._derive_asset_class("ES=F", {"contract_type": "INDEX_FUTURE"})
        == "FUTURES"
    )


# ---------------------------------------------------------------------------
# Module-level hoist guard: BOND_SYMBOLS / ETF_SYMBOLS imported once at top
# ---------------------------------------------------------------------------


def test_canonical_sets_hoisted_to_module_top() -> None:
    """`_AC_BOND_SYMBOLS` / `_AC_ETF_SYMBOLS` are bound at module scope.

    Cross-AI PR review HIGH cleanup: the per-call `from alpha_engine.asset_class
    import BOND_SYMBOLS as _BOND_HARD` (and the second one for ETF/BOND in
    block 3) were hot-path imports adding dict lookups on every pick.
    Hoisting moved them to the top of the file as module-level frozensets.
    """
    assert hasattr(dg, "_AC_BOND_SYMBOLS"), (
        "_AC_BOND_SYMBOLS must be a module-level binding (hoisted from "
        "the per-call try/except in _derive_asset_class)."
    )
    assert hasattr(dg, "_AC_ETF_SYMBOLS"), (
        "_AC_ETF_SYMBOLS must be a module-level binding (hoisted from "
        "the per-call import at the bottom of _derive_asset_class)."
    )
    assert isinstance(dg._AC_BOND_SYMBOLS, frozenset)
    assert isinstance(dg._AC_ETF_SYMBOLS, frozenset)
    # TLT and SPY are canonical members; if these fail, the canonical
    # set has drifted — investigate alpha_engine/asset_class.py.
    assert "TLT" in dg._AC_BOND_SYMBOLS
    assert "SPY" in dg._AC_ETF_SYMBOLS
    # Disjointness: a symbol must not be in both sets.
    assert dg._AC_BOND_SYMBOLS.isdisjoint(dg._AC_ETF_SYMBOLS), (
        "BOND_SYMBOLS and ETF_SYMBOLS overlap — precedence rules become "
        "ambiguous."
    )

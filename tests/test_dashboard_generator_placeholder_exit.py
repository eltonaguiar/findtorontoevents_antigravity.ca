"""Regression tests for the placeholder/sentinel-exit rejection fix.

Closes the QA-T2 gap from docs/superpowers/plans/2026-10-22-audit-dashboard-quality.md.

Background (see updates/2026-10-22-perf-accuracy-placeholder-exit-fix.md):
The dashboard counted rows where a price-fetch FAILURE stamped `exit_price <= 0`
as a "flat" close (outcome resolved, pnl_pct=0). 38 such placeholder rows existed
in prod (EQUITY x9 via stocksunify2, FOREX x29 via signal_validation), concentrated
in TIME_EXIT exits. Counting them inflated "flat" counts and deflated WR/PF for
those classes. The fix in `_is_valid_resolved_pick()` rejects any row whose
`exit_price <= 0`.

These tests assert the gate behaves correctly without running the full dashboard
generator (per repo rule: never run dashboard generators locally).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail import dashboard_generator as dg  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_pick(**overrides) -> dict:
    """A minimal *genuine* resolved pick that MUST pass validity."""
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "asset_class": "CRYPTO",
        "strategy": "signal_validation",
        "entry_price": 30000.0,
        "exit_price": 31500.0,
        "pnl_pct": 5.0,
        "status": "WON",
        "exit_reason": "TP_HIT",
        "outcome": "WON",
    }
    pick.update(overrides)
    return pick


# ---------------------------------------------------------------------------
# Placeholder / sentinel exit rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "exit_price",
    [
        0.0,
        -1.0,
        -0.0001,
        "0",
        "0.0",
        0,
        -5,
    ],
)
def test_rejects_nonpositive_exit_price(exit_price):
    pick = _base_pick(exit_price=exit_price, pnl_pct=0.0, status="EXPIRED",
                      exit_reason="TIME_EXIT")
    assert dg._is_valid_resolved_pick(pick) is False


def test_rejects_exit_price_none_but_pnl_zero():
    # exit_price absent + pnl 0 -> placeholder signature -> must be rejected
    pick = _base_pick()
    pick.pop("exit_price", None)
    pick["pnl_pct"] = 0.0
    pick["status"] = "EXPIRED"
    pick["exit_reason"] = "TIME_EXIT"
    assert dg._is_valid_resolved_pick(pick) is False


def test_accepts_genuine_positive_exit():
    assert dg._is_valid_resolved_pick(_base_pick()) is True


def test_accepts_win_with_distinct_positive_prices():
    # A genuine WIN (positive distinct exit price, positive pnl) must pass.
    pick = _base_pick(entry_price=30000.0, exit_price=31800.0, pnl_pct=6.0,
                      status="WON", exit_reason="TP_HIT")
    assert dg._is_valid_resolved_pick(pick) is True


def test_accepts_negative_pnl_with_positive_exit():
    # A real LOSS (positive exit price, negative pnl) must remain valid.
    pick = _base_pick(exit_price=28000.0, pnl_pct=-6.67, status="LOST",
                      exit_reason="SL_HIT", outcome="LOST")
    assert dg._is_valid_resolved_pick(pick) is True


def test_float_coercion_failure_treated_as_placeholder():
    # Non-numeric exit_price should be treated as placeholder (cannot price it).
    pick = _base_pick(exit_price="N/A", pnl_pct=0.0, status="EXPIRED",
                      exit_reason="TIME_EXIT")
    assert dg._is_valid_resolved_pick(pick) is False


# ---------------------------------------------------------------------------
# 38-row replication harness (prod evidence)
# ---------------------------------------------------------------------------

def test_stocksunify2_equity_placeholder_rows_rejected():
    """Representative stocksunify2 EQUITY TIME_EXIT row (exit_price<=0)."""
    pick = _base_pick(
        symbol="AAPL",
        direction="LONG",
        asset_class="EQUITY",
        strategy="stocksunify2",
        entry_price=150.0,
        exit_price=0.0,
        pnl_pct=0.0,
        status="EXPIRED",
        exit_reason="TIME_EXIT",
    )
    assert dg._is_valid_resolved_pick(pick) is False


def test_signal_validation_forex_placeholder_rows_rejected():
    """Representative signal_validation FOREX TIME_EXIT row (exit_price<=0)."""
    pick = _base_pick(
        symbol="GBPUSD=X",
        direction="LONG",
        asset_class="FOREX",
        strategy="signal_validation",
        entry_price=1.25,
        exit_price=-1.0,
        pnl_pct=0.0,
        status="EXPIRED",
        exit_reason="TIME_EXIT",
    )
    assert dg._is_valid_resolved_pick(pick) is False


def test_genuine_forex_row_with_positive_exit_accepted():
    pick = _base_pick(
        symbol="EURUSD=X",
        direction="LONG",
        asset_class="FOREX",
        strategy="signal_validation",
        entry_price=1.08,
        exit_price=1.10,
        pnl_pct=1.85,
        status="WON",
        exit_reason="TP_HIT",
    )
    assert dg._is_valid_resolved_pick(pick) is True


# ---------------------------------------------------------------------------
# Asset-class mislabel guard (QA-T3): known crypto tokens trump weak upstream
# EQUITY hints (e.g. momentum_breakout stamps BNB as asset_class="EQUITY").
# ---------------------------------------------------------------------------

def test_derive_asset_class_bnb_resolves_crypto():
    """BNB is an unambiguous crypto token; a stray EQUITY hint must not win."""
    ac = dg._derive_asset_class(
        symbol="BNB",
        raw={"asset_class": "EQUITY", "category": "equity"},
        source_system="momentum_breakout",
        strategy="momentum_breakout",
    )
    assert ac == "CRYPTO"


def test_derive_asset_class_bnb_plain_symbol():
    ac = dg._derive_asset_class(symbol="BNB")
    assert ac == "CRYPTO"


def test_derive_asset_class_known_equity_still_equity():
    """The guard must NOT reclassify genuine equities into CRYPTO."""
    ac = dg._derive_asset_class(
        symbol="MSTR",
        raw={"asset_class": "EQUITY", "category": "equity"},
        source_system="alpha_engine",
        strategy="vol_breakout",
    )
    assert ac == "EQUITY"

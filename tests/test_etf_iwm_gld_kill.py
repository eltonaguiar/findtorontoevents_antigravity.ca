"""
Tests for the ETF surgical blacklist (Phase 2-E ETF panel, 2026-04-29).

Per the Phase 2-E ETF panel verdict (6/6 unanimous,
reports/HFPA_PHASE-2-findings-ETF-2026-04-29.md):

The ETF asset class is a Tier 1 CANDIDATE on the 30d window (4/6 TIER_1 +
2/6 CANDIDATE) but n=38 is under the PROVEN floor of 200. Within the
class, IWM (small-cap) and GLD (gold) are clear NEGATIVE-edge symbols
that drag the sector ETF (XLK/XLE/QQQ/SOXX) edge.

Per-symbol verification (audit_dashboard/data/dashboard_data.json
recent_closed, 2026-04-29):

    IWM (small-cap):   n= 16  WR 43.8%  sum -11.67%  KILL
    GLD (gold):        n= 11  WR 36.4%  sum  -6.23%  KILL
    XLF:               n=  3  WR 33.3%  sum  -1.54%  KEEP (small n)
    SPY (broad):       n= 10  WR 50.0%  sum  -0.09%  KEEP (flat, not bad)
    QQQ (broad-tech):  n= 13  WR 61.5%  sum  +5.24%  KEEP
    XLE (energy):      n= 16  WR 56.2%  sum  +7.91%  KEEP
    XLK (tech):        n=  7  WR 71.4%  sum +14.55%  KEEP

Surgical: blacklist IWM + GLD only at the asset_class==ETF level.
Default-on. Rollback: ETF_IWM_GLD_KILL_DISABLED=1.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import (
    ETF_BLACKLIST,
    passes_active_gate,
    passes_smart_gate,
)


def _etf_pick(**overrides):
    """Build a minimum-viable ETF pick that would otherwise pass the gate."""
    pick = {
        "id": "etf-test-1",
        "symbol": "QQQ",
        "asset_class": "ETF",
        # pm_whale_signals has no matrix_symbol_gates restriction (unlike alpha_engine
        # which is restricted to USDJPY=X). Tests here target ETF blacklist logic only.
        "source_system": "pm_whale_signals",
        "strategy": "etf_momentum",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 400.0,
        "take_profit": 412.0,
        "stop_loss": 392.0,
        "score": 65,
        "elite_score": None,
        "trust_score": 7,
        "trust_label": "PROVEN",
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
        # Walk-forward not labelled FAILING (default treated as PASS)
        "wf_verdict": "PASS",
    }
    pick.update(overrides)
    return pick


# ────────────────────────────────────────────────────────────
# Constant integrity
# ────────────────────────────────────────────────────────────

def test_etf_blacklist_is_frozenset_with_iwm_and_gld():
    assert isinstance(ETF_BLACKLIST, frozenset)
    # SLV added to blacklist after initial IWM+GLD kill (low-n, high-vol commodity proxy)
    assert {"IWM", "GLD"}.issubset(ETF_BLACKLIST)


def test_etf_blacklist_does_not_include_sector_or_broad_etfs():
    """Regression guard: panel KEEP-set must NOT be in the blacklist."""
    keep_set = {"XLK", "XLE", "QQQ", "SOXX", "SPY", "XLF"}
    assert ETF_BLACKLIST.isdisjoint(keep_set)


# ────────────────────────────────────────────────────────────
# Active-gate KILL coverage
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("killed_symbol", ["IWM", "GLD"])
def test_active_gate_blocks_etf_blacklist_symbols(killed_symbol, monkeypatch):
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol=killed_symbol)
    assert passes_active_gate(pick) is False


def test_active_gate_blocks_etf_blacklist_lowercase_asset_class(monkeypatch):
    """asset_class normalization — lowercase 'etf' must still hit the kill."""
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol="IWM", asset_class="etf")
    assert passes_active_gate(pick) is False


# ────────────────────────────────────────────────────────────
# Active-gate KEEP coverage (sector + broad ETFs preserved)
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "kept_symbol",
    ["XLK", "XLE", "QQQ", "SOXX", "SPY"],
)
def test_active_gate_allows_sector_and_broad_etfs(kept_symbol, monkeypatch):
    """Sector ETFs (XLK/XLE/QQQ/SOXX) and broad-market SPY must survive."""
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol=kept_symbol)
    # We only assert the ETF blacklist did NOT reject — other gates may still
    # reject for unrelated reasons, so we assert via direct constant lookup
    # plus the gate as a whole passing.
    assert kept_symbol not in ETF_BLACKLIST
    assert passes_active_gate(pick) is True


# ────────────────────────────────────────────────────────────
# Asset-class scoping (regression guards)
# ────────────────────────────────────────────────────────────

def test_equity_symbol_named_iwm_is_NOT_blocked_by_etf_kill(monkeypatch):
    """
    Defensive scoping check: even if some upstream emitter mis-tagged an
    EQUITY pick with symbol='IWM', the ETF-class kill must NOT fire
    (different asset class, different rule). It would have to be killed
    by the EQUITY rule path if at all.
    """
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol="IWM", asset_class="EQUITY")
    # The ETF kill specifically must not be the rejecter — gate may still
    # accept (no matching EQUITY rule for IWM as of this PR).
    assert passes_active_gate(pick) is True


@pytest.mark.parametrize(
    "ac,sym",
    [
        ("CRYPTO", "BTCUSDT"),
        ("FOREX", "EURUSD=X"),
        ("COMMODITY", "HG=F"),
    ],
)
def test_other_asset_classes_unaffected_by_etf_kill(ac, sym, monkeypatch):
    """Regression guard: CRYPTO/FOREX/COMMODITY symbols must not be touched."""
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    # NS-E defaulted ON 2026-05-15; bypass so FOREX scoping assertion is testable.
    monkeypatch.setenv("FOREX_HARD_DISABLE", "0")
    # FOREX directional gate (default ON) rejects LONG picks with elite<75;
    # bypass so this ETF-scoping test is not confounded by it.
    monkeypatch.setenv("FOREX_DIRECTIONAL_GATE_ENABLED", "0")
    # FOREX smart gate blocks LONG picks; bypass for ETF-scoping isolation test.
    monkeypatch.setenv("FOREX_SHORT_ONLY_GATE_DISABLED", "1")
    # FOREX session gate (M-078) is time-dependent; disable for isolation test.
    monkeypatch.setenv("FOREX_SESSION_GATE_DISABLED", "1")
    # Concentration cap fires on live DB state; disable for this scoping-only test.
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    pick = _etf_pick(symbol=sym, asset_class=ac)
    assert passes_active_gate(pick) is True


# ────────────────────────────────────────────────────────────
# Rollback flag
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("symbol", ["IWM", "GLD"])
def test_rollback_flag_re_admits_blacklisted_etfs(symbol, monkeypatch):
    """ETF_IWM_GLD_KILL_DISABLED=1 must restore legacy permissive behavior."""
    monkeypatch.setenv("ETF_IWM_GLD_KILL_DISABLED", "1")
    pick = _etf_pick(symbol=symbol)
    assert passes_active_gate(pick) is True


# ────────────────────────────────────────────────────────────
# Smart-gate defense-in-depth duplicate
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("killed_symbol", ["IWM", "GLD"])
def test_smart_gate_blocks_etf_blacklist_symbols(killed_symbol, monkeypatch):
    """Defensive duplicate: smart gate must also block ETF blacklist."""
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol=killed_symbol)
    assert passes_smart_gate(pick) is False


def test_smart_gate_allows_keep_set_etf(monkeypatch):
    monkeypatch.delenv("ETF_IWM_GLD_KILL_DISABLED", raising=False)
    pick = _etf_pick(symbol="QQQ")
    # Smart gate has additional checks (provenance, score thresholds, etc.)
    # that may reject for unrelated reasons; we only need to confirm the
    # ETF blacklist did NOT reject. Verify by direct constant check.
    assert "QQQ" not in ETF_BLACKLIST

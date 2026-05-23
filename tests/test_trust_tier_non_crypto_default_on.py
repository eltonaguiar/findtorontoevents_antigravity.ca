"""
Tests for the default-on disable of trust-tier gate for non-CRYPTO
classes (2026-04-29, Gate 1 Q4 = A unanimous).

Per Gate 1 Q4 = A (5/5 UNANIMOUS panel + 8-stream consensus 2026-04-29):
The trust-tier model is calibrated for CRYPTO and produces INVERTED
results on every other asset class.

Verified data (recent_closed n=3500):
  EQUITY UNTRUSTED n=185 sum +$246.23 (TOP); RELIABLE n=26 sum -$10.51
  CRYPTO RELIABLE  n=716 sum +$107;          BANNED   n=157 sum -$57

Behavior:
  - Default-ON bypass for FOREX, COMMODITY, EQUITY, ETF, BOND, FUTURES.
  - CRYPTO trust-tier gate UNCHANGED.
  - Each non-CRYPTO class can be force-re-enabled via dedicated env flag:
      TRUST_TIER_GATE_FORCE_<CLASS>_ENABLED=1
  - Back-compat: PR #508's EQUITY_TRUST_TIER_EXEMPT_ENABLED still works.
"""

import os
from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import (
    NON_CRYPTO_TRUST_EXEMPT_CLASSES,
    passes_active_gate,
)


def _build_pick(asset_class: str, **overrides):
    """Build a pick that would otherwise pass the active gate.

    Symbol/source vary by asset class to stay realistic, but the
    trust-tier gate is class-agnostic so the structural minimum is the
    `asset_class` field plus a non-empty pick body.
    """
    sym_by_class = {
        "EQUITY": "AAPL",
        "FOREX": "EURUSD=X",
        # 2026-04-30: HG=F (copper, KEEP-set) instead of CL=F since #535
        # (COMMODITY sub-class kill) blacklists CL=F. Test must use a
        # non-blacklisted symbol or the gate rejects before trust-tier check.
        "COMMODITY": "HG=F",
        "ETF": "SPY",
        "BOND": "TLT",
        "FUTURES": "ES=F",
        "CRYPTO": "BTCUSDT",
    }
    # M-108 magnitude gate: TP/SL must be within per-class plausibility caps.
    # FOREX cap=6%, BOND cap=5%, all others cap≥12%. Use conservative values
    # so the magnitude gate never fires and the trust-tier logic is isolated.
    tp_by_class = {
        "FOREX": 103.0,   # 3% — within FOREX 6% cap
        "BOND":  104.0,   # 4% — within BOND 5% cap
    }
    sl_by_class = {
        "FOREX": 98.0,    # 2%
        "BOND":  97.0,    # 3%
    }
    pick = {
        "id": f"{asset_class.lower()}-1",
        "symbol": sym_by_class.get(asset_class, "AAPL"),
        "asset_class": asset_class,
        "source_system": "alpha_engine",
        "strategy": "alpha_engine_momo_v3",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": tp_by_class.get(asset_class, 110.0),
        "stop_loss": sl_by_class.get(asset_class, 95.0),
        "score": 65,
        "elite_score": None,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "RELIABLE",
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }
    pick.update(overrides)
    return pick


@pytest.fixture(autouse=True)
def _clear_flags(monkeypatch):
    """Each test starts with all relevant env flags cleared."""
    for flag in (
        "EQUITY_TRUST_TIER_EXEMPT_ENABLED",
        "TRUST_TIER_GATE_FORCE_EQUITY_ENABLED",
        "TRUST_TIER_GATE_FORCE_FOREX_ENABLED",
        "TRUST_TIER_GATE_FORCE_COMMODITY_ENABLED",
        "TRUST_TIER_GATE_FORCE_ETF_ENABLED",
        "TRUST_TIER_GATE_FORCE_BOND_ENABLED",
        "TRUST_TIER_GATE_FORCE_FUTURES_ENABLED",
        "TRUST_TIER_GATE_FORCE_CRYPTO_ENABLED",
    ):
        monkeypatch.delenv(flag, raising=False)
    # NS-E defaulted ON 2026-05-15 (FOREX class-wide halt). Disable here so
    # trust-tier logic under test is reachable for FOREX picks.
    monkeypatch.setenv("FOREX_HARD_DISABLE", "0")
    # FOREX smart gate blocks LONG picks; disable for trust-tier isolation tests.
    monkeypatch.setenv("FOREX_SHORT_ONLY_GATE_DISABLED", "1")
    # M-078 FOREX session gate is time-dependent; disable for isolation tests.
    monkeypatch.setenv("FOREX_SESSION_GATE_DISABLED", "1")
    yield


# ────────────────────────────────────────────────────────────────────
# Default-on bypass: non-CRYPTO BANNED picks PASS
# ────────────────────────────────────────────────────────────────────

def test_equity_banned_passes_by_default():
    """Q4=A: EQUITY BANNED passes by default (no env flag)."""
    pick = _build_pick("EQUITY", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_forex_banned_passes_by_default():
    """Q4=A: FOREX BANNED passes by default."""
    pick = _build_pick("FOREX", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_commodity_banned_passes_by_default():
    """Q4=A: COMMODITY BANNED passes by default."""
    pick = _build_pick("COMMODITY", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_etf_banned_passes_by_default():
    """Q4=A: ETF BANNED passes by default."""
    pick = _build_pick("ETF", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_bond_banned_passes_by_default():
    """Q4=A: BOND BANNED passes by default."""
    pick = _build_pick("BOND", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_futures_banned_passes_by_default():
    """Q4=A: FUTURES BANNED passes by default."""
    pick = _build_pick("FUTURES", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


# ────────────────────────────────────────────────────────────────────
# CRYPTO regression guard: trust-tier gate UNCHANGED
# ────────────────────────────────────────────────────────────────────

def test_crypto_banned_still_blocked_by_default():
    """Regression guard: CRYPTO BANNED is STILL blocked by default.

    The trust-tier model is correctly calibrated for CRYPTO; the
    Q4=A bypass is for non-CRYPTO only.
    """
    pick = _build_pick("CRYPTO", trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_crypto_avoid_still_blocked_by_default():
    """Regression guard: CRYPTO AVOID is STILL blocked by default."""
    pick = _build_pick("CRYPTO", trust_tier="AVOID")
    assert passes_active_gate(pick) is False


def test_crypto_untrusted_still_blocked_by_default():
    """Regression guard: CRYPTO UNTRUSTED is STILL blocked by default."""
    pick = _build_pick("CRYPTO", trust_tier="UNTRUSTED")
    assert passes_active_gate(pick) is False


# ────────────────────────────────────────────────────────────────────
# Per-class force-re-enable flags
# ────────────────────────────────────────────────────────────────────

def test_equity_banned_blocked_when_force_flag_on(monkeypatch):
    """Force flag ON: EQUITY BANNED is blocked again.

    Operator can re-enable trust-tier for EQUITY via
    TRUST_TIER_GATE_FORCE_EQUITY_ENABLED=1 if a class-specific
    re-trained trust model is validated.
    """
    monkeypatch.setenv("TRUST_TIER_GATE_FORCE_EQUITY_ENABLED", "1")
    pick = _build_pick("EQUITY", trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_forex_force_flag_re_enables_gate(monkeypatch):
    """Force flag ON for FOREX re-enables the trust-tier gate."""
    monkeypatch.setenv("TRUST_TIER_GATE_FORCE_FOREX_ENABLED", "1")
    pick = _build_pick("FOREX", trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_commodity_force_flag_re_enables_gate(monkeypatch):
    """Force flag ON for COMMODITY re-enables the trust-tier gate."""
    monkeypatch.setenv("TRUST_TIER_GATE_FORCE_COMMODITY_ENABLED", "1")
    pick = _build_pick("COMMODITY", trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_force_flag_only_affects_target_class(monkeypatch):
    """Force flag for EQUITY does NOT affect FOREX (per-class isolation)."""
    monkeypatch.setenv("TRUST_TIER_GATE_FORCE_EQUITY_ENABLED", "1")
    eq = _build_pick("EQUITY", trust_tier="BANNED")
    fx = _build_pick("FOREX", trust_tier="BANNED")
    assert passes_active_gate(eq) is False  # EQUITY now gated
    assert passes_active_gate(fx) is True   # FOREX still bypassed


def test_force_flag_non_one_value_treated_off(monkeypatch):
    """Only literal '1' force-re-enables; other values keep default bypass."""
    for val in ("0", "true", "yes", "ON", "2"):
        monkeypatch.setenv("TRUST_TIER_GATE_FORCE_EQUITY_ENABLED", val)
        pick = _build_pick("EQUITY", trust_tier="BANNED")
        assert (
            passes_active_gate(pick) is True
        ), f"Expected non-'1' value {val!r} to leave default bypass active"


# ────────────────────────────────────────────────────────────────────
# Back-compat with PR #508 (deprecated but still functional)
# ────────────────────────────────────────────────────────────────────

def test_pr508_legacy_flag_still_works_for_equity(monkeypatch):
    """Back-compat: PR #508 EQUITY_TRUST_TIER_EXEMPT_ENABLED=1 still allows
    EQUITY BANNED (same outcome as the new default-on bypass)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _build_pick("EQUITY", trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_pr508_legacy_flag_does_not_unblock_crypto(monkeypatch):
    """Back-compat regression guard: PR #508 flag is EQUITY-only and must
    NOT alter CRYPTO behavior."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _build_pick("CRYPTO", trust_tier="BANNED")
    assert passes_active_gate(pick) is False


# ────────────────────────────────────────────────────────────────────
# Constants / env-flag default sanity
# ────────────────────────────────────────────────────────────────────

def test_non_crypto_exempt_classes_constant_membership():
    """Constant lists exactly the 6 expected non-CRYPTO classes."""
    assert NON_CRYPTO_TRUST_EXEMPT_CLASSES == frozenset(
        {"EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"}
    )
    assert "CRYPTO" not in NON_CRYPTO_TRUST_EXEMPT_CLASSES


def test_default_force_flag_is_off_for_all_classes():
    """All TRUST_TIER_GATE_FORCE_<CLASS>_ENABLED flags read as '0' by default."""
    for cls in ("EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"):
        assert os.environ.get(f"TRUST_TIER_GATE_FORCE_{cls}_ENABLED", "0") == "0"

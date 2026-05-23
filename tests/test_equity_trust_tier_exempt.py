"""
Back-compat tests for the (DEPRECATED) opt-in EQUITY trust-tier exemption
flag from PR #508 (2026-04-29).

DEPRECATION NOTICE: As of the Gate 1 Q4=A unanimous decision (2026-04-29),
the trust-tier gate is bypassed by DEFAULT for ALL non-CRYPTO classes
(EQUITY, FOREX, COMMODITY, ETF, BOND, FUTURES). The legacy
`EQUITY_TRUST_TIER_EXEMPT_ENABLED` flag from PR #508 remains for
back-compat (still works when set to "1") but is now redundant — EQUITY
is bypassed regardless of the flag.

These tests verify back-compat is preserved. The behavioral change
(default-on bypass for non-CRYPTO) is covered in
test_trust_tier_non_crypto_default_on.py.

Per round 2 4-AI panel verdict (reports/ai_round2_synthesis_2026_04_29.md
Finding 2), the trust-tier gate is INVERTED on EQUITY:

  EQUITY UNTRUSTED: n=185, WR 58.9%, sum +$246.23 (TOP)
  EQUITY BANNED:    n=143, WR 47.6%, sum  +$51.05 (positive!)
  EQUITY RELIABLE:  n= 26, WR 61.5%, sum  -$10.51 (LOSING)

CRYPTO behaves normally (RELIABLE +$107, BANNED -$57). CRYPTO is NEVER
altered by either the legacy flag or the new default-on bypass.
"""

import os
from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import passes_active_gate


def _equity_pick(**overrides):
    """Build an EQUITY pick that would otherwise pass the active gate."""
    pick = {
        "id": "eq-1",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        # pm_whale_signals has no matrix_symbol_gates restriction (unlike alpha_engine
        # which is restricted to USDJPY=X). Tests here target trust-tier logic only.
        "source_system": "pm_whale_signals",
        "strategy": "alpha_engine_momo_v3",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
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


def _crypto_pick(**overrides):
    """Build a CRYPTO pick that would otherwise pass the active gate."""
    pick = {
        "id": "cr-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals",
        "strategy": "pm_whale_0xeee92f",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 65,
        "elite_score": None,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "RELIABLE",
        "confidence": 0.88,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }
    pick.update(overrides)
    return pick


@pytest.fixture(autouse=True)
def _clear_flag(monkeypatch):
    """Each test starts with the flag explicitly cleared."""
    monkeypatch.delenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", raising=False)
    yield


def test_default_env_flag_is_off():
    """Env-flag default is '0' (i.e., absence reads as off)."""
    # The implementation reads via os.environ.get(...,"0"); when unset it
    # MUST evaluate to "0" so back-compat is preserved.
    assert os.environ.get("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "0") == "0"


def test_equity_banned_passes_when_flag_off_default_q4a():
    """Q4=A default-on: EQUITY BANNED now PASSES with no flag set.

    BEHAVIOR CHANGE (2026-04-29 Gate 1 Q4=A): trust-tier model is
    calibrated for CRYPTO; on EQUITY it is INVERTED. Default-on bypass
    means EQUITY BANNED no longer blocked even when the legacy
    EQUITY_TRUST_TIER_EXEMPT_ENABLED flag is unset.
    """
    pick = _equity_pick(trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_equity_avoid_passes_when_flag_off_default_q4a():
    """Q4=A default-on: EQUITY AVOID also passes by default."""
    pick = _equity_pick(trust_tier="AVOID")
    assert passes_active_gate(pick) is True


def test_equity_untrusted_passes_when_flag_off_default_q4a():
    """Q4=A default-on: EQUITY UNTRUSTED passes by default.

    UNTRUSTED is the TOP performer on EQUITY (WR 58.9% sum +$246).
    With the Q4=A unanimous decision, it now passes without any flag.
    """
    pick = _equity_pick(trust_tier="UNTRUSTED")
    assert passes_active_gate(pick) is True


def test_equity_banned_passes_when_flag_on(monkeypatch):
    """Flag ON: EQUITY BANNED passes the trust-tier gate."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _equity_pick(trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_equity_untrusted_passes_when_flag_on(monkeypatch):
    """Flag ON: EQUITY UNTRUSTED passes (this is the target — top WR cohort)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _equity_pick(trust_tier="UNTRUSTED")
    assert passes_active_gate(pick) is True


def test_equity_avoid_passes_when_flag_on(monkeypatch):
    """Flag ON: EQUITY AVOID also passes (full bypass for EQUITY)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _equity_pick(trust_tier="AVOID")
    assert passes_active_gate(pick) is True


def test_crypto_banned_blocked_when_flag_off():
    """CRYPTO BANNED is blocked when flag is OFF (control)."""
    pick = _crypto_pick(trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_crypto_banned_blocked_when_flag_on(monkeypatch):
    """CRYPTO BANNED is STILL blocked when flag is ON — flag is EQUITY-only.

    This is the most important safety test: enabling the EQUITY exemption
    must NOT alter CRYPTO behavior. The trust model is correctly calibrated
    for crypto; the exemption is a surgical bypass for EQUITY only.
    """
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _crypto_pick(trust_tier="BANNED")
    assert passes_active_gate(pick) is False


def test_crypto_untrusted_blocked_when_flag_on(monkeypatch):
    """CRYPTO UNTRUSTED is STILL blocked when flag is ON (CRYPTO unchanged)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _crypto_pick(trust_tier="UNTRUSTED")
    assert passes_active_gate(pick) is False


def test_crypto_avoid_blocked_when_flag_on(monkeypatch):
    """CRYPTO AVOID is STILL blocked when flag is ON (CRYPTO unchanged)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _crypto_pick(trust_tier="AVOID")
    assert passes_active_gate(pick) is False


def test_equity_reliable_passes_regardless_of_flag():
    """EQUITY RELIABLE is not in the blocked set — passes either way."""
    pick = _equity_pick(trust_tier="RELIABLE")
    assert passes_active_gate(pick) is True


def test_equity_reliable_passes_with_flag_on(monkeypatch):
    """EQUITY RELIABLE still passes when flag is ON (no regression)."""
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "1")
    pick = _equity_pick(trust_tier="RELIABLE")
    assert passes_active_gate(pick) is True


def test_flag_string_zero_no_longer_blocks_q4a(monkeypatch):
    """Q4=A default-on: setting EQUITY_TRUST_TIER_EXEMPT_ENABLED='0'
    no longer blocks EQUITY BANNED — the new default-on non-CRYPTO
    bypass takes over. To force-block EQUITY again, operator must
    set TRUST_TIER_GATE_FORCE_EQUITY_ENABLED=1.
    """
    monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "0")
    pick = _equity_pick(trust_tier="BANNED")
    assert passes_active_gate(pick) is True


def test_flag_other_values_no_longer_block_q4a(monkeypatch):
    """Q4=A default-on: non-'1' values of the legacy flag no longer
    re-enable the trust-tier gate; default-on bypass is now in effect."""
    for val in ("true", "yes", "ON", "2", " 1 ", "0"):
        monkeypatch.setenv("EQUITY_TRUST_TIER_EXEMPT_ENABLED", val)
        pick = _equity_pick(trust_tier="BANNED")
        assert (
            passes_active_gate(pick) is True
        ), f"Expected default-on bypass to allow EQUITY BANNED for flag={val!r}"

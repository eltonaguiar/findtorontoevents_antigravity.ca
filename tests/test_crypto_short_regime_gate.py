"""
Tests for the CRYPTO SHORT regime-gate / kill-switch (Phase 2-A 7/8, 2026-04-29).

Two opt-in env-flags (both default-OFF, no behavior regression):
  - CRYPTO_SHORT_DISABLED=1: kill-switch, blocks ALL crypto SHORTs
  - CRYPTO_SHORT_REGIME_GATE_ENABLED=1: blocks crypto SHORTs in bull regime

The module-level _is_crypto_bull_regime() reads
alpha_engine/data/regime_report.json["regime"] and is monkey-patched to
mocks in these tests for determinism.

Defense-in-depth: gate is wired into BOTH passes_active_gate and
passes_smart_gate. Tests verify both paths.
"""

from datetime import datetime, timezone

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import (
    passes_active_gate,
    passes_smart_gate,
    _crypto_short_gate_block_reason,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _crypto_short_pick():
    """Minimal CRYPTO SHORT pick that would pass passes_active_gate by default
    (no SHORT-specific blocks unrelated to the new regime-gate)."""
    return {
        "id": "test-crypto-short-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "alpha_engine",
        "strategy": "test_neutral_strategy",
        "status": "OPEN",
        "direction": "SHORT",
        "entry_price": 70000.0,
        "take_profit": 65000.0,
        "stop_loss": 73000.0,
        "score": 65,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "trust_tier": "PROVEN",
        "confidence": 0.75,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }


def _crypto_long_pick():
    p = _crypto_short_pick()
    p["id"] = "test-crypto-long-1"
    p["direction"] = "LONG"
    p["take_profit"] = 75000.0
    p["stop_loss"] = 67000.0
    return p


def _equity_short_pick():
    p = _crypto_short_pick()
    p["id"] = "test-equity-short-1"
    p["asset_class"] = "EQUITY"
    p["symbol"] = "AAPL"
    p["entry_price"] = 200.0
    p["take_profit"] = 180.0
    p["stop_loss"] = 210.0
    return p


def _forex_short_pick():
    p = _crypto_short_pick()
    p["id"] = "test-forex-short-1"
    p["asset_class"] = "FOREX"
    p["symbol"] = "EURUSD=X"
    p["entry_price"] = 1.10
    p["take_profit"] = 1.05
    p["stop_loss"] = 1.12
    return p


def _commodity_short_pick():
    p = _crypto_short_pick()
    p["id"] = "test-commodity-short-1"
    p["asset_class"] = "COMMODITY"
    p["symbol"] = "GC=F"
    p["entry_price"] = 4500.0
    p["take_profit"] = 4200.0
    p["stop_loss"] = 4600.0
    return p


def _clear_short_flags(monkeypatch):
    """Ensure both flags are default-off at start of test."""
    monkeypatch.delenv("CRYPTO_SHORT_DISABLED", raising=False)
    monkeypatch.delenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", raising=False)


# ---------------------------------------------------------------------------
# 1. DEFAULT BEHAVIOR (both flags off ÔåÆ no change)
# ---------------------------------------------------------------------------


def test_default_on_crypto_short_blocked_in_bull(monkeypatch) -> None:
    """Default state as of 2026-05-13: CRYPTO_SHORT_REGIME_GATE_ENABLED defaults
    to '1' (ON) per 4/4 swarm consensus + verified 22.6pp LONG/SHORT asymmetry.
    With no flags set and bull regime (fallback default), helper returns the
    bull-regime block reason."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert (
        _crypto_short_gate_block_reason(_crypto_short_pick())
        == "crypto_short_blocked_in_bull_regime"
    )


def test_default_on_crypto_short_passes_in_non_bull(monkeypatch) -> None:
    """Default ON but regime not bull -> regime gate does not fire."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert _crypto_short_gate_block_reason(_crypto_short_pick()) is None


def test_default_off_explicitly_zero_no_block(monkeypatch) -> None:
    """Explicit "0" values ÔåÆ no block."""
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "0")
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "0")
    assert _crypto_short_gate_block_reason(_crypto_short_pick()) is None


def test_default_off_active_gate_no_short_specific_rejection(monkeypatch) -> None:
    """With both flags explicitly off (=0), the regime-gate must not contribute
    a rejection reason. Note: as of 2026-05-13 the default for
    CRYPTO_SHORT_REGIME_GATE_ENABLED changed to '1' (ON) per 4/4 swarm
    consensus. This test pins the explicit-zero path."""
    _clear_short_flags(monkeypatch)
    # Explicitly disable the regime gate (default is now '1'/ON since 2026-05-13)
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "0")
    monkeypatch.setattr(
        qg, "_is_crypto_bull_regime", lambda: True
    )  # would-be bull regime — but flag=0 → should not block
    pick = _crypto_short_pick()
    # Helper directly: must return None
    assert _crypto_short_gate_block_reason(pick) is None


# ---------------------------------------------------------------------------
# 2. KILL-SWITCH (CRYPTO_SHORT_DISABLED=1)
# ---------------------------------------------------------------------------


def test_kill_switch_blocks_crypto_short(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    reason = _crypto_short_gate_block_reason(_crypto_short_pick())
    assert reason == "crypto_short_killed_globally"


def test_kill_switch_blocks_via_active_gate(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert passes_active_gate(_crypto_short_pick()) is False


def test_kill_switch_blocks_via_smart_gate(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert passes_smart_gate(_crypto_short_pick()) is False


def test_kill_switch_does_not_block_crypto_long(monkeypatch) -> None:
    """CRYPTO LONG must pass the regime-gate even with kill-switch on."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert _crypto_short_gate_block_reason(_crypto_long_pick()) is None


def test_kill_switch_does_not_block_equity_short(monkeypatch) -> None:
    """EQUITY SHORT must pass — gate is CRYPTO-only."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert _crypto_short_gate_block_reason(_equity_short_pick()) is None


def test_kill_switch_does_not_block_forex_short(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert _crypto_short_gate_block_reason(_forex_short_pick()) is None


def test_kill_switch_does_not_block_commodity_short(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    assert _crypto_short_gate_block_reason(_commodity_short_pick()) is None


# ---------------------------------------------------------------------------
# 3. REGIME-GATE (CRYPTO_SHORT_REGIME_GATE_ENABLED=1)
# ---------------------------------------------------------------------------


def test_regime_gate_blocks_short_in_bull_regime(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    reason = _crypto_short_gate_block_reason(_crypto_short_pick())
    assert reason == "crypto_short_blocked_in_bull_regime"


def test_regime_gate_allows_short_in_bear_regime(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert _crypto_short_gate_block_reason(_crypto_short_pick()) is None


def test_regime_gate_allows_long_in_bull_regime(monkeypatch) -> None:
    """Even in bull regime with gate on, LONGs pass through."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert _crypto_short_gate_block_reason(_crypto_long_pick()) is None


def test_regime_gate_does_not_affect_equity_short(monkeypatch) -> None:
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: True)
    assert _crypto_short_gate_block_reason(_equity_short_pick()) is None


# ---------------------------------------------------------------------------
# 4. FLAG INTERACTION (kill-switch wins over regime-gate)
# ---------------------------------------------------------------------------


def test_both_flags_on_kill_switch_wins(monkeypatch) -> None:
    """When both flags on, kill-switch (more aggressive) takes precedence
    in the reason string returned, regardless of regime detection state."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)  # bear
    reason = _crypto_short_gate_block_reason(_crypto_short_pick())
    # Kill-switch wins — block, with the kill-switch reason
    assert reason == "crypto_short_killed_globally"


def test_both_flags_on_blocks_crypto_short_even_in_bear(monkeypatch) -> None:
    """In bear regime, regime-gate alone would NOT block — but kill-switch
    is also on, so the pick is still blocked (kill-switch ignores regime)."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    monkeypatch.setenv("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1")
    monkeypatch.setattr(qg, "_is_crypto_bull_regime", lambda: False)
    assert _crypto_short_gate_block_reason(_crypto_short_pick()) is not None


# ---------------------------------------------------------------------------
# 5. REGIME DETECTION SAFE FALLBACK (no crash on missing data)
# ---------------------------------------------------------------------------


def test_is_crypto_bull_regime_safe_fallback_on_missing_file(monkeypatch, tmp_path) -> None:
    """If regime_report.json doesn't exist, _is_crypto_bull_regime returns
    True (conservative default that blocks SHORTs when the gate is on)."""
    missing = str(tmp_path / "does_not_exist.json")
    monkeypatch.setattr(qg, "_REGIME_REPORT_PATH", missing)
    monkeypatch.setattr(qg, "_REGIME_CACHE", {"mtime": 0.0, "is_bull": True})
    # Must not raise
    result = qg._is_crypto_bull_regime()
    assert result is True


def test_is_crypto_bull_regime_reads_bull_label(monkeypatch, tmp_path) -> None:
    p = tmp_path / "regime_report.json"
    p.write_text('{"regime": "BULL", "btc_trend": "UP"}', encoding="utf-8")
    monkeypatch.setattr(qg, "_REGIME_REPORT_PATH", str(p))
    monkeypatch.setattr(qg, "_REGIME_CACHE", {"mtime": 0.0, "is_bull": False})
    assert qg._is_crypto_bull_regime() is True


def test_is_crypto_bull_regime_reads_bear_label(monkeypatch, tmp_path) -> None:
    p = tmp_path / "regime_report.json"
    p.write_text('{"regime": "BEAR", "btc_trend": "DOWN"}', encoding="utf-8")
    monkeypatch.setattr(qg, "_REGIME_REPORT_PATH", str(p))
    monkeypatch.setattr(qg, "_REGIME_CACHE", {"mtime": 0.0, "is_bull": True})
    assert qg._is_crypto_bull_regime() is False


def test_is_crypto_bull_regime_choppy_treated_as_non_bull(monkeypatch, tmp_path) -> None:
    """CHOPPY/RANGING regimes ÔåÆ NOT bull ÔåÆ regime-gate allows SHORTs."""
    p = tmp_path / "regime_report.json"
    p.write_text('{"regime": "CHOPPY", "btc_trend": "FLAT"}', encoding="utf-8")
    monkeypatch.setattr(qg, "_REGIME_REPORT_PATH", str(p))
    monkeypatch.setattr(qg, "_REGIME_CACHE", {"mtime": 0.0, "is_bull": True})
    assert qg._is_crypto_bull_regime() is False


# ---------------------------------------------------------------------------
# 6. SELL alias (treated as SHORT)
# ---------------------------------------------------------------------------


def test_kill_switch_blocks_sell_alias(monkeypatch) -> None:
    """SELL is the legacy alias for SHORT — must be blocked too."""
    _clear_short_flags(monkeypatch)
    monkeypatch.setenv("CRYPTO_SHORT_DISABLED", "1")
    pick = _crypto_short_pick()
    pick["direction"] = "SELL"
    assert _crypto_short_gate_block_reason(pick) == "crypto_short_killed_globally"

"""Regression tests for the 2026-04-28 CRYPTO RSI-4h killzone disable
+ CRYPTO_BANNED_SYMBOLS expansion (DOGEUSDT/LTCUSDT/TONUSDT).

Background — see `reports/crypto_rsi4h_killzone_review_2026_04_28.md`:
    - `technical_rsi_4h` is a writer artifact stamped per-symbol per regen
      (`audit_trail/dashboard_generator.py:12757`). 850 CRYPTO closed picks
      had only 28 unique RSI values → killzone was operationally a symbol
      blocklist, not an RSI filter.
    - `[40, 60)` window false-rejected NEAR (PF 2.02), INJ (PF 2.69), APT
      (PF 1.18), LINK (PF 1.14) and missed the truly bad bin `[60, 65)`
      (WR 23.5%, PF 0.55, n=17).
    - Decision: DISABLE the RSI-4h check; expand CRYPTO_BANNED_SYMBOLS with
      symbols hitting the empirical PF<0.95, n>=20 threshold instead.
    - Env-var override (HF_GATE_CRYPTO_RSI4H_KILL_LO/HI) preserved for
      shadow-mode tuning.

Companion to `tests/test_hedge_fund_quality_gate.py::TestCryptoRSI4hKillzone`,
which was updated in this PR to reflect the new disabled-by-default behavior.
"""
from __future__ import annotations

import importlib

import pytest

from alpha_engine import hedge_fund_quality_gate
from alpha_engine.hedge_fund_quality_gate import (
    CRYPTO_BANNED_SYMBOLS,
    CRYPTO_RSI4H_KILL_HI,
    CRYPTO_RSI4H_KILL_LO,
    passes_hedge_fund_gate,
)


def _p(**kwargs):
    base = {
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "strategy": "ok",
        "signal_type": "LONG",
        "confidence": 0.75,
    }
    base.update(kwargs)
    return base


class TestRSI4hKillzoneDisabledByDefault:
    """The previous [40, 60) killzone must no longer reject by default."""

    def test_killzone_constants_default_to_empty_interval(self):
        # `LO <= rsi < HI` with LO=HI=0 is the empty interval — i.e. disabled.
        assert CRYPTO_RSI4H_KILL_LO == 0.0
        assert CRYPTO_RSI4H_KILL_HI == 0.0

    def test_rsi_50_previously_rejected_now_passes(self):
        # RSI=50 sat squarely in the old [40, 60) killzone → was always rejected.
        # Post-fix it must pass on a non-banned symbol with neutral confidence.
        ok, reason = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=50.0,
        ))
        assert ok, f"RSI=50 should pass post-fix; got reject: {reason}"

    def test_rsi_45_previously_rejected_now_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=45.0,
        ))
        assert ok

    def test_rsi_at_old_lower_bound_now_passes(self):
        # 40.0 was rejected (lo-inclusive). Now passes.
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=40.0,
        ))
        assert ok

    def test_rsi_just_below_old_upper_bound_now_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=59.9,
        ))
        assert ok


class TestCryptoBannedSymbolsExpansion:
    """DOGEUSDT/LTCUSDT/TONUSDT must reject; non-banned CRYPTO symbols must pass."""

    def test_dogeusdt_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(symbol="DOGEUSDT"))
        assert not ok
        assert "DOGEUSDT" in reason

    def test_ltcusdt_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(symbol="LTCUSDT"))
        assert not ok
        assert "LTCUSDT" in reason

    def test_tonusdt_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(symbol="TONUSDT"))
        assert not ok
        assert "TONUSDT" in reason

    def test_btcusdt_still_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(symbol="BTCUSDT", confidence=0.75))
        assert ok

    def test_nearusdt_still_passes(self):
        # NEARUSDT was a false-reject candidate cited in the review (PF 2.02).
        ok, _ = passes_hedge_fund_gate(_p(symbol="NEARUSDT", confidence=0.75))
        assert ok

    def test_membership_constants(self):
        for sym in ("DOGEUSDT", "LTCUSDT", "TONUSDT"):
            assert sym in CRYPTO_BANNED_SYMBOLS, f"{sym} missing from CRYPTO_BANNED_SYMBOLS"


class TestEnvVarOverridePreserved:
    """HF_GATE_CRYPTO_RSI4H_KILL_LO/HI must still let a shadow-tuner re-enable the killzone."""

    def test_env_override_re_enables_killzone(self, monkeypatch):
        monkeypatch.setenv("HF_GATE_CRYPTO_RSI4H_KILL_LO", "40")
        monkeypatch.setenv("HF_GATE_CRYPTO_RSI4H_KILL_HI", "60")
        # Constants are read at module import time, so reload to pick up env.
        reloaded = importlib.reload(hedge_fund_quality_gate)
        try:
            assert reloaded.CRYPTO_RSI4H_KILL_LO == 40.0
            assert reloaded.CRYPTO_RSI4H_KILL_HI == 60.0
            ok, reason = reloaded.passes_hedge_fund_gate({
                "asset_class": "CRYPTO",
                "symbol": "BTCUSDT",
                "strategy": "ok",
                "signal_type": "LONG",
                "confidence": 0.75,
                "technical_rsi_4h": 50.0,
            })
            assert not ok, "env-override should re-enable the killzone"
            assert "killzone" in reason.lower()
        finally:
            # Restore default-disabled state for downstream tests.
            monkeypatch.delenv("HF_GATE_CRYPTO_RSI4H_KILL_LO", raising=False)
            monkeypatch.delenv("HF_GATE_CRYPTO_RSI4H_KILL_HI", raising=False)
            importlib.reload(hedge_fund_quality_gate)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])

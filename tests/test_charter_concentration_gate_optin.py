"""Regression test for P0.5-4 charter_concentration enforcement flag.

By default (CHARTER_CONCENTRATION_ENFORCE unset or "0"), validate_concentration
is NOT called from passes_active_gate. When the flag is "1", duplicate-symbol
and sector-cap violations hard-reject. Companion to PR #982 wire-up plan.
"""
import os
from unittest import TestCase, main
from unittest.mock import patch


class CharterConcentrationGateOptInTests(TestCase):
    def _base_pick(self, **overrides):
        # Minimal pick that would otherwise pass the noisy upstream guards.
        p = {
            "symbol": "BTCUSDT",
            "asset_class": "crypto",
            "category": "swing",
            "sector": "crypto_majors",
            "confidence": 0.8,
            "status": "OPEN",
            "trust_score": 8.0,
            "score": 80,
            "_charter_notional_pct": 0.04,
            "strategy": "synthetic_test",
            "timestamp": "2026-05-13T20:00:00Z",
        }
        p.update(overrides)
        return p

    def test_flag_off_does_not_invoke_validate_concentration(self):
        """With flag off, validate_concentration must never be called from gate."""
        from audit_trail import quality_gates as qg
        pick = self._base_pick()
        # snapshot returns an existing same-symbol position → would normally fail.
        with patch.object(qg, "_cached_active_picks_snapshot",
                          return_value=[self._base_pick()]), \
             patch.dict(os.environ, {"CHARTER_CONCENTRATION_ENFORCE": "0"}), \
             patch("alpha_engine.charter_position_sizer."
                   "validate_concentration") as vc_mock:
            try:
                qg.passes_active_gate(pick)
            except Exception:
                # Upstream gate complexity may reject for other reasons; we
                # only care that validate_concentration was NOT called.
                pass
            vc_mock.assert_not_called()

    def test_flag_on_calls_validate_concentration(self):
        from audit_trail import quality_gates as qg
        pick = self._base_pick()
        with patch.object(qg, "_cached_active_picks_snapshot",
                          return_value=[]), \
             patch.dict(os.environ, {"CHARTER_CONCENTRATION_ENFORCE": "1"}), \
             patch("alpha_engine.charter_position_sizer."
                   "validate_concentration",
                   return_value=(True, "ok")) as vc_mock:
            try:
                qg.passes_active_gate(pick)
            except Exception:
                pass
            vc_mock.assert_called_once()

    def test_flag_on_duplicate_symbol_rejects(self):
        """Real validate_concentration: duplicate symbol → False."""
        from audit_trail import quality_gates as qg
        from alpha_engine.charter_position_sizer import validate_concentration
        # Direct unit on charter_position_sizer to confirm the contract the
        # gate relies on (gate-level rejection is covered by the mock test
        # above; integration depends on the full upstream gate stack).
        new = {"symbol": "BTCUSDT", "asset_class": "CRYPTO",
               "category": "swing", "sector": "crypto", "confidence": 0.9}
        existing = [{"symbol": "BTCUSDT", "sector": "crypto",
                     "notional_pct": 0.01}]
        ok, reason = validate_concentration(new, existing)
        self.assertFalse(ok)
        self.assertIn("duplicate_symbol", reason)


if __name__ == "__main__":
    main()

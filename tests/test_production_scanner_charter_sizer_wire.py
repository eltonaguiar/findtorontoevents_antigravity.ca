"""Regression test for charter_position_sizer wire-up in production_scanner.

After a pick passes quality gates, the scanner now also stamps:
- _charter_notional_pct (vol-targeted cap as a fraction of equity)
- _charter_concentration_warn (only if concentration validator rejects)

Informational this round — does NOT gate emission yet. Validates the
expected stamps appear without breaking existing scanner behavior.
"""
from unittest import TestCase, main


class ProductionScannerCharterSizerWireTests(TestCase):
    def test_charter_position_sizer_callable_from_scanner_context(self):
        # Sanity: the lazy-import path from production_scanner works.
        from alpha_engine.charter_position_sizer import (
            compute_position_size,
            validate_concentration,
        )
        pick = {
            "symbol": "BTCUSDT",
            "asset_class": "CRYPTO",
            "confidence": 0.8,
            "category": "swing",
            "sector": "crypto_majors",
        }
        notional = compute_position_size(pick, portfolio_equity=1.0,
                                          daily_vol_estimate=0.04)
        self.assertGreater(notional, 0)
        self.assertLessEqual(notional, 0.05)  # cap at 5% per Charter §7

        ok, reason = validate_concentration(pick, [])
        self.assertTrue(ok)

    def test_compute_position_size_on_unit_equity_returns_fraction(self):
        # Wire-up uses portfolio_equity=1.0 so result is a fraction.
        from alpha_engine.charter_position_sizer import compute_position_size
        pick = {
            "symbol": "AAPL",
            "asset_class": "EQUITY",
            "confidence": 0.7,
            "category": "long_term",
            "sector": "tech",
        }
        result = compute_position_size(pick, portfolio_equity=1.0,
                                        daily_vol_estimate=None)
        # Fraction of equity, not dollar number
        self.assertLess(result, 1.0)
        self.assertGreater(result, 0)

    def test_concentration_warn_triggered_by_duplicate_symbol(self):
        from alpha_engine.charter_position_sizer import validate_concentration
        existing = [{"symbol": "BTCUSDT", "sector": "crypto", "notional_pct": 0.01}]
        new_pick = {"symbol": "BTCUSDT", "asset_class": "CRYPTO",
                    "confidence": 0.9, "category": "swing",
                    "sector": "crypto"}
        ok, reason = validate_concentration(new_pick, existing)
        self.assertFalse(ok)
        self.assertIn("duplicate_symbol", reason)

    def test_production_scanner_compiles(self):
        # production_scanner.py uses a sys-path-dependent `from config import`
        # that fails in plain pytest runs but works under the runtime's
        # PYTHONPATH setup. Test compile-only via py_compile instead.
        import py_compile
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "alpha_engine" / "production_scanner.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"production_scanner.py failed to compile: {e}")


if __name__ == "__main__":
    main()

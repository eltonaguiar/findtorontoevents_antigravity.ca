"""Smoke tests for tools/new_strategies_emitter.py.

Tests:
1. Module imports cleanly.
2. run(dry_run=True) returns a dict with a 'picks' list.
3. Output picks (when present) have required fields.
4. Emitter is disabled by NEW_STRATS_RUNNER_ENABLED=0.
"""
import os
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))


class TestNewStrategiesEmitterImport(unittest.TestCase):
    def test_import(self):
        import new_strategies_emitter  # noqa: F401
        self.assertTrue(True)

    def test_module_has_run_and_main(self):
        import new_strategies_emitter as m
        self.assertTrue(callable(m.run))
        self.assertTrue(callable(m.main))


class TestNewStrategiesEmitterDryRun(unittest.TestCase):
    """Dry-run test: uses mocked OHLCV data to avoid yfinance network calls."""

    def _make_fake_ohlcv(self):
        """Return a minimal {symbol: DataFrame} dict for offline testing."""
        try:
            import pandas as pd
            import numpy as np
            n = 300
            idx = pd.date_range("2025-01-01", periods=n, freq="D")
            base = 100.0
            close = pd.Series(base + np.cumsum(np.random.randn(n) * 0.5), index=idx)
            volume = pd.Series(np.random.randint(1_000_000, 5_000_000, n), index=idx)
            df = pd.DataFrame({
                "Open": close * 0.999,
                "High": close * 1.005,
                "Low": close * 0.995,
                "Close": close,
                "Volume": volume,
            })
            return df
        except ImportError:
            return None

    def test_dry_run_returns_dict_with_picks_list(self):
        import new_strategies_emitter as m

        fake_df = self._make_fake_ohlcv()
        if fake_df is None:
            self.skipTest("pandas not available")

        # Patch _load_ohlcv to return fake data instead of hitting the network
        all_syms = m.EQUITY_SYMBOLS + m.COMMODITY_SYMBOLS
        fake_data = {sym: fake_df.copy() for sym in all_syms}

        original_load = m._load_ohlcv
        m._load_ohlcv = lambda syms, period="6mo": {s: fake_df.copy() for s in syms}
        try:
            result = m.run(dry_run=True)
        finally:
            m._load_ohlcv = original_load

        self.assertIsInstance(result, dict)
        self.assertIn("picks", result)
        self.assertIsInstance(result["picks"], list)

    def test_dry_run_picks_have_required_fields(self):
        import new_strategies_emitter as m

        fake_df = self._make_fake_ohlcv()
        if fake_df is None:
            self.skipTest("pandas not available")

        original_load = m._load_ohlcv
        m._load_ohlcv = lambda syms, period="6mo": {s: fake_df.copy() for s in syms}
        try:
            result = m.run(dry_run=True)
        finally:
            m._load_ohlcv = original_load

        required = {
            "symbol", "strategy", "source_system", "asset_class",
            "direction", "entry_price", "take_profit", "stop_loss",
            "confidence", "status", "timestamp", "entry_time",
        }
        for pick in result["picks"]:
            missing = required - set(pick.keys())
            self.assertEqual(missing, set(), f"Pick missing fields: {missing}")

    def test_disabled_by_env_var(self):
        import new_strategies_emitter as m

        original = os.environ.get("NEW_STRATS_RUNNER_ENABLED")
        os.environ["NEW_STRATS_RUNNER_ENABLED"] = "0"
        try:
            result = m.run(dry_run=True)
        finally:
            if original is None:
                os.environ.pop("NEW_STRATS_RUNNER_ENABLED", None)
            else:
                os.environ["NEW_STRATS_RUNNER_ENABLED"] = original

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["picks"], [])


if __name__ == "__main__":
    unittest.main()

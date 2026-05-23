"""
Tests for audit_trail.regime_filter — B13 per-asset-class regime filter sidecar.

Uses patch.dict(os.environ, ...) and unittest.mock.mock_open to avoid
sys.modules poisoning that caused 3.11/3.12 divergence in prior B13 PRs.
"""

from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import mock_open, patch

from audit_trail.regime_filter import passes_regime_filter


def _fresh_report(regime: str = "BULL") -> str:
    ts = datetime.now(timezone.utc).isoformat()
    return json.dumps({
        "regime": regime,
        "regime_last_checked": ts,
        "timestamp": ts,
    })


def _stale_report(regime: str = "BULL") -> str:
    ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    return json.dumps({
        "regime": regime,
        "regime_last_checked": ts,
        "timestamp": ts,
    })


def _crypto_long() -> dict:
    return {"id": "t1", "asset_class": "CRYPTO", "direction": "LONG"}


def _crypto_short() -> dict:
    return {"id": "t2", "asset_class": "CRYPTO", "direction": "SHORT"}


class TestRegimeFilterDisabledByDefault(unittest.TestCase):
    """Master switch off → always None."""

    def test_master_flag_off_returns_none(self):
        with patch.dict(os.environ, {"REGIME_FILTER_ENABLED": "0"}):
            self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_master_flag_missing_returns_none(self):
        env = {k: v for k, v in os.environ.items() if k != "REGIME_FILTER_ENABLED"}
        with patch.dict(os.environ, env, clear=True):
            self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_crypto_flag_off_returns_none(self):
        with patch.dict(os.environ, {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "0",
            "REGIME_FILTER_LOG_ONLY": "0",
        }):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))


class TestRegimeFilterLogOnlyMode(unittest.TestCase):
    """LOG_ONLY=1 → never blocks, only logs."""

    def test_log_only_no_block_for_crypto_short_in_bull(self):
        with patch.dict(os.environ, {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
            "REGIME_FILTER_LOG_ONLY": "1",
        }):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_log_only_default_is_1(self):
        """REGIME_FILTER_LOG_ONLY defaults to '1' — first activation is shadow-only."""
        env = {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
        }
        # Remove LOG_ONLY so we test the default
        env2 = {k: v for k, v in {**os.environ, **env}.items()
                if k != "REGIME_FILTER_LOG_ONLY"}
        with patch.dict(os.environ, env2, clear=True):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    # LOG_ONLY default = "1" → no block even for SHORT in BULL
                    self.assertIsNone(passes_regime_filter(_crypto_short()))


class TestRegimeFilterEnforceMode(unittest.TestCase):
    """LOG_ONLY=0 + ENABLED=1 + CRYPTO_ENABLED=1 → enforce matrix."""

    def _env(self):
        return {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
            "REGIME_FILTER_LOG_ONLY": "0",
        }

    def test_crypto_short_blocked_in_bull(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    result = passes_regime_filter(_crypto_short())
                    self.assertIsNotNone(result)
                    self.assertIn("BULL", result)

    def test_crypto_long_allowed_in_bull(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(_crypto_long()))

    def test_crypto_short_allowed_in_bear(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BEAR"))):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_crypto_long_blocked_in_bear(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BEAR"))):
                    result = passes_regime_filter(_crypto_long())
                    self.assertIsNotNone(result)
                    self.assertIn("BEAR", result)

    def test_choppy_allows_both_directions(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("CHOPPY"))):
                    self.assertIsNone(passes_regime_filter(_crypto_long()))
                    self.assertIsNone(passes_regime_filter(_crypto_short()))


class TestRegimeFilterPermissiveFallbacks(unittest.TestCase):
    """Stale/missing file → permissive."""

    def _env(self):
        return {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
            "REGIME_FILTER_LOG_ONLY": "0",
        }

    def test_missing_regime_report_no_block(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = False
                self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_stale_regime_report_no_block(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_stale_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))

    def test_malformed_json_no_block(self):
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data="not-json")):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))


class TestRegimeFilterNonCryptoPermissive(unittest.TestCase):
    """Non-CRYPTO classes are always permissive (stubs)."""

    def _env(self):
        return {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
            "REGIME_FILTER_LOG_ONLY": "0",
        }

    def test_forex_short_in_bull_permissive(self):
        pick = {"id": "f1", "asset_class": "FOREX", "direction": "SHORT"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(pick))

    def test_equity_long_in_bear_permissive(self):
        pick = {"id": "e1", "asset_class": "EQUITY", "direction": "LONG"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BEAR"))):
                    self.assertIsNone(passes_regime_filter(pick))

    def test_commodity_short_in_bull_permissive(self):
        pick = {"id": "c1", "asset_class": "COMMODITY", "direction": "SHORT"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(pick))

    def test_bond_permissive(self):
        pick = {"id": "b1", "asset_class": "BOND", "direction": "LONG"}
        with patch.dict(os.environ, self._env()):
            self.assertIsNone(passes_regime_filter(pick))

    def test_etf_permissive(self):
        pick = {"id": "etf1", "asset_class": "ETF", "direction": "SHORT"}
        with patch.dict(os.environ, self._env()):
            self.assertIsNone(passes_regime_filter(pick))

    def test_unknown_class_permissive(self):
        pick = {"id": "u1", "asset_class": "UNKNOWN_XYZ", "direction": "SHORT"}
        with patch.dict(os.environ, self._env()):
            self.assertIsNone(passes_regime_filter(pick))


class TestRegimeFilterCryptoGateDisabled(unittest.TestCase):
    """Master ON, crypto sub-gate OFF → CRYPTO still permissive."""

    def test_crypto_sub_gate_off(self):
        with patch.dict(os.environ, {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "0",
            "REGIME_FILTER_LOG_ONLY": "0",
        }):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(_crypto_short()))


class TestRegimeFilterDirectionNormalization(unittest.TestCase):
    """BUY/SELL aliases and signal_type fallback."""

    def _env(self):
        return {
            "REGIME_FILTER_ENABLED": "1",
            "REGIME_FILTER_CRYPTO_ENABLED": "1",
            "REGIME_FILTER_LOG_ONLY": "0",
        }

    def test_sell_alias_blocked_in_bull(self):
        pick = {"id": "s1", "asset_class": "CRYPTO", "direction": "SELL"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    result = passes_regime_filter(pick)
                    self.assertIsNotNone(result)

    def test_buy_alias_allowed_in_bull(self):
        pick = {"id": "b1", "asset_class": "CRYPTO", "direction": "BUY"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    self.assertIsNone(passes_regime_filter(pick))

    def test_signal_type_fallback(self):
        pick = {"id": "s2", "asset_class": "CRYPTO", "signal_type": "SHORT"}
        with patch.dict(os.environ, self._env()):
            with patch("audit_trail.regime_filter._REGIME_REPORT_PATH") as mp:
                mp.exists.return_value = True
                with patch("builtins.open", mock_open(read_data=_fresh_report("BULL"))):
                    result = passes_regime_filter(pick)
                    self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()

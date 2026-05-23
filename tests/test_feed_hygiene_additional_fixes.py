"""Tests for the 2026-04-20 feed_hygiene hardening round:

  - Reject anonymous strategies at ingest
  - Default entry_time from timestamp fallbacks
  - Normalize FOREX pnl from decimal to percent form

Each test isolates one behavior.
"""
import unittest
from alpha_engine.feed_hygiene import (
    is_valid_active_pick,
    ensure_entry_time,
    normalize_forex_pnl,
)


def _base_pick(**overrides):
    """Minimum-viable active pick that passes all gates by default."""
    p = {
        "symbol": "BTCUSDT",
        "entry_price": 100.0,
        "direction": "LONG",
        "strategy": "some_real_strategy",
        "source_system": "alpha_engine",
        "status": "ACTIVE",
    }
    p.update(overrides)
    return p


class TestAnonymousStrategyRejection(unittest.TestCase):
    def test_empty_strategy_rejected(self):
        self.assertFalse(is_valid_active_pick(_base_pick(strategy="")))

    def test_whitespace_strategy_rejected(self):
        self.assertFalse(is_valid_active_pick(_base_pick(strategy="   ")))

    def test_unknown_strategy_rejected(self):
        self.assertFalse(is_valid_active_pick(_base_pick(strategy="unknown")))

    def test_none_sentinel_rejected(self):
        self.assertFalse(is_valid_active_pick(_base_pick(strategy="None")))

    def test_default_sentinel_rejected(self):
        self.assertFalse(is_valid_active_pick(_base_pick(strategy="default")))

    def test_self_named_rejected(self):
        # strategy == source_system is self-named (anonymous by convention)
        self.assertFalse(is_valid_active_pick(
            _base_pick(strategy="alpha_engine", source_system="alpha_engine")
        ))

    def test_real_strategy_accepted(self):
        self.assertTrue(is_valid_active_pick(_base_pick(strategy="rsi_bounce")))

    def test_case_insensitive_self_named_rejected(self):
        self.assertFalse(is_valid_active_pick(
            _base_pick(strategy="Alpha_Engine", source_system="alpha_engine")
        ))


class TestEnsureEntryTime(unittest.TestCase):
    def test_passthrough_when_entry_time_present(self):
        p = {"symbol": "X", "entry_time": "2026-04-20T12:00:00Z"}
        self.assertEqual(ensure_entry_time(p)["entry_time"], "2026-04-20T12:00:00Z")

    def test_fallback_from_timestamp(self):
        p = {"symbol": "X", "timestamp": "2026-04-20T12:00:00Z"}
        self.assertEqual(ensure_entry_time(p)["entry_time"], "2026-04-20T12:00:00Z")

    def test_fallback_from_created_at(self):
        p = {"symbol": "X", "created_at": "2026-04-20T12:00:00Z"}
        self.assertEqual(ensure_entry_time(p)["entry_time"], "2026-04-20T12:00:00Z")

    def test_fallback_prefers_timestamp_over_created_at(self):
        p = {
            "symbol": "X",
            "timestamp": "2026-04-20T12:00:00Z",
            "created_at": "2026-04-19T00:00:00Z",
        }
        self.assertEqual(ensure_entry_time(p)["entry_time"], "2026-04-20T12:00:00Z")

    def test_no_fallback_available_unchanged(self):
        p = {"symbol": "X"}
        self.assertNotIn("entry_time", ensure_entry_time(p))

    def test_empty_entry_time_triggers_fallback(self):
        p = {"symbol": "X", "entry_time": "", "timestamp": "2026-04-20T12:00:00Z"}
        self.assertEqual(ensure_entry_time(p)["entry_time"], "2026-04-20T12:00:00Z")

    def test_idempotent(self):
        p = {"symbol": "X", "timestamp": "2026-04-20T12:00:00Z"}
        once = ensure_entry_time(p)
        twice = ensure_entry_time(once)
        self.assertEqual(once["entry_time"], twice["entry_time"])


class TestNormalizeForexPnl(unittest.TestCase):
    def test_decimal_form_rescaled(self):
        p = {"symbol": "EURUSD=X", "pnl_pct": 0.0003}
        out = normalize_forex_pnl(p)
        self.assertAlmostEqual(out["pnl_pct"], 0.03, places=6)
        self.assertEqual(out["_pnl_pct_unit_normalized"], "decimal_to_percent")

    def test_negative_decimal_rescaled(self):
        p = {"symbol": "USDCHF=X", "pnl_pct": -0.012}
        out = normalize_forex_pnl(p)
        self.assertAlmostEqual(out["pnl_pct"], -1.2, places=6)

    def test_percent_form_passthrough(self):
        p = {"symbol": "EURUSD=X", "pnl_pct": 1.28}
        out = normalize_forex_pnl(p)
        self.assertEqual(out["pnl_pct"], 1.28)
        self.assertNotIn("_pnl_pct_unit_normalized", out)

    def test_non_forex_unchanged(self):
        p = {"symbol": "BTCUSDT", "pnl_pct": 0.0003}
        out = normalize_forex_pnl(p)
        self.assertEqual(out["pnl_pct"], 0.0003)

    def test_zero_pnl_unchanged(self):
        p = {"symbol": "EURUSD=X", "pnl_pct": 0}
        out = normalize_forex_pnl(p)
        self.assertEqual(out["pnl_pct"], 0)
        self.assertNotIn("_pnl_pct_unit_normalized", out)

    def test_none_pnl_unchanged(self):
        p = {"symbol": "EURUSD=X", "pnl_pct": None}
        out = normalize_forex_pnl(p)
        self.assertIsNone(out["pnl_pct"])

    def test_malformed_pnl_unchanged(self):
        p = {"symbol": "EURUSD=X", "pnl_pct": "not a number"}
        out = normalize_forex_pnl(p)
        self.assertEqual(out["pnl_pct"], "not a number")


if __name__ == "__main__":
    unittest.main()

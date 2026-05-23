"""Tests for the 2026-05-02 feed_hygiene schema-validation layer.

Covers:
  - validate_pick_schema rejects future timestamps
  - validate_pick_schema soft-fills ml_score / hf_conviction_tier / va_cohort_id
  - require_fields decorator rejects future-timestamp picks and soft-fills
  - sanitize_active_picks counts future_ts rejections without breaking
    well-formed input
"""
import unittest
from datetime import datetime, timedelta, timezone

from alpha_engine.feed_hygiene import (
    require_fields,
    sanitize_active_picks,
    validate_pick_schema,
)


def _base_pick(**overrides):
    p = {
        "symbol": "BTCUSDT",
        "entry_price": 100.0,
        "direction": "LONG",
        "strategy": "real_strategy",
        "source_system": "alpha_engine",
        "status": "ACTIVE",
    }
    p.update(overrides)
    return p


class ValidatePickSchemaTests(unittest.TestCase):
    def test_non_dict_rejected(self):
        self.assertIsNone(validate_pick_schema("not a dict"))
        self.assertIsNone(validate_pick_schema(None))

    def test_future_timestamp_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self.assertIsNone(validate_pick_schema(_base_pick(timestamp=future)))

    def test_past_timestamp_accepted(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = validate_pick_schema(_base_pick(timestamp=past))
        self.assertIsNotNone(result)

    def test_clock_skew_tolerance(self):
        # 30s in the future should be accepted (within 60s tolerance)
        soon = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        self.assertIsNotNone(validate_pick_schema(_base_pick(timestamp=soon)))

    def test_invalid_timestamp_tolerated(self):
        # Non-ISO timestamps should not crash; other gates handle staleness.
        result = validate_pick_schema(_base_pick(timestamp="not-a-date"))
        self.assertIsNotNone(result)

    def test_soft_fill_ml_score(self):
        p = _base_pick()
        p.pop("ml_score", None)
        result = validate_pick_schema(p)
        self.assertEqual(result["ml_score"], 0.0)

    def test_soft_fill_hf_conviction_tier(self):
        result = validate_pick_schema(_base_pick(hf_conviction_tier=None))
        self.assertEqual(result["hf_conviction_tier"], "UNKNOWN")

    def test_soft_fill_va_cohort_id(self):
        result = validate_pick_schema(_base_pick(va_cohort_id=""))
        self.assertEqual(result["va_cohort_id"], "none")

    def test_soft_fill_does_not_overwrite_existing(self):
        result = validate_pick_schema(_base_pick(ml_score=0.87))
        self.assertEqual(result["ml_score"], 0.87)

    def test_no_timestamp_field_accepted(self):
        # Missing timestamp is fine; only future timestamps are rejected.
        result = validate_pick_schema(_base_pick())
        self.assertIsNotNone(result)


class RequireFieldsDecoratorTests(unittest.TestCase):
    def test_decorator_rejects_future_ts(self):
        @require_fields()
        def passthrough(p):
            return p

        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        self.assertIsNone(passthrough(_base_pick(timestamp=future)))

    def test_decorator_soft_fills(self):
        @require_fields()
        def passthrough(p):
            return p

        result = passthrough(_base_pick())
        self.assertEqual(result["ml_score"], 0.0)
        self.assertEqual(result["hf_conviction_tier"], "UNKNOWN")

    def test_decorator_custom_soft_fields(self):
        @require_fields(soft={"custom_field": "DEFAULT"})
        def passthrough(p):
            return p

        result = passthrough(_base_pick())
        self.assertEqual(result["custom_field"], "DEFAULT")
        # baseline still applied
        self.assertEqual(result["ml_score"], 0.0)


class SanitizeActivePicksFutureTSTests(unittest.TestCase):
    def test_future_pick_dropped_and_counted(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        good = _base_pick()
        bad = _base_pick(symbol="ETHUSDT", timestamp=future)
        out = sanitize_active_picks([good, bad])
        symbols = [p["symbol"] for p in out]
        self.assertIn("BTCUSDT", symbols)
        self.assertNotIn("ETHUSDT", symbols)

    def test_well_formed_pick_passes(self):
        out = sanitize_active_picks([_base_pick()])
        self.assertEqual(len(out), 1)
        # Soft fills applied
        self.assertEqual(out[0]["ml_score"], 0.0)
        self.assertEqual(out[0]["hf_conviction_tier"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

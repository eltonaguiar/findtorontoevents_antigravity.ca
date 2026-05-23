"""Regression test for the COT publication-lag guard.

CFTC releases the COT report Friday ~3:30pm ET covering the prior Tuesday's
settlement. Emitting a pick that uses Tuesday-settled data BEFORE that Friday
release is look-ahead bias. The fix at alpha_engine/cot_positioning.py adds
a `_is_cot_row_public()` check that requires `COT_PUBLICATION_LAG_DAYS`
(default 3) between the report_date and the signal's `today` before the row
counts as public.

See reports/cot_timing_leakage_audit_2026-05-13.md for the audit trail.
"""
from datetime import datetime, timezone, timedelta
import unittest

from alpha_engine.cot_positioning import (
    _is_cot_row_public,
    COT_PUBLICATION_LAG_DAYS,
)


class CotPublicationLagTests(unittest.TestCase):
    def test_same_day_report_is_not_public(self):
        today = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_cot_row_public("2026-05-12", today=today))

    def test_one_day_old_report_is_not_public(self):
        today = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_cot_row_public("2026-05-12", today=today))

    def test_two_day_old_report_is_not_public(self):
        today = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_cot_row_public("2026-05-12", today=today))

    def test_three_day_old_report_is_public(self):
        # Tuesday-settled report becomes public at Friday ~3:30pm ET, which
        # is the conservative 3-calendar-day floor.
        today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_cot_row_public("2026-05-12", today=today))

    def test_old_report_is_public(self):
        today = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(_is_cot_row_public("2026-05-12", today=today))

    def test_malformed_date_is_not_public(self):
        today = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(_is_cot_row_public("not-a-date", today=today))
        self.assertFalse(_is_cot_row_public("", today=today))

    def test_lag_constant_default(self):
        # Anyone changing this without auditing the CFTC schedule should fail.
        self.assertEqual(COT_PUBLICATION_LAG_DAYS, 3)

    def test_custom_lag_override(self):
        today = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        # With lag_days=5, a 3-day-old report is still not public.
        self.assertFalse(_is_cot_row_public("2026-05-12", today=today, lag_days=5))
        # With lag_days=1, the same report becomes public.
        self.assertTrue(_is_cot_row_public("2026-05-12", today=today, lag_days=1))


if __name__ == "__main__":
    unittest.main()

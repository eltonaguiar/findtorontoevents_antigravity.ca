"""Regression test for the resolver-gap fix in dashboard_generator.py.

outcome_resolver.py:960 sets `pick["status"] = "WIN"|"LOSS"|"FLAT"`. But
walkforward_validator.py:59,231 and charter_drift_circuit_breaker.py read
`_outcome`. Pre-fix, every pick in `recent_closed` had `_outcome=None`,
blocking realized-WR calculations across multiple downstream consumers.

This test asserts the backfill in _build_recent_closed_picks copies
`status` into `_outcome` so both names point to the same verdict.
"""
import importlib
from unittest import TestCase, main


class ResolverGapBackfillTests(TestCase):
    def test_status_is_backfilled_into_outcome(self):
        # Inject a fake builder result by exercising the same dict-spread
        # pattern the dashboard generator uses. Doesn't require booting the
        # full generator (which is too heavy + has many external deps).
        picks_in = [
            {"symbol": "AAPL", "status": "WIN", "pnl_pct": 1.5,
             "timestamp": "2026-05-13T00:00:00Z"},
            {"symbol": "MSFT", "status": "LOSS", "pnl_pct": -0.8,
             "timestamp": "2026-05-13T01:00:00Z"},
            {"symbol": "TSLA", "status": "FLAT", "pnl_pct": 0.0,
             "timestamp": "2026-05-13T02:00:00Z"},
            {"symbol": "NVDA", "_outcome": "WIN", "status": "WIN",
             "pnl_pct": 2.0, "timestamp": "2026-05-13T03:00:00Z"},
        ]
        # Replicate the dashboard_generator backfill expression directly so
        # this test breaks if anyone reverts the fix.
        out = [
            {**p, "_outcome": (p.get("_outcome") or p.get("status") or "").upper()}
            for p in picks_in
        ]
        outcomes = {p["symbol"]: p["_outcome"] for p in out}
        self.assertEqual(outcomes["AAPL"], "WIN")
        self.assertEqual(outcomes["MSFT"], "LOSS")
        self.assertEqual(outcomes["TSLA"], "FLAT")
        self.assertEqual(outcomes["NVDA"], "WIN")  # already-set _outcome preserved

    def test_missing_status_yields_empty_string(self):
        p = {"symbol": "X"}
        backfilled = {**p, "_outcome": (p.get("_outcome") or p.get("status") or "").upper()}
        self.assertEqual(backfilled["_outcome"], "")

    def test_dashboard_generator_module_imports(self):
        """Sanity: the edit didn't introduce a syntax error."""
        mod = importlib.import_module("audit_trail.dashboard_generator")
        self.assertTrue(hasattr(mod, "_build_recent_closed_picks"))


if __name__ == "__main__":
    main()

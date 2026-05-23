"""Regression test for charter_drift_circuit_breaker wire in dashboard_generator.

The dashboard generator stamps a `circuit_breaker` dict on each
`asset_class_health[ac]` entry and overrides `sizing_allowed=False` when the
30-day realized WR drops more than 2 sigma below the walk-forward baseline.

We test the wire-up logic by directly invoking `evaluate_all_classes` and
applying the same stamp + override pattern used in dashboard_generator.py.
This avoids running the full generator (forbidden per CLAUDE.md) while still
guarding the contract.
"""
from datetime import datetime, timedelta, timezone
from unittest import TestCase, main


def _stamp(asset_class_health, recent_closed, wf_by_class):
    """Mirror of the dashboard_generator wire block."""
    from alpha_engine.charter_drift_circuit_breaker import evaluate_all_classes
    verdicts = evaluate_all_classes(recent_closed, wf_by_class)
    for ac, v in verdicts.items():
        if ac in asset_class_health:
            asset_class_health[ac]["circuit_breaker"] = {
                "breached": v["breached"],
                "reason": v["reason"],
                "realized_wr_30d": v["realized_wr_30d"],
                "realized_n_30d": v["realized_n_30d"],
            }
            if v["breached"]:
                asset_class_health[ac]["sizing_allowed"] = False
    return verdicts


class DashboardDriftBreakerWireTests(TestCase):
    def test_breach_overrides_sizing_allowed(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=1)).isoformat()
        # 40 losses, 0 wins → realized WR 0% — well below 60% - 2*5% = 50%.
        recent_closed = [
            {"asset_class": "CRYPTO", "_outcome": "LOSS", "timestamp": ts}
            for _ in range(40)
        ]
        wf_by_class = {"CRYPTO": {"oos_wr": 60.0, "oos_wr_std": 5.0}}
        ach = {"CRYPTO": {"sizing_allowed": True}}

        _stamp(ach, recent_closed, wf_by_class)

        self.assertIn("circuit_breaker", ach["CRYPTO"])
        self.assertTrue(ach["CRYPTO"]["circuit_breaker"]["breached"])
        self.assertFalse(ach["CRYPTO"]["sizing_allowed"])
        self.assertEqual(ach["CRYPTO"]["circuit_breaker"]["realized_n_30d"], 40)

    def test_ok_does_not_flip_sizing(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=1)).isoformat()
        # 24 wins, 16 losses → 60% WR, equal to baseline.
        recent_closed = (
            [{"asset_class": "EQUITY", "_outcome": "WIN", "timestamp": ts}] * 24
            + [{"asset_class": "EQUITY", "_outcome": "LOSS", "timestamp": ts}] * 16
        )
        wf_by_class = {"EQUITY": {"oos_wr": 60.0, "oos_wr_std": 5.0}}
        ach = {"EQUITY": {"sizing_allowed": True}}

        _stamp(ach, recent_closed, wf_by_class)

        self.assertFalse(ach["EQUITY"]["circuit_breaker"]["breached"])
        self.assertTrue(ach["EQUITY"]["sizing_allowed"])

    def test_cold_start_does_not_flip_sizing(self):
        # Thin sample (n<30) → cold_start, no flip even if WR is 0%.
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=1)).isoformat()
        recent_closed = [
            {"asset_class": "BOND", "_outcome": "LOSS", "timestamp": ts}
            for _ in range(5)
        ]
        wf_by_class = {"BOND": {"oos_wr": 55.0, "oos_wr_std": 5.0}}
        ach = {"BOND": {"sizing_allowed": True}}

        _stamp(ach, recent_closed, wf_by_class)

        self.assertFalse(ach["BOND"]["circuit_breaker"]["breached"])
        self.assertTrue(ach["BOND"]["sizing_allowed"])
        self.assertIn("cold_start", ach["BOND"]["circuit_breaker"]["reason"])

    def test_missing_class_is_skipped(self):
        # Class present in walkforward but NOT in asset_class_health → no key error.
        recent_closed: list[dict] = []
        wf_by_class = {"FUTURES": {"oos_wr": 50.0, "oos_wr_std": 5.0}}
        ach: dict = {}  # empty health map

        # Should not raise.
        _stamp(ach, recent_closed, wf_by_class)
        self.assertEqual(ach, {})


if __name__ == "__main__":
    main()

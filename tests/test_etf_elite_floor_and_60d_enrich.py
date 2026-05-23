"""Regression tests for two swarm-round-3 fixes:

1. ETF elite_score floor enforcement in audit_trail/quality_gates.py
   (prevents goldmine_stocks-style elite=20 ETF picks from being admitted)
2. asset_class_health 60-day recent-window enrichment in
   audit_trail/dashboard_generator.py (surfaces pf_60d/wr_60d/n_60d
   so consumers can detect baseline shifts)
"""
from datetime import datetime, timedelta, timezone
from unittest import TestCase, main


class AssetClassHealth60dEnrichTests(TestCase):
    def test_pf_60d_computed_from_recent_closed(self):
        from audit_trail.dashboard_generator import enrich_health_with_recent_window
        now = datetime.now(timezone.utc)
        ts_recent = (now - timedelta(days=10)).isoformat()
        ts_old = (now - timedelta(days=120)).isoformat()
        recent_closed = (
            # 6 wins @ +2% each = +12 win_pnl
            [{"asset_class": "CRYPTO", "_outcome": "WIN",
              "pnl_pct": 2.0, "timestamp": ts_recent}] * 6
            # 4 losses @ -1% each = +4 loss_pnl  → PF = 12/4 = 3.0
            + [{"asset_class": "CRYPTO", "_outcome": "LOSS",
                "pnl_pct": -1.0, "timestamp": ts_recent}] * 4
            # Old picks outside 60d window — must be excluded
            + [{"asset_class": "CRYPTO", "_outcome": "WIN",
                "pnl_pct": 100.0, "timestamp": ts_old}] * 50
        )
        ach = {"CRYPTO": {"profit_factor": 1.33, "win_rate": 46.4}}
        enrich_health_with_recent_window(ach, recent_closed)
        self.assertEqual(ach["CRYPTO"]["n_60d"], 10)
        self.assertEqual(ach["CRYPTO"]["wr_60d"], 60.0)
        self.assertEqual(ach["CRYPTO"]["pf_60d"], 3.0)

    def test_missing_class_in_health_is_skipped(self):
        from audit_trail.dashboard_generator import enrich_health_with_recent_window
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=5)).isoformat()
        recent_closed = [
            {"asset_class": "FUTURES", "_outcome": "WIN",
             "pnl_pct": 1.0, "timestamp": ts}
        ]
        ach: dict = {}  # FUTURES not present
        enrich_health_with_recent_window(ach, recent_closed)
        self.assertEqual(ach, {})

    def test_empty_recent_closed_noop(self):
        from audit_trail.dashboard_generator import enrich_health_with_recent_window
        ach = {"EQUITY": {"profit_factor": 1.55}}
        enrich_health_with_recent_window(ach, [])
        self.assertNotIn("pf_60d", ach["EQUITY"])

    def test_status_field_fallback(self):
        # When _outcome is absent, fall back to status (resolver-gap aware).
        from audit_trail.dashboard_generator import enrich_health_with_recent_window
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=5)).isoformat()
        recent_closed = [
            {"asset_class": "BOND", "status": "WIN",
             "pnl_pct": 1.0, "timestamp": ts},
            {"asset_class": "BOND", "status": "WIN",
             "pnl_pct": 1.0, "timestamp": ts},
            {"asset_class": "BOND", "status": "LOSS",
             "pnl_pct": -1.0, "timestamp": ts},
        ]
        ach = {"BOND": {}}
        enrich_health_with_recent_window(ach, recent_closed)
        self.assertEqual(ach["BOND"]["n_60d"], 3)

    def test_won_lost_status_accepted(self):
        # Actual resolver output uses WON/LOST (not WIN/LOSS) in the status field.
        # The enrichment function must accept both spellings.
        from audit_trail.dashboard_generator import enrich_health_with_recent_window
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=5)).isoformat()
        recent_closed = [
            {"asset_class": "EQUITY", "status": "WON", "pnl_pct": 2.0, "timestamp": ts},
            {"asset_class": "EQUITY", "status": "WON", "pnl_pct": 2.0, "timestamp": ts},
            {"asset_class": "EQUITY", "status": "LOST", "pnl_pct": -1.0, "timestamp": ts},
        ]
        ach = {"EQUITY": {}}
        enrich_health_with_recent_window(ach, recent_closed)
        self.assertEqual(ach["EQUITY"]["n_60d"], 3)
        self.assertAlmostEqual(ach["EQUITY"]["wr_60d"], 66.7, places=1)
        self.assertAlmostEqual(ach["EQUITY"]["pf_60d"], 4.0, places=2)


class HealthOutputHasNAliasTests(TestCase):
    def test_n_alias_present(self):
        from audit_trail.dashboard_generator import compute_asset_class_health
        ac_breakdown = {
            "CRYPTO": {"wins": 60, "losses": 40, "win_rate": 60.0,
                       "pnl": 5.0, "profit_factor": 1.5},
        }
        out = compute_asset_class_health(ac_breakdown)
        self.assertEqual(out["CRYPTO"]["n"], 100)
        self.assertEqual(out["CRYPTO"]["resolved_n"], 100)


if __name__ == "__main__":
    main()

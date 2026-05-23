"""Tests for charter_risk_budget cross-class allocator (P0.5-6)."""
from unittest import TestCase, main


class CharterRiskBudgetTests(TestCase):
    def test_within_cap_all_approved(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        picks = [
            {"symbol": "BTCUSDT", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.05, "confidence": 0.9},
            {"symbol": "ETHUSDT", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.05, "confidence": 0.8},
        ]
        approved, rejected = allocate_picks(picks)
        self.assertEqual(len(approved), 2)
        self.assertEqual(rejected, [])

    def test_class_cap_rejects_overflow(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        # CRYPTO cap = 0.25 by default. Three picks at 0.10 each = 0.30 > cap.
        picks = [
            {"symbol": f"COIN{i}", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.10,
             "confidence": 0.9 - 0.01 * i}
            for i in range(3)
        ]
        approved, rejected = allocate_picks(picks)
        self.assertEqual(len(approved), 2)
        self.assertEqual(len(rejected), 1)
        self.assertIn("class_cap_exceeded", rejected[0][1])

    def test_higher_confidence_wins(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        # FOREX cap = 0.15. Two picks at 0.10. Higher-confidence wins.
        picks = [
            {"symbol": "EURUSD", "asset_class": "FOREX",
             "_charter_notional_pct": 0.10, "confidence": 0.6},
            {"symbol": "GBPUSD", "asset_class": "FOREX",
             "_charter_notional_pct": 0.10, "confidence": 0.9},
        ]
        approved, rejected = allocate_picks(picks)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["symbol"], "GBPUSD")
        self.assertEqual(rejected[0][0]["symbol"], "EURUSD")

    def test_unknown_class_uses_fallback(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        # MEME has no entry → fallback 0.10. Pick at 0.15 exceeds.
        picks = [
            {"symbol": "DOGE", "asset_class": "MEME",
             "_charter_notional_pct": 0.15, "confidence": 0.9},
        ]
        approved, rejected = allocate_picks(picks)
        self.assertEqual(approved, [])
        self.assertEqual(len(rejected), 1)

    def test_no_size_stamp_rejected(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        picks = [{"symbol": "AAPL", "asset_class": "EQUITY",
                  "confidence": 0.8}]  # no _charter_notional_pct
        approved, rejected = allocate_picks(picks)
        self.assertEqual(approved, [])
        self.assertEqual(rejected[0][1], "no_size_stamp")

    def test_independent_class_budgets(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        # CRYPTO 0.20 + EQUITY 0.35 should both pass (each class within its
        # own cap; cross-class total > 100% is allowed by design).
        picks = [
            {"symbol": "BTC", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.20, "confidence": 0.9},
            {"symbol": "AAPL", "asset_class": "EQUITY",
             "_charter_notional_pct": 0.35, "confidence": 0.9},
        ]
        approved, rejected = allocate_picks(picks)
        self.assertEqual(len(approved), 2)
        self.assertEqual(rejected, [])

    def test_summarize_allocation(self):
        from alpha_engine.charter_risk_budget import (
            allocate_picks, summarize_allocation,
        )
        picks = [
            {"symbol": "BTC", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.10, "confidence": 0.9},
            {"symbol": "ETH", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.10, "confidence": 0.8},
            {"symbol": "AAPL", "asset_class": "EQUITY",
             "_charter_notional_pct": 0.05, "confidence": 0.7},
        ]
        approved, rejected = allocate_picks(picks)
        summary = summarize_allocation(approved, rejected)
        self.assertEqual(summary["approved_n"], 3)
        self.assertEqual(summary["rejected_n"], 0)
        self.assertAlmostEqual(summary["by_class"]["CRYPTO"]["approved_notional"], 0.20)
        self.assertEqual(summary["by_class"]["EQUITY"]["approved_n"], 1)

    def test_custom_class_caps_override(self):
        from alpha_engine.charter_risk_budget import allocate_picks
        # Override CRYPTO to 0.50; same input should now approve all.
        picks = [
            {"symbol": f"COIN{i}", "asset_class": "CRYPTO",
             "_charter_notional_pct": 0.10, "confidence": 0.9 - 0.01 * i}
            for i in range(4)
        ]
        approved, rejected = allocate_picks(picks, class_caps={"CRYPTO": 0.50})
        self.assertEqual(len(approved), 4)


if __name__ == "__main__":
    main()

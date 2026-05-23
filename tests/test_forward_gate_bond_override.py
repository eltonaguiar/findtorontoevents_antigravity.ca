"""Regression test for FORWARD_GATE_OVERRIDES per-asset-class min_trades.

BR-2 from reports/bond_root_cause_2026-05-12.md: BOND uses min_trades=10
because bond ETF volatility is structurally lower than crypto/equity.
"""
from unittest import TestCase, main


class ForwardGateBondOverrideTests(TestCase):
    def test_bond_override_constant_present(self):
        from alpha_engine.forward_validator import FORWARD_GATE_OVERRIDES
        self.assertEqual(FORWARD_GATE_OVERRIDES.get("bond"), 10)

    def test_bond_pick_with_12_trades_passes(self):
        from alpha_engine import forward_validator as fv
        picks = [{
            "strategy": "bond_momentum",
            "source_system": "bond_agent",
            "asset_class": "bond",
            "confidence": 0.7,
        }]
        perf = {
            "bond_momentum": {
                "wins": 7, "losses": 5, "closed_picks": 12,
                "win_rate": 0.583,
            }
        }
        fv.annotate_picks_with_forward_gate(picks, perf)
        self.assertTrue(picks[0]["forward_validated"],
                        f"BOND should pass at n=12 with override=10; "
                        f"got reason={picks[0]['forward_status']}")

    def test_crypto_pick_with_12_trades_still_blocked(self):
        # Same n=12, but CRYPTO has no override → blocked by global=50.
        from alpha_engine import forward_validator as fv
        picks = [{
            "strategy": "crypto_breakout",
            "source_system": "crypto_agent",
            "asset_class": "crypto",
            "confidence": 0.7,
        }]
        perf = {
            "crypto_breakout": {
                "wins": 7, "losses": 5, "closed_picks": 12,
                "win_rate": 0.583,
            }
        }
        fv.annotate_picks_with_forward_gate(picks, perf)
        self.assertFalse(picks[0]["forward_validated"])
        self.assertIn("insufficient_data", picks[0]["forward_status"])

    def test_bond_pick_below_10_trades_still_blocked(self):
        from alpha_engine import forward_validator as fv
        picks = [{
            "strategy": "bond_momentum",
            "asset_class": "bond",
            "confidence": 0.7,
        }]
        perf = {
            "bond_momentum": {
                "wins": 3, "losses": 2, "closed_picks": 5,
                "win_rate": 0.6,
            }
        }
        fv.annotate_picks_with_forward_gate(picks, perf)
        self.assertFalse(picks[0]["forward_validated"])
        self.assertIn("5/10", picks[0]["forward_status"])


if __name__ == "__main__":
    main()

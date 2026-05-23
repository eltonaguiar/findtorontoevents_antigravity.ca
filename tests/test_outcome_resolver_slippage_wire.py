"""Regression test for charter_slippage wire-up in outcome_resolver.py.

After a pick is resolved (pnl_pct + status assigned), the resolver now also
calls stamp_pick_net_pnl from alpha_engine.charter_slippage so every closed
pick carries _pnl_pct_gross + _pnl_pct_net for downstream consumers.

This test exercises the import path so any future refactor that breaks the
lazy-import contract will fail CI here.
"""
from unittest import TestCase, main


class OutcomeResolverSlippageWireTests(TestCase):
    def test_outcome_resolver_module_imports(self):
        # Sanity: outcome_resolver still imports cleanly even though it now
        # carries a lazy import to charter_slippage. The lazy-import pattern
        # is critical for partial-checkout test scenarios.
        import alpha_engine.outcome_resolver as resolver
        self.assertTrue(hasattr(resolver, "resolve_outcomes"))

    def test_charter_slippage_stamps_net_pnl(self):
        # The wired call: stamp_pick_net_pnl on a freshly-resolved pick
        # should populate _pnl_pct_gross and _pnl_pct_net per the
        # per-class round-trip bps in charter_slippage.
        from alpha_engine.charter_slippage import stamp_pick_net_pnl
        pick = {"pnl_pct": 0.5, "asset_class": "COMMODITY"}
        stamp_pick_net_pnl(pick)
        self.assertEqual(pick["_pnl_pct_gross"], 0.5)
        # COMMODITY round-trip = 12bp = 12/10000 = 0.0012 (post-M-069 units fix)
        # net = 0.5 - 0.0012 = 0.4988
        self.assertAlmostEqual(pick["_pnl_pct_net"], 0.4988, places=6)

    def test_multi_asset_cot_regression_reproduces_at_wire_level(self):
        # Post-M-069 fix: round_trip_bps correctly deducted as bps/10000.
        # COMMODITY 12bp round-trip = 0.0012 decimal.
        # A 7.18bp-gross trade (pnl_pct=0.0718) nets 0.0718 - 0.0012 = 0.0706 (winner).
        from alpha_engine.charter_slippage import stamp_pick_net_pnl
        pick = {"pnl_pct": 0.0718, "asset_class": "COMMODITY",
                "status": "WIN"}
        stamp_pick_net_pnl(pick)
        self.assertEqual(pick["status"], "WIN")  # gross classification unchanged
        self.assertGreater(pick["_pnl_pct_net"], 0)  # net is positive after correct slippage
        self.assertAlmostEqual(pick["_pnl_pct_net"], 0.0718 - 0.0012, places=6)


if __name__ == "__main__":
    main()

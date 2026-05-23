"""Tests for the 2026-05-02 walk_forward_by_class helper.

Covers per-asset-class slicing of the dashboard payload and propagation of
walk_forward_validate's metrics keys for each class with sufficient trades.
"""
import unittest

from alpha_engine.walkforward_validator import (
    walk_forward_by_class,
    DEFAULT_CLASS_WF_CONFIG,
)


def _payload(closed):
    return {"picks": {"recent_closed": closed}}


def _trade(asset_class: str, pnl: float, ts: str = "2026-04-01T00:00:00Z"):
    return {
        "asset_class": asset_class,
        "pnl_pct": pnl,
        "timestamp": ts,
        "strategy": "s1",
        "_outcome": "WIN" if pnl > 0 else "LOSS",
    }


class WalkForwardByClassTests(unittest.TestCase):
    def test_empty_payload(self):
        self.assertEqual(walk_forward_by_class({}), {})
        self.assertEqual(walk_forward_by_class({"picks": {}}), {})

    def test_below_min_trades_skipped(self):
        # 5 trades total < default min_trades=30 → empty result
        closed = [_trade("CRYPTO", 1.0) for _ in range(5)]
        self.assertEqual(walk_forward_by_class(_payload(closed)), {})

    def test_flat_outcomes_excluded(self):
        closed = []
        for i in range(40):
            closed.append({
                "asset_class": "CRYPTO",
                "pnl_pct": 0.0,
                "timestamp": "2026-04-01",
                "_outcome": "FLAT",
            })
        self.assertEqual(walk_forward_by_class(_payload(closed)), {})

    def test_class_slicing(self):
        # 35 CRYPTO + 35 EQUITY trades, alternating wins/losses
        closed = []
        for i in range(35):
            closed.append(_trade("CRYPTO", 1.0 if i % 2 == 0 else -1.0))
        for i in range(35):
            closed.append(_trade("EQUITY", 0.5 if i % 3 == 0 else -0.5))
        # FOREX has only 5 trades — should be filtered out
        for i in range(5):
            closed.append(_trade("FOREX", 0.1))

        result = walk_forward_by_class(_payload(closed), min_trades=30)
        self.assertIn("CRYPTO", result)
        self.assertIn("EQUITY", result)
        self.assertNotIn("FOREX", result)

    def test_returns_walk_forward_metrics(self):
        # 50 trades to ensure folds form
        closed = [_trade("CRYPTO", 1.0 if i % 2 == 0 else -0.5) for i in range(50)]
        result = walk_forward_by_class(_payload(closed), min_trades=30)
        self.assertIn("CRYPTO", result)
        crypto = result["CRYPTO"]
        # Keys produced by walk_forward_validate
        for key in ("folds", "oos_wr", "oos_sharpe", "decay"):
            self.assertIn(key, crypto)

    def test_default_class_when_missing(self):
        closed = [{"pnl_pct": 1.0, "timestamp": "2026-04-01"} for _ in range(35)]
        result = walk_forward_by_class(_payload(closed), min_trades=30)
        self.assertIn("CRYPTO", result)

    def test_commodity_universe_filter_drops_blacklisted_symbols(self):
        # 50 HG=F (allowed) + 50 CT=F (blacklisted by PR #535 universe).
        # Filter must keep HG=F and drop CT=F before windowing so the
        # OOS-Sharpe estimate isn't biased by symbols we banned.
        closed = []
        for i in range(50):
            closed.append({
                "asset_class": "COMMODITY", "symbol": "HG=F",
                "pnl_pct": 0.5 if i % 2 else -0.3,
                "timestamp": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
                "_outcome": "WIN" if i % 2 else "LOSS",
            })
        for i in range(50):
            closed.append({
                "asset_class": "COMMODITY", "symbol": "CT=F",
                "pnl_pct": -2.0,
                "timestamp": f"2026-02-{(i % 28) + 1:02d}T00:00:00Z",
                "_outcome": "LOSS",
            })
        result = walk_forward_by_class(_payload(closed), min_trades=30)
        self.assertIn("COMMODITY", result)
        commodity = result["COMMODITY"]
        self.assertEqual(commodity["symbols_allowed"], ["HG=F", "PL=F"])
        self.assertEqual(commodity["symbols_filtered_out"], ["CT=F"])
        self.assertEqual(commodity["window_config"]["n_trades"], 50)

    def test_commodity_production_config_produces_folds_at_n27(self):
        # Regression guard for the swarm-caught bug (2026-05-13): a previous
        # version of DEFAULT_CLASS_WF_CONFIG["COMMODITY"] had min_trades=200,
        # which silently skipped COMMODITY even after the HG=F+PL=F filter
        # shipped because post-filter n in recent_closed is ~27. This test
        # exercises the actual production code path (DEFAULT_CLASS_WF_CONFIG)
        # at the live n to ensure the threshold + window sizes produce a
        # populated COMMODITY block, not a silent skip.
        closed = []
        for i in range(27):
            closed.append({
                "asset_class": "COMMODITY", "symbol": "HG=F",
                "pnl_pct": 0.4 if i % 2 else -0.2,
                "timestamp": f"2026-04-{(i % 28) + 1:02d}T00:00:00Z",
                "_outcome": "WIN" if i % 2 else "LOSS",
            })
        result = walk_forward_by_class(
            _payload(closed), class_config=DEFAULT_CLASS_WF_CONFIG,
        )
        self.assertIn("COMMODITY", result,
                      "COMMODITY missing from result with production config — "
                      "min_trades is set too high for the post-filter n. Swarm "
                      "caught this same bug 2026-05-13.")
        commodity = result["COMMODITY"]
        self.assertGreaterEqual(commodity["folds"], 3,
                                "Too few folds — train/test/step sizes too "
                                "large for the post-filter n.")


if __name__ == "__main__":
    unittest.main()

"""Tests for tools/capacity_model.py -- the depth-curve interpolation and the net-APR function.

These pin the only real logic in the module: linear interpolation of the measured spread
curve (including the no-extrapolation rule), pair-cost construction, and net APR.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "capacity_model", REPO / "tools" / "capacity_model.py"
)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


# A synthetic measured curve: flat 1bp spread to $100k, then 5bp at $1M.
CURVE = [(1_000.0, 1.0), (100_000.0, 1.0), (1_000_000.0, 5.0)]


class InterpSpreadTests(unittest.TestCase):
    def test_exact_knot(self) -> None:
        self.assertEqual(cm.interp_spread(CURVE, 100_000.0), 1.0)

    def test_linear_midpoint(self) -> None:
        # halfway between $100k (1bp) and $1M (5bp) -> 3bp
        self.assertAlmostEqual(cm.interp_spread(CURVE, 550_000.0), 3.0, places=9)

    def test_below_floor_clamps_to_first(self) -> None:
        self.assertEqual(cm.interp_spread(CURVE, 10.0), 1.0)

    def test_above_ceiling_returns_none_not_extrapolated(self) -> None:
        # must NOT extrapolate past the deepest measured point
        self.assertIsNone(cm.interp_spread(CURVE, 2_000_000.0))

    def test_empty_curve(self) -> None:
        self.assertIsNone(cm.interp_spread([], 1000.0))


class PairCostTests(unittest.TestCase):
    def test_pair_cost_two_legs_four_fills(self) -> None:
        # 2 legs x (spread_rt 1bp + 2 x taker 10bp) = 2 x 21 = 42bp
        self.assertAlmostEqual(cm.pair_cost_bp(CURVE, 10.0, 100_000.0), 42.0, places=9)

    def test_2x_cost_doubles(self) -> None:
        a = cm.pair_cost_bp(CURVE, 10.0, 550_000.0, 1.0)
        b = cm.pair_cost_bp(CURVE, 10.0, 550_000.0, 2.0)
        self.assertAlmostEqual(b, 2 * a, places=9)

    def test_depth_exhausted_returns_none(self) -> None:
        self.assertIsNone(cm.pair_cost_bp(CURVE, 10.0, 5_000_000.0))


class CrossoverTests(unittest.TestCase):
    def test_crossover_interpolates(self) -> None:
        # threshold 43bp: pair cost = 2*(spread+20), so need spread=1.5.
        # spread=1.5 lies between 1bp@100k and 5bp@1M at fraction (1.5-1)/4=0.125
        # -> 100k + 0.125*(1M-100k) = 212,500.
        res = cm.crossover_notional(CURVE, 10.0, 43.0, 1.0)
        self.assertFalse(res["below_measured_floor"])
        self.assertAlmostEqual(res["usd"], 212_500.0, delta=1.0)

    def test_crossover_already_above_floor_is_flagged(self) -> None:
        res = cm.crossover_notional(CURVE, 10.0, 41.0, 1.0)  # 42 already > 41 at $1k
        self.assertTrue(res["below_measured_floor"])
        self.assertEqual(res["usd"], 1_000.0)

    def test_crossover_never_reached(self) -> None:
        res = cm.crossover_notional(CURVE, 10.0, 10_000.0, 1.0)
        self.assertIsNone(res["usd"])


class NetAprTests(unittest.TestCase):
    def test_net_apr_is_gross_minus_cost_over_hold(self) -> None:
        # gross 10%, pair cost 42bp = 0.42% over a 365d hold -> net = 10% - 0.42% = 9.58%
        n = cm.net_apr(CURVE, 10.0, 0.10, 365.0, 100_000.0, 1.0)
        self.assertAlmostEqual(n, 0.10 - 42.0 / 1e4, places=12)

    def test_shorter_hold_amortises_cost_harder(self) -> None:
        long_hold = cm.net_apr(CURVE, 10.0, 0.10, 365.0, 100_000.0)
        short_hold = cm.net_apr(CURVE, 10.0, 0.10, 30.0, 100_000.0)
        self.assertLess(short_hold, long_hold)

    def test_net_apr_decreases_with_size(self) -> None:
        small = cm.net_apr(CURVE, 10.0, 0.10, 30.0, 10_000.0)
        big = cm.net_apr(CURVE, 10.0, 0.10, 30.0, 1_000_000.0)
        self.assertLess(big, small)

    def test_net_apr_none_past_depth(self) -> None:
        self.assertIsNone(cm.net_apr(CURVE, 10.0, 0.10, 30.0, 9_000_000.0))


class GrossFundingTests(unittest.TestCase):
    def test_8h_to_apr(self) -> None:
        # 0.01% per 8h x 3 x 365 = 10.95% APR
        self.assertAlmostEqual(cm.gross_funding_apr(0.0001), 0.0001 * 3 * 365, places=12)


if __name__ == "__main__":
    unittest.main()


def test_deliberately_broken_gate_probe():
    assert 1 == 2, "intentional failure to prove the CI gate is wired"

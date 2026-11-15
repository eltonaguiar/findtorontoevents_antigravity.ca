import importlib
import importlib.util
import inspect
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path


class SimulationContractTests(unittest.TestCase):
    def runner(self):
        self.assertIsNotNone(
            importlib.util.find_spec("simulation_runner"),
            "The offline simulation runner has not been implemented",
        )
        return importlib.import_module("simulation_runner")

    def market(self, dates, spy, cash=None):
        runner = self.runner()
        cash = cash if cash is not None else [100.0] * len(dates)
        prices = {"SPY": spy, "SGOV": cash}
        return runner.MarketData(dates, prices, prices)

    def test_concurrent_positions_use_account_capital(self):
        runner = self.runner()
        prices = {"A": [100.0, 110.0], "B": [100.0, 110.0]}
        market = runner.MarketData([date(2024, 1, 2), date(2024, 1, 3)], prices, prices)
        rows = runner.run_book(market, {0: {"A": 0.5, "B": 0.5}}, 0.0)
        self.assertAlmostEqual(rows[-1].nav, 110000.0)

    def test_weights_drift_without_daily_rebalance(self):
        runner = self.runner()
        prices = {"A": [100.0, 200.0, 200.0], "B": [100.0, 100.0, 200.0]}
        market = runner.MarketData(
            [date(2024, 1, i) for i in (2, 3, 4)], prices, prices
        )
        rows = runner.run_book(market, {0: {"A": 0.5, "B": 0.5}}, 0.0)
        self.assertAlmostEqual(rows[-1].nav, 200000.0)

    def test_initial_and_terminal_costs_are_funded(self):
        runner = self.runner()
        market = self.market([date(2024, 1, 2), date(2024, 1, 3)], [100.0, 100.0])
        rows = runner.run_book(market, {0: {"SPY": 1.0}}, 0.01)
        self.assertAlmostEqual(rows[-1].nav, 100000.0 / 1.01 * 0.99)
        self.assertAlmostEqual(sum(row.cost for row in rows), 100000.0 - rows[-1].nav)
        self.assertTrue(all(row.cash >= 0 for row in rows))

    def test_signal_executes_next_close_not_signal_close(self):
        runner = self.runner()
        dates = [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 1),
                 date(2024, 3, 4), date(2024, 3, 28), date(2024, 4, 1)]
        market = self.market(dates, [100.0, 120.0, 180.0, 198.0, 210.0, 211.0])
        targets = runner.trend_targets(market, 2)
        self.assertNotIn(1, targets)
        self.assertEqual(targets[2], {"SPY": 1.0})
        rows = runner.run_book(market, targets, 0.0)
        self.assertAlmostEqual(rows[0].nav, 100000.0)
        self.assertAlmostEqual(rows[1].nav, 110000.0)

    def test_partial_final_month_does_not_generate_signal(self):
        runner = self.runner()
        dates = [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 1),
                 date(2024, 3, 13)]
        targets = runner.trend_targets(self.market(dates, [100., 120., 125., 130.]), 2)
        self.assertEqual(list(targets), [2])

    def test_future_price_change_cannot_change_earlier_target(self):
        runner = self.runner()
        dates = [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 1),
                 date(2024, 3, 28), date(2024, 4, 1), date(2024, 4, 30),
                 date(2024, 5, 1)]
        before = runner.trend_targets(self.market(dates, [100., 110., 111., 115., 116., 90., 91.]), 2)
        after = runner.trend_targets(self.market(dates, [100., 110., 111., 115., 116., 900., 901.]), 2)
        self.assertEqual({k: v for k, v in before.items() if k < 5},
                         {k: v for k, v in after.items() if k < 5})

    def test_nonpositive_or_missing_price_is_rejected(self):
        runner = self.runner()
        for bad in (0.0, -1.0, math.nan, math.inf, None):
            with self.subTest(price=bad), self.assertRaises(ValueError):
                runner.validate_market(self.market(
                    [date(2024, 1, 2), date(2024, 1, 3)], [100.0, bad]
                ))

    def test_duplicate_dates_or_mismatched_arrays_are_rejected(self):
        runner = self.runner()
        with self.assertRaises(ValueError):
            runner.validate_market(self.market([date(2024, 1, 2)] * 2, [100., 101.]))
        with self.assertRaises(ValueError):
            runner.validate_market(self.market(
                [date(2024, 1, 2), date(2024, 1, 3)], [100.]
            ))

    def test_overweight_target_is_rejected(self):
        runner = self.runner()
        market = self.market([date(2024, 1, 2), date(2024, 1, 3)], [100., 100.])
        with self.assertRaises(ValueError):
            runner.run_book(market, {0: {"SPY": 0.6, "SGOV": 0.5}}, 0.0)

    def test_joint_bootstrap_preserves_identical_benchmark(self):
        runner = self.runner()
        values = [-0.01, 0.02, -0.03, 0.04]
        result = runner.joint_scenarios(values, values, [0.0] * 4, 2, 5, 20, 7)
        self.assertEqual(result["fraction_beating_spy"], 0.0)
        self.assertEqual(result["excess_annualized_ci_95"], [0.0, 0.0])

    def test_csv_blank_is_not_zero(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("date,SPY_adj,SPY_close\n2024-01-02,,100\n")
            with self.assertRaises(ValueError):
                runner.load_market(path)

    def test_regular_returns_do_not_resample_boundary_fees(self):
        runner = self.runner()
        self.assertTrue(hasattr(runner, "regular_returns"),
                        "Boundary fees need separation from regular returns")
        market = self.market([date(2024, 1, 2), date(2024, 1, 3)], [100., 110.])
        rows = runner.run_book(market, {0: {"SPY": 1.0}}, 0.01)
        regular = runner.regular_returns(rows)
        self.assertEqual(len(regular), 1)
        self.assertAlmostEqual(regular[0], 0.10)

    def test_scenario_endpoint_costs_apply_once_for_every_horizon(self):
        runner = self.runner()
        self.assertIn("entry_factors", inspect.signature(runner.joint_scenarios).parameters,
                      "Fixed-horizon scenarios must account for endpoint fees")
        for horizon in (1, 100):
            with self.subTest(horizon=horizon):
                result = runner.joint_scenarios(
                    [0.] * 4, [0.] * 4, [0.] * 4, 2, horizon, 20, 7,
                    entry_factors=(.99, .99, .99), exit_factors=(.98, .98, .98),
                )
                for wealth in result["wealth_multiple_5_50_95"]:
                    self.assertAlmostEqual(wealth, .99 * .98)
                self.assertAlmostEqual(result["mdd_loss_pct_50_95"][0], 2.98)
                self.assertEqual(result["fraction_beating_spy"], 0.0)


if __name__ == "__main__":
    unittest.main()

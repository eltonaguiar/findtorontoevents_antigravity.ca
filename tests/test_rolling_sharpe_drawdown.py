"""Tests for tools/rolling_sharpe_drawdown.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rolling_sharpe_drawdown", REPO / "tools" / "rolling_sharpe_drawdown.py"
)
rsd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rsd)


def _picks(pnl_pcts: list[float], strategy: str = "demo",
           start: str = "2026-01-01T00:00:00Z") -> list[dict]:
    base = datetime.fromisoformat(start.replace("Z", "+00:00"))
    return [
        {"strategy": strategy, "pnl_pct": pnl,
         "closed_at": (base + timedelta(hours=i)).isoformat().replace("+00:00", "Z")}
        for i, pnl in enumerate(pnl_pcts)
    ]


class WindowMathTests(unittest.TestCase):
    def test_window_sharpe_zero_on_constant_returns(self) -> None:
        import numpy as np
        # Constant returns -> std=0 -> Sharpe defined as 0
        self.assertEqual(rsd._window_sharpe(np.array([1.0] * 30)), 0.0)

    def test_window_sharpe_positive_on_winning_series(self) -> None:
        import numpy as np
        # 9 wins of 1%, 1 loss of -0.5% -> positive mean, finite std
        win = np.array([1.0] * 9 + [-0.5])
        sharpe = rsd._window_sharpe(win)
        self.assertGreater(sharpe, 0.0)

    def test_window_max_drawdown_zero_on_monotone_winning(self) -> None:
        import numpy as np
        # All wins -> equity curve only goes up -> DD = 0
        win = np.array([1.0] * 30)
        self.assertEqual(rsd._window_max_drawdown(win), 0.0)

    def test_window_max_drawdown_captures_burst(self) -> None:
        import numpy as np
        # Compound drop: -10% then -10% => total ~19% DD from initial
        win = np.array([0.0, -10.0, -10.0])
        dd = rsd._window_max_drawdown(win)
        self.assertGreater(dd, 18.0)
        self.assertLess(dd, 20.0)


class AnalyzeStrategyTests(unittest.TestCase):
    def test_insufficient_n_returns_none(self) -> None:
        # 29 picks, default min_n = window = 30 -> None
        self.assertIsNone(rsd.analyze_strategy(_picks([1.0] * 29)))

    def test_monotone_improving_small_drawdown(self) -> None:
        # 50 picks of +1% -> small/zero drawdown
        result = rsd.analyze_strategy(_picks([1.0] * 50), window=30)
        self.assertIsNotNone(result)
        self.assertEqual(result["max_drawdown_30"], 0.0)
        self.assertEqual(result["current_drawdown_30"], 0.0)

    def test_large_loss_burst_big_drawdown(self) -> None:
        # 30 winners then 30 big losses
        pnls = [1.0] * 30 + [-5.0] * 30
        result = rsd.analyze_strategy(_picks(pnls), window=30)
        self.assertIsNotNone(result)
        # The loss-burst window should have a substantial drawdown
        self.assertGreater(result["max_drawdown_30"], 50.0)

    def test_sharpe_percentile_distribution_sane(self) -> None:
        # Random-looking series: pct10 < median < pct90
        import random
        rng = random.Random(42)
        pnls = [rng.gauss(0.5, 1.0) for _ in range(100)]
        result = rsd.analyze_strategy(_picks(pnls), window=30)
        self.assertIsNotNone(result)
        self.assertLessEqual(result["sharpe_pct10"], result["sharpe_median"])
        self.assertLessEqual(result["sharpe_median"], result["sharpe_pct90"])

    def test_skips_malformed_picks(self) -> None:
        good = _picks([1.0] * 35)
        bad = [
            {"strategy": "demo", "pnl_pct": None,
             "closed_at": "2026-01-15T00:00:00Z"},
            {"strategy": "demo", "pnl_pct": "not_a_number",
             "closed_at": "2026-01-15T00:00:00Z"},
        ]
        result = rsd.analyze_strategy(good + bad, window=30)
        self.assertIsNotNone(result)
        # Only the 35 good picks should be counted
        self.assertEqual(result["n"], 35)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_by_strategy_filters_small_n(self) -> None:
        picks = _picks([1.0] * 50, strategy="winner")
        picks += _picks([1.0] * 50, strategy="loser",
                        start="2026-02-01T00:00:00Z")
        # Trigger losses for "loser"
        for p in picks:
            if p["strategy"] == "loser":
                p["pnl_pct"] = -1.0 if int(p["closed_at"][8:10]) > 1 else 1.0
        picks += _picks([1.0] * 10, strategy="too_small",
                        start="2026-03-01T00:00:00Z")
        summary = rsd.analyze_all(picks, window=30, min_n=30)
        names = {s["strategy"] for s in summary["strategies"]}
        self.assertIn("winner", names)
        self.assertIn("loser", names)
        self.assertNotIn("too_small", names)


if __name__ == "__main__":
    unittest.main()

"""Tests for tools/strategy_correlation_matrix.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "strategy_correlation_matrix",
    REPO / "tools" / "strategy_correlation_matrix.py"
)
scm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scm)


def _picks(strategy: str, daily_pnls: dict[str, float]) -> list[dict]:
    """Build picks list for a strategy with date->pnl entries.

    `daily_pnls` is a dict like {"2026-01-01": 1.5, "2026-01-02": -0.5, ...}
    """
    out = []
    for date, pnl in daily_pnls.items():
        out.append({
            "strategy": strategy,
            "pnl_pct": pnl,
            "closed_at": f"{date}T12:00:00Z",
        })
    return out


def _date_range(start: str, days: int) -> list[str]:
    base = datetime.fromisoformat(start)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


class RankFunctionTests(unittest.TestCase):
    def test_unique_values(self) -> None:
        self.assertEqual(scm._ranks([3.0, 1.0, 2.0]), [3.0, 1.0, 2.0])

    def test_average_rank_tie_breaking(self) -> None:
        # [1, 1, 2] -> ranks [1.5, 1.5, 3]
        self.assertEqual(scm._ranks([1.0, 1.0, 2.0]), [1.5, 1.5, 3.0])

    def test_descending(self) -> None:
        self.assertEqual(scm._ranks([5.0, 4.0, 3.0]), [3.0, 2.0, 1.0])


class SpearmanRhoTests(unittest.TestCase):
    def test_identical_series_rho_one(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertAlmostEqual(scm.spearman_rho(a, a), 1.0)

    def test_perfectly_anticorrelated_rho_neg_one(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [5.0, 4.0, 3.0, 2.0, 1.0]
        self.assertAlmostEqual(scm.spearman_rho(a, b), -1.0)

    def test_uncorrelated_near_zero(self) -> None:
        # Permutation that gives near-zero rank correlation
        a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        b = [3.0, 1.0, 4.0, 6.0, 2.0, 5.0]
        rho = scm.spearman_rho(a, b)
        self.assertLess(abs(rho), 0.5)

    def test_unequal_length_raises(self) -> None:
        with self.assertRaises(ValueError):
            scm.spearman_rho([1.0, 2.0], [1.0, 2.0, 3.0])


class PairwiseCorrelationTests(unittest.TestCase):
    def test_identical_strategies_rho_one(self) -> None:
        dates = _date_range("2026-01-01", 35)
        pnls = {d: float(i % 5) - 2 for i, d in enumerate(dates)}
        picks = _picks("strat_a", pnls) + _picks("strat_b", pnls)
        daily = scm._aggregate_daily_by_strategy(picks)
        matrix, strats = scm.pairwise_correlations(daily, min_overlap=30)
        self.assertEqual(set(strats), {"strat_a", "strat_b"})
        self.assertAlmostEqual(matrix["strat_a"]["strat_b"]["rho"], 1.0)
        self.assertEqual(matrix["strat_a"]["strat_b"]["n_overlap_days"], 35)

    def test_anticorrelated_pair_rho_neg_one(self) -> None:
        dates = _date_range("2026-01-01", 35)
        pnls_a = {d: float(i) for i, d in enumerate(dates)}
        pnls_b = {d: float(-i) for i, d in enumerate(dates)}
        picks = _picks("a", pnls_a) + _picks("b", pnls_b)
        daily = scm._aggregate_daily_by_strategy(picks)
        matrix, _ = scm.pairwise_correlations(daily, min_overlap=30)
        self.assertAlmostEqual(matrix["a"]["b"]["rho"], -1.0)

    def test_no_overlap_excluded(self) -> None:
        dates_a = _date_range("2026-01-01", 35)
        dates_b = _date_range("2026-03-01", 35)  # no overlap with a
        picks = (_picks("a", {d: float(i) for i, d in enumerate(dates_a)})
                 + _picks("b", {d: float(i) for i, d in enumerate(dates_b)}))
        daily = scm._aggregate_daily_by_strategy(picks)
        matrix, _ = scm.pairwise_correlations(daily, min_overlap=30)
        self.assertNotIn("b", matrix.get("a", {}))

    def test_below_min_overlap_excluded(self) -> None:
        # Only 20 overlapping days; min_overlap=30 -> excluded
        dates = _date_range("2026-01-01", 20)
        pnls = {d: float(i) for i, d in enumerate(dates)}
        picks = _picks("a", pnls) + _picks("b", pnls)
        daily = scm._aggregate_daily_by_strategy(picks)
        matrix, _ = scm.pairwise_correlations(daily, min_overlap=30)
        self.assertNotIn("b", matrix.get("a", {}))


class ClusterTests(unittest.TestCase):
    def _three_correlated_picks(self) -> list[dict]:
        dates = _date_range("2026-01-01", 35)
        pnls = {d: float(i) for i, d in enumerate(dates)}
        # Three strategies with identical PnL series -> rho=1 between all
        out = []
        for s in ("a", "b", "c"):
            out += _picks(s, pnls)
        return out

    def test_three_correlated_form_one_cluster(self) -> None:
        summary = scm.analyze_all(self._three_correlated_picks(),
                                   min_overlap=30, cluster_threshold=0.7)
        self.assertEqual(len(summary["threshold_clusters"]), 1)
        cluster = summary["threshold_clusters"][0]
        self.assertEqual(set(cluster["strategies"]), {"a", "b", "c"})
        self.assertAlmostEqual(cluster["avg_rho"], 1.0)


class AnalyzeAllTests(unittest.TestCase):
    def test_skips_malformed_picks(self) -> None:
        dates = _date_range("2026-01-01", 35)
        good = _picks("a", {d: float(i) for i, d in enumerate(dates)})
        good += _picks("b", {d: float(i * 2) for i, d in enumerate(dates)})
        bad = [
            {"strategy": "a", "pnl_pct": None,
             "closed_at": "2026-02-01T00:00:00Z"},
            {"strategy": "a", "pnl_pct": "not_a_number",
             "closed_at": "2026-02-01T00:00:00Z"},
            {"strategy": "a", "pnl_pct": 1.0, "closed_at": None},
            {"strategy": "a", "pnl_pct": 1.0,
             "closed_at": "not-a-date"},
        ]
        summary = scm.analyze_all(good + bad, min_overlap=30)
        self.assertEqual(len(summary["strategies"]), 2)
        self.assertIn("a", summary["matrix"])
        self.assertIn("b", summary["matrix"]["a"])


if __name__ == "__main__":
    unittest.main()

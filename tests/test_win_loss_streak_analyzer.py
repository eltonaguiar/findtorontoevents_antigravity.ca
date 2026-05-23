"""Tests for tools/win_loss_streak_analyzer.py."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "win_loss_streak_analyzer",
    REPO / "tools" / "win_loss_streak_analyzer.py"
)
ws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ws)


def _picks(outcomes: list[int], strategy: str = "demo",
           start: str = "2026-01-01T00:00:00Z") -> list[dict]:
    base = datetime.fromisoformat(start.replace("Z", "+00:00"))
    return [
        {"strategy": strategy,
         "pnl_pct": 1.0 if w else -1.0,
         "closed_at": (base + timedelta(hours=i)).isoformat().replace("+00:00", "Z")}
        for i, w in enumerate(outcomes)
    ]


class StreakComputationTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(ws.compute_streaks([]), [])

    def test_alternating_no_streaks_above_1(self) -> None:
        streaks = ws.compute_streaks([1, 0, 1, 0, 1, 0])
        self.assertEqual(streaks, [(1, 1), (-1, 1), (1, 1), (-1, 1),
                                    (1, 1), (-1, 1)])
        # All streaks have length 1
        self.assertTrue(all(length == 1 for _, length in streaks))

    def test_single_run(self) -> None:
        self.assertEqual(ws.compute_streaks([1, 1, 1]), [(1, 3)])
        self.assertEqual(ws.compute_streaks([0, 0, 0, 0]), [(-1, 4)])

    def test_mixed_runs(self) -> None:
        # WW LLL W LL  -> [(+1,2), (-1,3), (+1,1), (-1,2)]
        streaks = ws.compute_streaks([1, 1, 0, 0, 0, 1, 0, 0])
        self.assertEqual(streaks, [(1, 2), (-1, 3), (1, 1), (-1, 2)])


class AnalyzeStrategyTests(unittest.TestCase):
    def test_alternating_max_streaks_one(self) -> None:
        result = ws.analyze_strategy(_picks([1, 0] * 15))
        self.assertIsNotNone(result)
        self.assertEqual(result["max_win_streak"], 1)
        self.assertEqual(result["max_loss_streak"], 1)
        self.assertEqual(result["n_streaks"], 30)

    def test_all_wins_single_streak(self) -> None:
        result = ws.analyze_strategy(_picks([1] * 25))
        self.assertEqual(result["max_win_streak"], 25)
        self.assertEqual(result["max_loss_streak"], 0)
        self.assertEqual(result["n_streaks"], 1)
        self.assertEqual(result["current_streak"], 25)

    def test_all_losses_single_streak(self) -> None:
        result = ws.analyze_strategy(_picks([0] * 25))
        self.assertEqual(result["max_win_streak"], 0)
        self.assertEqual(result["max_loss_streak"], 25)
        self.assertEqual(result["current_streak"], -25)

    def test_monotone_improving_small_loss_max(self) -> None:
        # 5 losses then 25 wins -> max_loss=5, max_win=25, current=+25
        result = ws.analyze_strategy(_picks([0] * 5 + [1] * 25))
        self.assertEqual(result["max_loss_streak"], 5)
        self.assertEqual(result["max_win_streak"], 25)
        self.assertEqual(result["current_streak"], 25)

    def test_current_streak_signed(self) -> None:
        # Last entries are 3 losses
        result = ws.analyze_strategy(_picks([1] * 10 + [0] * 5 + [1] * 7
                                              + [0] * 3))
        self.assertEqual(result["current_streak"], -3)

    def test_insufficient_n_returns_none(self) -> None:
        self.assertIsNone(ws.analyze_strategy(_picks([1, 0] * 5)))  # n=10

    def test_skips_malformed_pnl(self) -> None:
        good = _picks([1, 0] * 11)  # 22 picks
        bad = [
            {"strategy": "demo", "pnl_pct": None,
             "closed_at": "2026-01-15T00:00:00Z"},
            {"strategy": "demo", "pnl_pct": "x",
             "closed_at": "2026-01-15T00:00:00Z"},
        ]
        result = ws.analyze_strategy(good + bad)
        self.assertEqual(result["n"], 22)


class AnalyzeAllTests(unittest.TestCase):
    def test_groups_and_sorts_by_max_loss_streak_descending(self) -> None:
        picks = _picks([0] * 25, strategy="long_loser")
        picks += _picks([1] * 25, strategy="long_winner",
                        start="2026-02-01T00:00:00Z")
        picks += _picks([1, 0] * 15, strategy="alternator",
                        start="2026-03-01T00:00:00Z")
        picks += _picks([1] * 10, strategy="too_small",
                        start="2026-04-01T00:00:00Z")
        summary = ws.analyze_all(picks)
        names = [s["strategy"] for s in summary["strategies"]]
        self.assertNotIn("too_small", names)
        # long_loser has max_loss_streak=25 -> first
        self.assertEqual(names[0], "long_loser")
        # long_winner has max_loss_streak=0 -> last
        self.assertEqual(names[-1], "long_winner")


if __name__ == "__main__":
    unittest.main()

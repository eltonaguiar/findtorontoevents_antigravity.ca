"""Tests for tools/wr_posterior_online.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wr_posterior_online", REPO / "tools" / "wr_posterior_online.py"
)
wp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wp)


def _fake_stats(wins: int, n: int, **kwargs):
    """Deterministic test stats — avoids importlib of wr_posterior.

    Accepts kwargs (alpha0, beta0) so the production callsite that passes
    those through doesn't break tests.
    """
    if n <= 0:
        return {"p_wr_above_50": 0.5, "ci_low_95": 0.0, "ci_high_95": 1.0}
    p = wins / n
    return {"p_wr_above_50": float(p), "ci_low_95": max(0.0, p - 0.1),
            "ci_high_95": min(1.0, p + 0.1)}


def _picks(outcomes: list[int], strategy: str = "demo") -> list[dict]:
    return [{"strategy": strategy, "pnl_pct": 1.0 if w else -1.0}
            for w in outcomes]


class ColdStartTests(unittest.TestCase):
    def test_empty_prior_state(self) -> None:
        prior = {"strategies": {}, "schema_version": 1}
        picks = _picks([1, 1, 0, 1, 0])
        new_state, history = wp.update_posteriors(
            picks, prior, posterior_stats=_fake_stats)
        self.assertIn("demo", new_state["strategies"])
        s = new_state["strategies"]["demo"]
        # 3 wins, 2 losses, prior 0.5/0.5 -> alpha=3.5, beta=2.5
        self.assertEqual(s["alpha"], 3.5)
        self.assertEqual(s["beta"], 2.5)
        self.assertEqual(s["n_total"], 5)
        self.assertEqual(s["last_seen_pick_idx"], 4)
        self.assertEqual(len(history), 1)


class IdempotencyTests(unittest.TestCase):
    def test_replay_same_picks_does_not_double_count(self) -> None:
        prior = {"strategies": {}, "schema_version": 1}
        picks = _picks([1, 1, 0, 1, 0])
        first, _ = wp.update_posteriors(picks, prior,
                                        posterior_stats=_fake_stats)
        # Replay with the SAME picks - should not double-count
        second, history2 = wp.update_posteriors(picks, first,
                                                posterior_stats=_fake_stats)
        s = second["strategies"]["demo"]
        self.assertEqual(s["alpha"], 3.5)  # unchanged
        self.assertEqual(s["beta"], 2.5)
        self.assertEqual(s["n_total"], 5)
        self.assertEqual(len(history2), 0)  # no new history rows


class IncrementalUpdateTests(unittest.TestCase):
    def test_new_picks_extend_posterior(self) -> None:
        prior = {"strategies": {}, "schema_version": 1}
        first_picks = _picks([1, 1, 0])  # 2W 1L -> alpha 2.5 beta 1.5
        first, _ = wp.update_posteriors(first_picks, prior,
                                         posterior_stats=_fake_stats)
        # Add 2 more picks: indices 3 and 4
        second_picks = _picks([1, 1, 0, 0, 0])  # +2L -> alpha 2.5 beta 3.5
        second, _ = wp.update_posteriors(second_picks, first,
                                          posterior_stats=_fake_stats)
        s = second["strategies"]["demo"]
        self.assertEqual(s["alpha"], 2.5)
        self.assertEqual(s["beta"], 3.5)
        self.assertEqual(s["n_total"], 5)
        self.assertEqual(s["last_seen_pick_idx"], 4)


class DriftDetectionTests(unittest.TestCase):
    def test_large_delta_flags_drift(self) -> None:
        # First batch: 9 wins, 1 loss -> mean ~0.9
        prior = {"strategies": {}, "schema_version": 1}
        first, _ = wp.update_posteriors(_picks([1] * 9 + [0]), prior,
                                         posterior_stats=_fake_stats)
        # Second batch: append 10 losses -> mean drops sharply
        new_picks = _picks([1] * 9 + [0] + [0] * 10)
        second, history = wp.update_posteriors(new_picks, first,
                                                posterior_stats=_fake_stats,
                                                drift_threshold=0.05)
        s = second["strategies"]["demo"]
        self.assertTrue(s["drift_flag"])
        self.assertLess(s["delta_mean"], -0.05)

    def test_no_drift_below_threshold(self) -> None:
        prior = {"strategies": {}, "schema_version": 1}
        # Stable around 50%: 5W 5L
        picks = _picks([1, 0] * 5)
        first, _ = wp.update_posteriors(picks, prior,
                                         posterior_stats=_fake_stats)
        # Continue stable: same ratio
        picks_more = _picks([1, 0] * 10)
        second, _ = wp.update_posteriors(picks_more, first,
                                          posterior_stats=_fake_stats,
                                          drift_threshold=0.05)
        s = second["strategies"]["demo"]
        self.assertFalse(s["drift_flag"])


class MalformedPickTests(unittest.TestCase):
    def test_skips_missing_pnl(self) -> None:
        picks = [
            {"strategy": "demo", "pnl_pct": 1.0},
            {"strategy": "demo", "pnl_pct": None},
            {"strategy": "demo", "pnl_pct": "not_a_number"},
            {"strategy": "demo", "pnl_pct": 0.5},
        ]
        new_state, _ = wp.update_posteriors(
            picks, {"strategies": {}, "schema_version": 1},
            posterior_stats=_fake_stats)
        s = new_state["strategies"]["demo"]
        # Only 2 picks counted (indices 0 and 3), both wins
        self.assertEqual(s["n_total"], 2)
        self.assertEqual(s["alpha"], 2.5)


class StateRoundTripTests(unittest.TestCase):
    def test_save_and_load_state(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            state = {"schema_version": 1,
                     "strategies": {"x": {"alpha": 5.0, "beta": 3.0,
                                          "last_seen_pick_idx": 7,
                                          "n_total": 8}}}
            wp.save_state(state, path)
            loaded = wp.load_state(path)
            self.assertEqual(loaded["strategies"]["x"]["alpha"], 5.0)
            self.assertEqual(loaded["strategies"]["x"]["last_seen_pick_idx"], 7)
        finally:
            path.unlink(missing_ok=True)

    def test_load_missing_file_returns_empty(self) -> None:
        loaded = wp.load_state(Path("/nonexistent/path/state.json"))
        self.assertEqual(loaded, {"strategies": {}, "schema_version": 1})


if __name__ == "__main__":
    unittest.main()

"""2026-11-16 audit guards: impossible-winrate cohorts + effective-n CIs.

Live evidence behind these tests:
- pf_registry carried ADX Trend Confirmation / BTCUSDT at 91 wins / 0 losses
  and GainerPredictor1hStrategy / AVAXUSDT at 48/0 — both ranked as top sleeves.
- intrabar_truth_by_class published i.i.d. CIs while MEMECOIN resolved 74.5% of
  its cohort on a single day, so nominal n overstates independent observations.
"""
import pytest

from tools.build_pf_registry import _blank_stat, _accumulate, _finalize
from tools.build_intrabar_truth_by_class import _wilson_ci_pct


def _stat(wins, losses, win=0.02, loss=-0.02):
    st = _blank_stat()
    for _ in range(wins):
        _accumulate(st, win)
    for _ in range(losses):
        _accumulate(st, loss)
    return _finalize(st)


class TestImpossibleWinrateFlag:
    def test_91_wins_zero_losses_is_flagged(self):
        out = _stat(91, 0)
        assert out["impossible_winrate"] is True
        assert out["profit_factor"] is None  # no losses -> undefined PF

    def test_48_wins_zero_losses_is_flagged(self):
        # GainerPredictor1hStrategy / AVAXUSDT was 48W-0L in the live registry.
        assert _stat(48, 0)["impossible_winrate"] is True

    def test_29_wins_zero_losses_is_not_flagged(self):
        # Below the 30-close floor a clean streak can still be a small sample.
        assert _stat(29, 0)["impossible_winrate"] is False

    def test_one_loss_disables_the_flag(self):
        out = _stat(91, 1)
        assert out["impossible_winrate"] is False
        assert out["profit_factor"] is not None

    def test_normal_cohort_not_flagged(self):
        assert _stat(30, 20)["impossible_winrate"] is False

    def test_flag_is_additive_and_stats_intact(self):
        out = _stat(60, 0)
        assert out["n"] == 60 and out["wins"] == 60 and out["losses"] == 0
        assert out["win_rate_pct"] == 100.0
        assert out["wr_fraction"] == 1.0


class TestEffectiveNCI:
    def test_wilson_shrinks_as_n_drops(self):
        lo_big, hi_big = _wilson_ci_pct(41.7, 3716)
        lo_small, hi_small = _wilson_ci_pct(41.7, 132)
        assert lo_small < lo_big and hi_small > hi_big

    def test_wilson_contains_point_estimate(self):
        lo, hi = _wilson_ci_pct(35.8, 73)
        assert lo < 35.8 < hi

    def test_wilson_bounds_are_inside_0_100(self):
        lo, hi = _wilson_ci_pct(0.0, 14)
        assert 0.0 <= lo <= hi <= 100.0
        lo2, hi2 = _wilson_ci_pct(100.0, 4)
        assert 0.0 <= lo2 <= hi2 <= 100.0

    def test_degenerate_inputs_return_none(self):
        assert _wilson_ci_pct(50.0, 0) == (None, None)
        assert _wilson_ci_pct(None, 10) == (None, None)

    def test_honest_ci_flips_a_thin_watch_class_to_inconclusive(self):
        # COMMODITY headline: 40.2% WR on n=229 but only 48 distinct days.
        lo, hi = _wilson_ci_pct(40.2, 48)
        assert lo < 50.0 < hi, "day-clustered CI must straddle 50% (inconclusive)"


class TestRegistryCountsPlacement:
    """Regression: the 2026-11-16 counter first landed as a sibling of ``counts``
    (top-level) so dashboards reading ``counts.impossible_winrate_cohorts`` got
    None while the live file reported a top-level value of 10."""

    def test_counter_is_inside_counts_dict(self):
        import ast
        import pathlib
        src = pathlib.Path("tools/build_pf_registry.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        found = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = [k.value for k in node.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)]
                if "raw_rows" in keys and "policy_clean_rows" in keys:
                    found = keys
                    break
        assert found is not None, "counts dict literal not found"
        assert "impossible_winrate_cohorts" in found, (
            "impossible_winrate_cohorts must live inside the counts dict")

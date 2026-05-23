"""Tests for tools/walk_forward_eff_harness.py — PATH_TO_PROVEN_EDGE Step 1."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys, os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.walk_forward_eff_harness import (
    _eff,
    _is_win,
    _parse_dt,
    admissibility_verdict,
    compute_rolling_eff,
    run_harness,
    SCORE_FIELDS,
    EFF_FLOOR,
    MIN_WINDOWS,
    WINDOW_DAYS,
)


def _make_picks(n_won: int, n_lost: int, score_field: str,
                won_val: float, lost_val: float,
                days_ago: float = 1.0, noise: float = 2.0) -> list[dict]:
    """Build synthetic closed picks in a single time window with noise for non-zero std."""
    import random
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    picks = []
    rng = random.Random(int(days_ago * 1000))
    for _ in range(n_won):
        picks.append({score_field: won_val + rng.gauss(0, noise), "status": "WIN",
                      "closed_at": ts, "pnl_pct": 0.01})
    for _ in range(n_lost):
        picks.append({score_field: lost_val + rng.gauss(0, noise), "status": "LOSS",
                      "closed_at": ts, "pnl_pct": -0.01})
    return picks


class TestEff:
    def test_zero_separation(self):
        assert _eff([1.0, 1.0], [1.0, 1.0]) == pytest.approx(0.0, abs=1e-6)

    def test_clear_separation(self):
        import random; random.seed(0)
        won = [10.0 + random.gauss(0, 0.5) for _ in range(50)]
        lost = [0.0 + random.gauss(0, 0.5) for _ in range(50)]
        e = _eff(won, lost)
        assert e > 1.0

    def test_empty_lists_return_zero(self):
        assert _eff([], [1.0, 2.0]) == 0.0
        assert _eff([1.0, 2.0], []) == 0.0

    def test_sign(self):
        import random; random.seed(1)
        won = [5.0 + random.gauss(0, 0.5) for _ in range(30)]
        lost = [1.0 + random.gauss(0, 0.5) for _ in range(30)]
        assert _eff(won, lost) > 0
        assert _eff(lost, won) < 0


class TestIsWin:
    def test_win_status(self):
        assert _is_win({"status": "WIN"}) is True
        assert _is_win({"status": "TARGET_HIT"}) is True
        assert _is_win({"status": "TP_HIT"}) is True

    def test_loss_status(self):
        assert _is_win({"status": "LOSS"}) is False
        assert _is_win({"status": "SL_HIT"}) is False

    def test_pnl_fallback(self):
        assert _is_win({"status": "", "pnl_pct": 0.01}) is True
        assert _is_win({"status": "", "pnl_pct": -0.01}) is False

    def test_unknown_returns_none(self):
        assert _is_win({"status": "OPEN"}) is None


class TestParseDt:
    def test_iso_format(self):
        dt = _parse_dt("2026-05-17T10:00:00")
        assert dt is not None
        assert dt.year == 2026

    def test_none_input(self):
        assert _parse_dt(None) is None

    def test_empty_string(self):
        assert _parse_dt("") is None


class TestAdmissibilityVerdict:
    def _windows(self, effs: list[float]) -> list[dict]:
        return [
            {"window": i, "eff": e, "n_total": 50, "n_won": 25, "n_lost": 25,
             "start": "x", "end": "x", "mean_won": 1.0, "mean_lost": 0.0}
            for i, e in enumerate(effs)
        ]

    def test_admissible_when_stable_above_floor(self):
        result = admissibility_verdict(self._windows([0.40, 0.35, 0.38]),
                                       min_windows=3, eff_floor=0.30)
        assert result["verdict"] == "ADMISSIBLE"

    def test_unstable_when_sign_flips(self):
        result = admissibility_verdict(self._windows([0.40, -0.35, 0.38]),
                                       min_windows=3, eff_floor=0.30)
        assert result["verdict"] == "UNSTABLE"

    def test_weak_when_consistent_but_below_floor(self):
        result = admissibility_verdict(self._windows([0.20, 0.15, 0.18]),
                                       min_windows=3, eff_floor=0.30)
        assert result["verdict"] == "WEAK"

    def test_insufficient_data_when_too_few_windows(self):
        windows = self._windows([0.40, 0.35])  # only 2
        for w in windows:
            w["n_total"] = 5  # below min_n
        result = admissibility_verdict(windows, min_windows=3, eff_floor=0.30)
        assert result["verdict"] == "INSUFFICIENT_DATA"

    def test_winners_lower_admissible(self):
        result = admissibility_verdict(self._windows([-0.45, -0.40, -0.35]),
                                       min_windows=3, eff_floor=0.30)
        assert result["verdict"] == "ADMISSIBLE"
        assert result["direction"] == "WINNERS_LOWER"


class TestRunHarness:
    def _synthetic_picks(self) -> list[dict]:
        """Three windows: consistent admissible score + noise score."""
        picks = []
        for w in range(4):
            days_ago = w * WINDOW_DAYS + 3
            picks += _make_picks(30, 30, "admissible_score",
                                 won_val=80.0, lost_val=20.0, days_ago=days_ago)
            picks += _make_picks(30, 30, "noise_score",
                                 won_val=50.0, lost_val=50.0, days_ago=days_ago)
        return picks

    def test_admissible_score_passes(self):
        picks = self._synthetic_picks()
        result = run_harness(picks, score_fields=["admissible_score"],
                             min_windows=3, eff_floor=0.30)
        assert "admissible_score" in result["summary"]["admissible"]

    def test_noise_score_is_weak_or_unstable(self):
        picks = self._synthetic_picks()
        result = run_harness(picks, score_fields=["noise_score"],
                             min_windows=3, eff_floor=0.30)
        assert result["scores"]["noise_score"]["verdict"] in ("WEAK", "UNSTABLE", "INSUFFICIENT_DATA")

    def test_output_has_required_keys(self):
        picks = self._synthetic_picks()
        result = run_harness(picks, score_fields=["admissible_score"])
        assert "generated_at" in result
        assert "config" in result
        assert "summary" in result
        assert "admissible" in result["summary"]
        assert "unstable" in result["summary"]

    def test_empty_picks_returns_insufficient(self):
        result = run_harness([], score_fields=["elite_score"])
        assert result["scores"]["elite_score"]["verdict"] == "INSUFFICIENT_DATA"

    def test_all_standard_fields_present_in_output(self):
        picks = self._synthetic_picks()
        result = run_harness(picks, score_fields=SCORE_FIELDS)
        for field in SCORE_FIELDS:
            assert field in result["scores"], f"Missing {field} in output"


# Make pytest discoverable
import pytest

class TestEffPytest(TestEff):
    pass

class TestIsWinPytest(TestIsWin):
    pass

class TestParseDtPytest(TestParseDt):
    pass

class TestAdmissibilityVerdictPytest(TestAdmissibilityVerdict):
    pass

class TestRunHarnessPytest(TestRunHarness):
    pass

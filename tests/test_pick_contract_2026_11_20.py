"""Entry-field contract + retired DSR engine."""
import numpy as np
import pytest

from alpha_engine import pick_contract
from probabilistic_sharpe_engine import ProbabilisticSharpeAnalyzer


def test_derives_from_timestamp_when_entry_time_blank():
    ts, src = pick_contract.derive_entry_time({"entry_time": "", "timestamp": "2026-11-20T01:12:41Z"})
    assert ts == "2026-11-20T01:12:41Z" and src == "timestamp"


def test_entry_time_wins_over_timestamp():
    ts, src = pick_contract.derive_entry_time(
        {"entry_time": "2026-11-19T10:00:00Z", "timestamp": "2026-11-20T01:12:41Z"})
    assert ts == "2026-11-19T10:00:00Z" and src == "entry_time"


@pytest.mark.parametrize("raw,expected", [
    ("2026-11-20 01:12:41", "2026-11-20T01:12:41Z"),
    ("2026-11-20", "2026-11-20T00:00:00Z"),
    ("2026-11-20T01:12:41+02:00", "2026-11-19T23:12:41Z"),
    ("", None), (None, None), ("not a date", None),
])
def test_timestamp_normalisation(raw, expected):
    assert pick_contract.to_utc_iso(raw) == expected


def test_never_invents_a_price():
    out = pick_contract.ensure_entry_fields({"symbol": "BTCUSDT", "timestamp": "2026-11-20T00:00:00Z"})
    assert out["entry_time"] == "2026-11-20T00:00:00Z"
    assert out["entry_price"] is None
    assert out["entry_fields_complete"] is False


def test_zero_price_is_not_a_price():
    _, src = pick_contract.derive_entry_price({"entry_price": 0, "price": 101.5})
    assert src == "price"


def test_coverage_maths():
    rows = [
        {"entry_time": "2026-11-20T00:00:00Z", "entry_price": 10.0},
        {"entry_time": "", "entry_price": 5.0},
        {"timestamp": "2026-11-19T00:00:00Z", "entry_price": None},
        {},
    ]
    cov = pick_contract.coverage(rows)
    assert cov["n"] == 4
    assert cov["entry_time_pct"] == 25.0
    assert cov["entry_price_pct"] == 50.0
    assert cov["both_pct"] == 25.0


def test_ensure_does_not_mutate_input():
    src = {"entry_price": 3.0}
    pick_contract.ensure_entry_fields(src)
    assert "entry_time" not in src


def _noise(n=400, seed=7):
    return np.random.default_rng(seed).normal(0, 0.01, n)


def test_dsr_no_longer_scores_pure_noise_as_confident():
    """The old engine returned 1.0282 on zero-edge noise; that must be impossible now."""
    eng = ProbabilisticSharpeAnalyzer()
    out = eng.calculate_probabilistic_sharpe(_noise(), n_trials=100)
    assert 0.0 <= out["deflated_sharpe"] <= 1.0
    assert out["deflated_sharpe"] < 0.95
    assert out["deprecated"] is True


def test_expected_max_grows_with_trials_not_with_sample_length():
    eng = ProbabilisticSharpeAnalyzer()
    few = eng._calculate_expected_max_sharpe(n_trials=2, n_obs=1000)
    many = eng._calculate_expected_max_sharpe(n_trials=500, n_obs=1000)
    assert many > few > 0
    # one trial means no multiplicity correction at all
    assert eng._calculate_expected_max_sharpe(n_trials=1, n_obs=1000) == 0.0
    # holding trials fixed, more data must LOWER the expected maximum, not raise it
    assert eng._calculate_expected_max_sharpe(n_trials=100, n_obs=1000) < \
           eng._calculate_expected_max_sharpe(n_trials=100, n_obs=100)

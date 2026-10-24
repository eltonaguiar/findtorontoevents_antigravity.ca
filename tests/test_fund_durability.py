import numpy as np
import pandas as pd
import pytest
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools.fund_durability import metrics, rank_at, basket_path, paired_block_interval, compare_funds, book_returns


def test_daily_drawdown_includes_unrealized_loss():
    result = metrics(pd.Series([0, -0.8, 4.5], index=pd.date_range("2020-01-01", periods=3)))
    assert result["mdd_pct"] == pytest.approx(80)
    assert result["compound_pct"] == pytest.approx(10)


def test_past_only_rank_ignores_future_prices():
    dates = pd.bdate_range("2015-01-01", "2020-01-01")
    frame = pd.DataFrame({"A": np.linspace(100, 200, len(dates)), "B": np.linspace(100, 150, len(dates))}, index=dates)
    cut = pd.Timestamp("2018-12-31")
    before = rank_at(frame, cut, "trailing_total_return", min_obs=700)
    frame.loc[frame.index > cut, "B"] = 1000000
    assert rank_at(frame, cut, "trailing_total_return", min_obs=700) == before
    assert before[0][0] == "A"


def test_basket_weights_drift_not_daily_rebalanced():
    prices = pd.DataFrame({"A": [100, 200, 200], "B": [100, 100, 200]}, index=pd.date_range("2020-01-01", periods=3))
    daily = basket_path(prices, ["A", "B"], cost=0)
    assert (1 + daily).prod() == pytest.approx(2)
    assert daily.iloc[-1] == pytest.approx(1/3)


def test_basket_charges_both_sides_without_double_expenses():
    frame = pd.DataFrame({"A": [100, 100, 110]}, index=pd.date_range("2020-01-01", periods=3))
    daily = basket_path(frame, ["A"], cost=0.01)
    assert (1 + daily).prod() == pytest.approx(0.99 * 1.1 * 0.99)


def test_missing_prices_raise_instead_of_filling():
    frame = pd.DataFrame({"A": [100, np.nan, 110]}, index=pd.date_range("2020-01-01", periods=3))
    with pytest.raises(ValueError, match="price"):
        basket_path(frame, ["A"], cost=0)


def test_block_interval_is_deterministic_and_paired():
    frame = pd.Series(np.tile([0.001, -0.0005, 0.0005], 60))
    a = paired_block_interval(frame, seed=42, simulations=50)
    assert a == paired_block_interval(frame, seed=42, simulations=50)
    assert a[0] > 0


def test_low_volatility_ranking_direction():
    dates = pd.bdate_range("2015-01-01", "2019-01-01")
    t = np.arange(len(dates))
    frame = pd.DataFrame({"quiet": 100 * 1.0002 ** t, "wild": 100 * 1.0002 ** t * np.exp(0.1*np.sin(t))}, index=dates)
    assert rank_at(frame, dates[-1], "trailing_low_volatility", min_obs=700)[0][0] == "quiet"


def test_comparison_uses_exact_common_inception_dates():
    dates = pd.bdate_range("2020-01-01", periods=200)
    a = pd.Series(np.linspace(100, 200, 200), index=dates)
    b = a.iloc[50:] * 5
    result = compare_funds({"A": a, "B": b}, ["A", "B"])
    assert result["first"] == str(dates[50].date())
    assert result["metrics"]["A"] == pytest.approx(result["metrics"]["B"])
    assert result["metrics"]["A"]["n_days"] == 150


def test_comparison_rejects_mixed_currencies_and_duplicate_symbols():
    dates = pd.bdate_range("2020-01-01", periods=200)
    a = pd.Series(np.linspace(100, 200, 200), index=dates)
    with pytest.raises(ValueError, match="USD and CAD"):
        compare_funds({"A": a, "B.TO": a}, ["A", "B.TO"])
    with pytest.raises(ValueError, match="distinct"):
        compare_funds({"A": a}, ["A", "A"])


def test_skipped_schedule_days_remain_zero_yield_cash():
    dates = pd.bdate_range("2020-01-01", periods=10)
    frame = pd.DataFrame({"A": np.linspace(100, 110, 10)}, index=dates)
    schedules = [
        {"entry": dates[0], "exit": dates[2], "selected": ["A"]},
        {"entry": dates[7], "exit": dates[9], "selected": ["A"]},
    ]
    daily = book_returns(frame, schedules, 0.001)
    assert daily.index.equals(dates)
    assert (daily.iloc[3:7] == 0).all()
    expected = (frame.A.iloc[2]/frame.A.iloc[0])*(frame.A.iloc[9]/frame.A.iloc[7])*0.999**4
    assert (1+daily).prod() == pytest.approx(expected)
    assert metrics(daily)["n_days"] == 10


def test_compare_cli_reads_hashed_cache_and_writes_strict_json(tmp_path):
    dates = pd.bdate_range("2020-01-01", periods=150)
    manifest = {}
    for symbol in ["A", "B"]:
        payload = {"chart": {"result": [{
            "timestamp": [int(d.timestamp()) for d in dates],
            "indicators": {"adjclose": [{"adjclose": np.linspace(100, 110, len(dates)).tolist()}]},
        }]}}
        raw = json.dumps(payload).encode()
        (tmp_path/(symbol+".json")).write_bytes(raw)
        manifest[symbol] = {"status": "OK", "sha256": hashlib.sha256(raw).hexdigest()}
    (tmp_path/"manifest.json").write_text(json.dumps(manifest))
    output = tmp_path/"comparison.json"
    script = Path(__file__).resolve().parents[1]/"tools/fund_durability.py"
    completed = subprocess.run(
        [sys.executable, str(script), "compare", "--cache", str(tmp_path),
         "--symbols", "A", "B", "--output", str(output)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text())
    assert result["metrics"]["A"]["n_days"] == 150
    assert set(result["input_manifest"]) == {"A", "B"}
    assert result["currency"] == "USD"


def test_shared_rebalance_date_charges_old_exit_and_new_entry():
    dates = pd.bdate_range("2020-01-01", periods=3)
    frame = pd.DataFrame({"A": [100, 110, 121]}, index=dates)
    schedules = [
        {"entry": dates[0], "exit": dates[1], "selected": ["A"]},
        {"entry": dates[1], "exit": dates[2], "selected": ["A"]},
    ]
    daily = book_returns(frame, schedules, 0.01)
    assert len(daily) == 3
    assert (1+daily).prod() == pytest.approx(1.21*0.99**4)
    assert 1+daily.iloc[1] == pytest.approx(1.1*0.99**2)

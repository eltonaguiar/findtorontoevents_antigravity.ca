import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from tools.crypto_published_strategies import backtest, gates


def prices(values):
    return pd.DataFrame({"close": values}, index=pd.date_range("2020-01-01", periods=len(values)))


def trade(df, start=0, end=None):
    end = len(df) - 1 if end is None else end
    return {
        "entry_day": df.index[start],
        "exit_day": df.index[end],
        "entry": float(df.close.iloc[start]),
        "exit": float(df.close.iloc[end]),
        "pnl_pct": (df.close.iloc[end] / df.close.iloc[start] - 1) * 100,
    }


def test_signal_must_not_fill_at_the_close_that_created_it():
    df = prices([100, 110, 120, 130, 140])
    trades = backtest(df, [1, 1, 0, 0, 0], "causal")
    assert trades[0]["entry_day"] == df.index[1]
    assert trades[0]["entry"] == 110
    assert trades[0]["exit_day"] == df.index[3]
    assert trades[0]["exit"] == 130


def test_final_signal_cannot_create_zero_duration_trade():
    df = prices([100, 110, 120])
    assert backtest(df, [0, 1, 1], "too-late") == []


def test_closed_trade_endpoints_cannot_establish_drawdown():
    df = prices([100, 20, 110])
    result = gates([trade(df)], "missing-path", costs=0)
    assert result["mdd"] is None
    assert result["gates"]["g4_mdd"] is False


def test_daily_marks_capture_eighty_percent_loss_inside_winning_trade():
    df = prices([100, 20, 110])
    result = gates([trade(df)], "hidden-loss", costs=0, prices=df)
    assert result["mdd"] == pytest.approx(80)
    assert result["compound_pct"] == pytest.approx(10)
    assert result["gates"]["g4_mdd"] is False
    assert result["equity_basis"] == "daily_close_mtm"


def test_daily_fees_and_idle_cash_are_accounted_for():
    df = prices([100, 100, 110, 220])
    result = gates([trade(df, 1, 2)], "fees", costs=0.01, prices=df)
    assert result["compound_pct"] == pytest.approx((0.99 * 1.1 * 0.99 - 1) * 100)
    assert result["mdd"] >= 1


def test_unimplemented_proofs_are_null_and_cannot_pass():
    df = prices([100, 90, 120])
    result = gates([trade(df)], "proof", prices=df)
    for field in ("mc_pct", "dsr", "bootstrap_ci_lo"):
        assert result[field] is None
    for name in ("g3_ci", "g5_mc", "g6_dsr", "g8_conc"):
        assert result["gates"][name] is False
    assert result["gate"] == "FAIL"
    assert result["top_symbol_pct"] == 100
    assert all(type(v) is bool for v in result["gates"].values())
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("values", [[100, 0, 110], [100, float("nan"), 110]])
def test_invalid_prices_fail_explicitly(values):
    df = prices(values)
    with pytest.raises(ValueError, match="price"):
        gates([trade(df)], "invalid", prices=df)


def test_missing_daily_path_is_not_forward_filled():
    df = prices([100, 20, 110]).drop(pd.Timestamp("2020-01-02"))
    with pytest.raises(ValueError, match="daily"):
        gates([trade(df)], "missing-day", prices=df)


def test_overlapping_trades_are_not_double_funded():
    df = prices([100, 90, 110, 120])
    with pytest.raises(ValueError, match="overlap"):
        gates([trade(df, 0, 2), trade(df, 1, 3)], "overlap", prices=df)


def test_recorded_fills_must_match_daily_path():
    df = prices([100, 90, 110])
    record = trade(df)
    record["entry"] = 50
    with pytest.raises(ValueError, match="fill"):
        gates([record], "wrong-fill", prices=df)


def test_no_loss_pf_is_undefined_not_infinity():
    df = prices([100, 110, 120])
    result = gates([trade(df)], "no-loss", costs=0, prices=df)
    assert result["pf_cost"] is None
    assert result["gates"]["g2_pf"] is False
    json.dumps(result, allow_nan=False)


def test_cli_wires_daily_prices_and_emits_native_json(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "results.json"
    trials = tmp_path / "trials.csv"
    command = [
        sys.executable, str(root / "tools/crypto_published_strategies.py"),
        "--input", str(root / "audit_dashboard/data/btcusd_daily.csv"),
        "--output", str(output), "--trials", str(trials),
    ]
    subprocess.run(command, check=True, capture_output=True)
    first = output.read_bytes()
    results = json.loads(first)
    assert len(results) == 6
    assert all(r["equity_basis"] == "daily_close_mtm" for r in results)
    btc = next(r for r in results if r["label"] == "BTC 12-month absolute momentum")
    assert btc["n"] == 13
    assert btc["mdd"] == pytest.approx(81.74, abs=0.02)
    assert btc["cagr_pct"] == pytest.approx(53.35, abs=0.02)
    assert all(r["gate"] == "FAIL" for r in results)
    assert all(type(value) is bool for r in results for value in r["gates"].values())
    subprocess.run(command, check=True, capture_output=True)
    assert output.read_bytes() == first
    assert len(trials.read_text().splitlines()) == 12


def test_page_uses_rebuilt_btc_evidence_instead_of_static_pass_claims():
    root = Path(__file__).resolve().parents[1]
    page = (root / "audit_dashboard/opencode_paper_trading.html").read_text()
    assert "id=\"btc-mtm-evidence\"" in page
    assert "data/published_strategy_gates.json" in page
    assert "equity_basis !== 'daily_close_mtm'" in page

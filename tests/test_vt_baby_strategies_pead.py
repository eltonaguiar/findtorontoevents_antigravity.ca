import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from alpha_engine.vt_baby_strategies import vt_equity_earnings_drift_pead


def _mk_ohlcv(rows: int = 60) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    base = pd.Series(range(rows), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": 100.0 + base * 0.1,
            "high": 101.0 + base * 0.1,
            "low": 99.0 + base * 0.1,
            "close": 100.5 + base * 0.1,
            "volume": 2_000_000 + base * 1000,
        },
        index=idx,
    )


def _write_earnings(tmp_path, symbol: str, surprise_pct: float, days_ago: int) -> None:
    d = tmp_path / symbol
    d.mkdir(parents=True, exist_ok=True)
    earn_date = (datetime.now(timezone.utc).date() - timedelta(days=days_ago)).isoformat()
    payload = {
        "ticker": symbol,
        "history": [
            {"date": earn_date, "eps_actual": 1.0, "eps_estimate": 0.9, "surprise_pct": surprise_pct}
        ],
    }
    (d / "latest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_pead_disabled_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "0")
    _write_earnings(tmp_path, "AAPL", 7.0, days_ago=2)
    out = vt_equity_earnings_drift_pead({"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)})
    assert out == []


def test_pead_enabled_uses_real_earnings_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_earnings(tmp_path, "AAPL", 7.0, days_ago=2)
    out = vt_equity_earnings_drift_pead({"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)})
    assert out, "expected at least one PEAD signal with recent positive surprise"
    assert out[0]["strategy"] == "vt_earnings_pead"
    assert out[0]["symbol"] == "AAPL"
    assert out[0]["extra"]["surprise_pct"] == 7.0


def test_pead_skips_stale_earnings(monkeypatch, tmp_path):
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_earnings(tmp_path, "AAPL", 8.0, days_ago=30)
    out = vt_equity_earnings_drift_pead({"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)})
    assert out == []


def test_pead_returns_empty_when_earnings_cache_missing(monkeypatch, tmp_path):
    """Fail-safe: non-existent earnings_dir must not raise."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    missing = tmp_path / "does_not_exist"
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(missing)}
    )
    assert out == []


def test_pead_returns_empty_when_earnings_cache_is_invalid_json(monkeypatch, tmp_path):
    """Fail-safe: malformed JSON in cache must not raise."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    d = tmp_path / "AAPL"
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text("{not valid json,,,", encoding="utf-8")
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


@pytest.mark.parametrize("payload", ['"a string"', "42", "null", "[1, 2, 3]"])
def test_pead_returns_empty_when_earnings_cache_is_unexpected_type(
    monkeypatch, tmp_path, payload
):
    """Fail-safe: non-dict top-level JSON must not raise (Bug 1 regression)."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    d = tmp_path / "AAPL"
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(payload, encoding="utf-8")
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


def _write_raw_payload(tmp_path, symbol: str, payload: dict) -> None:
    d = tmp_path / symbol
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("history_value", ["not a list", 42, 3.14, True])
def test_pead_handles_non_list_history_field(monkeypatch, tmp_path, history_value):
    """Wave 2.3 regression: payload['history'] not a list must not raise."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_raw_payload(tmp_path, "AAPL", {"ticker": "AAPL", "history": history_value})
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


@pytest.mark.parametrize(
    "history_value",
    [
        ["a string"],
        [123],
        [3.14],
        [None],
        [["nested", "list"]],
        [{"date": "2026-04-26", "surprise_pct": 5.0}, "oops"],
        [42, {"date": "2026-04-26", "surprise_pct": 5.0}],
    ],
)
def test_pead_handles_non_dict_history_entry(monkeypatch, tmp_path, history_value):
    """Wave 2.3 regression: non-dict entries inside history list must not raise."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_raw_payload(tmp_path, "AAPL", {"ticker": "AAPL", "history": history_value})
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    # Either empty (all entries skipped) or a single PEAD signal from the one
    # well-formed entry. Either way, no AttributeError.
    assert isinstance(out, list)


def test_pead_handles_empty_history_list(monkeypatch, tmp_path):
    """Wave 2.3 regression: payload['history'] = [] must return [] cleanly."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_raw_payload(tmp_path, "AAPL", {"ticker": "AAPL", "history": []})
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


def test_pead_handles_history_none(monkeypatch, tmp_path):
    """Wave 2.3 regression: payload['history'] = None must return [] cleanly."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_raw_payload(tmp_path, "AAPL", {"ticker": "AAPL", "history": None})
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


def test_pead_handles_missing_history_key(monkeypatch, tmp_path):
    """Wave 2.3 regression: payload missing 'history' key entirely must return []."""
    monkeypatch.setenv("UEPS_ENABLE_PEAD", "1")
    _write_raw_payload(tmp_path, "AAPL", {"ticker": "AAPL"})
    out = vt_equity_earnings_drift_pead(
        {"AAPL": _mk_ohlcv()}, {"earnings_dir": str(tmp_path)}
    )
    assert out == []


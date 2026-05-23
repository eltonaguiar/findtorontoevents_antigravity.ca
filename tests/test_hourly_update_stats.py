"""Tests for audit_dashboard.generate_hourly_update quant metrics + staleness + healthchecks."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make audit_dashboard importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "audit_dashboard"))

import generate_hourly_update as ghu  # noqa: E402


def _make_state():
    """3-portfolio fixture: one winner, one loser, one mixed."""
    return {
        "winner_only": {
            "initial_capital": 10000,
            "equity": 10300,
            "wins": 3,
            "losses": 0,
            "closed": [
                {"pnl_pct": 1.0},
                {"pnl_pct": 1.5},
                {"pnl_pct": 0.5},
            ],
            "positions": [],
        },
        "loser_only": {
            "initial_capital": 10000,
            "equity": 9700,
            "wins": 0,
            "losses": 3,
            "closed": [
                {"pnl_pct": -1.0},
                {"pnl_pct": -2.0},
                {"pnl_pct": -0.5},
            ],
            "positions": [],
        },
        "mixed": {
            "initial_capital": 10000,
            "equity": 10100,
            "wins": 2,
            "losses": 2,
            "closed": [
                {"pnl_pct": 2.0},
                {"pnl_pct": 1.0},
                {"pnl_pct": -1.0},
                {"pnl_pct": -0.5},
            ],
            "positions": [],
        },
    }


def test_portfolio_stats_winner_only():
    stats = ghu.compute_portfolio_stats(_make_state())
    w = stats["winner_only"]
    assert w["wins"] == 3
    assert w["losses"] == 0
    assert w["wr"] == 1.0
    assert w["avg_win"] == pytest.approx(1.0)
    assert w["avg_loss"] == 0.0
    assert w["expectancy"] == pytest.approx(1.0)
    assert w["profit_factor"] is None  # undefined with zero losses


def test_portfolio_stats_loser_only():
    stats = ghu.compute_portfolio_stats(_make_state())
    l = stats["loser_only"]
    assert l["wins"] == 0
    assert l["losses"] == 3
    assert l["wr"] == 0.0
    assert l["expectancy"] == pytest.approx(-1.1666666, rel=1e-3)  # avg of -1, -2, -0.5
    assert l["profit_factor"] == 0.0


def test_portfolio_stats_mixed_expectancy_and_pf():
    stats = ghu.compute_portfolio_stats(_make_state())
    m = stats["mixed"]
    assert m["wins"] == 2
    assert m["losses"] == 2
    assert m["wr"] == 0.5
    # avg_win = (2+1)/2 = 1.5; avg_loss = (-1-0.5)/2 = -0.75
    # expectancy = 0.5*1.5 + 0.5*-0.75 = 0.375
    assert m["expectancy"] == pytest.approx(0.375)
    # PF = gross_win / gross_loss = 3.0 / 1.5 = 2.0
    assert m["profit_factor"] == pytest.approx(2.0)


def test_overall_stats_aggregation():
    pstats = ghu.compute_portfolio_stats(_make_state())
    overall = ghu.compute_overall_stats(pstats)
    # Total wins = 3 + 0 + 2 = 5
    # Total losses = 0 + 3 + 2 = 5
    assert overall["wins"] == 5
    assert overall["losses"] == 5
    assert overall["n"] == 10
    assert overall["wr"] == 0.5
    # gross_win = 1+1.5+0.5 + 2+1 = 6.0
    # gross_loss = 1+2+0.5 + 1+0.5 = 5.0
    assert overall["gross_win"] == pytest.approx(6.0)
    assert overall["gross_loss"] == pytest.approx(5.0)
    assert overall["profit_factor"] == pytest.approx(6.0 / 5.0)


def test_trade_pnl_pct_graceful_missing():
    assert ghu._trade_pnl_pct({}) == 0.0
    assert ghu._trade_pnl_pct({"pnl_pct": None}) == 0.0
    assert ghu._trade_pnl_pct({"pnl_pct": "not a number"}) == 0.0
    assert ghu._trade_pnl_pct({"pnl": 1.5}) == 1.5  # falls back to pnl


def test_staleness_first_run(tmp_path, monkeypatch):
    marker = tmp_path / "last_run.json"
    monkeypatch.setattr(ghu, "LAST_RUN_MARKER", str(marker))
    is_stale, age, msg = ghu.check_staleness()
    assert is_stale is False
    assert age is None
    assert "first run" in msg


def test_staleness_fresh(tmp_path, monkeypatch):
    marker = tmp_path / "last_run.json"
    monkeypatch.setattr(ghu, "LAST_RUN_MARKER", str(marker))
    now = datetime.now(timezone.utc)
    # Write a marker 30 min ago
    marker.parent.mkdir(parents=True, exist_ok=True)
    with open(marker, "w", encoding="utf-8") as f:
        json.dump({"last_run": (now - timedelta(minutes=30)).isoformat()}, f)
    is_stale, age, msg = ghu.check_staleness(now=now)
    assert is_stale is False
    assert age == pytest.approx(0.5, rel=1e-2)
    assert "fresh" in msg


def test_staleness_stale(tmp_path, monkeypatch):
    marker = tmp_path / "last_run.json"
    monkeypatch.setattr(ghu, "LAST_RUN_MARKER", str(marker))
    now = datetime.now(timezone.utc)
    # Write a marker 3 hours ago
    marker.parent.mkdir(parents=True, exist_ok=True)
    with open(marker, "w", encoding="utf-8") as f:
        json.dump({"last_run": (now - timedelta(hours=3)).isoformat()}, f)
    is_stale, age, msg = ghu.check_staleness(now=now)
    assert is_stale is True
    assert age == pytest.approx(3.0, rel=1e-2)
    assert "STALE" in msg


def test_write_and_read_marker_round_trip(tmp_path, monkeypatch):
    marker = tmp_path / "last_run.json"
    monkeypatch.setattr(ghu, "LAST_RUN_MARKER", str(marker))
    now = datetime.now(timezone.utc)
    ghu.write_last_run_marker(now=now)
    read = ghu.read_last_run_marker()
    assert read is not None
    # Compare to ISO seconds precision
    assert abs((read - now).total_seconds()) < 1.0


def test_read_marker_corrupt_returns_none(tmp_path, monkeypatch):
    marker = tmp_path / "last_run.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    with open(marker, "w", encoding="utf-8") as f:
        f.write("not valid json")
    monkeypatch.setattr(ghu, "LAST_RUN_MARKER", str(marker))
    assert ghu.read_last_run_marker() is None


def test_load_state_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(ghu, "STATE_FILE", str(tmp_path / "nonexistent.json"))
    with pytest.raises(FileNotFoundError):
        ghu.load_state()


def test_load_state_corrupt_raises(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    p.write_text("{not valid")
    monkeypatch.setattr(ghu, "STATE_FILE", str(p))
    with pytest.raises(json.JSONDecodeError):
        ghu.load_state()


def test_load_integrity_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(ghu, "REPORT_FILE", str(tmp_path / "nonexistent.json"))
    assert ghu.load_integrity() is None


def test_load_integrity_corrupt_returns_none(tmp_path, monkeypatch):
    p = tmp_path / "integrity.json"
    p.write_text("{not valid")
    monkeypatch.setattr(ghu, "REPORT_FILE", str(p))
    assert ghu.load_integrity() is None  # graceful, non-fatal


# ---------- Healthchecks.io dead-man's-switch ----------

def test_healthchecks_no_env_var_noop(monkeypatch):
    """Unset env var → ping is a no-op that returns False."""
    monkeypatch.delenv(ghu.HEALTHCHECKS_URL_ENV, raising=False)
    assert ghu.ping_healthchecks() is False


def test_healthchecks_empty_env_var_noop(monkeypatch):
    """Empty env var → ping is a no-op."""
    monkeypatch.setenv(ghu.HEALTHCHECKS_URL_ENV, "   ")
    assert ghu.ping_healthchecks() is False


def test_healthchecks_explicit_url_none_noop():
    """Explicit None url + no env var → no-op."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop(ghu.HEALTHCHECKS_URL_ENV, None)
        assert ghu.ping_healthchecks(url=None) is False


def test_healthchecks_success_returns_true(monkeypatch):
    """Successful 200 response → returns True."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        ok = ghu.ping_healthchecks(url="https://hc-ping.com/fake-uuid")
    assert ok is True
    mock_open.assert_called_once()


def test_healthchecks_non_2xx_returns_false(monkeypatch):
    """Non-2xx response → returns False but does not raise."""
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok = ghu.ping_healthchecks(url="https://hc-ping.com/fake-uuid")
    assert ok is False


def test_healthchecks_network_failure_swallowed():
    """Network exception → logged and returns False; must not raise."""
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        ok = ghu.ping_healthchecks(url="https://hc-ping.com/fake-uuid")
    assert ok is False  # No raise — caller must NEVER be blocked by monitoring outage

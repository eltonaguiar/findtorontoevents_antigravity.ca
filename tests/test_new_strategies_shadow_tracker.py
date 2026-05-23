"""Tests for tools/new_strategies_shadow_tracker.py (M-075)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import under test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.new_strategies_shadow_tracker import (
    _compute_summary,
    _resolve_pick,
    run_shadow_tracker,
)


def _pick(symbol="SPY", direction="LONG", tp=110.0, sl=90.0, entry=100.0, age_days=0, strategy="test_strat") -> dict:
    entry_dt = datetime.now(timezone.utc) - timedelta(days=age_days)
    return {
        "id": f"{symbol}:{strategy}:{entry_dt.isoformat()}",
        "symbol": symbol,
        "strategy": strategy,
        "direction": direction,
        "take_profit": tp,
        "stop_loss": sl,
        "entry_price": entry,
        "entry_time": entry_dt.isoformat(),
        "max_hold_bars": 30,
        "asset_class": "EQUITY",
    }


# ── _compute_summary ─────────────────────────────────────────────────────────

def test_summary_empty():
    result = _compute_summary([])
    assert result["n_total"] == 0
    assert result["win_rate"] is None
    assert result["profit_factor"] is None


def test_summary_all_open():
    picks = [_pick(), _pick("QQQ")]
    result = _compute_summary(picks)
    assert result["n_open"] == 2
    assert result["n_closed"] == 0
    assert result["win_rate"] is None


def test_summary_wins_and_losses():
    p1 = {**_pick("SPY"), "shadow_outcome": "WIN", "shadow_pnl_pct": 10.0}
    p2 = {**_pick("QQQ"), "shadow_outcome": "LOSS", "shadow_pnl_pct": -5.0}
    result = _compute_summary([p1, p2])
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["win_rate"] == pytest.approx(0.5)
    assert result["profit_factor"] == pytest.approx(2.0)  # 10 / 5


def test_summary_all_wins_pf_sentinel():
    p = {**_pick("SPY"), "shadow_outcome": "WIN", "shadow_pnl_pct": 5.0}
    result = _compute_summary([p])
    assert result["profit_factor"] == 9999.0  # sentinel for infinity


def test_summary_no_wins_pf_zero():
    p = {**_pick("SPY"), "shadow_outcome": "LOSS", "shadow_pnl_pct": -5.0}
    result = _compute_summary([p])
    assert result["profit_factor"] == pytest.approx(0.0)  # gross_win=0 / gross_loss=5 = 0


def test_summary_expired_not_counted():
    p = {**_pick("SPY"), "shadow_outcome": "EXPIRED"}
    result = _compute_summary([p])
    assert result["n_expired"] == 1
    assert result["n_closed"] == 0
    assert result["win_rate"] is None


def test_summary_per_strategy_breakdown():
    p1 = {**_pick("SPY", strategy="low_vol"), "shadow_outcome": "WIN", "shadow_pnl_pct": 8.0}
    p2 = {**_pick("QQQ", strategy="low_vol"), "shadow_outcome": "LOSS", "shadow_pnl_pct": -4.0}
    p3 = {**_pick("GLD", strategy="cot_roll"), "shadow_outcome": "WIN", "shadow_pnl_pct": 6.0}
    result = _compute_summary([p1, p2, p3])
    assert result["by_strategy"]["low_vol"]["wins"] == 1
    assert result["by_strategy"]["low_vol"]["losses"] == 1
    assert result["by_strategy"]["cot_roll"]["wins"] == 1


# ── _resolve_pick ─────────────────────────────────────────────────────────────

def test_resolve_expired_pick():
    pick = _pick(age_days=35)  # past max_hold_bars=30
    now = datetime.now(timezone.utc)
    result = _resolve_pick(pick, now)
    assert result["shadow_outcome"] == "EXPIRED"


def test_resolve_long_win(monkeypatch):
    pick = _pick(direction="LONG", tp=110.0, sl=90.0, entry=100.0, age_days=1)
    now = datetime.now(timezone.utc)

    mock_ticker = MagicMock()
    import pandas as pd
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [105.0], "High": [112.0], "Low": [102.0]}
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda sym: mock_ticker)

    result = _resolve_pick(pick, now)
    assert result["shadow_outcome"] == "WIN"
    assert result["shadow_exit_price"] == 110.0
    assert result.get("shadow_pnl_pct", 0) > 0


def test_resolve_long_loss(monkeypatch):
    pick = _pick(direction="LONG", tp=110.0, sl=90.0, entry=100.0, age_days=1)
    now = datetime.now(timezone.utc)

    mock_ticker = MagicMock()
    import pandas as pd
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [88.0], "High": [98.0], "Low": [85.0]}
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda sym: mock_ticker)

    result = _resolve_pick(pick, now)
    assert result["shadow_outcome"] == "LOSS"
    assert result["shadow_exit_price"] == 90.0


def test_resolve_short_win(monkeypatch):
    pick = _pick(direction="SHORT", tp=88.0, sl=112.0, entry=100.0, age_days=1)
    now = datetime.now(timezone.utc)

    mock_ticker = MagicMock()
    import pandas as pd
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [87.0], "High": [96.0], "Low": [85.0]}
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda sym: mock_ticker)

    result = _resolve_pick(pick, now)
    assert result["shadow_outcome"] == "WIN"


def test_resolve_still_open(monkeypatch):
    pick = _pick(direction="LONG", tp=110.0, sl=90.0, entry=100.0, age_days=1)
    now = datetime.now(timezone.utc)

    mock_ticker = MagicMock()
    import pandas as pd
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [102.0], "High": [105.0], "Low": [101.0]}
    )
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda sym: mock_ticker)

    result = _resolve_pick(pick, now)
    assert "shadow_outcome" not in result or result.get("shadow_outcome") is None


# ── run_shadow_tracker (integration) ─────────────────────────────────────────

def test_kill_switch(monkeypatch, tmp_path):
    monkeypatch.setenv("NEW_STRATS_SHADOW_DISABLED", "1")
    rc = run_shadow_tracker(dry_run=True)
    assert rc == 0


def test_missing_picks_file(monkeypatch, tmp_path):
    import tools.new_strategies_shadow_tracker as mod
    monkeypatch.setattr(mod, "PICKS_PATH", tmp_path / "nonexistent.json")
    monkeypatch.setattr(mod, "LOG_PATH", tmp_path / "log.json")
    rc = run_shadow_tracker(dry_run=True)
    assert rc == 1


def test_dry_run_does_not_write(monkeypatch, tmp_path):
    import tools.new_strategies_shadow_tracker as mod

    picks = [_pick("SPY"), _pick("QQQ")]
    picks_file = tmp_path / "picks.json"
    picks_file.write_text(json.dumps(picks))
    log_file = tmp_path / "log.json"

    monkeypatch.setattr(mod, "PICKS_PATH", picks_file)
    monkeypatch.setattr(mod, "LOG_PATH", log_file)
    monkeypatch.delenv("NEW_STRATS_SHADOW_DISABLED", raising=False)

    # Mock yfinance to return still-open prices
    import pandas as pd
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [102.0], "High": [105.0], "Low": [101.0]}
    )
    with patch("yfinance.Ticker", return_value=mock_ticker):
        rc = run_shadow_tracker(dry_run=True)

    assert rc == 0
    assert not log_file.exists()

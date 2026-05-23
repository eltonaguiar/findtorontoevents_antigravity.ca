from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from tools.hyrotrader_log_trade import close_trade, open_trade, sync_picks_file


def _seed_journal() -> dict:
    return {
        "baseline_equity_usdt": 5000,
        "trades": [],
    }


def _seed_picks(path: Path) -> None:
    payload = {
        "picks": [
            {
                "id": "hyro-2026-04-11-btc",
                "symbol_hint": "BTCUSDT",
                "status": "planned",
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "opened_at": None,
                "closed_at": None,
                "pnl_pct": None,
                "sl_confirmed": False,
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_open_trade_syncs_pick_state(tmp_path: Path) -> None:
    journal = _seed_journal()
    picks_path = tmp_path / "hyrotrader_picks.json"
    _seed_picks(picks_path)
    args = Namespace(
        pick_id="hyro-2026-04-11-btc",
        symbol="BTCUSDT",
        direction="LONG",
        entry_price=70000.0,
        entry_time="2026-04-11T12:00:00Z",
        stop_loss=69000.0,
        take_profit=72000.0,
    )

    trade = open_trade(journal, args)
    changed = sync_picks_file(trade, closed=False, picks_path=picks_path)

    assert changed is True
    picks = json.loads(picks_path.read_text(encoding="utf-8"))
    pick = picks["picks"][0]
    assert pick["status"] == "open"
    assert pick["entry_price"] == 70000.0
    assert pick["stop_loss"] == 69000.0
    assert pick["take_profit"] == 72000.0
    assert pick["opened_at"] == "2026-04-11T12:00:00Z"
    assert pick["sl_confirmed"] is True
    assert pick["position_size_usdt"] > 0
    assert pick["risk_amount_usdt"] == 50.0


def test_close_trade_syncs_pick_state(tmp_path: Path) -> None:
    journal = _seed_journal()
    picks_path = tmp_path / "hyrotrader_picks.json"
    _seed_picks(picks_path)
    open_args = Namespace(
        pick_id="hyro-2026-04-11-btc",
        symbol="BTCUSDT",
        direction="LONG",
        entry_price=70000.0,
        entry_time="2026-04-11T12:00:00Z",
        stop_loss=69000.0,
        take_profit=72000.0,
    )
    trade = open_trade(journal, open_args)
    sync_picks_file(trade, closed=False, picks_path=picks_path)

    close_args = Namespace(
        close_pick_id="hyro-2026-04-11-btc",
        exit_price=71500.0,
        exit_time="2026-04-11T16:00:00Z",
        exit_reason="take_profit",
        bars_held=4,
    )
    closed = close_trade(journal, close_args)
    changed = sync_picks_file(closed, closed=True, picks_path=picks_path)

    assert changed is True
    picks = json.loads(picks_path.read_text(encoding="utf-8"))
    pick = picks["picks"][0]
    assert pick["status"] == "closed"
    assert pick["closed_at"] == "2026-04-11T16:00:00Z"
    assert pick["pnl_pct"] > 0
    assert pick["pnl_usdt"] > 0
    assert pick["exit_reason"] == "take_profit"

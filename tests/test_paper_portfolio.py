"""Deterministic unit tests for tools/paper_portfolio.py - synthetic prices, no network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.paper_portfolio as pp  # noqa: E402


def _book(cash=100000.0, cost_bps=0.0):
    return pp.new_book(cash, cost_bps)


def _fixed_prices(mapping):
    """price_fn stub: symbol -> {"px","ts","source"} or None."""
    def fn(sym):
        v = mapping.get(sym)
        if v is None:
            return None
        return {"px": v, "ts": "2026-11-22T00:00:00Z", "source": "stub"}
    return fn


# 1 ---------------------------------------------------------------- mark to market
def test_buy_100_at_100_mark_110():
    book = _book(cash=100000.0, cost_bps=0.0)
    pp.open_position(book, "BTC/USDT", "LONG", 100, 100.0)

    payload = pp.mark_book(book, price_fn=_fixed_prices({"BTC/USDT": 110.0}))

    assert payload["positions_value"] == 11000.0          # 100 * 110
    assert payload["equity"] == book["cash"] + 11000.0     # cash + market value
    assert payload["unrealized_pnl"] == 1000.0             # (110-100)*100
    assert payload["n_open"] == 1


# 2 --------------------------------------------------------------------- TP hit
def test_tp_hit_realizes_net_of_two_sided_cost():
    book = _book(cash=10000.0, cost_bps=10.0)  # 10 bp per side
    pos = pp.open_position(book, "BTC/USDT", "LONG", 10, 100.0, tp=110.0, sl=90.0)

    payload = pp.mark_book(book, price_fn=_fixed_prices({"BTC/USDT": 110.0}))

    assert payload["n_open"] == 0
    assert payload["n_closed"] == 1
    rec = payload["closed_now"][0]
    assert rec["reason"] == "TP"
    assert rec["exit_px"] == 110.0
    # gross 100, entry fee 1.0, exit fee 1.1 -> net 97.9
    assert rec["gross"] == 100.0
    assert abs(rec["net"] - 97.9) < 1e-9
    assert abs(payload["realized_pnl"] - 97.9) < 1e-9
    assert abs(book["cash"] - (10000.0 + 97.9)) < 1e-9


# 3 --------------------------------------------------------------------- SL hit
def test_sl_hit_realizes_negative_net_of_two_sided_cost():
    book = _book(cash=10000.0, cost_bps=10.0)
    pp.open_position(book, "BTC/USDT", "LONG", 10, 100.0, tp=110.0, sl=90.0)

    payload = pp.mark_book(book, price_fn=_fixed_prices({"BTC/USDT": 90.0}))

    rec = payload["closed_now"][0]
    assert rec["reason"] == "SL"
    assert rec["exit_px"] == 90.0
    # gross -100, entry fee 1.0, exit fee 0.9 -> net -101.9
    assert rec["gross"] == -100.0
    assert abs(rec["net"] - (-101.9)) < 1e-9
    assert abs(payload["realized_pnl"] - (-101.9)) < 1e-9


# 4 ------------------------------------------------ THE pessimistic straddle rule
def test_bar_straddling_tp_and_sl_must_resolve_to_sl():
    pos = {"symbol": "BTC/USDT", "direction": "LONG", "entry_px": 100.0,
           "tp": 110.0, "sl": 90.0, "entry_ts": "2026-11-22T00:00:00Z"}
    # one bar that touches BOTH the target (high 115) and the stop (low 85)
    bar = {"open": 100.0, "high": 115.0, "low": 85.0}

    hit = pp.resolve_tp_sl(pos, bar)

    assert hit is not None
    reason, exit_px = hit
    assert reason == "SL", f"straddle bar must resolve SL (pessimistic), got {reason}"
    assert exit_px == 90.0


def test_bar_straddling_short_resolves_sl():
    pos = {"symbol": "BTC/USDT", "direction": "SHORT", "entry_px": 100.0,
           "tp": 90.0, "sl": 110.0, "entry_ts": "2026-11-22T00:00:00Z"}
    bar = {"open": 100.0, "high": 115.0, "low": 85.0}

    reason, exit_px = pp.resolve_tp_sl(pos, bar)

    assert reason == "SL"
    assert exit_px == 110.0


# 5 ------------------------------------------------------------------ partial book
def test_partial_book_one_winner_one_loser():
    book = _book(cash=10000.0, cost_bps=0.0)
    pp.open_position(book, "AAA", "LONG", 10, 100.0)   # -> 110  (+100)
    pp.open_position(book, "BBB", "LONG", 10, 200.0)   # -> 190  (-100)

    payload = pp.mark_book(book, price_fn=_fixed_prices({"AAA": 110.0, "BBB": 190.0}))

    assert payload["positions_value"] == 1100.0 + 1900.0
    assert payload["equity"] == book["cash"] + 3000.0
    assert abs(payload["unrealized_pnl"] - 0.0) < 1e-9
    assert payload["unrealized_pnl"] == 0.0
    assert payload["equity"] == 10000.0


# 6 ------------------------------------------------------- missing price -> STALE
def test_missing_price_is_stale_and_excluded_not_zeroed():
    book = _book(cash=10000.0, cost_bps=0.0)
    pp.open_position(book, "AAA", "LONG", 10, 100.0)    # priced 120
    pp.open_position(book, "NOPRICE", "LONG", 5, 50.0)  # no quote

    payload = pp.mark_book(book, price_fn=_fixed_prices({"AAA": 120.0}))

    # only AAA contributes to positions value / equity
    assert payload["positions_value"] == 1200.0
    assert payload["equity"] == book["cash"] + 1200.0
    assert "NOPRICE" in payload["stale_symbols"]
    stale = [p for p in book["positions"] if p["symbol"] == "NOPRICE"][0]
    assert stale["status"] == "STALE"
    assert stale["last_px"] is None          # never substituted with entry / zero
    # NOPRICE must be EXCLUDED, not valued at zero or at entry (5*50 = 250).
    assert payload["equity"] != book["cash"]
    assert payload["equity"] != book["cash"] + 250.0


# 7 ----------------------------------------------- equity append + dated snapshot
def test_equity_append_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "BOOK_DIR", tmp_path)
    monkeypatch.setattr(pp, "EQUITY_FILE", tmp_path / "equity_curve.jsonl")
    monkeypatch.setattr(pp, "SNAP_DIR", tmp_path / "snapshots")

    book = _book(cash=10000.0, cost_bps=0.0)
    pp.open_position(book, "AAA", "LONG", 10, 100.0)
    fn = _fixed_prices({"AAA": 110.0})

    p1 = pp.mark_book(book, price_fn=fn)
    pp.append_equity(p1)
    snap = pp.write_snapshot(book, p1)
    p2 = pp.mark_book(book, price_fn=fn)
    pp.append_equity(p2)

    lines = [json.loads(l) for l in (tmp_path / "equity_curve.jsonl").read_text().splitlines() if l]
    assert len(lines) == 2                       # two points, append works
    for k in ("ts_utc", "cash", "positions_value", "equity", "realized_pnl",
              "unrealized_pnl", "n_open", "n_closed", "prices"):
        assert k in lines[0]
    assert snap.exists() and snap.name.endswith(".json")
    snap_data = json.loads(snap.read_text())
    assert snap_data["purpose"] == "plumbing_demo_not_validated_edge"
    assert "positions" in snap_data


# 8 ---------------------------------------------------- purpose + short accounting
def test_book_purpose_and_short_accounting():
    book = _book(cash=10000.0, cost_bps=0.0)
    assert book["purpose"] == "plumbing_demo_not_validated_edge"
    pp.open_position(book, "AAA", "SHORT", 10, 100.0)   # cash +1000
    assert book["cash"] == 11000.0
    payload = pp.mark_book(book, price_fn=_fixed_prices({"AAA": 90.0}))
    # short gains when price falls: mv = -10*90 = -900 -> equity 10100
    assert payload["positions_value"] == -900.0
    assert payload["equity"] == 10100.0
    assert payload["unrealized_pnl"] == 100.0


def test_init_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "BOOK_FILE", tmp_path / "book.json")
    monkeypatch.setattr(pp, "BOOK_DIR", tmp_path)
    monkeypatch.setattr(pp, "EQUITY_FILE", tmp_path / "equity_curve.jsonl")
    monkeypatch.setattr(pp, "SNAP_DIR", tmp_path / "snapshots")
    assert pp.main(["--init", "--cash", "5000"]) == 0
    try:
        pp.main(["--init", "--cash", "6000"])
    except SystemExit as e:
        assert "force" in str(e)
    else:
        raise AssertionError("--init should refuse to overwrite without --force")
    assert pp.main(["--init", "--cash", "6000", "--force"]) == 0
    assert json.loads((tmp_path / "book.json").read_text())["starting_cash"] == 6000.0

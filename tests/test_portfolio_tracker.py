"""Portfolio tracker: three backends, one book.

The tests pin the properties the tracker is chosen for, not just arithmetic:
the ledger must survive a torn tail write, the snapshot must agree with the
ledger to the cent, the round-trip log must *refuse* to answer equity, and a
book imported from a real state file must reproduce that file's own P&L.
"""
import json
import math

import pytest

import tools.portfolio_tracker as pt


def _events():
    return [
        {"type": "FUND", "book": "t", "amount": 1000.0, "ts": "2026-01-01T00:00:00Z"},
        {"type": "OPEN", "book": "t", "id": "a", "symbol": "BTCUSDT", "qty": 0.01,
         "price": 50000.0, "fee_bps": 10.0, "ts": "2026-01-01T00:00:00Z"},
        {"type": "OPEN", "book": "t", "id": "b", "symbol": "ETHUSDT", "qty": 0.1,
         "price": 2000.0, "fee_bps": 10.0, "ts": "2026-01-01T00:00:00Z"},
        {"type": "MARK", "book": "t", "symbol": "BTCUSDT", "price": 51000.0},
        {"type": "CLOSE", "book": "t", "id": "b", "price": 2040.0, "reason": "TARGET"},
    ]


def test_replay_marks_and_realises():
    state = pt.replay(_events())
    t = state["totals"]
    # b: 0.1 * (2040 - 2000) = $4 gross, minus 0.2 entry fee and 0.204 exit fee.
    # Views are rounded to cents, so the assertions are too.
    assert t["realized"] == pytest.approx(3.60, abs=0.01)
    # a: 0.01 * (51000 - 50000) = $10 unrealised, b is closed
    assert t["unrealized"] == pytest.approx(10.0, abs=1e-6)
    assert t["n_open"] == 1 and t["n_closed"] == 1
    # cash 1000 - 500.5 - 200.2 + 203.796; plus a marked at 510
    assert t["equity"] == pytest.approx(1013.10, abs=0.01)
    assert t["fees"] == pytest.approx(0.90, abs=0.01)


def test_ledger_survives_torn_tail_write(tmp_path):
    ledger = pt.EventLedger(tmp_path / "l.jsonl")
    for evt in _events():
        ledger.append(evt)
    before = ledger.state()["totals"]
    with (tmp_path / "l.jsonl").open("a") as fh:
        fh.write('{"type": "OPEN", "id": "half')
    after = ledger.state()
    assert after["totals"] == before
    assert after["ledger"]["corrupt_lines"] == 1


def test_ledger_append_unique_is_idempotent(tmp_path):
    ledger = pt.EventLedger(tmp_path / "l.jsonl")
    assert ledger.append_unique(_events()[0]) is True
    assert ledger.append_unique(_events()[0]) is False
    assert len(ledger.read()[0]) == 1


def test_snapshot_matches_ledger_to_the_cent(tmp_path):
    ledger = pt.EventLedger(tmp_path / "l.jsonl")
    snap = pt.SnapshotStore(tmp_path / "s.json")
    for evt in _events():
        ledger.append(evt)
        snap.apply(evt)
    snap.save()
    l = ledger.state()["totals"]
    s = snap.state()["totals"]
    for key in ("fund", "equity", "realized", "unrealized", "fees", "exposure"):
        assert l[key] == pytest.approx(s[key], abs=0.01), key


def test_roundtrip_backend_refuses_equity(tmp_path):
    book = pt.RoundTripBook(tmp_path / "r.jsonl")
    book.record([{"id": "b", "symbol": "ETHUSDT", "realized": 39.596}])
    assert book.stats()["realized"] == pytest.approx(39.596)
    with pytest.raises(NotImplementedError):
        book.equity()


def test_compare_reports_agreement_and_recovery(tmp_path):
    out = tmp_path / "cmp.json"
    result = pt.compare(_events(), out)
    assert result["agreement"]["ledger_equals_snapshot"] is True
    assert result["ledger"]["torn_write_recovered"] is True
    assert result["ledger"]["corrupt_lines_after_torn_write"] == 1
    assert result["roundtrip"]["n"] == 1
    assert result["roundtrip"]["can_answer_equity"] is False
    assert json.loads(out.read_text())["n_events"] == len(_events())


def test_realtime_import_reproduces_source_pnl(tmp_path):
    state = {
        "tag": "s", "book_usd": 10000.0, "opened_at": "2026-01-01T00:00:00Z",
        "positions": [],
        "closed": [{
            "id": "s-BNBUSDT-1", "symbol": "BNBUSDT", "side": "LONG", "qty": 6.1,
            "entry_price": 546.0, "exit_price": 544.39, "tp_price": 549.0,
            "sl_price": 543.0, "opened_at": "2026-01-01T00:00:00Z",
            "closed_at": "2026-01-01T00:10:00Z", "exit_reason": "SPRINT_CLOSE",
            "gross_pct": -0.2949, "net_pct": -0.4949, "pnl_usd": -16.48,
        }],
    }
    path = tmp_path / "s.json"
    path.write_text(json.dumps(state))
    events = pt.events_from_realtime(path)
    state = pt.replay(events)
    assert state["books"]["s"]["n_closed"] == 1
    # 10 bps per side on entry and exit, prices already include slippage
    assert state["books"]["s"]["realized"] == pytest.approx(-16.48, abs=0.05)


def test_forward_book_import_splits_round_trip_cost(tmp_path):
    book = {"created_at": "2026-01-01T00:00:00Z", "entries": [{
        "id": "abc", "symbol": "LINK-USD", "asset_class": "CRYPTO",
        "direction": "LONG", "entry_date": "2026-01-01", "entry_price": 10.0,
        "stop_loss": 9.5, "take_profit": 11.0, "cost_bps": 20,
        "status": "RESOLVED",
        "resolution": {"exit_price": 11.0, "exit_date": "2026-01-05", "reason": "TP"},
    }]}
    path = tmp_path / "fb.json"
    path.write_text(json.dumps(book))
    events = pt.events_from_forward_book(path, notional=1000.0)
    opens = [e for e in events if e["type"] == "OPEN"]
    assert opens[0]["fee_bps"] == 10.0
    assert opens[0]["tp"] == 11.0 and opens[0]["sl"] == 9.5
    realised = pt.replay(events)["books"]["forward_book"]["realized"]
    # 100 shares * $1.00 = $100 gross, minus 20 bps of $1000 notional on each side
    assert realised == pytest.approx(100.0 - 1.0 - 1.1, abs=1e-6)


def test_mark_events_update_equity_without_touching_realised(tmp_path, monkeypatch):
    ledger = pt.EventLedger(tmp_path / "l.jsonl")
    for evt in _events():
        ledger.append(evt)
    monkeypatch.setattr(pt, "last_price", lambda symbol, cls="CRYPTO": 52000.0)
    state = ledger.state()
    marks = pt._mark_events(state)
    for evt in marks:
        ledger.append(evt)
    after = ledger.state()["totals"]
    assert after["realized"] == pytest.approx(state["totals"]["realized"])
    assert after["unrealized"] == pytest.approx(20.0)  # 1000 * 4%

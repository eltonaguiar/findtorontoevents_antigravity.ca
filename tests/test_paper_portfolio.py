"""Deterministic unit tests for tools/paper_portfolio.py - synthetic prices, no network."""
from __future__ import annotations

import hashlib
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


# ============================================================ gate-checked loader
# These lock the ONLY honest behaviour available today: the loader refuses when
# nothing passes the real forward gate, and it is still capable of loading when
# something genuinely does.

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pod(pod_id, *, status="pre_registered", hid="H-TEST", **extra):
    p = {"id": pod_id, "status": status, "registered_at": "2026-11-19",
         "hypothesis_id": hid, "strategies": [f"strat-{pod_id.lower()}"],
         "asset_classes": ["EQUITY"], "directions": ["LONG"]}
    p.update(extra)
    return p


def _write_manifest(tmp_path: Path, pods) -> Path:
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps({"schema": "audit3.confirmatory.v1", "pods": pods}))
    return f


def _row(i: int, hid="H-TEST") -> dict:
    """A forward row the real promotion() can judge.

    Alternates +8% / -2% so the series has BOTH wins and losses: an all-winner
    series has an infinite PF, whose CI is not estimable, and the gate rightly
    refuses it. Mean +3%, sd 5% -> IR 0.6 >= 0.5, PF 4.0.
    """
    return {"id": f"r{i}", "hypothesis_id": hid, "opened_at": "2026-11-20T00:00:00Z",
            "closed_at": "2026-11-20T04:00:00Z", "symbol": f"SYM{i}", "asset_class": "EQUITY",
            "side": "LONG", "entry_px": 100.0, "exit_px": 108.0 if i % 2 == 0 else 98.0,
            "qty": 1.0, "fees": 0.0,
            "funding": 0.0, "slippage_bps": 0.0, "resolver_version": "v1",
            "intrabar_first_touch": True, "benchmark_leg_ret": 0.001, "regime_ok": True,
            "created_at": "2026-11-20T04:00:01Z"}


def _write_ledger(tmp_path: Path, rows) -> Path:
    f = tmp_path / "ledger.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return f


def _write_registry(tmp_path: Path, hyps) -> Path:
    f = tmp_path / "registry.json"
    f.write_text(json.dumps({"hypotheses": hyps}))
    return f


def test_gate_real_state_refuses_and_leaves_book_untouched(tmp_path, monkeypatch):
    """The real repo gate state: nothing passes, so the book hash must not move."""
    monkeypatch.setattr(pp, "BOOK_FILE", tmp_path / "book.json")
    monkeypatch.setattr(pp, "BOOK_DIR", tmp_path)
    monkeypatch.setattr(pp, "EQUITY_FILE", tmp_path / "equity_curve.jsonl")
    monkeypatch.setattr(pp, "SNAP_DIR", tmp_path / "snapshots")
    assert pp.main(["--init", "--cash", "10000"]) == 0
    book = pp.load_book()
    pp.open_position(book, "BTC/USDT", "LONG", 0.05, 60000.0, strategy="demo_plumbing")
    pp.save_book(book)
    before = _sha(tmp_path / "book.json")

    assert pp.main(["--load-from-gate"]) == 0

    assert _sha(tmp_path / "book.json") == before, "refusal must leave book.json byte-identical"
    assert len(pp.load_book()["positions"]) == 1     # demo position kept, nothing added


def test_gate_real_state_outcome_is_refusal():
    """On the checked-in repo state every pod fails the real gate."""
    gate = pp.evaluate_gate()
    assert gate["pods"], "real manifest must expose pods"
    assert all(not p["loadable"] for p in gate["pods"]), \
        "some pod passes the real gate - the programme's conclusion changed, re-check"
    book = pp.new_book(10000.0, 10.0)
    outcome, out_book = pp.load_from_gate(book, gate)
    assert outcome["loaded"] == 0
    assert outcome["reason"] == "no_pod_passed_forward_gate"
    assert out_book is book and book["positions"] == []
    assert {p["pod"] for p in outcome["pod_results"]} == {p["pod"] for p in gate["pods"]}
    assert all("n" in p and "eligible" in p for p in outcome["pod_results"])


def test_gate_synthetic_eligible_pod_produces_position(tmp_path, monkeypatch):
    """Proof of capability: a pod that genuinely passes DOES load."""
    manifest = _write_manifest(tmp_path, [_pod("POD-EQUITY-BREAKOUT", hid="H-TEST")])
    ledger = _write_ledger(tmp_path, [_row(i) for i in range(120)])
    registry = _write_registry(tmp_path, [{"id": "H-TEST", "status": "FORWARD"}])
    monkeypatch.setattr(pp, "fetch_price",
                        lambda s: {"px": 500.0, "ts": "2026-11-22T00:00:00Z", "source": "stub"})

    gate = pp.evaluate_gate(manifest, ledger, registry)
    assert gate["pods"][0]["eligible"] is True     # real promotion() judged it
    assert gate["pods"][0]["loadable"] is True

    book = pp.new_book(10000.0, 10.0)
    outcome, book = pp.load_from_gate(book, gate)

    assert outcome["loaded"] == 1
    pos = book["positions"][0]
    assert pos["gated"] is True
    assert pos["strategy"] == "POD-EQUITY-BREAKOUT"
    assert pos["source"].startswith("forward-gate:")
    assert pos["qty"] > 0 and pos["entry_px"] == 500.0
    assert pos["gate_n"] == 120


def test_gate_promotable_false_is_never_loadable(tmp_path, monkeypatch):
    """Same passing numbers, but the registry vetoes it: never loadable."""
    manifest = _write_manifest(tmp_path, [_pod("POD-EQUITY-BREAKOUT", hid="H-TEST")])
    ledger = _write_ledger(tmp_path, [_row(i) for i in range(120)])
    registry = _write_registry(
        tmp_path, [{"id": "H-TEST", "status": "FORWARD", "promotable": False,
                    "promotable_reason": "not a pod"}])
    monkeypatch.setattr(pp, "fetch_price",
                        lambda s: {"px": 500.0, "ts": "2026-11-22T00:00:00Z", "source": "stub"})

    gate = pp.evaluate_gate(manifest, ledger, registry)
    pod = gate["pods"][0]
    assert pod["eligible"] is True            # the gate alone would pass it
    assert pod["promotable"] is False
    assert pod["loadable"] is False           # the registry flag vetoes it
    assert any("promotable: false" in r for r in pod["reasons"])

    book = pp.new_book(10000.0, 10.0)
    outcome, book = pp.load_from_gate(book, gate)
    assert outcome["loaded"] == 0
    assert book["positions"] == []


def test_gate_unpriced_pod_is_skipped_not_guessed(tmp_path, monkeypatch):
    """A passing pod whose instrument cannot be quoted adds nothing (no guess)."""
    manifest = _write_manifest(tmp_path, [_pod("POD-EQUITY-BREAKOUT", hid="H-TEST")])
    ledger = _write_ledger(tmp_path, [_row(i) for i in range(120)])
    registry = _write_registry(tmp_path, [{"id": "H-TEST", "status": "FORWARD"}])
    monkeypatch.setattr(pp, "fetch_price", lambda s: None)

    book = pp.new_book(10000.0, 10.0)
    outcome, book = pp.load_from_gate(book, pp.evaluate_gate(manifest, ledger, registry))

    assert outcome["loaded"] == 0
    assert book["positions"] == []
    assert outcome["skipped"][0]["reason"] == "no real quote"


def test_status_labels_demo_positions_as_ungated(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pp, "BOOK_FILE", tmp_path / "book.json")
    monkeypatch.setattr(pp, "BOOK_DIR", tmp_path)
    monkeypatch.setattr(pp, "EQUITY_FILE", tmp_path / "equity_curve.jsonl")
    monkeypatch.setattr(pp, "SNAP_DIR", tmp_path / "snapshots")
    assert pp.main(["--init", "--cash", "10000"]) == 0
    book = pp.load_book()
    pp.open_position(book, "BTC/USDT", "LONG", 0.05, 60000.0, strategy="demo_plumbing")
    pp.save_book(book)

    assert pp.main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "DEMO BOOK - NOT GATE-BACKED" in out
    assert "DEMO/UNGATED" in out
    assert "GATED" not in out.replace("DEMO/UNGATED", "").replace("NOT GATE-BACKED", "")

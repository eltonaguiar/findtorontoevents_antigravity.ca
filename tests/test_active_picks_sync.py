"""P0 (data-integrity): unit tests for active_picks_sync.compute_verdict().

compute_verdict is the per-pick TP / SL / time-exit decision that
active_picks_sync uses to close ACTIVE picks into closed_picks.json. It had
NO tests — yet it is the function that decides WON vs LOST and the realized
pnl_pct that every downstream aggregate (pf_registry, asset_class_health,
money_ready_verdict) reads. These tests pin its contract before the writer
is flipped from DRY-RUN to live.
"""
from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine.active_picks_sync import (
    PNL_WIN_THRESHOLD_BY_CLASS,
    apply_transition,
    compute_verdict,
    fetch_live_prices,
)

CRYPTO_THR = PNL_WIN_THRESHOLD_BY_CLASS["CRYPTO"]


def _pick(**kw):
    base = {
        "id": 1, "symbol": "BTCUSDT", "asset_class": "CRYPTO",
        "strategy": "t", "direction": "LONG",
        "entry_price": 100.0, "take_profit": 110.0, "stop_loss": 95.0,
        "signal_timestamp": datetime.now(timezone.utc),
    }
    base.update(kw)
    return base


# --- still-open / guard paths -------------------------------------------------

def test_open_pick_returns_none():
    # price between SL and TP, fresh timestamp -> not closed
    assert compute_verdict(_pick(), live_price=102.0, max_hold_hours=48,
                           win_threshold=CRYPTO_THR) is None


def test_none_price_returns_none():
    assert compute_verdict(_pick(), live_price=None, max_hold_hours=48,
                           win_threshold=CRYPTO_THR) is None


def test_nonpositive_entry_returns_none():
    assert compute_verdict(_pick(entry_price=0), live_price=110.0,
                           max_hold_hours=48, win_threshold=CRYPTO_THR) is None


# --- TP / SL hits -------------------------------------------------------------

def test_long_tp_hit_is_won():
    v = compute_verdict(_pick(), live_price=111.0, max_hold_hours=48,
                        win_threshold=CRYPTO_THR)
    assert v["new_status"] == "WON" and v["exit_reason"] == "TP_HIT"
    assert v["pnl_pct"] == 11.0  # (111-100)/100, reported as percent


def test_long_sl_hit_is_lost():
    v = compute_verdict(_pick(), live_price=94.0, max_hold_hours=48,
                        win_threshold=CRYPTO_THR)
    assert v["new_status"] == "LOST" and v["exit_reason"] == "SL_HIT"
    assert v["pnl_pct"] == -6.0


def test_short_tp_hit_is_won():
    v = compute_verdict(_pick(direction="SHORT", take_profit=90.0,
                               stop_loss=105.0), live_price=89.0,
                        max_hold_hours=48, win_threshold=CRYPTO_THR)
    assert v["new_status"] == "WON" and v["exit_reason"] == "TP_HIT"
    assert v["pnl_pct"] == 11.0  # (100-89)/100 for SHORT


def test_short_sl_hit_is_lost():
    v = compute_verdict(_pick(direction="SHORT", take_profit=90.0,
                               stop_loss=105.0), live_price=106.0,
                        max_hold_hours=48, win_threshold=CRYPTO_THR)
    assert v["new_status"] == "LOST" and v["exit_reason"] == "SL_HIT"


# --- WON-vs-PnL contradiction handling (the P0 #2 concern, in-flight) ---------

def test_tp_hit_with_negative_pnl_is_contradiction_lost():
    # Malformed pick: TP set BELOW entry on a LONG. live >= TP triggers tp_hit
    # but the realized pnl is negative -> trust the pnl sign, status LOST.
    v = compute_verdict(_pick(take_profit=90.0), live_price=91.0,
                        max_hold_hours=48, win_threshold=CRYPTO_THR)
    assert v["new_status"] == "LOST"
    assert v["exit_reason"] == "TP_HIT_CONTRADICTION"
    assert v["pnl_pct"] < 0


def test_sl_hit_with_positive_pnl_is_contradiction_won():
    # Malformed pick: SL set ABOVE entry on a LONG. live (104) <= SL (105)
    # triggers sl_hit, but live > entry (100) so realized pnl is positive ->
    # trust the pnl sign, status WON.
    v = compute_verdict(_pick(stop_loss=105.0), live_price=104.0,
                        max_hold_hours=48, win_threshold=CRYPTO_THR)
    assert v["new_status"] == "WON"
    assert v["exit_reason"] == "SL_HIT_CONTRADICTION"
    assert v["pnl_pct"] > 0


# --- time-exit ----------------------------------------------------------------

def _stale(**kw):
    return _pick(signal_timestamp=datetime.now(timezone.utc) - timedelta(hours=200),
                 **kw)


def test_time_exit_win():
    # stale pick, no TP/SL hit, price up -> WON via TIME_EXIT
    v = compute_verdict(_stale(take_profit=999.0, stop_loss=1.0),
                        live_price=103.0, max_hold_hours=48,
                        win_threshold=CRYPTO_THR)
    assert v["new_status"] == "WON" and v["exit_reason"] == "TIME_EXIT"


def test_time_exit_loss():
    v = compute_verdict(_stale(take_profit=999.0, stop_loss=1.0),
                        live_price=97.0, max_hold_hours=48,
                        win_threshold=CRYPTO_THR)
    assert v["new_status"] == "LOST" and v["exit_reason"] == "TIME_EXIT"


def test_time_exit_flat_is_expired():
    # price within +/- win_threshold of entry -> EXPIRED, not WON/LOST
    v = compute_verdict(_stale(take_profit=999.0, stop_loss=1.0),
                        live_price=100.0, max_hold_hours=48,
                        win_threshold=CRYPTO_THR)
    assert v["new_status"] == "EXPIRED" and v["exit_reason"] == "TIME_EXIT"


def test_buy_sell_aliases_normalized():
    # direction "BUY"/"SELL" must normalize to LONG/SHORT
    v = compute_verdict(_pick(direction="BUY"), live_price=111.0,
                        max_hold_hours=48, win_threshold=CRYPTO_THR)
    assert v["direction"] == "LONG"


# --- Bug-1: apply_transition rowcount gating (no DB/JSON divergence) ----------

class _FakeCursor:
    """Synthetic cursor mimicking pymysql's WHERE-matched rowcount behaviour.

    `matched_ids` is the set of pick ids whose row still satisfies the UPDATE
    WHERE clause (status IN OPEN/ACTIVE or NULL). For any other id the UPDATE
    matches 0 rows — exactly the Bug-1 scenario for an already-terminal row.
    """

    def __init__(self, matched_ids):
        self.matched_ids = set(matched_ids)
        self.rowcount = 0
        self.executed = []

    def execute(self, sql, params):
        self.executed.append((sql, params))
        # last param is the pick id (WHERE id=%s)
        pid = params[-1]
        self.rowcount = 1 if pid in self.matched_ids else 0


def test_apply_transition_returns_rowcount_1_when_row_matches():
    cur = _FakeCursor(matched_ids={42})
    res = apply_transition(cur, {"id": 42, "new_status": "WON",
                                 "exit_reason": "TP_HIT", "exit_price": 110.0,
                                 "pnl_pct": 10.0})
    assert res["ok"] is True
    assert res["rowcount"] == 1


def test_apply_transition_returns_rowcount_0_when_row_already_terminal():
    # id 99 is NOT in matched_ids -> already WON/LOST/EXPIRED -> UPDATE no-match
    cur = _FakeCursor(matched_ids={42})
    res = apply_transition(cur, {"id": 99, "new_status": "WON",
                                 "exit_reason": "TP_HIT", "exit_price": 110.0,
                                 "pnl_pct": 10.0})
    assert res["ok"] is True
    assert res["rowcount"] == 0  # the gate the JSON-append must respect


def test_apply_transition_missing_id_is_rejected():
    cur = _FakeCursor(matched_ids=set())
    res = apply_transition(cur, {"new_status": "WON"})
    assert res["ok"] is False and res["error"] == "missing_id"


def test_bug1_only_db_confirmed_rows_are_json_appended():
    """Replicates the main()-loop gate: a transition whose UPDATE matched 0
    rows must NOT land in the closed_picks.json append set."""
    cur = _FakeCursor(matched_ids={1, 3})  # id 2 is already terminal
    transitions = [
        {"id": 1, "new_status": "WON", "exit_reason": "TP_HIT",
         "exit_price": 110.0, "pnl_pct": 10.0},
        {"id": 2, "new_status": "LOST", "exit_reason": "SL_HIT",
         "exit_price": 95.0, "pnl_pct": -5.0},
        {"id": 3, "new_status": "EXPIRED", "exit_reason": "TIME_EXIT",
         "exit_price": 100.0, "pnl_pct": 0.0},
    ]
    applied_ids = set()
    for t in transitions:
        r = apply_transition(cur, t)
        if r.get("ok") and r.get("rowcount", 0) >= 1:
            applied_ids.add(str(t["id"]))
    # only DB-confirmed ids (1, 3) are eligible for the JSON append
    assert applied_ids == {"1", "3"}
    json_eligible = [t for t in transitions if str(t["id"]) in applied_ids]
    assert {t["id"] for t in json_eligible} == {1, 3}


# --- Bug-2: fetch_live_prices fail-loud on zero non-crypto prices -------------

def _stub_empty_yfinance(monkeypatch):
    """Make `import yfinance` succeed but every batch fetch yield nothing,
    reproducing a symbol-format mismatch / yfinance outage."""
    import sys
    import types

    fake = types.ModuleType("yfinance")

    class _Tickers:
        def __init__(self, *a, **kw):
            pass

        def history(self, *a, **kw):
            class _Empty:
                columns = []
            return _Empty()

    fake.Tickers = _Tickers
    monkeypatch.setitem(sys.modules, "yfinance", fake)


def test_bug2_fail_loud_raises_in_apply_mode(monkeypatch):
    _stub_empty_yfinance(monkeypatch)
    monkeypatch.setenv("ACTIVE_PICKS_SYNC_APPLY", "1")
    with pytest.raises(RuntimeError, match="refusing to proceed"):
        fetch_live_prices(["EURUSD", "GBPUSD"], "FOREX")


def test_bug2_dry_run_emits_warning_not_raise(monkeypatch, capsys):
    _stub_empty_yfinance(monkeypatch)
    monkeypatch.delenv("ACTIVE_PICKS_SYNC_APPLY", raising=False)
    # DRY-RUN: must NOT raise, must return {} and emit a ::warning:: annotation
    out = fetch_live_prices(["EURUSD", "GBPUSD"], "FOREX")
    assert out == {}
    captured = capsys.readouterr()
    assert "::warning" in captured.out


def test_bug2_no_fail_loud_for_crypto(monkeypatch):
    # CRYPTO uses api_failover, not yfinance — an empty result is tolerated
    # even in APPLY mode (no symbol-suffix class of bug there).
    monkeypatch.setenv("ACTIVE_PICKS_SYNC_APPLY", "1")

    import alpha_engine.active_picks_sync as aps
    monkeypatch.setattr("alpha_engine.api_failover.fetch_price",
                        lambda sym: None, raising=False)
    # should not raise even though 0 prices come back
    out = aps.fetch_live_prices(["FAKECOINUSDT"], "CRYPTO")
    assert out == {}

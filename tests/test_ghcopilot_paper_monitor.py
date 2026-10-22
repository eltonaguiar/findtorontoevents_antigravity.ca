from datetime import datetime, timedelta, timezone

import pytest

from tools.ghcopilot_paper_monitor import (
    admit_signals, advance_trade, bh_adjust, resolve_leg, screen_candidates, summarize, utc,
)


NOW = datetime(2026, 10, 22, 22, tzinfo=timezone.utc)


def bar(hours, opening=100, high=101, low=99, close=100):
    return {"time": (NOW + timedelta(hours=hours)).isoformat(),
            "open": opening, "high": high, "low": low, "close": close}


def leg():
    return {"entry_at": NOW.isoformat(), "entry": 100, "tp": 104,
            "sl": 98, "direction": "LONG", "expires_at": (NOW + timedelta(hours=48)).isoformat()}


def test_bh_corrects_entire_family():
    assert bh_adjust([.01, .04, .03]) == pytest.approx([.03, .04, .04])


def test_deploy_includes_scorecard_dependency_without_changing_ledger(tmp_path, monkeypatch):
    from tools import ghcopilot_paper_monitor as monitor

    root = tmp_path / "audit_dashboard"
    root.mkdir()
    (root / "audit_scorecard.js").write_bytes(b"scorecard")
    (root / "ghcopilot_paper.html").write_bytes(b"page")
    ledger = root / "ledger.json"
    ledger.write_bytes(b'{"immutable":"fixture"}')
    uploaded = []

    class FakeFTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, *args):
            pass

        def prot_p(self):
            pass

        def storbinary(self, command, stream):
            uploaded.append((command, stream.read()))

    monkeypatch.setattr(monitor, "ROOT", tmp_path)
    monkeypatch.setattr(monitor, "FTP_TLS", FakeFTP)
    monkeypatch.setenv("FTP_USER", "fixture")
    monkeypatch.setenv("FTP_PASS", "fixture")
    monitor.deploy(ledger)
    assert uploaded == [
        ("STOR /findtorontoevents.ca/audit/audit_scorecard.js", b"scorecard"),
        ("STOR /findtorontoevents.ca/audit/ghcopilot_paper.html", b"page"),
        ("STOR /findtorontoevents.ca/audit/data/ghcopilot_paper.json", b'{"immutable":"fixture"}'),
    ]
    assert ledger.read_bytes() == b'{"immutable":"fixture"}'


def test_stop_first_on_ambiguous_bar():
    result = resolve_leg(leg(), [bar(0, high=105, low=97)], NOW + timedelta(hours=2), "CRYPTO")
    assert result["reason"] == "SL_HIT"
    assert result["exit"] == 98


def test_adverse_gap_fills_at_open_not_stop():
    result = resolve_leg(leg(), [bar(0, opening=95, high=100, low=94)], NOW + timedelta(hours=2), "EQUITY")
    assert result["exit"] == 95
    assert result["reason"] == "GAP_SL"


def test_pre_entry_and_unclosed_bars_are_not_outcomes():
    assert resolve_leg(leg(), [bar(-1, high=110), bar(0, high=110)], NOW + timedelta(minutes=30), "CRYPTO") is None


def test_incomplete_horizon_not_expired():
    assert resolve_leg(leg(), [bar(0)], NOW + timedelta(hours=3), "CRYPTO") is None


def test_time_exit_uses_horizon_not_later_price():
    bars = [bar(h, close=101) for h in range(48)] + [bar(48, close=120, high=121)]
    result = resolve_leg(leg(), bars, NOW + timedelta(hours=50), "CRYPTO")
    assert result["reason"] == "TIME_EXIT"
    assert result["exit"] == 101


def test_crypto_missing_candle_is_explicit():
    with pytest.raises(ValueError, match="missing"):
        resolve_leg(leg(), [bar(0), bar(2, high=105)], NOW + timedelta(hours=4), "CRYPTO")


def test_short_stop_gap():
    trade = {**leg(), "direction": "SHORT", "tp": 96, "sl": 102}
    result = resolve_leg(trade, [bar(0, opening=105, high=106, low=100)], NOW + timedelta(hours=2), "EQUITY")
    assert result["exit"] == 105


def test_unknown_pnl_never_defaults_to_flat():
    with pytest.raises(ValueError):
        summarize([{"net_pct": None, "entry_at": NOW.isoformat()}])


def test_screen_deduplicates_identity_and_does_not_promote_tiny_sample():
    row = {"id": 1, "symbol": "A", "source_system": "alpha_engine",
           "strategy": "s", "asset_class": "EQUITY", "direction": "LONG",
           "opened_at": NOW, "entry_price": 100, "take_profit": 104,
           "stop_loss": 98, "intrabar_pnl_pct": 2}
    screen = screen_candidates([row, row], NOW)
    assert screen["duplicate_rows"] == 1
    assert screen["groups"][0]["n"] == 1
    assert not screen["groups"][0]["historical_gate_pass"]
    assert screen["candidates"]["EQUITY"] is None


def state():
    return {"locked_at": (NOW - timedelta(hours=1)).isoformat(),
            "candidates": {"EQUITY": {"source": "alphaengine", "strategy": "s"}},
            "trades": [], "seen": [], "rejections": {}}


def signal(**changes):
    return {"id": "private-id", "symbol": "A", "source_system": "AlphaEngine",
            "strategy": "s", "asset_class": "EQUITY", "direction": "LONG",
            "signal_timestamp": NOW - timedelta(minutes=30),
            "recorded_at": NOW - timedelta(minutes=20),
            "entry_price": 100, "take_profit": 104, "stop_loss": 98,
            "status": "OPEN", "was_stale": 0, "was_banned": 0,
            "was_demoted": 0, **changes}


def test_admission_is_prospective_and_restart_idempotent():
    s = state()
    admit_signals(s, [signal()], NOW)
    admit_signals(s, [signal()], NOW + timedelta(minutes=10))
    assert len(s["trades"]) == 1
    assert s["trades"][0]["observed_at"] == NOW.isoformat()
    assert "private-id" not in str(s)
    assert s["trades"][0]["status"] == "PENDING_ENTRY"


@pytest.mark.parametrize("changes,reason", [
    ({"signal_timestamp": NOW - timedelta(hours=3)}, "stale_signal"),
    ({"recorded_at": NOW - timedelta(days=10)}, "before_lock"),
    ({"stop_loss": 105}, "invalid_geometry"),
    ({"status": "WON"}, "not_open"),
    ({"was_banned": 1}, "policy_flag"),
])
def test_invalid_signals_are_counted_not_traded(changes, reason):
    s = state()
    if reason == "stale_signal":
        s["locked_at"] = (NOW - timedelta(days=1)).isoformat()
    admit_signals(s, [signal(**changes)], NOW)
    assert not s["trades"]
    assert s["rejections"][reason] == 1


def test_one_position_per_class():
    s = state()
    admit_signals(s, [signal(), signal(id="second", symbol="B")], NOW)
    assert len(s["trades"]) == 1
    assert s["rejections"]["exposure_cap"] == 1


def test_utc_accepts_canonical_naive_db_dates():
    assert utc(datetime(2026, 1, 1)).tzinfo is timezone.utc


def test_known_historical_reemission_strategy_is_quarantined():
    row = {"id": 1, "symbol": "AAPL", "source_system": "alpha_engine",
           "strategy": "vt_equity_two_day_rsi_reversal", "asset_class": "EQUITY",
           "direction": "LONG", "opened_at": NOW, "entry_price": 100,
           "take_profit": 104, "stop_loss": 98, "intrabar_pnl_pct": 2}
    result = screen_candidates([row], NOW)
    assert result["excluded_rows"]["known_historical_reemission"] == 1
    assert not result["groups"]


def test_ambiguous_historical_candles_not_used_as_independent_proof():
    row = {"id": 1, "symbol": "AAPL", "source_system": "alpha_engine",
           "strategy": "s", "asset_class": "EQUITY", "direction": "LONG",
           "opened_at": NOW, "entry_price": 100, "take_profit": 104,
           "stop_loss": 98, "intrabar_pnl_pct": 2, "intrabar_ambiguous": 1}
    assert screen_candidates([row], NOW)["excluded_rows"]["ambiguous_history"] == 1


def test_missing_session_is_not_silently_treated_as_market_closure():
    with pytest.raises(ValueError, match="unverified session closure"):
        resolve_leg(leg(), [bar(0), bar(25, high=105)],
                    NOW + timedelta(hours=27), "EQUITY")


def test_first_fill_is_next_hour_not_containing_observation_bar():
    s = state()
    admit_signals(s, [signal()], NOW + timedelta(minutes=20))
    trade = s["trades"][0]
    advance_trade(trade, [bar(0), bar(1, opening=101, low=100, high=102)],
                  NOW + timedelta(hours=3))
    assert trade["entry"] == 101
    assert utc(trade["entry_at"]) == NOW + timedelta(hours=1)
    assert trade["status"] == "OPEN"


def test_random_control_uses_independent_stop_target_path():
    trade = {"observed_at": NOW.isoformat(), "status": "PENDING_ENTRY",
             "asset_class": "CRYPTO", "direction": "LONG", "control_direction": "SHORT",
             "tp_distance": .04, "sl_distance": .02, "notional_usd": 1000,
             "cost_pp": .3}
    advance_trade(trade, [bar(0, high=105, low=99)], NOW + timedelta(hours=2))
    assert trade["strategy_result"]["reason"] == "TP_HIT"
    assert trade["control_result"]["reason"] == "SL_HIT"
    assert trade["strategy_result"]["net_pct"] == pytest.approx(3.7)
    assert trade["control_result"]["net_pct"] == pytest.approx(-2.3)
    assert trade["status"] == "CLOSED"

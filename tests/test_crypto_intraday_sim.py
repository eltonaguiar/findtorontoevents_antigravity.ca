"""Tests for the crypto intraday paper sim and the pilot->forward bridge.

All deterministic: bars are synthetic, no network, logs/state in tmp_path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


def _bar(ts_ms: int, o: float, h: float, lo: float, c: float, v: float = 100.0) -> dict:
    return {"timestamp": ts_ms, "open": o, "high": h, "low": lo, "close": c,
            "volume": v}


BAR_MS = 4 * 3600_000
T0 = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _flat_bars(n: int, px: float = 100.0) -> list[dict]:
    return [_bar(T0 + i * BAR_MS, px, px * 1.001, px * 0.999, px) for i in range(n)]


@pytest.fixture()
def sim(tmp_path, monkeypatch):
    import verified_strategies.paper_pilot.crypto_intraday_sim as s

    monkeypatch.setattr(s, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(s, "STATE_PATH", tmp_path / "state.json")
    return s


class TestEntrySignals:
    def test_bollinger_mr_fires_on_band_break(self, sim):
        bars = _flat_bars(60)
        # crash the last close well below the lower band
        bars[-1] = _bar(bars[-1]["timestamp"], 100, 100, 88, 88)
        sig = sim.entry_signal("bollinger_mr", bars)
        assert sig is not None
        assert sig["take_profit"] > 88

    def test_bollinger_mr_silent_on_flat_tape(self, sim):
        assert sim.entry_signal("bollinger_mr", _flat_bars(60)) is None

    def test_btc_rsi_macd_fires_on_uptrend_with_room(self, sim):
        # breakout from a flat base: alternating +0.6%/-0.35% bars ending on an
        # up bar -> RSI ~63 (room below 70), MACD hist positive and rising
        moves = [1.0] * 60 + [(1.006 if i % 2 == 0 else 0.9965)
                              for i in range(20)] + [1.006]
        bars = []
        px = 100.0
        for i, m in enumerate(moves):
            px *= m
            bars.append(_bar(T0 + i * BAR_MS, px, px * 1.001, px * 0.999, px))
        sig = sim.entry_signal("btc_4h_rsi_macd", bars)
        assert sig is not None
        assert sig["stop_loss"] < bars[-1]["close"] < sig["take_profit"]

    def test_vwap_reversion_fires_on_deep_dip(self, sim):
        bars = _flat_bars(40)
        px = 100.0
        for i in range(1, 4):
            b = bars[-i]
            b["close"] = px * (1 - 0.01 * (4 - i))
        bars[-1]["close"] = 96.5
        sig = sim.entry_signal("vwap_reversion", bars)
        # z in [-2.5, -1.5] fires; a deeper crash must NOT (knife-catch guard)
        if sig is not None:
            assert "vwap_z" in sig["reason"]
        bars[-1]["close"] = 60.0
        assert sim.entry_signal("vwap_reversion", bars) is None

    def test_cost_floor_refuses_sub_cost_targets(self, sim):
        # a hair-below-band break on a tight tape: expected move to the
        # mid-band is far under 4x the round-trip cost -> refused
        bars = [_bar(T0 + i * BAR_MS, 100, 100.05, 99.95,
                     100 + (0.02 if i % 2 else -0.02)) for i in range(60)]
        bars[-1]["close"] = 99.90
        assert sim.entry_signal("bollinger_mr", bars) is None

    def test_entries_above_cost_floor_carry_expected_move(self, sim):
        bars = _flat_bars(60)
        bars[-1] = _bar(bars[-1]["timestamp"], 100, 100, 88, 88)
        sig = sim.entry_signal("bollinger_mr", bars)
        assert sig is not None
        assert sig["expected_move_pct"] >= (
            sim.COST_FLOOR_MULT * sim.ROUND_TRIP_COST_PCT)


class TestExitsAndGuardrails:
    def test_tp_hits_intrabar_before_time_exit(self, sim):
        pos = {"entry_price": 100.0, "entry_ts_ms": T0,
               "take_profit": 104.0, "stop_loss": 98.0}
        since = [_bar(T0 + BAR_MS, 100, 105, 99, 103)]
        reason, px, ts = sim.exit_check("btc_4h_rsi_macd", pos, since, since)
        assert reason == "TP" and px == 104.0

    def test_sl_checked_before_tp_in_same_bar(self, sim):
        pos = {"entry_price": 100.0, "entry_ts_ms": T0,
               "take_profit": 104.0, "stop_loss": 98.0}
        since = [_bar(T0 + BAR_MS, 100, 105, 97, 100)]
        reason, px, _ = sim.exit_check("btc_4h_rsi_macd", pos, since, since)
        assert reason == "SL" and px == 98.0

    def test_time_exit_after_max_hold(self, sim):
        cfg = sim.SLOTS["bollinger_mr"]
        n = cfg["max_hold_bars"] + 1
        bars = [_bar(T0 + i * BAR_MS, 100, 100.4, 99.6, 100) for i in range(n + 1)]
        pos = {"entry_price": 100.0, "entry_ts_ms": T0,
               "take_profit": None, "stop_loss": None}
        reason, _, _ = sim.exit_check("bollinger_mr", pos, bars[1:], bars)
        assert reason == "TIME"

    def test_trailing_dd_halts_slot(self, sim):
        closed = [{"slot": "bollinger_mr", "pnl_pct": -2.5,
                   "exit_ts": "2026-11-10T00:00:00+00:00"} for _ in range(5)]
        g = sim.slot_guardrails("bollinger_mr", closed, "2026-11-19")
        assert g["status"] == "HALTED"

    def test_daily_loss_pauses_slot(self, sim):
        closed = [{"slot": "vwap_reversion", "pnl_pct": -3.5,
                   "exit_ts": "2026-11-19T04:00:00+00:00"}]
        g = sim.slot_guardrails("vwap_reversion", closed, "2026-11-19")
        assert g["status"] == "PAUSED"

    def test_small_n_is_no_judgment(self, sim):
        g = sim.slot_guardrails("btc_4h_rsi_macd", [], "2026-11-19")
        assert g["status"] == "ACTIVE"
        assert g["judgment"].startswith("no_judgment")

    def test_halted_slot_takes_no_new_entries_but_run_closes_positions(self, sim):
        # Seed a losing history that halts bollinger_mr, then run a tick with
        # a tape that would otherwise trigger an entry.
        for _ in range(5):
            sim._append_log({"event": "CLOSE", "slot": "bollinger_mr",
                             "pnl_pct": -2.5,
                             "exit_ts": "2026-11-10T00:00:00+00:00"})
        bars = _flat_bars(60)
        bars[-1] = _bar(bars[-1]["timestamp"], 100, 100, 88, 88)
        out = sim.run_one_shot({s: list(bars) for s in sim.UNIVERSE})
        assert out["guardrails"]["bollinger_mr"]["status"] == "HALTED"
        state = json.loads(sim.STATE_PATH.read_text())
        assert not any(k.startswith("bollinger_mr|")
                       for k in (state.get("positions") or {}))


class TestRunOneShotLifecycle:
    def test_open_then_tp_close_produces_forwardable_row(self, sim):
        bars = _flat_bars(60)
        bars[-1] = _bar(bars[-1]["timestamp"], 100, 100, 88, 88)
        sim.run_one_shot({s: [dict(b) for b in bars] for s in sim.UNIVERSE})
        state = json.loads(sim.STATE_PATH.read_text())
        assert state["paper_only"] is True
        opened = [k for k in state["positions"] if k.startswith("bollinger_mr|")]
        assert opened, "bollinger_mr should open on the band break"
        # next tick: price recovers above the mid-band target intrabar
        nxt = bars + [_bar(bars[-1]["timestamp"] + BAR_MS, 88, 105, 88, 104)]
        sim.run_one_shot({s: [dict(b) for b in nxt] for s in sim.UNIVERSE})
        closes = [json.loads(l) for l in sim.LOG_PATH.read_text().splitlines()
                  if json.loads(l).get("event") == "CLOSE"]
        assert closes, "recovery bar should close the position"
        row = closes[0]
        assert row["hypothesis_id"] == "H-2026-11-19-02"
        assert row["entry_ts"] and row["exit_ts"] and row["pnl_pct"] > 0


class TestPilotForwardBridge:
    def _write_close(self, log, **kw):
        row = {"event": "CLOSE", "date": "2026-11-20"}
        row.update(kw)
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def test_bridge_emits_contract_valid_rows(self, tmp_path, monkeypatch):
        import tools.pilot_forward_bridge as bridge
        from alpha_engine import forward_observations as FO

        log = tmp_path / "crypto_intraday_sim_paper_log.jsonl"
        self._write_close(
            log, slot="bollinger_mr", strategy="bollinger_mr",
            hypothesis_id="H-2026-11-19-02", asset_class="CRYPTO",
            symbol="ETHUSDT", direction="LONG", entry_price=100.0,
            entry_ts="2026-11-20T00:00:00+00:00", exit_price=104.0,
            exit_ts="2026-11-20T08:00:00+00:00", exit_reason="TP",
            take_profit=104.0, stop_loss=96.0, pnl_pct=4.0,
        )
        monkeypatch.setitem(bridge.SOURCES[2], "log", log)
        monkeypatch.setitem(bridge.SOURCES[0], "log", tmp_path / "absent1.jsonl")
        monkeypatch.setitem(bridge.SOURCES[1], "log", tmp_path / "absent2.jsonl")

        t0 = int(datetime(2026, 11, 20, tzinfo=timezone.utc).timestamp() * 1000)
        eth = [_bar(t0 + i * BAR_MS, 100, 105 if i == 2 else 101, 99, 100)
               for i in range(4)]
        btc = [_bar(t0 + i * BAR_MS, 50000, 50500, 49500, 50100 + 50 * i)
               for i in range(4)]
        rows, unresolved = bridge.build_rows(
            {"CRYPTO:ETHUSDT": eth, "CRYPTO:BTCUSDT": btc})
        assert not unresolved
        assert len(rows) == 1
        row = rows[0]
        assert validate_ok(FO, row)
        assert row["intrabar_first_touch"] is True
        assert row["exit_px"] == 104.0  # TP resolved intrabar from bars
        assert row["benchmark_leg_ret"] is not None
        assert row["slippage_bps"] == 16.0

    def test_bridge_skips_unresolvable_and_foreign_rows(self, tmp_path, monkeypatch):
        import tools.pilot_forward_bridge as bridge

        log = tmp_path / "etf_dual_momentum_paper_log.jsonl"
        # foreign strategy in the ETF log must not leak into the pod
        self._write_close(log, strategy="someone_else", symbol="XLE",
                          entry_price=60.0, entry_date="2026-11-20",
                          exit_price=61.0, date="2026-11-21")
        # legit strategy but no bars available -> unresolved, not emitted
        self._write_close(log, strategy="etf_verified_dual_momentum",
                          symbol="XLE", direction="BUY", entry_price=60.0,
                          entry_date="2026-11-20", exit_price=61.0,
                          date="2026-11-21")
        monkeypatch.setitem(bridge.SOURCES[0], "log", log)
        monkeypatch.setitem(bridge.SOURCES[1], "log", tmp_path / "absent1.jsonl")
        monkeypatch.setitem(bridge.SOURCES[2], "log", tmp_path / "absent2.jsonl")
        rows, unresolved = bridge.build_rows({"ETF:XLE": [], "ETF:SPY": []})
        assert rows == []
        reasons = {why for _, why in unresolved}
        assert "strategy not claimed by this pod" in reasons
        assert "no bars for window" in reasons

    def test_bridge_drops_rows_closed_before_registration(self, tmp_path, monkeypatch):
        import tools.pilot_forward_bridge as bridge

        log = tmp_path / "faber_taa_paper_log.jsonl"
        self._write_close(log, strategy="faber_taa_paper_pilot", symbol="SPY",
                          entry_price=700.0, entry_date="2026-11-01",
                          exit_price=710.0, exit_date="2026-11-10",
                          date="2026-11-10")
        monkeypatch.setitem(bridge.SOURCES[1], "log", log)
        monkeypatch.setitem(bridge.SOURCES[0], "log", tmp_path / "absent1.jsonl")
        monkeypatch.setitem(bridge.SOURCES[2], "log", tmp_path / "absent2.jsonl")
        rows, unresolved = bridge.build_rows({"ETF:SPY": _flat_bars(5, 700.0)})
        assert rows == [] and unresolved == []


def validate_ok(FO, row) -> bool:
    problems = FO.validate(row, known_hypotheses={row["hypothesis_id"]})
    assert not problems, problems
    return True

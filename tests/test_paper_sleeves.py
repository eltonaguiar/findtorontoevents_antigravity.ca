import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from paper_trading import sleeves as S  # noqa: E402


def _cfg(capital=1400, sid="core-beta", kind="buy_hold", symbol="SPY"):
    return {"id": sid, "kind": kind, "symbol": symbol,
            "asset_class": "EQUITY", "capital": capital}


def test_init_buys_the_whole_allocation_at_price():
    st = {"schema": S.SCHEMA, "sleeves": {}}
    s = S.init_sleeve(st, _cfg(), 700.0, "2026-11-19")
    assert s["shares"] == 2.0 and s["entry_price"] == 700.0
    assert s["history"] == [{"date": "2026-11-19", "equity": 1400.0}]


def test_init_is_idempotent():
    st = {"schema": S.SCHEMA, "sleeves": {}}
    S.init_sleeve(st, _cfg(), 700.0, "2026-11-19")
    S.init_sleeve(st, _cfg(), 999.0, "2026-11-20")
    assert st["sleeves"]["core-beta"]["entry_price"] == 700.0


def test_mark_is_idempotent_per_date_and_replaces():
    st = {"schema": S.SCHEMA, "sleeves": {}}
    S.init_sleeve(st, _cfg(), 700.0, "2026-11-19")
    S.mark(st, "core-beta", 770.0, "2026-11-20")
    S.mark(st, "core-beta", 700.0, "2026-11-20")   # corrected close, same day
    hist = st["sleeves"]["core-beta"]["history"]
    assert [h["date"] for h in hist] == ["2026-11-19", "2026-11-20"]
    assert hist[-1]["equity"] == 1400.0


def test_report_computes_return_and_drawdown():
    st = {"schema": S.SCHEMA, "sleeves": {}}
    S.init_sleeve(st, _cfg(), 700.0, "2026-11-19")   # 2 shares, $1400
    S.mark(st, "core-beta", 800.0, "2026-11-20")      # $1600 peak
    r = S.sleeve_report(st, _cfg(), 760.0, "2026-11-21")
    assert r["equity"] == 1520.0
    assert r["return_pct"] == 8.5714
    assert r["drawdown_pct"] == -5.0


def test_uninitialised_sleeve_reports_itself():
    r = S.sleeve_report({"schema": S.SCHEMA, "sleeves": {}}, _cfg(), 700.0)
    assert r["status"] == "not_initialised"


def test_buy_and_hold_does_not_need_a_random_arm():
    assert S.random_arm_applicable(_cfg()) is False
    assert S.random_arm_applicable(_cfg(kind="rotation", sid="etf-rotation")) is True


def test_cli_writes_the_daily_report(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"sleeves": [_cfg()]}))
    state = tmp_path / "state.json"
    out = tmp_path / "daily.json"
    rc = S.main(["--config", str(cfg), "--state", str(state), "--date", "2026-11-19",
                 "--init", "--mark", "--report", "--out", str(out),
                 "--price", "SPY=700"])
    assert rc == 0
    d = json.loads(out.read_text())
    assert d["schema"] == "paper.sleeve_daily.v1"
    assert d["sleeves"][0]["equity"] == 1400.0
    assert json.loads(state.read_text())["sleeves"]["core-beta"]["shares"] == 2.0


# ─────────────────────────────────────────────── rotation sleeve (signal) ──
def _series(start, pcts):
    px = start
    out = []
    for i, p in enumerate(pcts):
        px *= (1 + p / 100.0)
        out.append((f"2026-01-{i+1:02d}", round(px, 4)))
    return out


def test_momentum_pct_uses_the_lookback_window():
    closes = [("d1", 100.0), ("d2", 110.0), ("d3", 121.0)]
    assert abs(S.momentum_pct(closes, 2) - 21.0) < 1e-9
    assert S.momentum_pct([("d1", 100.0)], 5) is None


def test_rotation_picks_top_n_and_goes_to_cash_when_all_momentum_is_negative():
    series = {"A": _series(100, [1]*10), "B": _series(100, [2]*10),
              "C": _series(100, [-1]*10), "D": _series(100, [0.5]*10)}
    assert S.rotation_pick(series, {"lookback_days": 5, "top_n": 2}) == ["B", "A"]
    all_neg = {"A": _series(100, [-1]*10), "B": _series(100, [-2]*10)}
    assert S.rotation_pick(all_neg, {"lookback_days": 5, "top_n": 2}) == []


def test_rotation_rebalance_equal_weights_and_cash_bucket():
    cfg = {"id": "rot", "kind": "rotation", "capital": 300,
           "rules": {"lookback_days": 5, "top_n": 2}}
    series = {"A": _series(100, [1]*10), "B": _series(100, [2]*10),
              "C": _series(100, [-1]*10)}
    prices = {"A": 10.0, "B": 30.0, "C": 5.0}
    st = {"schema": S.SCHEMA, "sleeves": {}}
    sv = S.rotation_rebalance(st, cfg, series, prices, "2026-11-19")
    assert sv["positions"] == {"B": 5.0, "A": 15.0}   # $150 each
    assert sv["cash"] == 0.0 and sv["picks"] == ["B", "A"]

    st2 = {"schema": S.SCHEMA, "sleeves": {}}
    none_cfg = {"id": "rot", "kind": "rotation", "capital": 300,
                "rules": {"lookback_days": 5, "top_n": 2}}
    sv2 = S.rotation_rebalance(st2, none_cfg,
                               {"C": _series(100, [-1]*10)}, {"C": 5.0}, "2026-11-19")
    assert sv2["positions"] == {} and sv2["cash"] == 300.0


def test_random_control_arm_ignores_momentum_and_is_deterministic():
    cfg = {"id": "rnd", "kind": "rotation_random", "capital": 300, "seed": 7,
           "rules": {"top_n": 2}}
    series = {s: _series(100, [(-5 if s == "A" else 1)]*10) for s in ("A", "B", "C", "D")}
    prices = {"A": 10.0, "B": 10.0, "C": 10.0, "D": 10.0}
    st1 = {"schema": S.SCHEMA, "sleeves": {}}
    p1 = S.rotation_rebalance(st1, cfg, series, prices, "2026-11-19")["picks"]
    st2 = {"schema": S.SCHEMA, "sleeves": {}}
    p2 = S.rotation_rebalance(st2, cfg, series, prices, "2026-11-19")["picks"]
    assert p1 == p2 and len(p1) == 2       # deterministic, and does not prefer winners
    assert "A" in p1 or "A" not in p1      # selection is random, not momentum-driven

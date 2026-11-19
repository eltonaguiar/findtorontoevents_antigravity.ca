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

"""The QA ledger must reconcile its own counters, honour a quarantine, and check
that a published PnL is implied by the row's own prices.

2026-11-21: run 44849286981 printed "18 flags (12 critical)" while the per-class
lines summed to 11 -- PNL_OUT_OF_BOUNDS was flagged but never counted, so the
summary could not explain its own red. And two classes were invisible: a
quarantined row still publishing a PnL, and a PnL no pair of published prices
implies.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(monkeypatch, tmp_path, picks):
    spec = importlib.util.spec_from_file_location("qa_ledger", ROOT / "tools" / "qa_ledger.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    live = tmp_path / "live.json"
    out = tmp_path / "qa.json"
    live.write_text(json.dumps({"picks": picks}), encoding="utf-8")
    monkeypatch.setattr(mod, "LIVE_JSON", live)
    monkeypatch.setattr(mod, "OUT_JSON", out)
    monkeypatch.setattr(mod, "fetch_external", lambda sym, aclass: (None, None))
    rc = mod.run()
    return rc, json.loads(out.read_text())


def _row(**kw):
    base = {"symbol": "AAA", "asset_class": "EQUITY", "direction": "LONG",
            "entry_price": 100.0, "current_price": 101.0, "pnl_pct": 1.0,
            "tp_pct": 5.0, "sl_pct": -3.0}
    base.update(kw)
    return base


def test_clean_row_passes(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [_row()])
    assert rc == 0
    assert rep["flag_counts"] == {"total": 0, "critical": 0}
    assert rep["by_class"]["EQUITY"]["self_inconsistent"] == 0


def test_out_of_bounds_is_counted_so_the_summary_reconciles(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [
        _row(symbol="MBS", asset_class="BOND", entry_price=8.295,
             current_price=58.215, pnl_pct=601.81)])
    assert rc == 1
    bond = rep["by_class"]["BOND"]
    assert bond["out_of_bounds"] == 1
    # the printed counters must explain the critical count
    assert rep["flag_counts"]["critical"] == 1
    assert sum(v for k, v in bond.items() if k != "n") == 1
    assert any(f["verdict"] == "PNL_OUT_OF_BOUNDS" for f in rep["flags"])


def test_quarantined_row_is_not_unpriced_and_passes(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [
        _row(symbol="MBS", asset_class="BOND", current_price=None, pnl_pct=None,
             quarantined=True, price_source="quarantined:implausible_move")])
    assert rc == 0
    assert rep["by_class"]["BOND"]["quarantined"] == 1
    assert rep["flag_counts"]["total"] == 0


def test_quarantine_that_still_publishes_a_pnl_is_critical(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [
        _row(quarantined=True, price_source="quarantined:implausible_move")])
    assert rc == 1
    assert rep["by_class"]["EQUITY"]["quarantine_leak"] == 1
    assert any(f["verdict"] == "QUARANTINE_LEAK" for f in rep["flags"])


def test_pnl_not_implied_by_its_own_prices_is_flagged(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [
        _row(entry_price=100.0, current_price=110.0, pnl_pct=5.0)])
    assert rc == 1
    assert rep["by_class"]["EQUITY"]["self_inconsistent"] == 1
    assert any(f["verdict"] == "SELF_INCONSISTENT" for f in rep["flags"])


def test_blank_tp_sl_is_a_flag_but_not_critical(monkeypatch, tmp_path):
    rc, rep = _run(monkeypatch, tmp_path, [_row(tp_pct=None, sl_pct=None)])
    assert rc == 0
    assert rep["flag_counts"] == {"total": 1, "critical": 0}

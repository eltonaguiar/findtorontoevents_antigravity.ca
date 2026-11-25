"""The QA ledger must reconcile its own counters, honour a quarantine, and check
that a published PnL is implied by the row's own prices.

2026-11-21: run 44849286981 printed "18 flags (12 critical)" while the per-class
lines summed to 11 -- PNL_OUT_OF_BOUNDS was flagged but never counted, so the
summary could not explain its own red. And two classes were invisible: a
quarantined row still publishing a PnL, and a PnL no pair of published prices
implies.

2026-11-25: the fixture below wrote `{"picks": [...]}` with no `generated_at`,
so every case silently picked up the `STALE_SNAPSHOT` critical flag that
`bd6f9e30de9d` added a freshness gate for. All five assertions that expect
`rc == 0` failed on a clean `main` -- the tool was right and the fixture was
stale. `tools/qa_ledger_selftest.py` (same commit) already asserts the opposite
of what this file asserted, so the two suites contradicted each other and only
`CI Tests` noticed. The fixture now stamps a fresh `generated_at`, and
`test_missing_generated_at_is_critical` pins the contract in pytest so the two
suites cannot drift apart again.
"""
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fresh_stamp(minutes_ago=0):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


_NOW = object()  # sentinel: stamp at call time, never at import time


def _run(monkeypatch, tmp_path, picks, external=(None, None), generated_at=_NOW):
    """Run the ledger against a synthetic snapshot.

    `generated_at` defaults to "now" because an un-stamped snapshot is itself a
    critical condition -- the freshness gate cannot prove it is current. Pass
    `generated_at=None` to model that case deliberately.
    """
    if generated_at is _NOW:
        generated_at = _fresh_stamp()
    spec = importlib.util.spec_from_file_location("qa_ledger", ROOT / "tools" / "qa_ledger.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    live = tmp_path / "live.json"
    out = tmp_path / "qa.json"
    snapshot = {"picks": picks}
    if generated_at is not None:
        snapshot["generated_at"] = generated_at
    live.write_text(json.dumps(snapshot), encoding="utf-8")
    monkeypatch.setattr(mod, "LIVE_JSON", live)
    monkeypatch.setattr(mod, "OUT_JSON", out)
    monkeypatch.setattr(mod, "fetch_external", lambda sym, aclass: external)
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


def test_null_entry_price_with_a_live_quote_does_not_kill_the_run(monkeypatch, tmp_path):
    """float(None) raised before OUT_JSON was written, so CI kept a stale artifact."""
    rc, rep = _run(monkeypatch, tmp_path, [_row(entry_price=None, current_price=101.0)],
                   external=(101.5, "ext"))
    assert rep["n_picks"] == 1
    assert rep["by_class"]["EQUITY"]["mismatch"] == 0


def test_forex_priced_by_the_validation_feed_is_counted_not_flagged(monkeypatch, tmp_path):
    """Same feed on both sides means diff 0 by construction: count, never claim verified."""
    rc, rep = _run(monkeypatch, tmp_path, [
        _row(symbol="EURUSD", asset_class="FOREX", entry_price=1.10,
             current_price=1.101, pnl_pct=0.09, price_source="forex_failover")],
        external=(1.20, "forex_failover"))
    assert rc == 0
    assert rep["by_class"]["FOREX"]["unverified_source"] == 1
    assert rep["by_class"]["FOREX"]["mismatch"] == 0
    assert rep["flag_counts"]["total"] == 0


def test_missing_generated_at_is_critical(monkeypatch, tmp_path):
    """Pins the freshness contract so this file and tools/qa_ledger_selftest.py
    cannot contradict each other again.

    A snapshot with no `generated_at` cannot be proven current, so the ledger
    must raise a critical STALE_SNAPSHOT and exit 1. `_run` stamps a fresh
    timestamp by default, so pass None to model the un-stamped case.
    """
    rc, rep = _run(monkeypatch, tmp_path, [_row()], generated_at=None)
    assert rc == 1
    assert rep["flag_counts"]["critical"] >= 1
    snapshot_flags = [f for f in rep["flags"] if f["verdict"] == "STALE_SNAPSHOT"]
    assert snapshot_flags, "un-stamped snapshot must raise STALE_SNAPSHOT"
    assert any(f["asset_class"] == "SNAPSHOT" for f in snapshot_flags)


def test_stale_generated_at_is_critical(monkeypatch, tmp_path):
    """A snapshot older than the freshness limit is the same failure as a missing one."""
    rc, rep = _run(monkeypatch, tmp_path, [_row()], generated_at=_fresh_stamp(minutes_ago=600))
    assert rc == 1
    assert any(f["verdict"] == "STALE_SNAPSHOT" for f in rep["flags"])


def test_fresh_generated_at_is_not_flagged(monkeypatch, tmp_path):
    """Guard against over-correcting: a fresh stamp must not trip the gate."""
    rc, rep = _run(monkeypatch, tmp_path, [_row()])
    assert rc == 0
    assert not any(f["verdict"] == "STALE_SNAPSHOT" for f in rep["flags"])

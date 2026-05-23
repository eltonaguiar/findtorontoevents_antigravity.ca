"""Tests for D-001 CT=F COT-filtered shadow tracker (tools/ctf_shadow_tracker.py)."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_pick(
    symbol="CT=F",
    asset_class="COMMODITY",
    status="open",
    direction="LONG",
    entry_price=82.0,
    take_profit=90.0,
    stop_loss=78.0,
    confidence=0.70,
    pick_id="test-pick-001",
    cot_date: str | None = None,
    days_ago: int = 0,
) -> dict:
    if cot_date is None:
        # Fresh COT date by default
        cot_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    entry_date = (datetime.now(timezone.utc).date() - timedelta(days=days_ago)).isoformat()
    return {
        "id": pick_id,
        "symbol": symbol,
        "asset_class": asset_class,
        "status": status,
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "strategy": "test_strategy",
        "entry_date": entry_date,
        "extra": {"latest_cot_date": cot_date},
    }


def _run_tracker(picks: list[dict], dry_run: bool = False,
                 current_price: float | None = None) -> tuple[int, list[dict]]:
    """Run the tracker with synthetic picks, return (rc, logged_entries)."""
    import tools.ctf_shadow_tracker as t

    with tempfile.TemporaryDirectory() as td:
        picks_path = Path(td) / "active_picks.json"
        log_path = Path(td) / "ctf_shadow_log.jsonl"
        picks_path.write_text(json.dumps(picks), encoding="utf-8")

        # Patch paths and price feed
        orig_active = t._ACTIVE_PICKS
        orig_fetch = t._fetch_ctf_price
        t._ACTIVE_PICKS = picks_path
        t._fetch_ctf_price = lambda: current_price

        try:
            rc = t.main(dry_run=dry_run, log_path=log_path)
            entries = []
            if log_path.exists():
                for line in log_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        finally:
            t._ACTIVE_PICKS = orig_active
            t._fetch_ctf_price = orig_fetch

    return rc, entries


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCtfShadowTrackerBasics:
    def test_dry_run_returns_zero_no_file(self):
        picks = [_make_pick()]
        with tempfile.TemporaryDirectory() as td:
            import tools.ctf_shadow_tracker as t
            log_path = Path(td) / "ctf_shadow_log.jsonl"
            orig = t._ACTIVE_PICKS
            picks_path = Path(td) / "active_picks.json"
            picks_path.write_text(json.dumps(picks), encoding="utf-8")
            t._ACTIVE_PICKS = picks_path
            orig_fetch = t._fetch_ctf_price
            t._fetch_ctf_price = lambda: 82.0
            try:
                rc = t.main(dry_run=True, log_path=log_path)
            finally:
                t._ACTIVE_PICKS = orig
                t._fetch_ctf_price = orig_fetch
            assert rc == 0
            assert not log_path.exists(), "dry-run must not write file"

    def test_eligible_ctf_pick_logged(self):
        pick = _make_pick()
        rc, entries = _run_tracker([pick])
        assert rc == 0
        logged = [e for e in entries if e.get("_entry_logged")]
        assert len(logged) == 1
        assert logged[0]["symbol"] == "CT=F"
        assert logged[0]["direction"] == "LONG"

    def test_non_ctf_symbol_skipped(self):
        pick = _make_pick(symbol="GC=F", asset_class="COMMODITY")
        rc, entries = _run_tracker([pick])
        assert rc == 0
        assert entries == [], "GC=F should not be logged"

    def test_non_commodity_class_skipped(self):
        pick = _make_pick(asset_class="FUTURES")
        rc, entries = _run_tracker([pick])
        assert rc == 0
        assert entries == []

    def test_closed_pick_skipped(self):
        pick = _make_pick(status="closed")
        rc, entries = _run_tracker([pick])
        assert rc == 0
        assert entries == []

    def test_fail_open_empty_picks(self):
        rc, entries = _run_tracker([])
        assert rc == 0
        assert entries == []

    def test_fail_open_missing_picks_file(self):
        import tools.ctf_shadow_tracker as t
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "ctf_shadow_log.jsonl"
            orig = t._ACTIVE_PICKS
            t._ACTIVE_PICKS = Path(td) / "nonexistent.json"
            orig_fetch = t._fetch_ctf_price
            t._fetch_ctf_price = lambda: None
            try:
                rc = t.main(log_path=log_path)
            finally:
                t._ACTIVE_PICKS = orig
                t._fetch_ctf_price = orig_fetch
            assert rc == 0, "must be fail-open when picks file missing"


class TestCtfCotGate:
    def test_fresh_cot_date_passes(self):
        cot = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
        pick = _make_pick(cot_date=cot)
        rc, entries = _run_tracker([pick])
        assert len([e for e in entries if e.get("_entry_logged")]) == 1

    def test_stale_cot_date_rejected(self):
        stale = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()
        pick = _make_pick(cot_date=stale)
        rc, entries = _run_tracker([pick])
        assert entries == [], "stale COT date must be rejected"

    def test_missing_cot_date_rejected(self):
        pick = _make_pick()
        pick["extra"] = {}  # no latest_cot_date
        rc, entries = _run_tracker([pick])
        assert entries == [], "missing COT date must be rejected"

    def test_boundary_cot_date_passes(self):
        boundary = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
        pick = _make_pick(cot_date=boundary)
        rc, entries = _run_tracker([pick])
        assert len([e for e in entries if e.get("_entry_logged")]) == 1, \
            "exactly-at-boundary COT date (10 days) should pass"


class TestCtfExitLogic:
    def test_tp_hit_long(self):
        pick = _make_pick(direction="LONG", entry_price=80.0,
                          take_profit=90.0, stop_loss=75.0)
        rc, entries = _run_tracker([pick], current_price=91.0)
        exited = [e for e in entries if e.get("_exited")]
        assert len(exited) == 1
        assert exited[0]["exit_reason"] == "tp"
        assert exited[0]["_pnl_pct"] > 0

    def test_sl_hit_long(self):
        pick = _make_pick(direction="LONG", entry_price=80.0,
                          take_profit=90.0, stop_loss=75.0)
        rc, entries = _run_tracker([pick], current_price=74.0)
        exited = [e for e in entries if e.get("_exited")]
        assert len(exited) == 1
        assert exited[0]["exit_reason"] == "sl"
        assert exited[0]["_pnl_pct"] < 0

    def test_tp_hit_short(self):
        pick = _make_pick(direction="SHORT", entry_price=82.0,
                          take_profit=76.0, stop_loss=87.0)
        rc, entries = _run_tracker([pick], current_price=75.0)
        exited = [e for e in entries if e.get("_exited")]
        assert len(exited) == 1
        assert exited[0]["exit_reason"] == "tp"
        assert exited[0]["_pnl_pct"] > 0

    def test_time_stop(self):
        pick = _make_pick(days_ago=11, direction="LONG", entry_price=80.0,
                          take_profit=90.0, stop_loss=75.0)
        # price neither hits TP nor SL
        rc, entries = _run_tracker([pick], current_price=82.0)
        exited = [e for e in entries if e.get("_exited")]
        assert len(exited) == 1
        assert exited[0]["exit_reason"] == "time_stop"

    def test_no_exit_when_price_in_range(self):
        pick = _make_pick(direction="LONG", entry_price=80.0,
                          take_profit=90.0, stop_loss=75.0)
        rc, entries = _run_tracker([pick], current_price=82.0)
        open_picks = [e for e in entries if e.get("_entry_logged") and not e.get("_exited")]
        assert len(open_picks) == 1

    def test_no_duplicate_logging(self):
        pick = _make_pick()
        rc, entries = _run_tracker([pick], current_price=82.0)
        first_count = len([e for e in entries if e.get("_entry_logged")])
        # Second run with same pick should not add another entry
        import tools.ctf_shadow_tracker as t
        with tempfile.TemporaryDirectory() as td:
            picks_path = Path(td) / "active_picks.json"
            log_path = Path(td) / "log.jsonl"
            picks_path.write_text(json.dumps([pick]), encoding="utf-8")
            orig_a, orig_f = t._ACTIVE_PICKS, t._fetch_ctf_price
            t._ACTIVE_PICKS = picks_path
            t._fetch_ctf_price = lambda: 82.0
            try:
                t.main(log_path=log_path)
                t.main(log_path=log_path)  # second run
                entries2 = [json.loads(l) for l in
                            log_path.read_text().splitlines() if l.strip()]
            finally:
                t._ACTIVE_PICKS = orig_a
                t._fetch_ctf_price = orig_f
        logged = [e for e in entries2 if e.get("_entry_logged")]
        assert len(logged) == 1, "same pick must not be logged twice"

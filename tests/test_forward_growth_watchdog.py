import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import forward_growth_watchdog as W  # noqa: E402

NOW = datetime(2026, 11, 19, 21, 0, tzinfo=timezone.utc)


def test_no_eligible_rows_is_ok_even_with_an_empty_ledger():
    v = W.assess(0, None, NOW)
    assert v["ok"] is True and v["status"] == "no_eligible_rows"


def test_eligible_rows_with_no_ledger_row_fails():
    v = W.assess(50, None, NOW)
    assert v["ok"] is False and v["status"] == "ledger_empty"


def test_fresh_row_passes():
    v = W.assess(50, (NOW - timedelta(hours=6)).isoformat(), NOW)
    assert v["ok"] is True and v["status"] == "growing"
    assert v["age_days"] < 1


def test_stale_row_fails_at_the_threshold():
    v = W.assess(50, (NOW - timedelta(days=7, hours=1)).isoformat(), NOW)
    assert v["ok"] is False and v["status"] == "stalled"
    assert "STALLED" in v["detail"]


def test_threshold_is_inclusive_at_exactly_seven_days():
    v = W.assess(50, (NOW - timedelta(days=7)).isoformat(), NOW)
    assert v["ok"] is True


def test_newest_timestamp_handles_z_suffix_and_opened_at():
    rows = [{"created_at": "2026-11-01T00:00:00Z"},
            {"opened_at": "2026-11-10T00:00:00Z"}]
    ts = W.newest_timestamp(rows)
    assert ts and ts.startswith("2026-11-10")

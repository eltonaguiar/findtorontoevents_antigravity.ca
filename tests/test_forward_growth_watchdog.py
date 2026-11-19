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


# ─────────────────────────────────── per-hypothesis + pod coverage (B3b) ──
ROWS = [{"hypothesis_id": "H-119", "created_at": (NOW - timedelta(days=1)).isoformat()},
        {"hypothesis_id": "H-119", "created_at": (NOW - timedelta(days=2)).isoformat()}]


def test_per_hypothesis_flags_a_starved_hypothesis_while_another_is_fresh():
    stale = ROWS + [{"hypothesis_id": "H-OLD",
                     "created_at": (NOW - timedelta(days=30)).isoformat()}]
    got = {h["hypothesis_id"]: h for h in
           W.per_hypothesis(stale, {"H-119": 400, "H-OLD": 5}, NOW)}
    assert got["H-119"]["ok"] is True
    assert got["H-OLD"]["ok"] is False and got["H-OLD"]["status"] == "stalled"


def test_hypothesis_with_eligible_rows_but_no_ledger_row_fails():
    got = W.per_hypothesis(ROWS, {"H-119": 400, "H-BABY": 3}, NOW)
    baby = next(h for h in got if h["hypothesis_id"] == "H-BABY")
    assert baby["ok"] is False and baby["status"] == "missing_rows"


def test_pre_registered_pod_inside_grace_is_a_warning_not_a_failure():
    manifest = {"pods": [{"id": "POD-X", "status": "pre_registered",
                          "hypothesis_id": "H-X",
                          "registered_at": (NOW - timedelta(days=2)).date().isoformat()}]}
    pods = W.pod_coverage(manifest, ROWS, NOW, grace_days=7)
    assert pods[0]["severity"] == "WARN" and pods[0]["ok"] is True


def test_pre_registered_pod_past_grace_with_zero_rows_fails():
    manifest = {"pods": [{"id": "POD-X", "status": "pre_registered",
                          "hypothesis_id": "H-X",
                          "registered_at": (NOW - timedelta(days=10)).date().isoformat()}]}
    pods = W.pod_coverage(manifest, ROWS, NOW, grace_days=7)
    assert pods[0]["severity"] == "FAIL" and pods[0]["ok"] is False


def test_pod_with_rows_is_not_reported_as_starved():
    manifest = {"pods": [{"id": "POD-H119", "status": "pre_registered",
                          "hypothesis_id": "H-119",
                          "registered_at": (NOW - timedelta(days=30)).date().isoformat()}]}
    assert W.pod_coverage(manifest, ROWS, NOW, grace_days=7) == []


def test_assess_all_fails_when_a_pod_is_starved_even_if_global_is_fresh():
    manifest = {"pods": [{"id": "POD-EQUITY-BREAKOUT", "status": "pre_registered",
                          "hypothesis_id": "H-BABY",
                          "registered_at": (NOW - timedelta(days=10)).date().isoformat()}]}
    v = W.assess_all(430, ROWS, {"H-119": 430}, manifest, NOW)
    assert v["ok"] is False and v["n_failed"] >= 1

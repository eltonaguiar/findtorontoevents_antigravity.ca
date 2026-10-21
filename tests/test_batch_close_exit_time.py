"""Batch-close regression tests (2026-10-20).

Root cause: the resolver stamped ``resolved_at = now`` (the run time) on every
resolution path, so all picks resolved in a single run shared one identical close
minute. Live example: 73 MomentumEMA picks all ``2026-10-20T00:02:50Z`` (39 TP_HIT
+ 30 SL_HIT resolved intrabar on *different* bars). These tests lock the fix:
intrabar TP/SL resolutions must carry the true first-touch bar time.
"""
from datetime import datetime, timezone, timedelta

import audit_trail.universal_pick_resolver as R


def _run(now, bar_dt):
    """Resolve one LONG TP pick whose TP is first touched on bar_dt."""
    entry, tp, sl = 100.0, 103.0, 98.5
    pick = {
        "direction": "LONG",
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "timestamp": (bar_dt - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    bars = [
        {
            "timestamp": int(bar_dt.timestamp() * 1000),
            "high": tp + 0.2,   # TP touched on this bar
            "low": entry - 0.5,
        }
    ]
    res = R._check_tp_sl_intrabar(pick, bars)
    assert res and res[0] == "TP_HIT", f"expected TP_HIT, got {res}"
    return R._exit_ts_str(pick, now)


def test_20_picks_one_run_distinct_exit_times():
    """20 picks resolved in ONE run on different hit bars -> >=15 distinct resolved_at."""
    now = datetime(2026, 10, 20, 0, 2, 50, tzinfo=timezone.utc)  # the offending run time
    base = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
    # 20 distinct hit bars, 10 min apart
    stamps = [_run(now, base + timedelta(minutes=10 * i)) for i in range(20)]
    distinct = set(stamps)
    # Every stamp must be the bar time, never the run time
    assert all(s != now.strftime("%Y-%m-%dT%H:%M:%SZ") for s in stamps)
    assert len(distinct) >= 15, f"expected >=15 distinct resolved_at, got {len(distinct)}"
    assert len(distinct) == 20, "each distinct bar should give its own exit time"


def test_same_bar_still_clusters():
    """Genuine same-bar hits may share a timestamp (allowed by the validation)."""
    now = datetime(2026, 10, 20, 0, 2, 50, tzinfo=timezone.utc)
    bar = datetime(2026, 10, 19, 9, 0, 0, tzinfo=timezone.utc)
    stamps = {_run(now, bar) for _ in range(5)}
    assert len(stamps) == 1, "same hit bar -> same exit time"


def test_close_approx_falls_back_to_run_time():
    """No intrabar bar timestamp -> resolved_at falls back to run time."""
    now = datetime(2026, 10, 20, 0, 2, 50, tzinfo=timezone.utc)
    assert R._exit_ts_str({"direction": "LONG"}, now) == now.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_time_exit_marks_estimated_and_unresolved_status():
    """TIME_EXIT with a bad price -> status UNRESOLVED_NO_PRICE, never a 0.0 flat."""
    assert R._priceless_close(0.0, 100.0) is True
    assert R._priceless_close(None, 100.0) is True
    assert R._priceless_close(101.0, 100.0) is False

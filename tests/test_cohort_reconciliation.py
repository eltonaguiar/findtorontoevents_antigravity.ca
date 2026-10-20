# tests/test_cohort_reconciliation.py
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.cohort_reconciliation import load_json, parse_ts


def _write_tmp(tmp_path, data):
    p = tmp_path / "f.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_load_json_reads_valid(tmp_path):
    p = _write_tmp(tmp_path, {"a": 1})
    assert load_json(p) == {"a": 1}


def test_load_json_returns_none_when_missing(tmp_path):
    assert load_json(str(tmp_path / "nope.json")) is None


def test_load_json_raises_on_malformed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    try:
        load_json(str(p))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_ts_normalizes_z_and_microseconds():
    dt = parse_ts("2026-10-19T19:32:56.089767Z")
    assert dt.isoformat().startswith("2026-10-19T19:32:56")
    assert dt.tzinfo is not None
    dt2 = parse_ts("2026-06-21T06:31:08+00:00")
    assert dt2.tzinfo is not None


from tools.cohort_reconciliation import _pf, metric_block, recompute_rolling_metrics


def _rec(pnl, closed_at, strategy="s1", asset_class="EQUITY"):
    return {"strategy": strategy, "asset_class": asset_class,
            "pnl_pct": pnl, "closed_at": closed_at,
            "source_system": "alpha_engine", "id": "x"}


def test_pf_basic():
    rows = [_rec(2.0, "2026-10-19T00:00:00Z"), _rec(-1.0, "2026-10-19T00:00:00Z")]
    assert _pf(rows) == 2.0


def test_pf_no_losses_is_inf():
    assert _pf([_rec(1.0, "2026-10-19T00:00:00Z")]) == "inf"


def test_pf_empty_is_none():
    assert _pf([]) is None


def test_metric_block_hides_wr_below_20():
    rows = [_rec(1.0 if i % 2 == 0 else -1.0, "2026-10-19T00:00:00Z") for i in range(10)]
    m = metric_block(rows)
    assert m["n"] == 10
    assert m["win_rate"] is None
    assert m["win_rate_hidden"] is True


def test_metric_block_shows_wr_at_20():
    rows = [_rec(1.0 if i % 2 == 0 else -1.0, "2026-10-19T00:00:00Z") for i in range(20)]
    m = metric_block(rows)
    assert m["win_rate"] == 0.5
    assert m["win_rate_hidden"] is False


def test_recompute_coverage_complete():
    generated = "2026-10-20T00:00:00Z"
    start = "2026-10-05T00:00:00Z"  # 15d before -> covers 14d window
    records = [_rec(1.0, start), _rec(-1.0, "2026-10-19T00:00:00Z")]
    out = recompute_rolling_metrics(records, 336, generated)
    assert out["coverage"]["status"] == "complete"
    # Only the in-window record (>= window start 2026-10-06) counts toward metrics
    assert out["by_class"]["EQUITY"]["n"] == 1


def test_recompute_coverage_incomplete():
    generated = "2026-10-20T00:00:00Z"
    start = "2026-10-18T00:00:00Z"  # only 2d back -> incomplete for 14d
    records = [_rec(1.0, start)]
    out = recompute_rolling_metrics(records, 336, generated)
    assert out["coverage"]["status"] == "incomplete_coverage"

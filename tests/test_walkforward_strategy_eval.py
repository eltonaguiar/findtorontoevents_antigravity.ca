"""Tests for the walk-forward strategy evaluation harness (tools/walkforward_strategy_eval.py).

This is the "closest to forward test" tool: it applies artifact filters and a
strict chronological out-of-sample split to closed resolved picks, then ranks
cells whose edge survives out-of-sample.
"""
import os.path
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.walkforward_strategy_eval import (
    clean_picks,
    compute_cell_metrics,
    detect_artifact_cells,
    evaluate_all,
    load_picks,
    walkforward_split,
)


def _row(symbol="XYZ", direction="LONG", strategy="s1", asset_class="EQUITY",
         status="WON", pnl=2.0, exit_price=100.0, closed_at="2026-10-01T00:00:00Z"):
    return {
        "id": f"{symbol}|{direction}|{strategy}|{closed_at}",
        "symbol": symbol,
        "direction": direction,
        "strategy": strategy,
        "asset_class": asset_class,
        "status": status,
        "pnl_pct": pnl,
        "exit_price": exit_price,
        "entry_price": 98.0,
        "timestamp": closed_at,
        "closed_at": closed_at,
    }


def test_load_picks_returns_list(tmp_path):
    import json
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"picks": {"recent_closed": [_row()]}}))
    rows = load_picks(str(path))
    assert isinstance(rows, list)
    assert len(rows) == 1


def test_clean_picks_drops_sentinel_and_missing_pnl():
    rows = [
        _row(closed_at="2026-10-01T00:00:00Z"),
        _row(pnl=999999.9999, closed_at="2026-10-02T00:00:00Z"),
        _row(pnl=None, closed_at="2026-10-03T00:00:00Z"),
        _row(pnl=0.0, closed_at="2026-10-04T00:00:00Z"),
        _row(status="OPEN", pnl=None, closed_at="2026-10-05T00:00:00Z"),
    ]
    cleaned, dropped = clean_picks(rows)
    assert len(cleaned) == 1
    assert dropped["sentinel_placeholder"] == 2
    assert dropped["missing_pnl"] == 2


def test_clean_picks_dedupes_by_id():
    rows = [
        _row(closed_at="2026-10-01T00:00:00Z"),
        _row(closed_at="2026-10-01T00:00:00Z"),
    ]
    cleaned, dropped = clean_picks(rows)
    assert len(cleaned) == 1
    assert dropped["duplicate_ids"] == 1


def test_detect_artifact_cells_flags_repeated_exit():
    # 5 wins all on the same day at the same exit price -> frozen-exit artifact.
    rows = [
        _row(closed_at="2026-10-01T00:00:00Z", exit_price=100.0) for _ in range(5)
    ]
    artifact = detect_artifact_cells(rows)
    key = "EQUITY|XYZ|s1|LONG"
    assert key in artifact


def test_no_artifact_when_distinct_exits():
    rows = [
        _row(closed_at=f"2026-10-0{i}T00:00:00Z", exit_price=100.0 + i)
        for i in range(1, 6)
    ]
    artifact = detect_artifact_cells(rows)
    assert artifact == set()


def test_walkforward_split_is_chronological():
    rows = [
        _row(closed_at="2026-10-01T00:00:00Z"),
        _row(closed_at="2026-10-02T00:00:00Z"),
        _row(closed_at="2026-10-03T00:00:00Z"),
        _row(closed_at="2026-10-04T00:00:00Z"),
    ]
    train, test = walkforward_split(rows, frac=0.5)
    assert len(train) == 2 and len(test) == 2
    # every test row resolves at-or-after every train row
    train_latest = max(r["closed_at"] for r in train)
    assert all(r["closed_at"] >= train_latest for r in test)


def test_compute_cell_metrics_pf_wr():
    rows = [
        _row(status="WON", pnl=2.0),
        _row(status="WON", pnl=1.0),
        _row(status="LOST", pnl=-1.0),
        _row(status="LOST", pnl=-1.0),
    ]
    m = compute_cell_metrics(rows)
    assert m["n"] == 4
    assert m["wr"] == pytest.approx(0.5)
    assert m["pf"] == pytest.approx(3.0 / 2.0)


def test_evaluate_all_ranks_oos_stable_cell():
    # Cell A: strong in both halves (OOS-stable). Cell B: strong only early.
    rows = []
    for i in range(1, 21):  # 20 equally split
        day = f"2026-10-{i:02d}T00:00:00Z"
        rows.append(_row(symbol="AAA", direction="SHORT", strategy="stable",
                         asset_class="EQUITY", status="WON", pnl=1.5,
                         exit_price=100.0 - i, closed_at=day))
    # B: wins in first 10, losses in last 10
    for i in range(1, 21):
        day = f"2026-10-{i:02d}T00:00:00Z"
        st = "WON" if i <= 10 else "LOST"
        pnl = 1.5 if i <= 10 else -1.5
        rows.append(_row(symbol="BBB", direction="LONG", strategy="early_only",
                         asset_class="EQUITY", status=st, pnl=pnl,
                         exit_price=100.0 + i, closed_at=day))
    res = evaluate_all(rows)
    winner_keys = [c["key"] for c in res["winners"]]
    assert any("AAA" in k and "stable" in k for k in winner_keys)
    # early-only cell must not be a winner (test-side PF < 1)
    assert not any("BBB" in k and "early_only" in k for k in winner_keys)

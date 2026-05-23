"""Smoke tests for tools/quantstats_tearsheets.py.

These are unit-level: they don't require quantstats (we stub the heavy
HTML render) and they don't touch the production picks ledger. The
actual rendering path is exercised in CI only when quantstats is in
the environment (the smoke test below is skipped otherwise).
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

# Ensure tools/ is importable as a top-level package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import quantstats_tearsheets as qst  # noqa: E402


# ---------------------------------------------------------------------------
# load_closed_picks: container-shape detection
# ---------------------------------------------------------------------------


def _write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_load_picks_dashboard_data_shape(tmp_path):
    """audit_dashboard/data/dashboard_data.json shape: picks.recent_closed list."""
    p = tmp_path / "dashboard_data.json"
    _write_json(
        p,
        {
            "picks": {
                "active": [{"id": 1}],
                "recent_closed": [
                    {"id": "a", "asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T12:00:00Z"},
                    {"id": "b", "asset_class": "CRYPTO", "pnl_pct": -0.02, "closed_at": "2026-04-02T12:00:00Z"},
                ],
            }
        },
    )
    rows = qst.load_closed_picks(p)
    assert len(rows) == 2
    assert rows[0]["id"] == "a"


def test_load_picks_dashboard_payload_shape(tmp_path):
    """audit_trail/data/dashboard_payload.json shape: picks list."""
    p = tmp_path / "dashboard_payload.json"
    _write_json(p, {"picks": [{"id": "x", "pnl_pct": 0.0, "closed_at": "2026-04-01T00:00:00Z"}]})
    rows = qst.load_closed_picks(p)
    assert len(rows) == 1


def test_load_picks_top_level_list(tmp_path):
    """universal_resolved_picks.json shape: top-level list."""
    p = tmp_path / "universal_resolved_picks.json"
    _write_json(p, [{"id": "y", "pnl_pct": 0.05, "closed_at": "2026-04-01T00:00:00Z"}])
    rows = qst.load_closed_picks(p)
    assert len(rows) == 1


def test_load_picks_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        qst.load_closed_picks(tmp_path / "does_not_exist.json")


def test_load_picks_unknown_shape_raises(tmp_path):
    p = tmp_path / "weird.json"
    _write_json(p, {"foo": "bar"})
    with pytest.raises(ValueError):
        qst.load_closed_picks(p)


# ---------------------------------------------------------------------------
# picks_to_daily_returns: aggregation + unit-mismatch guard
# ---------------------------------------------------------------------------


def test_returns_aggregate_daily():
    pd = pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T01:00:00Z"},
        {"asset_class": "EQUITY", "pnl_pct": 0.02, "closed_at": "2026-04-01T23:00:00Z"},
        {"asset_class": "EQUITY", "pnl_pct": -0.005, "closed_at": "2026-04-02T08:00:00Z"},
        {"asset_class": "CRYPTO", "pnl_pct": 0.10, "closed_at": "2026-04-01T00:00:00Z"},
    ]
    s = qst.picks_to_daily_returns(picks, asset_class="EQUITY")
    assert isinstance(s, pd.Series)
    # 2 trading days, EQUITY only
    assert len(s) == 2
    assert s.iloc[0] == pytest.approx(0.03)  # 0.01 + 0.02
    assert s.iloc[1] == pytest.approx(-0.005)


def test_returns_filter_class():
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T00:00:00Z"},
        {"asset_class": "CRYPTO", "pnl_pct": 0.05, "closed_at": "2026-04-01T00:00:00Z"},
    ]
    eq = qst.picks_to_daily_returns(picks, asset_class="EQUITY")
    cr = qst.picks_to_daily_returns(picks, asset_class="CRYPTO")
    assert eq.iloc[0] == pytest.approx(0.01)
    assert cr.iloc[0] == pytest.approx(0.05)


def test_returns_drops_unparseable_timestamps():
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T00:00:00Z"},
        {"asset_class": "EQUITY", "pnl_pct": 0.02, "closed_at": "garbage"},
        {"asset_class": "EQUITY", "pnl_pct": 0.03, "closed_at": None},
    ]
    s = qst.picks_to_daily_returns(picks, asset_class="EQUITY")
    assert len(s) == 1
    assert s.iloc[0] == pytest.approx(0.01)


def test_returns_unit_forced_decimal_raises_on_mismatch():
    """If pnl_unit='decimal' is forced and the data is actually integer-percent,
    the unit-check raises (cycle10 unit-mismatch bug guard)."""
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 12.5, "closed_at": f"2026-04-{(i % 28) + 1:02d}T00:00:00Z"}
        for i in range(100)
    ]
    with pytest.raises(ValueError, match="unit mismatch"):
        qst.picks_to_daily_returns(picks, asset_class="EQUITY", pnl_unit="decimal")


def test_returns_unit_check_can_be_disabled():
    """``pnl_unit_check=False`` lets the caller opt out of the guard."""
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 50.0, "closed_at": "2026-04-01T00:00:00Z"},
    ]
    # Force decimal AND disable the check:
    s = qst.picks_to_daily_returns(
        picks, asset_class="EQUITY", pnl_unit="decimal", pnl_unit_check=False
    )
    assert s.iloc[0] == pytest.approx(50.0)


def test_detect_pnl_unit_percent():
    picks = [{"pnl_pct": v} for v in [3.4, 1.2, -2.0, 5.5, 4.1]]
    assert qst.detect_pnl_unit(picks) == "percent"


def test_detect_pnl_unit_decimal():
    picks = [{"pnl_pct": v} for v in [0.034, 0.012, -0.020, 0.055, 0.041]]
    assert qst.detect_pnl_unit(picks) == "decimal"


def test_detect_pnl_unit_empty():
    assert qst.detect_pnl_unit([]) == "decimal"
    assert qst.detect_pnl_unit([{"pnl_pct": None}]) == "decimal"


def test_returns_auto_detects_percent_units():
    """Auto-detect should recognize EQUITY-style integer-percent and scale by 1/100."""
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 3.0, "closed_at": "2026-04-01T00:00:00Z"},
        {"asset_class": "EQUITY", "pnl_pct": -1.0, "closed_at": "2026-04-02T00:00:00Z"},
        {"asset_class": "EQUITY", "pnl_pct": 5.0, "closed_at": "2026-04-03T00:00:00Z"},
    ]
    s = qst.picks_to_daily_returns(picks, asset_class="EQUITY")  # auto
    # Expect scaled to decimal: 0.03, -0.01, 0.05
    assert s.iloc[0] == pytest.approx(0.03)
    assert s.iloc[1] == pytest.approx(-0.01)
    assert s.iloc[2] == pytest.approx(0.05)


def test_returns_explicit_percent_unit():
    pytest.importorskip("pandas")
    picks = [
        {"asset_class": "FOREX", "pnl_pct": 2.5, "closed_at": "2026-04-01T00:00:00Z"},
    ]
    s = qst.picks_to_daily_returns(picks, asset_class="FOREX", pnl_unit="percent")
    assert s.iloc[0] == pytest.approx(0.025)


def test_returns_invalid_pnl_unit_raises():
    pytest.importorskip("pandas")
    with pytest.raises(ValueError, match="pnl_unit must be"):
        qst.picks_to_daily_returns(
            [{"asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T00:00:00Z"}],
            asset_class="EQUITY",
            pnl_unit="ratio",
        )


def test_returns_empty_input():
    pd = pytest.importorskip("pandas")
    s = qst.picks_to_daily_returns([], asset_class="EQUITY")
    assert isinstance(s, pd.Series)
    assert s.empty


# ---------------------------------------------------------------------------
# write_tearsheet: stubbed so we don't need quantstats present
# ---------------------------------------------------------------------------


def test_write_tearsheet_empty_returns_writes_placeholder(tmp_path, monkeypatch):
    pd = pytest.importorskip("pandas")
    out = tmp_path / "empty.html"
    qst.write_tearsheet(pd.Series(dtype=float), out, title="EMPTY")
    assert out.exists()
    txt = out.read_text(encoding="utf-8")
    assert "EMPTY" in txt
    assert "No returns data" in txt


def test_write_tearsheet_invokes_quantstats(tmp_path, monkeypatch):
    pd = pytest.importorskip("pandas")
    # Stub the quantstats module so the test runs even without it installed.
    captured = {}

    def fake_html(returns, benchmark=None, title=None, output=None):
        captured["title"] = title
        captured["output"] = output
        # write a stub file so the caller's existence check passes
        Path(output).write_text(f"<html>{title}</html>", encoding="utf-8")

    fake_qs = types.SimpleNamespace(reports=types.SimpleNamespace(html=fake_html))
    monkeypatch.setattr(qst, "_QS", fake_qs)

    s = pd.Series([0.01, -0.02, 0.005], index=pd.to_datetime(["2026-04-01", "2026-04-02", "2026-04-03"]))
    out = tmp_path / "tear.html"
    qst.write_tearsheet(s, out, title="TEST")
    assert out.exists()
    assert captured["title"] == "TEST"


def test_write_all_tearsheets_per_class(tmp_path, monkeypatch):
    pytest.importorskip("pandas")
    # Set up a fake dashboard_data.json with two classes
    data = tmp_path / "dashboard_data.json"
    _write_json(
        data,
        {
            "picks": {
                "recent_closed": [
                    {"asset_class": "EQUITY", "pnl_pct": 0.01, "closed_at": "2026-04-01T00:00:00Z"},
                    {"asset_class": "EQUITY", "pnl_pct": 0.02, "closed_at": "2026-04-02T00:00:00Z"},
                    {"asset_class": "CRYPTO", "pnl_pct": -0.05, "closed_at": "2026-04-01T00:00:00Z"},
                    {"asset_class": "CRYPTO", "pnl_pct": 0.03, "closed_at": "2026-04-02T00:00:00Z"},
                ]
            }
        },
    )

    # Stub QuantStats render
    def fake_html(returns, benchmark=None, title=None, output=None):
        Path(output).write_text(f"<html>{title}</html>", encoding="utf-8")

    monkeypatch.setattr(
        qst, "_QS", types.SimpleNamespace(reports=types.SimpleNamespace(html=fake_html))
    )

    out_dir = tmp_path / "tears"
    written = qst.write_all_tearsheets(data, out_dir)
    # Expect EQUITY, CRYPTO, ALL
    assert "EQUITY" in written
    assert "CRYPTO" in written
    assert "ALL" in written
    for path in written.values():
        assert path.exists()

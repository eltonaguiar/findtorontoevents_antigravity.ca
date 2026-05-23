"""Tests for audit_trail/cross_asset_correlation.py (B15)."""
from __future__ import annotations

import importlib
import json
import math
from datetime import datetime, timezone

import pytest

_numpy_available = importlib.util.find_spec("numpy") is not None
_requires_numpy = pytest.mark.skipif(not _numpy_available, reason="numpy not installed")

from audit_trail.cross_asset_correlation import (
    pearson_correlation,
    build_daily_pnl_series,
    compute_pair_correlation,
    build_correlation_report,
    HIGH_CORR_THRESHOLD,
    _MONITORED_CLASSES,
)


_NOW = datetime(2026, 4, 28, tzinfo=timezone.utc)


def _write(tmp_path, name, payload):
    fp = tmp_path / name
    fp.write_text(json.dumps(payload), encoding="utf-8")
    return fp


def _make_pick(asset_class, pnl_pct, days_ago=1, direction="BUY"):
    from datetime import timedelta
    dt = _NOW - timedelta(days=days_ago)
    return {
        "asset_class": asset_class,
        "pnl_pct": pnl_pct,
        "closed_at": dt.isoformat(),
        "signal_type": direction,
    }


# ---------------------------------------------------------------------------
# pearson_correlation
# ---------------------------------------------------------------------------


def test_pearson_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert pearson_correlation(xs, xs) == 1.0


def test_pearson_perfect_negative():
    xs = [1.0, 2.0, 3.0]
    ys = [3.0, 2.0, 1.0]
    assert pearson_correlation(xs, ys) == -1.0


def test_pearson_uncorrelated():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [5.0, 3.0, 1.0, 3.0, 5.0]  # parabola — zero linear correlation
    r = pearson_correlation(xs, ys)
    assert r is not None
    assert abs(r) < 0.3


def test_pearson_too_short_returns_none():
    assert pearson_correlation([1.0], [1.0]) is None


def test_pearson_mismatched_length_returns_none():
    assert pearson_correlation([1.0, 2.0], [1.0]) is None


def test_pearson_constant_xs_returns_none():
    assert pearson_correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


# ---------------------------------------------------------------------------
# build_daily_pnl_series
# ---------------------------------------------------------------------------


def test_series_groups_by_asset_class():
    picks = [
        _make_pick("CRYPTO", 0.05, days_ago=1),
        _make_pick("CRYPTO", 0.03, days_ago=2),
        _make_pick("EQUITY", 0.01, days_ago=1),
    ]
    series = build_daily_pnl_series(picks, window_days=30, now=_NOW)
    assert "CRYPTO" in series
    assert "EQUITY" in series


def test_series_excludes_unknown_class():
    picks = [_make_pick("UNKNOWN_CLASS", 0.05, days_ago=1)]
    series = build_daily_pnl_series(picks, window_days=30, now=_NOW)
    assert "UNKNOWN_CLASS" not in series


def test_series_excludes_old_picks():
    picks = [_make_pick("CRYPTO", 0.05, days_ago=45)]
    series = build_daily_pnl_series(picks, window_days=30, now=_NOW)
    assert series.get("CRYPTO", {}) == {}


def test_series_excludes_missing_pnl():
    pick = {"asset_class": "CRYPTO", "closed_at": _NOW.isoformat()}  # no pnl_pct
    series = build_daily_pnl_series([pick], window_days=30, now=_NOW)
    assert series.get("CRYPTO", {}) == {}


def test_series_averages_same_day():
    dt = _NOW
    picks = [
        {"asset_class": "EQUITY", "pnl_pct": 0.10, "closed_at": dt.isoformat()},
        {"asset_class": "EQUITY", "pnl_pct": 0.20, "closed_at": dt.isoformat()},
    ]
    series = build_daily_pnl_series(picks, window_days=30, now=_NOW)
    date_str = dt.strftime("%Y-%m-%d")
    avg = series["EQUITY"][date_str]
    assert abs(avg - 0.15) < 1e-9


# ---------------------------------------------------------------------------
# compute_pair_correlation
# ---------------------------------------------------------------------------


def test_pair_corr_insufficient_data():
    a = {"2026-04-20": 0.01}
    b = {"2026-04-20": 0.02}
    result = compute_pair_correlation(a, b)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["r"] is None


def test_pair_corr_no_overlap():
    a = {"2026-04-20": 0.01, "2026-04-21": 0.02, "2026-04-22": 0.01,
         "2026-04-23": 0.03, "2026-04-24": 0.02}
    b = {"2026-04-10": 0.01, "2026-04-11": 0.02, "2026-04-12": 0.01,
         "2026-04-13": 0.03, "2026-04-14": 0.02}
    result = compute_pair_correlation(a, b)
    assert result["status"] == "INSUFFICIENT_DATA"


def test_pair_corr_returns_r():
    dates = [f"2026-04-{d:02d}" for d in range(1, 16)]
    vals = list(range(15))
    a = dict(zip(dates, vals))
    b = dict(zip(dates, vals))
    result = compute_pair_correlation(a, b)
    assert result["status"] == "OK"
    assert result["r"] == 1.0


# ---------------------------------------------------------------------------
# build_correlation_report
# ---------------------------------------------------------------------------


def test_report_empty_picks(tmp_path):
    fp = _write(tmp_path, "picks.json", {"picks": {"recent_closed": []}})
    out = build_correlation_report(fp, window_days=30, now=_NOW)
    assert out["n_picks_loaded"] == 0
    assert out["pairs"] == []
    assert out["flags"] == []
    assert out["alert"] is False


def test_report_single_class_no_pairs(tmp_path):
    picks = [_make_pick("CRYPTO", 0.05, days_ago=i) for i in range(1, 10)]
    fp = _write(tmp_path, "picks.json", picks)
    out = build_correlation_report(fp, window_days=30, now=_NOW)
    assert out["pairs"] == []


def test_report_two_classes_compute_pair(tmp_path):
    picks = (
        [_make_pick("CRYPTO", 0.05, days_ago=i) for i in range(1, 10)]
        + [_make_pick("EQUITY", 0.03, days_ago=i) for i in range(1, 10)]
    )
    fp = _write(tmp_path, "picks.json", picks)
    out = build_correlation_report(fp, window_days=30, now=_NOW)
    assert len(out["pairs"]) == 1


def test_report_high_correlation_flagged(tmp_path):
    # Both classes have same daily pnl → r=1.0
    from datetime import timedelta
    picks = []
    for i in range(1, 16):
        picks.append(_make_pick("CRYPTO", 0.05 * i, days_ago=i))
        picks.append(_make_pick("EQUITY", 0.05 * i, days_ago=i))
    fp = _write(tmp_path, "picks.json", picks)
    out = build_correlation_report(fp, window_days=30, now=_NOW)
    corr_pair = next((p for p in out["pairs"]
                      if set([p["class_a"], p["class_b"]]) == {"CRYPTO", "EQUITY"}), None)
    assert corr_pair is not None
    if corr_pair["r"] is not None:
        assert corr_pair["high_correlation"] == (abs(corr_pair["r"]) >= HIGH_CORR_THRESHOLD)


def test_report_writes_output_file(tmp_path):
    fp = _write(tmp_path, "picks.json", [])
    out_path = tmp_path / "out.json"
    build_correlation_report(fp, window_days=30, now=_NOW, out_path=out_path)
    assert out_path.exists()
    loaded = json.loads(out_path.read_text())
    for k in ("generated_at", "window_days", "n_picks_loaded", "pairs", "flags", "alert"):
        assert k in loaded


def test_report_dashboard_data_format(tmp_path):
    picks = [_make_pick("CRYPTO", 0.05, days_ago=2)]
    payload = {"picks": {"recent_closed": picks, "active": []}}
    fp = _write(tmp_path, "dash.json", payload)
    out = build_correlation_report(fp, window_days=30, now=_NOW)
    assert out["n_picks_loaded"] == 1


# ===========================================================================
# T2.2/B7: _compute_cross_asset_correlation — dashboard payload integration.
# Lives in audit_trail/dashboard_generator.py (separate from B15 sidecar).
# ===========================================================================

from datetime import timedelta

from audit_trail.dashboard_generator import _compute_cross_asset_correlation


def _live_pick(asset_class: str, days_ago: int, pnl_pct: float, pid: str = "x") -> dict:
    """Build a pick anchored to NOW (the dashboard helper uses datetime.now)."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "asset_class": asset_class,
        "closed_at": ts,
        "pnl_pct": pnl_pct,
        "id": pid,
        "symbol": "TEST",
    }


class TestDashboardCorrelationEmpty:
    def test_empty_picks_returns_empty_matrix(self):
        result = _compute_cross_asset_correlation([])
        assert result["matrix"] == {}
        assert result["asset_classes"] == []
        assert result["n_days"] == 0
        assert result["lookback_days"] == 30
        assert "generated_at" in result

    def test_picks_outside_lookback_window_excluded(self):
        picks = [_live_pick("CRYPTO", 60, 1.0, f"c{i}") for i in range(5)]
        result = _compute_cross_asset_correlation(picks, lookback_days=30)
        assert result["matrix"] == {}
        assert result["n_days"] == 0


class TestDashboardCorrelationSingleClass:
    def test_single_asset_class_returns_identity_1x1(self):
        picks = [_live_pick("CRYPTO", i, 1.0 + i * 0.1, f"c{i}") for i in range(5)]
        result = _compute_cross_asset_correlation(picks, lookback_days=30)
        assert result["asset_classes"] == ["CRYPTO"]
        assert result["matrix"] == {"CRYPTO": {"CRYPTO": 1.0}}
        assert result["n_days"] == 5

    def test_single_class_diagonal_is_one(self):
        picks = [_live_pick("EQUITY", i, float(i + 1), f"e{i}") for i in range(3)]
        result = _compute_cross_asset_correlation(picks)
        assert result["matrix"]["EQUITY"]["EQUITY"] == 1.0


@_requires_numpy
class TestDashboardCorrelationPerfectlyCorrelated:
    def test_two_classes_perfectly_correlated_rho_near_one(self):
        picks = []
        for i in range(7):
            pnl = float(i + 1)
            picks.append(_live_pick("CRYPTO", i, pnl, f"c{i}"))
            picks.append(_live_pick("EQUITY", i, pnl, f"e{i}"))
        result = _compute_cross_asset_correlation(picks, lookback_days=30)
        assert set(result["asset_classes"]) == {"CRYPTO", "EQUITY"}
        rho = result["matrix"]["CRYPTO"]["EQUITY"]
        assert rho is not None
        assert rho == pytest.approx(1.0, abs=1e-3)
        assert result["matrix"]["EQUITY"]["CRYPTO"] == pytest.approx(1.0, abs=1e-3)
        assert result["matrix"]["CRYPTO"]["CRYPTO"] == 1.0
        assert result["matrix"]["EQUITY"]["EQUITY"] == 1.0


@_requires_numpy
class TestDashboardCorrelationPerfectlyAntiCorrelated:
    def test_two_classes_perfectly_anti_correlated_rho_near_neg_one(self):
        picks = []
        for i in range(7):
            picks.append(_live_pick("CRYPTO", i, float(i + 1), f"c{i}"))
            picks.append(_live_pick("EQUITY", i, -float(i + 1), f"e{i}"))
        result = _compute_cross_asset_correlation(picks, lookback_days=30)
        rho = result["matrix"]["CRYPTO"]["EQUITY"]
        assert rho is not None
        assert rho == pytest.approx(-1.0, abs=1e-3)


class TestDashboardCorrelationLookbackWindow:
    def test_different_lookbacks_produce_different_n_days(self):
        picks = [_live_pick("CRYPTO", i, float(i + 1), f"c{i}") for i in range(20)]
        result_7d = _compute_cross_asset_correlation(picks, lookback_days=7)
        result_30d = _compute_cross_asset_correlation(picks, lookback_days=30)
        assert result_7d["n_days"] < result_30d["n_days"]
        assert result_7d["n_days"] <= 8
        assert result_30d["n_days"] == 20
        assert result_7d["lookback_days"] == 7
        assert result_30d["lookback_days"] == 30


class TestDashboardCorrelationPayloadShape:
    def test_payload_has_required_keys(self):
        picks = [_live_pick("CRYPTO", i, 1.0, f"c{i}") for i in range(3)]
        result = _compute_cross_asset_correlation(picks)
        for key in ("matrix", "n_days", "asset_classes", "lookback_days", "generated_at"):
            assert key in result, f"missing key: {key}"

    def test_unknown_asset_class_excluded(self):
        picks = [
            _live_pick("UNKNOWN", 1, 1.0, "u1"),
            _live_pick("", 2, 2.0, "u2"),
            _live_pick("CRYPTO", 3, 3.0, "c1"),
        ]
        result = _compute_cross_asset_correlation(picks)
        assert "UNKNOWN" not in result["asset_classes"]
        assert "" not in result["asset_classes"]

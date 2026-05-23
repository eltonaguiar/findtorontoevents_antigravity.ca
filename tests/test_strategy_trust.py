"""Unit tests for tools.adaptive.strategy_trust (stdlib only)."""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.adaptive import strategy_trust as st  # noqa: E402


NOW = datetime(2026, 4, 13, 23, 0, 0, tzinfo=timezone.utc).timestamp()
DAY = 86400.0


def _make_trades(offsets_hours: list[float], pnls: list[float]) -> list[tuple[float, float]]:
    assert len(offsets_hours) == len(pnls)
    return [(NOW - h * 3600.0, p) for h, p in zip(offsets_hours, pnls)]


# --------------------------------------------------------------------------- #
# Wilson CI
# --------------------------------------------------------------------------- #
def test_wilson_ci_zero_n():
    lo, hi = st.wilson_ci_95(0, 0)
    assert (lo, hi) == (0.0, 0.0)


def test_wilson_ci_all_wins():
    lo, hi = st.wilson_ci_95(10, 10)
    assert lo < 1.0
    assert hi <= 1.0 + 1e-9
    assert lo > 0.6  # wide but below 1


def test_wilson_ci_all_losses():
    lo, hi = st.wilson_ci_95(0, 10)
    assert lo >= 0.0
    assert hi < 0.4


def test_wilson_ci_symmetric_midpoint():
    lo, hi = st.wilson_ci_95(50, 100)
    assert 0.40 < lo < 0.50
    assert 0.50 < hi < 0.60
    assert abs((lo + hi) / 2 - 0.5) < 0.02


# --------------------------------------------------------------------------- #
# EWM math
# --------------------------------------------------------------------------- #
def test_ewm_weight_monotonic_decay():
    w_recent = st._ewm_weight(NOW, NOW - 1 * DAY, 23.0)
    w_old = st._ewm_weight(NOW, NOW - 46 * DAY, 23.0)
    assert w_recent > w_old
    # 46d ≈ 2 half-lives → roughly 1/4
    assert 0.20 < w_old < 0.30


def test_ewm_weight_half_life_exact():
    w = st._ewm_weight(NOW, NOW - 23 * DAY, 23.0)
    assert abs(w - 0.5) < 1e-9


def test_ewm_profit_factor_weights_recent_more():
    # Recent losses, old wins — EWM PF should be much lower than raw PF.
    trades = [
        (NOW - 60 * DAY, +5.0),
        (NOW - 60 * DAY, +5.0),
        (NOW - 1 * DAY, -5.0),
        (NOW - 1 * DAY, -5.0),
    ]
    raw_pf = st._profit_factor([t[1] for t in trades])
    assert abs(raw_pf - 1.0) < 1e-9
    ewm_pf = st.ewm_profit_factor(trades, NOW, half_life_days=23.0)
    assert ewm_pf is not None
    assert ewm_pf < 0.5  # recent losses dominate


def test_ewm_profit_factor_all_wins_infinite():
    trades = [(NOW - i * DAY, 1.0) for i in range(5)]
    pf = st.ewm_profit_factor(trades, NOW)
    assert pf == float("inf")


def test_ewm_profit_factor_empty():
    assert st.ewm_profit_factor([], NOW) is None


def test_ewm_win_rate_recent_emphasis():
    trades = [
        (NOW - 60 * DAY, +1.0),  # old win
        (NOW - 60 * DAY, +1.0),  # old win
        (NOW - 1 * DAY, -1.0),   # recent loss
        (NOW - 1 * DAY, -1.0),   # recent loss
    ]
    wr = st.ewm_win_rate(trades, NOW)
    assert wr is not None
    assert wr < 0.5  # recent losses weighted more heavily


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def _base_metrics(**overrides):
    metrics = {
        "n": 50,
        "last_48h": {"n": 6, "pf": 1.0, "wr": 0.5},
        "last_7d": {"n": 20, "pf": 1.0, "wr": 0.5},
    }
    metrics.update(overrides)
    return metrics


def test_classify_hot_hand():
    m = _base_metrics(last_48h={"n": 6, "pf": 3.0, "wr": 0.7},
                      last_7d={"n": 20, "pf": 1.0, "wr": 0.5})
    assert st.classify(m) == "HOT"


def test_classify_cold_hand():
    m = _base_metrics(last_48h={"n": 6, "pf": 0.4, "wr": 0.3},
                      last_7d={"n": 20, "pf": 1.5, "wr": 0.55})
    assert st.classify(m) == "COLD"


def test_classify_stable():
    m = _base_metrics(last_48h={"n": 6, "pf": 1.1, "wr": 0.52},
                      last_7d={"n": 20, "pf": 1.0, "wr": 0.5})
    assert st.classify(m) == "STABLE"


def test_classify_insufficient_n():
    m = _base_metrics(n=5, last_48h={"n": 5, "pf": 3.0, "wr": 0.7})
    assert st.classify(m) == "INSUFFICIENT"


def test_classify_insufficient_recent():
    # n >= 20 but only 2 trades in last 48h → INSUFFICIENT regardless of PF.
    m = _base_metrics(n=50, last_48h={"n": 2, "pf": 10.0, "wr": 1.0})
    assert st.classify(m) == "INSUFFICIENT"


def test_classify_hot_requires_five_recent():
    # 4 recent trades with PF ratio that would otherwise qualify → STABLE, not HOT.
    m = _base_metrics(n=50, last_48h={"n": 4, "pf": 5.0, "wr": 0.8})
    # 4 recent < MIN_RECENT_48H=3? No: 4 >= 3 so not INSUFFICIENT,
    # but 4 < HOT_COLD_MIN_N=5 so cannot be HOT → STABLE.
    assert st.classify(m) == "STABLE"


def test_classify_hot_with_infinite_pf():
    m = _base_metrics(last_48h={"n": 6, "pf": float("inf"), "wr": 1.0},
                      last_7d={"n": 20, "pf": 1.5, "wr": 0.55})
    assert st.classify(m) == "HOT"


# --------------------------------------------------------------------------- #
# End-to-end via synthetic fixtures
# --------------------------------------------------------------------------- #
def test_build_report_hot_cold_stable_mix():
    bucket = {
        # HOT: n=30, 6 recent big wins, 7d baseline is break-even.
        "hot_strat": (
            _make_trades([1, 2, 3, 4, 5, 6], [5, 5, 5, 5, 5, 5])
            + _make_trades([72 + i for i in range(24)], [+1 if i % 2 else -1 for i in range(24)])
        ),
        # COLD: n=30, 6 recent big losses, 7d has wins.
        "cold_strat": (
            _make_trades([1, 2, 3, 4, 5, 6], [-5, -5, -5, -5, -5, -5])
            + _make_trades([30, 40, 50, 60, 70, 80], [+2, +2, +2, +2, +2, +2])
            + _make_trades([100 + i for i in range(18)], [+0.5 if i % 3 else -0.2 for i in range(18)])
        ),
        # STABLE: n=25, recent 48h 5 trades mild profit, 7d similar.
        "stable_strat": (
            _make_trades(
                [i + 1 for i in range(25)],
                [0.8 if i % 2 == 0 else -0.6 for i in range(25)],
            )
        ),
        # INSUFFICIENT: n < 20.
        "tiny_strat": _make_trades([1, 2, 3], [1, -1, 0.5]),
    }
    report = st.build_report(bucket, NOW)
    assert report["total_strategies"] == 4
    classes = {r["strategy"]: r["classification"]
               for r in report["hot_hand"] + report["cold_hand"]
               + report["stable"] + report["insufficient"]}
    assert classes["hot_strat"] == "HOT"
    assert classes["cold_strat"] == "COLD"
    assert classes["stable_strat"] in ("STABLE", "HOT", "COLD")
    # stable_strat has 48h_n small; ensure it is eligible (n>=20)
    stable_entry = next(r for r in report["hot_hand"] + report["cold_hand"] + report["stable"]
                        if r["strategy"] == "stable_strat")
    assert stable_entry["n"] == 25
    # tiny_strat must land in INSUFFICIENT
    assert any(r["strategy"] == "tiny_strat" for r in report["insufficient"])


def test_build_report_sorted_descending_stable():
    # Two stable strategies — verify stable list is sorted by ewm_pf descending.
    bucket = {
        "lo_pf": _make_trades(
            [i + 1 for i in range(25)],
            [0.2 if i % 2 == 0 else -1.5 for i in range(25)],
        ),
        "hi_pf": _make_trades(
            [i + 1 for i in range(25)],
            [1.5 if i % 2 == 0 else -0.2 for i in range(25)],
        ),
    }
    report = st.build_report(bucket, NOW)
    stable = report["stable"]
    if len(stable) >= 2:
        pfs = [s["ewm_pf_23d"] for s in stable]
        # Coerce inf sort key consistently
        def _k(v):
            if v is None:
                return -1.0
            if isinstance(v, float) and math.isinf(v):
                return 1e18
            return float(v)
        assert all(_k(pfs[i]) >= _k(pfs[i + 1]) for i in range(len(pfs) - 1))


def test_sanitize_infinity():
    out = st._sanitize({"pf": float("inf"), "neg": float("-inf"), "nan": float("nan"), "ok": 1.2})
    assert out["pf"] == "Infinity"
    assert out["neg"] == "-Infinity"
    assert out["nan"] is None
    assert out["ok"] == 1.2

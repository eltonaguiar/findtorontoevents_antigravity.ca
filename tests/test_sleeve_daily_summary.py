import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import sleeve_daily_summary as SUM  # noqa: E402


def _state(eqs, sid="s"):
    hist = [{"date": f"2026-01-{i+1:02d}", "equity": e} for i, e in enumerate(eqs)]
    return {"sleeves": {sid: {"history": hist}}}


def _daily(**kw):
    row = {"id": "s", "equity": 100.0, "return_pct": 0.0, "drawdown_pct": 0.0}
    row.update(kw)
    return {"as_of": "2026-01-31", "sleeves": [row]}


def test_returns_are_percent_changes():
    r = SUM._returns([{"equity": 100}, {"equity": 110}, {"equity": 99}])
    assert abs(r[0] - 10.0) < 1e-9 and abs(r[1] + 10.0) < 1e-9


def test_mean_ci_is_none_below_two_points():
    assert SUM._mean_ci([1.0]) == (None, None)
    mean, ci = SUM._mean_ci([1.0, 3.0])
    assert mean == 2.0 and ci[0] < 2.0 < ci[1]


def test_tiers_collecting_then_observing():
    s = SUM.summarise(_state([100.0] * 10), _daily())
    assert s["sleeves"][0]["status"] == "collecting"
    s = SUM.summarise(_state([100.0 + i for i in range(40)]), _daily())
    assert s["sleeves"][0]["status"] in ("observing", "observing_no_edge")


def test_eligible_requires_positive_ci_at_n_100():
    eqs = [100.0 * (1.01 ** i) for i in range(120)]      # steady +1%/day
    s = SUM.summarise(_state(eqs), _daily())
    assert s["sleeves"][0]["n_marks"] == 120
    assert s["sleeves"][0]["status"] == "eligible_for_review"
    flat = [100.0] * 120
    s2 = SUM.summarise(_state(flat), _daily())
    assert s2["sleeves"][0]["status"] == "observing_no_edge"


def test_render_names_every_sleeve_and_status():
    s = SUM.summarise(_state([100.0]), _daily())
    out = SUM.render(s)
    assert "s" in out and "collecting" in out

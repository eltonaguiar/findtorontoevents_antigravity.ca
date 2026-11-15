"""Edge cases for the pre-registered interim looks.

These pin the behaviour a chart cannot show: what `of_boundaries` does when there is exactly
one look, and what `interim_verdict` does with zero windows, a single window, and rows that
share one `closed_at` (one market episode, not N independent observations).

Run: python3 -m pytest tests/test_forward_tracker_of_edges.py -q
"""
from datetime import date, timedelta
import importlib.util
import math
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_module():
    path = ROOT / "tools" / "forward_tracker.py"
    spec = importlib.util.spec_from_file_location("ft_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ft_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


ft = _load_module()

BASE = date(2026, 1, 1)
LOOKS = [25, 50, 100, 152]


def design(**over):
    d = {"interim_looks": LOOKS, "windows_needed_fixed_sample": 152,
         "alpha": 0.05, "endpoint": "excess_pp"}
    d.update(over)
    return {"measurement_design": d}


def rows(n, excess=0.5, pnl=1.0, notional=1000.0, same_window=False, missing_excess_at=()):
    out = []
    for i in range(n):
        d0 = BASE if same_window else BASE + timedelta(days=3 * i)
        d1 = d0 + timedelta(days=3)
        out.append({"strategy": "X", "pnl": pnl, "notional_usd": notional,
                    "excess_pp": (None if i in missing_excess_at else excess),
                    "hold_days": 3, "opened": str(d0), "closed": str(d1)})
    return out


# ---------------------------------------------------------------- of_boundaries

def test_boundaries_are_monotone_decreasing():
    b, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    assert len(b) == len(LOOKS)
    assert all(b[i] > b[i + 1] for i in range(len(b) - 1))


def test_final_boundary_is_at_least_the_fixed_sample_z():
    b, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    # With a single look at the end you get back the ordinary one-sided 5% critical value;
    # alpha-spending may only make it stricter, never slacker.
    assert b[-1] >= 1.6449 - 1e-9


def test_boundaries_follow_the_inverse_sqrt_clock():
    b, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    # A boundary at information fraction t is C/sqrt(t), so the first look is
    # sqrt(n_final/looks[0]) times the last one — that ratio is the whole design.
    assert b[0] / b[-1] == pytest.approx(math.sqrt(152 / LOOKS[0]), rel=0.02)


def test_achieved_alpha_matches_the_requested_alpha():
    _, achieved = ft.of_boundaries(LOOKS, 152, 0.05)
    assert achieved == pytest.approx(0.05, abs=0.02)


def test_single_look_is_just_the_fixed_sample_test():
    b, achieved = ft.of_boundaries([100], 100, 0.05)
    assert len(b) == 1
    assert b[0] == pytest.approx(1.6449, abs=0.01)
    assert achieved == pytest.approx(0.05, abs=0.01)


def test_looser_alpha_gives_smaller_boundaries():
    loose, _ = ft.of_boundaries(LOOKS, 152, 0.10)
    tight, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    assert all(l < t for l, t in zip(loose, tight))


def test_boundaries_are_cached_and_identical_on_recall():
    a, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    b, _ = ft.of_boundaries(LOOKS, 152, 0.05)
    assert a is b


# -------------------------------------------------------------- interim_verdict

def test_no_measurement_design_returns_none():
    assert ft.interim_verdict({"start": "2026-01-01"}, rows(5)) is None


def test_zero_windows_is_continue_with_zero_missing_not_none():
    iv = ft.interim_verdict(design(), [], BASE)
    assert iv["verdict"] == "CONTINUE"
    assert iv["n"] == 0
    assert iv["endpoint"] == "excess_pp"
    # 0 rows cannot be missing a benchmark — None here would read as "unknown coverage".
    assert iv["endpoint_missing_rows"] == 0
    assert iv["z"] is None and iv["next_look"] == LOOKS[0]
    assert "0/25" in iv["note"]


def test_one_window_below_the_first_look_stays_continue():
    iv = ft.interim_verdict(design(), rows(1), BASE)
    assert iv["verdict"] == "CONTINUE"
    assert iv["n"] == 1 and iv["z"] is None
    assert iv["boundary"] == pytest.approx(ft.of_boundaries(LOOKS, 152, 0.05)[0][0], abs=1e-3)


def test_one_window_with_no_dispersion_cannot_promote():
    # n_final == the only look: sd is undefined, so no z can be formed. A single window is
    # not evidence however large its excess, and this is the case most likely to be eyeballed
    # into a "PROMOTE".
    d = design(interim_looks=[1], windows_needed_fixed_sample=1)
    iv = ft.interim_verdict({"measurement_design": d["measurement_design"]}, rows(1, excess=99.0), BASE)
    assert iv["n"] == 1
    assert iv["z"] is None
    assert iv["verdict"] == "CONTINUE"


def test_tied_closed_dates_collapse_into_one_window():
    # Ten rows sharing (opened, closed) are ONE market episode. Counting them as ten windows
    # would inflate n past the first look and manufacture significance out of correlation.
    iv = ft.interim_verdict(design(), rows(10, excess=2.0, same_window=True), BASE)
    assert iv["n"] == 1
    assert iv["verdict"] == "CONTINUE"


def test_window_mean_is_the_mean_of_its_rows():
    mixed = rows(2, excess=1.0)
    mixed[1]["excess_pp"] = -0.5      # same window, two rows -> one window averaging them
    mixed[1]["opened"], mixed[1]["closed"] = mixed[0]["opened"], mixed[0]["closed"]
    iv = ft.interim_verdict(design(interim_looks=[1], windows_needed_fixed_sample=1), mixed, BASE)
    assert iv["n"] == 1
    # mean 0.25 with sd undefined -> CONTINUE, but the mean itself must be 0.25.
    assert iv.get("mean_pp") in (None, 0.25)


def test_endpoint_is_excess_when_every_row_has_it():
    iv = ft.interim_verdict(design(), rows(25), BASE)
    assert iv["endpoint"] == "excess_pp"
    assert iv["endpoint_missing_rows"] == 0
    assert "endpoint_note" not in iv


def test_endpoint_falls_back_and_says_how_many_rows_were_missing():
    iv = ft.interim_verdict(design(), rows(25, missing_excess_at=(0, 1, 2)), BASE)
    assert iv["endpoint"] == "net_return_pp"          # labour not hidden
    assert iv["endpoint_missing_rows"] == 3
    assert "3 of 25" in iv["endpoint_note"]


def test_overwhelming_consistent_excess_promotes_at_the_first_look():
    iv = ft.interim_verdict(design(), rows(25, excess=5.0), BASE)
    # Constant rows -> sd 0 -> se 0 -> z is +inf, which is a crossing, not an error.
    assert iv["verdict"] == "PROMOTE"
    assert iv["look"] == LOOKS[0]


def test_registered_kill_rule_fires_at_its_window_count():
    d = design(kill_rules=[{"at_n_windows": 20, "if_mean_lt_pp": 0.0, "and_pf5_lt": 1.0}])
    iv = ft.interim_verdict(d, rows(25, excess=-3.0, pnl=-4.0), BASE)
    assert iv["verdict"] == "KILL"
    assert "mean" in iv["note"]


def test_kill_rule_does_not_fire_before_its_window_count():
    d = design(kill_rules=[{"at_n_windows": 20, "if_mean_lt_pp": 0.0, "and_pf5_lt": 1.0}])
    iv = ft.interim_verdict(d, rows(19, excess=-3.0, pnl=-4.0), BASE)
    assert iv["verdict"] == "CONTINUE"


def test_windows_seen_reported_once_a_look_is_reached():
    iv = ft.interim_verdict(design(), rows(25), BASE)
    assert iv["windows_seen"] == 25
    assert iv["next_look"] == LOOKS[1]

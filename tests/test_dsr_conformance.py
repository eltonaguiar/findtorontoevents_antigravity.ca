#!/usr/bin/env python3
"""Tests for tools/dsr_conformance.py.

The harness exists to catch a specific class of defect: a function named
`deflated_sharpe` whose value does not depend on the number of trials. These tests
pin the harness's own logic with synthetic implementations so they cannot pass
merely because the real implementations happen to import.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import dsr_conformance as dc  # noqa: E402


def _impl(name, call, *, accepts=True, unit="probability"):
    return dc.Impl(name, f"synthetic/{name}.py", 1, lambda *a, **k: call(*a, **k),
                   accepts, call, unit)


def _battery():
    return (dc.Scenario("s", 40, 0.1, seed=1),)


TRIALS = (1, 121)


# ------------------------------------------------------------------ the battery
def test_battery_is_deterministic():
    first = dc.BATTERY[0].returns()
    second = dc.BATTERY[0].returns()
    assert first == second, "a scenario must return an identical series every run"


def test_battery_hits_its_target_sharpe():
    scenario = dc.BATTERY[0]
    sr = dc._per_period_sr(scenario.returns())
    assert sr == pytest.approx(scenario.target_sr, abs=5e-3)


def test_fat_tail_scenario_differs_from_normal():
    normal = dc.BATTERY[0].returns()
    fat = dc.BATTERY[3].returns()
    assert normal != fat


# ------------------------------------------------------------------- the verdicts
def test_deflating_implementation_is_recognised():
    impl = _impl("real", lambda r, sr, n_obs, N: 1.0 / (1.0 + N))
    report = dc.run([impl], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "DEFLATES"


def test_trial_blind_implementation_is_flagged():
    """The defect this harness exists for: identical value at N=1 and N=4987."""
    impl = _impl("blind", lambda r, sr, n_obs, N: 0.97)
    report = dc.run([impl], _battery(), TRIALS)
    verdict = report["verdicts"][0]
    assert verdict["verdict"] == "IGNORES_N"
    assert verdict["moved_scenarios"] == "0/1"


def test_signature_without_trial_count_is_flagged_even_if_value_moves():
    """accepts_n_trials=False is a structural defect, not an empirical one."""
    impl = _impl("no_trials_arg", lambda r, sr, n_obs, N: 0.5, accepts=False)
    report = dc.run([impl], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "IGNORES_N"
    assert "takes no trial count" in report["verdicts"][0]["detail"]


def test_none_at_one_trial_is_judged_on_the_pairs_it_did_answer():
    """audit3_tribunal returns None at N=1 by design (no correction is possible).
    That must not be scored as trial-blindness."""
    impl = _impl("declines_n1", lambda r, sr, n_obs, N: None if N < 2 else 1.0 / (1.0 + N))
    report = dc.run([impl], _battery(), (1, 26, 121))
    verdict = report["verdicts"][0]
    assert verdict["verdict"] == "DEFLATES"
    assert verdict["moved_scenarios"] == "1/1"


def test_single_usable_trial_count_is_unjudgeable_not_guilty():
    """One answer cannot show sensitivity; saying IGNORES_N there would be a false accusation."""
    impl = _impl("one_answer", lambda r, sr, n_obs, N: None if N < 2 else 0.5)
    report = dc.run([impl], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "UNJUDGEABLE"


def test_zscore_outside_unit_interval_is_called_out():
    impl = _impl("z", lambda r, sr, n_obs, N: 3.2 - N * 0.01)
    report = dc.run([impl], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "DEFLATES_UNIT_AMBIGUOUS"


def test_raising_implementation_is_a_finding_not_a_crash():
    def boom(r, sr, n_obs, N):
        raise ZeroDivisionError("degenerate")

    report = dc.run([_impl("boom", boom)], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "NEVER_RETURNS"
    assert all(c["status"] == "RAISED" for c in report["cells"])
    assert "ZeroDivisionError" in report["cells"][0]["error"]


def test_unimportable_implementation_is_reported():
    impl = dc.Impl("gone", "nope/missing.py", 9, None, True,
                   lambda *a: None, "UNIMPORTABLE: ModuleNotFoundError")
    report = dc.run([impl], _battery(), TRIALS)
    assert report["verdicts"][0]["verdict"] == "UNIMPORTABLE"


# ------------------------------------------------------------- the real registry
def test_real_registry_drives_several_implementations():
    registry = dc.build_registry()
    drivable = [i for i in registry if not i.unit.startswith("UNIMPORTABLE")]
    assert len(drivable) >= 4, [i.name for i in registry]
    report = dc.run(registry, (dc.BATTERY[0],), (1, 121))
    assert len(report["cells"]) == len(registry) * 2
    allowed = {"DEFLATES", "IGNORES_N", "DEFLATES_UNIT_AMBIGUOUS", "UNJUDGEABLE",
               "NEVER_RETURNS", "UNIMPORTABLE"}
    assert {v["verdict"] for v in report["verdicts"]} <= allowed


def test_canonical_pointer_takes_no_trial_count():
    """alpha_engine/deflated_sharpe.py:179 deprecates itself in favour of
    alpha_engine/validation/sharpe_metrics.py:83, whose signature has no trial
    count. If that changes, this test should change with it - deliberately."""
    registry = {i.name: i for i in dc.build_registry()}
    canonical = registry["validation.sharpe_metrics_CANONICAL"]
    assert canonical.accepts_n_trials is False
    assert canonical.line == 83


def test_markdown_renders_every_verdict():
    report = dc.run([_impl("a", lambda r, sr, n_obs, N: 1.0 / (1.0 + N))],
                    _battery(), TRIALS)
    md = dc.to_markdown(report)
    assert "| implementation | file:line | verdict |" in md
    assert "DEFLATES" in md
    assert "Verdict key" in md


def test_json_round_trip(tmp_path):
    report = dc.run([_impl("a", lambda r, sr, n_obs, N: 0.5)], _battery(), TRIALS)
    import json

    out = tmp_path / "r.json"
    out.write_text(json.dumps(report))
    assert json.loads(out.read_text())["schema"] == dc.SCHEMA

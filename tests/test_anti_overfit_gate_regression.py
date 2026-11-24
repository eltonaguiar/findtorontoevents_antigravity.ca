"""The anti-overfit gate fails on regression, not on the standing 6/80.

Before 2026-11-21 the CI step failed whenever any strategy sat below DSR 0.95.
74 of 80 always do, so every hourly run was red and the colour carried no
information (see updates/2026-11-20-anti-overfit-dsr-gate-never-passes.md).
These tests pin the replacement contract: the absolute number is always logged,
and the job only goes red when the previous audit was better.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _sidecar():
    pytest.importorskip("pymysql")
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location(
        "aos", ROOT / "tools" / "anti_overfit_audit_sidecar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _labels():
    spec = importlib.util.spec_from_file_location(
        "adpl", ROOT / "tools" / "apply_dsr_probation_labels.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cur(pass_count, scored, prev=None):
    payload = {"strategies": [], "dsr_pass_count": pass_count,
               "dsr_scored_count": scored,
               "dsr_pass_rate": round(pass_count / scored, 4) if scored else None}
    if prev is not None:
        payload["dsr_prev_audit"] = {"pass_count": prev[0], "scored_count": prev[1],
                                     "generated_at": "2026-11-20T21:46:53Z"}
    return payload


def test_standing_state_is_not_a_failure():
    reasons, note = _sidecar().regression_reasons(_cur(6, 80, prev=(6, 80)))
    assert reasons == []
    assert "previous audit 6/80" in note


def test_one_strategy_slipping_across_the_line_is_a_regression():
    reasons, _ = _sidecar().regression_reasons(_cur(5, 80, prev=(6, 80)))
    assert reasons and "-1.2pp" in reasons[0]
    assert "7.5%" in reasons[0] and "6.2%" in reasons[0]


def test_a_drop_inside_the_tolerance_is_noise():
    assert _sidecar().regression_reasons(_cur(795, 1000, prev=(800, 1000)))[0] == []


def test_an_improvement_is_not_a_regression():
    assert _sidecar().regression_reasons(_cur(8, 80, prev=(6, 80)))[0] == []


def test_a_collapsing_scored_population_is_a_regression_at_a_flat_rate():
    reasons, _ = _sidecar().regression_reasons(_cur(3, 40, prev=(6, 80)))
    assert any("shrank" in r for r in reasons), reasons


def test_a_payload_without_pass_counts_cannot_pass():
    reasons, note = _sidecar().regression_reasons({"strategies": [
        {"strategy": "x", "n": 50, "dsr": None}]})
    assert reasons and "no usable pass counts" in reasons[0]
    assert note == "no baseline"


def test_a_first_run_without_a_baseline_is_not_a_failure():
    reasons, note = _sidecar().regression_reasons(_cur(6, 80))
    assert reasons == [] and "no previous audit" in note


def test_the_absolute_number_is_always_in_the_line():
    state = _sidecar().absolute_state(_cur(6, 80))
    assert "6/80" in state and "7.5%" in state and "74 below" in state


def test_read_previous_audit_reads_the_baseline_and_survives_garbage(tmp_path):
    mod = _sidecar()
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"dsr_pass_count": 6, "dsr_scored_count": 80,
                                "dsr_pass_rate": 0.075, "generated_at": "t"}))
    assert mod.read_previous_audit(good)["pass_count"] == 6
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert mod.read_previous_audit(bad) == {}
    assert mod.read_previous_audit(tmp_path / "missing.json") == {}


def test_the_prev_block_survives_the_post_merge_label_restamp():
    payload = {"strategies": [{"strategy": "a", "n": 50, "dsr": 0.97}],
               "dsr_prev_audit": {"pass_count": 6, "scored_count": 80}}
    out = _labels().apply_labels(payload)
    assert out["dsr_prev_audit"] == {"pass_count": 6, "scored_count": 80}


def _run(payload, tmp_path, gate=True):
    f = tmp_path / "payload.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    args = [sys.executable, str(ROOT / "tools" / "anti_overfit_audit_sidecar.py"),
            "--check-only", "--in", str(f)]
    if gate:
        args.append("--gate")
    return subprocess.run(args, capture_output=True, text=True, timeout=180)


def test_cli_fails_on_regression_and_still_prints_the_absolute_number(tmp_path):
    r = _run(_cur(5, 80, prev=(6, 80)), tmp_path)
    assert r.returncode == 2, r.stderr
    assert "regression" in r.stderr
    assert "5/80" in r.stderr and "75 below" in r.stderr


def test_cli_passes_on_the_standing_state(tmp_path):
    r = _run(_cur(6, 80, prev=(6, 80)), tmp_path)
    assert r.returncode == 0, r.stderr
    assert "PASS" in r.stderr and "6/80" in r.stderr


def test_cli_without_gate_stays_advisory(tmp_path):
    r = _run(_cur(5, 80, prev=(6, 80)), tmp_path, gate=False)
    assert r.returncode == 0 and "advisory" in r.stderr

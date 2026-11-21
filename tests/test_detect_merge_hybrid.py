"""The hybrid gate must fire on a merge-collided artifact and stay silent otherwise.

2026-11-20T20:46: `git pull -X ours` merged a labelled anti-overfit payload against
a freshly generated one and pushed 81 rows for 80 strategies. The label re-stamp
repairs that payload; this gate is the general form of the same check, so the next
artifact a line-based merge collides is stopped before it is pushed -- and, just as
importantly, a clean payload is never blocked.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _gate():
    spec = importlib.util.spec_from_file_location(
        "detect_merge_hybrid", ROOT / "tools" / "detect_merge_hybrid.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows(n):
    return [{"strategy": "s%d" % i, "n": 10 + i} for i in range(n)]


def test_clean_payload_passes():
    assert _gate().inspect({"n_strategies_audited": 3, "strategies": _rows(3)}) == []


def test_count_that_names_its_array_is_checked():
    found = _gate().inspect({"n_strategies_audited": 2, "strategies": _rows(3)})
    assert any("n_strategies_audited=2" in f for f in found)


def test_subset_tally_is_not_a_row_count():
    """`n_fdr_pass=1` beside five top_sleeves means "one of these five passed"."""
    payload = {"classes": {"CRYPTO": {"top_sleeves": _rows(5), "n_fdr_pass": 1}}}
    assert _gate().inspect(payload) == []


def test_wide_count_difference_is_a_different_record_set():
    assert _gate().inspect({"n_strategies_audited": 40, "strategies": _rows(3)}) == []


def test_byte_identical_duplicate_is_flagged():
    row = {"strategy": "regime_mild_bear", "n": 283}
    found = _gate().inspect({"n_strategies_audited": 1, "strategies": [row, dict(row)]})
    assert any("byte-identical" in f for f in found)


def test_repeated_name_needs_a_count_problem_to_fail():
    rows = [{"strategy": "x", "n": 1}, {"strategy": "x", "n": 2}, {"strategy": "y", "n": 3}]
    assert _gate().inspect({"strategies": rows}) == []
    found = _gate().inspect({"n_strategies_audited": 2, "strategies": rows})
    assert any("differing values" in f for f in found)


def test_list_valued_identity_does_not_crash():
    """Some payloads carry a list where a name belongs; the gate has to survive it."""
    rows = [{"id": ["a"], "n": 1}, {"id": ["a"], "n": 2}, {"id": ["b"], "n": 3}]
    assert _gate().inspect({"strategies": rows}) == []


def test_nested_array_is_reached():
    found = _gate().inspect({"payload": {"n_picks": 1, "picks": _rows(2)}})
    assert any("n_picks=1" in f for f in found)


def test_cli_exit_codes(tmp_path):
    gate_path = ROOT / "tools" / "detect_merge_hybrid.py"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"n_strategies_audited": 1, "strategies": _rows(2)}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(gate_path), str(bad)], capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"n_strategies_audited": 2, "strategies": _rows(2)}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(gate_path), str(good)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_rows_missing_the_identity_key_do_not_crash():
    """The shape that crashed: 9 of 10 rows carry `symbol`, one does not."""
    rows = [{"symbol": "A", "n": 7}, {"symbol": "A", "n": 7}]
    rows += [{"symbol": "S%d" % i, "n": i} for i in range(7)]
    rows += [{"n": 99}]
    found = _gate().inspect({"picks": rows})
    assert any("byte-identical" in f for f in found), found
def test_default_cap_covers_the_largest_generated_artifact():
    assert _gate().MAX_BYTES >= 64 * 1024 * 1024


def test_oversize_artifact_is_reported_as_ungated(tmp_path):
    p = tmp_path / "big.json"
    p.write_text(json.dumps({"n_strategies_audited": 1,
                             "strategies": [{"strategy": "a"}]}))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "detect_merge_hybrid.py"),
                        "--max-mb", "0.000001", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "NOT gated" in r.stdout
    assert "WARNING" in r.stderr and "NOT gated" in r.stderr


def test_artifact_under_the_cap_is_inspected(tmp_path):
    p = tmp_path / "small.json"
    p.write_text(json.dumps({"n_strategies_audited": 1,
                             "strategies": [{"strategy": "a"}]}))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "detect_merge_hybrid.py"), str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 inspected" in r.stdout

"""The anti-overfit gate must be able to FAIL (2026-11-20).

A gate that runs but cannot fail is not enforcement. These tests pin both
directions: a passing payload returns 0, a failing payload returns non-zero,
and the CLI exit codes are checked through the real entry points.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _run(args, **kw):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          cwd=str(REPO), timeout=180, **kw)


def _payload(rows):
    return {"strategies": rows}


def test_sidecar_gate_passes_on_clean_payload(tmp_path):
    pytest.importorskip("pymysql")
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(_payload([
        {"strategy": "a", "n": 50, "dsr": 0.97},
        {"strategy": "b", "n": 50, "dsr": 0.99},
    ])))
    r = _run(["tools/anti_overfit_audit_sidecar.py", "--check-only", "--gate", "--in", str(f)])
    assert r.returncode == 0, r.stderr
    assert "PASS" in r.stderr


def test_sidecar_gate_fails_on_bad_dsr(tmp_path):
    pytest.importorskip("pymysql")
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(_payload([
        {"strategy": "good", "n": 50, "dsr": 0.99},
        {"strategy": "noise", "n": 50, "dsr": 0.31},
    ])))
    r = _run(["tools/anti_overfit_audit_sidecar.py", "--check-only", "--gate", "--in", str(f)])
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "noise" in r.stderr and "good" not in r.stderr.split("FAIL")[1]


def test_sidecar_missing_payload_is_an_error_not_a_pass(tmp_path):
    pytest.importorskip("pymysql")
    r = _run(["tools/anti_overfit_audit_sidecar.py", "--check-only", "--gate",
              "--in", str(tmp_path / "nope.json")])
    assert r.returncode == 3, (r.returncode, r.stderr)


def test_sidecar_without_gate_is_advisory(tmp_path):
    pytest.importorskip("pymysql")
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(_payload([{"strategy": "noise", "n": 50, "dsr": 0.1}])))
    r = _run(["tools/anti_overfit_audit_sidecar.py", "--check-only", "--in", str(f)])
    assert r.returncode == 0 and "advisory" in r.stderr


def test_null_dsr_is_a_failure_not_a_pass(tmp_path):
    pytest.importorskip("pymysql")
    f = tmp_path / "null.json"
    f.write_text(json.dumps(_payload([{"strategy": "x", "n": 50, "dsr": None}])))
    r = _run(["tools/anti_overfit_audit_sidecar.py", "--check-only", "--gate", "--in", str(f)])
    assert r.returncode == 2


def test_system_gate_treats_skip_as_failure():
    sys.path.insert(0, str(REPO / "tools"))
    import run_anti_overfit_audit as rao
    assert rao._gate_failures([{"source_system": "s", "deflated_sharpe": 0.5}], 0.95)
    assert rao._gate_failures([{"source_system": "s", "skipped": "insufficient sample"}], 0.95)
    assert not rao._gate_failures([{"source_system": "s", "deflated_sharpe": 0.96}], 0.95)


def test_workflow_gate_step_is_blocking_and_after_deploy():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load((REPO / ".github/workflows/audit-dashboard.yml").read_text())
    steps = doc["jobs"]["generate-and-deploy"]["steps"]
    names = [s.get("name", "") for s in steps]
    gate = [s for s in steps if s.get("name", "").startswith("Anti-overfit GATE")]
    assert len(gate) == 1, names
    assert gate[0].get("continue-on-error") in (None, False)
    deploy_i = [i for i, n in enumerate(names) if n.startswith("Deploy to all 3 FTP")][0]
    assert names.index(gate[0]["name"]) > deploy_i

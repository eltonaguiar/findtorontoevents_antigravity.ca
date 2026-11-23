"""I10/O2: tests for tools/check_fund_schema.py.

The gate exists because the report quoted numbers the tool no longer produced.
If the gate itself silently stops gating, that protection is imaginary, so the
failure modes are tested as carefully as the success.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "tools" / "check_fund_schema.py"
TRACKED = REPO_ROOT / "reports" / "fund_deep_dive.json"


def _run(payload_path, tracked_path):
    p = subprocess.run(
        [sys.executable, str(GATE), str(payload_path), str(tracked_path)],
        capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


@pytest.fixture
def good():
    if not TRACKED.exists():
        pytest.skip("no tracked payload in this checkout")
    return json.loads(TRACKED.read_text())


def _write(tmp_path, payload, name="p.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


def test_passes_on_the_real_payload(good, tmp_path):
    code, out = _run(_write(tmp_path, good), TRACKED)
    assert code == 0, out
    assert "schema OK" in out


def test_ignores_generated_at(good, tmp_path):
    """A new timestamp must not count as drift - otherwise every run fails."""
    mutate = json.loads(json.dumps(good))
    mutate["generated_at"] = "1999-01-01T00:00:00+00:00"
    code, out = _run(_write(tmp_path, mutate), TRACKED)
    assert code == 0, out


def test_fails_on_schema_version_bump(good, tmp_path):
    mutate = json.loads(json.dumps(good))
    mutate["schema_version"] = 99
    code, out = _run(_write(tmp_path, mutate), TRACKED)
    assert code == 1
    assert "schema_version" in out


def test_fails_when_a_contract_key_disappears(good, tmp_path):
    mutate = json.loads(json.dumps(good))
    key = next(iter(mutate["funds"]))
    del mutate["funds"][key]["net_cagr_pct"]
    code, out = _run(_write(tmp_path, mutate), TRACKED)
    assert code == 1
    assert "net_cagr_pct" in out


def test_fails_when_net_exceeds_gross(good, tmp_path):
    """The gross/net mix-up is the exact error that produced a false bug report."""
    mutate = json.loads(json.dumps(good))
    key = "SPY_adj"
    mutate["funds"][key]["net_cagr_pct"] = mutate["funds"][key]["cagr_pct"] + 1.0
    code, out = _run(_write(tmp_path, mutate), TRACKED)
    assert code == 1
    assert "backwards" in out or "gross" in out


def test_fails_when_tracked_artifact_is_stale(good, tmp_path):
    mutate = json.loads(json.dumps(good))
    mutate["funds"]["SPY_adj"]["cagr_pct"] = 123.4
    fresh = _write(tmp_path, good, "fresh.json")
    stale = _write(tmp_path, mutate, "stale.json")
    code, out = _run(fresh, stale)
    assert code == 1
    assert "STALE" in out


def test_zero_fee_fund_must_be_unchanged_by_the_fee_step(good, tmp_path):
    mutate = json.loads(json.dumps(good))
    if "FZROX_adj" not in mutate["funds"]:
        pytest.skip("FZROX not in payload")
    mutate["funds"]["FZROX_adj"]["net_cagr_pct"] = (
        mutate["funds"]["FZROX_adj"]["cagr_pct"] - 0.5
    )
    code, out = _run(_write(tmp_path, mutate), TRACKED)
    assert code == 1
    assert "FZROX" in out

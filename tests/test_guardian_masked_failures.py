"""Unit tests for the guardian's masked-failure detector (green job, failed step)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import actions_failure_guardian as g  # noqa: E402


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


def _mk_run(rid=1, name="wf", status="completed", conclusion="success"):
    return {"id": rid, "name": name, "status": status, "conclusion": conclusion,
            "run_number": 7, "head_branch": "main", "html_url": "u", "created_at": "t"}


def test_detects_green_job_with_failed_step(monkeypatch):
    jobs = {"jobs": [{"name": "build", "conclusion": "success", "steps": [
        {"name": "ok", "conclusion": "success", "number": 1},
        {"name": "masked-step", "conclusion": "failure", "number": 2},
    ]}]}
    monkeypatch.setattr(g, "gh_request", lambda *a, **k: _Resp(jobs))
    monkeypatch.setattr(g.time, "sleep", lambda *a, **k: None)
    out = g.detect_masked_failures("repo", "tok", [_mk_run()], max_runs=10)
    assert len(out) == 1
    assert out[0]["failed_step_count"] == 1
    assert out[0]["failed_steps"][0]["name"] == "masked-step"


def test_clean_green_job_not_flagged(monkeypatch):
    jobs = {"jobs": [{"name": "b", "conclusion": "success", "steps": [
        {"name": "ok", "conclusion": "success", "number": 1}]}]}
    monkeypatch.setattr(g, "gh_request", lambda *a, **k: _Resp(jobs))
    monkeypatch.setattr(g.time, "sleep", lambda *a, **k: None)
    assert g.detect_masked_failures("repo", "tok", [_mk_run(2)]) == []


def test_non_success_runs_skipped(monkeypatch):
    # a failed run is not a "masked" candidate (top-level guardian already catches it)
    called = {"n": 0}
    def _gh(*a, **k):
        called["n"] += 1
        return _Resp({"jobs": []})
    monkeypatch.setattr(g, "gh_request", _gh)
    monkeypatch.setattr(g.time, "sleep", lambda *a, **k: None)
    g.detect_masked_failures("repo", "tok", [_mk_run(3, conclusion="failure")])
    assert called["n"] == 0  # no /jobs call for non-success runs


def test_masker_workflow_filter(monkeypatch):
    jobs = {"jobs": [{"name": "b", "conclusion": "success", "steps": [
        {"name": "x", "conclusion": "failure", "number": 1}]}]}
    monkeypatch.setattr(g, "gh_request", lambda *a, **k: _Resp(jobs))
    monkeypatch.setattr(g.time, "sleep", lambda *a, **k: None)
    runs = [_mk_run(4, name="other"), _mk_run(5, name="masker-wf")]
    out = g.detect_masked_failures("repo", "tok", runs, masker_workflows=frozenset({"masker-wf"}))
    assert len(out) == 1 and out[0]["workflow_name"] == "masker-wf"

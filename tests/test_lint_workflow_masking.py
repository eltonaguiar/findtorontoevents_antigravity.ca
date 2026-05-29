"""Unit tests for the workflow masking-policy linter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lint_workflow_masking as L  # noqa: E402


def _wf(d: Path, name: str, body: str):
    (d / name).write_text(body)


def _setup(tmp_path):
    wf = tmp_path / "workflows"
    wf.mkdir()
    _wf(wf, "silent_new.yml", "steps:\n  - run: x\n    continue-on-error: true\n")
    _wf(wf, "baselined.yml", "steps:\n  - run: y\n    continue-on-error: true\n")
    _wf(wf, "warned.yml", "steps:\n  - run: z || echo '::warning::stale'\n    continue-on-error: true\n")
    _wf(wf, "approved.yml", "steps:\n  - run: a\n    continue-on-error: true\n")
    _wf(wf, "clean.yml", "steps:\n  - run: b\n")
    return str(wf)


def _manifest():
    return {"approved": [{"workflow": "approved.yml", "reason": "intentional"}],
            "known_silent": ["baselined.yml"]}


def test_classifies_each_tier(tmp_path):
    res = L.scan(_setup(tmp_path), _manifest())
    by = {r["workflow"]: r["status"] for r in res["rows"]}
    assert by["silent_new.yml"] == "silent"
    assert by["baselined.yml"] == "silent"
    assert by["warned.yml"] == "warn_surfaced"
    assert by["approved.yml"] == "approved"
    assert "clean.yml" not in by  # coe==0 not reported
    assert res["silent_new"] == ["silent_new.yml"]
    assert res["silent_baselined"] == ["baselined.yml"]


def test_baselined_and_approved_do_not_count_as_new(tmp_path):
    # remove the genuinely-new one; only baselined + approved remain -> 0 NEW
    wf = _setup(tmp_path)
    (Path(wf) / "silent_new.yml").unlink()
    res = L.scan(wf, _manifest())
    assert res["silent_new"] == []

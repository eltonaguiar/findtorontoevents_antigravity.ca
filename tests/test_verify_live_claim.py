"""Tests for tools/verify_live_claim.py — the guard against reporting a
branch-only feature as live.

The ref fixtures are built in a throwaway git repo instead of borrowing this
clone's refs: CI checks out a detached merge ref with no origin/main, and a test
that needs one fails there for a reason unrelated to the tool.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import verify_live_claim as v  # noqa: E402

GIT = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t"]


def _scratch_repo(tmp_path):
    """A tiny repo whose refs/remotes/origin/main points at its only commit."""
    subprocess.run(GIT + ["init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "live.txt").write_text("shipped\n")
    subprocess.run(GIT + ["-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "update-ref",
                    "refs/remotes/origin/main", "HEAD"], check=True)
    return str(tmp_path)


def test_path_on_ref_detects_a_merged_file(tmp_path):
    repo = _scratch_repo(tmp_path)
    ok, detail = v.path_on_ref("live.txt", ref="origin/main", cwd=repo)
    assert ok is True, detail
    assert "present on" in detail


def test_path_absent_from_ref_is_flagged(tmp_path):
    repo = _scratch_repo(tmp_path)
    ok, detail = v.path_on_ref("this/does/not/exist_xyz.py", ref="origin/main", cwd=repo)
    assert ok is False
    assert "ABSENT" in detail


def test_local_main_is_used_when_there_is_no_origin_remote(tmp_path):
    # This is the CI shape: a detached checkout with a local `main` only.
    repo = _scratch_repo(tmp_path)
    subprocess.run(["git", "-C", repo, "update-ref", "-d", "refs/remotes/origin/main"], check=True)
    ok, detail = v.path_on_ref("live.txt", ref="origin/main", cwd=repo)
    assert ok is True, detail
    assert "present on" in detail


def test_unresolvable_ref_refuses_instead_of_passing(tmp_path):
    repo = _scratch_repo(tmp_path)
    ok, detail = v.path_on_ref("live.txt", ref="origin/does-not-exist", cwd=repo)
    assert ok is False, "an unverifiable claim must never read as verified"
    assert "cannot resolve" in detail


def test_verdict_refuses_when_any_claim_is_unsupported(capsys):
    code = v.verdict([(True, "path a.py", "present"), (False, "url https://x/y", "HTTP 404")])
    assert code == 1
    err = capsys.readouterr().err
    assert "REFUSING" in err
    assert "1 of 2" in err


def test_verdict_passes_when_all_claims_hold(capsys):
    assert v.verdict([(True, "path a.py", "present"), (True, "url https://x/y", "HTTP 200")]) == 0


def test_no_claims_is_a_usage_error():
    try:
        v.main(["--no-fetch"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for an empty claim list")

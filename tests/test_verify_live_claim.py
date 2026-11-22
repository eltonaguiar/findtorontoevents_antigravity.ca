"""Tests for tools/verify_live_claim.py — the guard against reporting a
branch-only feature as live."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import verify_live_claim as v  # noqa: E402


def test_path_absent_from_ref_is_flagged():
    ok, detail = v.path_on_ref("this/does/not/exist_xyz.py", ref="origin/main", cwd=str(ROOT))
    assert ok is False
    assert "ABSENT" in detail


def test_path_on_ref_detects_a_merged_file():
    # tools/forward_book.py landed on main in PR #1047; if it is ever removed this
    # test tells us the guard is looking at the right tree.
    ok, detail = v.path_on_ref("tools/forward_book.py", ref="origin/main", cwd=str(ROOT))
    assert ok is True, detail
    assert "present on origin/main" in detail


def test_verdict_refuses_when_any_claim_is_unsupported(capsys):
    code = v.verdict([(True, "path a.py", "present"), (False, "url https://x/y", "HTTP 404")])
    assert code == 1
    err = capsys.readouterr().err
    assert "REFUSING" in err
    assert "1 of 2" in err


def test_verdict_passes_when_all_claims_hold():
    assert v.verdict([(True, "path a.py", "present"), (True, "url https://x/y", "HTTP 200")]) == 0


def test_no_claims_is_a_usage_error():
    try:
        v.main(["--no-fetch"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for an empty claim list")

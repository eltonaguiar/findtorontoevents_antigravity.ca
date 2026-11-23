"""Offline tests for tools/verify_peer_claims.py.

Deterministic and network-free: a throwaway git repo is built in tmp_path and the
checker functions are driven directly. No gh, no origin remote, no network.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import verify_peer_claims as vpc  # noqa: E402


def _run(*args, cwd):
    return subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, filename: str, content: str, message: str) -> str:
    (repo / filename).write_text(content, encoding="utf-8")
    _run("git", "add", filename, cwd=repo)
    _run("git", "-c", "user.name=Test Bot", "-c", "user.email=test-bot@example.com",
         "commit", "-m", message, cwd=repo)
    return _run("git", "rev-parse", "HEAD", cwd=repo)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run("git", "init", "-q", "-b", "main", cwd=path)
    return path


def _repo_with_origin_main(tmp_path: Path):
    """A repo whose origin/main is the first commit; side branches carry later work."""
    repo = _init_repo(tmp_path / "repo")
    first = _commit(repo, "base.txt", "base\n", "base commit")
    _run("git", "update-ref", "refs/remotes/origin/main", first, cwd=repo)
    return repo, first


def test_ancestor_of_main_passes(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_commit_ancestor_of_main(repo, first)
    assert status == vpc.STATUS_PASS, detail


def test_existing_commit_not_ancestor_fails(tmp_path):
    # The exact defect class: cat-file succeeds, but the commit is not reachable from origin/main.
    repo, _first = _repo_with_origin_main(tmp_path)
    local_only = _commit(repo, "side.txt", "side\n", "local only")
    exists, _ = vpc.check_commit_exists(repo, local_only)
    assert exists == vpc.STATUS_PASS
    status, detail = vpc.check_commit_ancestor_of_main(repo, local_only)
    assert status == vpc.STATUS_FAIL
    assert "NOT an ancestor" in detail
    status, detail = vpc.check_commit_on_any_origin_ref(repo, local_only)
    assert status == vpc.STATUS_FAIL


def test_commit_on_origin_branch_passes(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    side = _commit(repo, "side.txt", "side\n", "on a pushed branch")
    _run("git", "update-ref", "refs/remotes/origin/research/side", side, cwd=repo)
    status, detail = vpc.check_commit_on_any_origin_ref(repo, side)
    assert status == vpc.STATUS_PASS, detail
    # On an origin branch is still not an ancestor of main.
    status, _ = vpc.check_commit_ancestor_of_main(repo, side)
    assert status == vpc.STATUS_FAIL


def test_path_on_main_pass_and_fail(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_path_on_main(repo, "base.txt")
    assert status == vpc.STATUS_PASS, detail
    status, detail = vpc.check_path_on_main(repo, "missing.txt")
    assert status == vpc.STATUS_FAIL


def test_path_on_main_blob_prefix(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    blob = _run("git", "rev-parse", f"{first}:base.txt", cwd=repo)
    status, detail = vpc.check_path_on_main(repo, "base.txt", blob_prefix=blob[:9])
    assert status == vpc.STATUS_PASS, detail
    status, detail = vpc.check_path_on_main(repo, "base.txt", blob_prefix="0000000")
    assert status == vpc.STATUS_FAIL
    assert "no entry sha starts with" in detail


def test_path_absent_from_main_passes(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_path_absent_from_main(repo, "never_there.py")
    assert status == vpc.STATUS_PASS, detail
    status, _ = vpc.check_path_absent_from_main(repo, "base.txt")
    assert status == vpc.STATUS_FAIL


def test_commit_absent_typo_claim(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_commit_absent(repo, "0000000")
    assert status == vpc.STATUS_PASS, detail


def test_author_set(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    # `first` is a root commit, so the range is just the sha itself.
    status, detail = vpc.check_author_set(repo, first, ["test-bot@example.com"])
    assert status == vpc.STATUS_PASS, detail
    status, _ = vpc.check_author_set(repo, first, ["someone@else.com"])
    assert status == vpc.STATUS_FAIL


def test_derive_verdict_rules():
    P, F, S = vpc.STATUS_PASS, vpc.STATUS_FAIL, vpc.STATUS_SKIP
    assert vpc.derive_verdict([(P, ""), (P, "")]) == "VERIFIED"
    assert vpc.derive_verdict([(F, "")]) == "NOT LANDED"
    assert vpc.derive_verdict([(F, ""), (F, "")]) == "NOT LANDED"
    assert vpc.derive_verdict([(P, ""), (F, "")]) == "PARTIALLY"
    assert vpc.derive_verdict([]) == "UNVERIFIABLE"
    assert vpc.derive_verdict([(S, ""), (S, "")]) == "UNVERIFIABLE"
    # SKIPs never decide anything on their own.
    assert vpc.derive_verdict([(P, ""), (S, "")]) == "VERIFIED"


def test_manual_claims_never_block_strict(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    claim = {"id": "M1", "group": "B", "claimant": "peer", "summary": "human call",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": "0000000"}],
             "manual": True, "manual_reason": "needs a human", "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim)
    assert result["manual"] is True
    assert result["any_fail"] is True
    assert result["computed_verdict"].endswith(vpc.MANUAL_SUFFIX)
    assert vpc.strict_violations([result]) == []
    # Same claim without the manual flag IS a violation.
    claim["manual"] = False
    claim.pop("manual_reason")
    result = vpc.run_claim(repo, "origin/main", None, claim)
    assert [v["id"] for v in vpc.strict_violations([result])] == ["M1"]


def test_normalize_verdict_composite_tags():
    assert vpc.normalize_verdict("VERIFIED (was true)") == "VERIFIED"
    assert vpc.normalize_verdict("VERIFIED — DEFECT CLOSED") == "VERIFIED"
    assert vpc.normalize_verdict("VERIFIED (facts), but NOT MINE") == "VERIFIED"
    assert vpc.normalize_verdict("NOT LANDED (on origin)") == "NOT LANDED"
    assert vpc.normalize_verdict("PARTIALLY") == "PARTIALLY"
    assert vpc.normalize_verdict("garbage") is None


def test_pr_state_skips_without_repo_or_gh(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_pr_state(repo, 1, "OPEN", repo=None)
    assert status == vpc.STATUS_SKIP, detail


def test_validate_claims_rejects_bad_manifest():
    good = [{"id": "X1", "group": "A", "claimant": "c", "summary": "s",
             "checks": [{"kind": "commit_exists", "sha": "abc"}],
             "manual": False, "expected_verdict": "VERIFIED"}]
    assert vpc.validate_claims(good) == []
    bad = json.loads(json.dumps(good))
    bad[0]["checks"][0]["kind"] = "made_up_kind"
    bad[0]["expected_verdict"] = "MAYBE"
    problems = vpc.validate_claims(bad)
    assert any("unsupported kind" in p for p in problems)
    assert any("expected_verdict" in p for p in problems)


def test_report_rendering_is_deterministic_and_avoids_docs(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    claim = {"id": "D1", "group": "A", "claimant": "peer", "summary": "exists",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": first}],
             "manual": False, "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim)
    meta = {"generated_utc": "2026-11-23T00:00:00Z", "origin_main": first, "ref": "origin/main",
            "claims_path": "claims/x.json", "claims_sha256": "0" * 64, "n_claims": 1,
            "n_agree": 1, "n_disagree": 0, "n_disagree_nonmanual": 0, "n_manual": 0}
    first_render = vpc.build_report(meta, [result])
    assert first_render == vpc.build_report(meta, [result])
    assert "## What this run does NOT verify" in first_render
    assert "COMS bus" in first_render
    assert "ref-reachability result only" in first_render

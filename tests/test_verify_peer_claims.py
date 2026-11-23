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


# --------------------------------------------------------------------------- #
# git checks
# --------------------------------------------------------------------------- #
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


def test_commit_absent_only_when_object_missing(tmp_path):
    """commit_absent is honest about what it proves: object missing, nothing more."""
    repo, _first = _repo_with_origin_main(tmp_path)
    # Genuinely garbage sha -> object absent -> PASS.
    status, detail = vpc.check_commit_absent(repo, "0000000")
    assert status == vpc.STATUS_PASS, detail
    # Existing-but-unreachable sha -> commit_absent must NOT pass (it exists in this clone).
    local_only = _commit(repo, "side.txt", "side\n", "local only")
    status, detail = vpc.check_commit_absent(repo, local_only)
    assert status == vpc.STATUS_FAIL, detail
    assert "DOES exist" in detail


def test_commit_not_reachable_when_only_local(tmp_path):
    """A commit on a temp branch that no origin ref carries -> commit_not_reachable PASSes."""
    repo, _first = _repo_with_origin_main(tmp_path)
    local_only = _commit(repo, "side.txt", "side\n", "local only")
    status, detail = vpc.check_commit_not_reachable(repo, local_only)
    assert status == vpc.STATUS_PASS, detail
    assert "no refs/remotes/origin" in detail
    # Once an origin ref carries it, it is reachable and the check fails.
    _run("git", "update-ref", "refs/remotes/origin/research/side", local_only, cwd=repo)
    status, detail = vpc.check_commit_not_reachable(repo, local_only)
    assert status == vpc.STATUS_FAIL, detail


def test_commit_not_reachable_fails_for_missing_object(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    status, detail = vpc.check_commit_not_reachable(repo, "0000000")
    assert status == vpc.STATUS_FAIL, detail


def test_author_set(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    # `first` is a root commit, so the range is just the sha itself.
    status, detail = vpc.check_author_set(repo, first, ["test-bot@example.com"])
    assert status == vpc.STATUS_PASS, detail
    status, _ = vpc.check_author_set(repo, first, ["someone@else.com"])
    assert status == vpc.STATUS_FAIL


def test_author_is_bot_removed():
    """Block 26: author_is_bot was indistinguishable from author_set and could not detect bots."""
    assert "author_is_bot" not in vpc.CHECKS
    assert not hasattr(vpc, "check_author_is_bot")


# --------------------------------------------------------------------------- #
# per-check ref + remote map
# --------------------------------------------------------------------------- #
def _review_repo(tmp_path: Path):
    review = _init_repo(tmp_path / "review")
    tip = _commit(review, "assessment.md", "hub\n", "review commit")
    return review, tip


def test_per_check_ref_against_remote_map(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    review, tip = _review_repo(tmp_path)
    extras = {"review": str(review)}
    claim = {"id": "R1", "group": "B", "claimant": "peer", "summary": "review sha",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": tip,
                         "ref": "review/main", "polarity": "supports"}],
             "manual": False, "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim, extras)
    assert result["checks"][0]["status"] == vpc.STATUS_PASS, result["checks"][0]["detail"]
    assert result["checks"][0]["ref"] == "review/main"
    assert result["computed_verdict"] == "VERIFIED"


def test_remote_map_env_var(tmp_path, monkeypatch):
    repo, _first = _repo_with_origin_main(tmp_path)
    review, tip = _review_repo(tmp_path)
    monkeypatch.setenv("VERIFY_EXTRA_REMOTES", json.dumps({"review": str(review)}))
    claims = tmp_path / "claims.json"
    claims.write_text(json.dumps({"claims": [
        {"id": "R2", "group": "B", "claimant": "peer", "summary": "review sha",
         "checks": [{"kind": "commit_ancestor_of_main", "sha": tip,
                     "ref": "review/main", "polarity": "supports"}],
         "manual": False, "expected_verdict": "VERIFIED"}]}), encoding="utf-8")
    out = tmp_path / "report.md"
    rc = vpc.main(["--claims", str(claims), "--out", str(out), "--strict", "--allow-dirty-ref"])
    assert rc == 0
    assert "R2" in out.read_text(encoding="utf-8")


def test_unresolvable_ref_skips_not_fails(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    claim = {"id": "R3", "group": "B", "claimant": "peer", "summary": "review sha",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": "0000000",
                         "ref": "review/main", "polarity": "supports"}],
             "manual": False, "expected_verdict": "UNVERIFIABLE"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert result["checks"][0]["status"] == vpc.STATUS_SKIP
    assert "cannot resolve review/main" in result["checks"][0]["detail"]
    assert result["computed_verdict"] == "UNVERIFIABLE"


def test_skipped_check_does_not_fail_strict(tmp_path):
    """An unresolvable ref yields SKIP; with nothing else decidable --strict must exit 0."""
    repo, _first = _repo_with_origin_main(tmp_path)
    claim = {"id": "R4", "group": "B", "claimant": "peer", "summary": "review sha",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": "0000000",
                         "ref": "review/main", "polarity": "supports"}],
             "manual": False, "expected_verdict": "UNVERIFIABLE"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert vpc.strict_violations([result]) == []
    # ... and a real disagreement still does fail strict.
    claim["expected_verdict"] = "VERIFIED"
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert [v["id"] for v in vpc.strict_violations([result])] == []


# --------------------------------------------------------------------------- #
# polarity + verdict derivation (the Block 26 correction)
# --------------------------------------------------------------------------- #
def test_derive_verdict_rules():
    P, F, S = vpc.STATUS_PASS, vpc.STATUS_FAIL, vpc.STATUS_SKIP
    SU, RE = vpc.POLARITY_SUPPORTS, vpc.POLARITY_REFUTES
    assert vpc.derive_verdict([(P, SU), (P, SU)]) == "VERIFIED"
    assert vpc.derive_verdict([(F, SU)]) == "NOT LANDED"
    assert vpc.derive_verdict([(F, SU), (F, SU)]) == "NOT LANDED"
    assert vpc.derive_verdict([(P, SU), (F, SU)]) == "PARTIALLY"
    assert vpc.derive_verdict([]) == "UNVERIFIABLE"
    assert vpc.derive_verdict([(S, SU), (S, SU)]) == "UNVERIFIABLE"
    # SKIPs never decide anything on their own.
    assert vpc.derive_verdict([(P, SU), (S, SU)]) == "VERIFIED"
    # 'refutes' polarity flips the meaning: a PASS on a refuting check is evidence against.
    assert vpc.derive_verdict([(P, RE)]) == "NOT LANDED"
    assert vpc.derive_verdict([(F, RE)]) == "VERIFIED"


def test_absent_path_claim_is_not_landed(tmp_path):
    """Targets the Block 26 rule: a PASSing path_absent_from_main is NOT support.

    Under the old rule this claim derived VERIFIED (all checks PASSed); under the
    polarity rule it must derive NOT LANDED.
    """
    repo, _first = _repo_with_origin_main(tmp_path)
    claim = {"id": "T1", "group": "B", "claimant": "peer", "summary": "claims to add a file",
             "checks": [{"kind": "path_absent_from_main", "path": "never_there.py",
                         "polarity": "refutes"}],
             "manual": False, "expected_verdict": "NOT LANDED"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert result["checks"][0]["status"] == vpc.STATUS_PASS
    assert result["supporting"] == 0 and result["refuting"] == 1
    assert result["computed_verdict"] == "NOT LANDED"
    assert result["computed_verdict"] not in ("PARTIALLY", "VERIFIED")


def test_mixed_supporting_and_refuting_is_partially(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    claim = {"id": "T2", "group": "B", "claimant": "peer", "summary": "mixed",
             "checks": [
                 {"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"},
                 {"kind": "path_absent_from_main", "path": "never_there.py", "polarity": "refutes"}],
             "manual": False, "expected_verdict": "PARTIALLY"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert result["supporting"] == 1 and result["refuting"] == 1
    assert result["computed_verdict"] == "PARTIALLY"


def test_default_polarity_is_supports(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    claim = {"id": "T3", "group": "B", "claimant": "peer", "summary": "no polarity key",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": first}],
             "manual": False, "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert result["checks"][0]["polarity"] == vpc.POLARITY_SUPPORTS
    assert result["computed_verdict"] == "VERIFIED"


def test_manifest_declares_polarity_and_absence_checks_refute():
    """FIX 2: every check in the real manifest has an explicit polarity, and every
    absence check (path_absent_from_main / commit_absent / commit_not_reachable) refutes."""
    manifest = Path(__file__).resolve().parent.parent / "claims" / "verification_claims.json"
    claims = json.loads(manifest.read_text(encoding="utf-8"))["claims"]
    absence_kinds = {"path_absent_from_main", "commit_absent", "commit_not_reachable"}
    n_checks = 0
    for claim in claims:
        for chk in claim["checks"]:
            n_checks += 1
            assert chk.get("polarity") in vpc.POLARITIES, (claim["id"], chk)
            if chk["kind"] in absence_kinds:
                assert chk["polarity"] == vpc.POLARITY_REFUTES, (claim["id"], chk)
    assert n_checks >= 40
    assert vpc.validate_claims(claims) == []


def test_manual_claims_never_block_strict(tmp_path):
    repo, _first = _repo_with_origin_main(tmp_path)
    claim = {"id": "M1", "group": "B", "claimant": "peer", "summary": "human call",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": "0000000", "polarity": "supports"}],
             "manual": True, "manual_reason": "needs a human", "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    assert result["manual"] is True
    assert result["any_fail"] is True
    assert result["computed_verdict"].endswith(vpc.MANUAL_SUFFIX)
    assert vpc.strict_violations([result]) == []
    # Same claim without the manual flag IS a violation.
    claim["manual"] = False
    claim.pop("manual_reason")
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
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
    bad[0]["checks"][0]["polarity"] = "sideways"
    bad[0]["expected_verdict"] = "MAYBE"
    problems = vpc.validate_claims(bad)
    assert any("unsupported kind" in p for p in problems)
    assert any("polarity" in p for p in problems)
    assert any("expected_verdict" in p for p in problems)


def test_report_rendering_is_deterministic_and_avoids_docs(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    claim = {"id": "D1", "group": "A", "claimant": "peer", "summary": "exists",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"}],
             "manual": False, "expected_verdict": "VERIFIED"}
    result = vpc.run_claim(repo, "origin/main", None, claim, {})
    meta = {"generated_utc": "2026-11-23T00:00:00Z", "origin_main": first, "ref": "origin/main",
            "extra_remotes": "", "claims_path": "claims/x.json", "claims_sha256": "0" * 64,
            "n_claims": 1, "n_agree": 1, "n_disagree": 0, "n_disagree_nonmanual": 0, "n_manual": 0}
    first_render = vpc.build_report(meta, [result])
    assert first_render == vpc.build_report(meta, [result])
    assert "## What this run does NOT verify" in first_render
    assert "COMS bus" in first_render
    assert "ref-reachability result only" in first_render
    assert "clone-local" in first_render

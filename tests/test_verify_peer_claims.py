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
    # --allow-shallow: main() runs against this checkout's repo root, which may
    # itself be shallow-marked; this test is about the remote map, not depth.
    rc = vpc.main(["--claims", str(claims), "--out", str(out), "--strict",
                   "--allow-dirty-ref", "--allow-shallow"])
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
    absence check (path_absent_from_main / commit_absent / commit_not_reachable) refutes.

    Exception: B5-typo asserts non-existence, so its `commit_absent` check is `supports`
    there - a PASS is evidence FOR that claim. Any other absence check must refute.

    Retired claims are exempt from the absence rule only: a retired claim's checks are
    a frozen historical record of what was checked when the claim was live, and they
    are no longer evidence either way (Block 42 - see `## Retiring a claim` in
    docs/VERIFICATION.md). Their polarity must still be well-formed, and every ACTIVE
    claim is held to the same rule as before.
    """
    manifest = Path(__file__).resolve().parent.parent / "claims" / "verification_claims.json"
    claims = json.loads(manifest.read_text(encoding="utf-8"))["claims"]
    absence_kinds = {"path_absent_from_main", "commit_absent", "commit_not_reachable"}
    n_checks = 0
    for claim in claims:
        for chk in claim["checks"]:
            n_checks += 1
            assert chk.get("polarity") in vpc.POLARITIES, (claim["id"], chk)
            if claim.get("retired"):
                continue
            if chk["kind"] in absence_kinds and claim["id"] != "B5-typo":
                assert chk["polarity"] == vpc.POLARITY_REFUTES, (claim["id"], chk)
    assert n_checks >= 40
    assert vpc.validate_claims(claims) == []


def test_split_typo_claim_verifies_both_propositions(tmp_path):
    """B5 bundles two propositions: the intended commits landed, and the cited sha is a typo.

    Averaged into one claim they cancel to PARTIALLY; split, each computes VERIFIED.
    """
    repo, first = _repo_with_origin_main(tmp_path)
    second = _commit(repo, "second.txt", "second\n", "second commit")
    _run("git", "update-ref", "refs/remotes/origin/main", second, cwd=repo)
    typo = second[:6] + "0f0f0f"  # a sha that does not exist in this clone

    landing = {"id": "T-landing", "group": "B", "claimant": "peer", "summary": "landed",
               "checks": [{"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"},
                          {"kind": "commit_ancestor_of_main", "sha": second, "polarity": "supports"}],
               "manual": False, "expected_verdict": "VERIFIED"}
    citation = {"id": "T-typo", "group": "B", "claimant": "peer", "summary": "typo",
                "checks": [{"kind": "commit_absent", "sha": typo, "polarity": "supports"},
                           {"kind": "commit_ancestor_of_main", "sha": second, "polarity": "supports"}],
                "manual": False, "expected_verdict": "VERIFIED"}

    for claim in (landing, citation):
        result = vpc.run_claim(repo, "origin/main", None, claim, {})
        assert result["computed_verdict"] == "VERIFIED", result
        assert result["refuting"] == 0, result
        assert vpc.strict_violations([result]) == []

    # Averaged into a single claim (the original B5 shape: the typo check declared
    # `refutes`), the same evidence reads PARTIALLY.
    bundled_checks = landing["checks"] + [{"kind": "commit_absent", "sha": typo, "polarity": "refutes"},
                                          {"kind": "commit_ancestor_of_main", "sha": second,
                                           "polarity": "supports"}]
    bundled = dict(landing, checks=bundled_checks)
    assert vpc.run_claim(repo, "origin/main", None, bundled, {})["computed_verdict"] == "PARTIALLY"


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


# --------------------------------------------------------------------------- #
# shallow clones (Block 30: depth-1 inverts landed verdicts)
# --------------------------------------------------------------------------- #
def _shallow_pair(tmp_path: Path):
    """A two-commit source repo plus a depth-1 clone of it, with the engine copied in.

    The clone is real (`git clone --depth 1 file://...`), so `git rev-parse
    --is-shallow-repository` prints true there - exactly the CI condition.
    """
    src = _init_repo(tmp_path / "shallow_src")
    base = _commit(src, "base.txt", "base\n", "base commit")
    second = _commit(src, "second.txt", "second\n", "second commit")
    _run("git", "update-ref", "refs/remotes/origin/main", second, cwd=src)
    dst = tmp_path / "shallow_dst"
    _run("git", "clone", "-q", "--depth", "1", f"file://{src}", str(dst), cwd=tmp_path)
    (dst / "tools").mkdir()
    (dst / "tools" / "verify_peer_claims.py").write_text(
        (TOOLS / "verify_peer_claims.py").read_text(encoding="utf-8"), encoding="utf-8")
    claims = dst / "claims.json"
    claims.write_text(json.dumps({"claims": [
        {"id": "S1", "group": "B", "claimant": "peer", "summary": "base landed",
         "checks": [{"kind": "commit_ancestor_of_main", "sha": base, "polarity": "supports"}],
         "manual": False, "expected_verdict": "VERIFIED"},
        {"id": "S2", "group": "B", "claimant": "peer", "summary": "base on origin",
         "checks": [{"kind": "commit_on_any_origin_ref", "sha": base, "polarity": "supports"}],
         "manual": False, "expected_verdict": "VERIFIED"},
    ]}), encoding="utf-8")
    return src, dst, base, second


def _cli(repo: Path, *args):
    return subprocess.run(
        [sys.executable, "tools/verify_peer_claims.py", *args],
        cwd=str(repo), capture_output=True, text=True)


def test_shallow_clone_is_fatal_by_default(tmp_path):
    _src, dst, _base, _second = _shallow_pair(tmp_path)
    assert _run("git", "rev-parse", "--is-shallow-repository", cwd=dst) == "true"
    proc = _cli(dst, "--claims", "claims.json", "--out", "out.md",
                "--allow-dirty-ref", "--strict")
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert "FATAL: this is a shallow clone" in proc.stderr
    assert "--allow-shallow" in proc.stderr
    assert not (dst / "out.md").exists()


def test_allow_shallow_marks_results_unreliable(tmp_path):
    _src, dst, _base, _second = _shallow_pair(tmp_path)
    proc = _cli(dst, "--claims", "claims.json", "--out", "out.md",
                "--allow-dirty-ref", "--allow-shallow")
    assert proc.returncode == 0, (proc.returncode, proc.stderr)
    assert "WARNING: shallow clone" in proc.stderr
    report = (dst / "out.md").read_text(encoding="utf-8")
    # The inverted NOT LANDED is present but can never be mistaken for a real one.
    assert "NOT LANDED [SHALLOW CLONE - results unreliable]" in report
    assert report.count(vpc.SHALLOW_SUFFIX) >= 2


def test_full_clone_does_not_warn_shallow(tmp_path):
    src, _dst, base, _second = _shallow_pair(tmp_path)
    (src / "tools").mkdir()
    (src / "tools" / "verify_peer_claims.py").write_text(
        (TOOLS / "verify_peer_claims.py").read_text(encoding="utf-8"), encoding="utf-8")
    proc = _cli(src, "--claims", str(_dst_claims(tmp_path)), "--out", "out.md",
                "--allow-dirty-ref", "--strict")
    # In the full repo the same claims are decidable: the base commit IS landed.
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "shallow" not in proc.stderr.lower()
    assert vpc.SHALLOW_SUFFIX not in (src / "out.md").read_text(encoding="utf-8")


def _dst_claims(tmp_path: Path) -> Path:
    return tmp_path / "shallow_dst" / "claims.json"


def test_header_records_shallow_status_and_head_at_report_time(tmp_path):
    _src, dst, _base, second = _shallow_pair(tmp_path)
    proc = _cli(dst, "--claims", "claims.json", "--out", "out.md",
                "--allow-dirty-ref", "--allow-shallow")
    assert proc.returncode == 0, proc.stderr
    header = (dst / "out.md").read_text(encoding="utf-8").splitlines()[:12]
    text = "\n".join(header)
    assert "- shallow: true" in text
    assert f"- checked-out HEAD at report time: `{second}`" in text
    assert "- ref used for checks: `origin/main`" in text


def test_detect_shallow_returns_none_when_git_fails(tmp_path):
    empty = tmp_path / "not_a_repo"
    empty.mkdir()
    assert vpc.detect_shallow(empty) is None


def test_run_claim_marks_only_shallow_sensitive_checks(tmp_path):
    repo, first = _repo_with_origin_main(tmp_path)
    claim = {"id": "K1", "group": "B", "claimant": "peer", "summary": "mixed kinds",
             "checks": [{"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"},
                        {"kind": "pr_state", "number": 1, "expect_state": "OPEN",
                         "polarity": "supports"}],
             "manual": False, "expected_verdict": "VERIFIED"}
    shallow = vpc.run_claim(repo, "origin/main", None, claim, {}, shallow=True)
    full = vpc.run_claim(repo, "origin/main", None, claim, {}, shallow=False)
    assert shallow["checks"][0]["detail"].endswith(vpc.SHALLOW_SUFFIX)
    assert not shallow["checks"][1]["detail"].endswith(vpc.SHALLOW_SUFFIX)
    assert vpc.SHALLOW_SUFFIX not in full["computed_verdict"]
    assert vpc.SHALLOW_SUFFIX in shallow["computed_verdict"]


# --------------------------------------------------------------------------- #
# report header provenance (Block 30)
# --------------------------------------------------------------------------- #
def test_header_carries_head_at_report_and_shallow_fields():
    meta = {"generated_utc": "2026-11-23T00:00:00Z", "origin_main": "a" * 40,
            "ref": "origin/main", "head_at_report": "b" * 40, "shallow": False,
            "extra_remotes": "", "claims_path": "claims/x.json", "claims_sha256": "0" * 64,
            "n_claims": 0, "n_agree": 0, "n_disagree": 0, "n_disagree_nonmanual": 0,
            "n_manual": 0}
    text = vpc.build_report(meta, [])
    assert f"- checked-out HEAD at report time: `{'b' * 40}`" in text
    assert f"- ref used for checks: `origin/main` (`{'a' * 40}`)" in text
    assert "- shallow: false" in text
    assert "WARNING: shallow clone" not in text


def test_shallow_strict_violations_are_marked_but_still_counted(tmp_path):
    """--allow-shallow degrades honestly: a disagreement stays a disagreement."""
    _src, dst, _base, _second = _shallow_pair(tmp_path)
    proc = _cli(dst, "--claims", "claims.json", "--out", "out.md",
                "--allow-dirty-ref", "--allow-shallow", "--strict")
    assert proc.returncode == 1, (proc.returncode, proc.stderr)
    assert "strict violations: 2" in proc.stdout
    assert "VIOLATION [S1]" in proc.stderr


# --------------------------------------------------------------------------- #
# claim retirement (Block 42: a resolved claim is not a still-true claim)
# --------------------------------------------------------------------------- #
def _retired_claim_manifest(tmp_path: Path, *, reason: str | None = "resolved by a later PR"):
    """One retired claim whose check would DISAGREE (expected VERIFIED, evidence refutes)."""
    claim = {"id": "RET1", "group": "B", "claimant": "peer", "summary": "retired claim",
             "checks": [{"kind": "commit_exists", "sha": "0000000", "polarity": "supports"}],
             "manual": False, "expected_verdict": "VERIFIED", "retired": True}
    if reason is not None:
        claim["retired_reason"] = reason
    claims = tmp_path / "claims.json"
    claims.write_text(json.dumps({"claims": [claim]}), encoding="utf-8")
    return claims


def _run_main(tmp_path: Path, capsys, claims: Path, *extra):
    """Drive main() with --ref HEAD so nothing depends on origin/main in the host repo."""
    out = tmp_path / "report.md"
    rc = vpc.main(["--claims", str(claims), "--out", str(out), "--ref", "HEAD",
                   "--allow-dirty-ref", "--allow-shallow", *extra])
    captured = capsys.readouterr()
    report = out.read_text(encoding="utf-8") if out.exists() else ""
    return rc, captured, report


def test_retired_claim_is_listed_but_excluded_from_tallies(tmp_path, capsys):
    """A retired claim with refuting evidence is not in the disagree count, but IS reported.

    Its checks are still executed and their raw output still printed - a retirement
    that deleted the evidence would be indistinguishable from a cover-up.
    """
    claims = _retired_claim_manifest(tmp_path)
    rc, captured, report = _run_main(tmp_path, capsys, claims)
    assert rc == 0
    assert "0 disagree" in captured.out
    assert "1 retired" in captured.out
    # The claim itself is still printed, marked RETIRED, with its check output.
    assert "[RET1] RETIRED" in captured.out
    assert "commit_exists" in captured.out and "FAIL" in captured.out
    # ... and it is not in the main table, only in the trailing retired section.
    assert "| RET1 |" not in report
    assert "## Retired claims" in report
    assert "### RET1 - B - peer (RETIRED)" in report
    assert "resolved by a later PR" in report
    assert "commit_exists" in report.split("## Retired claims")[1]


def test_retired_claim_cannot_be_a_strict_violation(tmp_path, capsys):
    """Retirement removes a claim from --strict; the same claim un-retired is still a violation."""
    claims = _retired_claim_manifest(tmp_path)
    rc, captured, _ = _run_main(tmp_path, capsys, claims, "--strict")
    assert rc == 0
    assert "strict violations: 0" in captured.out

    # Positive control: without the retirement flag the same evidence IS a violation.
    data = json.loads(claims.read_text(encoding="utf-8"))
    data["claims"][0].pop("retired")
    data["claims"][0].pop("retired_reason")
    claims.write_text(json.dumps(data), encoding="utf-8")
    rc, captured, _ = _run_main(tmp_path, capsys, claims, "--strict")
    assert rc == 1
    assert "strict violations: 1" in captured.out


def test_retirement_requires_a_reason(tmp_path, capsys):
    """An unexplained retirement exits 2 and writes no report."""
    claims = _retired_claim_manifest(tmp_path, reason=None)
    rc, captured, report = _run_main(tmp_path, capsys, claims)
    assert rc == 2
    assert "retired_reason" in captured.err
    assert report == ""
    # The schema check names it too.
    problems = vpc.validate_claims(json.loads(claims.read_text(encoding="utf-8"))["claims"])
    assert any("retired_reason" in p for p in problems)


def test_retired_verdict_never_reports_verified_or_not_landed(tmp_path):
    """Whatever the checks say, a retired claim's verdict is RETIRED - never a live verdict."""
    repo, first = _repo_with_origin_main(tmp_path)
    base = {"id": "RET2", "group": "B", "claimant": "peer", "summary": "s",
            "manual": False, "expected_verdict": "VERIFIED", "retired": True,
            "retired_reason": "resolved"}
    cases = [
        # would derive VERIFIED
        [{"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"}],
        # would derive NOT LANDED
        [{"kind": "commit_exists", "sha": "0000000", "polarity": "supports"}],
        # would derive PARTIALLY
        [{"kind": "commit_ancestor_of_main", "sha": first, "polarity": "supports"},
         {"kind": "commit_exists", "sha": "0000000", "polarity": "supports"}],
    ]
    for checks in cases:
        claim = dict(base, checks=checks)
        result = vpc.run_claim(repo, "origin/main", None, claim, {})
        assert result["computed_verdict"] == vpc.RETIRED_VERDICT
        assert vpc.normalize_verdict(result["computed_verdict"]) == vpc.RETIRED_VERDICT
        assert not result["computed_verdict"].startswith(("VERIFIED", "NOT LANDED", "PARTIALLY"))
        assert result["agree"] is False
        assert vpc.strict_violations([result]) == []
        # every check still ran and is on the record
        assert len(result["checks"]) == len(checks)
        assert all(c["status"] in (vpc.STATUS_PASS, vpc.STATUS_FAIL) for c in result["checks"])


def test_argument_parsing_produces_exit_zero():
    """--help parses cleanly and exits 0 (the CLI's happy path for argument handling)."""
    proc = subprocess.run([sys.executable, str(TOOLS / "verify_peer_claims.py"), "--help"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    for flag in ("--claims", "--ref", "--remote-map", "--strict", "--allow-shallow"):
        assert flag in proc.stdout

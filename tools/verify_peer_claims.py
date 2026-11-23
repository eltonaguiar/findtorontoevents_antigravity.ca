#!/usr/bin/env python3
"""verify_peer_claims.py - deterministic peer-claim verification engine.

Why this exists (2026-11-23): a peer review of fleet "landed" claims found the same
failure mode over and over - a commit that existed only in a local clone (or on an
unmerged branch) was reported as landed.  `tools/verify_citations.py` checks
`git cat-file -e <sha>` (existence only) and therefore cannot catch it.  This tool
checks *reachability*: is the object an ancestor of origin/main, or on some
`refs/remotes/origin/*` ref?  A commit that exists only locally is NOT LANDED.

It reads a claims manifest (`claims/verification_claims.json`), runs each claim's
checks against real git refs, and writes a markdown report with the mechanical
result next to the verdict the hand-written report
(`updates/2026-11-23-peer-claim-verification.md`) recorded, so disagreements are
visible instead of being papered over.

Verdict vocabulary (fixed):
    VERIFIED / NOT LANDED / PARTIALLY / UNVERIFIABLE

Verdict derivation rule (applied per claim, after dropping SKIPped checks):
    * no executable check left                      -> UNVERIFIABLE
    * every executable check PASSes                 -> VERIFIED
    * at least one PASS and at least one FAIL       -> PARTIALLY
    * only FAILs                                   -> NOT LANDED
    * if the claim is `manual`, append " (manual judgement required)"; a manual
      claim's result is reported but NEVER blocks --strict.

Check kinds (exactly these):
    commit_ancestor_of_main  sha                        PASS if `git merge-base --is-ancestor <sha> <ref>` exits 0
    commit_on_any_origin_ref sha                        PASS if some refs/remotes/origin/* contains <sha>
    commit_exists            sha                        PASS if `git cat-file -e <sha>^{commit}` exits 0
    commit_absent            sha                        PASS if cat-file fails OR it is on no origin ref
    path_on_main             path[, blob_prefix]        PASS if `git ls-tree <ref> -- <path>` is non-empty
                                                        (and the entry sha starts with blob_prefix when given)
    path_absent_from_main    path                       PASS if `git ls-tree <ref> -- <path>` is empty
    pr_state                 number, expect_state       `gh pr view`; SKIP when gh is absent/unauthorised
    author_is_bot            sha_range, expect_authors  PASS if the %ae set of `git log <range>` matches
    author_set               sha_range, expect_authors  (same PASS criterion; author_is_bot adds a note
                                                        about whether the identities look like bots)

--strict semantics: a violation is (a) a non-manual claim whose computed verdict
disagrees with `expected_verdict`, or (b) a check FAIL inside a claim that the hand
report recorded as VERIFIED (a claimed-to-have-landed object that did not).
A FAIL inside a claim the hand report recorded as NOT LANDED / PARTIALLY is the
expected evidence for that verdict, not a violation.

Stdlib only - no imports from this repository, so it runs both as
`python3 tools/verify_peer_claims.py` and `python -m tools.verify_peer_claims`.

Usage:
    python3 tools/verify_peer_claims.py --strict --json-out /tmp/claims_run.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VERDICT_VOCAB = ("VERIFIED", "NOT LANDED", "PARTIALLY", "UNVERIFIABLE")
MANUAL_SUFFIX = " (manual judgement required)"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"


# --------------------------------------------------------------------------- #
# git plumbing
# --------------------------------------------------------------------------- #
def _git(root, args, timeout: int = 120):
    """(returncode, stdout.strip(), stderr.strip()) for `git -C root <args>`."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "", "git not available"
    except subprocess.TimeoutExpired:
        return 124, "", f"git timed out after {timeout}s"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def find_repo_root(start: Path | None = None) -> Path:
    """Repo root of `start` (default: this script's directory), else the script's grandparent."""
    start = start or Path(__file__).resolve().parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path(__file__).resolve().parent.parent


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text.strip() else ""


def resolve_ref(root, ref: str) -> str | None:
    """Commit sha of `ref`, or None when it does not exist in this clone."""
    rc, out, _ = _git(root, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    if rc != 0 or not out:
        return None
    return out.splitlines()[0]


def _commit_exists(root, sha: str) -> bool:
    rc, _, _ = _git(root, ["cat-file", "-e", f"{sha}^{{commit}}"])
    return rc == 0


def _origin_refs_containing(root, sha: str):
    """(refs, error) - origin remote refs that contain `sha`."""
    rc, out, err = _git(root, ["for-each-ref", "--contains", sha,
                               "--format=%(refname:short)", "refs/remotes/origin/"])
    if rc != 0:
        return [], err
    return [line for line in out.splitlines() if line.strip()], ""


def _shorten_refs(refs, limit: int = 3) -> str:
    shown = ", ".join(refs[:limit])
    if len(refs) > limit:
        shown += f" (+{len(refs) - limit} more)"
    return shown


# --------------------------------------------------------------------------- #
# check functions - each returns (status, detail) with status in PASS/FAIL/SKIP
# --------------------------------------------------------------------------- #
def check_commit_ancestor_of_main(root, sha: str, ref: str = "origin/main"):
    """PASS iff `git merge-base --is-ancestor <sha> <ref>` exits 0.

    Existence is checked first so 'exists but not an ancestor' (the defect class)
    is reported as FAIL with that exact wording, not as an error.
    """
    if resolve_ref(root, ref) is None:
        return STATUS_SKIP, f"cannot resolve {ref} in this clone"
    if not _commit_exists(root, sha):
        return STATUS_FAIL, f"{sha} does not resolve to a commit (git cat-file -e {sha}^{{commit}} -> non-zero)"
    rc, _, err = _git(root, ["merge-base", "--is-ancestor", sha, ref])
    if rc == 0:
        return STATUS_PASS, f"git merge-base --is-ancestor {sha} {ref} -> rc=0"
    if rc == 1:
        return STATUS_FAIL, (f"git merge-base --is-ancestor {sha} {ref} -> rc=1 "
                             f"(commit exists but is NOT an ancestor)")
    return STATUS_FAIL, f"git merge-base --is-ancestor {sha} {ref} -> rc={rc}: {_first_line(err)}"


def check_commit_on_any_origin_ref(root, sha: str):
    """PASS iff some refs/remotes/origin/* ref contains `sha`."""
    if not _commit_exists(root, sha):
        return STATUS_FAIL, f"{sha} does not resolve to a commit"
    refs, err = _origin_refs_containing(root, sha)
    if err:
        return STATUS_FAIL, f"git for-each-ref --contains {sha} failed: {_first_line(err)}"
    if refs:
        return STATUS_PASS, f"on origin ref(s): {_shorten_refs(refs)}"
    return STATUS_FAIL, f"{sha} is on no refs/remotes/origin/* ref (exists only locally)"


def check_commit_exists(root, sha: str):
    """PASS iff `git cat-file -e <sha>^{commit}` exits 0."""
    rc, out, _ = _git(root, ["cat-file", "-t", f"{sha}^{{commit}}"])
    if rc == 0:
        return STATUS_PASS, f"git cat-file -e {sha}^{{commit}} -> rc=0 (type {out or 'commit'})"
    return STATUS_FAIL, f"git cat-file -e {sha}^{{commit}} -> rc={rc} (object absent)"


def check_commit_absent(root, sha: str):
    """PASS iff the object does not exist, or exists but sits on no origin ref."""
    if not _commit_exists(root, sha):
        return STATUS_PASS, f"{sha} does not exist (git cat-file -e -> non-zero)"
    refs, err = _origin_refs_containing(root, sha)
    if refs:
        return STATUS_FAIL, f"{sha} exists and is on origin ref(s): {_shorten_refs(refs)}"
    if err:
        return STATUS_PASS, f"{sha} exists locally; origin refs unreadable ({_first_line(err)}) - no origin ref claims it"
    return STATUS_PASS, f"{sha} exists locally but is on no refs/remotes/origin/* ref"


def _ls_tree(root, ref: str, path: str):
    """(entries, error). entries = [(mode, type, sha, path)] from `git ls-tree <ref> -- <path>`."""
    rc, out, err = _git(root, ["ls-tree", ref, "--", path.rstrip("/")])
    if rc != 0:
        return [], err or f"git ls-tree -> rc={rc}"
    entries = []
    for line in out.splitlines():
        meta, _, entry_path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 3:
            entries.append((parts[0], parts[1], parts[2], entry_path))
    return entries, ""


def check_path_on_main(root, path: str, blob_prefix: str | None = None, ref: str = "origin/main"):
    """PASS iff `path` exists in the tree of `ref` (and its sha starts with blob_prefix if given)."""
    if resolve_ref(root, ref) is None:
        return STATUS_SKIP, f"cannot resolve {ref} in this clone"
    entries, err = _ls_tree(root, ref, path)
    if err:
        return STATUS_SKIP, f"git ls-tree {ref} -- {path} failed: {_first_line(err)}"
    if not entries:
        return STATUS_FAIL, f"git ls-tree {ref} -- {path} -> empty (ABSENT from {ref})"
    if blob_prefix:
        for _mode, typ, sha, entry_path in entries:
            if sha.startswith(blob_prefix):
                return STATUS_PASS, (f"{entry_path} on {ref} ({typ} {sha[:12]}) - "
                                     f"sha matches prefix {blob_prefix}")
        got = ", ".join(f"{e[1]} {e[2][:12]}" for e in entries)
        return STATUS_FAIL, (f"{path} is on {ref} but no entry sha starts with {blob_prefix} "
                             f"(got {got})")
    mode, typ, sha, entry_path = entries[0]
    return STATUS_PASS, f"{entry_path} on {ref} ({typ} {sha[:12]})"


def check_path_absent_from_main(root, path: str, ref: str = "origin/main"):
    """PASS iff `git ls-tree <ref> -- <path>` is empty."""
    if resolve_ref(root, ref) is None:
        return STATUS_SKIP, f"cannot resolve {ref} in this clone"
    entries, err = _ls_tree(root, ref, path)
    if err:
        return STATUS_SKIP, f"git ls-tree {ref} -- {path} failed: {_first_line(err)}"
    if entries:
        mode, typ, sha, entry_path = entries[0]
        return STATUS_FAIL, f"{entry_path} IS on {ref} ({typ} {sha[:12]})"
    return STATUS_PASS, f"git ls-tree {ref} -- {path} -> empty (absent)"


def check_pr_state(root, number, expect_state: str, repo: str | None = None):
    """PASS iff `gh pr view <number> --json state` matches expect_state; SKIP if gh is unusable."""
    if not repo:
        return STATUS_SKIP, "no --repo given (and no origin remote to derive one) - PR state not checkable"
    try:
        proc = subprocess.run(
            ["gh", "pr", "view", str(number), "--repo", str(repo), "--json", "state"],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return STATUS_SKIP, "gh not installed - PR state not checkable here"
    except subprocess.TimeoutExpired:
        return STATUS_SKIP, "gh timed out"
    if proc.returncode != 0:
        why = _first_line(proc.stderr) or f"rc={proc.returncode}"
        return STATUS_SKIP, f"gh unavailable or unauthorised ({why})"
    try:
        state = str(json.loads(proc.stdout).get("state", ""))
    except json.JSONDecodeError:
        return STATUS_SKIP, f"gh returned unparsable JSON: {proc.stdout[:80]!r}"
    if state.upper() == str(expect_state).upper():
        return STATUS_PASS, f"gh pr view {number} --repo {repo} -> state={state}"
    return STATUS_FAIL, f"gh pr view {number} --repo {repo} -> state={state}, expected {expect_state}"


def _author_set(root, sha_range: str):
    """(sorted author emails, detail) - detail carries the error when the range is unreadable."""
    rc, out, err = _git(root, ["log", "--format=%ae", sha_range])
    if rc != 0:
        return None, f"git log {sha_range} failed: {_first_line(err) or 'rc=' + str(rc)}"
    authors = sorted({line.strip() for line in out.splitlines() if line.strip()})
    return authors, ", ".join(authors) if authors else "(no commits in range)"


def check_author_set(root, sha_range: str, expect_authors):
    """PASS iff the %ae set of `git log <range>` equals expect_authors exactly."""
    authors, detail = _author_set(root, sha_range)
    if authors is None:
        return STATUS_SKIP, detail
    expected = sorted(expect_authors)
    if authors == expected:
        return STATUS_PASS, f"authors in {sha_range}: {detail} (matches expected set)"
    return STATUS_FAIL, f"authors in {sha_range}: {detail}; expected: {', '.join(expected)}"


def check_author_is_bot(root, sha_range: str, expect_authors):
    """Same PASS criterion as check_author_set, plus a note on whether the identities are bots.

    NOTE: the manifest contract defines this kind by author-set equality, so it cannot
    distinguish human from bot authorship on its own; the bot-ness note is informational.
    """
    status, detail = check_author_set(root, sha_range, expect_authors)
    if status == STATUS_SKIP:
        return status, detail
    human_like = [a for a in expect_authors
                  if "bot" not in a.lower() and "noreply" not in a.lower()
                  and not a.lower().startswith("github-actions")]
    note = (f"; human-looking expected authors: {', '.join(human_like)}" if human_like
            else "; every expected author looks like a machine identity")
    return status, detail + note


CHECKS = {
    "commit_ancestor_of_main": lambda root, ref, repo, c: check_commit_ancestor_of_main(root, c["sha"], ref),
    "commit_on_any_origin_ref": lambda root, ref, repo, c: check_commit_on_any_origin_ref(root, c["sha"]),
    "commit_exists": lambda root, ref, repo, c: check_commit_exists(root, c["sha"]),
    "commit_absent": lambda root, ref, repo, c: check_commit_absent(root, c["sha"]),
    "path_on_main": lambda root, ref, repo, c: check_path_on_main(root, c["path"], c.get("blob_prefix"), ref),
    "path_absent_from_main": lambda root, ref, repo, c: check_path_absent_from_main(root, c["path"], ref),
    "pr_state": lambda root, ref, repo, c: check_pr_state(root, c["number"], c["expect_state"], repo),
    "author_is_bot": lambda root, ref, repo, c: check_author_is_bot(root, c["sha_range"], c["expect_authors"]),
    "author_set": lambda root, ref, repo, c: check_author_set(root, c["sha_range"], c["expect_authors"]),
}


# --------------------------------------------------------------------------- #
# verdict derivation / claim evaluation
# --------------------------------------------------------------------------- #
def normalize_verdict(text) -> str | None:
    """Leading vocabulary token of a verdict string ('VERIFIED (was true)' -> 'VERIFIED')."""
    if not isinstance(text, str):
        return None
    cleaned = text.replace(MANUAL_SUFFIX, "").strip().upper()
    for token in ("NOT LANDED", "VERIFIED", "PARTIALLY", "UNVERIFIABLE"):
        if cleaned.startswith(token):
            return token
    return None


def derive_verdict(results, manual: bool = False) -> str:
    """Apply the derivation rule documented in the module docstring.

    results: iterable of (status, detail); SKIPs are dropped before deciding.
    """
    statuses = [status for status, _detail in results if status != STATUS_SKIP]
    if not statuses:
        base = "UNVERIFIABLE"
    elif all(s == STATUS_PASS for s in statuses):
        base = "VERIFIED"
    elif STATUS_PASS in statuses:
        base = "PARTIALLY"
    else:
        base = "NOT LANDED"
    return base + MANUAL_SUFFIX if manual else base


def run_claim(root, ref: str, repo: str | None, claim: dict) -> dict:
    """Run every check of one claim and derive its mechanical verdict."""
    checks = []
    for chk in claim.get("checks", []):
        kind = chk.get("kind")
        fn = CHECKS.get(kind)
        if fn is None:
            status, detail = STATUS_FAIL, f"unknown check kind {kind!r}"
        else:
            try:
                status, detail = fn(root, ref, repo, chk)
            except KeyError as exc:
                status, detail = STATUS_FAIL, f"check {kind!r} is missing required param {exc}"
        checks.append({"kind": kind, "status": status, "detail": detail, "params": {
            k: v for k, v in chk.items() if k != "kind"}})
    manual = bool(claim.get("manual"))
    computed = derive_verdict([(c["status"], c["detail"]) for c in checks], manual=manual)
    expected = claim.get("expected_verdict", "")
    return {
        "id": claim.get("id"),
        "group": claim.get("group"),
        "claimant": claim.get("claimant"),
        "summary": claim.get("summary"),
        "manual": manual,
        "manual_reason": claim.get("manual_reason"),
        "checks": checks,
        "computed_verdict": computed,
        "expected_verdict": expected,
        "agree": normalize_verdict(computed) == normalize_verdict(expected),
        "any_fail": any(c["status"] == STATUS_FAIL for c in checks),
        "any_skip": any(c["status"] == STATUS_SKIP for c in checks),
    }


def strict_violations(results) -> list[dict]:
    """Violations under --strict: non-manual disagreement, or a FAIL on an expected-VERIFIED claim."""
    bad = []
    for r in results:
        if r["manual"]:
            continue
        if not r["agree"]:
            bad.append({"id": r["id"], "why": "disagreement",
                        "computed": r["computed_verdict"], "expected": r["expected_verdict"]})
        elif r["any_fail"] and normalize_verdict(r["expected_verdict"]) == "VERIFIED":
            bad.append({"id": r["id"], "why": "check FAIL on a claim the hand report recorded as VERIFIED",
                        "computed": r["computed_verdict"], "expected": r["expected_verdict"]})
    return bad


def validate_claims(claims) -> list[str]:
    """Schema problems in the claims manifest (empty list = valid)."""
    problems = []
    if not isinstance(claims, list) or not claims:
        return ["claims must be a non-empty array"]
    seen = set()
    for i, c in enumerate(claims):
        where = f"claims[{i}]"
        if not isinstance(c, dict):
            problems.append(f"{where}: not an object")
            continue
        cid = c.get("id")
        for key in ("id", "group", "claimant", "summary", "checks", "manual", "expected_verdict"):
            if key not in c:
                problems.append(f"{where}: missing {key!r}")
        if cid in seen:
            problems.append(f"{where}: duplicate id {cid!r}")
        seen.add(cid)
        if c.get("group") not in ("A", "B"):
            problems.append(f"{where} ({cid}): group must be 'A' or 'B'")
        if not isinstance(c.get("checks"), list):
            problems.append(f"{where} ({cid}): checks must be an array")
        else:
            for j, chk in enumerate(c["checks"]):
                if not isinstance(chk, dict) or "kind" not in chk:
                    problems.append(f"{where} ({cid}) checks[{j}]: missing 'kind'")
                elif chk["kind"] not in CHECKS:
                    problems.append(f"{where} ({cid}) checks[{j}]: unsupported kind {chk['kind']!r}")
        if c.get("manual") and not c.get("checks") and not c.get("manual_reason"):
            problems.append(f"{where} ({cid}): manual claim with no checks must carry manual_reason")
        if normalize_verdict(c.get("expected_verdict")) is None:
            problems.append(f"{where} ({cid}): expected_verdict {c.get('expected_verdict')!r} "
                            f"is outside the fixed vocabulary")
    return problems


# --------------------------------------------------------------------------- #
# report rendering
# --------------------------------------------------------------------------- #
def _cell(value) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def build_report(meta: dict, results) -> str:
    """Deterministic markdown report - same meta+results always give the same bytes."""
    lines = [
        "# Peer claim verification - generated report",
        "",
        "Generated by `tools/verify_peer_claims.py`. Verdict vocabulary is fixed: "
        "**VERIFIED** / **NOT LANDED** / **PARTIALLY** / **UNVERIFIABLE**.",
        "",
        f"- generated_utc: `{meta['generated_utc']}`",
        f"- origin/main sha: `{meta['origin_main']}`",
        f"- ref used: `{meta['ref']}`",
        f"- claims file: `{meta['claims_path']}` (sha256 `{meta['claims_sha256']}`)",
        f"- claims: {meta['n_claims']} total, {meta['n_agree']} agree with the hand report, "
        f"{meta['n_disagree']} disagree ({meta['n_disagree_nonmanual']} non-manual), "
        f"{meta['n_manual']} manual",
        "",
        "| id | group | claimant | mechanical result | expected (hand report) | checks | notes |",
        "|----|-------|----------|-------------------|------------------------|--------|-------|",
    ]
    for r in results:
        counts = {}
        for c in r["checks"]:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        check_summary = (", ".join(f"{counts[k]} {k}" for k in
                                   (STATUS_PASS, STATUS_FAIL, STATUS_SKIP) if counts.get(k))
                         or "no executable checks")
        notes = []
        notes.append("agree" if r["agree"] else
                     f"DISAGREE: mechanical {normalize_verdict(r['computed_verdict'])} vs "
                     f"hand {normalize_verdict(r['expected_verdict'])}")
        if r["manual"]:
            notes.append("manual")
        for c in r["checks"]:
            if c["status"] == STATUS_SKIP:
                notes.append(f"SKIP {c['kind']}: {c['detail']}")
        lines.append(
            f"| {_cell(r['id'])} | {_cell(r['group'])} | {_cell(r['claimant'])} | "
            f"{_cell(r['computed_verdict'])} | {_cell(r['expected_verdict'])} | "
            f"{_cell(check_summary)} | {_cell('; '.join(notes))} |"
        )

    lines += ["", "## Claims that still require a human judgement", ""]
    manual = [r for r in results if r["manual"]]
    if not manual:
        lines.append("None - every claim in this manifest was decided by ref checks.")
    for r in manual:
        lines += [
            f"### {r['id']} - {r['group']} - {r['claimant']}",
            "",
            f"- Claim: {r['summary']}",
            f"- Hand report: **{r['expected_verdict']}**; mechanical: **{r['computed_verdict']}**",
            f"- Why a human is needed: {r['manual_reason'] or '(no reason recorded)'}",
        ]
        for c in r["checks"]:
            lines.append(f"  - {c['kind']} -> {c['status']}: {c['detail']}")
        lines.append("")

    lines += [
        "## What this run does NOT verify",
        "",
        "- It does not consult the COMS bus. No message traffic was read or replayed, so a claim "
        "that was only ever broadcast on COMS is neither confirmed nor refuted here.",
        "- It does not re-derive the underlying edge research. No backtests, PnL, win rates or pick "
        "quality were recomputed; only git ref reachability was measured.",
        "- A PASS is a ref-reachability result only. It says the cited object is reachable from the "
        "named ref - not that the work is correct, complete, or profitable, and not that a "
        "human-judgement verdict (ownership, wording, PARTIALLY vs NOT LANDED) is settled.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def derive_repo_slug(root) -> str | None:
    rc, out, _ = _git(root, ["remote", "get-url", "origin"])
    if rc != 0 or not out:
        return None
    match = re.search(r"github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?$", out.strip())
    return match.group("slug") if match else None


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claims", default="claims/verification_claims.json",
                    help="claims manifest (JSON); relative paths resolve against the repo root")
    ap.add_argument("--ref", default="origin/main", help="git ref the checks run against")
    ap.add_argument("--out", default="updates/peer-claim-verification-latest.md",
                    help="markdown report path (must NOT live under docs/)")
    ap.add_argument("--repo", default=None, help="owner/name for gh PR lookups (default: origin remote)")
    ap.add_argument("--json", action="store_true", help="also emit machine-readable results to --json-out")
    ap.add_argument("--json-out", default=None, help="path for the machine-readable results")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on a non-manual verdict disagreement or an unexpected check FAIL")
    ap.add_argument("--allow-dirty-ref", action="store_true",
                    help="silence the warning about uncommitted changes in the working tree")
    args = ap.parse_args(argv)

    root = find_repo_root()
    print(f"[verify_peer_claims] repo root: {root}")

    rc, _, _ = _git(root, ["rev-parse", "--git-dir"])
    if rc != 0:
        print(f"[verify_peer_claims] ERROR: not a git repository: {root}", file=sys.stderr)
        return 2

    tip = resolve_ref(root, args.ref)
    if tip is None:
        print(f"[verify_peer_claims] ERROR: cannot resolve {args.ref} in {root} "
              f"(fetch it first: git fetch origin --prune)", file=sys.stderr)
        return 2

    claims_path = Path(args.claims)
    if not claims_path.is_absolute():
        claims_path = root / claims_path
    if not claims_path.is_file():
        print(f"[verify_peer_claims] ERROR: claims file not found: {claims_path}", file=sys.stderr)
        return 2
    if args.json and not args.json_out:
        ap.error("--json requires --json-out PATH")

    if not args.allow_dirty_ref:
        rc, out, _ = _git(root, ["status", "--porcelain"])
        if out:
            print(f"[verify_peer_claims] WARNING: working tree has uncommitted changes; every "
                  f"check reads {args.ref}, never the working copy "
                  f"(pass --allow-dirty-ref to silence)")

    raw = claims_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[verify_peer_claims] ERROR: {claims_path} is not valid JSON: {exc}", file=sys.stderr)
        return 2
    claims = data.get("claims", []) if isinstance(data, dict) else data
    problems = validate_claims(claims)
    if problems:
        print(f"[verify_peer_claims] ERROR: invalid claims manifest {claims_path}:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    repo_slug = args.repo or derive_repo_slug(root)
    results = [run_claim(root, args.ref, repo_slug, claim) for claim in claims]

    violations = strict_violations(results)
    n_disagree = sum(1 for r in results if not r["agree"])
    meta = {
        "generated_utc": _now_utc(),
        "origin_main": tip,
        "ref": args.ref,
        "claims_path": str(claims_path.relative_to(root)) if claims_path.is_relative_to(root) else str(claims_path),
        "claims_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "n_claims": len(results),
        "n_agree": sum(1 for r in results if r["agree"]),
        "n_disagree": n_disagree,
        "n_disagree_nonmanual": sum(1 for r in results if not r["agree"] and not r["manual"]),
        "n_manual": sum(1 for r in results if r["manual"]),
    }

    for r in results:
        print(f"[{r['id']}] {r['computed_verdict']}  (hand: {r['expected_verdict']})"
              f"{'' if r['agree'] else '  <-- DISAGREE'}{'  [manual]' if r['manual'] else ''}")
        for c in r["checks"]:
            print(f"    {c['status']:<4} {c['kind']}: {c['detail']}")

    report = build_report(meta, results)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = root / out_path
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"[verify_peer_claims] ERROR: cannot write report {out_path}: {exc}", file=sys.stderr)
        return 2
    print(f"[verify_peer_claims] report written: {out_path}")

    if args.json_out:
        json_path = Path(args.json_out)
        payload = {"generated_utc": meta["generated_utc"], "ref": args.ref,
                   "origin_main": tip, "claims_sha256": meta["claims_sha256"],
                   "claims": results, "strict_violations": violations}
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"[verify_peer_claims] json written: {json_path}")

    print(f"[verify_peer_claims] {meta['n_claims']} claims: {meta['n_agree']} agree, "
          f"{meta['n_disagree']} disagree ({meta['n_disagree_nonmanual']} non-manual), "
          f"{meta['n_manual']} manual; strict violations: {len(violations)}")
    for v in violations:
        print(f"  VIOLATION [{v['id']}] {v['why']}: mechanical {v['computed']} vs hand {v['expected']}",
              file=sys.stderr)
    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Refuse commits that touch another agent's files, and amends of another agent's commit.

WHY THIS EXISTS
    2026-11-23, this clone: `git add <my note> && git commit --amend` was run while another
    agent committed `f1489c159a3` (goldmines vendor, 24 foreign files) onto HEAD in the gap
    between the add and the amend. The amend then rewrote THAT commit, folding my file into
    someone else's work. Nothing was pushed, so the fix was `git reset --soft`, but the rule
    "only commit your own files" was broken by a race, not by intent.

    A rule that depends on an agent remembering is not a control. Author identity cannot help:
    every agent here commits as github-actions[bot], so there is no per-agent author to check.
    Ownership must be DECLARED BY PATH (tools/agent_ownership.json) and enforced mechanically.

WHAT IT CHECKS
    commit  every staged path must be inside this agent's owned_prefixes.
    amend   EVERY file in HEAD must be inside this agent's owned_prefixes - because amending
            rewrites that commit and re-signs its content as yours.
    head    the HEAD sha must still be the one the caller started from (race detector).

USAGE
    python3 tools/git_guard_check.py --mode commit
    python3 tools/git_guard_check.py --mode amend [--head <sha>]
    python3 tools/git_guard_check.py --mode head --head <sha> --expect <sha>
    python3 tools/git_guard_check.py --mode amend --files a.md,b.md --json   # testable, no git

EXIT
    0 allow · 1 refuse · 2 configuration problem (treated as refuse by the hook)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OWNERSHIP = REPO / "tools" / "agent_ownership.json"
UNKNOWN_AGENT = "__unregistered__"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout


def load_ownership(path: Path | None = None) -> dict:
    path = Path(path) if path else OWNERSHIP
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"[guard] cannot read {path}: {exc}")
    data.setdefault("agents", {})
    data.setdefault("foreign_prefixes", [])
    data.setdefault("default_agent", UNKNOWN_AGENT)
    return data


def resolve_agent(explicit: str | None = None) -> str:
    """Env beats git config beats the declared default. Read-only, no state written."""
    if explicit:
        return explicit
    for var in ("AGENT_ID", "AGENT_GUARD_AGENT"):
        if os.environ.get(var):
            return os.environ[var].strip()
    try:
        cfg = _git("config", "--get", "agent.id").strip()
        if cfg:
            return cfg
    except subprocess.CalledProcessError:
        pass
    marker = REPO / ".git" / "agent-id"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    # NO default-to-me fallback: in a shared clone that would hand every unidentified
    # process my ownership list and block legitimate foreign commits.
    return UNKNOWN_AGENT


def classify(paths: list[str], own: list[str], foreign: list[str]) -> dict:
    """Split paths into owned / foreign-listed / unlisted. Explicit foreign wins over prefixes."""
    def hit(p: str, prefixes: list[str]) -> bool:
        return any(p == q or p.startswith(q) for q in prefixes)

    out = {"owned": [], "foreign": [], "unlisted": []}
    for p in paths:
        if hit(p, foreign):
            out["foreign"].append(p)
        elif hit(p, own):
            out["owned"].append(p)
        else:
            out["unlisted"].append(p)
    return out


def staged_files() -> list[str]:
    raw = _git("diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB")
    return [line for line in raw.splitlines() if line.strip()]


def files_in_commit(sha: str) -> list[str]:
    """Files changed by a commit (root commit handled by --root)."""
    raw = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha)
    return [line for line in raw.splitlines() if line.strip()]


def head_sha() -> str:
    return _git("rev-parse", "HEAD").strip()


def evaluate(mode: str, agent: str, ownership: dict, files: list[str] | None = None,
             expect_head: str | None = None) -> dict:
    """Pure decision function so the tests never need to mutate a repo."""
    agents = ownership.get("agents", {})
    entry = agents.get(agent)
    registered = entry is not None
    own = list((entry or {}).get("owned_prefixes", []))
    foreign = list(ownership.get("foreign_prefixes", []))

    if mode == "head":
        current = head_sha()
        ok = expect_head is None or current == expect_head
        return {"mode": mode, "agent": agent, "registered": registered, "allow": ok,
                "head": current, "expected": expect_head,
                "reason": (None if ok else
                           f"HEAD moved from {expect_head} to {current} while the guard was "
                           "running - another agent committed on this branch")}

    if files is not None:
        paths = files
    elif mode == "commit":
        paths = staged_files()
    else:                       # amend: the file list of the commit being rewritten
        paths = files_in_commit(REPO and head_sha())
    split = classify(paths, own, foreign)

    if not registered:
        would_block = split["foreign"] + split["unlisted"]
        note = ("ADVISORY ONLY: no AGENT_ID / agent.id set, so ownership cannot be attributed. "
                "Export AGENT_ID=<your agent name> to make this guard enforce.")
        if would_block:
            note += (f" Would have blocked {len(would_block)} path(s) not owned by a registered "
                     f"agent: {', '.join(would_block[:3])}")
        return {"mode": mode, "agent": agent, "registered": False, "allow": True,
                "files": paths, "split": split, "reason": note}

    blocking = split["foreign"] + split["unlisted"]
    if mode == "amend":
        ok = not blocking
        reason = None if ok else (
            f"REFUSED: --amend would rewrite HEAD, which contains {len(blocking)} file(s) this "
            f"agent does not own ({', '.join(blocking[:3])}{'...' if len(blocking) > 3 else ''}). "
            "Amending re-signs that commit's whole content as yours. Commit your own files on top "
            "instead, or reset --soft to your own commit first.")
    else:
        ok = not blocking
        reason = None if ok else (
            f"REFUSED: {len(blocking)} staged path(s) are not yours "
            f"({', '.join(blocking[:3])}{'...' if len(blocking) > 3 else ''}). Stage only your "
            "own files - a shared clone is not a staging area for other agents' work.")
    return {"mode": mode, "agent": agent, "registered": True, "allow": ok,
            "files": paths, "split": split, "reason": reason}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("commit", "amend", "head"), default="commit")
    ap.add_argument("--agent", default=None)
    ap.add_argument("--head", default=None, help="sha to inspect (amend/head modes)")
    ap.add_argument("--expect", default=None, help="sha HEAD must still equal (race detector)")
    ap.add_argument("--files", default=None,
                    help="comma-separated paths to evaluate instead of reading git (tests)")
    ap.add_argument("--repo", default=None,
                    help="repository to inspect (tests use a throwaway repo)")
    ap.add_argument("--ownership", default=None,
                    help="ownership file to read (tests point at the real one)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global REPO, OWNERSHIP
    if args.repo:
        REPO = Path(args.repo).resolve()
        OWNERSHIP = REPO / "tools" / "agent_ownership.json"
    if args.ownership:
        OWNERSHIP = Path(args.ownership).resolve()

    if os.environ.get("AGENT_GUARD_ALLOW") == "1":
        print("[guard] ALLOWED BY OVERRIDE (AGENT_GUARD_ALLOW=1). This is logged on purpose: "
              "an override is a reviewed exception, never a routine one.", file=sys.stderr)
        return 0

    ownership = load_ownership()
    agent = resolve_agent(args.agent)
    files = [f for f in args.files.split(",") if f] if args.files else None

    if args.mode == "amend" and files is None:
        target = args.head or head_sha()
        files = files_in_commit(target)
        result = evaluate("amend", agent, ownership, files=files)
        result["target"] = target
    elif args.mode == "head":
        result = evaluate("head", agent, ownership, expect_head=args.expect)
    else:
        result = evaluate("commit", agent, ownership, files=files)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result.get("reason"):
        print(f"[guard] {result['reason']}", file=sys.stderr if not result["allow"] else sys.stdout)
    else:
        print(f"[guard] {args.mode} allowed for {agent} "
              f"({len(result.get('files', []))} file(s) checked)")

    if args.mode == "amend" and files is not None and not result["allow"]:
        print("[guard] HEAD's file list, for the record:", file=sys.stderr)
        split = result["split"]
        for p in split["foreign"][:10]:
            print(f"[guard]   foreign-listed: {p}", file=sys.stderr)
        for p in split["unlisted"][:10]:
            print(f"[guard]   unlisted      : {p}", file=sys.stderr)
    return 0 if result["allow"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

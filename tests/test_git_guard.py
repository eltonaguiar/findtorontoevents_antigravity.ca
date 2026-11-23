"""The commit guard must actually refuse, not just report.

Every test builds a THROWAWAY git repo in tmp_path: no dependence on this clone's history, no
mutation of the shared working tree, no network. The ownership file is the real one, passed
explicitly with --ownership, so the policy under test is the policy that ships.

The failure this guards against happened here on 2026-11-23: another agent committed 24 foreign
files onto HEAD between `git add` and `git commit --amend`, and the amend rewrote their commit.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "tools" / "git_guard_check.py"
OWNERSHIP = REPO_ROOT / "tools" / "agent_ownership.json"
AGENT = "freebuff-deepseek-v4-flash"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> dict:
    """Two commits: THEIR foreign commit first, then MY commit on top."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "bot@example.com")
    _git(r, "config", "user.name", "github-actions[bot]")
    _git(r, "config", "commit.gpgsign", "false")

    (r / "investments" / "goldmines").mkdir(parents=True)
    (r / "investments" / "goldmines" / "index.html").write_text("<html>theirs</html>")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "goldmines: vendor the source")
    theirs = _git(r, "rev-parse", "HEAD")

    (r / "reports").mkdir()
    (r / "reports" / "mine.md").write_text("my report")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "docs: my note")
    mine = _git(r, "rev-parse", "HEAD")
    return {"path": r, "theirs": theirs, "mine": mine}


def _guard(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.pop("AGENT_GUARD_ALLOW", None)
    e["AGENT_ID"] = AGENT
    if env:
        e.update(env)
    return subprocess.run([sys.executable, str(GUARD), "--repo", str(repo),
                           "--ownership", str(OWNERSHIP), *args],
                          capture_output=True, text=True, env=e)


# ── the incident itself ─────────────────────────────────────────────────────
def test_amend_of_foreign_head_is_refused(repo):
    """The 2026-11-23 incident: amending a commit full of another agent's files."""
    out = _guard(repo["path"], "--mode", "amend", "--head", repo["theirs"])
    assert out.returncode == 1, out.stdout + out.stderr
    assert "REFUSED" in out.stderr
    assert "goldmines" in out.stderr


def test_amend_of_own_head_is_allowed(repo):
    out = _guard(repo["path"], "--mode", "amend", "--head", repo["mine"])
    assert out.returncode == 0, out.stdout + out.stderr


def test_amend_uses_head_when_no_sha_given(repo):
    """Default target is HEAD, so a race that moves HEAD changes the verdict."""
    assert _guard(repo["path"], "--mode", "amend").returncode == 0   # HEAD is mine
    _git(repo["path"], "reset", "-q", "--soft", repo["theirs"])      # now HEAD is theirs
    assert _guard(repo["path"], "--mode", "amend").returncode == 1


# ── plain commits ───────────────────────────────────────────────────────────
def test_commit_refuses_foreign_staged_file(repo):
    (repo["path"] / "investments" / "goldmines" / "extra.html").write_text("x")
    _git(repo["path"], "add", "investments/goldmines/extra.html")
    out = _guard(repo["path"], "--mode", "commit")
    assert out.returncode == 1
    assert "REFUSED" in out.stderr


def test_commit_allows_own_staged_file(repo):
    (repo["path"] / "reports" / "second.md").write_text("y")
    _git(repo["path"], "add", "reports/second.md")
    assert _guard(repo["path"], "--mode", "commit").returncode == 0


# ── policy edges ────────────────────────────────────────────────────────────
def test_unregistered_agent_warns_but_never_blocks(repo):
    out = _guard(repo["path"], "--mode", "amend", "--head", repo["theirs"], "--agent", "ghost")
    assert out.returncode == 0
    payload = json.loads(_guard(repo["path"], "--mode", "amend", "--head", repo["theirs"],
                               "--agent", "ghost", "--json").stdout)
    assert payload["registered"] is False and payload["allow"] is True


def test_head_moved_is_refused(repo):
    out = _guard(repo["path"], "--mode", "head", "--expect", "0" * 40)
    assert out.returncode == 1
    assert "HEAD moved" in out.stderr


def test_head_unchanged_is_allowed(repo):
    assert _guard(repo["path"], "--mode", "head", "--expect", repo["mine"]).returncode == 0


def test_override_is_honoured_but_announced(repo):
    out = _guard(repo["path"], "--mode", "amend", "--head", repo["theirs"],
                 env={"AGENT_GUARD_ALLOW": "1"})
    assert out.returncode == 0
    assert "OVERRIDE" in out.stderr


def test_missing_ownership_file_is_an_error_not_a_pass(tmp_path):
    out = _guard(tmp_path, "--mode", "commit", "--ownership", str(tmp_path / "nope.json"))
    assert out.returncode != 0, "a missing ownership file must never silently allow"

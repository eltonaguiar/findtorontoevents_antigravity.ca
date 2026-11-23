"""Offline tests for tools/check_dossier_citations.py.

Deterministic and network-free: a throwaway git repo is built in tmp_path and
the checker is driven through main(). No origin remote, no gh.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_dossier_citations as cc  # noqa: E402

DOCS = "docs/audit_review_2026-11-22"


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.name", "Test Bot", cwd=repo)
    _run("git", "config", "user.email", "test@example.com", cwd=repo)
    for name, content in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _run("git", "add", "-A", cwd=repo)
    _run("git", "commit", "-q", "-m", "fixture", cwd=repo)
    return repo


def _base_files() -> dict[str, str]:
    return {
        f"{DOCS}/01_CRYPTO.md": (
            "# CRYPTO\n\n"
            "The ledger is [SRC: reports/class_metrics.json:12].\n"
            "Costs come from `tools/cost_measure.py`.\n"
            "Also see [the sibling](reports/class_metrics.md).\n"
            "A live surface `/audit/data/dashboard_data.json` is not a repo path.\n"
            "A bare name `audit2.js` and a glob `_raw/audit*_page.html` are ignored.\n"
        ),
        f"{DOCS}/_reviews/01_CRYPTO.review.md": (
            "Nested review citing [SRC: reports/nested_only.json].\n"
        ),
        "reports/class_metrics.json": "{}\n",
        "reports/class_metrics.md": "sibling\n",
        "reports/nested_only.json": "{}\n",
        "tools/cost_measure.py": "print('x')\n",
    }


def test_resolvable_citations_pass(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, _base_files())
    assert cc.main(["--root", str(repo), "--ref", "HEAD"]) == 0


def test_unresolvable_citation_fails(tmp_path: Path) -> None:
    files = _base_files()
    files[f"{DOCS}/02_EQUITY.md"] = "Broken: [SRC: reports/ghost.json:1]\n"
    repo = _make_repo(tmp_path, files)
    assert cc.main(["--root", str(repo), "--ref", "HEAD"]) == 1


def test_allow_missing_exempts_annotated_path(tmp_path: Path) -> None:
    files = _base_files()
    files[f"{DOCS}/02_EQUITY.md"] = "Broken: [SRC: reports/ghost.json:1]\n"
    repo = _make_repo(tmp_path, files)
    assert cc.main(["--root", str(repo), "--ref", "HEAD"]) == 1
    assert cc.main(["--root", str(repo), "--ref", "HEAD", "--allow-missing", "reports/ghost.json"]) == 0


def test_nested_reviews_are_scanned(tmp_path: Path) -> None:
    files = _base_files()
    del files["reports/nested_only.json"]  # only cited from _reviews/
    repo = _make_repo(tmp_path, files)
    assert cc.main(["--root", str(repo), "--ref", "HEAD"]) == 1


def test_bad_ref_is_usage_error(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, _base_files())
    assert cc.main(["--root", str(repo), "--ref", "no-such-ref"]) == 2


def test_is_repo_path_rejects_non_repo_tokens() -> None:
    for token in ("/audit/data/x.json", "./data/x.json", "manifest:entries",
                  "*.py", "_raw/audit*_page.html", "audit2.js", "https://x.y/z.md"):
        assert not cc.is_repo_path(token), token
    for token in ("reports/a.json", "tools/b.py", "docs/c/d.md"):
        assert cc.is_repo_path(token), token

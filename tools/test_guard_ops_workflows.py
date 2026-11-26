#!/usr/bin/env python3
"""Unit tests for tools/guard_ops_workflows.py. Run: python3 tools/test_guard_ops_workflows.py"""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_ops_workflows import (  # noqa: E402
    DEFAULT_PREFIX,
    automated_commits,
    evaluate,
    filter_protected,
    is_automated,
    is_protected,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
# The real incident: "Alpha Engine FAST: 2026-11-26 08:12 [AUTO] [skip ci]" deleted the
# ops-* workflows along with 571 other files.
INCIDENT = "26dd4f9df832"


def _have(rev: str) -> bool:
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{rev}^{{commit}}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


class AutomationDetectionTest(unittest.TestCase):
    def test_github_actions_bot_name(self):
        self.assertTrue(
            is_automated(
                "github-actions[bot]",
                "41898282+github-actions[bot]@users.noreply.github.com",
                "Alpha Engine FAST: 2026-11-26 08:12 [AUTO] [skip ci]",
            )
        )

    def test_bot_name_without_message_marker(self):
        self.assertTrue(is_automated("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com", "Bump x"))

    def test_bot_email_without_bot_name(self):
        self.assertTrue(is_automated("Elton Aguiar", "github-actions[bot]@users.noreply.github.com", "nightly"))

    def test_auto_subject_marker(self):
        self.assertTrue(is_automated("Elton Aguiar", "eltonaguiar@users.noreply.github.com", "picks [skip ci]"))

    def test_human_commit_is_not_automated(self):
        self.assertFalse(
            is_automated("Elton Aguiar", "eltonaguiar@users.noreply.github.com", "Restore the php52 gate")
        )

    def test_automated_commits_filters(self):
        commits = [
            ("a", "Elton Aguiar", "eltonaguiar@users.noreply.github.com", "human work"),
            ("b", "github-actions[bot]", "x@users.noreply.github.com", "update [skip ci]"),
        ]
        self.assertEqual([c[0] for c in automated_commits(commits)], ["b"])


class ProtectionTest(unittest.TestCase):
    def test_protected_prefix_root_only(self):
        self.assertTrue(is_protected(".github/workflows/ops-install-laptop-key.yml"))
        self.assertTrue(is_protected(".github/workflows/ops-windows-sshd.yaml"))
        self.assertFalse(is_protected(".github/workflows/php52-compat-lint.yml"))
        self.assertFalse(is_protected(".github/workflows/nested/ops-thing.yml"))
        self.assertFalse(is_protected("ops-thing.yml"))
        self.assertFalse(is_protected(".github/workflows/ops-thing.txt"))

    def test_filter_dedupes_and_sorts(self):
        paths = [
            ".github/workflows/ops-b.yml",
            ".github/workflows/ops-a.yml",
            ".github/workflows/ops-a.yml",
            ".github/workflows/other.yml",
            "tools/ops-c.yml",
        ]
        self.assertEqual(
            filter_protected(paths),
            [".github/workflows/ops-a.yml", ".github/workflows/ops-b.yml"],
        )

    def test_prefix_is_configurable(self):
        self.assertTrue(is_protected(".github/workflows/php52-compat-lint.yml", prefix="php52-"))
        self.assertEqual(DEFAULT_PREFIX, "ops-")


class EvaluateTest(unittest.TestCase):
    def test_unreadable_range_warns_instead_of_failing(self):
        code, lines = evaluate("0" * 40, "f" * 40, cwd=REPO_ROOT)
        self.assertEqual(code, 0)
        self.assertTrue(any(line.startswith("::warning::") for line in lines))

    @unittest.skipUnless(_have(INCIDENT), f"{INCIDENT} not in this clone")
    def test_incident_range_is_a_violation(self):
        code, lines = evaluate(f"{INCIDENT}^", INCIDENT, cwd=REPO_ROOT)
        text = "\n".join(lines)
        self.assertEqual(code, 1, text)
        self.assertIn("ops-install-laptop-key.yml", text)
        self.assertIn("ops-windows-sshd.yml", text)

    @unittest.skipUnless(_have(INCIDENT), f"{INCIDENT} not in this clone")
    def test_dry_run_exits_zero(self):
        self.assertEqual(
            main(["--before", f"{INCIDENT}^", "--after", INCIDENT, "--dry-run"]),
            0,
        )

    @unittest.skipUnless(_have(INCIDENT), f"{INCIDENT} not in this clone")
    def test_all_zeroes_is_not_a_failure(self):
        self.assertEqual(main(["--before", "0" * 40, "--after", INCIDENT]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

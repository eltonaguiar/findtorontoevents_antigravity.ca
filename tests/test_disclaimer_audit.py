"""Disclaimer audit: assert every user-facing output file carries the
global "Not financial advice" disclaimer invariant.

Any file matching the user-facing glob patterns below MUST contain the
phrase "not financial advice" (case-insensitive). If a file lacks it, the
task is considered failed per the global invariant.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The exact canonical disclaimer line (the audit matches it case-insensitively).
DISCLAIMER_LINE = (
    "*Not financial advice. Research/educational only. "
    "Past performance does not guarantee future results.*"
)

# Case-insensitive phrase that must appear in every user-facing file.
DISCLAIMER_RE = re.compile(r"not financial advice", re.IGNORECASE)

# File patterns considered user-facing. These output user-visible content:
# HTML dashboards, JSON payloads (consumed by dashboards), and Markdown reports.
USER_FACING_GLOBS = (
    "audit_dashboard/*.html",
    "audit_dashboard/data/*.json",
    "updates/*.md",
    "reports/*.md",
)


def user_facing_files():
    """Return all user-facing files matching the configured glob patterns."""
    files = set()
    for pattern in USER_FACING_GLOBS:
        files.update(str(p) for p in REPO_ROOT.glob(pattern))
    return sorted(files)


def test_all_user_facing_files_contain_disclaimer():
    """Every user-facing file must include the 'Not financial advice' phrase."""
    missing = []
    for rel in user_facing_files():
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        if not DISCLAIMER_RE.search(text):
            missing.append(rel)

    assert not missing, (
        "User-facing files missing the 'Not financial advice' disclaimer "
        f"({len(missing)} total):\n"
        + "\n".join(f"  - {m}" for m in missing)
    )

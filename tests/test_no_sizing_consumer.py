"""Contract test — operator_review_today.json isolation discipline.

Background
----------
``audit_dashboard/data/operator_review_today.json`` is a hand-curated DAILY sidecar
("operator-review-only" surface). The schema contract on the payload itself reads::

    "_schema_note": "...Read-only to all sizing/sync paths: every config path
                     that would treat this as a sizing surface must check
                     operator_review_only=true and refuse to ingest."

That contract is currently a docstring — Python has no way to enforce it. This
test enforces it pre-merge so a future ``tools/consume_picks.py`` (or any *.py under
``tools/``, ``audit_trail/``, ``alpha_engine/``) that silently re-ingests the sidecar
as a sizing source FAILS the test instead of shipping to production.

The contract — two acceptable signals in a consumer candidate:

1. The file references the guard flag ``operator_review_only`` somewhere (the
   ``operator_review_only == true`` gate proxy), OR
2. The file carries an explicit ``# allowed: operator-review consumer`` comment
   on its own line (a human-acknowledged override — used for the writer, the
   dashboard JS, manual debug scripts, etc.)

A file that reads ``operator_review_today.json`` and carries neither signal is
flagged as an **unguarded consumer** and the test fails. The papercut this fixes
came up in the operator-review code-review's Q7c.

Cron-mode fail-closed (added 2026-06-22; papercut #2 from the same review)
--------------------------------------------------------------------------
When ``OPERATOR_REVIEW_CRON_MODE=1`` is set in the env, the workflow's
"Run contract tests" step runs this file in fail-closed mode: a missing
sidecar AFTER the build step ran becomes a ``pytest.fail()`` (not a
``pytest.skip()``). Local pytest runs (env unset) keep the developer-
friendly skip path so a local run on a tree without the build is not a
false-negative. The env var is set ONLY at the contract-test step's env
block (not workflow-env, not job-env) so other test jobs in the same
repo are NOT affected. See the ``CRON_MODE`` constant below + the
inline cron branch in
``test_sidecar_payload_carries_required_contract_keys``.

See:
- ``audit_dashboard/data/operator_review_today.json`` for the sidecar + its
  ``_schema_note`` field.
- ``updates/2026-06-22-operator-review-today-panel.md`` §"Contract enforcement".
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Configuration — keep this list narrow; only writers and self may be exempt. #
# --------------------------------------------------------------------------- #

REPO = Path(__file__).resolve().parent.parent

# Scan roots: any *.py here that reads the sidecar is a consumer candidate.
SCAN_ROOTS = [
    REPO / "tools",
    REPO / "audit_trail",
    REPO / "alpha_engine",
]

# Files exempt from the scan. Two legitimate categories today:
#   1. The writer (build script — it WRITES the sidecar, never reads it back as
#      a sizing source, but the sidecar's filename literal appears in source).
#   2. The test file itself (it necessarily mentions both strings).
EXEMPT_BASENAMES = {
    "build_operator_review_today.py",   # writer — produces the sidecar
    "test_no_sizing_consumer.py",       # self — this file
}

# Cache & generated artifacts we never want to scan.
EXEMPT_SUFFIX_PARTS = ("__pycache__", ".pyc")

# Contract signals.
SIDECAR_FILENAME = "operator_review_today.json"
GUARD_FLAG = "operator_review_only"
# Accept the marker as a line-leading OR inline trailing comment. Anchored
# on the literal `#` and word-boundary `consumer\b` so typos fail loudly.
ALLOW_COMMENT_RE = re.compile(
    r"#\s*allowed:\s*operator-review\s+consumer\b"
)
SIDECAR_CONTRACT_KEYS_REQUIRED = ("_schema_note", "operator_review_only")

# Cron-mode gate: when the workflow's "Run contract tests" step sets
# OPERATOR_REVIEW_CRON_MODE=1 in its env block, a missing sidecar AFTER
# the build step ran is a HARD regression. The inline cron branch in
# test_sidecar_payload_carries_required_contract_keys converts the
# developer-friendly pytest.skip() into a hard pytest.fail() so the
# workflow contract step stops before the commit step can run.
# Local pytest runs (env unset) keep the skip-friendly default so a
# developer can run this contract test without first running the build.
# Wired in .github/workflows/operator-review-today.yml step
# "Run contract tests (fail-closed on skip + missing-sidecar)".
#
# COVERAGE LIMITATION: this constant + the inline pytest.fail() in
# test_sidecar_payload_carries_required_contract_keys ONLY catches the one
# known skip (missing sidecar). If a future maintainer adds a SECOND
# pytest.skip() (e.g. @pytest.mark.skip(reason="WIP")) to this file, it
# will silently pass through the workflow. This file is a contract test,
# not a feature test bed — any future skip here MUST be coordinated with
# the contract owner OR replaced with explicit pytest.fail() in cron mode.
CRON_MODE = os.environ.get("OPERATOR_REVIEW_CRON_MODE", "") == "1"


# --------------------------------------------------------------------------- #
# Detection helpers — substring/line-based; deliberately NOT AST, because the  #
# contract is about human-readable intent (the gate proxy name is the signal). #
# --------------------------------------------------------------------------- #

def _consumes_sidecar(content: str) -> bool:
    """True if the file opens AND reads the operator_review_today.json sidecar.

    Both the filename substring AND a loader-intent pattern must appear in the
    same file. Pure docstring-mentions (e.g., explaining the sidecar's role in
    prose) do NOT qualify — this rejects false positives where the substring
    appears only in a docstring/comment with no actual read.
    """
    if SIDECAR_FILENAME not in content:
        return False
    intent_patterns = (
        "open(", "read_text", "read_bytes",  # pathlib / Pathlib-style read
        "json.load", "json.loads",             # most-common sidecar consumer
        "yaml.safe_load", "yaml.load",         # alternate config loader
        "tomllib.load",                         # stdlib py3.11+
        ".load(", ".loads(",                    # generic pickle/csv/etc.
    )
    return any(pat in content for pat in intent_patterns)


def _carries_guard(content: str) -> bool:
    """True if the file references the operator_review_only gate flag
    anywhere in source — as a name, attribute access, or string literal."""
    return GUARD_FLAG in content


def _carries_allow_marker(content: str) -> bool:
    """True if the file carries an explicit `# allowed: operator-review
    consumer` marker — line-leading OR trailing inline-comment.

    The pattern is anchored on the literal `#`, on a word boundary after
    `consumer`, and tolerates inline trailing comments (e.g., after code).
    Strict-enough to reject typos; loose-enough to accept real usage.
    """
    return bool(ALLOW_COMMENT_RE.search(content))


def _is_exempt(path: Path) -> bool:
    """Exempt test self + writer + cache artifacts."""
    if path.name in EXEMPT_BASENAMES:
        return True
    if any(part in EXEMPT_SUFFIX_PARTS for part in path.parts):
        return True
    return False


def _scan_files():
    """Yield every scanned-eligible *.py under SCAN_ROOTS."""
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if not path.is_file():
                continue
            if _is_exempt(path):
                continue
            yield path


# --------------------------------------------------------------------------- #
# Pytest test functions.                                                      #
# --------------------------------------------------------------------------- #

def test_no_unguarded_consumer_in_scan_roots():
    """ANY *.py under tools/ + audit_trail/ + alpha_engine/ that opens
    operator_review_today.json MUST also reference the operator_review_only
    gate flag OR carry the explicit `# allowed: operator-review consumer`
    marker on its own line. Otherwise it is an UNGUARDED consumer and the
    test fails — surfacing the violation in the merge queue."""
    violations: list[str] = []

    for path in _scan_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Non-text files, symlinks, unreadable — skip.
            continue

        if not _consumes_sidecar(content):
            continue

        if _carries_allow_marker(content):
            continue

        if _carries_guard(content):
            continue

        violations.append(path.relative_to(REPO).as_posix())

    assert not violations, (
        "Unguarded consumers of operator_review_today.json detected. "
        "Every *.py that opens the sidecar under {tools/, audit_trail/, "
        "alpha_engine/} must EITHER reference the `operator_review_only` "
        "gate-flag string (anywhere in the file) OR carry a line reading "
        "exactly `# allowed: operator-review consumer` (human-acknowledged "
        "override). Either add the guard reference, or add the override "
        "comment, or — if the read is no longer needed — remove the read. "
        f"Violations: {violations}"
    )


def test_sidecar_payload_carries_required_contract_keys():
    """Mirror check on the sidecar itself: the payload must carry the
    `_schema_note` AND `operator_review_only` fields — without these, the
    _schema_note docstring alone cannot enforce the contract on consumers."""
    sidecar_path = REPO / "audit_dashboard" / "data" / "operator_review_today.json"

    if not sidecar_path.exists():
        # Cron-mode (env OPERATOR_REVIEW_CRON_MODE=1, set by the workflow's
        # "Run contract tests" step): the build step just ran, so the sidecar
        # MUST exist on disk. A missing sidecar in cron mode is a HARD
        # regression — fail-loud so the workflow stops BEFORE the
        # `Commit JSON back to main` step can run.
        if CRON_MODE:
            pytest.fail(
                f"HARD REGRESSION: {sidecar_path.relative_to(REPO).as_posix()} "
                "is missing AFTER the operator-review build step ran "
                "(OPERATOR_REVIEW_CRON_MODE=1). Possible causes: "
                "build script (tools/build_operator_review_today.py) "
                "failed silently to write the payload, or the workflow "
                "validate / contract / commit step sequence is wrong, "
                "or the contract test is running out of order. "
                "Investigate the build before re-running the cron. "
                "(Locally: unset OPERATOR_REVIEW_CRON_MODE to run in "
                "developer-friendly skip mode.)"
            )
        # Local non-cron mode: developer-friendly skip — the build hasn't
        # run yet; the cron lands the sidecar at 07:00 UTC.
        pytest.skip(
            f"{sidecar_path.relative_to(REPO).as_posix()} not yet produced; "
            "the operator-review cron at 07:00 UTC will land it. "
            "(unset OPERATOR_REVIEW_CRON_MODE to suppress the cron-mode "
            "fail-closed path.)"
        )

    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))

    missing = [k for k in SIDECAR_CONTRACT_KEYS_REQUIRED if k not in payload]
    assert not missing, (
        f"{sidecar_path.relative_to(REPO).as_posix()} is missing required "
        f"contract keys: {missing}. Both `_schema_note` (human-readable "
        "contract) and `operator_review_only` (machine-readable gate flag) "
        "are required — the test_no_unguarded_consumer_in_scan_roots test "
        "above would have nothing to verify against."
    )

    # The machine-readable gate flag must be a boolean True. If a refactor
    # accidentally stringifies it, consumers checking truthiness alone are OK
    # but operators reading the file by eye are misled.
    assert payload["operator_review_only"] is True, (
        f"operator_review_only must be a strict boolean True; got "
        f"{payload['operator_review_only']!r} instead. The fail-closed "
        "contract depends on a strict type match (not just truthiness)."
    )


def test_exempt_set_includes_writer_and_self():
    """Sanity guard: the EXEMPT_BASENAMES table must include the writer
    (build_operator_review_today.py) and the test file itself — otherwise
    the writer's OUT_PATH literal would false-positive the main test, or
    this test would flag itself."""
    today = REPO / "tests" / "test_no_sizing_consumer.py"
    writer = REPO / "tools" / "build_operator_review_today.py"

    # THIS test file's own name must be in the exempt set — otherwise self-flag.
    assert today.name in EXEMPT_BASENAMES, (
        "EXEMPT_BASENAMES must contain the test file's own name to avoid a "
        "self-flagged violation on every run."
    )

    # The writer is in the scan root and contains a path literal to the
    # sidecar; it must be exempt explicitly. If the writer is renamed in
    # the future, update this assertion + EXEMPT_BASENAMES together.
    assert writer.name in EXEMPT_BASENAMES, (
        f"EXEMPT_BASENAMES must contain {writer.name!r} (the sidecar's "
        "build script). The writer opens the sidecar's path literal to set "
        "OUT_PATH; scanning it without exemption would false-positive on "
        "every run. Either add the writer to EXEMPT_BASENAMES, or — if the "
        "writer is being retired — delete this assertion."
    )

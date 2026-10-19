"""Contract test — audit_trail/blocked_registry.json isolation discipline.

Background
----------
``audit_trail/blocked_registry.json`` is a KILL-LIST registry holding
blocked symbols + blocked source systems + probation stages + audit
summary. Hand-curated (last edit 2026-06-22). It currently carries::

    "_schema_note": "Hand-curated blocked-symbol/...; KILL-list data..."
    "blocked_registry_only": true

The payload encodes VERDICT data — never a sizing signal. The schema
contract is the ``blocked_registry_only: true`` gate flag.

See:
- ``audit_trail/blocked_registry.json`` for the payload
- ``tools/blocked_symbol_review_monitor.py`` for the only confirmed
  Python consumer — it carries the `# allowed: blocked-registry
  consumer` marker so this contract test does not false-positive.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

SCAN_ROOTS = [
    REPO / "tools",
    REPO / "audit_trail",
    REPO / "alpha_engine",
]

EXEMPT_BASENAMES = {
    # No automated writer — registry is hand-curated. The only Python
    # consumer is the review monitor, which carries the allow-marker.
    "blocked_symbol_review_monitor.py",          # monitor (allow-marker)
    "test_no_blocked_registry_consumer.py",      # self
}

EXEMPT_SUFFIX_PARTS = ("__pycache__", ".pyc")

SIDECAR_FILENAME = "blocked_registry.json"
GUARD_FLAG = "blocked_registry_only"
ALLOW_COMMENT_RE = re.compile(
    r"#\s*allowed:\s*blocked[_-]registry\s+consumer\b"
)
SIDECAR_CONTRACT_KEYS_REQUIRED = ("_schema_note", "blocked_registry_only")

CRON_MODE = os.environ.get("BLOCKED_REGISTRY_CRON_MODE", "") == "1"


def _consumes_sidecar(content: str) -> bool:
    if SIDECAR_FILENAME not in content:
        return False
    intent_patterns = (
        "open(", "read_text", "read_bytes",
        "json.load", "json.loads",
        "yaml.safe_load", "yaml.load",
        "tomllib.load",
        ".load(", ".loads(",
    )
    return any(pat in content for pat in intent_patterns)


def _carries_guard(content: str) -> bool:
    return GUARD_FLAG in content


def _carries_allow_marker(content: str) -> bool:
    return bool(ALLOW_COMMENT_RE.search(content))


def _is_exempt(path: Path) -> bool:
    if path.name in EXEMPT_BASENAMES:
        return True
    if any(part in EXEMPT_SUFFIX_PARTS for part in path.parts):
        return True
    return False


def _scan_files():
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if not path.is_file():
                continue
            if _is_exempt(path):
                continue
            yield path


def test_no_unguarded_consumer_in_scan_roots():
    violations: list[str] = []
    for path in _scan_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not _consumes_sidecar(content):
            continue
        if _carries_allow_marker(content):
            continue
        if _carries_guard(content):
            continue
        violations.append(path.relative_to(REPO).as_posix())

    assert not violations, (
        "Unguarded consumers of audit_trail/blocked_registry.json detected. "
        "Every *.py that opens the registry must EITHER reference "
        "`blocked_registry_only` OR carry a line reading exactly "
        "`# allowed: blocked-registry consumer` (or underscore variant). "
        f"Violations: {violations}"
    )


def test_sidecar_payload_carries_required_contract_keys():
    sidecar_path = REPO / "audit_trail" / SIDECAR_FILENAME

    if not sidecar_path.exists():
        if CRON_MODE:
            pytest.fail(
                f"HARD REGRESSION: {sidecar_path.relative_to(REPO).as_posix()} "
                "is missing AFTER the registry-curl step ran "
                "(BLOCKED_REGISTRY_CRON_MODE=1). The registry is hand-curated; "
                "this is a sign the repo has lost the curated file."
            )
        pytest.skip(
            f"{sidecar_path.relative_to(REPO).as_posix()} not present in "
            "this checkout. The registry is hand-curated; restore from VCS or "
            "the operator-curated master."
        )

    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))

    missing = [k for k in SIDECAR_CONTRACT_KEYS_REQUIRED if k not in payload]
    assert not missing, (
        f"{sidecar_path.relative_to(REPO).as_posix()} is missing required "
        f"contract keys: {missing}. Both `_schema_note` and "
        "`blocked_registry_only` are required."
    )

    assert payload["blocked_registry_only"] is True, (
        "blocked_registry_only must be a strict boolean True; got "
        f"{payload['blocked_registry_only']!r} instead."
    )


def test_exempt_set_includes_monitor_and_self():
    today = REPO / "tests" / "test_no_blocked_registry_consumer.py"
    monitor = REPO / "tools" / "blocked_symbol_review_monitor.py"
    assert today.name in EXEMPT_BASENAMES
    assert monitor.name in EXEMPT_BASENAMES, (
        "EXEMPT_BASENAMES must contain "
        f"{monitor.name!r} (the registry's only Python consumer; it carries "
        "the allow-marker so this test does not false-positive on the "
        "legitimate monitor read)."
    )

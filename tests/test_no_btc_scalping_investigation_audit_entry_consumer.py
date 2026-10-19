"""Contract test — BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json isolation discipline.

Background
----------
``audit_trail/BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json`` is a
HAND-CURATED audit investigation entry (Kimi_Code_CLI strategy
verification audit, 2026-03-27). It carries the CLOSED audit ledger for
the BTC scalping strategy replication investigation. It currently
carries::

    "_schema_note": "Hand-curated audit investigation entry ...; AUDIT ledger entry — NOT sizing input..."
    "investigation_entry_only": true

The payload encodes AUDIT entry data — never a sizing signal. There is
NO automated Python writer. The only consumers are .md summary docs
(which are themselves human-curated).

This test is a discipline guard: any future *.py under tools/, audit_trail/,
alpha_engine/ that opens this file as a sizing input will FAIL the main
contract test below (the scan guard).

See:
- ``audit_trail/BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json`` for the payload
- ``BTC_SCALPING_INTEGRATION_SUMMARY.md`` for the related human-curated report
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
    # No automated writer — entry is hand-curated.
    "test_no_btc_scalping_investigation_audit_entry_consumer.py",  # self
}

EXEMPT_SUFFIX_PARTS = ("__pycache__", ".pyc")

SIDECAR_FILENAME = "BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json"
GUARD_FLAG = "investigation_entry_only"
ALLOW_COMMENT_RE = re.compile(
    r"#\s*allowed:\s*(?:btc[_-]scalping[_-]investigation|investigation[_-]audit[_-]entry)\s+consumer\b"
)
SIDECAR_CONTRACT_KEYS_REQUIRED = ("_schema_note", "investigation_entry_only")

CRON_MODE = os.environ.get("INVESTIGATION_ENTRY_CRON_MODE", "") == "1"


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
    """ANY *.py under tools/ + audit_trail/ + alpha_engine/ that opens
    BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json MUST reference the
    investigation_entry_only gate flag OR carry the explicit
    ``# allowed: btc-scalping-investigation consumer`` (or
    ``investigation-audit-entry``) marker."""
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
        "Unguarded consumers of BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json "
        "detected. Every *.py that opens the entry under {tools/, "
        "audit_trail/, alpha_engine/} must EITHER reference "
        "`investigation_entry_only` OR carry a line reading exactly "
        "`# allowed: btc-scalping-investigation consumer` (or "
        "investigation-audit-entry). "
        f"Violations: {violations}"
    )


def test_sidecar_payload_carries_required_contract_keys():
    sidecar_path = REPO / "audit_trail" / SIDECAR_FILENAME

    if not sidecar_path.exists():
        if CRON_MODE:
            pytest.fail(
                f"HARD REGRESSION: {sidecar_path.relative_to(REPO).as_posix()} "
                "is missing AFTER an audit entry write step ran "
                "(INVESTIGATION_ENTRY_CRON_MODE=1). Investigate."
            )
        pytest.skip(
            f"{sidecar_path.relative_to(REPO).as_posix()} not in this "
            "checkout. The entry is hand-curated; restore from VCS."
        )

    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))

    missing = [k for k in SIDECAR_CONTRACT_KEYS_REQUIRED if k not in payload]
    assert not missing, (
        f"{sidecar_path.relative_to(REPO).as_posix()} is missing required "
        f"contract keys: {missing}. Both `_schema_note` and "
        "`investigation_entry_only` are required."
    )

    assert payload["investigation_entry_only"] is True, (
        "investigation_entry_only must be a strict boolean True; got "
        f"{payload['investigation_entry_only']!r} instead."
    )


def test_exempt_set_includes_self():
    """Sanity guard for the BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY contract.
    Unlike the other 4 mirror tests, the BTC entry has NO automated Python
    writer — the JSON is hand-curated (audit investigation entry by
    Kimi_Code_CLI, 2026-03-27). So the EXEMPT_BASENAMES table is just
    ``{<self>}`` (no writer to exempt). If a future maintainer adds a
    Python writer for this entry, add its basename + extend this
    function accordingly. If a future maintainer \"fixes\" the asymmetry
    by inventing a fake writer entry, they should delete this asymmetry
    note first."""
    today = REPO / "tests" / "test_no_btc_scalping_investigation_audit_entry_consumer.py"
    assert today.name in EXEMPT_BASENAMES

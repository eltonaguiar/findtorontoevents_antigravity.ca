#!/usr/bin/env python3
"""sync_dark_audit_sidecar_scan.py — one-shot scanner for the audit-dashboard
sidecar contract discipline.

Purpose
-------
Run all 5 STRONG + 2 mirrored contract tests in one bash invocation, and
**prior to any test pass/fail verdict**, directly enumerate the on-disk
state of the sidecar contracts (Section A) AND the unguarded-reader state
of the source tree (Section B). This makes the orphan-papercut visible
**before review**, not after a regression.

Background
----------
The audit-dashboard mirror contract discipline runs a separate contract
test for each sidecar (see ``tests/test_no_<foo>_consumer.py`` for each of:
operator_review_today, winner_hunt_replay, audit_surface_truth,
anti_overfit_audit, blacklist_reconciliation, blocked_registry,
btc_scalping_investigation). In dev mode the tests ``pytest.skip()`` when
the sidecar is missing — convenient for the contributor, but it means a
sidecar that's missing its ``_schema_note`` + ``<X>_only`` gate flag at
review-time shows up as a "skipped" not a "failed". This script wraps the
tests with a pre-flight scan that does not skip — the missing-flag case
surfaces as a Section A FAIL **even when the sidecar does NOT yet exist
in the checkout** it surfaces as a "sidecar missing on disk" — so the
operator sees the orphan *before* they fire the cron.

Four sections, one report:

- **Section A — flag-on-disk check.** For each of the 7 contracts, parse
  the sidecar JSON (if present) and verify it carries BOTH
  ``_schema_note`` AND the per-contract gate flag (``<X>_only: True``).
  State-by-state: PRESENT+FLAG-OK | PRESENT+FLAG-MISSING | MISSING.

- **Section B — live reader scan.** For each contract, walk
  ``tools/`` + ``audit_trail/`` + ``alpha_engine/``, find every ``*.py``
  that opens the sidecar (filename substring AND a loader-intent pattern
  BOTH present), and verify it EITHER references the gate flag OR carries
  the ``# allowed: <kebab>-consumer`` allow-marker. This is the orphan-
  reader enumeration — exactly the test logic, but run live at the
  filesystem level so the violations show as a list, not as a pytest
  assertion-message blob.

- **Section C — pytest contract summary.** Spawn ``python3 -m pytest
  tests/test_no_<foo>_consumer.py --tb=line -q`` per contract in
  parallel (ThreadPoolExecutor, max-workers=7) and capture
  pass/fail/skip counts from stdout. This is the authoritative cross-
  check: if Section B says "no violations" but Section C fails (or vice
  versa), the cross-reference surfaces the mismatch.

- **Section D — cross-reference.** Per contract: combine A+B+C findings
  into a single status line so the operator can see the full picture in
  one table.

Output
------
Default: human-readable text with status-box ASCII framing.

``--json``: machine-readable envelope (per-contract status + global
summary) for CI integration.

``--contract <name>``: scope to a single contract for fast iteration.

``--no-pytest``: skip Section C (pure pre-flight scan; useful when the
test files themselves are the subject of an edit).

Exit codes
----------
- ``0`` each section is green per its own contract (sidecar flag OK or
      missing-but-flag-undefined; no unguarded readers; pytest passes)
- ``1`` any contract has a real regression in B or C (the contract discipline
      is violated by a consumer or by the sidecar flag removal)
- ``2`` the scan itself errored (e.g., sidecar JSON unparseable, manifest
      typo)

Cron-mode usage
--------------
For cron-mode fail-closed (the same pattern used in each
``tests/test_no_<foo>_consumer.py``), set ``ALL_SIDECAR_CRON_MODE=1`` so
Section A treats a MISSING sidecar (after the build step ran) as a HARD
regression rather than a soft "missing on dev machine". Local runs keep
the developer-friendly default.

See:
- ``tests/test_no_sizing_consumer.py`` — the canonical pattern this
  script mirrors
- ``tests/test_no_<foo>_consumer.py`` x7 — the 7 contract tests
- ``audit_dashboard/data/<sidecar>.json`` — the sidecar contracts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #

REPO = Path(__file__).resolve().parent.parent

# Scan roots: any *.py here that reads a sidecar is a consumer candidate.
# Mirrors the SCAN_ROOTS in each test file.
SCAN_ROOTS = [
    REPO / "tools",
    REPO / "audit_trail",
    REPO / "alpha_engine",
]

# Cache & generated artifacts we never want to scan.
EXEMPT_SUFFIX_PARTS = ("__pycache__", ".pyc")

# Cron-mode gate: when the workflow that wraps ALL these contracts sets
# ALL_SIDECAR_CRON_MODE=1 in its env block (e.g., a unified
# sync-dark-audit-sidecar-scan workflow that runs after every cron
# rebuild), the cron-mode FAIL-CLOSED pattern from each individual test
# propagates into Section A: a missing sidecar on cron machines is a
# HARD regression, not a "missing in dev checkout" skip. Local runs (env
# unset) keep the soft-missing default.
ALL_CRON_MODE = os.environ.get("ALL_SIDECAR_CRON_MODE", "") == "1"


# --------------------------------------------------------------------------- #
# Contract manifest — the SINGLE SOURCE OF TRUTH for which sidecars this      #
# script scans. Adding a new mirror contract = adding one entry here + the   #
# corresponding tests/test_no_<foo>_consumer.py file.                         #
# --------------------------------------------------------------------------- #

# Loader-intent patterns: a file that mentions the sidecar filename MUST
# also exhibit one of these to count as a "consumer". Pure prose mentions
# in docstrings don't qualify. Mirrors _consumes_sidecar() in the tests.
_LOADER_INTENT = (
    "open(", "read_text", "read_bytes",
    "json.load", "json.loads",
    "yaml.safe_load", "yaml.load",
    "tomllib.load",
    ".load(", ".loads(",
)


def _build_contracts() -> list[dict[str, Any]]:
    """Build the contract manifest. Implemented as a function so the
    REPO-relative paths can be resolved without module-level side-effects
    when this file is imported by tests or other tools."""
    return [
        # ------------------------------------------------------------------ #
        # Existing 2 (mirrored from operations/sister-cron work)            #
        # ------------------------------------------------------------------ #
        {
            "name": "operator_review_today",
            "sidecar": REPO / "audit_dashboard/data/operator_review_today.json",
            "flag_key": "operator_review_only",
            "marker_kebab": "operator-review",
            "test_file": REPO / "tests/test_no_sizing_consumer.py",
            "writer": REPO / "tools/build_operator_review_today.py",
        },
        {
            "name": "winner_hunt_replay",
            "sidecar": REPO / "audit_dashboard/data/winner_hunt_replay_payload.json",
            "flag_key": "winner_hunt_replay_only",
            "marker_kebab": "winner-hunt-replay",
            "test_file": REPO / "tests/test_no_winner_hunt_replay_consumer.py",
            "writer": REPO / "tools/build_winner_hunt_replay.py",
        },
        # ------------------------------------------------------------------ #
        # 5 STRONG-candidate mirror contracts                                #
        # ------------------------------------------------------------------ #
        {
            "name": "audit_surface_truth",
            "sidecar": REPO / "audit_dashboard/data/audit_surface_truth.json",
            "flag_key": "audit_surface_truth_only",
            "marker_kebab": "audit-surface-truth",
            "test_file": REPO / "tests/test_no_audit_surface_truth_consumer.py",
            "writer": REPO / "tools/build_audit_surface_truth.py",
        },
        {
            "name": "anti_overfit_audit",
            "sidecar": REPO / "audit_dashboard/data/anti_overfit_audit.json",
            "flag_key": "anti_overfit_audit_only",
            "marker_kebab": "anti-overfit-audit",
            "test_file": REPO / "tests/test_no_anti_overfit_audit_consumer.py",
            "writer": REPO / "tools/anti_overfit_audit_sidecar.py",
        },
        {
            "name": "blacklist_reconciliation",
            "sidecar": REPO / "audit_dashboard/data/blacklist_reconciliation.json",
            "flag_key": "blacklist_only",
            "marker_kebab": "blacklist-reconciliation",
            "test_file": REPO / "tests/test_no_blacklist_reconciliation_consumer.py",
            "writer": REPO / "tools/blacklist_reconciler.py",
        },
        {
            "name": "blocked_registry",
            "sidecar": REPO / "audit_trail/blocked_registry.json",
            "flag_key": "blocked_registry_only",
            "marker_kebab": "blocked-registry",
            "test_file": REPO / "tests/test_no_blocked_registry_consumer.py",
            # No automated writer — registry is hand-curated.
            "writer": None,
            "known_readers": [
                # The monitor carries the allow-marker.
                REPO / "tools/blocked_symbol_review_monitor.py",
            ],
        },
        {
            "name": "btc_scalping_investigation",
            "sidecar": REPO / "audit_trail/BTC_SCALPING_INVESTIGATION_AUDIT_ENTRY.json",
            "flag_key": "investigation_entry_only",
            # Two valid marker kebabs per the contract test.
            "marker_kebab": "btc-scalping-investigation",
            "marker_kebab_alt": "investigation-audit-entry",
            "test_file": REPO / "tests/test_no_btc_scalping_investigation_audit_entry_consumer.py",
            # No automated writer — entry is hand-curated.
            "writer": None,
        },
    ]


CONTRACTS = _build_contracts()


# --------------------------------------------------------------------------- #
# Section A: flag-on-disk check                                               #
# --------------------------------------------------------------------------- #

def _sidecar_flag_status(contract: dict[str, Any]) -> dict[str, Any]:
    """Parse the sidecar (if present) and report its gate-flag state.

    Returns one of:
      {"state": "OK", ...}        — sidecar present, _schema_note + flag-True
      {"state": "FLAG_MISSING", ...} — sidecar present but missing _schema_note
        or flag key, or flag is not strict True
      {"state": "MISSING", ...}  — sidecar not on disk (dev default; cron = FAIL)
      {"state": "UNPARSEABLE", ...} — sidecar present but JSON load fails
    """
    sidecar = contract["sidecar"]
    flag_key = contract["flag_key"]

    result: dict[str, Any] = {
        "contract": contract["name"],
        "sidecar": str(sidecar),
        "sidecar_exists": sidecar.exists(),
        "flag_key_required": ("_schema_note", flag_key),
        "state": "MISSING",
        "detail": "",
    }

    if not sidecar.exists():
        if ALL_CRON_MODE:
            result["state"] = "MISSING_CRON_HARD_FAIL"
            result["detail"] = (
                "sidecar not on disk in ALL_SIDECAR_CRON_MODE=1 — "
                "HARD regression; the producing cron did NOT land the file"
            )
        else:
            result["detail"] = (
                "sidecar not on this checkout's disk — the producing cron "
                "has not yet landed this file; pytest will skip in dev mode"
            )
        return result

    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        result["state"] = "UNPARSEABLE"
        result["detail"] = f"json.load failed: {type(e).__name__}: {e}"
        return result

    if not isinstance(payload, dict):
        result["state"] = "FLAG_MISSING"
        result["detail"] = (
            f"payload is not a JSON object (got {type(payload).__name__}); "
            "contract discipline requires an object envelope for _schema_note + flag"
        )
        return result

    missing_keys = [
        k for k in ("_schema_note", flag_key) if k not in payload
    ]
    if missing_keys:
        result["state"] = "FLAG_MISSING"
        result["detail"] = f"missing required keys: {missing_keys}"
        return result

    if payload[flag_key] is not True:
        result["state"] = "FLAG_MISSING"
        result["detail"] = (
            f"{flag_key} must be a strict boolean True; got "
            f"{payload[flag_key]!r}"
        )
        return result

    result["state"] = "OK"
    result["detail"] = (
        f"sidecar {sidecar.stat().st_size}-bytes; "
        f"_schema_note + {flag_key}: True present"
    )
    return result


# --------------------------------------------------------------------------- #
# Section B: live reader scan                                                 #
# --------------------------------------------------------------------------- #

def _marker_re_for(contract: dict[str, Any]) -> re.Pattern[str]:
    """Build the allow-marker regex for a contract (handles alt-kebab for BTC)."""
    kebab = contract["marker_kebab"]
    alt = contract.get("marker_kebab_alt")
    if alt:
        # Same pattern as the BTC test file.
        return re.compile(
            rf"#\s*allowed:\s*(?:{re.escape(kebab)}|{re.escape(alt)})\s+consumer\b"
        )
    return re.compile(rf"#\s*allowed:\s*{re.escape(kebab)}\s+consumer\b")


def _is_exempt(path: Path, contract: dict[str, Any]) -> bool:
    """A *.py file is exempt from the consumer-scan if any of these:
      1. Its name is the writer (writer carries the path literal; EXEMPT_BASENAMES
         per the contract test pattern).
      2. Its name is the test file for THIS contract (self-reference).
      3. Its path contains __pycache__ or .pyc.
    """
    name = path.name
    writer = contract.get("writer")
    if writer is not None and name == writer.name:
        return True
    if name == contract["test_file"].name:
        return True
    if any(part in EXEMPT_SUFFIX_PARTS for part in path.parts):
        return True
    return False


def _sidecar_consumed_by(content: str, contract: dict[str, Any]) -> bool:
    """True iff the file's source BOTH mentions the sidecar filename
    AND shows a loader-intent pattern. Pure prose mentions don't count."""
    filename = contract["sidecar"].name
    if filename not in content:
        return False
    return any(pat in content for pat in _LOADER_INTENT)


def _has_guard(content: str, contract: dict[str, Any]) -> bool:
    return contract["flag_key"] in content


def _has_marker(content: str, contract: dict[str, Any]) -> bool:
    return bool(_marker_re_for(contract).search(content))


def _reader_scan_for(contract: dict[str, Any]) -> dict[str, Any]:
    """Walk SCAN_ROOTS, find every *.py that opens the sidecar, and verify
    it carries the gate-flag reference OR the allow-marker. Anything that
    opens without one of those two signals is an UNGUARDED READER and is
    added to the result."""
    violations: list[str] = []
    files_scanned = 0

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for py_path in root.rglob("*.py"):
            if not py_path.is_file():
                continue
            if _is_exempt(py_path, contract):
                continue
            files_scanned += 1

            try:
                content = py_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # Non-text / unreadable; skip silently — matches the
                # contract-test skip behavior.
                continue

            if not _sidecar_consumed_by(content, contract):
                continue

            # Carries gate-flag OR marker → safe.
            if _has_guard(content, contract):
                continue
            if _has_marker(content, contract):
                continue

            violations.append(py_path.relative_to(REPO).as_posix())

    return {
        "contract": contract["name"],
        "files_scanned": files_scanned,
        "scan_roots": [str(r) for r in SCAN_ROOTS],
        "unguarded_readers": sorted(violations),
        "violation_count": len(violations),
        "state": "OK" if not violations else "FAIL",
    }


def _marker_bearers_for(contract: dict[str, Any]) -> dict[str, Any]:
    """Mirror of _reader_scan_for, but enumerate the WHITELIST (files that DO
    carry the allow-marker), not the blacklist. Exported via the JSON envelope
    as ``known_marker_bearers`` so a CI run can detect:

      * Symlink / pipeline papercuts  — file present in tree, expected to
        carry the marker, but does NOT (cross-checked against
        ``-expected_min_bearers``).
      * Marker drift                  — a contract's marker regex DOES match
        a file, but the file has been refactored out of the load path.

    The function walks the same SCAN_ROOTS / exempt / load-intent gates as
    _reader_scan_for so it is symmetric. A file appearing here means it
    "claims" the marker contract for this sidecar — investigate it before
    deleting or moving.
    """
    bearers: list[str] = []

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for py_path in root.rglob("*.py"):
            if not py_path.is_file():
                continue
            if _is_exempt(py_path, contract):
                continue

            try:
                content = py_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # A marker-bearing file MAY or MAY NOT exhibit loader intent
            # (some markers live on consumer files that have been refactored
            # but still carry the allow-marker for review-time discovery).
            # So we look for the marker regex against the FULL content
            # without requiring a sidecar-filename match.
            if _has_marker(content, contract):
                bearers.append(py_path.relative_to(REPO).as_posix())

    return {
        "contract": contract["name"],
        "marker_bearers": sorted(bearers),
        "bearer_count": len(bearers),
        # Floor: at least the writer + the test file would be exempt, but
        # we expect >=1 non-exempt bearer (the dashboard / consumer module).
        # We can't enforce a specific count here — it varies by sidecar —
        # so just expose the number and let consumers decide.
    }


# --------------------------------------------------------------------------- #
# Section C: pytest summary                                                  #
# --------------------------------------------------------------------------- #

def _run_one_pytest(contract: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    """Run the contract's pytest test file and capture pass/fail/skip counts.

    Parses pytest's progress line ("3 passed", "2 failed, 1 passed", ...).
    On a non-zero exit, captures the violation messages so they can be
    surfaced in the cross-reference.
    """
    test_file = contract["test_file"]
    cmd = [
        sys.executable, "-m", "pytest", str(test_file),
        "--tb=line", "-q", "--no-header",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=str(REPO),
        )
    except subprocess.TimeoutExpired:
        return {
            "contract": contract["name"],
            "test_file": str(test_file),
            "state": "TIMEOUT",
            "passed": 0, "failed": 0, "skipped": 0,
            "violation_lines": [f"pytest timed out after {timeout}s"],
        }
    except OSError as e:
        return {
            "contract": contract["name"],
            "test_file": str(test_file),
            "state": "OS_ERROR",
            "passed": 0, "failed": 0, "skipped": 0,
            "violation_lines": [f"subprocess error: {e}"],
        }

    # Parse the summary line. Pytest -q output has a final "= X ... ="
    # block with phrases like "3 passed", "2 failed", "1 skipped" — pick
    # out integers next to those keywords.
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    counts = {"passed": 0, "failed": 0, "skipped": 0}
    pattern = re.compile(r"(\d+)\s+(passed|failed|skipped|error|xfailed|xpassed)")
    for match in pattern.finditer(stdout):
        n = int(match.group(1))
        key = match.group(2)
        # Map error/xpassed/xfailed to the closest "outcome" bucket.
        if key in ("passed", "failed", "skipped"):
            counts[key] = n
        elif key == "error":
            counts["failed"] += n

    # Surface the FAILED-section assertion messages if any. Pytest -q
    # writes one "tb=line" per failure.
    violation_lines: list[str] = []
    if counts["failed"] > 0 or proc.returncode != 0:
        for line in stdout.splitlines() + stderr.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Look for assertion failure signatures.
            if stripped.startswith("AssertionError") or "Unguarded" in stripped \
                    or "HARD REGRESSION" in stripped or "missing required" in stripped:
                violation_lines.append(stripped)
                if len(violation_lines) >= 10:
                    break

    if proc.returncode == 0:
        state = "OK" if counts["failed"] == 0 else "FAIL"
    else:
        # exit 1 → failures; exit 5 → no tests collected; etc.
        if counts["failed"] > 0:
            state = "FAIL"
        elif counts["skipped"] > 0 and counts["passed"] == 0:
            state = "SKIPPED"
        else:
            state = f"EXIT_{proc.returncode}"

    return {
        "contract": contract["name"],
        "test_file": str(test_file),
        "state": state,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "violation_lines": violation_lines,
        "returncode": proc.returncode,
    }


# --------------------------------------------------------------------------- #
# Section D: cross-reference                                                 #
# --------------------------------------------------------------------------- #

def _cross_ref(contract: dict[str, Any], a: dict[str, Any], b: dict[str, Any],
               c: dict[str, Any]) -> dict[str, Any]:
    """Combine A+B+C into a single per-contract verdict."""
    a_ok = a["state"] in ("OK", "MISSING")
    b_ok = b["state"] == "OK"
    c_ok = c["state"] in ("OK", "SKIPPED")

    overall = "OK" if (a_ok and b_ok and c_ok) else "FAIL"
    if a_ok and b_ok and c_ok and a["state"] == "MISSING":
        overall = "MISSING"

    return {
        "contract": contract["name"],
        "display": contract["name"].replace("_", "-"),
        "sidecar_flag": a["state"],
        "sidecar_flag_detail": a["detail"],
        "reader_scan": b["state"],
        "unguarded_reader_count": b["violation_count"],
        "unguarded_readers": b["unguarded_readers"],
        "pytest": c["state"],
        "pytest_passed": c["passed"],
        "pytest_failed": c["failed"],
        "pytest_skipped": c["skipped"],
        "pytest_violations": c["violation_lines"],
        "verdict": overall,
    }


# --------------------------------------------------------------------------- #
# Output rendering                                                            #
# --------------------------------------------------------------------------- #

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_GREY = "\033[90m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _color(text: str, code: str, force: bool = False) -> str:
    if not sys.stdout.isatty() and not force:
        return text
    return f"{code}{text}{_RESET}"


_STATUS_TO_COLOR = {
    "OK": _GREEN,
    "FAIL": _RED,
    "MISSING": _YELLOW,
    "MISSING_CRON_HARD_FAIL": _RED,
    "FLAG_MISSING": _RED,
    "UNPARSEABLE": _RED,
    "EXIT_5": _RED,
}


def _render_text(contracts: list[dict[str, Any]],
                 section_a: list[dict[str, Any]],
                 section_b: list[dict[str, Any]],
                 section_c: list[dict[str, Any]],
                 section_d: list[dict[str, Any]]) -> str:
    """Human-readable text report."""
    out = []
    out.append(_color(_BOLD + "=" * 78 + _RESET, ""))
    out.append(_color(_BOLD + "sync_dark_audit_sidecar_scan.py" + _RESET, ""))
    out.append(_color(_BOLD + "=" * 78 + _RESET, ""))
    out.append(f"Working dir: {REPO}")
    out.append(f"Contract count: {len(contracts)}")
    out.append(f"All-cron-mode: {ALL_CRON_MODE}")
    out.append("")

    # --- Section A --- #
    out.append(_color("--- (A) Sidecar flag-on-disk check ---", _BOLD))
    for s in section_a:
        col = _STATUS_TO_COLOR.get(s["state"], _YELLOW)
        marker = {
            "OK": "  OK  ",
            "FAIL": " FAIL ",
            "MISSING": " MISS ",
            "MISSING_CRON_HARD_FAIL": "CRON! ",
            "FLAG_MISSING": " FLAG ",
            "UNPARSEABLE": "PARS! ",
        }.get(s["state"], " ???  ")
        line = f"[{_color(marker, col)}] {s['contract']:<30} {s['detail']}"
        out.append(line)
    out.append("")

    # --- Section B --- #
    out.append(_color("--- (B) Live reader scan over {tools/, audit_trail/, alpha_engine/} ---",
                      _BOLD))
    for s in section_b:
        if s["violation_count"] == 0:
            out.append(
                f"[{_color('  OK  ', _GREEN)}] {s['contract']:<30} "
                f"0 unguarded readers ({s['files_scanned']} files scanned)"
            )
        else:
            out.append(
                f"[{_color(' FAIL ', _RED)}] {s['contract']:<30} "
                f"{s['violation_count']} unguarded readers "
                f"({s['files_scanned']} files scanned):"
            )
            for v in s["unguarded_readers"]:
                out.append(f"    - {v}")
    out.append("")

    # --- Section C --- #
    out.append(_color("--- (C) Pytest contract-test pass/fail summary ---", _BOLD))
    for s in section_c:
        if s["state"] == "OK":
            summary = f"{s['passed']} passed"
        elif s["state"] == "SKIPPED":
            summary = f"{s['skipped']} skipped, {s['passed']} passed"
        elif s["state"] in ("FAIL", "TIMEOUT", "OS_ERROR"):
            summary = (
                f"{s['failed']} failed, {s['passed']} passed, {s['skipped']} skipped"
            )
        else:
            summary = f"{s['state']} (rc={s['returncode']})"
        col = _GREEN if s["state"] in ("OK", "SKIPPED") else _RED
        out.append(
            f"[{_color('  OK  ' if s['state'] in ('OK', 'SKIPPED') else ' FAIL ', col)}] "
            f"{s['test_file'].replace(str(REPO) + '/', ''):<70} {summary}"
        )
        for line in s["violation_lines"][:3]:
            out.append(f"    ! {line}")
    out.append("")

    # --- Section D --- #
    # NB: f-string in this block precomputes each verdict cell outside the
    # outer f-string. Substituting `_color(formatted_verdict, col)` directly
    # into the f-string would break Python 3.6-3.11 f-string parsing because
    # the inner `:` triggers the format-spec separator (the format-spec would
    # then span `<10, col)` which is invalid). Local-variable indirection
    # keeps the f-string well-formed.
    out.append(_color("--- (D) Cross-reference per contract ---", _BOLD))
    out.append(f"{'contract':<28} {'A:flag':<22} {'B:readers':<14} "
               f"{'C:pytest':<14} {'VERDICT':<10}")
    out.append("-" * 90)
    for d in section_d:
        col = _GREEN if d["verdict"] == "OK" else (_YELLOW if d["verdict"] == "MISSING" else _RED)
        verdict_cell = _color(f"{d['verdict']:<10}", col)
        out.append(
            f"{d['contract']:<28} {d['sidecar_flag']:<22} "
            f"{(d['reader_scan'] + ' (' + str(d['unguarded_reader_count']) + ')'):<14} "
            f"{d['pytest']:<14} {verdict_cell}"
        )
    out.append("")

    # --- Global summary --- #
    verdicts = [d["verdict"] for d in section_d]
    n_ok = verdicts.count("OK")
    n_missing = verdicts.count("MISSING")
    n_fail = verdicts.count("FAIL")
    out.append(_color("--- Global summary ---", _BOLD))
    out.append(
        f"Total: {len(contracts)} | OK: {n_ok} | MISSING: {n_missing} | "
        f"FAIL: {n_fail}"
    )
    if n_fail > 0:
        out.append(_color(f"\n*** {n_fail} contract(s) FAIL — review required ***",
                          _RED, force=True))
    elif n_missing == len(contracts):
        out.append(_color(
            "\nAll sidecars MISSING on this checkout's disk — typical for a "
            "first-time clone before the crons have run; run this script on "
            "the cron host (or after running each writer locally) to get "
            "a meaningful B/C scan.",
            _YELLOW, force=True,
        ))
    elif n_ok == len(contracts):
        out.append(_color("\n*** ALL CONTRACTS GREEN ***", _GREEN, force=True))
    return "\n".join(out)


def _render_json(section_a: list[dict[str, Any]], section_b: list[dict[str, Any]],
                 section_c: list[dict[str, Any]], section_d: list[dict[str, Any]],
                 known_marker_bearers: Optional[list[dict[str, Any]]] = None) -> str:
    envelope: dict[str, Any] = {
        "repo": str(REPO),
        "all_cron_mode": ALL_CRON_MODE,
        "section_a_sidecar_flag": section_a,
        "section_b_reader_scan": section_b,
        "section_c_pytest": section_c,
        "section_d_cross_ref": section_d,
        "known_marker_bearers": known_marker_bearers or [],
        "global_summary": {
            "total": len(section_d),
            "ok": sum(1 for d in section_d if d["verdict"] == "OK"),
            "missing": sum(1 for d in section_d if d["verdict"] == "MISSING"),
            "fail": sum(1 for d in section_d if d["verdict"] == "FAIL"),
            "scan_errors": (
                sum(1 for s in section_a if s["state"] == "UNPARSEABLE")
                + sum(1 for s in section_c if s["state"] in ("TIMEOUT", "OS_ERROR"))
            ),
            "marker_bearer_total": sum(
                m["bearer_count"] for m in (known_marker_bearers or [])
            ),
        },
    }
    return json.dumps(envelope, indent=2, sort_keys=True)


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-shot scanner for the 7 audit-dashboard sidecar contracts.",
    )
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON envelope instead of human-readable text.")
    parser.add_argument("--contract", type=str, metavar="NAME",
                        help="Scope to one contract by name (debug).")
    parser.add_argument("--no-pytest", action="store_true",
                        help="Skip Section C; pure pre-flight scan (A+B+D).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress all output; rely solely on exit code.")
    parser.add_argument("--timeout", type=int, default=60, metavar="SEC",
                        help="Per-pytest timeout, default 60s.")
    args = parser.parse_args(argv)

    # ----- Filter contracts by --contract ----- #
    contracts = CONTRACTS
    if args.contract:
        contract_names = {c["name"] for c in contracts}
        if args.contract not in contract_names:
            print(f"Unknown contract: {args.contract}. "
                  f"Available: {sorted(contract_names)}", file=sys.stderr)
            return 2
        contracts = [c for c in contracts if c["name"] == args.contract]

    # ----- Section A: sidecar flag check (parallel) ----- #
    section_a: list[dict[str, Any]] = []
    section_b: list[dict[str, Any]] = []
    section_d: list[dict[str, Any]] = []
    section_c: list[dict[str, Any]] = []
    marker_bearers: list[dict[str, Any]] = []

    # A and B are CPU-light + IO-heavy; thread pool is fine over process
    # pool for this scale (7 contracts × ~200 files per directory walk).
    with ThreadPoolExecutor(max_workers=max(7, len(contracts))) as pool:
        future_to_c_a = {pool.submit(_sidecar_flag_status, c): c for c in contracts}
        future_to_c_b = {pool.submit(_reader_scan_for, c): c for c in contracts}
        # Whitelist-scan (known_marker_bearers) for the JSON envelope —
        # cheap, runs alongside A/B/C without contending for pytest slots.
        future_to_c_mb = {pool.submit(_marker_bearers_for, c): c for c in contracts}

        if not args.no_pytest:
            future_to_c_c = {
                pool.submit(_run_one_pytest, c, args.timeout): c
                for c in contracts
            }
        else:
            future_to_c_c = {}

        # Collect A
        for fut in as_completed(future_to_c_a):
            section_a.append(fut.result())
        # Collect B
        for fut in as_completed(future_to_c_b):
            section_b.append(fut.result())
        # Collect C (if requested)
        for fut in as_completed(future_to_c_c):
            section_c.append(fut.result())
        # Collect whitelist (marker bearers)
        for fut in as_completed(future_to_c_mb):
            marker_bearers.append(fut.result())

    if args.no_pytest:
        section_c = [
            {
                "contract": c["name"],
                "test_file": str(c["test_file"]),
                "state": "SKIPPED",
                "passed": 0, "failed": 0, "skipped": 0,
                "violation_lines": [],
                "returncode": -1,
            }
            for c in contracts
        ]

    # ----- Section D: cross-ref ----- #
    a_by_name = {x["contract"]: x for x in section_a}
    b_by_name = {x["contract"]: x for x in section_b}
    c_by_name = {x["contract"]: x for x in section_c}
    for c in contracts:
        section_d.append(_cross_ref(
            c, a_by_name[c["name"]], b_by_name[c["name"]], c_by_name[c["name"]],
        ))

    # ----- Render ----- #
    if not args.quiet:
        if args.json:
            mb_sorted = sorted(marker_bearers, key=lambda m: m["contract"])
            print(_render_json(section_a, section_b, section_c, section_d, mb_sorted))
        else:
            # Sort D by contract name for stable human ordering.
            section_d_sorted = sorted(section_d, key=lambda d: d["contract"])
            print(_render_text(contracts, section_a, section_b, section_c,
                               section_d_sorted))

    # ----- Exit code ----- #
    # Resolution order:
    #   2  scanner self-broken (UNPARSEABLE sidecar JSON, TIMEOUT / OS_ERROR
    #      on pytest subprocess). Counts roll up from Section A + Section C
    #      directly — bypassing cross_ref so a SCAN_ERROR doesn't get
    #      silently obscured as a FAIL.
    #   1  contract discipline violation (FAIL in cross_ref) OR a cron-sidecar
    #      MISSING_CRON_HARD_FAIL (sidecar absent in ALL_SIDECAR_CRON_MODE=1).
    #   0  all green.
    n_scan_error = (
        sum(1 for s in section_a if s["state"] == "UNPARSEABLE")
        + sum(1 for s in section_c if s["state"] in ("TIMEOUT", "OS_ERROR"))
    )
    n_fail = sum(1 for d in section_d if d["verdict"] == "FAIL")
    n_cron_hard_fail = sum(1 for s in section_a
                           if s["state"] == "MISSING_CRON_HARD_FAIL")
    if n_scan_error > 0:
        return 2
    if n_cron_hard_fail > 0:
        return 1  # cron-sidecar-missing is a hard regression in cron-mode
    if n_fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

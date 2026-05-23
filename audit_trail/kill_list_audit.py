"""SHA-256 integrity audit for the kill_list (opt-in sidecar).

Defense-in-depth module per panel review item #7
(reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md, 4/4 quick-win).

Background
----------
PR #519's `mutation_name` fallback path could allow a mutation_name suffix to
silently coincide with an existing kill_list entry, potentially bypassing it
without an explicit kill-run event. This module computes a stable SHA-256 hash
of the current `alpha_engine/data/core_whitelist.json::kill_list` array and
appends it to an append-only JSON-lines log, so any silent drift is detectable
post-hoc.

Public API
----------
- audit_kill_list(audit_cycle_id) -> dict
    Compute current hash + stats, append to log, return new entry.
- detect_unexpected_changes(window_hours=24) -> list[dict]
    Return log entries within the window where the hash changed without an
    explicit `last_kill_run` change relative to the previous entry. These are
    candidate drift events.

CLI
---
    python -m audit_trail.kill_list_audit

Wire-Up Plan (out of scope for this PR)
---------------------------------------
Future call site: `audit_trail/dashboard_generator.py`, after the function that
loads core_whitelist.json (typically `_load_external_kill_set` or equivalent).
Expected wire-up PR: 2026-05-02.

This module is stdlib-only (json, hashlib, datetime, pathlib).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths (overridable for testing)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WHITELIST_PATH = REPO_ROOT / "alpha_engine" / "data" / "core_whitelist.json"
DEFAULT_LOG_PATH = REPO_ROOT / "audit_trail" / "data" / "kill_list_audit_log.json"


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------


def _normalize_kill_list(entries: list[Any]) -> list[str]:
    """Return a deterministically sorted, lowercased, deduped list of strings.

    Order-independence and case-insensitivity are required so that cosmetic
    reorderings (or case fluctuations from upstream mutators) do not produce
    spurious hash mismatches.
    """
    cleaned = []
    seen = set()
    for raw in entries or []:
        if raw is None:
            continue
        s = str(raw).strip().lower()
        if not s:
            # The live kill_list contains an empty string at index 0; we drop
            # blanks because they carry no semantic meaning.
            continue
        if s in seen:
            continue
        seen.add(s)
        cleaned.append(s)
    cleaned.sort()
    return cleaned


def compute_kill_list_sha256(entries: list[Any]) -> str:
    """Compute the SHA-256 hex digest of the normalized kill_list."""
    normalized = _normalize_kill_list(entries)
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Whitelist + log I/O
# ---------------------------------------------------------------------------


def _read_whitelist(whitelist_path: Path) -> dict:
    if not whitelist_path.exists():
        return {}
    with whitelist_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_log(log_path: Path) -> list[dict]:
    """Read the append-only audit log. Tolerates JSON-lines OR a JSON array."""
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    # Try JSON array first (single load); fall back to JSON-lines.
    try:
        loaded = json.loads(text)
        if isinstance(loaded, list):
            return [e for e in loaded if isinstance(e, dict)]
    except json.JSONDecodeError:
        pass
    entries: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                entries.append(obj)
        except json.JSONDecodeError:
            # Skip malformed lines rather than crash the audit.
            continue
    return entries


def _append_log(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audit_kill_list(
    audit_cycle_id: str,
    *,
    whitelist_path: Path | None = None,
    log_path: Path | None = None,
    now: datetime | None = None,
) -> dict:
    """Compute current hash + stats, append to log, return the new entry.

    Parameters
    ----------
    audit_cycle_id : str
        Stable identifier for the cycle issuing this audit (e.g. the dashboard
        generator's run id or a timestamp).
    whitelist_path : Path, optional
        Override path to core_whitelist.json (testing).
    log_path : Path, optional
        Override path to the append-only log (testing).
    now : datetime, optional
        Timestamp injection for deterministic tests.
    """
    whitelist_path = whitelist_path or DEFAULT_WHITELIST_PATH
    log_path = log_path or DEFAULT_LOG_PATH
    ts = (now or datetime.now(timezone.utc)).isoformat()

    whitelist = _read_whitelist(Path(whitelist_path))
    kill_list_raw = whitelist.get("kill_list") or []
    metadata = whitelist.get("kill_list_metadata") or {}
    last_kill_run = metadata.get("last_kill_run") or whitelist.get("last_kill_run")
    auto_expired = bool(
        metadata.get("auto_expired")
        or whitelist.get("kill_list_auto_expired")
        or False
    )

    entry = {
        "timestamp": ts,
        "kill_list_count": len(_normalize_kill_list(kill_list_raw)),
        "kill_list_sha256": compute_kill_list_sha256(kill_list_raw),
        "last_kill_run": last_kill_run,
        "auto_expired": auto_expired,
        "audit_cycle_id": str(audit_cycle_id),
    }

    _append_log(Path(log_path), entry)
    return entry


def detect_unexpected_changes(
    window_hours: int = 24,
    *,
    log_path: Path | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Return log entries where the hash changed without a `last_kill_run` change.

    A drift entry is one whose `kill_list_sha256` differs from the immediately
    preceding entry while `last_kill_run` did NOT change between them. These
    are candidate silent edits worth alerting on.
    """
    log_path = log_path or DEFAULT_LOG_PATH
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=window_hours)
    entries = _read_log(Path(log_path))
    if len(entries) < 2:
        return []

    drifts: list[dict] = []
    prev = entries[0]
    for cur in entries[1:]:
        # Window check on the current entry.
        try:
            cur_ts = datetime.fromisoformat(str(cur.get("timestamp")).replace("Z", "+00:00"))
        except Exception:
            prev = cur
            continue
        if cur_ts.tzinfo is None:
            cur_ts = cur_ts.replace(tzinfo=timezone.utc)
        if cur_ts < cutoff:
            prev = cur
            continue

        hash_changed = cur.get("kill_list_sha256") != prev.get("kill_list_sha256")
        run_changed = cur.get("last_kill_run") != prev.get("last_kill_run")
        if hash_changed and not run_changed:
            drifts.append(
                {
                    "timestamp": cur.get("timestamp"),
                    "audit_cycle_id": cur.get("audit_cycle_id"),
                    "from_sha256": prev.get("kill_list_sha256"),
                    "to_sha256": cur.get("kill_list_sha256"),
                    "from_count": prev.get("kill_list_count"),
                    "to_count": cur.get("kill_list_count"),
                    "last_kill_run": cur.get("last_kill_run"),
                    "auto_expired": cur.get("auto_expired"),
                }
            )
        prev = cur
    return drifts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    cycle_id = "cli-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    entry = audit_kill_list(cycle_id)
    print(json.dumps(entry, indent=2))
    drifts = detect_unexpected_changes(window_hours=24)
    if drifts:
        print(f"\n[drift] {len(drifts)} unexpected change(s) in last 24h:")
        for d in drifts:
            print(json.dumps(d, indent=2))
    else:
        print("\n[drift] none in last 24h.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())

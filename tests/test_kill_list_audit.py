"""Tests for audit_trail.kill_list_audit."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from audit_trail import kill_list_audit as kla


def _write_whitelist(path: Path, kill_list: list, *, last_kill_run: str | None = None,
                     auto_expired: bool = False) -> None:
    payload = {"kill_list": kill_list}
    if last_kill_run is not None or auto_expired:
        payload["kill_list_metadata"] = {
            "last_kill_run": last_kill_run,
            "auto_expired": auto_expired,
        }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_compute_hash_stable_under_reorder():
    a = ["alpha", "Beta", "gamma"]
    b = ["GAMMA", "alpha", "beta"]
    assert kla.compute_kill_list_sha256(a) == kla.compute_kill_list_sha256(b)


def test_compute_hash_drops_blanks_and_dedupes():
    base = kla.compute_kill_list_sha256(["alpha", "beta"])
    noisy = kla.compute_kill_list_sha256(["", "alpha", "alpha", " beta ", None])
    assert base == noisy


def test_compute_hash_changes_on_real_addition():
    h1 = kla.compute_kill_list_sha256(["alpha", "beta"])
    h2 = kla.compute_kill_list_sha256(["alpha", "beta", "gamma"])
    assert h1 != h2


def test_audit_kill_list_appends_entry(tmp_path: Path):
    wl = tmp_path / "core_whitelist.json"
    log = tmp_path / "log.json"
    _write_whitelist(wl, ["alpha", "beta", ""], last_kill_run="2026-04-29T00:00:00+00:00")

    entry = kla.audit_kill_list("cycle-1", whitelist_path=wl, log_path=log)
    assert entry["kill_list_count"] == 2
    assert entry["audit_cycle_id"] == "cycle-1"
    assert entry["last_kill_run"] == "2026-04-29T00:00:00+00:00"
    assert len(entry["kill_list_sha256"]) == 64

    # Log is JSON-lines.
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["audit_cycle_id"] == "cycle-1"


def test_audit_kill_list_idempotent_hash_across_calls(tmp_path: Path):
    wl = tmp_path / "core_whitelist.json"
    log = tmp_path / "log.json"
    _write_whitelist(wl, ["alpha", "beta"], last_kill_run="2026-04-29T00:00:00+00:00")

    e1 = kla.audit_kill_list("cycle-1", whitelist_path=wl, log_path=log)
    e2 = kla.audit_kill_list("cycle-2", whitelist_path=wl, log_path=log)
    # Same kill_list -> same hash; different cycle_id -> different entries.
    assert e1["kill_list_sha256"] == e2["kill_list_sha256"]
    assert e1["audit_cycle_id"] != e2["audit_cycle_id"]
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_audit_handles_missing_whitelist(tmp_path: Path):
    wl = tmp_path / "missing.json"
    log = tmp_path / "log.json"
    entry = kla.audit_kill_list("cycle-x", whitelist_path=wl, log_path=log)
    assert entry["kill_list_count"] == 0
    # Hash of empty list is deterministic.
    assert entry["kill_list_sha256"] == kla.compute_kill_list_sha256([])


def test_detect_unexpected_changes_flags_silent_drift(tmp_path: Path):
    wl = tmp_path / "core_whitelist.json"
    log = tmp_path / "log.json"
    now = datetime.now(timezone.utc)

    # First audit at T-2h.
    _write_whitelist(wl, ["alpha", "beta"], last_kill_run="2026-04-29T00:00:00+00:00")
    kla.audit_kill_list("c1", whitelist_path=wl, log_path=log,
                        now=now - timedelta(hours=2))

    # Silent edit: kill_list changed, last_kill_run did NOT.
    _write_whitelist(wl, ["alpha"], last_kill_run="2026-04-29T00:00:00+00:00")
    kla.audit_kill_list("c2", whitelist_path=wl, log_path=log,
                        now=now - timedelta(hours=1))

    drifts = kla.detect_unexpected_changes(window_hours=24, log_path=log, now=now)
    assert len(drifts) == 1
    assert drifts[0]["audit_cycle_id"] == "c2"
    assert drifts[0]["from_count"] == 2
    assert drifts[0]["to_count"] == 1


def test_detect_unexpected_changes_ignores_legit_kill_run(tmp_path: Path):
    wl = tmp_path / "core_whitelist.json"
    log = tmp_path / "log.json"
    now = datetime.now(timezone.utc)

    _write_whitelist(wl, ["alpha"], last_kill_run="2026-04-29T00:00:00+00:00")
    kla.audit_kill_list("c1", whitelist_path=wl, log_path=log,
                        now=now - timedelta(hours=2))

    # Legit kill-run: hash AND last_kill_run change together.
    _write_whitelist(wl, ["alpha", "gamma"], last_kill_run="2026-04-29T12:00:00+00:00")
    kla.audit_kill_list("c2", whitelist_path=wl, log_path=log,
                        now=now - timedelta(hours=1))

    drifts = kla.detect_unexpected_changes(window_hours=24, log_path=log, now=now)
    assert drifts == []


def test_detect_unexpected_changes_respects_window(tmp_path: Path):
    log = tmp_path / "log.json"
    now = datetime.now(timezone.utc)

    # Two entries 48h ago: drift outside the 24h window.
    e1 = {
        "timestamp": (now - timedelta(hours=49)).isoformat(),
        "kill_list_count": 2,
        "kill_list_sha256": "a" * 64,
        "last_kill_run": "x",
        "auto_expired": False,
        "audit_cycle_id": "old1",
    }
    e2 = {
        "timestamp": (now - timedelta(hours=48)).isoformat(),
        "kill_list_count": 3,
        "kill_list_sha256": "b" * 64,
        "last_kill_run": "x",
        "auto_expired": False,
        "audit_cycle_id": "old2",
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as fh:
        for e in (e1, e2):
            fh.write(json.dumps(e) + "\n")

    drifts = kla.detect_unexpected_changes(window_hours=24, log_path=log, now=now)
    assert drifts == []


def test_detect_unexpected_changes_handles_empty_log(tmp_path: Path):
    log = tmp_path / "log.json"
    assert kla.detect_unexpected_changes(window_hours=24, log_path=log) == []
    log.write_text("", encoding="utf-8")
    assert kla.detect_unexpected_changes(window_hours=24, log_path=log) == []


def test_detect_unexpected_changes_tolerates_malformed_lines(tmp_path: Path):
    log = tmp_path / "log.json"
    now = datetime.now(timezone.utc)
    valid1 = {
        "timestamp": (now - timedelta(hours=2)).isoformat(),
        "kill_list_count": 1,
        "kill_list_sha256": "a" * 64,
        "last_kill_run": "k",
        "auto_expired": False,
        "audit_cycle_id": "v1",
    }
    valid2 = {
        "timestamp": (now - timedelta(hours=1)).isoformat(),
        "kill_list_count": 1,
        "kill_list_sha256": "b" * 64,
        "last_kill_run": "k",
        "auto_expired": False,
        "audit_cycle_id": "v2",
    }
    with log.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(valid1) + "\n")
        fh.write("not-json-garbage\n")
        fh.write(json.dumps(valid2) + "\n")

    drifts = kla.detect_unexpected_changes(window_hours=24, log_path=log, now=now)
    assert len(drifts) == 1
    assert drifts[0]["audit_cycle_id"] == "v2"


def test_audit_records_auto_expired_flag(tmp_path: Path):
    wl = tmp_path / "core_whitelist.json"
    log = tmp_path / "log.json"
    _write_whitelist(wl, ["alpha"], last_kill_run="2026-04-29T00:00:00+00:00",
                     auto_expired=True)
    entry = kla.audit_kill_list("c-expired", whitelist_path=wl, log_path=log)
    assert entry["auto_expired"] is True


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))

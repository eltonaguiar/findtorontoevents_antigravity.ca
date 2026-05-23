"""Tamper-evident forward record for /audit picks.

Why this exists
---------------
A sophisticated visitor to `/audit` does not need another self-computed
metric — they need a tamper-evident commitment that the picks claimed
"as of date X" really were the picks at date X. Without one, every
attribution / DSR / drift number on the page is computed by the same
party that publishes the picks, which is exactly the conflict of
interest a public audit is supposed to remove.

This tool produces a deterministic SHA-256 hash of the canonical JSON
representation of the active-picks list and appends it (with timestamp,
git SHA, and summary stats) to an append-only log committed alongside
the rest of the repo. Git history is itself a public timestamp; once a
notary entry is in `origin/main`, it cannot be backdated without
rewriting public history.

A future v2 should anchor each entry into Bitcoin via OpenTimestamps,
which makes the timestamp commitment provable to a third party even if
the GitHub repo is rewritten or deleted. For MVP, git+commit is enough.

Wiring status: OPT-IN SIDECAR. No production caller. Run manually:
    python tools/pick_notarizer.py notarize
    python tools/pick_notarizer.py verify --git-sha <sha>
A follow-up PR will hook the `notarize` step into the
`audit-dashboard.yml` cron after the payload write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
NOTARY_DIR = REPO_ROOT / "audit_trail" / "notary"
LOG_PATH = NOTARY_DIR / "notary_log.jsonl"
SCHEMA_VERSION = 1


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization for hashing.

    sort_keys=True + separators kills whitespace/key-order drift.
    ensure_ascii=True stops Unicode normalization bugs.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode("ascii").strip()
    except Exception:
        return ""


def _git_show(git_sha: str, repo_relative_path: str) -> str:
    """Return file contents from a past git commit."""
    spec = f"{git_sha}:{repo_relative_path}"
    out = subprocess.check_output(
        ["git", "show", spec], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
    )
    return out.decode("utf-8", errors="replace")


def _hash_picks_payload(payload: dict) -> dict[str, Any]:
    """Hash the parts of the payload that constitute the public commitment.

    `picks.active` is the dispositive forward-record field. We also
    hash a small `summary` block separately so the verifier can prove
    headline numbers without re-hashing the full active set.
    """
    picks = payload.get("picks", {}) or {}
    active = picks.get("active", []) or []
    summary = payload.get("summary", {}) or {}
    recent_closed = picks.get("recent_closed", []) or []

    return {
        "active_picks_hash": _sha256(_canonical_json(active)),
        "summary_hash": _sha256(_canonical_json(summary)),
        "recent_closed_hash": _sha256(_canonical_json(recent_closed)),
        "n_active": len(active),
        "n_recent_closed": len(recent_closed),
    }


def cmd_notarize(args) -> int:
    if not PICKS_PATH.exists():
        print(f"ERROR: picks file not found at {PICKS_PATH}", file=sys.stderr)
        return 2
    with PICKS_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    hashes = _hash_picks_payload(payload)
    entry = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "git_sha": _git_head_sha(),
        "picks_path": "audit_dashboard/data/dashboard_data.json",
        **hashes,
        "generated_at": payload.get("generated_at") or payload.get("metadata", {}).get("generated_at"),
    }

    NOTARY_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    if not args.quiet:
        print("Notarized:")
        for k, v in entry.items():
            print(f"  {k}: {v}")
        print(f"Appended to: {LOG_PATH}")
    return 0


def cmd_verify(args) -> int:
    """Verify a past notary entry by re-hashing the payload at the recorded git_sha.

    Strategy:
      1. Locate the entry in the log (by git_sha or ts_utc).
      2. `git show <git_sha>:<picks_path>` to retrieve historical payload.
      3. Recompute hashes; compare to log entry.

    If verification fails, the picks file at that commit has been mutated
    relative to the notarized commitment — i.e. tamper detected.
    """
    if not LOG_PATH.exists():
        print(f"ERROR: notary log missing at {LOG_PATH}", file=sys.stderr)
        return 2

    entries: list[dict] = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    matches = []
    for e in entries:
        if args.git_sha and len(args.git_sha) >= 7 and e.get("git_sha", "").startswith(args.git_sha):
            matches.append(e)
        elif args.ts and e.get("ts_utc", "") == args.ts:
            matches.append(e)
    if not args.git_sha and not args.ts:
        # Default: verify the most recent entry
        matches = entries[-1:]
    if not matches:
        print("No matching notary entry found.", file=sys.stderr)
        return 3

    failures = 0
    for entry in matches:
        sha = entry.get("git_sha")
        path = entry.get("picks_path", "audit_dashboard/data/dashboard_data.json")
        if not sha:
            print(f"SKIP: entry has no git_sha (ts={entry.get('ts_utc')})")
            continue
        try:
            raw = _git_show(sha, path)
        except subprocess.CalledProcessError as exc:
            print(f"FAIL: git show {sha}:{path} -> {exc}")
            failures += 1
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"FAIL: payload at {sha} not valid JSON: {exc}")
            failures += 1
            continue
        recomputed = _hash_picks_payload(payload)
        ok = (
            recomputed["active_picks_hash"] == entry["active_picks_hash"]
            and recomputed["summary_hash"] == entry["summary_hash"]
            and recomputed["recent_closed_hash"] == entry["recent_closed_hash"]
        )
        flag = "PASS" if ok else "FAIL"
        print(f"{flag}: ts={entry['ts_utc']} sha={sha[:12]} "
              f"n_active={entry['n_active']} (now {recomputed['n_active']})")
        if not ok:
            failures += 1
            print("  active_picks_hash:")
            print(f"    notarized = {entry['active_picks_hash']}")
            print(f"    recomputed= {recomputed['active_picks_hash']}")
    return 0 if failures == 0 else 1


def cmd_log(args) -> int:
    if not LOG_PATH.exists():
        print(f"(no log yet at {LOG_PATH})")
        return 0
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            print(f"{e['ts_utc']} sha={e.get('git_sha','-')[:12]} "
                  f"n_active={e['n_active']} n_closed={e['n_recent_closed']} "
                  f"active_hash={e['active_picks_hash'][:23]}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_notarize = sub.add_parser("notarize", help="Append a notary entry for the current picks")
    p_notarize.add_argument("--quiet", action="store_true")
    p_notarize.set_defaults(func=cmd_notarize)

    p_verify = sub.add_parser("verify", help="Verify a past notary entry against git history")
    p_verify.add_argument("--git-sha", default=None,
                          help="Verify the entry recorded against this git SHA (prefix match OK)")
    p_verify.add_argument("--ts", default=None,
                          help="Verify the entry with this exact ts_utc")
    p_verify.set_defaults(func=cmd_verify)

    p_log = sub.add_parser("log", help="Print all notary entries")
    p_log.set_defaults(func=cmd_log)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

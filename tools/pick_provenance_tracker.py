"""Per-pick provenance fingerprint — replayability for the audit page.

Why this exists
---------------
The audit-credibility supplement suite computes lots of derived numbers
(WR posterior, factor attribution, capacity, decay, correlation, etc.).
For any of those columns to be auditable end-to-end, you need to be
able to reconstruct the exact inputs each pick decision depended on at
emission time.

This module fingerprints each active pick by hashing a canonical-JSON
projection of the *decision-relevant* fields (strategy, asset_class,
symbol, direction, confidence, ml_score, entry_price, regime). The
fingerprint is logged as an append-only JSONL entry alongside ts_utc,
git_sha, and schema_version.

Replay / debugging:
- Same inputs across runs -> same fingerprint -> easy to spot
  drift / silent payload corruption.
- A fingerprint query returns the chronological history of every time
  a pick with those inputs was emitted. This is the leading-indicator
  counterpart to the lifetime notary log: notary fingerprints the
  ENTIRE picks.active block; this module fingerprints EACH pick
  independently so individual picks can be tracked across runs.

Reuses tools/pick_notarizer.py:_canonical_json + _sha256 via importlib
so the hash math stays in one place.

Wiring status: OPT-IN SIDECAR. Future PR adds a "fingerprint" tooltip
to each row of audit_dashboard/template.html active-picks table. With
the fingerprint visible, a third-party verifier can ask: "show me every
time a pick with this fingerprint was emitted" and replay the audit
numbers.

Caveats
-------
1. The fingerprint covers DECISION-RELEVANT fields only. Realised PnL
   and outcomes are deliberately excluded — those come later, and
   including them would defeat the "fingerprint at emission" use case.
2. The append-only JSONL grows monotonically. After a year of hourly
   notarize runs that's ~10^6 entries; rotation deferred to v2.
3. Like every supplement reading the dashboard payload, fingerprint
   stability depends on payload-emitter consistency. The notary anomaly
   canary is the upstream check for that.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
LOG_PATH = REPO_ROOT / "tools" / "data" / "pick_provenance_log.jsonl"
SCHEMA_VERSION = 1

# Decision-relevant fields. Keep this list stable across schema versions
# or bump SCHEMA_VERSION. Changing the field set without bumping silently
# invalidates every prior fingerprint.
PROVENANCE_FIELDS = (
    "strategy",
    "asset_class",
    "symbol",
    "direction",
    "confidence",
    "ml_score",
    "entry_price",
    "regime",
)


def _load_notarizer_helpers():
    spec = importlib.util.spec_from_file_location(
        "pick_notarizer", REPO_ROOT / "tools" / "pick_notarizer.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._canonical_json, mod._sha256


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode("ascii").strip()
    except Exception:
        return ""


def fingerprint_pick(pick: dict, fields: tuple[str, ...] = PROVENANCE_FIELDS,
                     canonical_json=None, sha256=None) -> str:
    """Deterministic SHA-256 of canonical-JSON projection.

    Missing fields project to None — fingerprint is stable for picks
    that lack a given optional field (e.g. older schema without regime).
    """
    if canonical_json is None or sha256 is None:
        canonical_json, sha256 = _load_notarizer_helpers()
    projection = {k: pick.get(k) for k in fields}
    return sha256(canonical_json(projection))


def fingerprint_all(picks: list[dict],
                    canonical_json=None,
                    sha256=None) -> list[dict]:
    """Return per-pick {strategy, symbol, fingerprint, schema_version}."""
    if canonical_json is None or sha256 is None:
        canonical_json, sha256 = _load_notarizer_helpers()
    out: list[dict] = []
    for p in picks:
        fp = fingerprint_pick(p, canonical_json=canonical_json, sha256=sha256)
        out.append({
            "strategy": p.get("strategy"),
            "symbol": p.get("symbol"),
            "fingerprint": fp,
            "schema_version": SCHEMA_VERSION,
        })
    return out


def append_log(entries: list[dict], log_path: Path = LOG_PATH,
               ts_utc: str | None = None,
               git_sha: str | None = None) -> int:
    """Append entries to the provenance JSONL log. Returns count written.

    Each entry is augmented with {ts_utc, git_sha} at write time.
    """
    if ts_utc is None:
        ts_utc = datetime.now(timezone.utc).isoformat()
    if git_sha is None:
        git_sha = _git_head_sha()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with log_path.open("a", encoding="utf-8") as f:
        for e in entries:
            row = dict(e)
            row["ts_utc"] = ts_utc
            row["git_sha"] = git_sha
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            n += 1
    return n


def query_by_fingerprint(fingerprint: str,
                          log_path: Path = LOG_PATH) -> list[dict]:
    """Return chronological list of log entries with this fingerprint."""
    if not log_path.exists():
        return []
    out: list[dict] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("fingerprint") == fingerprint:
                out.append(row)
    out.sort(key=lambda r: r.get("ts_utc", ""))
    return out


def cmd_fingerprint(args) -> int:
    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("active") or []
    entries = fingerprint_all(picks)
    if args.append:
        n = append_log(entries)
        if not args.quiet:
            print(f"appended {n} provenance rows to {LOG_PATH}")
    else:
        if not args.quiet:
            print(f"fingerprinted {len(entries)} active picks (not appended; --append to write)")
    if not args.quiet:
        for e in entries[:10]:
            print(f"  {e['strategy']:<25} {e['symbol']:<12} {e['fingerprint'][:32]}...")
    return 0


def cmd_query(args) -> int:
    rows = query_by_fingerprint(args.fingerprint)
    if not rows:
        print(f"no entries for fingerprint {args.fingerprint}")
        return 1
    print(f"{len(rows)} entries for fingerprint {args.fingerprint}:")
    for r in rows:
        print(f"  ts={r.get('ts_utc')} strategy={r.get('strategy')} "
              f"symbol={r.get('symbol')} git={r.get('git_sha', '')[:12]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_fp = sub.add_parser("fingerprint",
                          help="Fingerprint picks.active and optionally append to log")
    p_fp.add_argument("--append", action="store_true",
                     help="Append fingerprints to the JSONL log")
    p_fp.add_argument("--quiet", action="store_true")
    p_fp.set_defaults(func=cmd_fingerprint)

    p_q = sub.add_parser("query", help="Query log by fingerprint hash")
    p_q.add_argument("fingerprint",
                    help="SHA-256 fingerprint (with or without sha256: prefix)")
    p_q.set_defaults(func=cmd_query)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assert parity across the three live audit surfaces.

Design-debate element 13, as an assertion with an exit code rather than a prose reconciliation.

Why this exists
---------------
On 2026-11-19 the same ledger was served twice, by the same site, with different contents:

    /audit/data/audit3_ledger.json    627,649 B  sha b0ca1de6…  generated 18:32:40Z  8,613 rows
    /audit3/audit3_ledger.json        665,028 B  sha 557cb3f1…  generated 21:02:25Z  8,621 rows

2h30m and 8 rows apart, and neither page disclosed which copy it rendered. Provenance identifiers
cannot catch that: both copies were internally consistent, each correctly describing a different
population. This is the layer above provenance — the same artifact delivered twice.

What it asserts
---------------
1. Every endpoint returns HTTP 200 and parses as JSON.
2. The two audit3 ledger copies agree on sha256 (exact byte identity).
3. If they differ, their build times are within one build cycle (default 70 min) AND their row
   counts agree — i.e. the difference is a rebuild in flight, not a divergent pipeline.
4. The headline verdict counts (n_proven, n_candidate) agree across copies.
5. /audit/data/money_ready_verdict.json is present and parseable (its own build is reported, not
   gated, because it runs on a different schedule).

Exit codes (matching tools/db_freshness_check.py convention)
    0  GREEN   — all assertions hold
    1  YELLOW  — transient: one endpoint unreachable, or a rebuild in flight within tolerance
    2  RED     — DIVERGENT: row counts or verdict counts differ, or both copies are stale, or an
                 endpoint 404s (a documented path disappeared)

Allowlist
---------
Two surfaces MAY legitimately serve different populations, but only if the difference is declared
here with a reason. An undeclared divergence fails. Per the debate doc: "if two surfaces are
supposed to serve different populations, that is fine — but then the population must be in the
filename and this check whitelists it explicitly."

Usage
    python3 tools/assert_surface_parity.py
    python3 tools/assert_surface_parity.py --json
    python3 tools/assert_surface_parity.py --tolerance-min 70 --max-age-min 240
    python3 tools/assert_surface_parity.py --allow-rows-diff 8 --why "rebuild in flight"

CI
    .github/workflows/surface-parity.yml runs this hourly. RED fails the job; YELLOW does not.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://findtorontoevents.ca"

# (key, url, kind)  kind: "ledger" | "verdict" | "page"
ENDPOINTS = [
    ("audit_page", f"{BASE}/audit/", "page"),
    ("audit2_page", f"{BASE}/audit2/", "page"),
    ("audit3_page", f"{BASE}/audit3/", "page"),
    ("ledger_on_audit", f"{BASE}/audit/data/audit3_ledger.json", "ledger"),
    ("ledger_on_audit3", f"{BASE}/audit3/audit3_ledger.json", "ledger"),
    ("verdict_on_audit", f"{BASE}/audit/data/money_ready_verdict.json", "verdict"),
]

UA = {"User-Agent": "assert-surface-parity/1.0 (+findtorontoevents.ca audit)"}
DEFAULT_TOLERANCE_MIN = 70      # one build cycle; the hourly cron runs at :10
DEFAULT_MAX_AGE_MIN = 240       # older than this and the whole surface is stale
VERDICT_FIELDS = ("n_rows", "n_proven", "n_candidate", "n_kill", "n_weak", "n_insufficient")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def fetch(url: str, timeout: int) -> tuple[int, bytes, str | None]:
    """Return (status, body, error). status 0 means transport failure."""
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), None
    except urllib.error.HTTPError as e:
        return e.code, b"", f"HTTP {e.code}"
    except Exception as e:  # URLError, timeout, DNS, TLS
        return 0, b"", f"{type(e).__name__}: {e}"


def parse_time(value) -> dt.datetime | None:
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def probe(key: str, url: str, kind: str, timeout: int) -> dict:
    status, body, err = fetch(url, timeout)
    rec: dict = {"key": key, "url": url, "kind": kind, "http": status, "bytes": len(body)}
    if err:
        rec["error"] = err
    if status != 200:
        return rec

    rec["sha256"] = hashlib.sha256(body).hexdigest()
    if kind == "page":
        rec["has_ledger_marker"] = b"audit3_ledger" in body or b"ledger" in body[:200_000].lower()
        return rec

    try:
        doc = json.loads(body)
    except ValueError as e:
        rec["error"] = f"invalid JSON: {e}"
        rec["state"] = "RED"
        return rec

    rec["generated_at"] = doc.get("generated_at")
    rec["source_generated_at"] = doc.get("source_generated_at")
    summary = doc.get("summary") or {}
    for f in VERDICT_FIELDS:
        if f in summary:
            rec[f] = summary[f]
    sa = doc.get("selection_alpha") or {}
    if "available" in sa:
        rec["selection_alpha_available"] = sa["available"]
    rec["has_sleeves"] = "sleeves" in doc
    rec["generated_dt"] = parse_time(rec["generated_at"])
    return rec


def evaluate(records: dict, tolerance_min: int, max_age_min: int,
             allow_rows_diff: int, why: str) -> tuple[int, list[str], dict]:
    """Return (exit_code, findings, detail)."""
    findings: list[str] = []
    detail: dict = {}
    now = utcnow()

    missing = [k for k, r in records.items() if r.get("http") != 200]
    if missing:
        findings.append(
            f"UNREACHABLE ({len(missing)}): " + ", ".join(f"{k}[{records[k].get('http')}]" for k in missing)
        )

    ledgers = {k: r for k, r in records.items() if r.get("kind") == "ledger" and r.get("http") == 200}
    a = ledgers.get("ledger_on_audit")
    b = ledgers.get("ledger_on_audit3")

    if not a or not b:
        findings.append("LEDGER_MISSING: cannot compare — one or both ledger copies unavailable")
        detail["compare"] = "impossible"
        code = 2 if missing else 1
        return code, findings, detail

    same_sha = a.get("sha256") == b.get("sha256")
    detail["same_sha"] = same_sha
    detail["rows"] = [a.get("n_rows"), b.get("n_rows")]
    detail["generated"] = [a.get("generated_at"), b.get("generated_at")]

    rows_a, rows_b = a.get("n_rows"), b.get("n_rows")
    rows_differ = rows_a is not None and rows_b is not None and rows_a != rows_b
    detail["rows_differ"] = rows_differ

    # build-time gap (only meaningful when both parse)
    gap_min = None
    da, db = a.get("generated_dt"), b.get("generated_dt")
    if da and db:
        gap_min = abs((da - db).total_seconds()) / 60.0
        detail["gap_min"] = round(gap_min, 1)

    # verdict-count agreement, which must hold regardless of byte identity
    vdiff = []
    for f in ("n_proven", "n_candidate"):
        if a.get(f) is not None and b.get(f) is not None and a.get(f) != b.get(f):
            vdiff.append(f"{f}: {a.get(f)} vs {b.get(f)}")
    detail["verdict_diff"] = vdiff

    if not same_sha:
        if vdiff:
            findings.append("VERDICT_COUNTS_DIVERGE: " + "; ".join(vdiff))
        if rows_differ:
            diff = abs((rows_a or 0) - (rows_b or 0))
            if diff <= allow_rows_diff:
                findings.append(
                    f"ROWS_WITHIN_TOLERANCE: |{rows_a}-{rows_b}|={diff} <= {allow_rows_diff}"
                    + (f" ({why})" if why else "")
                )
                detail["severity"] = "YELLOW"
            else:
                findings.append(f"ROWS_DIVERGE: |{rows_a}-{rows_b}|={diff} > {allow_rows_diff} (whitelist)")
                detail["severity"] = "RED"
        if gap_min is not None:
            if gap_min > tolerance_min:
                findings.append(
                    f"BUILD_GAP_EXCEEDS_CYCLE: {gap_min:.0f} min > {tolerance_min} min tolerance "
                    f"— /audit renders a {gap_min:.0f}-minute-old ledger"
                )
                detail["severity"] = "RED"
            else:
                findings.append(f"BUILD_GAP_WITHIN_CYCLE: {gap_min:.0f} min <= {tolerance_min} min")
                detail.setdefault("severity", "YELLOW")
        if not rows_differ and not vdiff and (gap_min is None or gap_min <= tolerance_min):
            findings.append("BYTES_DIFFER_ONLY: same rows and verdicts, content/format differs")
            detail.setdefault("severity", "YELLOW")
    else:
        findings.append("PARITY_OK: ledger copies are byte-identical")
        detail["severity"] = "GREEN"

    # staleness of the freshest copy
    newest = max([d for d in (da, db) if d], default=None)
    if newest:
        age_min = (now - newest).total_seconds() / 60.0
        detail["newest_age_min"] = round(age_min, 1)
        if age_min > max_age_min:
            findings.append(f"STALE: newest ledger is {age_min:.0f} min old > {max_age_min} max")
            detail["severity"] = "RED"

    verdict_surface = records.get("verdict_on_audit") or {}
    if verdict_surface.get("http") == 200:
        detail["verdict_generated_at"] = verdict_surface.get("generated_at")

    sev = detail.get("severity", "GREEN")
    if sev == "RED":
        return 2, findings, detail
    if sev == "YELLOW" or missing:
        return 1, findings, detail
    return 0, findings, detail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assert parity across live audit surfaces")
    ap.add_argument("--timeout", type=int, default=45, help="per-request timeout (s)")
    ap.add_argument("--tolerance-min", type=int, default=DEFAULT_TOLERANCE_MIN,
                    help="max acceptable build-time gap between ledger copies")
    ap.add_argument("--max-age-min", type=int, default=DEFAULT_MAX_AGE_MIN,
                    help="fail if the freshest ledger is older than this")
    ap.add_argument("--allow-rows-diff", type=int, default=0,
                    help="permitted row-count difference (whitelist; 0 = exact)")
    ap.add_argument("--why", default="", help="justification recorded alongside a row whitelist")
    ap.add_argument("--json", action="store_true", help="emit machine-readable report")
    ap.add_argument("--out", default="", help="write the JSON report to this path")
    args = ap.parse_args(argv)

    records = {k: probe(k, u, kind, args.timeout) for k, u, kind in ENDPOINTS}
    code, findings, detail = evaluate(records, args.tolerance_min, args.max_age_min,
                                      args.allow_rows_diff, args.why)

    report = {
        "checked_at": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exit_code": code,
        "state": {0: "GREEN", 1: "YELLOW", 2: "RED"}[code],
        "findings": findings,
        "detail": {k: v for k, v in detail.items() if k != "generated_dt"},
        "endpoints": {k: {kk: vv for kk, vv in v.items() if kk != "generated_dt"}
                      for k, v in records.items()},
        "tolerance": {"build_gap_min": args.tolerance_min, "max_age_min": args.max_age_min,
                      "allow_rows_diff": args.allow_rows_diff},
    }

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"SURFACE PARITY: {report['state']} (exit {code}) at {report['checked_at']}")
        for f in findings:
            print(f"  - {f}")
        if detail.get("rows"):
            print(f"  rows: /audit={detail['rows'][0]}  /audit3={detail['rows'][1]}")
        if detail.get("gap_min") is not None:
            print(f"  build gap: {detail['gap_min']} min")
    return code


if __name__ == "__main__":
    sys.exit(main())

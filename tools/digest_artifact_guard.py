#!/usr/bin/env python3
"""digest_artifact_guard.py — fail any published digest whose bytes are not retrievable.

Why this exists
---------------
A published digest (``rows_sha256``) is only a reconciliation key if the exact
bytes it hashes can be fetched back later. The audit surfaces publish digests
(ledger ``63609da5…``, dashboard_data ``ed25b59c…``, live /audit ``e346e65f…``)
but the rows sidecar they describe is not committed and is overwritten on the
live host, so most published digests are uncheckable after the fact.

This guard reads a manifest of published digests and, for each one, resolves
its artifact and recomputes the digest over the artifact's rows. It is
deliberately read-only: no DB, no rebuild, no writes.

Contract (four outcomes per published digest)
---------------------------------------------
* ``PASS``  — artifact retrievable and the recomputed digest matches.
* ``FAIL``  — digest published but no artifact is retrievable (missing ref,
              path absent, fetch failed, or the artifact carries no rows).
* ``FAIL``  — artifact retrievable but the recomputed digest differs.
* ``SKIP``  — the manifest publishes no digests at all. Explicitly NOT a pass.

The canonical digest is the one defined by ``alpha_engine/resolved_closed_view``:
rows sorted by ``closed_at``, serialized with ``sort_keys=True`` and
``separators=(",", ":")``, UTF-8, SHA-256.

Usage
-----
    python tools/digest_artifact_guard.py                     # offline, default manifest
    python tools/digest_artifact_guard.py --online            # also fetch url: refs
    python tools/digest_artifact_guard.py --json              # machine-readable

Exit codes: 0 = PASS or SKIP, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO / "reports" / "published_digests_manifest.json"

OUTCOME_PASS = "PASS"
OUTCOME_FAIL = "FAIL"
OUTCOME_SKIP = "SKIP"

# Failure reasons, all collapsed under the single FAIL outcome.
REASON_NO_ARTIFACT = "no_artifact"
REASON_UNRETRIEVABLE = "artifact_unretrievable"
REASON_NO_ROWS = "artifact_has_no_rows"
REASON_MISMATCH = "hash_mismatch"


def canonical_rows_digest(rows: list[dict]) -> str:
    """SHA-256 of the canonical row set, exactly as resolved_closed_view.build_view."""
    ordered = sorted(rows, key=lambda r: (r.get("closed_at") or ""))
    blob = json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _extract_rows(payload: bytes):
    """Rows from an artifact payload (``{"rows": [...]}`` or a bare list). None if absent."""
    try:
        doc = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return None
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        rows = doc.get("rows")
        if isinstance(rows, list):
            return rows
    return None


def evaluate(manifest: dict, resolve) -> dict:
    """Pure: manifest + artifact resolver -> per-digest results and an aggregate verdict.

    ``resolve(ref) -> bytes | None`` maps an artifact reference to its payload.
    """
    entries = manifest.get("digests") or []
    results = []
    for entry in entries:
        name = entry.get("surface") or entry.get("name") or "?"
        published = str(entry.get("digest") or "")
        ref = entry.get("artifact")

        if not ref:
            results.append({
                "surface": name, "outcome": OUTCOME_FAIL, "reason": REASON_NO_ARTIFACT,
                "published_digest": published, "artifact": None, "actual_digest": None,
            })
            continue

        payload = resolve(ref)
        if payload is None:
            results.append({
                "surface": name, "outcome": OUTCOME_FAIL, "reason": REASON_UNRETRIEVABLE,
                "published_digest": published, "artifact": ref, "actual_digest": None,
            })
            continue

        rows = _extract_rows(payload)
        if rows is None:
            results.append({
                "surface": name, "outcome": OUTCOME_FAIL, "reason": REASON_NO_ROWS,
                "published_digest": published, "artifact": ref, "actual_digest": None,
            })
            continue

        actual = canonical_rows_digest(rows)
        ok = bool(published) and actual == published
        results.append({
            "surface": name, "outcome": OUTCOME_PASS if ok else OUTCOME_FAIL,
            "reason": None if ok else REASON_MISMATCH,
            "published_digest": published, "artifact": ref, "actual_digest": actual,
            "rows": len(rows),
        })

    if not entries:
        verdict = OUTCOME_SKIP
        note = "no digests published in the manifest — SKIP is not a pass"
    elif any(r["outcome"] == OUTCOME_FAIL for r in results):
        verdict = OUTCOME_FAIL
        note = "at least one published digest is unretrievable or does not match its artifact"
    else:
        verdict = OUTCOME_PASS
        note = "every published digest has a retrievable artifact that matches"

    return {
        "schema": "digest_artifact_guard.v1",
        "manifest": manifest.get("schema"),
        "verdict": verdict,
        "note": note,
        "n_digests": len(entries),
        "n_pass": sum(1 for r in results if r["outcome"] == OUTCOME_PASS),
        "n_fail": sum(1 for r in results if r["outcome"] == OUTCOME_FAIL),
        "results": results,
    }


def make_resolver(*, online: bool = False, timeout: int = 60, root: Path = REPO):
    """Artifact resolver.

    References:
      * ``url:https://…``  — fetched only when ``online`` (offline => unretrievable)
      * ``file:PATH``      — read from disk (relative to ``root``)
      * anything else      — treated as a path (relative to ``root``)
    """

    def resolve(ref: str):
        ref = str(ref)
        if ref.startswith("url:"):
            if not online:
                return None
            url = ref[len("url:"):]
            # The live audit host answers HTTP 412 to urllib's default agent
            # (verified 2026-11-22), so send a real one or every url: ref would
            # be a false "unretrievable".
            req = urllib.request.Request(url, headers={"User-Agent": "digest-artifact-guard/1"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    return resp.read()
            except Exception:
                return None
        path = ref[len("file:"):] if ref.startswith("file:") else ref
        p = Path(path)
        if not p.is_absolute():
            p = root / p
        try:
            return p.read_bytes() if p.is_file() else None
        except OSError:
            return None

    return resolve


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail any published digest with no retrievable artifact.")
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--online", action="store_true", help="also fetch url: artifact refs")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = ap.parse_args(argv)

    path = Path(args.manifest)
    if not path.is_absolute():
        path = REPO / path
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"::error title=digest_artifact_guard::manifest not found: {path}")
        return 1
    except ValueError as exc:
        print(f"::error title=digest_artifact_guard::manifest is not valid JSON: {exc}")
        return 1

    report = evaluate(manifest, make_resolver(online=args.online, timeout=args.timeout))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"# digest artifact guard — verdict={report['verdict']} ({report['note']})")
        for r in report["results"]:
            detail = r.get("reason") or "match"
            print(f"  {r['outcome']:4s} {r['surface']}: {detail} "
                  f"published={str(r['published_digest'])[:12]} "
                  f"actual={str(r['actual_digest'])[:12]} artifact={r['artifact']}")
    return 0 if report["verdict"] in (OUTCOME_PASS, OUTCOME_SKIP) else 1


if __name__ == "__main__":
    sys.exit(main())

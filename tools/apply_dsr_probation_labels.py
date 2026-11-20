#!/usr/bin/env python3
"""Label strategies below the DSR floor PROBATION, keeping every row and its n.

The anti-overfit gate flags 74 of 80 strategies at DSR < 0.95, and the gate is
supposed to fail -- that is the honest answer, not a bug. What was missing is a
publication label: a demoted strategy has to stay visible, with its sample size,
so the failure can be audited later. Deleting or filtering the row would make the
gate's own output unauditable, and would silently change what the ledger claims.

So this tool only writes labels:

    publication_label   PUBLISHABLE  (dsr >= threshold)
                        PROBATION    (dsr <  threshold)
                        UNRATED      (dsr is null/unavailable)
    publication_reason  the arithmetic behind the label
    publication_dsr_threshold

Rows, n, PF, WR and every other field are left byte-identical. Dry run by
default; --apply writes and keeps a timestamped .bak.

Usage:
    python3 tools/apply_dsr_probation_labels.py
    python3 tools/apply_dsr_probation_labels.py --apply
    python3 tools/apply_dsr_probation_labels.py --path audit_dashboard/data/anti_overfit_audit.json
    python3 tools/apply_dsr_probation_labels.py --dsr-threshold 0.90
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import shutil
import sys

DEFAULT_PATH = "audit_dashboard/data/anti_overfit_audit.json"


def label_for(dsr, threshold: float) -> tuple[str, str]:
    """(label, reason) for one strategy. A label, never a filter."""
    if dsr is None:
        return "UNRATED", "DSR unavailable -- cannot be demoted or published"
    try:
        value = float(dsr)
    except (TypeError, ValueError):
        return "UNRATED", "DSR not numeric (%r)" % (dsr,)
    if value >= threshold:
        return "PUBLISHABLE", "DSR %.4f >= %.2f" % (value, threshold)
    return "PROBATION", "DSR %.4f < %.2f" % (value, threshold)


def apply_labels(payload: dict, threshold: float = 0.95) -> dict:
    """Stamp labels in place on a payload's strategy rows; return the payload."""
    rows = payload.get("strategies") or []
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        label, reason = label_for(row.get("dsr"), threshold)
        row["publication_label"] = label
        row["publication_reason"] = reason
        row["publication_dsr_threshold"] = threshold
        counts[label] += 1
    payload["publication_label_counts"] = dict(counts)
    payload["publication_label_rule"] = (
        "label only -- a PROBATION strategy keeps its row and its n in this "
        "payload; nothing is deleted or filtered, so the demotion stays auditable"
    )
    payload["publication_labelled_at"] = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return payload


def check_payload(payload: dict, threshold: float = 0.95) -> list[str]:
    """Problems that mean the labels no longer describe the rows."""
    issues: list[str] = []
    rows = payload.get("strategies") or []
    if not rows:
        return ["payload has no strategies"]
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        label = row.get("publication_label")
        name = row.get("strategy", "?")
        if label not in ("PUBLISHABLE", "PROBATION", "UNRATED"):
            issues.append("%s: no publication label (row is unlabelled)" % name)
            continue
        counts[label] += 1
        want, _ = label_for(row.get("dsr"), row.get("publication_dsr_threshold", threshold))
        if label != want:
            issues.append("%s: labelled %s but dsr=%s implies %s"
                          % (name, label, row.get("dsr"), want))
    stated = {k: v for k, v in (payload.get("publication_label_counts") or {}).items() if v}
    actual = {k: v for k, v in counts.items() if v}
    if stated != actual:
        issues.append("published counts %r != actual %r" % (stated, actual))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=DEFAULT_PATH, help="payload to label")
    ap.add_argument("--dsr-threshold", type=float, default=0.95,
                    help="DSR floor for PUBLISHABLE (default 0.95)")
    ap.add_argument("--apply", action="store_true", help="write the labels")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any row lacks a label or the stated counts disagree")
    args = ap.parse_args()

    path = pathlib.Path(args.path)
    if not path.is_absolute():
        path = pathlib.Path(__file__).resolve().parents[1] / path
    if not path.is_file():
        print("no payload at %s" % path, file=sys.stderr)
        return 2

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows_before = len(payload.get("strategies") or [])
    ns_before = [r.get("n") for r in payload.get("strategies") or []]

    if args.check:
        problems = check_payload(payload, args.dsr_threshold)
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            print("LABEL DRIFT: %d problem(s) in %s" % (len(problems), path), file=sys.stderr)
            return 1
        print("labels consistent: %d rows, %s"
              % (rows_before, payload.get("publication_label_counts")))
        return 0

    payload = apply_labels(payload, args.dsr_threshold)

    rows_after = len(payload.get("strategies") or [])
    ns_after = [r.get("n") for r in payload.get("strategies") or []]
    if rows_after != rows_before or ns_after != ns_before:
        print("REFUSING: labelling changed the row set or the n column "
              "(%d -> %d rows)" % (rows_before, rows_after), file=sys.stderr)
        return 3

    counts = payload["publication_label_counts"]
    print("rows=%d (unchanged)  threshold=%.2f" % (rows_after, args.dsr_threshold))
    for label in ("PUBLISHABLE", "PROBATION", "UNRATED"):
        if counts.get(label):
            print("  %-12s %3d" % (label, counts[label]))
    example = next((r for r in payload["strategies"]
                    if r.get("publication_label") == "PROBATION"), None)
    if example:
        print("  example: %s n=%s %s"
              % (example.get("strategy"), example.get("n"), example.get("publication_reason")))

    if not args.apply:
        print("dry run; pass --apply to write (a .bak is kept)")
        return 0

    bak = path.with_suffix(path.suffix + ".bak-" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S"))
    shutil.copy2(path, bak)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("wrote %s (backup %s)" % (path, bak.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

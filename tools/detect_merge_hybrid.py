#!/usr/bin/env python3
"""Detect a generated JSON artifact that a textual merge has hybridised.

`git pull --no-rebase -X ours` merges generated JSON line by line. When both
sides touched the same region the merge keeps both copies of a row, or keeps a
stale header beside a new body. Both leave the same fingerprint: the payload
disagrees with itself -- a declared count no longer matches the rows it
describes, or a row appears twice.

Usage:
  detect_merge_hybrid.py --staged            # files staged for the next commit
  detect_merge_hybrid.py --rev-range A..B    # JSON touched by a commit/range
  detect_merge_hybrid.py path/a.json ...
Options:
  --under DIR ...   only inspect paths beneath these prefixes
Exit 0 clean, 1 hybridised.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# A field only counts an array if it *names* that array. `n_fdr_pass=4` beside
# five `top_sleeves` rows means "4 of these 5 passed", not "the array holds 4
# rows" -- treating subset tallies as row counts flagged 172 of 251 clean
# artifacts, which would have made this gate useless. See
# reports/2026-11-20-generated-artifact-hybrid-scan.md.
COUNT_PREFIXES = ("n_", "num_", "count_", "total_")
COUNT_SUFFIXES = ("_audited", "_count", "_total", "_length", "_len", "_size", "_n", "_rows")
COUNT_BARE = ("count", "total", "length", "len", "size", "rows", "items", "n")
IDENTITY = ("strategy", "symbol", "id", "name", "ticker", "pair", "slug", "key", "asset",
            "source", "model", "agent")
# 2026-11-21: raised 12 -> 64 MB. The two largest generated artifacts are
# audit_dashboard/data/pf_registry.json (15.9 MB: 0.06 s to load, 0.11 s to
# inspect, ~56 MB RSS) and alpha_engine/data/expired_picks_archive.json
# (32.1 MB: 0.11 s, ~136 MB RSS). At 12 MB both were skipped, so they were
# committed hourly without being gated at all. The cap is there to stop a
# runaway file, not to skip real ones -- and anything still over it is now named
# in a WARNING line, so a skip cannot be silent.
MAX_BYTES = 64 * 1024 * 1024
# A merge of generated JSON is off by the rows it duplicated or resurrected: a
# handful, never half the file. A wide difference is a different record set, not
# a hybrid, so it is left alone -- this gate must never block a clean run.
NEAR_MISS = 5


def iter_arrays(doc):
    """Yield (path, container, rows) for object arrays up to two levels deep."""
    def walk(node, prefix, depth):
        if depth > 2 or not isinstance(node, dict):
            return
        for k, v in node.items():
            label = "%s.%s" % (prefix, k) if prefix else k
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                yield label, node, v
            elif isinstance(v, dict):
                yield from walk(v, label, depth + 1)
    yield from walk(doc, "", 0)


def _names_array(field, array_name):
    """Does this count field claim to count `array_name` itself?"""
    f = field.lower()
    if f in COUNT_BARE:
        return True
    for prefix in COUNT_PREFIXES:
        if f.startswith(prefix):
            f = f[len(prefix):]
            break
    changed = True
    while changed:
        changed = False
        for suffix in COUNT_SUFFIXES:
            if f.endswith(suffix):
                f = f[: -len(suffix)]
                changed = True
    a = array_name.lower()
    stem = a[:-1] if a.endswith("s") else a
    return f in (a, stem + "s", stem) or f == a.replace("_", "")


def identity_key(rows):
    """The field that names a row, if the array has one."""
    for key in IDENTITY:
        if sum(1 for r in rows if key in r) >= max(2, int(0.9 * len(rows))):
            return key
    return None


def _hashable(value):
    # Some payloads carry a list or dict where a name belongs.
    return json.dumps(value, sort_keys=True, default=str)


def inspect(doc):
    """Return the payload's self-contradictions; empty means consistent."""
    findings = []
    for label, container, rows in iter_arrays(doc):
        n = len(rows)
        count_problem = False
        for k, v in container.items():
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                continue
            if not _names_array(k, label.split(".")[-1]):
                continue
            if v != n and abs(v - n) <= NEAR_MISS:
                findings.append("%s: declares %s=%d but holds %d rows" % (label, k, v, n))
                count_problem = True
        key = identity_key(rows)
        if not key:
            continue
        # A row without the identity key is not part of any group. Indexing it
        # raised KeyError on real data (expired_picks_archive.json carries rows
        # both with and without `symbol`), which a 12 MB cap had been hiding by
        # never letting that file be inspected at all.
        groups = {}
        for r in rows:
            if key not in r:
                continue
            groups.setdefault(_hashable(r[key]), []).append(r)
        for group in groups.values():
            if len(group) < 2:
                continue
            shown = str(group[0].get(key))[:60]
            identical = len({_hashable(g) for g in group}) == 1
            if identical:
                findings.append("%s: %r appears %d times byte-identical"
                                % (label, shown, len(group)))
            elif count_problem:
                findings.append("%s: %r appears %d times with differing values"
                                % (label, shown, len(group)))
    return findings


def targets(args):
    if args.staged:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                             capture_output=True, text=True).stdout
    elif args.rev_range:
        out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACMR", args.rev_range],
                             capture_output=True, text=True).stdout
    else:
        out = "\n".join(args.paths)
    files = [p for p in out.split() if p.endswith(".json")]
    if args.under:
        files = [p for p in files
                 if any(p.startswith(u.rstrip("/") + "/") for u in args.under)]
    return files



# --- committed audit trail ---------------------------------------------------
# A passing gate is otherwise invisible: its only output is one line in a
# 60-minute job log, and GitHub expires those. --report writes the counts into a
# small JSON file the workflow commits, so "what was gated, and how much of it"
# is answerable from the repository alone.
REPORT_SCHEMA = 2
REPORT_MAX_ENTRIES = 50
# The newest entry carries the paths it actually opened; older entries keep only
# the count. That answers "was this file gated?" without letting 50 entries of
# paths grow without bound -- 500 paths is ~30 KB, and an excess is counted, not
# silently dropped.
REPORT_MAX_PATHS = 500


def record(report_path, *, phase, rev_range, inspected, skipped, findings, verdict,
           inspected_paths=None):
    """Append or update this run's entry in the committed gate report.

    Keyed by (GITHUB_RUN_ID, phase, rev_range) and deliberately carrying no
    timestamp: a retry that observes the same numbers rewrites identical bytes, so
    the workflow's `git diff --quiet` guard does not manufacture another commit.

    Only the entry being written keeps its inspected paths; every older entry is
    rotated down to its count. The rotation runs before the append, over *all*
    entries, so writing the same entry twice still produces the same bytes.
    """
    path = Path(report_path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        doc = {}
    entries = [e for e in (doc.get("entries") or []) if isinstance(e, dict)]
    for e in entries:
        e.pop("inspected_paths", None)
        e.pop("inspected_paths_truncated", None)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    key = (run_id, phase, rev_range or "")
    entries = [e for e in entries
               if (e.get("run_id"), e.get("phase"), e.get("rev_range") or "") != key]
    paths = list(inspected_paths or [])
    entry = {
        "run_id": run_id,
        "phase": phase,
        "rev_range": rev_range,
        "inspected": inspected,
        "inspected_paths": paths[:REPORT_MAX_PATHS],
        "skipped": [{"path": q, "mb": round(mb, 1)} for q, mb in skipped],
        "findings": findings,
        "verdict": verdict,
    }
    if len(paths) > REPORT_MAX_PATHS:
        entry["inspected_paths_truncated"] = len(paths) - REPORT_MAX_PATHS
    entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": REPORT_SCHEMA,
                                "tool": "tools/detect_merge_hybrid.py",
                                "entries": entries[-REPORT_MAX_ENTRIES:]},
                               indent=2) + "\n", encoding="utf-8")

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--rev-range", default=None)
    ap.add_argument("--under", nargs="*", default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--report", default=None,
                    help="write an audit entry (counts, skips, verdict) to this "
                         "JSON file; the workflow commits it")
    ap.add_argument("--max-mb", type=float, default=MAX_BYTES / 1048576,
                    help="size cap per artifact in MB (default %.0f); larger files are "
                         "skipped and reported as NOT gated" % (MAX_BYTES / 1048576))
    args = ap.parse_args(argv)

    files = targets(args)
    if not files:
        print("no JSON artifacts to inspect")
        return 0
    max_bytes = int(args.max_mb * 1024 * 1024)
    bad = 0
    inspected = 0
    inspected_paths = []
    skipped = []
    for p in files:
        f = Path(p)
        if not f.exists():
            continue
        if f.stat().st_size > max_bytes:
            skipped.append((p, f.stat().st_size / 1048576))
            print("skip %s (%.1f MB, over the %.0f MB cap) -- NOT gated"
                  % (p, f.stat().st_size / 1048576, max_bytes / 1048576))
            continue
        try:
            doc = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            print("%s: not valid JSON (%s) -- a merge may have cut it" % (p, exc))
            bad += 1
            continue
        inspected += 1
        inspected_paths.append(p)
        found = inspect(doc)
        if found:
            bad += 1
            print("%s: HYBRIDISED -- %d contradiction(s)" % (p, len(found)))
            for line in found:
                print("   " + line)
    if skipped:
        print("\nWARNING: %d artifact(s) were NOT gated (over the %.0f MB cap): %s"
              % (len(skipped), max_bytes / 1048576,
                 ", ".join("%s (%.1f MB)" % (q, mb) for q, mb in skipped)),
              file=sys.stderr)
    if args.report:
        record(args.report,
               phase="staged" if args.staged else ("rev-range" if args.rev_range else "paths"),
               rev_range=args.rev_range,
               inspected=inspected, inspected_paths=inspected_paths,
               skipped=skipped, findings=bad,
               verdict="hybridised" if bad else "clean")
    if bad:
        print("\nREFUSING: %d generated artifact(s) disagree with themselves. A textual "
              "merge has hybridised them -- regenerate or restore before commit." % bad)
        return 1
    if not args.quiet:
        print("no hybridised artifacts (%d inspected)" % inspected)
    return 0

if __name__ == "__main__":
    sys.exit(main())

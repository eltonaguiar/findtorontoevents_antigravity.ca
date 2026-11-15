#!/usr/bin/env python3
"""Read-only GitHub Actions sprawl audit.

Counts workflows, scheduled workflows, push-to-main writers, cron density, and
duplicate names so the sprawl recommendation in 04_SUGGESTED_FIXES.md can be
re-measured at any time.

Usage (from repo root):
    python3 GHACTIONS_PR_ISSUES/<stamp>/06_PATCHES/audit_workflow_sprawl.py
"""
from __future__ import annotations

import os
import re
from collections import Counter, defaultdict

WF_DIR = ".github/workflows"


def main() -> int:
    files = sorted(
        os.path.join(WF_DIR, n)
        for n in os.listdir(WF_DIR)
        if os.path.isfile(os.path.join(WF_DIR, n))
    )
    active, parked = [], []
    for f in files:
        if f.endswith((".disabled", ".retired", ".draft", ".md")):
            parked.append(f)
        elif f.endswith((".yml", ".yaml")):
            active.append(f)

    cron_minute = Counter()
    sched = push = dispatch = push_main = 0
    names = []
    for f in active:
        text = open(f, encoding="utf-8", errors="ignore").read()
        m = re.search(r"^\s*name:\s*(.+)$", text, re.M)
        names.append((os.path.basename(f), m.group(1).strip() if m else "?"))
        if re.search(r"^\s*schedule:", text, re.M):
            sched += 1
        if re.search(r"^\s*push:", text, re.M):
            push += 1
        if "workflow_dispatch" in text:
            dispatch += 1
        if re.search(r"git push|safe_push|safe_commit", text):
            push_main += 1
        for c in re.findall(r"cron:\s*[\"']([^\"']+)[\"']", text):
            parts = c.split()
            if len(parts) >= 2:
                cron_minute[parts[1]] += 1

    seen = defaultdict(list)
    for fn, nm in names:
        seen[nm.lower()].append(fn)
    dups = {k: v for k, v in seen.items() if len(v) > 1}

    print(f"active workflows      : {len(active)}")
    print(f"parked (.disabled/..): {len(parked)}")
    print(f"with schedule         : {sched}")
    print(f"with push: trigger    : {push}")
    print(f"can workflow_dispatch : {dispatch}")
    print(f"push to main (code)   : {push_main}")
    print("\ntop cron minutes (load spikes):")
    for mn, c in cron_minute.most_common(10):
        print(f"  minute {mn:>3}: {c} workflows")
    print(f"\nduplicate workflow names: {len(dups)}")
    for k, v in dups.items():
        print(f"  {k} -> {v}")

    if push_main > 1:
        print(
            f"\nWARNING: {push_main} workflows can push to main. "
            "Serialize them under one concurrency group to stop rebase storms."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

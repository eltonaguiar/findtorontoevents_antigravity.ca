#!/usr/bin/env python3
"""Workflow masking-policy linter.

Detects "silent maskers": .github/workflows steps that use
`continue-on-error: true` WITHOUT emitting a `::warning` to surface the swallowed
failure (the "green but lying" pattern). Driven by .github/masking_manifest.yaml:

  approved      — intentional maskers (documented exit-code semantics etc.); ignored.
  known_silent  — existing baseline, grandfathered in.

Default: report-only (exit 0). With --fail-on-new: exit 1 only when a workflow has
coe>0 / ::warning==0, is NOT approved, and is NOT in the baseline — i.e. a NEWLY
introduced silent masker. So existing maskers never break CI; new ones are caught.

Usage:
  python scripts/lint_workflow_masking.py            # report
  python scripts/lint_workflow_masking.py --fail-on-new   # CI gate (PR-only)
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None


def _count(txt: str, needle: str) -> int:
    return txt.count(needle)


def scan(workflows_dir: str, manifest: dict) -> dict:
    approved = {a["workflow"] for a in (manifest.get("approved") or []) if isinstance(a, dict) and a.get("workflow")}
    baseline = set(manifest.get("known_silent") or [])
    files = sorted(glob.glob(os.path.join(workflows_dir, "*.yml")) +
                   glob.glob(os.path.join(workflows_dir, "*.yaml")))
    rows, silent_new, silent_baselined = [], [], []
    for f in files:
        txt = open(f, errors="replace").read()
        coe = _count(txt, "continue-on-error: true") + _count(txt, "continue-on-error: True")
        warn = _count(txt, "::warning")
        b = os.path.basename(f)
        if coe == 0:
            continue
        status = "ok"
        if b in approved:
            status = "approved"
        elif warn > 0:
            status = "warn_surfaced"
        else:
            status = "silent"
            (silent_baselined if b in baseline else silent_new).append(b)
        rows.append({"workflow": b, "coe": coe, "warn": warn, "status": status})
    return {"rows": rows, "silent_new": silent_new, "silent_baselined": silent_baselined}


def load_manifest(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML required to read the manifest")
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".github/workflows")
    ap.add_argument("--manifest", default=".github/masking_manifest.yaml")
    ap.add_argument("--fail-on-new", action="store_true",
                    help="exit 1 if any NEW (non-baselined, non-approved) silent masker exists")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    res = scan(args.dir, manifest)
    rows = res["rows"]
    n_silent = len(res["silent_new"]) + len(res["silent_baselined"])
    print(f"[masking-lint] {len(rows)} workflows with continue-on-error; "
          f"{n_silent} silent ({len(res['silent_baselined'])} baselined, {len(res['silent_new'])} NEW)")
    if res["silent_new"]:
        print("[masking-lint] NEW silent maskers (add a ::warning naming the stale file, "
              "or flip continue-on-error:false, or baseline in masking_manifest.yaml):")
        for b in res["silent_new"]:
            print(f"  - {b}")
    if args.fail_on_new and res["silent_new"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

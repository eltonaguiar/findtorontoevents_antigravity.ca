#!/usr/bin/env python3
"""Audit GitHub Actions health across the repos this project deploys from.

Three questions, in the order they matter:

1. RECOVERED OR NOT — a failure only matters if nothing succeeded afterwards.
   For every workflow, find the most recent failure and ask whether any later
   run succeeded. A failure with a later success is history; one without is a
   live break.

2. SELDOM/NEVER RUNS — workflows whose last run is older than N days, or that
   have no runs at all in the fetched window, are dormant. Either the cron is
   wrong, the trigger is unreachable, or the workflow is dead weight.

3. STRUCTURALLY SKIPPED — steps and jobs gated on a condition that can never be
   true in CI (`if: false`, a `vars.*` nobody sets, a push trigger with no push
   paths matched). Detected from the workflow YAML, because a skipped step
   reports "skipped" rather than failing, so run statistics never surface it.

Usage:
    python3 tools/gha_stale_and_skipped_audit.py [--repos a/b,c/d] [--days 30]
                                                 [--pages 10] [--json out.json]

Requires the `gh` CLI authenticated with read access to Actions.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPOS = [
    "eltonaguiar/findtorontoevents_antigravity.ca",
    "eltonaguiar/findtorontoevents.ca",
    "eltonaguiar/TORONTOEVENTS_ANTIGRAVITY",
    "eltonaguiar/STOCKSUNIFY2",
]

# `if:` fragments that are false in CI for most or all runs.
NEVER_TRUE = re.compile(
    r"^\s*if:\s*(false|False|'\s*'|\"\s*\"|0)\s*$"
    r"|^\s*if:\s*\$\{\{\s*false\s*\}\}\s*$",
    re.MULTILINE,
)
# A gate on a repository variable nobody has set: silently always-false.
VARS_GATE = re.compile(r"\$\{\{\s*vars\.([A-Za-z0-9_]+)\s*(?:\|\|[^}]*)?\}\}")
SECRETS_GATE = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}")


def gh_json(path: str):
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode != 0:
        msg = proc.stderr.strip().splitlines()
        return None, (msg[0] if msg else "gh api failed")
    return json.loads(proc.stdout), None


def fetch_runs(repo: str, pages: int) -> tuple[list[dict], str | None]:
    runs: list[dict] = []
    for page in range(1, pages + 1):
        data, err = gh_json(f"repos/{repo}/actions/runs?per_page=100&page={page}")
        if err:
            return runs, err
        batch = data.get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            break
    return runs, None


def fetch_workflows(repo: str) -> tuple[list[dict], str | None]:
    out: list[dict] = []
    for page in range(1, 6):
        data, err = gh_json(f"repos/{repo}/actions/workflows?per_page=100&page={page}")
        if err:
            return out, err
        batch = data.get("workflows", [])
        out.extend(batch)
        if len(batch) < 100:
            break
    return out, None


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def analyse_runs(runs: list[dict]) -> dict:
    """Per-workflow: latest failure that no later run recovered."""
    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_wf[r["name"]].append(r)
    rows = []
    for name, rs in by_wf.items():
        rs.sort(key=lambda r: r["created_at"])
        last = rs[-1]
        failures = [r for r in rs if r["conclusion"] == "failure"]
        unrecovered = []
        for f in failures:
            later_ok = any(
                r["conclusion"] == "success" and r["created_at"] > f["created_at"]
                for r in rs
            )
            if not later_ok:
                unrecovered.append(f)
        rows.append({
            "name": name,
            "runs": len(rs),
            "last_run": last["created_at"],
            "last_conclusion": last["conclusion"] or last["status"],
            "failures": len(failures),
            "unrecovered_failures": len(unrecovered),
            "last_unrecovered_failure": unrecovered[-1]["created_at"] if unrecovered else None,
            "last_success": next(
                (r["created_at"] for r in reversed(rs) if r["conclusion"] == "success"), None
            ),
        })
    return rows


def scan_yaml(repo_dir: Path | None, workflow_path: str) -> list[str]:
    """Structural skip signals for one workflow file."""
    if not repo_dir:
        return []
    path = repo_dir / workflow_path
    if not path.is_file():
        return []
    text = path.read_text(errors="replace")
    findings = []
    if NEVER_TRUE.search(text):
        findings.append("has a literal `if: false` guard")
    vars_used = sorted(set(VARS_GATE.findall(text)))
    if vars_used:
        findings.append("gates on vars." + ", vars.".join(vars_used))
    if re.search(r"^\s*on:\s*\n(?:\s+[^\n]*\n)*?\s+workflow_dispatch:", text, re.MULTILINE) and \
       not re.search(r"^\s+schedule:", text, re.MULTILINE):
        findings.append("dispatch-only (never runs on its own)")
    if "continue-on-error: true" in text:
        findings.append("has continue-on-error steps (failures swallowed)")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default=",".join(DEFAULT_REPOS))
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--json", default="")
    ap.add_argument("--max-lookups", type=int, default=250,
                    help="cap per-workflow last-run API lookups per repo")
    args = ap.parse_args()

    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    now = datetime.now(timezone.utc)
    report = {"generated_at": now.isoformat(), "repos": {}}

    for repo in repos:
        wfs, wf_err = fetch_workflows(repo)
        runs, run_err = fetch_runs(repo, args.pages)
        if run_err:
            print(f"{repo}: {run_err}", file=sys.stderr)
            continue
        stats = analyse_runs(runs)
        local = Path.cwd() if (Path.cwd() / ".github" / "workflows").is_dir() else None

        print(f"\n{'='*78}\n{repo}  ({len(runs)} runs fetched, {len(wfs)} workflows registered)")
        if run_err:
            print(f"  !! {run_err}")

        print("\n-- UNRECOVERED FAILURES (nothing succeeded after them) --")
        broken = sorted(
            [s for s in stats if s["unrecovered_failures"]],
            key=lambda s: s["last_unrecovered_failure"] or "",
            reverse=True,
        )
        if not broken:
            print("  none")
        for s in broken:
            print(f"  {s['last_unrecovered_failure'][:16]}  {s['last_conclusion']:9} "
                  f"{s['name'][:52]:52} fails={s['failures']}/{s['runs']} "
                  f"last_success={s['last_success'][:16] if s['last_success'] else 'NONE'}")

        print(f"\n-- DORMANT (no run in {args.days}+ days) --")
        seen = {s["name"] for s in stats}
        dormant = []
        for s in stats:
            age = (now - parse_ts(s["last_run"])).days
            if age >= args.days:
                dormant.append((s["name"], s["last_run"], age))
        # A workflow absent from the fetched window is NOT necessarily dormant:
        # the window may be one busy day. Ask the API for its true last run.
        unscanned = 0
        for w in wfs:
            if w["name"] in seen or w["state"] != "active":
                continue
            if unscanned >= args.max_lookups:
                print(f"  ... {args.max_lookups} per-workflow lookups hit; remaining unscanned")
                break
            unscanned += 1
            data, err = gh_json(
                f"repos/{repo}/actions/workflows/{w['id']}/runs?per_page=1"
            )
            runs_w = (data or {}).get("workflow_runs") or []
            if not runs_w:
                dormant.append((w["name"], "never run", -2))
                continue
            last = runs_w[0]["created_at"]
            age = (now - parse_ts(last)).days
            if age >= args.days:
                dormant.append((w["name"], last, age))
        if not dormant:
            print("  none")
        for name, when, age in sorted(dormant, key=lambda d: d[1]):
            label = {(True): 'never'}.get(age < -1, "n/r") if age < 0 else f"{age}d"
            print(f"  {label:>6}  {name[:56]:56} last={when[:16]}")

        print("\n-- STRUCTURALLY SKIPPED / GATED --")
        gated = []
        for w in wfs:
            findings = scan_yaml(local, w.get("path", ""))
            if findings:
                gated.append((w["name"], w["path"], findings))
        if not gated:
            print("  none found in local checkout (run from the repo root for YAML checks)")
        for name, path, findings in gated[:40]:
            print(f"  {name[:44]:44} {'; '.join(findings)}")

        report["repos"][repo] = {
            "runs_fetched": len(runs),
            "workflows_registered": len(wfs),
            "unrecovered": broken,
            "dormant": [{"name": n, "last": w, "age_days": a} for n, w, a in dormant],
            "gated": [{"name": n, "path": p, "findings": f} for n, p, f in gated],
        }

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Per-workflow RUN matrix for every registered GitHub Actions workflow.

`tools/gha_local_run_check.py` answers "does this workflow parse and would its
steps plausibly resolve?" — static. This tool answers the different question the
operator actually cares about: **has this workflow ever run, and did it work?**

For every workflow GitHub has registered on the repo it pulls the real run
history from `gh run list --workflow=<file> --branch main` and classifies it:

  GREEN_RECENT   latest main run succeeded                      -> ran, works
  RED_REGRESSION latest run failed but an earlier one succeeded  -> ran, broke later
  ALWAYS_RED     every run in the window failed                 -> never worked
  NEVER_RUN      no run recorded for this workflow at all       -> never validated
  SCHEDULE_ONLY  no dispatchable trigger and no run             -> cannot verify on demand
  DISABLED       workflow is manually disabled                   -> out of scope

Output: reports/GHA_PER_WORKFLOW_RUN_MATRIX.{md,json}, one checkbox per workflow
(so the operator has a literal todo per workflow), plus a `--dispatch-missing`
mode that triggers the dispatchable NEVER_RUN / ALWAYS_RED ones.

Usage:
    python3 tools/gha_workflow_run_matrix.py                 # write the matrix
    python3 tools/gha_workflow_run_matrix.py --dispatch-missing --limit 10
    python3 tools/gha_workflow_run_matrix.py --class NEVER_RUN   # filter
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS = REPO_ROOT / "reports"
JSON_OUT = REPORTS / "GHA_PER_WORKFLOW_RUN_MATRIX.json"
MD_OUT = REPORTS / "GHA_PER_WORKFLOW_RUN_MATRIX.md"

CLASSES = ["GREEN_RECENT", "RED_REGRESSION", "ALWAYS_RED", "NEVER_RUN",
           "SCHEDULE_ONLY", "DISABLED"]


def gh(args: list[str], timeout: int = 90) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:400])
    return r.stdout


def list_workflows() -> list[dict]:
    out = gh(["workflow", "list", "--all", "--limit", "600",
              "--json", "name,path,state,id"])
    wfs = json.loads(out)
    for w in wfs:                       # path is "dynamic/name.yml" for newer uploads
        p = w["path"]
        w["file"] = p.split("/")[-1]
    return sorted(wfs, key=lambda w: w["file"])


def triggers(file: str) -> set[str]:
    """Parse `on:` straight from the file so we know what can be dispatched."""
    path = REPO_ROOT / ".github" / "workflows" / file
    if not path.exists():
        return set()
    try:
        import yaml
        doc = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return set()
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on.keys())
    return set()


def runs_for(file: str, limit: int = 8) -> list[dict]:
    try:
        out = gh(["run", "list", "--workflow", file, "--branch", "main",
                  "--limit", str(limit),
                  "--json", "conclusion,status,createdAt,headSha,databaseId,event"])
        return json.loads(out)
    except Exception:
        return []


def classify(wf: dict, runs: list[dict]) -> dict:
    file = wf["file"]
    done = [r for r in runs if r.get("conclusion")]
    latest = done[0] if done else None
    successes = [r for r in done if r["conclusion"] == "success"]
    trig = triggers(file)

    if wf["state"] == "disabled_manually":
        cls = "DISABLED"
    elif not done:
        cls = "NEVER_RUN" if ("workflow_dispatch" in trig or "push" in trig) else "SCHEDULE_ONLY"
    elif latest and latest["conclusion"] == "success":
        cls = "GREEN_RECENT"
    elif successes:
        cls = "RED_REGRESSION"
    else:
        cls = "ALWAYS_RED"

    if cls in ("NEVER_RUN", "ALWAYS_RED", "RED_REGRESSION"):
        if "workflow_dispatch" in trig:
            action = f"gh workflow run {file} --ref main"
        elif "schedule" in trig:
            action = "schedule only — wait for cron, or add workflow_dispatch"
        else:
            action = "no dispatch trigger — must fire from a push/PR event"
    else:
        action = "none"

    return {
        "file": file,
        "name": wf["name"],
        "state": wf["state"],
        "triggers": sorted(trig),
        "class": cls,
        "latest_run": {
            "conclusion": latest["conclusion"] if latest else None,
            "created": latest["createdAt"][:16] if latest else None,
            "sha": latest["headSha"][:8] if latest else None,
            "id": latest["databaseId"] if latest else None,
            "event": latest["event"] if latest else None,
        },
        "runs_seen": len(done),
        "successes_seen": len(successes),
        "dispatchable": "workflow_dispatch" in trig,
        "next_action": action,
    }


def build(limit_runs: int, workers: int) -> list[dict]:
    wfs = list_workflows()
    print(f"[matrix] {len(wfs)} registered workflows; pulling run history…", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(runs_for, w["file"], limit_runs): w for w in wfs}
        rows = []
        for i, fut in enumerate(futures, 1):
            w = futures[fut]
            try:
                runs = fut.result()
            except Exception:
                runs = []
            rows.append(classify(w, runs))
            if i % 40 == 0:
                print(f"[matrix] {i}/{len(wfs)}", file=sys.stderr)
    return rows


def write_outputs(rows: list[dict]) -> None:
    REPORTS.mkdir(exist_ok=True)
    JSON_OUT.write_text(json.dumps(rows, indent=2) + "\n")

    counts = {c: sum(1 for r in rows if r["class"] == c) for c in CLASSES}
    lines = [
        "# Per-workflow run matrix — has every workflow actually run?",
        "",
        "Generated by `tools/gha_workflow_run_matrix.py`. Source: the real run",
        "history on `main` (`gh run list --workflow <file> --branch main`).",
        "This is the *execution* counterpart to `reports/gha_local_run_check.md`,",
        "which only proves the workflow parses and its scripts resolve.",
        "",
        "## Totals",
        "",
        "| Class | Count | Meaning |",
        "|---|---|---|",
    ]
    meaning = {
        "GREEN_RECENT": "latest run on main succeeded — ran, works",
        "RED_REGRESSION": "latest failed but an earlier run succeeded — ran, broke later",
        "ALWAYS_RED": "every run in the window failed — has never worked",
        "NEVER_RUN": "no run on record — never validated at all",
        "SCHEDULE_ONLY": "cron-only with no run on record — cannot dispatch to verify",
        "DISABLED": "disabled manually — out of scope",
    }
    for c in CLASSES:
        lines.append(f"| {c} | {counts[c]} | {meaning[c]} |")
    lines += ["", f"**Total workflows: {len(rows)}**", ""]

    lines += ["## Per-workflow todos", "",
              "One checkbox per workflow. `[ ]` = still needs validation,",
              "`[x]` = proven by a green run on `main`.", ""]
    for c in CLASSES:
        group = [r for r in rows if r["class"] == c]
        if not group:
            continue
        lines += [f"### {c} ({len(group)})", ""]
        for r in group:
            box = "x" if c in ("GREEN_RECENT", "DISABLED") else " "
            latest = r["latest_run"]
            if latest["conclusion"]:
                ev = f"last `{latest['conclusion']}` @ {latest['sha']} ({latest['created']}Z, {latest['event']})"
            else:
                ev = "no runs"
            trig = ", ".join(r["triggers"]) or "none"
            lines.append(f"- [{box}] `{r['file']}` — {ev}; triggers: {trig}"
                         + (f"; **next:** {r['next_action']}" if r["next_action"] != "none" else ""))
        lines.append("")

    MD_OUT.write_text("\n".join(lines) + "\n")
    print(json.dumps(counts, indent=2))
    print(f"wrote {MD_OUT.relative_to(REPO_ROOT)} and {JSON_OUT.relative_to(REPO_ROOT)}")


def dispatch_missing(rows: list[dict], limit: int, classes: set[str]) -> None:
    todo = [r for r in rows if r["class"] in classes and r["dispatchable"]]
    print(f"[dispatch] {len(todo)} dispatchable workflow(s) in {sorted(classes)}; limit {limit}",
          file=sys.stderr)
    for r in todo[:limit]:
        try:
            gh(["workflow", "run", r["file"], "--ref", "main"])
            print(f"  dispatched {r['file']}")
        except Exception as e:
            print(f"  FAILED {r['file']}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=8, help="run history depth per workflow")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--dispatch-missing", action="store_true")
    ap.add_argument("--limit", type=int, default=10, help="max dispatches")
    ap.add_argument("--class", dest="cls", action="append", default=None,
                    help="only handle this class (repeatable)")
    args = ap.parse_args()

    rows = build(args.runs, args.workers)
    write_outputs(rows)
    if args.dispatch_missing:
        dispatch_missing(rows, args.limit, set(args.cls or ["NEVER_RUN"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Phase 1 Inventory: scan all workflow YAML files for hygiene signals.

Uses PyYAML for accurate parsing. Outputs a JSON report with per-workflow:
- name, path, state (active/disabled/retired)
- triggers: schedule (list), push (bool), pull_request (bool), workflow_dispatch (bool)
- path_filters: push paths, PR paths
- concurrency: group, cancel-in-progress
- timeout-minutes per job
- issues: missing concurrency, missing timeout, no path filter on push, disabled_manually
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not available — install with: pip install pyyaml")
    sys.exit(1)

WORKFLOW_DIR = Path(".github/workflows")
OUT = Path("reports/gha_inventory_phase1.json")


def parse_workflow(path: Path) -> dict:
    """Parse a workflow YAML file and extract hygiene signals."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return {
            "name": path.stem,
            "path": str(path),
            "file": path.name,
            "state": "disabled" if ".disabled" in path.name else "retired" if ".retired" in path.name else "active",
            "parse_error": str(e),
            "triggers": {"schedule": [], "push": False, "pull_request": False, "workflow_dispatch": False},
            "push_paths": [],
            "pr_paths": [],
            "concurrency": None,
            "jobs": {},
            "issues": [{"type": "parse_error", "severity": "high", "message": f"YAML parse error: {e}"}],
        }

    if not isinstance(data, dict):
        return {
            "name": path.stem,
            "path": str(path),
            "file": path.name,
            "state": "disabled" if ".disabled" in path.name else "retired" if ".retired" in path.name else "active",
            "triggers": {"schedule": [], "push": False, "pull_request": False, "workflow_dispatch": False},
            "push_paths": [],
            "pr_paths": [],
            "concurrency": None,
            "jobs": {},
            "issues": [{"type": "not_a_mapping", "severity": "high", "message": "Workflow YAML is not a mapping"}],
        }

    name = data.get("name") or path.stem
    on = data.get("on")
    # PyYAML 1.1 interprets YAML `on` as boolean True — check both
    if on is None and True in data:
        on = data[True]

    triggers = {"schedule": [], "push": False, "pull_request": False, "workflow_dispatch": False}
    push_paths = []
    pr_paths = []

    # on can be a dict or a list of strings
    if isinstance(on, dict):
        if "schedule" in on:
            sched = on["schedule"]
            if isinstance(sched, list):
                for item in sched:
                    if isinstance(item, dict) and "cron" in item:
                        triggers["schedule"].append(item["cron"])
                    elif isinstance(item, str):
                        triggers["schedule"].append(item)
            elif isinstance(sched, str):
                triggers["schedule"].append(sched)
        if "push" in on:
            triggers["push"] = True
            push = on["push"]
            if isinstance(push, dict) and "paths" in push:
                push_paths = push["paths"] or []
        if "pull_request" in on:
            triggers["pull_request"] = True
            pr = on["pull_request"]
            if isinstance(pr, dict) and "paths" in pr:
                pr_paths = pr["paths"] or []
        if "workflow_dispatch" in on:
            triggers["workflow_dispatch"] = True
    elif isinstance(on, str):
        # Single-string trigger like `on: push` or `on: schedule`
        if on == "push":
            triggers["push"] = True
        elif on == "pull_request":
            triggers["pull_request"] = True
        elif on == "workflow_dispatch":
            triggers["workflow_dispatch"] = True
    elif isinstance(on, list):
        for item in on:
            if isinstance(item, str):
                if item == "push":
                    triggers["push"] = True
                elif item == "pull_request":
                    triggers["pull_request"] = True
                elif item == "workflow_dispatch":
                    triggers["workflow_dispatch"] = True

    concurrency = None
    if "concurrency" in data:
        conc = data["concurrency"]
        if isinstance(conc, dict):
            concurrency = {
                "group": conc.get("group"),
                "cancel_in_progress": conc.get("cancel-in-progress"),
            }
        elif isinstance(conc, str):
            concurrency = {"group": conc, "cancel_in_progress": None}

    jobs = {}
    if "jobs" in data and isinstance(data["jobs"], dict):
        for job_name, job in data["jobs"].items():
            if not isinstance(job, dict):
                continue
            timeout = job.get("timeout-minutes")
            runs_on = job.get("runs-on")
            try:
                timeout_val = int(timeout) if timeout is not None else None
            except (ValueError, TypeError):
                timeout_val = None  # expression like ${{ inputs.timeout_minutes }}
            jobs[job_name] = {
                "timeout_minutes": timeout_val,
                "runs_on": str(runs_on) if runs_on is not None else None,
            }
        return {
            "name": name,
        "path": str(path),
        "file": path.name,
        "triggers": triggers,
        "push_paths": push_paths,
        "pr_paths": pr_paths,
        "concurrency": concurrency,
        "jobs": jobs,
    }


def classify_issues(wf: dict, path: Path) -> list[dict]:
    issues = []
    triggers = wf.get("triggers", {})
    concurrency = wf.get("concurrency")
    jobs = wf.get("jobs", {})

    # Check for disabled/retired file suffix
    if ".disabled" in path.name:
        issues.append({
            "type": "disabled_manually",
            "severity": "info",
            "message": "File suffix .disabled — workflow is intentionally disabled",
        })
    if ".retired" in path.name:
        issues.append({
            "type": "retired",
            "severity": "info",
            "message": "File suffix .retired — workflow is retired",
        })

    # No triggers at all (and not disabled/retired)
    if not any([
        triggers["schedule"],
        triggers["push"],
        triggers["pull_request"],
        triggers["workflow_dispatch"],
    ]) and ".disabled" not in path.name and ".retired" not in path.name:
        issues.append({
            "type": "no_triggers",
            "severity": "critical",
            "message": "Workflow has no schedule/push/PR/dispatch trigger — will never run",
        })

    # Missing concurrency
    if not concurrency:
        issues.append({
            "type": "no_concurrency",
            "severity": "high",
            "message": "No concurrency group — runs can stack and hog the queue",
        })

    # Missing timeout on any job
    for job_name, job in jobs.items():
        if job.get("timeout_minutes") is None:
            issues.append({
                "type": "no_timeout",
                "severity": "medium",
                "message": f"Job '{job_name}' has no timeout-minutes (default 360 min)",
            })
        elif job.get("timeout_minutes", 0) > 60:
            issues.append({
                "type": "long_timeout",
                "severity": "low",
                "message": f"Job '{job_name}' timeout {job['timeout_minutes']}min > 60min",
            })

    # Push without path filter
    if triggers["push"] and not wf.get("push_paths", []):
        issues.append({
            "type": "push_no_path_filter",
            "severity": "high",
            "message": "Push trigger with no path filter — runs on every push",
        })

    return issues


def main() -> int:
    workflows = []
    for pattern in ("*.yml", "*.yml.disabled", "*.yml.retired"):
        for path in sorted(WORKFLOW_DIR.glob(pattern)):
            wf = parse_workflow(path)
            wf["state"] = (
                "disabled" if ".disabled" in path.name else
                "retired" if ".retired" in path.name else
                "active"
            )
            wf["issues"] = classify_issues(wf, path)
            workflows.append(wf)

    # Summary
    total = len(workflows)
    active = sum(1 for w in workflows if w["state"] == "active")
    disabled = sum(1 for w in workflows if w["state"] == "disabled")
    retired = sum(1 for w in workflows if w["state"] == "retired")
    no_concurrency = sum(1 for w in workflows if any(i["type"] == "no_concurrency" for i in w["issues"]))
    no_timeout = sum(1 for w in workflows if any(i["type"] == "no_timeout" for i in w["issues"]))
    push_no_filter = sum(1 for w in workflows if any(i["type"] == "push_no_path_filter" for i in w["issues"]))
    no_triggers = sum(1 for w in workflows if any(i["type"] == "no_triggers" for i in w["issues"]))
    parse_errors = sum(1 for w in workflows if any(i["type"] == "parse_error" for i in w["issues"]))

    summary = {
        "total_workflows": total,
        "active": active,
        "disabled": disabled,
        "retired": retired,
        "no_concurrency": no_concurrency,
        "no_timeout": no_timeout,
        "push_no_path_filter": push_no_filter,
        "no_triggers": no_triggers,
        "parse_errors": parse_errors,
    }

    report = {"summary": summary, "workflows": workflows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Scanned {total} workflow files")
    print(f"  Active: {active}, Disabled: {disabled}, Retired: {retired}")
    print(f"  No concurrency: {no_concurrency}")
    print(f"  No timeout: {no_timeout}")
    print(f"  Push without path filter: {push_no_filter}")
    print(f"  No triggers: {no_triggers}")
    print(f"  Parse errors: {parse_errors}")
    print(f"Report written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

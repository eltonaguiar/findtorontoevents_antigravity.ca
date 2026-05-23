#!/usr/bin/env python3
"""
GitHub Actions Debug Tool
=========================
Inspect, diagnose, and report on GitHub Actions workflow runs.

Usage:
    python gh_actions_debug.py                    # Show all recent runs
    python gh_actions_debug.py --workflow <file>  # Filter by workflow file
    python gh_actions_debug.py --run <run_id>     # Inspect a specific run
    python gh_actions_debug.py --failed           # Show only failed runs
    python gh_actions_debug.py --validate         # Validate all workflow YAMLs
    python gh_actions_debug.py --secrets          # List configured secret names

Requires:
    - GITHUB_TOKEN env var (or gh CLI authenticated)
    - git remote pointing to a GitHub repo

Works with both `gh` CLI and direct GitHub REST API (curl/urllib).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import glob as globmod
from pathlib import Path


def get_owner_repo():
    """Detect owner/repo from git remote."""
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except subprocess.CalledProcessError:
        print("ERROR: Not a git repo or no 'origin' remote found.")
        sys.exit(1)

    # Match github.com/owner/repo or github.com:owner/repo
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not m:
        print(f"ERROR: Remote URL doesn't look like GitHub: {url}")
        sys.exit(1)
    return m.group(1)


def has_gh():
    """Check if gh CLI is available and authenticated."""
    return shutil.which("gh") is not None


def gh_run(*args):
    """Run a gh CLI command and return stdout."""
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"gh error: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def api_get(owner_repo, path):
    """GET from GitHub REST API using urllib (no external deps)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("ERROR: Set GITHUB_TOKEN or GH_TOKEN env var, or install/auth gh CLI.")
        sys.exit(1)

    import urllib.request
    import urllib.error

    url = f"https://api.github.com/repos/{owner_repo}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"API error {e.code}: {e.reason}\n{body[:500]}")
        return None


def list_runs(owner_repo, workflow=None, failed_only=False, limit=15):
    """List recent workflow runs."""
    if has_gh():
        cmd = ["run", "list", "--limit", str(limit), "--json",
               "databaseId,status,conclusion,name,createdAt,headBranch,event"]
        if workflow:
            cmd += ["--workflow", workflow]
        raw = gh_run(*cmd)
        if not raw:
            return []
        runs = json.loads(raw)
    else:
        qs = f"?per_page={limit}"
        if workflow:
            # Need workflow ID first
            wfs = api_get(owner_repo, "/actions/workflows")
            if not wfs:
                return []
            wf_id = None
            for w in wfs.get("workflows", []):
                if workflow in w.get("path", "") or workflow in w.get("name", ""):
                    wf_id = w["id"]
                    break
            if wf_id:
                qs = f"?per_page={limit}"
                data = api_get(owner_repo, f"/actions/workflows/{wf_id}/runs{qs}")
            else:
                print(f"Workflow '{workflow}' not found.")
                return []
        else:
            data = api_get(owner_repo, f"/actions/runs{qs}")
        if not data:
            return []
        runs = []
        for r in data.get("workflow_runs", []):
            runs.append({
                "databaseId": r["id"],
                "status": r["status"],
                "conclusion": r.get("conclusion") or "n/a",
                "name": r["name"],
                "createdAt": r["created_at"],
                "headBranch": r.get("head_branch", ""),
                "event": r.get("event", ""),
            })

    if failed_only:
        runs = [r for r in runs if r.get("conclusion") == "failure"]

    return runs


def inspect_run(owner_repo, run_id):
    """Get detailed info about a specific run, including failed steps."""
    print(f"\n--- Run {run_id} ---")

    if has_gh():
        detail = gh_run("run", "view", str(run_id), "--json",
                        "status,conclusion,name,createdAt,updatedAt,event,headBranch,jobs")
        if detail:
            data = json.loads(detail)
            print(f"Name:       {data.get('name')}")
            print(f"Status:     {data.get('status')}")
            print(f"Conclusion: {data.get('conclusion')}")
            print(f"Event:      {data.get('event')}")
            print(f"Branch:     {data.get('headBranch')}")
            print(f"Created:    {data.get('createdAt')}")
            print(f"Updated:    {data.get('updatedAt')}")
            print()

            for job in data.get("jobs", []):
                icon = "PASS" if job.get("conclusion") == "success" else "FAIL"
                print(f"  [{icon}] Job: {job.get('name')} ({job.get('conclusion')})")
                for step in job.get("steps", []):
                    s_icon = "  ok" if step.get("conclusion") == "success" else "FAIL"
                    print(f"    [{s_icon}] Step {step.get('number')}: {step.get('name')}")

        # Show failed logs
        print("\n--- Failed step logs ---")
        log_out = gh_run("run", "view", str(run_id), "--log-failed")
        if log_out:
            # Truncate to last 100 lines if very long
            lines = log_out.split("\n")
            if len(lines) > 100:
                print(f"(showing last 100 of {len(lines)} lines)")
                lines = lines[-100:]
            print("\n".join(lines))
        else:
            print("(no failed logs or run succeeded)")
    else:
        # Use API
        data = api_get(owner_repo, f"/actions/runs/{run_id}")
        if data:
            print(f"Name:       {data.get('name')}")
            print(f"Status:     {data.get('status')}")
            print(f"Conclusion: {data.get('conclusion')}")
            print(f"Event:      {data.get('event')}")
            print(f"Branch:     {data.get('head_branch')}")
            print(f"Created:    {data.get('created_at')}")
            print(f"Updated:    {data.get('updated_at')}")

        jobs_data = api_get(owner_repo, f"/actions/runs/{run_id}/jobs")
        if jobs_data:
            print()
            for job in jobs_data.get("jobs", []):
                icon = "PASS" if job.get("conclusion") == "success" else "FAIL"
                print(f"  [{icon}] Job: {job.get('name')} ({job.get('conclusion')})")
                for step in job.get("steps", []):
                    s_icon = "  ok" if step.get("conclusion") == "success" else "FAIL"
                    print(f"    [{s_icon}] Step {step.get('number')}: {step.get('name')}")


def validate_workflows():
    """Validate all workflow YAML files in .github/workflows/."""
    workflow_dir = Path(".github/workflows")
    if not workflow_dir.exists():
        print("No .github/workflows/ directory found.")
        return

    try:
        import yaml
    except ImportError:
        print("PyYAML not installed. Install with: pip install pyyaml")
        print("Falling back to basic syntax check...")
        yaml = None

    files = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    if not files:
        print("No workflow files found.")
        return

    errors = 0
    warnings = 0

    for f in files:
        print(f"\n--- {f} ---")
        content = f.read_text(encoding="utf-8")

        # YAML parse check
        if yaml:
            try:
                data = yaml.safe_load(content)
                print("  YAML: valid")
            except yaml.YAMLError as e:
                print(f"  YAML: INVALID - {e}")
                errors += 1
                continue
        else:
            # Basic check: try json-style parse won't work, just check for tabs
            data = None
            if "\t" in content:
                print("  WARNING: File contains tabs (YAML requires spaces)")
                warnings += 1
            else:
                print("  YAML: (skipped, no pyyaml)")

        if data and isinstance(data, dict):
            # Check for common issues
            if "on" not in data and True not in data:
                print("  WARNING: No 'on' trigger defined")
                warnings += 1

            jobs = data.get("jobs", {})
            if not jobs:
                print("  WARNING: No jobs defined")
                warnings += 1

            for job_name, job in jobs.items():
                runs_on = job.get("runs-on", "")
                if not runs_on:
                    print(f"  WARNING: Job '{job_name}' has no runs-on")
                    warnings += 1

                for i, step in enumerate(job.get("steps", []), 1):
                    uses = step.get("uses", "")
                    if uses:
                        # Check for deprecated action versions
                        if "@v1" in uses or "@v2" in uses:
                            if "setup-php" not in uses:  # setup-php v2 is still current
                                print(f"  WARNING: Job '{job_name}' step {i} uses old version: {uses}")
                                warnings += 1
                        if "actions/checkout@v3" in uses:
                            print(f"  WARNING: Job '{job_name}' step {i}: checkout@v3 -> recommend @v4")
                            warnings += 1

            # Check permissions
            perms = data.get("permissions", {})
            for job_name, job in jobs.items():
                for step in job.get("steps", []):
                    run_cmd = step.get("run", "")
                    if "git push" in run_cmd and not perms.get("contents"):
                        print(f"  WARNING: Job '{job_name}' does git push but no 'permissions: contents: write'")
                        warnings += 1
                        break

    print(f"\n=== Summary: {len(files)} files, {errors} errors, {warnings} warnings ===")
    if errors > 0:
        sys.exit(1)


def list_secrets(owner_repo):
    """List configured secret names (values are never exposed)."""
    if has_gh():
        out = gh_run("secret", "list")
        if out:
            print("Configured secrets:")
            print(out)
        else:
            print("Could not list secrets (check gh auth).")
    else:
        data = api_get(owner_repo, "/actions/secrets")
        if data:
            print("Configured secrets:")
            for s in data.get("secrets", []):
                print(f"  {s['name']:40} (updated: {s.get('updated_at', 'unknown')})")
        else:
            print("Could not list secrets.")


def main():
    parser = argparse.ArgumentParser(description="GitHub Actions Debug Tool")
    parser.add_argument("--workflow", "-w", help="Filter by workflow file name")
    parser.add_argument("--run", "-r", type=int, help="Inspect a specific run ID")
    parser.add_argument("--failed", "-f", action="store_true", help="Show only failed runs")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate workflow YAML files")
    parser.add_argument("--secrets", "-s", action="store_true", help="List configured secret names")
    parser.add_argument("--limit", "-l", type=int, default=15, help="Number of runs to show (default: 15)")
    args = parser.parse_args()

    owner_repo = get_owner_repo()
    print(f"Repository: {owner_repo}")
    print(f"gh CLI:     {'available' if has_gh() else 'not found (using REST API)'}")
    print()

    if args.validate:
        validate_workflows()
        return

    if args.secrets:
        list_secrets(owner_repo)
        return

    if args.run:
        inspect_run(owner_repo, args.run)
        return

    # Default: list runs
    runs = list_runs(owner_repo, workflow=args.workflow, failed_only=args.failed, limit=args.limit)

    if not runs:
        print("No runs found." + (" (filtered: --failed)" if args.failed else ""))
        return

    print(f"{'ID':>12}  {'Status':12}  {'Conclusion':12}  {'Event':16}  {'Name':40}  {'Created'}")
    print("-" * 130)
    for r in runs:
        run_id = r.get("databaseId", "")
        status = r.get("status", "")
        conclusion = r.get("conclusion") or "n/a"
        name = r.get("name", "")[:40]
        created = r.get("createdAt", "")[:19]
        event = r.get("event", "")[:16]
        print(f"{run_id:>12}  {status:12}  {conclusion:12}  {event:16}  {name:40}  {created}")

    # Summary
    failed = [r for r in runs if r.get("conclusion") == "failure"]
    if failed:
        print(f"\n{len(failed)} failed run(s). Inspect with: python gh_actions_debug.py --run <ID>")


if __name__ == "__main__":
    main()

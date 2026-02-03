#!/usr/bin/env python3
"""
Trigger the "Scrape events" GitHub Actions workflow and poll until it completes.
Use this to re-run and debug the workflow from the command line.

Requires: GITHUB_TOKEN env var (PAT with repo + workflow scope).

Usage:
  python tools/trigger_and_watch_scrape_workflow.py          # trigger and wait
  python tools/trigger_and_watch_scrape_workflow.py --trigger # trigger only (no wait)
  python tools/trigger_and_watch_scrape_workflow.py --watch   # wait for latest run only
  python tools/trigger_and_watch_scrape_workflow.py --watch --run-id 21611695045  # monitor specific run
"""
import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from typing import Optional

OWNER = "eltonaguiar"
REPO = "findtorontoevents_antigravity.ca"
WORKFLOW_ID = "scrape-events.yml"
API_BASE = f"https://api.github.com/repos/{OWNER}/{REPO}"


def _req(method: str, url: str, token: str, data: dict = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, method=method, headers=headers)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        raise


def trigger(token: str) -> None:
    url = f"{API_BASE}/actions/workflows/{WORKFLOW_ID}/dispatches"
    _req("POST", url, token, {"ref": "main"})
    print("Workflow triggered.")


def get_run(token: str, run_id: int) -> Optional[dict]:
    url = f"{API_BASE}/actions/runs/{run_id}"
    return _req("GET", url, token)


def get_latest_run(token: str) -> Optional[dict]:
    url = f"{API_BASE}/actions/workflows/{WORKFLOW_ID}/runs?per_page=1"
    data = _req("GET", url, token)
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger and/or watch Scrape events workflow")
    parser.add_argument("--trigger", action="store_true", help="Only trigger; do not wait")
    parser.add_argument("--watch", action="store_true", help="Only wait for latest run (do not trigger)")
    parser.add_argument("--run-id", type=int, default=None, help="Monitor specific run ID (e.g. 21611695045)")
    parser.add_argument("--poll", type=int, default=15, help="Poll interval in seconds (default 15)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token and not args.watch:
        print("GITHUB_TOKEN not set. Set it or use --watch to only poll.", file=sys.stderr)
        print(f"Manual trigger: https://github.com/{OWNER}/{REPO}/actions/workflows/{WORKFLOW_ID}", file=sys.stderr)
        return 1

    if not args.watch:
        try:
            trigger(token)
        except Exception as e:
            print(f"Trigger failed: {e}", file=sys.stderr)
            return 1
        if args.trigger:
            print(f"See: https://github.com/{OWNER}/{REPO}/actions")
            return 0
        time.sleep(5)

    if not token:
        print("GITHUB_TOKEN required to poll run status.", file=sys.stderr)
        return 1

    def poll_run(run_id: Optional[int] = None) -> Optional[dict]:
        if run_id is not None:
            return get_run(token, run_id)
        return get_latest_run(token)

    target_run_id = args.run_id
    print("Waiting for run to complete...")
    while True:
        run = poll_run(target_run_id)
        if not run:
            print("No run found.", file=sys.stderr)
            return 1
        status = run.get("status")
        conclusion = run.get("conclusion")
        run_url = run.get("html_url", "")
        print(f"  Run #{run.get('run_number', '?')} (id={run.get('id')}) status={status} conclusion={conclusion or '-'}")

        if status == "completed":
            print(f"Result: {conclusion or 'unknown'}")
            print(run_url)
            return 0 if conclusion == "success" else 1
        time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())

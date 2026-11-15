"""GitHub Actions health scan — failed runs with no subsequent success.

Core question: for each workflow, is the MOST RECENT completed run a failure
with no later success? Those are the only failures that actually matter; older
failures that were followed by a green run are already resolved.

Uses the public REST API (repo is public), so it does not depend on `gh auth`.

Usage:
    python proof/gh_actions_health.py                      # human table
    python proof/gh_actions_health.py --json               # machine output
    python proof/gh_actions_health.py --repo owner/name --pages 5 --branch main

Exit code 0 = no unresolved failures, 1 = at least one workflow is red with no
subsequent success (makes it usable as a CI/watchdog gate).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict

API = "https://api.github.com"
NEUTRAL = {"cancelled", "skipped", "neutral", "stale", None}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "hermes-actions-health",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect(repo: str, pages: int, branch: str | None) -> list[dict]:
    runs: list[dict] = []
    for p in range(1, pages + 1):
        q = f"{API}/repos/{repo}/actions/runs?per_page=100&page={p}"
        if branch:
            q += f"&branch={branch}"
        try:
            data = fetch(q)
        except Exception as e:  # network / rate limit
            print(f"WARN: page {p} fetch failed: {e}", file=sys.stderr)
            break
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
    return runs


def analyse(runs: list[dict]) -> dict:
    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_wf[r.get("name") or str(r.get("workflow_id"))].append(r)

    workflows = []
    for name, rs in by_wf.items():
        rs.sort(key=lambda r: r["created_at"], reverse=True)
        completed = [r for r in rs if r.get("conclusion") not in (None,)]
        if not completed:
            continue
        last = completed[0]
        # consecutive failures at the tip (ignoring cancelled/skipped)
        streak = 0
        for r in completed:
            if r["conclusion"] in NEUTRAL:
                continue
            if r["conclusion"] == "failure":
                streak += 1
            else:
                break
        last_success = next((r for r in rs if r.get("conclusion") == "success"), None)
        workflows.append({
            "workflow": name,
            "last_conclusion": last["conclusion"],
            "last_run_at": last["created_at"],
            "consecutive_failures": streak if last["conclusion"] == "failure" else 0,
            "unresolved": last["conclusion"] == "failure",
            "last_success_at": last_success["created_at"] if last_success else None,
            "last_failing_run_id": last["id"] if last["conclusion"] == "failure" else None,
            "last_failing_url": last.get("html_url") if last["conclusion"] == "failure" else None,
            "total_runs_seen": len(rs),
        })

    workflows.sort(key=lambda w: (not w["unresolved"], -w["consecutive_failures"], w["workflow"]))
    unresolved = [w for w in workflows if w["unresolved"]]
    return {
        "workflows_seen": len(workflows),
        "unresolved_failing": len(unresolved),
        "total_consecutive_failures": sum(w["consecutive_failures"] for w in workflows),
        "workflows": workflows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="eltonaguiar/findtorontoevents_antigravity.ca")
    ap.add_argument("--pages", type=int, default=3, help="100 runs per page")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    runs = collect(a.repo, a.pages, a.branch)
    res = analyse(runs)
    res["runs_scanned"] = len(runs)

    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"repo: {a.repo}  branch: {a.branch or 'any'}  runs scanned: {len(runs)}")
        print(f"workflows: {res['workflows_seen']}   UNRESOLVED FAILING: {res['unresolved_failing']}"
              f"   total consecutive failures: {res['total_consecutive_failures']}")
        print()
        print(f"{'status':10} {'streak':>6}  {'workflow':42} last_run_at           last_success_at")
        print("-" * 118)
        for w in res["workflows"]:
            status = "RED" if w["unresolved"] else "ok"
            print(f"{status:10} {w['consecutive_failures']:>6}  {w['workflow'][:42]:42} "
                  f"{w['last_run_at'][:19]:20} {str(w['last_success_at'])[:19]}")
        if res["unresolved_failing"]:
            print("\nUnresolved (no subsequent successful run):")
            for w in res["workflows"]:
                if w["unresolved"]:
                    print(f"  - {w['workflow']}  x{w['consecutive_failures']}  {w['last_failing_url']}")

    return 1 if res["unresolved_failing"] else 0


if __name__ == "__main__":
    sys.exit(main())

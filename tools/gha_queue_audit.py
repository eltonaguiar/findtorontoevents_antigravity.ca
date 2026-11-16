#!/usr/bin/env python3
"""GHA Queue & Duration Audit (Phase 3)

Surfaces, without auto-fixing:
- Jobs/runs stuck `queued` or `pending` beyond a threshold (phantom queue)
- `in_progress` jobs running beyond a duration threshold (runner hogs)
- Workflows whose latest completed run is a failure AND no success after it
- Per-workflow duration p50/p90 from recent completed runs

Reuses scripts/actions_failure_guardian.py helpers (load_runs, gh_request).

Usage:
  python tools/gha_queue_audit.py
  python tools/gha_queue_audit.py --out reports/gha_queue_audit.json

Env:
  GITHUB_TOKEN / GH_TOKEN / GIT_PAT_CLASSIC
  GHA_AUDIT_REPO (default eltonaguiar/findtorontoevents_antigravity.ca)
  GHA_AUDIT_BRANCH (default main)
  GHA_AUDIT_PAGES (default 4)
  GHA_AUDIT_QUEUE_MINUTES (default 30)
  GHA_AUDIT_LONG_MINUTES (default 90)
  GHA_AUDIT_P90_MINUTES (default 60)  # flag workflows whose p90 exceeds this
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.actions_failure_guardian import (  # noqa: E402
    gh_request,
    load_runs,
)


def _iso_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _duration_minutes(started: str | None, completed: str | None, now: datetime) -> float:
    s = _iso_to_dt(started)
    if s is None:
        return 0.0
    e = _iso_to_dt(completed) or now
    return max(0.0, (e - s).total_seconds() / 60.0)


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _normalize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a run from either the REST API shape or the CDP-embedded
    Actions-page shape (state.status / createdAt.timestamp / enum names)."""
    def _ts(field: str, nested: str) -> str | None:
        v = run.get(field)
        if isinstance(v, str):
            return v
        obj = run.get(nested)
        if isinstance(obj, dict):
            return obj.get("timestamp")
        return None

    state = run.get("state") or {}
    status = run.get("status") or state.get("status")
    conclusion = run.get("conclusion") or state.get("conclusion")
    if isinstance(status, str) and status.startswith("WORKFLOW_RUN_STATUS_"):
        status = status.replace("WORKFLOW_RUN_STATUS_", "").lower()
    if isinstance(conclusion, str) and conclusion.startswith("WORKFLOW_RUN_CONCLUSION_"):
        conclusion = conclusion.replace("WORKFLOW_RUN_CONCLUSION_", "").lower()

    branch = run.get("head_branch") or run.get("headBranch")
    if not branch:
        b = run.get("branch")
        if isinstance(b, dict):
            branch = b.get("title") or b.get("name")
    if isinstance(branch, str) and branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/"):]

    wf_key = run.get("workflow_id") or run.get("workflowId") or run.get("workflowFilePath")

    return {
        "id": run.get("id"),
        "run_number": run.get("runNumber") or run.get("run_number"),
        "workflow_id": wf_key,
        "workflow_name": run.get("name") or run.get("workflowName"),
        "workflow_path": run.get("workflowFilePath"),
        "status": status,
        "conclusion": conclusion,
        "created_at": _ts("created_at", "createdAt"),
        "started_at": run.get("run_started_at") or _ts("created_at", "createdAt"),
        "completed_at": run.get("updated_at") or _ts("updated_at", "updatedAt"),
        "branch": branch,
        "html_url": run.get("html_url") or run.get("htmlUrl") or run.get("runUrl"),
    }


def audit(
    runs: List[Dict[str, Any]],
    now: datetime,
    queue_minutes: float,
    long_minutes: float,
    p90_minutes: float,
) -> Dict[str, Any]:
    queued_stuck: List[Dict[str, Any]] = []
    long_running: List[Dict[str, Any]] = []
    durations_by_wf: Dict[Any, List[float]] = defaultdict(list)
    latest_by_wf: Dict[Any, Dict[str, Any]] = {}

    for raw in runs:
        run = _normalize_run(raw)
        wid = run["workflow_id"]
        status = run["status"]
        dur = _duration_minutes(run["started_at"], run["completed_at"] if status == "completed" else None, now)

        if status == "completed":
            if wid is not None and dur > 0:
                durations_by_wf[wid].append(dur)
            if wid is not None:
                prev = latest_by_wf.get(wid)
                if prev is None or (run["created_at"] or "") > (prev["created_at"] or ""):
                    latest_by_wf[wid] = run
            continue

        if status in ("queued", "pending"):
            age = _duration_minutes(run["created_at"], None, now)
            if age >= queue_minutes:
                queued_stuck.append({
                    "run_id": run["id"],
                    "run_number": run["run_number"],
                    "workflow_name": run["workflow_name"],
                    "workflow_id": wid,
                    "status": status,
                    "branch": run["branch"],
                    "created_at": run["created_at"],
                    "age_minutes": round(age, 1),
                })
            continue

        if status == "in_progress":
            if dur >= long_minutes:
                long_running.append({
                    "run_id": run["id"],
                    "run_number": run["run_number"],
                    "workflow_name": run["workflow_name"],
                    "workflow_id": wid,
                    "branch": run["branch"],
                    "started_at": run["started_at"],
                    "duration_minutes": round(dur, 1),
                })

    duration_stats: List[Dict[str, Any]] = []
    for wid, vals in durations_by_wf.items():
        if not vals:
            continue
        p50 = _percentile(vals, 50)
        p90 = _percentile(vals, 90)
        if p90 >= p90_minutes:
            latest = latest_by_wf.get(wid) or {}
            duration_stats.append({
                "workflow_id": wid,
                "workflow_name": latest.get("workflow_name"),
                "n": len(vals),
                "p50_minutes": round(p50, 1),
                "p90_minutes": round(p90, 1),
                "max_minutes": round(max(vals), 1),
            })
    duration_stats.sort(key=lambda x: -x["p90_minutes"])

    failed_no_success: List[Dict[str, Any]] = []
    for wid, latest in latest_by_wf.items():
        if latest.get("status") != "completed":
            continue
        if latest.get("conclusion") in ("failure", "timed_out", "startup_failure", "stale", "action_required"):
            failed_no_success.append({
                "workflow_id": wid,
                "workflow_name": latest.get("workflow_name"),
                "run_id": latest.get("id"),
                "run_number": latest.get("run_number"),
                "conclusion": latest.get("conclusion"),
                "created_at": latest.get("created_at"),
                "html_url": latest.get("html_url"),
            })
    failed_no_success.sort(key=lambda x: x.get("created_at") or "")

    return {
        "queued_stuck": queued_stuck,
        "long_running": long_running,
        "duration_stats": duration_stats,
        "failed_no_success": failed_no_success,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/gha_queue_audit.json")
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GIT_PAT_CLASSIC")
    if not token:
        print("Missing GITHUB_TOKEN/GH_TOKEN/GIT_PAT_CLASSIC")
        return 1

    repo = os.getenv("GHA_AUDIT_REPO", "eltonaguiar/findtorontoevents_antigravity.ca")
    branch = os.getenv("GHA_AUDIT_BRANCH", "main")
    pages = int(os.getenv("GHA_AUDIT_PAGES", "4"))
    queue_minutes = float(os.getenv("GHA_AUDIT_QUEUE_MINUTES", "30"))
    long_minutes = float(os.getenv("GHA_AUDIT_LONG_MINUTES", "90"))
    p90_minutes = float(os.getenv("GHA_AUDIT_P90_MINUTES", "60"))

    runs = load_runs(repo, token, pages=pages, per_page=100)
    if not runs:
        print("::warning::queue audit: no runs returned (rate limit?) — skipping")
        return 0

    now = datetime.now(timezone.utc)
    result = audit(runs, now, queue_minutes, long_minutes, p90_minutes)

    report = {
        "generated_at": now.isoformat(),
        "repo": repo,
        "branch": branch,
        "runs_scanned": len(runs),
        "thresholds": {
            "queue_minutes": queue_minutes,
            "long_minutes": long_minutes,
            "p90_minutes": p90_minutes,
        },
        **result,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Scanned {len(runs)} runs")
    print(f"Queued stuck >{queue_minutes:.0f}m: {len(result['queued_stuck'])}")
    for e in result["queued_stuck"][:10]:
        print(f"  - {e['workflow_name']} #{e['run_number']} {e['age_minutes']}m ({e['branch']})")
    print(f"Long-running >{long_minutes:.0f}m: {len(result['long_running'])}")
    for e in result["long_running"][:10]:
        print(f"  - {e['workflow_name']} #{e['run_number']} {e['duration_minutes']}m ({e['branch']})")
    print(f"Workflows with p90 >{p90_minutes:.0f}m: {len(result['duration_stats'])}")
    for e in result["duration_stats"][:10]:
        print(f"  - {e['workflow_name']}: p50={e['p50_minutes']}m p90={e['p90_minutes']}m n={e['n']}")
    print(f"Latest-failed-no-subsequent-success: {len(result['failed_no_success'])}")
    for e in result["failed_no_success"][:15]:
        print(f"  - {e['workflow_name']} #{e['run_number']} {e['conclusion']} {e['created_at']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

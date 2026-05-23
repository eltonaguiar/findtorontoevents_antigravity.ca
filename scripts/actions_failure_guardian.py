#!/usr/bin/env python3
"""
Actions Failure Guardian

Finds failed workflow runs whose workflow/branch has not had a newer run,
and triggers rerun of failed jobs to self-heal transient failures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


API_BASE = "https://api.github.com"
BAD_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure", "stale"}


def _iso_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def gh_request(method: str, path: str, token: str, **kwargs) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "actions-failure-guardian/1.0",
    }
    return requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=30, **kwargs)


def load_runs(repo: str, token: str, pages: int, per_page: int) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    for page in range(1, pages + 1):
        resp = gh_request(
            "GET",
            f"/repos/{repo}/actions/runs",
            token,
            params={"per_page": per_page, "page": page},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch runs page {page}: {resp.status_code} {resp.text[:300]}")
        payload = resp.json()
        chunk = payload.get("workflow_runs", [])
        if not chunk:
            break
        runs.extend(chunk)
    return runs


def load_workflows(repo: str, token: str, pages: int = 5, per_page: int = 100) -> List[Dict[str, Any]]:
    workflows: List[Dict[str, Any]] = []
    for page in range(1, pages + 1):
        resp = gh_request(
            "GET",
            f"/repos/{repo}/actions/workflows",
            token,
            params={"per_page": per_page, "page": page},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch workflows page {page}: {resp.status_code} {resp.text[:300]}")
        payload = resp.json()
        chunk = payload.get("workflows", [])
        if not chunk:
            break
        workflows.extend(chunk)
        if len(chunk) < per_page:
            break
    return workflows


def find_unresolved_latest_failures(
    runs: List[Dict[str, Any]],
    target_branch: str,
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    for run in runs:
        wid = run.get("workflow_id")
        branch = run.get("head_branch")
        if wid is None or not branch:
            continue
        if target_branch and branch != target_branch:
            continue
        grouped[(int(wid), branch)].append(run)

    unresolved: List[Dict[str, Any]] = []
    for (_wid, _branch), items in grouped.items():
        items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        latest = items[0]
        if latest.get("status") != "completed":
            continue
        if latest.get("conclusion") not in BAD_CONCLUSIONS:
            continue
        unresolved.append(
            {
                "run_id": latest.get("id"),
                "run_number": latest.get("run_number"),
                "workflow_id": latest.get("workflow_id"),
                "workflow_name": latest.get("name"),
                "branch": latest.get("head_branch"),
                "conclusion": latest.get("conclusion"),
                "created_at": latest.get("created_at"),
                "html_url": latest.get("html_url"),
            }
        )

    unresolved.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return unresolved


def find_chronic_cancelled_workflows(
    runs: List[Dict[str, Any]],
    target_branch: str,
    *,
    window: int = 15,
    min_cancelled: int = 4,
    min_runs_in_window: int = 5,
    min_hours_since_success: float = 48.0,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Flag workflows that keep finishing as *cancelled* on *target_branch* with no
    recent *success* — typical of concurrency preemption, queue overload, or
    timeouts killing every run.

    Uses only runs present in *runs* (same pages as the main scan); tune
    FAILURE_GUARD_PAGES / per_page if you need a longer lookback.
    """
    now = now or datetime.now(timezone.utc)
    grouped: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    for run in runs:
        wid = run.get("workflow_id")
        branch = run.get("head_branch")
        if wid is None or not branch:
            continue
        if target_branch and branch != target_branch:
            continue
        grouped[(int(wid), branch)].append(run)

    alerts: List[Dict[str, Any]] = []
    for (wid, branch), items in grouped.items():
        items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        if not items:
            continue
        latest = items[0]
        if latest.get("status") != "completed":
            continue
        if latest.get("conclusion") != "cancelled":
            continue

        window_items = items[:window]
        if len(window_items) < min_runs_in_window:
            continue

        n_cancel = sum(
            1
            for r in window_items
            if r.get("status") == "completed" and r.get("conclusion") == "cancelled"
        )
        n_success = sum(
            1
            for r in window_items
            if r.get("status") == "completed" and r.get("conclusion") == "success"
        )
        if n_cancel < min_cancelled or n_success > 0:
            continue

        last_success_at: Optional[str] = None
        for r in items:
            if r.get("status") == "completed" and r.get("conclusion") == "success":
                last_success_at = r.get("created_at")
                break

        hours_since_success: Optional[float] = None
        if last_success_at:
            dt_succ = _iso_to_dt(last_success_at)
            if dt_succ:
                hours_since_success = (now - dt_succ).total_seconds() / 3600.0
        else:
            hours_since_success = None

        if last_success_at is not None and hours_since_success is not None:
            if hours_since_success < min_hours_since_success:
                continue

        wf_name = latest.get("name") or f"workflow-{wid}"
        alerts.append(
            {
                "workflow_id": wid,
                "workflow_name": wf_name,
                "branch": branch,
                "latest_run_id": latest.get("id"),
                "latest_created_at": latest.get("created_at"),
                "window_size": len(window_items),
                "cancelled_in_window": n_cancel,
                "success_in_window": n_success,
                "last_success_at": last_success_at,
                "hours_since_success": round(hours_since_success, 2)
                if hours_since_success is not None
                else None,
            }
        )

    alerts.sort(key=lambda x: (-(x.get("cancelled_in_window") or 0), x.get("workflow_name", "")))
    return alerts


def evaluate_workflow_health(
    workflows: List[Dict[str, Any]],
    runs: List[Dict[str, Any]],
    stale_hours: float,
    now: Optional[datetime] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    now = now or datetime.now(timezone.utc)

    latest_by_workflow: Dict[int, Dict[str, Any]] = {}
    for run in runs:
        wid = run.get("workflow_id")
        if wid is None:
            continue
        wid_i = int(wid)
        existing = latest_by_workflow.get(wid_i)
        if not existing or (run.get("created_at", "") > existing.get("created_at", "")):
            latest_by_workflow[wid_i] = run

    disabled: List[Dict[str, Any]] = []
    stale: List[Dict[str, Any]] = []
    for wf in workflows:
        wid = int(wf.get("id", 0))
        name = wf.get("name") or wf.get("path") or f"workflow-{wid}"
        path = wf.get("path", "")
        state = wf.get("state", "unknown")

        if state in {"disabled_manually", "disabled_inactivity"}:
            disabled.append(
                {
                    "workflow_id": wid,
                    "workflow_name": name,
                    "path": path,
                    "state": state,
                }
            )
            continue

        latest = latest_by_workflow.get(wid)
        if not latest:
            stale.append(
                {
                    "workflow_id": wid,
                    "workflow_name": name,
                    "path": path,
                    "state": state,
                    "created_at": None,
                    "age_hours": None,
                    "reason": "never_run",
                }
            )
            continue

        created = _iso_to_dt(latest.get("created_at"))
        if not created:
            continue
        age_h = (now - created).total_seconds() / 3600.0
        if age_h > stale_hours:
            stale.append(
                {
                    "workflow_id": wid,
                    "workflow_name": name,
                    "path": path,
                    "state": state,
                    "created_at": latest.get("created_at"),
                    "age_hours": round(age_h, 2),
                    "reason": f"latest_run_older_than_{stale_hours:.0f}h",
                }
            )

    disabled.sort(key=lambda x: (x.get("state", ""), x.get("workflow_name", "")))
    stale.sort(key=lambda x: (x.get("age_hours") is None, -(x.get("age_hours") or 0.0)))
    return disabled, stale


def rerun_failed_jobs(repo: str, token: str, run_id: int) -> tuple[bool, str]:
    resp = gh_request("POST", f"/repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs", token)
    if resp.status_code in (201, 202):
        return True, f"rerun requested ({resp.status_code})"
    return False, f"{resp.status_code}: {resp.text[:250]}"


def post_discord_summary(webhook: str, report: Dict[str, Any]) -> None:
    if not webhook:
        return
    unresolved = report.get("unresolved_failures", [])
    disabled = report.get("disabled_workflows", [])
    stale_workflows = report.get("stale_workflows", [])
    chronic_cancel = report.get("chronic_cancel_workflows", [])
    rerun_ok = [r for r in unresolved if r.get("rerun_triggered")]
    rerun_fail = [r for r in unresolved if r.get("rerun_attempted") and not r.get("rerun_triggered")]

    lines = [
        f"Scanned runs: {report.get('runs_scanned', 0)}",
        f"Unresolved failures: {len(unresolved)}",
        f"Reruns triggered: {len(rerun_ok)}",
        f"Rerun failures: {len(rerun_fail)}",
        f"Chronic cancel (no recent success): {len(chronic_cancel)}",
        f"Disabled workflows: {len(disabled)}",
        f"Stale workflows: {len(stale_workflows)}",
    ]
    if unresolved:
        lines.append("")
        lines.append("Latest unresolved:")
        for row in unresolved[:5]:
            lines.append(
                f"- {row.get('workflow_name')} #{row.get('run_number')} ({row.get('conclusion')})"
            )
    if disabled:
        lines.append("")
        lines.append("Disabled workflows:")
        for row in disabled[:5]:
            lines.append(f"- {row.get('workflow_name')} ({row.get('state')})")
    if stale_workflows:
        lines.append("")
        lines.append("Stale workflows:")
        for row in stale_workflows[:5]:
            age = row.get("age_hours")
            age_txt = f"{age:.1f}h" if isinstance(age, (int, float)) else "never"
            lines.append(f"- {row.get('workflow_name')} ({age_txt})")
    if chronic_cancel:
        lines.append("")
        lines.append("Chronic cancellations (latest=cancelled, no success in window):")
        for row in chronic_cancel[:5]:
            hs = row.get("hours_since_success")
            hs_txt = f"last ok {hs:.0f}h ago" if isinstance(hs, (int, float)) else "no success in scan"
            lines.append(
                f"- {row.get('workflow_name')} "
                f"({row.get('cancelled_in_window')}/{row.get('window_size')} cancelled, {hs_txt})"
            )

    payload = {
        "embeds": [
            {
                "title": "GitHub Actions Failure Guardian",
                "description": "\n".join(lines),
                "color": 15158332 if (unresolved or chronic_cancel) else 3066993,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    import time as _time
    for _attempt in range(3):
        try:
            r = requests.post(webhook, json=payload, timeout=10)
            if r.status_code in (200, 204):
                break
            if r.status_code == 429:
                _time.sleep(r.json().get("retry_after", 3))
                continue
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))
                continue
            break
        except Exception:
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))


## ---------------------------------------------------------------------------
#  Stale Data Watchdog
## ---------------------------------------------------------------------------

STALE_THRESHOLDS: Dict[str, float] = {
    "alpha_engine/data/active_picks.json": 3.0,
    "alpha_engine/data/contrarian_picks.json": 8.0,
    "claude_gainer_ml/tracker/short_term_active.json": 3.0,
    "battleground/data/active_picks.json": 3.0,
    "cross_aggregation/data/super_signals.json": 3.0,
}


def _get_last_commit_dt(repo: str, token: str, filepath: str) -> datetime | None:
    """Return the datetime of the most recent commit that touched *filepath*."""
    resp = gh_request(
        "GET",
        f"/repos/{repo}/commits",
        token,
        params={"path": filepath, "per_page": 1, "sha": "main"},
    )
    if resp.status_code != 200:
        return None
    commits = resp.json()
    if not commits:
        return None
    date_str = (
        commits[0]
        .get("commit", {})
        .get("committer", {})
        .get("date")
    )
    return _iso_to_dt(date_str)


def check_stale_data(repo: str, token: str) -> List[Dict[str, Any]]:
    """Check critical data files for staleness and return alerts."""
    now = datetime.now(timezone.utc)
    stale_files: List[Dict[str, Any]] = []

    for filepath, threshold_hours in STALE_THRESHOLDS.items():
        last_modified = _get_last_commit_dt(repo, token, filepath)
        if last_modified is None:
            stale_files.append({
                "file": filepath,
                "threshold_hours": threshold_hours,
                "age_hours": None,
                "reason": "file not found or API error",
            })
            continue

        age_hours = (now - last_modified).total_seconds() / 3600.0
        if age_hours > threshold_hours:
            stale_files.append({
                "file": filepath,
                "threshold_hours": threshold_hours,
                "age_hours": round(age_hours, 2),
                "reason": f"stale ({age_hours:.1f}h > {threshold_hours:.0f}h threshold)",
            })

    return stale_files


def post_discord_stale_alert(webhook: str, stale_files: List[Dict[str, Any]]) -> None:
    """Post a Discord embed listing stale data files."""
    if not webhook or not stale_files:
        return

    lines = [f"**{len(stale_files)}** critical data file(s) are stale:\n"]
    for entry in stale_files:
        age = entry.get("age_hours")
        age_str = f"{age:.1f}h" if age is not None else "unknown"
        lines.append(
            f"- `{entry['file']}` — age {age_str} "
            f"(threshold {entry['threshold_hours']:.0f}h)"
        )

    payload = {
        "embeds": [
            {
                "title": "Stale Data Watchdog Alert",
                "description": "\n".join(lines),
                "color": 15105570,  # orange
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    for _attempt in range(3):
        try:
            r = requests.post(webhook, json=payload, timeout=10)
            if r.status_code in (200, 204):
                break
            if r.status_code == 429:
                time.sleep(r.json().get("retry_after", 3))
                continue
            if _attempt < 2:
                time.sleep(2 * (_attempt + 1))
                continue
            break
        except Exception:
            if _attempt < 2:
                time.sleep(2 * (_attempt + 1))


def main() -> int:
    token = os.getenv("GIT_PAT_CLASSIC") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY", "eltonaguiar/findtorontoevents_antigravity.ca")
    branch = os.getenv("FAILURE_GUARD_BRANCH", "main")
    pages = int(os.getenv("FAILURE_GUARD_PAGES", "6"))
    per_page = int(os.getenv("FAILURE_GUARD_PER_PAGE", "100"))
    max_age_hours = float(os.getenv("FAILURE_GUARD_MAX_AGE_HOURS", "72"))
    workflow_stale_hours = float(os.getenv("FAILURE_GUARD_WORKFLOW_STALE_HOURS", "168"))
    workflow_pages = int(os.getenv("FAILURE_GUARD_WORKFLOW_PAGES", "5"))
    chronic_window = int(os.getenv("FAILURE_GUARD_CHRONIC_WINDOW", "15"))
    chronic_min_cancelled = int(os.getenv("FAILURE_GUARD_CHRONIC_MIN_CANCELLED", "4"))
    chronic_min_runs = int(os.getenv("FAILURE_GUARD_CHRONIC_MIN_RUNS", "5"))
    chronic_min_hours_no_success = float(
        os.getenv("FAILURE_GUARD_CHRONIC_MIN_HOURS_NO_SUCCESS", "48")
    )

    if not token:
        print("Missing GITHUB_TOKEN/GH_TOKEN")
        return 1

    runs = load_runs(repo, token, pages=pages, per_page=per_page)
    workflows = load_workflows(repo, token, pages=workflow_pages, per_page=100)
    unresolved = find_unresolved_latest_failures(runs, target_branch=branch)
    disabled_workflows, stale_workflows = evaluate_workflow_health(
        workflows=workflows,
        runs=runs,
        stale_hours=workflow_stale_hours,
    )
    chronic_cancel_workflows = find_chronic_cancelled_workflows(
        runs,
        target_branch=branch,
        window=chronic_window,
        min_cancelled=chronic_min_cancelled,
        min_runs_in_window=chronic_min_runs,
        min_hours_since_success=chronic_min_hours_no_success,
    )

    now = datetime.now(timezone.utc)
    for row in unresolved:
        row["rerun_attempted"] = False
        row["rerun_triggered"] = False
        row["rerun_message"] = ""

        created = _iso_to_dt(row.get("created_at"))
        age_h = ((now - created).total_seconds() / 3600.0) if created else 9999.0
        row["age_hours"] = round(age_h, 2)
        if age_h > max_age_hours:
            row["rerun_message"] = f"skipped (age {age_h:.1f}h > {max_age_hours:.1f}h)"
            continue

        run_id = int(row["run_id"])
        ok, msg = rerun_failed_jobs(repo, token, run_id)
        row["rerun_attempted"] = True
        row["rerun_triggered"] = ok
        row["rerun_message"] = msg
        # small pacing to avoid burst abuse
        time.sleep(0.4)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "branch": branch,
        "runs_scanned": len(runs),
        "workflows_scanned": len(workflows),
        "unresolved_failures_count": len(unresolved),
        "unresolved_failures": unresolved,
        "disabled_workflows_count": len(disabled_workflows),
        "disabled_workflows": disabled_workflows,
        "stale_workflows_count": len(stale_workflows),
        "stale_workflows": stale_workflows,
        "chronic_cancel_workflows_count": len(chronic_cancel_workflows),
        "chronic_cancel_workflows": chronic_cancel_workflows,
    }

    report_path = Path("reports/actions_failure_guardian.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))

    post_discord_summary(os.getenv("DISCORD_WEBHOOK_URL", ""), report)

    if disabled_workflows:
        print(f"\n[Workflow Health] Disabled workflows: {len(disabled_workflows)}")
        for row in disabled_workflows[:20]:
            print(f"  - {row['workflow_name']} ({row['state']})")
    else:
        print("\n[Workflow Health] No disabled workflows found.")

    if stale_workflows:
        print(f"[Workflow Health] Stale workflows: {len(stale_workflows)}")
        for row in stale_workflows[:20]:
            age = row.get("age_hours")
            age_txt = f"{age:.1f}h" if isinstance(age, (int, float)) else "never"
            print(f"  - {row['workflow_name']} ({age_txt})")
    else:
        print("[Workflow Health] No stale workflows above threshold.")

    if chronic_cancel_workflows:
        print(
            f"\n[Chronic cancellations] {len(chronic_cancel_workflows)} workflow(s) "
            f"(latest=cancelled, ≥{chronic_min_cancelled} in last {chronic_window}, "
            f"0 success in window, no success in {chronic_min_hours_no_success:.0f}h+):"
        )
        for row in chronic_cancel_workflows[:25]:
            hs = row.get("hours_since_success")
            hs_txt = f"{hs:.1f}h since last success" if isinstance(hs, (int, float)) else "no success in scan range"
            print(
                f"  - {row['workflow_name']}: "
                f"{row['cancelled_in_window']}/{row['window_size']} cancelled — {hs_txt}"
            )
    else:
        print("\n[Chronic cancellations] No repeating cancel + stale-success pattern on scanned runs.")

    # --- Stale Data Watchdog ---
    stale_files = check_stale_data(repo, token)
    if stale_files:
        print(f"\n[Stale Data Watchdog] {len(stale_files)} stale file(s) detected:")
        for entry in stale_files:
            print(f"  - {entry['file']}: {entry['reason']}")
        post_discord_stale_alert(os.getenv("DISCORD_WEBHOOK_URL", ""), stale_files)
    else:
        print("\n[Stale Data Watchdog] All critical data files are fresh.")

    report["stale_data"] = stale_files
    # Re-write report with stale data included
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Workflow Health Check - monitors all workflows for failures."""
import subprocess, json, sys, os
from collections import defaultdict

# Force UTF-8 output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime, timezone


def gh(cmd):
    r = subprocess.run(f"gh {cmd}", shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def find_chronic_cancelled_workflows(
    runs,
    *,
    branch="main",
    window=15,
    min_cancelled=4,
    min_runs_in_window=5,
    min_hours_since_success=48.0,
    now=None,
):
    """
    Workflows whose latest completed run on *branch* is *cancelled*, with many
    cancellations and no success in the recent window, and no successful run
    within *min_hours_since_success* in the fetched history (or never).
    """
    now = now or datetime.now(timezone.utc)
    by_name = defaultdict(list)
    for r in runs:
        if r.get("headBranch") != branch:
            continue
        by_name[r.get("workflowName") or ""].append(r)

    alerts = []
    for wf_name, items in by_name.items():
        if not wf_name:
            continue
        items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
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

        last_success_at = None
        for r in items:
            if r.get("status") == "completed" and r.get("conclusion") == "success":
                last_success_at = r.get("createdAt")
                break

        hours_since_success = None
        if last_success_at:
            dt_s = _parse_iso(last_success_at)
            if dt_s:
                hours_since_success = (now - dt_s).total_seconds() / 3600.0
        if last_success_at is not None and hours_since_success is not None:
            if hours_since_success < min_hours_since_success:
                continue

        alerts.append(
            {
                "workflow_name": wf_name,
                "latest_run_id": latest.get("databaseId"),
                "window_size": len(window_items),
                "cancelled_in_window": n_cancel,
                "success_in_window": n_success,
                "last_success_at": last_success_at,
                "hours_since_success": round(hours_since_success, 2)
                if hours_since_success is not None
                else None,
            }
        )

    alerts.sort(
        key=lambda x: (-(x.get("cancelled_in_window") or 0), x.get("workflow_name", ""))
    )
    return alerts


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*55}")
    print(f"  Workflow Health Check -- {now}")
    print(f"{'='*55}\n")

    # Get recent failures
    failures = gh('run list --status failure --limit 50 --json workflowName,databaseId,createdAt')
    broken = []
    fixed = []
    pending = []

    if not failures:
        print("No recent failures in the last 50 failure-tagged runs.\n")
    else:
        # Unique workflow names (preserving order)
        seen = {}
        for r in failures:
            name = r["workflowName"]
            if name not in seen:
                seen[name] = r["databaseId"]

        for wf_name, fail_id in seen.items():
            recent = gh(f'run list -w "{wf_name}" --limit 3 --json conclusion,databaseId,createdAt')
            if not recent:
                pending.append((wf_name, "no recent runs"))
                continue

            latest = recent[0]
            conclusion = latest.get("conclusion", "unknown")

            if conclusion == "success":
                fixed.append(wf_name)
                print(f"  [OK] {wf_name} -- FIXED")
            elif conclusion == "failure":
                rid = latest["databaseId"]
                err_r = subprocess.run(
                    f"gh run view {rid} --log-failed",
                    shell=True, capture_output=True, text=True
                )
                err_lines = []
                for line in err_r.stdout.splitlines():
                    low = line.lower()
                    if any(k in low for k in ["error", "exception", "modulenot", "keyerror", "not connected", "importerror", "no module"]):
                        cleaned = line.split("\t")[-1].strip()
                        if cleaned and "except" not in cleaned.lower():
                            err_lines.append(cleaned)
                err_summary = "; ".join(err_lines[:2]) if err_lines else "unknown error"
                broken.append((wf_name, err_summary))
                print(f"  [FAIL] {wf_name} -- STILL FAILING")
                print(f"         Error: {err_summary[:150]}")
            elif conclusion == "cancelled":
                pending.append((wf_name, "cancelled"))
                print(f"  [SKIP] {wf_name} -- CANCELLED")
            else:
                pending.append((wf_name, conclusion))
                print(f"  [????] {wf_name} -- {conclusion}")

        print(f"\n{'='*55}")
        print(f"  Summary: {len(fixed)} fixed | {len(broken)} broken | {len(pending)} pending")
        print(f"{'='*55}\n")

    if broken:
        print("BROKEN WORKFLOWS:")
        for name, err in broken:
            print(f"  - {name}: {err[:200]}")
        print()

    # --- Chronic cancellations (concurrency / timeouts; no green runs) ---
    scan_limit = int(os.environ.get("WORKFLOW_HEALTH_CHRONIC_SCAN_LIMIT", "500"))
    chronic_window = int(os.environ.get("WORKFLOW_HEALTH_CHRONIC_WINDOW", "15"))
    chronic_min_cancel = int(os.environ.get("WORKFLOW_HEALTH_CHRONIC_MIN_CANCELLED", "4"))
    chronic_min_runs = int(os.environ.get("WORKFLOW_HEALTH_CHRONIC_MIN_RUNS", "5"))
    chronic_hours = float(os.environ.get("WORKFLOW_HEALTH_CHRONIC_MIN_HOURS_NO_SUCCESS", "48"))

    all_runs = gh(
        "run list --branch main --limit %d --json workflowName,conclusion,createdAt,"
        "databaseId,status,headBranch" % scan_limit
    )
    chronic = find_chronic_cancelled_workflows(
        all_runs or [],
        branch="main",
        window=chronic_window,
        min_cancelled=chronic_min_cancel,
        min_runs_in_window=chronic_min_runs,
        min_hours_since_success=chronic_hours,
    )

    print(f"{'='*55}")
    print("  Chronic cancellations (latest=cancelled, no success in window,")
    print(f"  no successful run in {chronic_hours:.0f}h+ within last {scan_limit} runs scan)")
    print(f"{'='*55}")
    if chronic:
        for row in chronic:
            hs = row.get("hours_since_success")
            hs_txt = (
                f"{hs:.1f}h since last success"
                if isinstance(hs, (int, float))
                else "no success in scan range"
            )
            print(
                f"  [CHRONIC] {row['workflow_name']} — "
                f"{row['cancelled_in_window']}/{row['window_size']} cancelled, {hs_txt}"
            )
        print()
    else:
        print("  (none)\n")

    return len(broken) + len(chronic)

if __name__ == "__main__":
    sys.exit(main())

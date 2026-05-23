#!/usr/bin/env python3
"""Shared GitHub Actions summary collection for HTML dashboard generation."""
from __future__ import annotations

import json
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
GUARDIAN_JSON = REPO_ROOT / "reports" / "actions_failure_guardian.json"

BAD_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure", "stale"}
IN_PROGRESS_STATUSES = {"in_progress", "queued", "waiting", "pending"}

SIGNAL_LINE = re.compile(
    r"|".join(
        [
            r"##\[error\]",
            r"KeyError",
            r"NameError",
            r"ValueError",
            r"TypeError",
            r"Traceback \(most recent",
            r"Quote not found for symbol",
            r"symbol.*not found",
            r"HTTP Error 404",
            r"HTTP Error 451",
            r"403 Client Error",
            r"fatal:",
            r"unknown switch",
            r"pathspec .* did not match",
            r"merge conflict",
            r"CONFLICT \(",
            r"Could not fetch data for",
            r"All Binance endpoints failed",
            r"CIRCUIT BREAKER",
            r"STALE payload",
            r"Process completed with exit code",
            r"submodule",
            r"No url found for submodule",
        ]
    ),
    re.I,
)

ERROR_WARNING_LINE = re.compile(r"\b(error|warning)\b", re.I)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def run_gh(
    args: List[str],
    *,
    timeout: int = 120,
    retries: int = 3,
) -> Tuple[int, str, str]:
    cmd = ["gh", *args]
    delay = 2.0
    for attempt in range(retries):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 1, "", "timeout"
        except FileNotFoundError:
            return 127, "", "gh CLI not found"
        if proc.returncode == 0:
            return 0, proc.stdout, proc.stderr
        err = (proc.stderr or proc.stdout or "").lower()
        if attempt < retries - 1 and (
            "rate limit" in err or "403" in err or "429" in err or "secondary rate" in err
        ):
            time.sleep(delay)
            delay *= 2
            continue
        return proc.returncode, proc.stdout, proc.stderr
    return 1, "", "gh failed after retries"


def gh_json(args: List[str], *, timeout: int = 120) -> List | Dict:
    code, out, err = run_gh(args, timeout=timeout)
    if code != 0:
        raise RuntimeError(err or out or "gh command failed: " + " ".join(args))
    if not (out or "").strip():
        return []
    return json.loads(out)


def gh_api_json(repo: str, api_path: str) -> dict:
    code, out, err = run_gh(["api", f"repos/{repo}{api_path}"])
    if code != 0:
        raise RuntimeError(err or out or f"gh api failed: {api_path}")
    return json.loads(out)


def list_all_workflows(repo: str) -> List[Dict[str, Any]]:
    workflows: List[Dict[str, Any]] = []
    page = 1
    while True:
        data = gh_api_json(repo, f"/actions/workflows?per_page=100&page={page}")
        batch = data.get("workflows") or []
        workflows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return workflows


def fetch_bulk_runs(
    repo: str,
    branch: str,
    limit: int = 600,
) -> List[Dict[str, Any]]:
    """Bulk run list for chronic / unresolved detection."""
    code, out, err = run_gh(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,workflow_id,status,conclusion,createdAt,headBranch,url,name",
        ],
        timeout=180,
    )
    if code != 0 or not out.strip():
        return []
    rows = json.loads(out)
    normalized = []
    for r in rows:
        normalized.append(
            {
                "id": r.get("databaseId"),
                "databaseId": r.get("databaseId"),
                "workflow_id": r.get("workflow_id"),
                "workflow_name": r.get("workflowName") or r.get("name"),
                "name": r.get("workflowName") or r.get("name"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "created_at": r.get("createdAt"),
                "createdAt": r.get("createdAt"),
                "head_branch": r.get("headBranch"),
                "headBranch": r.get("headBranch"),
                "html_url": r.get("url"),
                "url": r.get("url"),
            }
        )
    return normalized


def fetch_recent_runs(
    repo: str,
    workflow_name: str,
    branch: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    code, out, _ = run_gh(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "-w",
            workflow_name,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,status,conclusion,createdAt,updatedAt,url,headBranch",
        ],
        timeout=90,
    )
    if code != 0 or not (out or "").strip():
        return []
    return json.loads(out)


def find_unresolved_latest_failures(
    runs: List[Dict[str, Any]],
    target_branch: str,
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    for run in runs:
        wid = run.get("workflow_id")
        branch = run.get("head_branch") or run.get("headBranch")
        if wid is None or not branch:
            continue
        if target_branch and branch != target_branch:
            continue
        grouped[(int(wid), branch)].append(run)

    unresolved: List[Dict[str, Any]] = []
    for (_wid, _branch), items in grouped.items():
        items.sort(key=lambda r: r.get("created_at") or r.get("createdAt") or "", reverse=True)
        latest = items[0]
        if latest.get("status") != "completed":
            continue
        if latest.get("conclusion") not in BAD_CONCLUSIONS:
            continue
        unresolved.append(
            {
                "run_id": latest.get("id") or latest.get("databaseId"),
                "workflow_id": latest.get("workflow_id"),
                "workflow_name": latest.get("workflow_name") or latest.get("name"),
                "branch": _branch,
                "conclusion": latest.get("conclusion"),
                "created_at": latest.get("created_at") or latest.get("createdAt"),
                "html_url": latest.get("html_url") or latest.get("url"),
            }
        )
    unresolved.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return unresolved


def find_chronic_cancelled_workflows(
    runs: List[Dict[str, Any]],
    *,
    branch: str = "main",
    window: int = 15,
    min_cancelled: int = 4,
    min_runs_in_window: int = 5,
    min_hours_since_success: float = 48.0,
    now: Optional[datetime] = None,
    group_by_workflow_name: bool = False,
) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    by_key: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for r in runs:
        br = r.get("head_branch") or r.get("headBranch")
        if branch and br != branch:
            continue
        if group_by_workflow_name:
            key = r.get("workflow_name") or r.get("workflowName") or r.get("name") or ""
        else:
            wid = r.get("workflow_id")
            if wid is None:
                continue
            key = (int(wid), br or branch)
        if not key:
            continue
        by_key[key].append(r)

    alerts: List[Dict[str, Any]] = []
    for key, items in by_key.items():
        items.sort(key=lambda x: x.get("created_at") or x.get("createdAt") or "", reverse=True)
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
                last_success_at = r.get("created_at") or r.get("createdAt")
                break

        hours_since_success = None
        if last_success_at:
            dt_s = parse_iso(last_success_at)
            if dt_s:
                hours_since_success = (now - dt_s).total_seconds() / 3600.0
        if last_success_at is not None and hours_since_success is not None:
            if hours_since_success < min_hours_since_success:
                continue

        wf_name = (
            latest.get("workflow_name")
            or latest.get("workflowName")
            or latest.get("name")
            or (key if isinstance(key, str) else f"workflow-{key[0]}")
        )
        alerts.append(
            {
                "workflow_id": latest.get("workflow_id"),
                "workflow_name": wf_name,
                "branch": br if (br := latest.get("head_branch") or latest.get("headBranch")) else branch,
                "latest_run_id": latest.get("id") or latest.get("databaseId"),
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


def classify_failure(log_tail: str) -> str:
    s = log_tail.lower()
    if "access denied" in s and "ejaguiar1_" in s:
        return "ENV — MySQL password/secret (check trailing newline in gh secret set)"
    if "sync complete:" in s and "upserted" in s and "errors" in s:
        return "BROKEN — sync mostly OK but exit 1 on dedup/upsert errors (see mysql_trading_sync.py)"
    if "github pages" in s or "pages deployment" in s or "ensure github pages" in s:
        return "ENV — GitHub Pages not enabled on repo"
    if "name or service not known" in s or "gaierror" in s:
        return "ENV — FTP_HOST / DNS misconfigured in secrets"
    if "not connected" in s and "mput" in s:
        return "ENV — FTP session dropped (mirror host creds or TLS)"
    if "exit code 128" in s and "git" in s:
        return "FLAKY — git push/rebase race during auto-commit"
    if "invalid username or token" in s:
        return "ENV — GH_PAT / token permissions for Pages deploy"
    if "filenotfounderror" in s and "dashboard_data.json" in s:
        return "BROKEN — missing dashboard_data.json (generated by audit-dashboard pipeline)"
    if "integrity check failed" in s and "no healthy fallback" in s:
        return "BROKEN — stale tmp/backtest_forward_drift_analysis.json or no backtest baselines"
    if "input required and not supplied: server" in s:
        return "ENV — FTP server secret missing in workflow"
    return "UNKNOWN — needs manual log review"


def fetch_log_excerpt(
    run_id: int,
    repo: str,
    *,
    max_full_log_lines: int = 120,
    timeout: int = 120,
) -> str:
    code, out, err = run_gh(
        ["run", "view", str(run_id), "--repo", repo, "--log-failed"],
        timeout=timeout,
    )
    text = (out or "") + (err or "")
    if text.strip():
        return text
    code2, out2, err2 = run_gh(
        ["run", "view", str(run_id), "--repo", repo, "--log"],
        timeout=timeout,
    )
    full = (out2 or "") + (err2 or "")
    lines = full.splitlines()
    if len(lines) <= max_full_log_lines:
        return full
    return "\n".join(lines[-max_full_log_lines:])


def scan_log_for_issues(
    run_id: int,
    repo: str,
    *,
    log_timeout: int = 120,
    max_samples: int = 25,
) -> Dict[str, Any]:
    log = fetch_log_excerpt(run_id, repo, timeout=log_timeout)
    error_count = 0
    warning_count = 0
    sample_lines: List[str] = []
    critical_signals: List[str] = []

    for line in log.splitlines():
        if SIGNAL_LINE.search(line):
            s = line.strip()
            if len(s) > 400:
                s = s[:400] + "…"
            if s not in critical_signals:
                critical_signals.append(s)
            if len(critical_signals) >= max_samples:
                break

    for line in log.splitlines():
        low = line.lower()
        if re.search(r"\berror\b", low):
            error_count += 1
        if re.search(r"\bwarning\b", low):
            warning_count += 1
        if ERROR_WARNING_LINE.search(line):
            s = line.strip()
            if len(s) > 400:
                s = s[:400] + "…"
            if s and s not in sample_lines:
                sample_lines.append(s)
            if len(sample_lines) >= max_samples:
                break

    tail = log.splitlines()[-12:]
    classification = classify_failure("\n".join(tail))

    return {
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_signals": critical_signals[:max_samples],
        "sample_lines": sample_lines[:max_samples],
        "classification": classification,
        "log_tail": "\n".join(tail[-12:]) if tail else "",
    }


def load_guardian_cache(max_age_minutes: int = 90) -> Optional[Dict[str, Any]]:
    if not GUARDIAN_JSON.exists():
        return None
    try:
        data = json.loads(GUARDIAN_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    gen = parse_iso(data.get("generated_at"))
    if not gen:
        return None
    age_min = (datetime.now(timezone.utc) - gen).total_seconds() / 60.0
    if age_min > max_age_minutes:
        return None
    return data


def normalize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": run.get("databaseId") or run.get("id"),
        "status": run.get("status") or "",
        "conclusion": run.get("conclusion") or "",
        "created_at": run.get("createdAt") or run.get("created_at") or "",
        "updated_at": run.get("updatedAt") or run.get("updated_at") or "",
        "url": run.get("url") or run.get("html_url") or "",
    }


def workflow_shard(name: str, shard: int, shards: int) -> bool:
    if shards <= 1:
        return True
    import hashlib

    h = int(hashlib.md5(name.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
    return (h % shards) == shard


def build_stale_workflow_set(guardian: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Map workflow_name -> reason (never_run, stale_168h, etc.)."""
    out: Dict[str, str] = {}
    if not guardian:
        return out
    for row in guardian.get("stale_workflows") or []:
        name = row.get("workflow_name") or ""
        if name:
            out[name] = row.get("reason") or "stale"
    return out


def should_scan_logs(run: Dict[str, Any], *, skip_logs: bool) -> bool:
    if skip_logs:
        return False
    st = (run.get("status") or "").lower()
    if st in IN_PROGRESS_STATUSES:
        return True
    if st == "completed":
        conc = (run.get("conclusion") or "").lower()
        return conc not in ("success", "skipped", "")
    return False

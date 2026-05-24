#!/usr/bin/env python3
"""
GitHub Actions Health Monitor
- Checks every 15 minutes for failures
- Deep dives into failures
- Logs to ___HELL_HEALTH_OPENCODE.MD
- Skips next check if investigation is complex
"""

import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path("/home/eaguiar2015/findtorontoevents_antigravity.ca")
LOG_FILE = WORKSPACE_ROOT / "___HELL_HEALTH_OPENCODE.MD"
STATE_FILE = WORKSPACE_ROOT / ".github/gh_monitor_state.json"

COMPLEX_FAILURE_PATTERNS = [
    "Access denied",
    "Authentication failed",
    "database",
    "MySQL",
    "git push",
    "exit code 128",
    "RPC failed",
]

def run_gh_command(cmd: str) -> str:
    """Run gh CLI command and return output."""
    result = subprocess.run(
        f"gh {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"gh command failed: {cmd}")
    return result.stdout.strip()

def get_recent_runs() -> list:
    """Get recent GitHub Actions runs."""
    output = run_gh_command(
        "run list --limit 60 --json databaseId,status,conclusion,name,workflowName,headBranch,updatedAt,url "
        "--jq 'sort_by(.updatedAt) | reverse'"
    )
    return json.loads(output) if output else []

def get_failure_logs(run_id: str) -> str:
    """Get detailed logs for a failed run."""
    result = subprocess.run(
        f"gh run view {run_id} --log",
        shell=True,
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.stdout + result.stderr

def is_complex_failure(logs: str) -> bool:
    """Determine if failure requires deep investigation."""
    logs_lower = logs.lower()
    return any(pattern.lower() in logs_lower for pattern in COMPLEX_FAILURE_PATTERNS)

def load_state() -> dict:
    """Load monitor state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_check": None,
        "last_failure_check": {},
        "skip_next": False,
        "skip_reason": None,
        "total_checks": 0,
        "total_failures": 0
    }

def save_state(state: dict):
    """Save monitor state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def format_failure_report(run: dict, logs: str) -> str:
    """Format a detailed failure report."""
    report = f"""
### {run['workflowName']}
- **Run ID:** {run['databaseId']}
- **Status:** ❌ FAILED
- **Time:** {run['updatedAt']}
- **URL:** {run['url']}
- **Root Cause:** **Investigation Needed**

**Initial Analysis:**
{analyze_failure(run, logs)}

**Impact:** TBD

---
"""
    return report

def analyze_failure(run: dict, logs: str) -> str:
    """Analyze failure logs and provide initial assessment."""
    if "Access denied" in logs:
        return "- Authentication/credentials issue detected\n- Check GitHub Secrets and external service permissions"
    elif "exit code 128" in logs:
        return "- Git operation failure\n- Possible race condition or state corruption"
    elif "RPC failed" in logs or "HTTP 401" in logs:
        return "- Network/authentication failure during push\n- Token permissions may need update"
    elif "MySQL" in logs or "database" in logs:
        return "- Database connectivity issue\n- Verify credentials and IP whitelists"
    else:
        return "- Generic failure detected\n- Requires manual investigation"

def append_to_log(content: str):
    """Append content to the health log file."""
    with open(LOG_FILE, 'a') as f:
        f.write(content)

def check_failures():
    """Main check function."""
    state = load_state()
    state["total_checks"] += 1
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Check if we should skip this check
    if state.get("skip_next"):
        skip_reason = state.get("skip_reason")
        append_to_log(f"\n---\n\n## ⏭️ SKIPPED CHECK ({timestamp})\n\n**Reason:** {skip_reason}\n\n**Next Check:** Will resume at next interval\n")
        state["skip_next"] = False
        state["skip_reason"] = None
        state["last_check"] = timestamp
        save_state(state)
        print(f"Skipping check: {skip_reason}")
        return
    
    try:
        runs = get_recent_runs()
    except Exception as exc:
        append_to_log(f"\n---\n\n## ⚠️ MONITOR ERROR ({timestamp})\n\n**Status:** Could not read GitHub Actions runs\n**Error:** {exc}\n\n---\n")
        state["last_check"] = timestamp
        save_state(state)
        print(f"Monitor error: {exc}")
        return
    
    failures = [r for r in runs if r.get('conclusion') == 'failure']
    
    if not failures:
        append_to_log(f"\n---\n\n## ✅ HEALTHY CHECK ({timestamp})\n\n**Status:** All recent workflows passing\n**Checked:** {len(runs)} recent runs\n**Failures:** 0\n\n---\n")
        state["last_check"] = timestamp
        save_state(state)
        print("All checks passed")
        return
    
    # New failures detected
    new_failures = []
    for failure in failures:
        run_id = str(failure['databaseId'])
        if run_id not in state.get("last_failure_check", {}):
            new_failures.append(failure)
    
    if not new_failures:
        append_to_log(f"\n---\n\n## ℹ️ NO NEW FAILURES ({timestamp})\n\n**Status:** Previously detected failures still being investigated\n**Known Failures:** {len(failures)}\n\n---\n")
        state["last_check"] = timestamp
        save_state(state)
        print("No new failures")
        return
    
    # Log new failures
    header = f"""
---

## 🚨 NEW FAILURES DETECTED ({timestamp})

**Check #{state["total_checks"]}**  
**New Failures:** {len(new_failures)}  
**Total Known Failures:** {len(failures)}

"""
    append_to_log(header)
    
    complex_investigation_needed = False
    
    for failure in new_failures:
        run_id = str(failure['databaseId'])
        logs = get_failure_logs(run_id)
        
        report = format_failure_report(failure, logs)
        append_to_log(report)
        
        state.setdefault("last_failure_check", {})[run_id] = {
            "detected_at": timestamp,
            "workflow": failure['workflowName'],
            "logs_snapshot": logs[:2000] if logs else ""
        }
        
        if is_complex_failure(logs):
            complex_investigation_needed = True
            state["skip_next"] = True
            state["skip_reason"] = f"Complex failure in {failure['workflowName']} (Run #{run_id}) - requires deep investigation"
    
    state["total_failures"] += len(new_failures)
    state["last_check"] = timestamp
    save_state(state)
    
    print(f"Detected {len(new_failures)} new failure(s)")
    if complex_investigation_needed:
        print(f"⚠️  Next check will be skipped due to complex failure requiring investigation")

if __name__ == "__main__":
    check_failures()

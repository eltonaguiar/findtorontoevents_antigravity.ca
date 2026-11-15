"""GitHub Actions full audit — every workflow, then per-workflow health.

Two passes:
  PASS 1  enumerate EVERY workflow defined in .github/workflows (via the API),
          so workflows that never ran are visible, not invisible.
  PASS 2  for each workflow classify the latest state:
            RED_>1        latest completed run failed, streak > 1
            RED_1         latest completed run failed, streak == 1
            SKIPPED       latest completed run was skipped (workflow effectively off)
            STUCK         an in_progress/queued run older than --stuck-min worth
            STALE         no run within --stale-hours (default 26h)
            NEVER_RUN     workflow defined but zero runs on the branch
            NEVER_SUCCEEDED  runs exist, none ever succeeded
            OK

Unauthenticated public REST API (60 req/hr/IP). Uses 1 + pages requests.

Usage:
  python proof/gh_actions_audit.py                     # human report
  python proof/gh_actions_audit.py --json              # machine report
  python proof/gh_actions_audit.py --pages 5 --stale-hours 26 --stuck-min 60

Exit 0 = nothing flagged, 1 = at least one workflow flagged.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://api.github.com"
NEUTRAL = {"cancelled", "skipped", "neutral", "stale"}
DONE = {"success", "failure", "timed_out", "action_required", "startup_failure"}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "hermes-actions-audit",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def age_hours(ts: str | None, now: datetime) -> float | None:
    if not ts:
        return None
    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (now - t).total_seconds() / 3600.0


def check_rate_limit(needed: int = 10) -> dict:
    """Anonymous API allows 60 req/hr/IP shared with every other agent on this
    host. If we are near the floor, say RATE_LIMITED loudly — reporting 'no
    runs' for 366 workflows would read as a catastrophic outage when the truth
    is 'we could not look'."""
    try:
        d = fetch(f"{API}/rate_limit")["resources"]["core"]
    except Exception as e:
        return {"ok": False, "reason": f"cannot read rate_limit: {e}"}
    return {
        "ok": d["remaining"] >= needed,
        "remaining": d["remaining"],
        "limit": d["limit"],
        "reset_in_min": max(0, int((d["reset"] - __import__("time").time()) / 60)),
    }


def state_sweep(repo: str, branch: str, per_page: int = 50) -> dict:
    """Query each terminal problem state directly.

    The run-window scan above only sees the newest N runs, so a run that has
    been QUEUED since May never appears in it. GitHub's status filter is the
    only way to see them, and it is per-state (one call each).
    """
    states = ["action_required", "cancelled", "failure", "neutral",
              "queued", "skipped", "stale", "timed_out", "waiting"]
    now = datetime.now(timezone.utc)
    out = {}
    for s in states:
        q = f"{API}/repos/{repo}/actions/runs?status={s}&per_page={per_page}&branch={branch}"
        try:
            d = fetch(q)
        except Exception as e:
            out[s] = {"error": str(e)}
            continue
        runs = d.get("workflow_runs", [])
        if not runs:
            out[s] = {"total": d.get("total_count", 0), "oldest": None, "oldest_age_h": None,
                      "top": [], "zombie": 0}
            continue
        oldest = min(runs, key=lambda r: r["created_at"])
        age = age_hours(oldest["created_at"], now)
        # a queued run older than 2h is not backlog, it is wedged
        zombie = sum(1 for r in runs
                     if s == "queued" and (age_hours(r["created_at"], now) or 0) > 2.0)
        out[s] = {
            "total": d.get("total_count", 0),
            "oldest": oldest["created_at"],
            "oldest_age_h": round(age, 1) if age else None,
            "zombie": zombie,
            "top": [{"name": r["name"], "created_at": r["created_at"],
                     "id": r["id"], "url": r.get("html_url")} for r in runs[:5]],
        }
    return out


def collect_workflow_defs(repo: str, branch: str) -> dict[str, dict]:
    """All workflow files defined on the branch (catches never-run ones).

    The workflows endpoint is PAGINATED at 100/page — the repo has ~367
    workflows, so a single page silently hides two-thirds of them.
    """
    out = {}
    page = 1
    while page <= 5:
        try:
            d = fetch(f"{API}/repos/{repo}/actions/workflows?per_page=100&page={page}&branch={branch}")
        except Exception as e:
            print(f"WARN: workflow list page {page} failed: {e}", file=sys.stderr)
            break
        batch = d.get("workflows", [])
        if not batch:
            break
        for wf in batch:
            out[wf["name"]] = {
                "path": wf.get("path"),
                "id": wf.get("id"),
                "state": wf.get("state"),
            }
        if len(batch) < 100:
            break
        page += 1
    return out


def collect_runs(repo: str, pages: int, branch: str | None) -> list[dict]:
    runs = []
    for p in range(1, pages + 1):
        q = f"{API}/repos/{repo}/actions/runs?per_page=100&page={p}"
        if branch:
            q += f"&branch={branch}"
        try:
            data = fetch(q)
        except Exception as e:
            print(f"WARN: runs page {p} failed: {e}", file=sys.stderr)
            break
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
    return runs


def analyse(defs: dict[str, dict], runs: list[dict], stale_hours: float,
            stuck_min: float) -> dict:
    now = datetime.now(timezone.utc)
    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_wf[r.get("name") or str(r.get("workflow_id"))].append(r)

    names = sorted(set(defs) | set(by_wf))
    rows = []
    for name in names:
        rs = sorted(by_wf.get(name, []), key=lambda r: r["created_at"], reverse=True)
        d = defs.get(name, {})
        row = {
            "workflow": name,
            "path": d.get("path"),
            "defined": bool(d),
            "state": d.get("state"),
            "disabled": bool(d.get("state") and "disabled" in str(d.get("state"))),
            "runs_seen": len(rs),
            "flag": "OK",
            "detail": "",
            "last_run_at": rs[0]["created_at"] if rs else None,
            "age_hours": round(age_hours(rs[0]["created_at"], now), 1) if rs else None,
            "last_url": rs[0].get("html_url") if rs else None,
        }

        # A disabled workflow is a silent outage regardless of its run history:
        # GitHub keeps showing the last (possibly green) run while nothing fires.
        if row["disabled"]:
            row["flag"] = "DISABLED"
            row["detail"] = f"state={row['state']} — will not run until re-enabled"
            rows.append(row)
            continue

        if not rs:
            # NBNB: absence inside the scanned window is NOT proof it never ran.
            # Only a workflow with zero runs across the window AND a defined
            # file is reported as out-of-window, never as NEVER_RUN.
            row["flag"] = "NO_RUNS_IN_WINDOW" if d else "UNKNOWN"
            row["detail"] = ("defined; no runs among the scanned runs "
                             "(widen --pages before calling this dead)") if d else "runs only, no definition"
            rows.append(row)
            continue

        # in-flight runs first — a stuck run is its own failure mode
        inflight = [r for r in rs if r.get("status") in ("in_progress", "queued")]
        stuck = [r for r in inflight if (age_hours(r["created_at"], now) or 0) > stuck_min / 60.0]

        completed = [r for r in rs if r.get("conclusion") in DONE or r.get("conclusion") in NEUTRAL]
        last = completed[0] if completed else None
        if not completed:
            row["flag"] = "STUCK" if stuck else "IN_FLIGHT"
            row["detail"] = f"{len(inflight)} run(s) not completed"
            rows.append(row)
            continue

        row["last_conclusion"] = last["conclusion"]
        streak = 0
        for r in completed:
            if r["conclusion"] in NEUTRAL:
                continue
            if r["conclusion"] == "failure":
                streak += 1
            else:
                break
        successes = [r for r in rs if r.get("conclusion") == "success"]
        row["last_success_at"] = successes[0]["created_at"] if successes else None
        row["streak"] = streak

        if stuck:
            row["flag"] = "STUCK"
            row["detail"] = f"{len(stuck)} run(s) > {stuck_min:.0f}min in progress (run {stuck[0]['id']})"
        elif last["conclusion"] == "failure":
            row["flag"] = "RED_>1" if streak > 1 else "RED_1"
            row["detail"] = f"{streak} consecutive failure(s)"
        elif last["conclusion"] == "skipped":
            row["flag"] = "SKIPPED"
            row["detail"] = "latest completed run was skipped — workflow effectively off"
        elif last["conclusion"] not in ("success",):
            row["flag"] = "ODD"
            row["detail"] = f"latest conclusion={last['conclusion']}"
        elif row["age_hours"] and row["age_hours"] > stale_hours:
            row["flag"] = "STALE"
            row["detail"] = f"last run {row['age_hours']:.1f}h ago (> {stale_hours:.0f}h)"
        if not row["last_success_at"] and row["flag"].startswith("RED"):
            row["detail"] += "; NEVER SUCCEEDED"

        rows.append(row)

    order = {"RED_>1": 0, "RED_1": 1, "STUCK": 2, "DISABLED": 3, "NEVER_SUCCEEDED": 4, "SKIPPED": 5,
             "STALE": 6, "NO_RUNS_IN_WINDOW": 7, "ODD": 8, "IN_FLIGHT": 9, "UNKNOWN": 10, "OK": 11}
    rows.sort(key=lambda r: (order.get(r["flag"], 99), -(r.get("streak") or 0), r["workflow"]))

    counts = defaultdict(int)
    for r in rows:
        counts[r["flag"]] += 1
    flagged = [r for r in rows if r["flag"] not in ("OK", "IN_FLIGHT")]
    return {
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflows_total": len(rows),
        "flagged": len(flagged),
        "counts": dict(counts),
        "workflows": rows,
    }


def secondary_recent(repo: str, n: int = 2, branch: str | None = None) -> dict:
    """Last N runs of a secondary repo + whether any failure was followed by success."""
    q = f"{API}/repos/{repo}/actions/runs?per_page={max(n + 20, 30)}"
    if branch:
        q += f"&branch={branch}"
    try:
        d = fetch(q)
    except Exception as e:
        return {"repo": repo, "error": str(e)}
    runs = d.get("workflow_runs", [])
    if not runs:
        return {"repo": repo, "runs": [], "note": "no runs"}
    recent = runs[:n]
    out = []
    for r in recent:
        later_success = next(
            (x for x in runs
             if x["name"] == r["name"] and x["created_at"] > r["created_at"]
             and x.get("conclusion") == "success"), None)
        out.append({
            "workflow": r["name"], "conclusion": r.get("conclusion"),
            "created_at": r["created_at"], "url": r.get("html_url"),
            "resolved_by_later_success": bool(later_success),
        })
    return {"repo": repo, "runs": out, "total_count": d.get("total_count")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="eltonaguiar/findtorontoevents_antigravity.ca")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--stale-hours", type=float, default=26.0)
    ap.add_argument("--stuck-min", type=float, default=60.0)
    ap.add_argument("--secondary", default="eltonaguiar/BESTIEJOB")
    ap.add_argument("--secondary-runs", type=int, default=2)
    ap.add_argument("--states", action="store_true",
                    help="also sweep the 9 problem states directly (9 extra API calls)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rl = check_rate_limit(needed=(8 + a.pages + (9 if a.states else 0)))
    if not rl.get("ok"):
        print("RATE_LIMITED: cannot audit right now — this is NOT a green result.")
        print(f"  remaining={rl.get('remaining')}/{rl.get('limit')} "
              f"reset_in={rl.get('reset_in_min')}min reason={rl.get('reason','')}")
        print("  The unauthenticated 60 req/hr limit is shared with every other agent on this host.")
        print("  Fix: supply a GitHub token (GITHUB_TOKEN / PAT with actions:read) or retry after reset.")
        return 2

    defs = collect_workflow_defs(a.repo, a.branch)
    runs = collect_runs(a.repo, a.pages, a.branch)
    res = analyse(defs, runs, a.stale_hours, a.stuck_min)
    res["runs_scanned"] = len(runs)
    sec = secondary_recent(a.secondary, a.secondary_runs, a.branch)
    res["secondary"] = sec
    if a.states:
        res["states"] = state_sweep(a.repo, a.branch)

    if a.json:
        print(json.dumps(res, indent=2))
    else:
        c = res["counts"]
        print(f"repo {a.repo}  branch {a.branch}  runs_scanned {len(runs)}  {res['generated_utc']}")
        print(f"workflows defined+seen: {res['workflows_total']}   FLAGGED: {res['flagged']}")
        print("  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items()) if k != "OK"))
        print()
        print(f"{'flag':14} {'streak':>6}  {'age_h':>6}  {'workflow':44} detail")
        print("-" * 122)
        for r in res["workflows"]:
            if r["flag"] in ("OK",):
                continue
            print(f"{r['flag']:14} {r.get('streak', 0):>6}  {str(r['age_hours']):>6}  "
                  f"{r['workflow'][:44]:44} {r['detail'][:48]}")
        ok = c.get("OK", 0)
        print(f"\n{ok} workflow(s) OK.")
        for r in res["workflows"]:
            if r["flag"] in ("RED_>1", "RED_1", "STUCK", "SKIPPED") and r["last_url"]:
                print(f"  {r['flag']:8} {r['workflow'][:50]:50} {r['last_url']}")

        print(f"\n--- SECONDARY: {a.secondary} — last {a.secondary_runs} run(s) ---")
        s = res.get("secondary", {})
        if s.get("error"):
            print(f"  could not read: {s['error']}")
        for r in s.get("runs", []):
            state = r["conclusion"] or "in-flight"
            resolved = ("then-succeeded" if r["resolved_by_later_success"]
                        else ("NO SUBSEQUENT SUCCESS" if state == "failure" else "-"))
            print(f"  {state:12} {r['created_at'][:19]}  {r['workflow'][:44]:44} {resolved}")
            if state == "failure" and not r["resolved_by_later_success"]:
                print(f"               {r['url']}")

        st = res.get("states")
        if st:
            print("\n--- STATE SWEEP (direct status queries; window scan cannot see old runs) ---")
            print(f"  {'state':16} {'total':>7} {'oldest':20} {'age_h':>8}  flag")
            for name, v in st.items():
                if v.get("error"):
                    print(f"  {name:16} {'ERR':>7}  {v['error'][:40]}")
                    continue
                flag = ""
                if name == "queued" and v.get("zombie"):
                    flag = f"ZOMBIE x{v['zombie']} (queued > 2h, never acquired a runner)"
                elif name in ("failure",) and v.get("total"):
                    flag = "needs per-workflow triage (see RED rows above)"
                print(f"  {name:16} {v.get('total', 0):>7} {str(v.get('oldest'))[:19]:20} "
                      f"{str(v.get('oldest_age_h')):>8}  {flag}")

    zombie = int((res.get("states") or {}).get("queued", {}).get("zombie") or 0)
    return 1 if (res["flagged"] or zombie) else 0


if __name__ == "__main__":
    sys.exit(main())
